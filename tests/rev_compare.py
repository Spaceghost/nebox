#!/usr/bin/env python3
"""Side-by-side test of nebox rev against util-linux 2.38.1 rev.
Usage: tests/rev_compare.py path/to/nebox [random-cases]
Fixtures on /dev/shm: plain lines, missing final newline, empty lines and
files, NUL bytes at the start, middle and end of lines, bytes above 127
(EILSEQ in the C locale) on the first, middle and last line, lines around
the 8192-character buffer and its doublings (with NULs and bad bytes past
the first buffer), several files with unreadable and missing ones, a
directory, standard input, every option and option error, output to
/dev/full below and above the stdio buffer, and SIGTERM; then random
inputs over a small alphabet with NUL, newline and high bytes. stdout,
stderr and exit status must match. --version output differs by design
(nebox's line); only its status is compared."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 400
d = tempfile.mkdtemp(prefix='rev-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
rnd = random.Random(11)
F = {
    'a': b'hello world\nsecond line\n\nlast\n',
    'nonl': b'abc\ndef',
    'empty': b'',
    'blank': b'\n\n\n',
    'nul1': b'ab\0cd\nef\n',
    'nul2': b'ab\0cd\n',
    'nul3': b'\0abc\nxyz\n',
    'nul4': b'ab\0cd',
    'nul5': b'x\0\0y\n\0\n\0\0\nlast\0\n',
    'hi1': b'a\xffb\nxy\n',
    'hi2': b'ab\nc\xffd\nxy\n',
    'hi3': b'ab\ncd\nx\x80',
    'hi4': b'\xc3\xa9t\xc3\xa9\n',
    'crlf': b'one\r\ntwo\r\n',
    'tabs': b'a\tb\tc\n \t \n',
    'ctl': bytes(range(1, 128)) + b'\n',
}
for n in (8190, 8191, 8192, 8193, 16382, 16383, 16384, 16385, 32768, 50000):
    F['long%d' % n] = b'x' * (n - 1) + b'y\nshort\n'
    F['longnonl%d' % n] = b'z' * n
F['longnul'] = b'q' * 9000 + b'\0' + b'w' * 9000 + b'\nnext\n'
F['longnul2'] = b'q' * 100 + b'\0' + b'w' * 20000 + b'\nnext\nmore\n'
F['longhi'] = b'r' * 9000 + b'\xfe' + b's' * 10 + b'\nnext\n'
F['longhi2'] = b'r' * 8191 + b'\xfe\nnext\n'
F['longhi3'] = b'r' * 8190 + b'\xfe\nnext\n'
F['manylines'] = b''.join(b'line %d\n' % i for i in range(3000))
F['bigout'] = b'0123456789\n' * 500
for k, v in F.items():
    open(os.path.join(d, k), 'wb').write(v)
os.mkdir(os.path.join(d, 'dir'))
open(os.path.join(d, 'noread'), 'wb').write(b'secret\n')
os.chmod(os.path.join(d, 'noread'), 0)

CASES = ['@ %s' % k for k in F]
CASES += [
    '@ a nonl', '@ a nosuch nonl', '@ nosuch', '@ hi1 a', '@ a hi2 nonl', '@ nul1 nul2 nul4 a', '@ dir', '@ dir a',
    '@ noread a', '@ -', '@ - a < a', '@ < a', 'cat a | @', 'cat hi2 | @', 'cat nul5 | @', 'cat long16385 | @',
    '@ < /dev/null', '@ long8193 long16385 nul1 longnul', '@ longhi longhi2 a', '@ longnul2 longnul', '@ empty empty',
    '@ -V', '@ --version', '@ -h', '@ --help', '@ --he', '@ --h a', '@ --v', '@ -x', '@ --zero', '@ -0 a', '@ -hV',
    '@ -Vh', '@ -- -h', '@ a -- nonl', '@ --bogus a', '@ --help=x', '@ -h a nosuch', '@ a -h',
    '@ a > /dev/full; echo $?', '@ bigout > /dev/full; echo $?', '@ manylines > /dev/full; echo $?',
    '@ -h > /dev/full; echo $?', '@ nosuch > /dev/full; echo $?', '@ a >&-; echo $?',
    '@ manylines | head -2', '@ a 2>&1 nosuch hi1 nonl',
    'sleep 2 | timeout --preserve-status -s TERM 0.3 @; echo $?',
    'sleep 2 | timeout --preserve-status -s INT 0.3 @; echo $?',
    '(printf "abc\\n"; sleep 2) | timeout --preserve-status -s TERM 0.3 @; echo $?',
]
NOVERSION = {'@ -V', '@ --version', '@ --v', '@ -Vh'}

for k in range(NRAND):
    parts = []
    for _ in range(rnd.randint(1, 3)):
        n = rnd.choice([0, 1, 3, 10, 40, 200, 8191, 8192, 9000])
        alpha = rnd.choice([b'ab\n', b'abc \t\n', b'ab\n\0', b'ab\n\0\xff', b'a\n\n\n\0', b'xyz\n\x80'])
        weights = [1.0] * len(alpha)
        if b'\xff'[0] in alpha:
            weights[alpha.index(b'\xff'[0])] = 0.02
        if 0x80 in alpha:
            weights[alpha.index(0x80)] = 0.02
        data = bytes(rnd.choices(alpha, weights, k=n))
        name = 'r%d_%d' % (k, len(parts))
        open(os.path.join(d, name), 'wb').write(data)
        parts.append(name)
    if rnd.random() < 0.2:
        CASES.append('cat %s | @' % parts[0])
    else:
        CASES.append('@ ' + ' '.join(parts))


def run(c, which):
    prog = 'rev' if which == 'gnu' else NEBOX + ' rev'
    cmd = c.replace('@', prog)
    p = subprocess.run(['bash', '-c', 'ulimit -v 3000000; ' + cmd], cwd=d, env=env, capture_output=True,
                       timeout=60, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


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
print('rev_compare: %d cases, %d mismatches' % (len(CASES), bad))
os.chmod(os.path.join(d, 'noread'), 0o600)
shutil.rmtree(d)
sys.exit(1 if bad else 0)
