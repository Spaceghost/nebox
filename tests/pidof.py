"""Exercise PID lookup with private, long-lived processes under our own UID."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
installed = Path(sys.argv[2]).absolute()
assert installed.is_symlink()

def lookup(command, *args):
    result = subprocess.run([*command, *args], capture_output=True, text=True, timeout=10)
    assert result.returncode in (0, 1) and not result.stderr, (args, result)
    if result.returncode == 1:
        assert not result.stdout, (args, result)
        return []
    assert result.stdout.endswith("\n"), result
    return [int(word) for word in result.stdout.split()]

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    prefix = "nbp" + str(os.getpid())
    longname = prefix + "_long_process_name"
    programs = [root / prefix, root / longname, root / "separate" / prefix]
    programs[2].parent.mkdir()
    for program in programs:
        shutil.copy2(shutil.which("sleep"), program)
    # A symlink tests path matching by executable identity.
    alias = root / (prefix + "_alias")
    alias.symlink_to(programs[0])
    script = root / (prefix + "_script")
    script.write_text("read -r line\n")
    children = []
    try:
        for program in programs:
            children.append(subprocess.Popen([program, "60"]))
        children.append(subprocess.Popen(["sh", script], stdin=subprocess.PIPE))
        first, second, third, script_process = [p.pid for p in children]
        parent_name = Path(sys.executable).name
        for command in ([binary, "pidof"], [installed]):
            assert set(lookup(command, prefix)) == {first, third}
            assert lookup(command, longname) == [second]
            assert set(lookup(command, prefix, longname, prefix)) == {first, second, third}
            assert len(lookup(command, prefix, longname, prefix)) == 3
            single = lookup(command, "-s", prefix, longname)
            assert len(single) == 1 and single[0] in (first, second, third)
            assert lookup(command, "-o", f"{first},{third}", prefix, longname) == [second]
            assert lookup(command, "-o", str(first), "-o", str(third), prefix) == []
            assert lookup(command, str(alias)) == [first]
            assert lookup(command, str(programs[2])) == [third]
            assert lookup(command, prefix + "_absent") == []
            assert lookup(command) == []
            assert lookup(command, script.name) == []
            assert lookup(command, "-x", script.name) == [script_process]
            assert os.getpid() in lookup(command, parent_name)
            assert os.getpid() not in lookup(command, "-o", "%PPID", parent_name)
            for invalid in ("/proc/self", "12x", "1,", "", "4294967296"):
                result = subprocess.run([*command, "-o", invalid, prefix], capture_output=True, text=True)
                assert result.returncode != 0 and "invalid omit PID" in result.stderr, result
    finally:
        for child in children:
            child.terminate()
        for child in children:
            child.wait(timeout=5)
            if child.stdin:
                child.stdin.close()
