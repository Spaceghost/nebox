"""Boot a Theseus-enabled nebox with a supplied Linux bzImage in QEMU."""

import argparse
import os
from pathlib import Path
import selectors
import stat
import subprocess
import tempfile
import time


def write_initramfs(path, nebox, lua=None, necc=None, nebuild=None):
    entries = [
        ("bin", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("dev", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("proc", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("sys", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("mnt", stat.S_IFDIR | 0o755, b"", 0, 0),
        ("dev/console", stat.S_IFCHR | 0o600, b"", 5, 1),
        ("bin/nebox", stat.S_IFREG | 0o755, nebox.read_bytes(), 0, 0),
        ("init", stat.S_IFLNK | 0o777, b"/bin/nebox", 0, 0),
    ]
    if lua or nebuild:
        entries.append(("bin/sh", stat.S_IFLNK | 0o777, b"nebox", 0, 0))
    if lua:
        entries.append(("bin/nelua-lua", stat.S_IFREG | 0o755, lua.read_bytes(), 0, 0))
    if nebuild:
        entries.extend([
            ("bin/nebuild", stat.S_IFREG | 0o755, nebuild.read_bytes(), 0, 0),
            ("demo.ne", stat.S_IFREG | 0o644,
             b"build answer\n\tprintf 42 > answer\ndefault answer\n", 0, 0),
        ])
    if necc:
        entries.extend([
            ("bin/necc", stat.S_IFREG | 0o755, necc.read_bytes(), 0, 0),
            ("answer.c", stat.S_IFREG | 0o644, b"int main(void) { return 6 * 7; }\n", 0, 0),
        ])
    entries.append(("TRAILER!!!", 0, b"", 0, 0))
    with path.open("wb") as archive:
        for inode, (name, mode, data, major, minor) in enumerate(entries, 1):
            filename = name.encode() + b"\0"
            fields = (inode, mode, 0, 0, 1, 0, len(data), 0, 0,
                      major, minor, len(filename), 0)
            archive.write(b"070701" + "".join(f"{value:08x}" for value in fields).encode())
            archive.write(filename)
            archive.write(b"\0" * (-archive.tell() % 4))
            archive.write(data)
            archive.write(b"\0" * (-archive.tell() % 4))


def smoke(kernel, initramfs, lua=False, necc=False, nebuild=False):
    vm = subprocess.Popen(
        ["qemu-system-x86_64", "-nodefaults", "-display", "none",
         "-serial", "stdio", "-m", "256M", "-no-reboot",
         "-kernel", str(kernel), "-initrd", str(initramfs),
         "-append", "console=ttyS0 rdinit=/init quiet"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(vm.stdout, selectors.EVENT_READ)

            def expect(marker, timeout):
                deadline = time.monotonic() + timeout
                while marker not in output:
                    if not selector.select(max(0, deadline - time.monotonic())):
                        raise RuntimeError(f"Timed out waiting for {marker!r}")
                    chunk = os.read(vm.stdout.fileno(), 4096)
                    if not chunk:
                        raise RuntimeError(f"QEMU exited before {marker!r}")
                    output.extend(chunk)

            expect(b"theseus: starting console shell", 45)
            vm.stdin.write(
                b"/bin/nebox grep -q ' /proc proc ' /proc/mounts && "
                b"/bin/nebox grep -q ' /sys sysfs ' /proc/mounts && "
                b"/bin/nebox mount -t tmpfs tmpfs /mnt && "
                b"/bin/nebox grep -q ' /mnt tmpfs ' /proc/mounts && "
                b"/bin/nebox true && printf 'THESEUS_%s\\n' BOOT_OK\n"
            )
            vm.stdin.flush()
            expect(b"THESEUS_BOOT_OK", 15)
            if lua:
                vm.stdin.write(
                    b"/bin/nelua-lua -e 'assert(require(\"lfs\").attributes(\"/mnt\", \"mode\") == \"directory\"); "
                    b"assert(os.execute(\"/bin/nebox true\")); assert(6 * 7 == 42)' && "
                    b"printf 'THESEUS_%s\\n' LUA_OK\n"
                )
                vm.stdin.flush()
                expect(b"THESEUS_LUA_OK", 15)
            if necc:
                vm.stdin.write(
                    b"/bin/necc /answer.c -o /mnt/answer.s && "
                    b"/bin/nebox grep -q 'imull %ecx, %eax' /mnt/answer.s && "
                    b"printf 'THESEUS_%s\\n' NECC_OK\n"
                )
                vm.stdin.flush()
                expect(b"THESEUS_NECC_OK", 15)
            if nebuild:
                vm.stdin.write(
                    b"(cd /mnt && /bin/nebuild /demo.ne && "
                    b"test \"$(/bin/nebox cat answer)\" = 42 && "
                    b"/bin/nebuild /demo.ne > noop.log && test ! -s noop.log) && "
                    b"printf 'THESEUS_%s\\n' NEBUILD_OK\n"
                )
                vm.stdin.flush()
                expect(b"THESEUS_NEBUILD_OK", 15)
            vm.stdin.write(
                b"/bin/nebox sh -c '/bin/nebox sleep 3 & echo $! > /mnt/orphan'; "
                b"read pid < /mnt/orphan; "
                b"if /bin/nebox grep -Eq '^PPid:[[:space:]]+1$' /proc/$pid/status; "
                b"then while test -e /proc/$pid; do /bin/nebox sleep 1; done; "
                b"printf 'THESEUS_%s\\n' REAP_OK; fi\n"
            )
            vm.stdin.flush()
            expect(b"THESEUS_REAP_OK", 15)
            vm.stdin.write(b"exit\nprintf 'THESEUS_%s\\n' RESPAWN_OK\n")
            vm.stdin.flush()
            expect(b"THESEUS_RESPAWN_OK", 15)
    except Exception:
        print(output.decode(errors="replace"), end="")
        raise
    finally:
        vm.terminate()
        try:
            vm.wait(timeout=5)
        except subprocess.TimeoutExpired:
            vm.kill()
            vm.wait()
    print("Theseus boot, tmpfs mount, child execution, orphan reaping, and shell respawn passed")
    if lua:
        print("Lua arithmetic, filesystem access, and Nebox shell execution passed")
    if necc:
        print("necc compiled C to x86-64 assembly inside the guest")
    if nebuild:
        print("nebuild built a target and skipped a no-op rebuild inside the guest")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel", type=Path)
    parser.add_argument("nebox", type=Path)
    parser.add_argument("--lua", type=Path, help="standalone Nelua Lua interpreter")
    parser.add_argument("--necc", type=Path, help="standalone necc compiler")
    parser.add_argument("--nebuild", type=Path, help="standalone nebuild runner")
    parser.add_argument("--initramfs-out", type=Path, help="retain the initramfs at this path")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="theseus-boot-") as tmp:
        image = args.initramfs_out or Path(tmp) / "initramfs.cpio"
        write_initramfs(image, args.nebox, args.lua, args.necc, args.nebuild)
        smoke(args.kernel, image, bool(args.lua), bool(args.necc), bool(args.nebuild))
