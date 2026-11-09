#!/usr/bin/env python3
"""Side-by-side test of nebox which against debianutils 5.7 which (the
/bin/sh script, run by dash).
Usage: tests/which_compare.py path/to/nebox
A fixture tree on /dev/shm with executable, non-executable, directory,
symlinked and dangling entries; PATH edge cases (empty, unset, leading,
trailing, doubled and lone ':' elements, relative and trailing-slash
elements, duplicates), names with a slash, empty names, -a, "--", option
clusters and illegal options (dash's getopts message and status 2), no
operands, output to /dev/full and a non-empty KSH_VERSION. stdout, stderr
and exit status must match. The script reports itself by its path; that
path is replaced by "which" in GNU's output."""
import os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='which-compare-', dir='/dev/shm')
GNU = '/usr/bin/which'
os.makedirs(os.path.join(d, 'b1'))
os.makedirs(os.path.join(d, 'b2'))
os.makedirs(os.path.join(d, 'b3', 'sub'))
os.makedirs(os.path.join(d, 'b1', 'isdir'))


def mk(path, mode, data=b'#!/bin/sh\n'):
    p = os.path.join(d, path)
    open(p, 'wb').write(data)
    os.chmod(p, mode)


mk('b1/tool', 0o755)
mk('b2/tool', 0o755)
mk('b3/tool', 0o644)
mk('b2/only2', 0o700)
mk('b3/noexec', 0o644)
mk('b3/xonly', 0o711)
mk('b3/gx', 0o654)
mk('b1/-a', 0o755)
mk('b1/sp ace', 0o755)
mk('here', 0o755)
os.symlink('tool', os.path.join(d, 'b2', 'link'))
os.symlink('nowhere', os.path.join(d, 'b2', 'dangling'))
os.symlink('isdir', os.path.join(d, 'b1', 'dirlink'))
B1, B2, B3 = (os.path.join(d, x) for x in ('b1', 'b2', 'b3'))
P = '%s:%s:%s' % (B1, B2, B3)

CASES = []


def C(cmd, path=P, extra=None):
    CASES.append((cmd, path, extra or {}))


for a in ['tool', '-a tool', 'only2', 'noexec', 'xonly', 'gx', 'isdir', 'dirlink', 'link', 'dangling', 'nosuch',
          'tool only2 nosuch', '-a tool only2', 'tool nosuch', "''", "'' tool", '-a', '', '--', '-- -a', '-- tool',
          '-aa tool', '-a -a tool', '-a -- tool', '- tool', 'tool -a', '-s tool', '-b', '-ab tool', '-ax', '--help',
          '--version', '-', '-- --', "'sp ace'", "-a 'sp ace'", 'b1/tool', './b1/tool', '"$PWD/b1/tool"',
          'b3/tool', 'b1/isdir', 'b1/', '/', 'here', './here', 'b2/link', 'b2/dangling', 'sub', '-a nosuch tool',
          'tool tool', '-a link tool']:
    C('@ ' + a)
C('@ tool', '')
C('@ here', '')
C('@ here', ':')
C('@ here', '::')
C('@ -a here', ':' + B1 + ':')
C('@ -a tool', B1 + ':')
C('@ -a here', B1 + ':')
C('@ -a here', B1 + '::')
C('@ -a here', '::' + B1)
C('@ -a tool', B1 + ':' + B1)
C('@ -a tool', B1 + '/:' + B2 + '//')
C('@ -a tool', 'b1:b2')
C('@ -a tool', './b1::b2')
C('@ -a tool', '/nonexist:' + P)
C('@ tool', '/nonexist')
C('@ -a here tool', ':' + P + ':')
C('@ -a tool', P + ':')
C('@ -a sh', None)
C('@ -a sh ls', '/usr/bin:/bin')
C('@ tool > /dev/full; echo $?')
C('@ tool only2 > /dev/full; echo $?')
C('@ nosuch > /dev/full; echo $?')
C('@ -x > /dev/full; echo $?')
C('@ tool', P, {'KSH_VERSION': '1'})
C('@ nosuch', P, {'KSH_VERSION': '1'})
C('@ -q', P, {'KSH_VERSION': '1'})
C('@ tool', P, {'KSH_VERSION': ''})
C('cd b3 && @ tool', '.')
C('cd b3 && @ -a tool', ':.:' + B1)
C('@ tool >&-; echo $?')


def run(c, which):
    cmd, path, extra = c
    prog = GNU if which == 'gnu' else NEBOX + ' which'
    e = dict(os.environ, LC_ALL='C')
    e.pop('KSH_VERSION', None)
    e.update(extra)
    if path is None:
        e.pop('PATH', None)
    else:
        e['PATH'] = path
    # bash looks up nothing itself: the program and the shell helpers are absolute
    sh = cmd.replace('@', prog).replace('timeout', '/usr/bin/timeout')
    p = subprocess.run(['/bin/bash', '-c', sh], cwd=d, env=e, capture_output=True, timeout=60,
                       stdin=subprocess.DEVNULL)
    out = p.stdout.replace(GNU.encode(), b'which')
    err = p.stderr.replace(GNU.encode(), b'which')
    return p.returncode, out, err


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('which_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
