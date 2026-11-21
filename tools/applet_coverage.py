#!/usr/bin/env python3
"""Compare a built Nebox with both pinned upstream applet catalogs."""
import argparse
from collections import Counter
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = ROOT / "tests" / "data" / "applets"
REPORT = ROOT / "docs" / "APPLET-COVERAGE.md"


def names(lines, source):
    if not lines or any(not name or any(ch.isspace() for ch in name) for name in lines):
        raise ValueError(f"{source}: expected one applet per line")
    duplicates = [name for name, count in Counter(lines).items() if count > 1]
    if duplicates:
        raise ValueError(f"{source}: duplicate applets: {', '.join(duplicates)}")
    return set(lines)


def shell_commands(binary, candidates):
    # An unusable PATH makes command -v report only commands the shell handles.
    result = subprocess.run(
        [binary, "sh", "-c", 'for name do command -v "$name" || :; done', "sh", *sorted(candidates)],
        check=True, capture_output=True, text=True, env={"PATH": "/dev/null", "LC_ALL": "C"},
    )
    found = set(result.stdout.splitlines())
    if not found <= candidates:
        raise ValueError(f"{binary}: unexpected shell lookup results: {sorted(found - candidates)}")
    return found


def report(busybox, toybox, shell_only, nebox, builtins, missing):
    union = busybox | toybox
    groups = [
        ("Both projects", busybox & toybox),
        ("BusyBox only", busybox - toybox),
        ("Toybox only", toybox - busybox),
    ]
    lines = [
        "# Applet coverage",
        "",
        "The target includes every applet declared by BusyBox 1.38.0 or Toybox 0.8.15, "
        "including aliases and optional commands. The two multiplexer names are excluded.",
        "",
        "The standalone Nebox binary reports executable applets through `--list`. "
        "Toybox also declares shell-only commands. Nebox checks these using `command -v` "
        "inside its own shell with an unusable PATH. A name is covered when every dispatch "
        "form declared upstream is present. Individual tests exercise behavior and options.",
        "",
        "| Upstream catalog | Covered | Missing | Total |",
        "|---|---:|---:|---:|",
    ]
    for title, group in [*groups, ("Union", union)]:
        lines.append(f"| {title} | {len(group - missing)} | {len(group & missing)} | {len(group)} |")

    lines.extend([
        "",
        "## Applet names",
        "",
        "A dash in a Nebox column means neither upstream requires that form.",
        "",
        "| Applet | BusyBox | Toybox | Nebox executable | Nebox shell |",
        "|---|:---:|:---:|---|---|",
    ])
    for name in sorted(union):
        busy = "yes" if name in busybox else ""
        toy = "yes" if name in toybox else ""
        executable = "Registered" if name in nebox else "Missing"
        shell = "—"
        if name in shell_only:
            toy = "shell"
            shell = "Builtin" if name in builtins else "Missing"
            if name not in busybox:
                executable = "—"
        lines.append(f"| `{name}` | {busy} | {toy} | {executable} | {shell} |")

    extras = ", ".join(f"`{name}`" for name in sorted(nebox - union)) or "None"
    lines.extend(["", "## Additional Nebox names", "", extras, ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="path to the built Nebox executable")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-report", action="store_true", help="compare against the checked-in standalone report")
    mode.add_argument("--require-complete", action="store_true", help="fail if any upstream applet is missing")
    args = parser.parse_args()
    busy = names((CATALOGS / "busybox-1.38.0.txt").read_text().splitlines(), "BusyBox")
    toy = names((CATALOGS / "toybox-0.8.15.txt").read_text().splitlines(), "Toybox")
    shell_only = names((CATALOGS / "toybox-0.8.15-shell.txt").read_text().splitlines(), "Toybox shell")
    if not shell_only <= toy:
        raise ValueError("Toybox shell commands must occur in the Toybox catalog")
    binary = args.binary.resolve()
    result = subprocess.run([binary, "--list"], check=True, capture_output=True, text=True)
    current = names(result.stdout.splitlines(), binary)
    builtins = shell_commands(binary, shell_only) if "sh" in current else set()
    missing_exec = (busy | (toy - shell_only)) - current
    missing_shell = shell_only - builtins
    missing = missing_exec | missing_shell
    if args.require_complete:
        if missing:
            print(f"{len(missing)} upstream names missing required dispatch", file=sys.stderr)
        if missing_exec:
            print(f"Missing executables ({len(missing_exec)}): {' '.join(sorted(missing_exec))}", file=sys.stderr)
        if missing_shell:
            print(f"Missing shell commands ({len(missing_shell)}): {' '.join(sorted(missing_shell))}", file=sys.stderr)
        return int(bool(missing))

    markdown = report(busy, toy, shell_only, current, builtins, missing)
    if args.check_report:
        if REPORT.read_text() != markdown:
            print("Applet coverage changed. Inspect the diff after running make update-applet-coverage.", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
