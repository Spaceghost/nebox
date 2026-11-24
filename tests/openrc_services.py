"""Exercise real Unix sockets, terminals, and per-account cron jobs as root."""

import os
import pty
from pathlib import Path
import pwd
import select
import shlex
import socket
import stat
import subprocess
import sys
import tempfile
import time


def wait_for(predicate, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError(f"timed out after {timeout} seconds")


def check_syslog(binary, work):
    endpoint = work / "log.sock"
    messages = work / "messages"
    args = [binary, "syslogd", "-nt", "-p", str(endpoint), "-O", str(messages), "-s", "1"]
    with subprocess.Popen(args) as server:
        try:
            wait_for(endpoint.is_socket)
            assert stat.S_IMODE(endpoint.stat().st_mode) == 0o666
            assert subprocess.run(args, timeout=5, capture_output=True).returncode == 1
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                client.sendto(b"<14>Jan  1 12:34:56 nebox: one\nline\x1b\x00", str(endpoint))
            wait_for(lambda: b"nebox: one line^[\n" in messages.read_bytes())
            assert b"12:34:56" not in messages.read_bytes()
            with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
                client.sendto(b"x" * 1100, str(endpoint))
                wait_for(lambda: messages.stat().st_size > 1024)
                client.sendto(b"rotated", str(endpoint))
            wait_for(lambda: messages.exists() and b"rotated" in messages.read_bytes())
            assert b"nebox: one line^[\n" in (work / "messages.0").read_bytes()
        finally:
            server.terminate()
            assert server.wait(timeout=5) == 0
    assert not endpoint.exists()
    endpoint.write_text("keep this file")
    assert subprocess.run(args, timeout=5, capture_output=True).returncode == 1
    assert endpoint.read_text() == "keep this file"


def check_getty(binary, work):
    login = work / "login"
    login.write_text(
        '#!/bin/sh\n'
        'test -t 0 && test -t 1 && test -t 2 && test -r /dev/tty || exit 4\n'
        'printf "login argv [%s] [%s], TERM=%s\\n" "$1" "$2" "$TERM"\n'
    )
    login.chmod(0o755)
    master, slave = pty.openpty()
    output = bytearray()

    def read_until(expect):
        end = time.monotonic() + 5
        while expect not in output and time.monotonic() < end:
            ready, _, _ = select.select([master], [], [], 0.05)
            if ready:
                output.extend(os.read(master, 4096))
        assert expect in output, output

    try:
        with subprocess.Popen(
            [binary, "getty", "-i", "-l", str(login), "38400", os.ttyname(slave), "vt100"],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        ) as process:
            try:
                read_until(b"login: ")
                os.write(master, b"-froot\n")
                read_until(b"Invalid login name")
                os.write(master, b"console-user\n")
                read_until(b"login argv [--] [console-user], TERM=vt100")
                assert process.wait(timeout=5) == 0
            finally:
                if process.poll() is None:
                    process.kill()
    finally:
        os.close(slave)
        os.close(master)


def check_cron(binary, work):
    spool = work / "crontabs"
    spool.mkdir()
    root_job = work / "root-job"
    invalid_job = work / "invalid"
    user = pwd.getpwnam("nobody")
    user_job = work / "user-job"
    user_job.touch()
    os.chown(user_job, user.pw_uid, user.pw_gid)
    root_table = spool / "root"
    root_table.write_text(
        f"*/1 0-23 1-31 1-12 0-7 echo \"$LOGNAME\" > {shlex.quote(str(root_job))}\n"
        f"60 * * * * touch {shlex.quote(str(invalid_job))}\n"
    )
    (spool / user.pw_name).write_text(f"* * * * * id -u > {shlex.quote(str(user_job))}\n")
    work.chmod(0o755)
    with subprocess.Popen([binary, "crond", "-f", "-c", str(spool)]) as daemon:
        try:
            wait_for(lambda: root_job.exists() and user_job.stat().st_size > 0, 70)
            assert root_job.read_text() == "root\n"
            assert user_job.read_text() == f"{user.pw_uid}\n"
            assert not invalid_job.exists()
        finally:
            daemon.terminate()
            daemon.wait(timeout=5)
    spool.chmod(0o777)
    result = subprocess.run([binary, "crond", "-f", "-c", str(spool)], timeout=5, capture_output=True)
    assert result.returncode == 1


def main():
    if os.geteuid() != 0:
        raise SystemExit("run in a disposable Linux container as root")
    binary = str(Path(sys.argv[1]).resolve())
    with tempfile.TemporaryDirectory(prefix="nebox-openrc-") as directory:
        work = Path(directory)
        check_syslog(binary, work)
        print("syslogd local socket and shutdown passed", flush=True)
        check_getty(binary, work)
        print("getty console handoff and argument validation passed", flush=True)
        check_cron(binary, work)
        print("crond schedule and credential checks passed", flush=True)


if __name__ == "__main__":
    main()
