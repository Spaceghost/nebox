"""Check TTY discovery and the two kernel-generated random identifier formats."""
import fcntl
import os
from pathlib import Path
import pty
import re
import struct
import subprocess
import sys
import termios

binary = Path(sys.argv[1]).resolve()
links = Path(sys.argv[2]).resolve()
for mode in ('multicall','link'):
    def command(name, *args):
        return [binary, name, *args] if mode == 'multicall' else [links / name, *args]

    for args, output in [((), '80 24\n'), (('h','w','h'), '24 80 24\n')]:
        result = subprocess.run(command('ttysize', *args), stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True)
        assert result.stdout == output, result
    master, slave = pty.openpty()
    try:
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 37, 119, 0, 0))
        assert subprocess.check_output(command('ttysize'), stdin=slave, text=True) == '119 37\n'
    finally:
        os.close(master)
        os.close(slave)

    for applet, option, pattern in [
        ('uuidgen','--random',r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\n'),
        ('mcookie','--verbose',r'[0-9a-f]{32}\n'),
    ]:
        result = subprocess.run(command(applet, option), capture_output=True, text=True, check=True)
        assert re.fullmatch(pattern, result.stdout), applet
        if applet == 'mcookie':
            assert 'getrandom' in result.stderr
        second = subprocess.check_output(command(applet), text=True)
        assert re.fullmatch(pattern, second) and result.stdout != second, applet
    assert subprocess.check_output(command('mcookie','-V'), text=True) == 'mcookie from nebox\n'
    for argv in [('uuidgen','--bad'),('uuidgen','extra'),('mcookie','--bad')]:
        assert subprocess.run(command(*argv), capture_output=True).returncode != 0
