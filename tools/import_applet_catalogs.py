#!/usr/bin/env python3
"""Import the declared applet names from the pinned upstream release archives."""

import argparse
import hashlib
from pathlib import Path
import re
import tarfile


# BusyBox scripts/gen_build_files.sh reads //applet: lines in */*.c and */*/*.c.
# Keep the public name (first argument), including aliases and scripted applets.
BUSYBOX_DECL = re.compile(
    rb"^//applet:IF_.*?\bAPPLET(?:_(?:NOEXEC|NOFORK|ODDNAME|SCRIPTED))?\(\s*([^,\s]+)\s*,"
)
# Toybox scripts/make.sh collects every USE_ entry in toys/*/*.c, including
# pending, platform-specific, shell-only and example commands, before config.
TOYBOX_DECL = re.compile(rb"^USE_[A-Z0-9_]+\((?:NEW|OLD)TOY\(\s*([^,\s]+)\s*,")


def read_catalog(path, digest, sources, declaration, shell_flag=None):
    names = set()
    shell_only = set()
    with path.open("rb") as archive:
        checksum = hashlib.sha256()
        for block in iter(lambda: archive.read(1024 * 1024), b""):
            checksum.update(block)
        if checksum.hexdigest() != digest:
            raise ValueError(f"{path}: expected SHA-256 {digest}, got {checksum.hexdigest()}")
        archive.seek(0)
        with tarfile.open(fileobj=archive, mode="r|*") as tar:
            for member in tar:
                if member.isfile() and sources.fullmatch(member.name):
                    with tar.extractfile(member) as source:
                        for line in source:
                            match = declaration.match(line)
                            if match:
                                name = match[1].decode("ascii")
                                names.add(name)
                                # Toybox's toy_exec_which skips NOFORK entries. BusyBox
                                # NOFORK applets are callable through its multiplexer.
                                if shell_flag and shell_flag in line[match.end():]:
                                    shell_only.add(name)
    return names, shell_only


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("busybox_archive", type=Path, help="busybox-1.38.0.tar.bz2 from busybox.net/downloads")
    parser.add_argument("toybox_archive", type=Path, help="toybox-0.8.15.tar.gz from landley.net/toybox/downloads")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).resolve().parents[1] / "tests/data/applets")
    args = parser.parse_args()
    try:
        busybox, _ = read_catalog(args.busybox_archive,
                               "34f9ea6ff8636f2c9241153b9114eefa9e65674a45318ae1ef95bb5f31c53bb2",
                               re.compile(r"busybox-1\.38\.0/(?:[^/]+/){1,2}[^/]+\.c"), BUSYBOX_DECL)
        toybox, shell_only = read_catalog(args.toybox_archive,
                              "44e2bab43dfe2c171743297631ce558c6d9ed38b87a66fd751cef617574b375e",
                              re.compile(r"toybox-0\.8\.15/toys/[^/]+/[^/]+\.c"), TOYBOX_DECL, b"TOYFLAG_NOFORK")
        # BusyBox conditionally registers its own driver; Toybox prepends its
        # driver outside toys/. Neither executable name is an applet target.
        busybox.remove("busybox")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for filename, names in (("busybox-1.38.0.txt", busybox), ("toybox-0.8.15.txt", toybox),
                                ("toybox-0.8.15-shell.txt", shell_only)):
            output = args.output_dir / filename
            output.write_bytes("".join(name + "\n" for name in sorted(names)).encode("ascii"))
            print(f"{output}: {len(names)} applets")
    except (OSError, ValueError, tarfile.TarError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
