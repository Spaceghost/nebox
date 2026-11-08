#!/usr/bin/env python3
"""Side-by-side test of nebox tsort against GNU coreutils tsort.
Usage: tests/tsort_compare.py path/to/nebox [random-cases]
Fixed cases plus random graphs (DAGs, self-pairs, several cycles, mixed
blanks); stdout, diagnostics (the loop listings) and exit status must
match."""
import os, random, subprocess, sys, tempfile, shutil

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 400
d = tempfile.mkdtemp(prefix='tsort-compare-')
env = dict(os.environ, LC_ALL='C')
files = {'t': 'a b\nb c\n', 'odd': 'a b c\n', 'cyc': 'a b\nb a\n', 'self': 'a a\nb b\n', 'e': '', 'tabs': 'a\tb  c\n\nd\te\n',
         'cyc3': 'a b b c c a c d\n', 'two': 'a b b a c d d c\n'}
for n, v in files.items():
    open(os.path.join(d, n), 'w').write(v)
CASES = ['@tsort %s' % n for n in files] + ['@tsort < t', '@tsort - < cyc', '@tsort nonexistent', '@tsort t odd', '@tsort -x',
         '@tsort --bogus', '@tsort -w t', '@tsort -- t', '@tsort t > /dev/full; echo $?', 'printf "a b" | @tsort', '@tsort dir']
os.mkdir(os.path.join(d, 'dir'))
rnd = random.Random(5)
for k in range(NRAND):
    names = ['n%d' % i for i in range(rnd.randint(1, 12))] + rnd.choice([[], ['zz', 'a', 'B', '_x']])
    pairs = []
    for _ in range(rnd.randint(0, 25)):
        a, b = rnd.choice(names), rnd.choice(names)
        if rnd.random() < 0.7 and names.index(a) > names.index(b):
            a, b = b, a
        pairs.append((a, b))
    seps = [' ', '\t', '\n', '  ']
    data = ''.join(a + rnd.choice(seps) + b + rnd.choice(seps) for a, b in pairs)
    name = 'r%d' % k
    open(os.path.join(d, name), 'w').write(data)
    CASES.append('@tsort %s' % name)


def run(cmd, which):
    c = cmd.replace('@tsort', (NEBOX + ' tsort') if which == 'nebox' else 'tsort')
    p = subprocess.run(['bash', '-c', c], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 20:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('tsort_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
