#!/usr/bin/env python3
"""Side-by-side test of nebox nl, comm and paste against GNU coreutils.
Usage: tests/nlcp_compare.py path/to/nebox [random-cases] [seed]
Random inputs (section delimiters, blank runs, unsorted lines, missing final
newlines, NUL-terminated data) under random options; output, diagnostics
(minus "Try --help") and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 500
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='nlcp-compare-')


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


def rand_text(sections=False, sort=False, eol=b'\n'):
    lines = []
    for _ in range(rng.choice([0, 1, 3, 8, 15])):
        r = rng.random()
        if sections and r < 0.15:
            lines.append(rng.choice([b'\\:\\:\\:', b'\\:\\:', b'\\:', b'XX', b'XXXX', b'XXXXXX', b'\\:x']))
        elif r < 0.35:
            lines.append(b'')
        else:
            lines.append(rng.choice([b'a', b'b', b'apple', b'Apple', b'banana', b'cherry', b'x y', b'z\tq', b'a:b']))
    if sort:
        lines.sort()
        if rng.random() < 0.15 and len(lines) > 1:
            lines[0], lines[-1] = lines[-1], lines[0]
    text = eol.join(lines)
    if lines and rng.random() < 0.85:
        text += eol
    return text


def nl_case():
    w('a', rand_text(sections=True))
    opts = []
    for _ in range(rng.choice([0, 1, 2, 3])):
        opts.append(rng.choice(['-ba', '-bt', '-bn', "-b 'pa.*e'", '-ha', '-fa', '-v 5', '-v -3', '-i 2', '-i -1', '-p',
                                '-l 2', '-ba -l 3', "-s '|'", '-s ""', '-w 3', '-w 1', '-n ln', '-n rz', '-n rn',
                                '-d XX', '-d X', "-d 'XXX'", "-d ''", '--body-numbering=a', '--number-width=2', '-bp^b']))
    if rng.random() < 0.04:
        opts.append(rng.choice(['-bx', '-n zz', '-w 0', '-l 0', '-v x', "-b 'p['"]))
    return '@nl %s a' % ' '.join(opts)


def comm_case():
    eol = b'\0' if rng.random() < 0.1 else b'\n'
    w('a', rand_text(sort=True, eol=eol))
    w('b', rand_text(sort=True, eol=eol))
    opts = []
    for _ in range(rng.choice([0, 1, 2])):
        opts.append(rng.choice(['-1', '-2', '-3', '-12', '-13', '-23', '--check-order', '--nocheck-order', '--total',
                                "--output-delimiter=:", "--output-delimiter=''", '--output-delimiter=XY']))
    if eol == b'\0':
        opts.append('-z')
    return '@comm %s a b | od -c' % ' '.join(opts)


def paste_case():
    eol = b'\0' if rng.random() < 0.1 else b'\n'
    w('a', rand_text(eol=eol))
    w('b', rand_text(eol=eol))
    w('c', rand_text(eol=eol))
    opts = []
    if rng.random() < 0.5:
        opts.append('-d ' + rng.choice(["':'", "':,'", "'\\n'", "'\\0'", "'\\t-'", "''", "'ab\\\\'", "'x\\'"]))
    if rng.random() < 0.35:
        opts.append('-s')
    if eol == b'\0':
        opts.append('-z')
    files = rng.choice(['a', 'a b', 'a b c', 'b - a', '- -', 'a a', 'c b a'])
    pre = 'cat c | ' if '-' in files.split() else ''
    return '%s@paste %s %s | od -c' % (pre, ' '.join(opts), files)


FIXED = ['@nl', '@nl nofile', '@comm a', '@comm', '@comm a b c', '@comm --output-delimiter=x --output-delimiter=y a b',
         '@comm --output-delimiter=x --output-delimiter=x a b', '@paste nofile', '@paste -d "a\\\\" a',
         '@comm - - < a', '@paste -s - - < a']


def run(cmd, which):
    c = cmd
    for a in ('nl', 'comm', 'paste'):
        c = c.replace('@' + a, (NEBOX + ' ' + a) if which == 'nebox' else a)
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


w('a', b'x\n'); w('b', b'y\n'); w('c', b'z\n')
cases = [(c, None) for c in FIXED]
for _ in range(CASES):
    r = rng.random()
    c = nl_case() if r < 0.34 else (comm_case() if r < 0.67 else paste_case())
    snap = {f: open(os.path.join(d, f), 'rb').read() for f in ('a', 'b', 'c')}
    cases.append((c, snap))
bad = 0
for c, snap in cases:
    if snap:
        for f, data in snap.items():
            w(f, data)
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            if snap:
                print('  files:', {k: v[:80] for k, v in snap.items()})
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:400] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:400] if isinstance(y, bytes) else y))
print('nlcp_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
