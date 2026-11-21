"""Verify process directory lookup, PID spelling, and per-process failures."""
from pathlib import Path
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
link = Path(sys.argv[2]).absolute()
assert link.is_symlink()
with tempfile.TemporaryDirectory() as tmp:
    cwd = Path(tmp).resolve() / ("x" * 130) / "directory with spaces"
    cwd.mkdir(parents=True)
    # exec keeps the shell's PID. Reading our own cwd works on restricted procfs.
    for command in ([binary, "pwdx"], [link]):
        result = subprocess.run(
            ["sh", "-c", 'exec "$@" -- "$$" "00$$" "/proc/$$"', "sh", *command],
            cwd=cwd, text=True, capture_output=True)
        assert result.returncode == 0, (command, result)
        first = result.stdout.split(":", 1)[0]
        assert first.isdecimal() and result.stdout == "".join(
            f"{pid}: {cwd}\n" for pid in (first, "00"+first, "/proc/"+first)), result

    result = subprocess.run(["sh", "-c", 'exec "$1" pwdx 0 "$$"', "sh", binary],
                            cwd=cwd, text=True, capture_output=True)
    lines = result.stdout.splitlines()
    assert result.returncode == 1 and len(lines) == 2, result
    assert lines[0] == "0: No such process" and lines[1].endswith(f": {cwd}"), result

for invalid in ["", "/proc/self", "/proc/1/cwd", "7x", "+1", " 2", "4294967296"]:
    result = subprocess.run([binary, "pwdx", invalid], capture_output=True, text=True)
    assert result.returncode != 0 and "invalid process id" in result.stderr, (invalid, result)
result = subprocess.run([binary, "pwdx"], capture_output=True, text=True)
assert result.returncode != 0 and "usage:" in result.stderr, result
