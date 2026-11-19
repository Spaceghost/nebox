"""Boot a Theseus-enabled nebox with a supplied Linux bzImage in QEMU."""

import argparse
from contextlib import nullcontext
import os
from pathlib import Path
import selectors
import stat
import subprocess
import tempfile
import time


def sdk_files(sdk, compiler_source, runtime_source):
    def directory(name, mode=0o755):
        return (name, stat.S_IFDIR | mode, b"", 0, 0)

    def regular(name, data, mode=0o644):
        return (name, stat.S_IFREG | mode, data, 0, 0)

    yield directory("tmp", 0o1777)
    yield directory("usr")
    yield directory("usr/lib")
    yield directory("usr/lib/necc")
    yield directory("usr/src")
    yield directory("usr/src/demo")
    yield ("dev/null", stat.S_IFCHR | 0o666, b"", 1, 3)
    yield ("dev/urandom", stat.S_IFCHR | 0o666, b"", 1, 9)
    for applet in ("basename", "cat", "cmp", "dirname", "env", "mkdir", "pwd",
                   "readlink", "realpath", "rm", "uname", "which"):
        yield ("bin/" + applet, stat.S_IFLNK | 0o777, b"nebox", 0, 0)
    for path in sorted(sdk.rglob("*")):
        name = "usr/lib/necc/" + path.relative_to(sdk).as_posix()
        if path.is_symlink():
            yield (name, stat.S_IFLNK | 0o777, os.fsencode(os.readlink(path)), 0, 0)
        elif path.is_dir():
            yield directory(name)
        elif path.is_file():
            yield regular(name, path.read_bytes(), 0o755 if path.stat().st_mode & 0o111 else 0o644)
    yield regular("usr/src/demo/hello.c", b"""#include <stdint.h>
#include <stdio.h>
int main(void) { int64_t n = INT64_C(3000000000); printf("native %ld\\n", n + 42); return 23; }
""")
    yield regular("usr/src/demo/arrays.nelua", b"""local t: [3]integer = {10, 12, 20}
print(t[0] + t[1] + t[2])
""")
    yield regular("usr/src/demo/direct.nelua", b"do return 42 end\n")
    yield regular("usr/src/demo/args.lua", b"""assert(arg[1] == 'two words')
assert(require('lfs').attributes('/mnt', 'mode') == 'directory')
print(_VERSION)
""")
    graph = []
    for output, filename, flags in (("native", "hello.c", ""), ("arrays", "arrays.nelua", ""),
                                    ("direct", "direct.nelua", "--direct ")):
        src = "/usr/src/demo/" + filename
        deps = [src, "/bin/necc", "/usr/lib/necc/tcc/tcc", "/usr/lib/necc/libnelibc.a"]
        if output == "arrays":
            deps.append("/usr/lib/necc/nelua-lua")
        elif output == "direct":
            deps.append("/usr/lib/necc/nlc")
        graph.extend(["build " + " ".join([output, *deps]), f"\t/bin/necc {flags}{src} -o {output}"])
    graph.append("default native arrays direct")
    yield regular("usr/src/demo/build.ne", ("\n".join(graph) + "\n").encode())
    if compiler_source:
        yield directory("usr/src/necc")
        for path in sorted(compiler_source.glob("*.nelua")):
            yield regular("usr/src/necc/" + path.name, path.read_bytes())

    if runtime_source:
        yield regular("usr/src/necc/render-lua.lua", (compiler_source / "render-lua.lua").read_bytes())
        yield directory("usr/src/nelua")
        yield directory("usr/src/nelua/src")
        root = runtime_source / "src"
        for path in sorted(root.rglob("*")):
            name = "usr/src/nelua/src/" + path.relative_to(root).as_posix()
            if path.is_dir():
                yield directory(name)
            elif path.suffix in {".c", ".h", ".lua"}:
                yield regular(name, path.read_bytes())


def write_initramfs(path, nebox, lua=None, necc=None, nebuild=None, nlc=None,
                    sdk=None, compiler_source=None, runtime_source=None):
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
    if nlc:
        entries.extend([
            ("bin/nlc", stat.S_IFREG | 0o755, nlc.read_bytes(), 0, 0),
            ("answer.nelua", stat.S_IFREG | 0o644, b"do return 42 end\n", 0, 0),
        ])
    if sdk:
        entries.extend(sdk_files(sdk, compiler_source, runtime_source))
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


def smoke(kernel, initramfs, lua=False, necc=False, nebuild=False, nlc=False,
          sdk=False, compiler_source=False, runtime_source=False, serial_log=None, distro=False):
    vm = subprocess.Popen(
        ["qemu-system-x86_64", "-nodefaults", "-display", "none",
         "-serial", "stdio", "-m", "512M" if sdk or distro else "256M", "-no-reboot",
         "-kernel", str(kernel), "-initrd", str(initramfs),
         "-append", "console=ttyS0 rdinit=/init quiet"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    output = bytearray()
    try:
        with selectors.DefaultSelector() as selector, (serial_log.open("wb") if serial_log else nullcontext()) as transcript:
            selector.register(vm.stdout, selectors.EVENT_READ)

            def expect(marker, timeout, failure=None):
                deadline = time.monotonic() + timeout
                while marker not in output:
                    if failure and failure in output:
                        raise RuntimeError(f"Guest command reported {failure!r}")
                    if not selector.select(max(0, deadline - time.monotonic())):
                        raise RuntimeError(f"Timed out waiting for {marker!r}")
                    chunk = os.read(vm.stdout.fileno(), 4096)
                    if not chunk:
                        raise RuntimeError(f"QEMU exited before {marker!r}")
                    output.extend(chunk)
                    if transcript:
                        transcript.write(chunk)
                        transcript.flush()

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
            if distro:
                vm.stdin.write(
                    b"export PATH=/bin:/usr/bin HOME=/root TMPDIR=/tmp; "
                    b"(cd /mnt && test -x /usr/bin/ls && test -c /dev/null && test -d /root && "
                    b"test \"$(id -un)\" = root && test \"$(lua -e 'print(_VERSION)')\" = 'Lua 5.4' && "
                    b"printf 'int main(void) {return 42;}\\n' > check.c && "
                    b"printf 'build check check.c\\n\\tcc check.c -o check\\ndefault check\\n' > build.ne && "
                    b"nebuild build.ne && { rc=0; ./check || rc=$?; test \"$rc\" = 42; } && "
                    b"nebuild build.ne > noop && test ! -s noop && "
                    b"printf 'local t: [2]integer = {20,22}\\nprint(t[0]+t[1])\\n' > demo.nelua && "
                    b"necc demo.nelua -o demo && test \"$(./demo)\" = 42) && "
                    b"printf 'THESEUS_%s\\n' DISTRO_OK || printf 'THESEUS_%s\\n' DISTRO_FAILED\n"
                )
                vm.stdin.flush()
                expect(b"THESEUS_DISTRO_OK", 120, b"THESEUS_DISTRO_FAILED")
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
            if nlc:
                vm.stdin.write(
                    b"NLC_INPUT=/answer.nelua NLC_OUTPUT=/mnt/answer.c /bin/nlc && "
                    b"/bin/nebox grep -Fq 'return INT64_C(42);' /mnt/answer.c && "
                    b"printf 'THESEUS_%s\\n' NLC_OK\n"
                )
                vm.stdin.flush()
                expect(b"THESEUS_NLC_OK", 15)
            if sdk:
                vm.stdin.write(
                    b"export PATH=/bin HOME=/tmp TMPDIR=/tmp; "
                    b"(cd /mnt && /bin/nebuild -j 2 /usr/src/demo/build.ne && "
                    b"{ rc=0; ./native > c.out || rc=$?; test \"$rc\" = 23; } && "
                    b"test \"$(cat c.out)\" = 'native 3000000042' && test \"$(./arrays)\" = 42 && "
                    b"{ rc=0; ./direct || rc=$?; test \"$rc\" = 42; } && "
                    b"test \"$(/bin/necc /usr/src/demo/args.lua 'two words')\" = 'Lua 5.4' && "
                    b"/bin/nebuild -j 2 /usr/src/demo/build.ne > sdk-noop && test ! -s sdk-noop) && "
                    b"printf 'THESEUS_%s\\n' SDK_OK || printf 'THESEUS_%s\\n' SDK_FAILED\n"
                )
                vm.stdin.flush()
                expect(b"THESEUS_SDK_OK", 120, b"THESEUS_SDK_FAILED")
                if compiler_source:
                    vm.stdin.write(
                        b"(cd /usr/src/necc && /bin/necc necc.nelua -o /mnt/necc2 && "
                        b"/mnt/necc2 necc.nelua -o /mnt/necc3 && cmp /mnt/necc2 /mnt/necc3 && "
                        b"/mnt/necc3 /usr/src/demo/hello.c -o /mnt/rebuilt-hello && "
                        b"{ rc=0; /mnt/rebuilt-hello > /mnt/rebuilt.out || rc=$?; test \"$rc\" = 23; } && "
                        b"test \"$(cat /mnt/rebuilt.out)\" = 'native 3000000042') && "
                        b"printf 'THESEUS_%s\\n' SDK_REBUILD_OK || printf 'THESEUS_%s\\n' SDK_REBUILD_FAILED\n"
                    )
                    vm.stdin.flush()
                    expect(b"THESEUS_SDK_REBUILD_OK", 360, b"THESEUS_SDK_REBUILD_FAILED")
                if runtime_source:
                    vm.stdin.write(
                        b"(mkdir /mnt/runtime && cd /mnt/runtime && "
                        b"/bin/necc --lua /usr/src/necc/render-lua.lua /mnt/necc3 /usr/lib/necc /usr/src/nelua > build.ne && "
                        b"/bin/nebuild -j 4 build.ne > build.log && "
                        b"/bin/nebox ln -s /usr/lib/necc/lualib lualib && /bin/nebox ln -s /usr/lib/necc/lib lib && "
                        b"./nelua-lua -e 'assert(load(\"local _aF09=0x2a; return _aF09\")() == 42); "
                        b"assert(require(\"lfs\").currentdir() == \"/mnt/runtime\")' && "
                        b"./nelua-lua -lnelua nelua.lua --cc /usr/lib/necc/tcc/tcc --cache-dir /tmp "
                        b"-c -o /mnt/runtime/full.c /usr/src/demo/arrays.nelua && "
                        b"/bin/nebox grep -q 'Generated by Nelua' full.c && "
                        b"/bin/nebuild -j 4 build.ne > noop.log && test ! -s noop.log) && "
                        b"printf 'THESEUS_%s\\n' RUNTIME_REBUILD_OK || printf 'THESEUS_%s\\n' RUNTIME_REBUILD_FAILED\n"
                    )
                    vm.stdin.flush()
                    expect(b"THESEUS_RUNTIME_REBUILD_OK", 360, b"THESEUS_RUNTIME_REBUILD_FAILED")
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
    if distro:
        print("The packaged distro booted with applet links, root account lookup, Lua, a native C build and a full Nelua executable")
    if lua:
        print("Lua arithmetic, filesystem access, and Nebox shell execution passed")
    if necc:
        print("necc compiled C to x86-64 assembly inside the guest")
    if nebuild:
        print("nebuild built a target and skipped a no-op rebuild inside the guest")
    if nlc:
        print("The necc-built frontend compiled Nelua to C inside the guest")
    if sdk:
        print("The guest built and ran native C and both Nelua frontends, ran Lua, and skipped a parallel no-op")
    if compiler_source:
        print("Two guest rebuilds of necc matched byte for byte and the rebuilt compiler compiled a working C program")
    if runtime_source:
        print("The guest rebuilt the complete Lua runtime with nebuild, compiled its lexer table with necc, and used the new runtime to compile Nelua")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kernel", type=Path)
    parser.add_argument("nebox", type=Path, nargs="?")
    parser.add_argument("--boot-image", type=Path, help="boot and test a development initramfs from tools/distro_image.lua")
    parser.add_argument("--lua", type=Path, help="standalone Nelua Lua interpreter")
    parser.add_argument("--necc", type=Path, help="standalone necc compiler")
    parser.add_argument("--nebuild", type=Path, help="standalone nebuild runner")
    parser.add_argument("--nlc", type=Path, help="standalone Nelua subset frontend built by necc")
    parser.add_argument("--sdk", type=Path, help="staged necc SDK directory")
    parser.add_argument("--necc-source", type=Path, help="rebuild necc from these Nelua sources inside the guest")
    parser.add_argument("--runtime-source", type=Path, help="rebuild the bundled Lua interpreter from this Nelua checkout in the guest")
    parser.add_argument("--serial-log", type=Path, help="save the guest serial console as it runs")
    parser.add_argument("--initramfs-out", type=Path, help="retain the initramfs at this path")
    args = parser.parse_args()
    if args.boot_image:
        if any((args.nebox, args.lua, args.necc, args.nebuild, args.nlc, args.sdk, args.necc_source, args.runtime_source, args.initramfs_out)):
            parser.error("--boot-image accepts a kernel and an optional --serial-log")
        smoke(args.kernel, args.boot_image, serial_log=args.serial_log, distro=True)
        parser.exit()
    if not args.nebox:
        parser.error("supply a Nebox executable or --boot-image")
    if args.sdk and not (args.necc and args.nebuild):
        parser.error("--sdk requires --necc and --nebuild")
    if args.necc_source and not args.sdk:
        parser.error("--necc-source requires --sdk")
    if args.runtime_source and not args.necc_source:
        parser.error("--runtime-source requires --necc-source")
    with tempfile.TemporaryDirectory(prefix="theseus-boot-") as tmp:
        image = args.initramfs_out or Path(tmp) / "initramfs.cpio"
        write_initramfs(image, args.nebox, args.lua, args.necc, args.nebuild, args.nlc, args.sdk, args.necc_source, args.runtime_source)
        smoke(args.kernel, image, args.lua, args.necc, args.nebuild, args.nlc, args.sdk, args.necc_source, args.runtime_source, args.serial_log)
