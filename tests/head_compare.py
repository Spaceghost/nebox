#!/usr/bin/env python3
"""Side-by-side test of nebox head against GNU head.
Usage: tests/head_compare.py path/to/nebox [random-cases] [seed]
Random line and byte counts (with GNU suffixes and "-N" elision) over files
small and large, pipes, NUL-terminated data and files without a final
newline; "{ head ...; cat; } < file" checks the file offset head leaves.
Output, diagnostics (minus "Try --help") and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='head-compare-')
frng = random.Random(9)


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


def lines(n, eol=b'\n', final=True, width=30):
    out = eol.join(b'line %d %s' % (i, b'x' * frng.randrange(width)) for i in range(n))
    return out + (eol if final and n else b'')


w('small', lines(15))
w('nonl', lines(15, final=False))
w('big', lines(5000, width=80))
w('bignonl', lines(5000, final=False, width=80))
w('z', lines(20, eol=b'\0'))
w('empty', b'')
w('one', b'x')
w('blank', b'\n\n\n')
os.mkdir(os.path.join(d, 'adir'))
FILES = ['small', 'nonl', 'big', 'bignonl', 'z', 'empty', 'one', 'blank']

FIXED = ['@head small', '@head -n 3 small', '@head -3 small', '@head -c 10 small', '@head -c 1k big | wc -c', '@head -c 1kB big | wc -c',
         '@head -c 2b big | wc -c', '@head -n -3 small', '@head -c -5 small', '@head -n 0 small', '@head -n -0 small',
         '@head small nonl', '@head -q small nonl', '@head -v small', '@head -n 2 small nofile nonl', '@head adir',
         '@head -n 2 -z z | od -c | head -3', '@head -5c small', '@head -2l small', '@head -2q small nonl', '@head -2v small',
         '@head -2z z | od -c | tail -2', '@head -2x small', '@head -n x small', '@head -n 1Q small', '@head -n 99999999999999999999999 small',
         '@head -c -99999999999999999999 small', '@head small -5', '@head -n 1 -- -n', '@head --lines=2 small', '@head --bytes=3 small',
         '@head --lin=2 small', '@head --zero-terminated -n1 z | od -c', '@head ---presume-input-pipe -n -2 small',
         '@head -n K small | wc -l', '@head -c 1M big | wc -c', '@head -n +3 small', '@head -c +3 small',
         '{ @head -n 2; cat; } < small', '{ @head -c 7; cat; } < small', '{ @head -n -2; echo ---; cat; } < small',
         '{ @head -n -2; echo ---; cat; } < big | tail -5', '{ @head -c -100; echo ---; cat; } < big | tail -3',
         '{ @head -n -3; echo ---; cat; } < bignonl | tail -5', 'cat big | @head -n -4990', 'cat bignonl | @head -n -2 | tail -2',
         'cat big | @head -c -70000 | tail -c 50', '@head -n -1 nonl', '@head -n -1 one', '@head -n -2 blank | od -c']


def rand_case():
    f = rng.choice(FILES)
    r = rng.random()
    neg = rng.random() < 0.4
    unit = rng.choice(['n', 'n', 'c'])
    num = rng.choice(['0', '1', '2', '3', '5', '10', '14', '15', '16', '100', '4999', '5000', '5001', '8191', '8192', '8193',
                      '70000', '1k', '2b'])
    opt = '-%s %s%s' % (unit, '-' if neg else '', num)
    if rng.random() < 0.1:
        opt += ' -z'
    form = rng.random()
    if form < 0.5:
        cmd = '@head %s %s' % (opt, f)
    elif form < 0.75:
        cmd = 'cat %s | @head %s' % (f, opt)
    else:
        cmd = '{ @head %s; echo ---; cat; } < %s' % (opt, f)
    return cmd + ' | md5sum'


def run(cmd, which):
    c = cmd.replace('@head', NEBOX + ' head') if which == 'nebox' else cmd.replace('@', '')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
print('head_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
