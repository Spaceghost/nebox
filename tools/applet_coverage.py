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


def report(busybox, toybox, nebox):
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
        "Registered names come from the selected Nebox binary’s `--list` output. "
        "The checked-in report uses the standalone build. Individual applet tests "
        "cover flags, output and exit status.",
        "",
        "| Upstream catalog | Registered | Missing | Total |",
        "|---|---:|---:|---:|",
    ]
    for title, group in [*groups, ("Union", union)]:
        lines.append(f"| {title} | {len(nebox & group)} | {len(group - nebox)} | {len(group)} |")

    for heading in ("Missing", "Registered"):
        lines.extend(["", f"## {heading} applets"])
        for title, group in groups:
            subset = group - nebox if heading == "Missing" else group & nebox
            formatted = ", ".join(f"`{name}`" for name in sorted(subset)) or "None"
            lines.extend(["", f"### {title}", "", formatted])

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
    result = subprocess.run([args.binary.resolve(), "--list"], check=True, capture_output=True, text=True)
    current = names(result.stdout.splitlines(), args.binary)
    if args.require_complete:
        missing = (busy | toy) - current
        if missing:
            print(f"{len(missing)} upstream applet names missing: {' '.join(sorted(missing))}", file=sys.stderr)
        return int(bool(missing))

    markdown = report(busy, toy, current)
    if args.check_report:
        if REPORT.read_text() != markdown:
            print("Applet coverage changed. Inspect the diff after running make update-applet-coverage.", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(markdown)
    return 0


if __name__ == "__main__":
    sys.exit(main())
