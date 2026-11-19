"""Render the x86-64 bootstrap graph for a staged Nebox image."""

import argparse
from pathlib import Path
import shlex


ZIG = "/tool/zig/zig"
ZIG_LIB = "/tool/zig/lib"
NELIBC = "/work/src/nelibc"
NELUA = "/work/src/nelua"
NEBOX = "/work/src/nebox"
THESEUS = "/work/src/theseus"
NATIVE = "/work/native-nelua"
OUT = "/work/out"
ARCHIVE = f"{OUT}/lib/libnelibc-standalone-zig.a"


def sources(root, path, suffixes):
    return [
        "/" + candidate.relative_to(root).as_posix()
        for candidate in sorted((root / path.lstrip("/")).rglob("*"))
        if candidate.is_file() and candidate.suffix in suffixes
    ]


def edge(output, inputs, command):
    print(" ".join(["build", output, *dict.fromkeys(inputs)]))
    print("\t" + command)


def archive_plan(recipes):
    archives = []
    compiled = {}
    for command in recipes.splitlines():
        if command.startswith(ZIG + " ar "):
            args = shlex.split(command)
            if args[2:4] == ["rcs", ARCHIVE]:
                archives.append((command, args[4:]))
        elif command.startswith((ZIG + " cc ", NELUA + "/nelua ")):
            args = shlex.split(command)
            if "-o" in args:
                output = args[args.index("-o") + 1]
                old = compiled.setdefault(output, (command, args))
                if old[0] != command:
                    raise ValueError(f"conflicting recipes for {output}")
    members = list(dict.fromkeys(path for _, paths in archives for path in paths))
    if not members:
        raise ValueError(f"missing archive recipes for {ARCHIVE}")
    for output in members:
        if output not in compiled:
            raise ValueError(f"missing compile recipe for {output}")
    return archives, members, compiled


def render(root, recipes):
    archives, members, compiled = archive_plan(recipes)
    headers = sources(root, NELIBC + "/include", {".h"})
    nelua_modules = sources(root, NELUA + "/lib", {".nelua", ".lua", ".h"})
    nelua_modules += sources(root, NELUA + "/lualib", {".lua"})
    seed = [NELUA + "/nelua", NELUA + "/nelua-lua", *nelua_modules]

    for output in members:
        command, args = compiled[output]
        inputs = [ZIG, *headers, *(f"{NELIBC}/{arg}" for arg in args if arg.startswith("src/"))]
        if args[0] == NELUA + "/nelua":
            inputs.extend(seed)
        edge(output, inputs, f"cd {NELIBC} && {command}")

    archive_commands = " && ".join(command for command, _ in archives)
    edge(ARCHIVE, [ZIG, *members], f"rm -f {ARCHIVE} && {archive_commands}")

    recipe = NELIBC + "/tools/build-nelua-runtime.sh"
    runtime_sources = sources(root, NELUA + "/src", {".c", ".h"})
    edge(
        NATIVE + "/nelua-lua",
        [ZIG, ARCHIVE, recipe, *runtime_sources, *headers],
        f"/bin/sh {recipe} {ZIG} {ZIG_LIB} {NELUA} {NELIBC} {ARCHIVE} {NATIVE}/nelua-lua",
    )

    cflags = (
        "-DNELIBC_STANDALONE -nostdlib -static -no-pie -fno-pie "
        "-fno-stack-protector -ffreestanding -fno-builtin -fno-sanitize=all "
        f"-Wl,-e,_start -Wl,--build-id=none -I{NELIBC}/include "
        f"-isystem {ZIG_LIB}/libc/include/x86-linux-any "
        f"-isystem {ZIG_LIB}/libc/include/any-linux-any "
        "-DNEBOX_NELIBC_STAMP=$stamp"
    )
    ldflags = f"-Wl,--whole-archive {ARCHIVE} -Wl,--no-whole-archive -Wl,--strip-all"
    edge(
        OUT + "/nebox",
        [ZIG, ARCHIVE, NATIVE + "/nelua", NATIVE + "/nelua-lua", *headers, *nelua_modules,
         *sources(root, NEBOX + "/src", {".nelua"}), *sources(root, THESEUS + "/src", {".nelua"})],
        f"cd {NEBOX} && "
        f"stamp=$(sha256sum {ARCHIVE} | cut -c1-16) && "
        f"{NATIVE}/nelua --cache-dir /work/cache/nebox -r -L src "
        f"-L {THESEUS}/src -D THESEUS_BOOT=true "
        f"--cc '{ZIG} cc -target x86_64-linux-musl -mcpu=x86_64' "
        f'--cflags="{cflags}" --ldflags=\'{ldflags}\' -o {OUT}/nebox src/nebox.nelua',
    )
    print(f"default {OUT}/nebox")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image_root", type=Path)
    parser.add_argument("nelibc_recipes", type=Path, help="output of make -n -B lib-standalone-zig")
    args = parser.parse_args()
    render(args.image_root, args.nelibc_recipes.read_text())
