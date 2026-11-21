"""Verify the default Linux module table and deterministic procfs fixtures."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

binary = Path(sys.argv[1]).resolve()
header = f"{'Module':23} Size  Used by\n"
link = Path(sys.argv[2]).absolute()
assert link.is_symlink()
for command in ([binary, "lsmod"], [link]):
    result = subprocess.run(command, capture_output=True, text=True)
    if Path("/proc/modules").is_file():
        assert result.returncode == 0 and result.stdout.startswith(header), (command, result)
        for row in result.stdout.splitlines()[1:]:
            columns = row.split()
            assert len(columns) in (3, 4) and columns[1].isdigit(), row
            assert columns[2] == "-" or columns[2].lstrip("-").isdigit(), row
            if len(columns) == 4:
                assert columns[3] != "-" and not columns[3].endswith(","), row
    else:
        assert result.returncode != 0 and "/proc/modules" in result.stderr, (command, result)

if os.geteuid() == 0:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        shutil.copyfile(binary, root / "nebox")
        (root / "nebox").chmod(0o755)
        (root / "proc").mkdir()
        modules = root / "proc/modules"

        def run():
            return subprocess.run(["chroot", tmp, "/nebox", "lsmod"], capture_output=True, text=True)

        result = run()
        assert result.returncode != 0 and "/proc/modules" in result.stderr, result
        modules.touch()
        result = run()
        assert result.returncode == 0 and result.stdout == header, result
        modules.write_text("one 1024 0 - Live 0x0\nlong_module_name_0123456789 65536 7 alpha,beta, Live 0x0\n"
                           "permanent\t128 - - Live 0x0")
        expected = (header + f"{'one':19} {'1024':>8}  0 \n"
                    + f"{'long_module_name_0123456789':19} {'65536':>8}  7 alpha,beta\n"
                    + f"{'permanent':19} {'128':>8}  - \n")
        result = run()
        assert result.returncode == 0 and result.stdout == expected, result
        modules.write_text("one 1024\n")
        result = run()
        assert result.returncode != 0 and "/proc/modules" in result.stderr, result
