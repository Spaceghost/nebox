#!/usr/bin/env python3
"""Side-by-side test of nebox cmp against GNU diffutils cmp.
Usage: tests/cmp_compare.py path/to/nebox [random-cases]
Fixtures on /dev/shm: equal files, first differences at line and chunk
boundaries, prefixes (every EOF message form), empty files, control and
high bytes, files over 64 KiB; every option (-b -c -i SKIP and SKIP1:SKIP2
with suffixes and bases, -l, -n, -s, SKIP operands), standard input from
pipes and files, the same file, directories, missing files, output to
/dev/null and /dev/full, and option errors; then random pairs with random
options. stdout, stderr and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 400
d = tempfile.mkdtemp(prefix='cmp-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
GNU = '/usr/bin/cmp'
rnd = random.Random(7)
F = {
    'a': b'line one\nline two\nline three\n',
    'b': b'line one\nline Two\nline three\n',
    'pre': b'line one\nline',
    'pre2': b'line one\n',
    'e': b'',
    'bin1': bytes(range(256)),
    'bin2': bytes(range(255, -1, -1)),
    'big1': bytes(rnd.getrandbits(8) for _ in range(200000)),
}
big2 = bytearray(F['big1']); big2[65536] ^= 1; big2[131071] ^= 0x80; big2[150000] = 10
F['big2'] = bytes(big2)
F['big3'] = F['big1'][:65536]
F['nl'] = b'\n\n\n\nx'
F['nl2'] = b'\n\n\n\ny'
for k, v in F.items():
    open(os.path.join(d, k), 'wb').write(v)
os.mkdir(os.path.join(d, 'dir'))
os.symlink('a', os.path.join(d, 'alink'))
os.link(os.path.join(d, 'a'), os.path.join(d, 'ahard'))
CASES = [
    'a a', 'a b', 'a ahard', 'a alink', 'a pre', 'pre a', 'a pre2', 'pre2 a', 'e a', 'a e', 'e e', 'bin1 bin2', 'nl nl2',
    'big1 big2', 'big1 big3', 'big3 big1', '-l big1 big2', '-b big1 big2', '-lb big1 big2', '-l a b', '-b a b', '-c a b',
    '-l bin1 bin2', '-lb bin1 bin2', '-l a pre', '-l pre a', '-b a pre', '-l e a', '-s a b', '-s a a', '-s a pre', '-s e a',
    '-n 5 a b', '-n 20 a b', '-n 0 a b', '-n 1k a b', '-n 1kB a b', '-n 0x10 a b', '-n 010 a b', '-n -1 a b', '-n x a b',
    '-n 99999999999999999999 a b', '--bytes=12 a b', '-n 5 -n 20 a b', '-n 20 -n 5 a b', '-l -n 15 a b', '-l -n 15 a pre',
    '-i 5 a b', '-i 5:3 a b', '-i 3:5 a b', '-i 10 a pre', '-i 1k a b', '-i 0x2 a b', '-i 5: a b', '-i :5 a b', '-i x a b',
    '-i 5:x a b', '-i -1 a b', '-i 1:2:3 a b', '-i 2 -i 4 a b', '--ignore-initial=9 a b', '-i 9 -l a b',
    'a b 5', 'a b 5 3', 'a b 3 5', 'a b x', 'a b 1 2 3', 'a b 1k', '-i 4 a b 2', 'a a 1 2', 'a a 2 2',
    'a', '', 'nonexistent a', 'a nonexistent', '-s nonexistent a', '-s a nonexistent', 'dir a', 'a dir', '-s dir a',
    '-l -s a b', '-s -l a b', '-l -l a b', '-x a b', '--bogus a b', '--verb a b', '--print-bytes a b', '--print-chars a b',
    '--quiet a b', '--silent a b', '- a < b', 'a - < b', 'a < b', '- - < a', 'a - < a', '-l a - < b',
    'cat b | @ a', 'cat b | @ - a', 'cat a | @ -i 5 - b', 'cat big2 | @ -l big1', 'cat a | @ -s a', 'cat pre | @ a',
    'a b > /dev/null; echo $?', '-l a b > /dev/null; echo $?', 'a pre > /dev/null', '-l big1 big2 > /dev/full; echo $?',
    'a b > /dev/full; echo $?', '-s a b > /dev/full; echo $?', 'a a > /dev/full; echo $?', '-b big1 big2 > /dev/full',
]


def run(c, which):
    prog = GNU if which == 'gnu' else NEBOX + ' cmp'
    cmd = c.replace('@', prog) if '@' in c else prog + ' ' + c
    p = subprocess.run(['bash', '-c', cmd], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(GNU.encode(), b'cmp')
    return p.returncode, p.stdout, err


for k in range(NRAND):
    n = rnd.randint(0, 40)
    x = bytes(rnd.choice(b'ab\n\x00\x7f\xc3') for _ in range(n))
    y = bytearray(x)
    for _ in range(rnd.randint(0, 3)):
        if y and rnd.random() < 0.7:
            y[rnd.randrange(len(y))] = rnd.choice(b'ab\n\x00\x7f\xc3z')
    if rnd.random() < 0.3:
        y = y[:rnd.randint(0, len(y))] if rnd.random() < 0.5 else y + bytes(rnd.choice(b'ab\n') for _ in range(rnd.randint(1, 5)))
    open(os.path.join(d, 'r%dx' % k), 'wb').write(x)
    open(os.path.join(d, 'r%dy' % k), 'wb').write(bytes(y))
    opts = []
    for o in rnd.sample(['-l', '-b', '-s', '-n %d' % rnd.randint(0, 30), '-i %d' % rnd.randint(0, 5), '-i %d:%d' % (rnd.randint(0, 5), rnd.randint(0, 5))], rnd.randint(0, 3)):
        opts.append(o)
    ops = ['r%dx' % k, 'r%dy' % k]
    if rnd.random() < 0.15:
        ops += [str(rnd.randint(0, 4))]
    CASES.append(' '.join(opts + ops))

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
print('cmp_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
