"""Exercise session ownership on a real Linux pseudoterminal."""
import os
import pty
import subprocess
import sys

binary = os.path.abspath(sys.argv[1])
probe = """
import os
with open('/dev/tty', 'rb', buffering=0) as tty:
    assert os.tcgetpgrp(tty.fileno()) == os.getpgrp()
print(os.getpid(), os.getsid(0), os.getpgrp())
"""


def session(options, group_leader=False):
    master, slave = pty.openpty()
    try:
        with subprocess.Popen(
            [binary, "setsid", *options, sys.executable, "-c", probe],
            stdin=slave, stdout=subprocess.PIPE, text=True,
            preexec_fn=os.setpgrp if group_leader else None,
        ) as process:
            output, _ = process.communicate(timeout=5)
            assert process.returncode == 0, process.returncode
            pid, sid, pgid = map(int, output.split())
            assert pid == sid == pgid, (pid, sid, pgid)
            return process.pid, pid
    finally:
        os.close(slave)
        os.close(master)


launcher, child = session(["--ctty"])
assert launcher == child, "a nonleader must exec the command in place"
launcher, child = session(["--ctty", "--wait"], group_leader=True)
assert launcher != child, "a group leader must fork before setsid"
launcher, child = session(["-cfw"])
assert launcher != child, "--fork must create a child even for a nonleader"
print("setsid controlling terminal and process identity: pass")
