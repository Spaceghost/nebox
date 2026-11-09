#!/usr/bin/env python3
"""Side-by-side test of nebox sync against GNU coreutils 9.1 sync.
Usage: tests/sync_compare.py path/to/nebox
No operands, files, directories, a FIFO (opened non-blocking), a socket,
write-only and unreadable files, missing paths and ENOTDIR, character
devices (/dev/null fails fsync with EINVAL), /proc files, -d/--data,
-f/--file-system, their conflict and the operand-less --data error,
option errors, --help and output to /dev/full. Run as root it adds files
root reads despite their modes. stdout, stderr and exit status must
match; --version differs by design (nebox's line), only its status is
compared; --help omits GNU's closing links. What sync writes to disk is not observable here and is not
compared."""
import os, shutil, socket, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='sync-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
ROOT = os.geteuid() == 0
open(os.path.join(d, 'f'), 'w').write('data\n')
open(os.path.join(d, 'wo'), 'w').write('data\n')
os.chmod(os.path.join(d, 'wo'), 0o200)
open(os.path.join(d, 'none'), 'w').write('data\n')
os.chmod(os.path.join(d, 'none'), 0)
os.mkdir(os.path.join(d, 'dir'))
os.mkfifo(os.path.join(d, 'fifo'))
s = socket.socket(socket.AF_UNIX)
s.bind(os.path.join(d, 'sock'))
os.symlink('f', os.path.join(d, 'link'))
os.symlink('nowhere', os.path.join(d, 'dangling'))
os.mkdir(os.path.join(d, 'nodir'))
os.chmod(os.path.join(d, 'nodir'), 0)

CASES = []
for opts in ['', '-d', '-f', '--data', '--file-system', '--d', '--f', '--fi']:
    for ops in ['f', 'f dir', 'dir', 'fifo', 'sock', 'wo', 'none', 'nosuch', 'f/x', 'link', 'dangling', 'f nosuch dir',
                '/dev/null', '/dev/zero', 'f /dev/null f', '/proc/self/status', '/proc', 'nodir/x', "''", '-- -f']:
        CASES.append('@ %s %s' % (opts, ops))
CASES += ['@', '@ -d', '@ --data', '@ -f', '@ -df f', '@ -d -f', '@ -fd', '@ --data --file-system f', '@ -df',
          '@ -x', '@ --bogus', '@ -x f', '@ --help', '@ --help f', '@ --he', '@ --version', '@ --help=x', '@ -- --help',
          '@ --help > /dev/full; echo $?', '@ f > /dev/full; echo $?', '@ nosuch > /dev/full; echo $?', '@ --data=1 f']
NOVERSION = {'@ --version'}


def run(c, which):
    prog = 'sync' if which == 'gnu' else NEBOX + ' sync'
    p = subprocess.run(['bash', '-c', c.replace('@', prog)], cwd=d, env=env, capture_output=True, timeout=60,
                       stdin=subprocess.DEVNULL)
    out = p.stdout
    if which == 'gnu' and b'\nGNU coreutils online help' in out:
        # --help without GNU's closing links, by design
        out = out[:out.index(b'\nGNU coreutils online help')]
    return p.returncode, out, p.stderr


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if c in NOVERSION:
        g, n = (g[0], b'', g[2]), (n[0], b'', n[2])
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('sync_compare: %d cases%s, %d mismatches' % (len(CASES), ' (as root)' if ROOT else '', bad))
s.close()
os.chmod(os.path.join(d, 'nodir'), 0o700)
shutil.rmtree(d)
sys.exit(1 if bad else 0)
