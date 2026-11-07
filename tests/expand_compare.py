#!/usr/bin/env python3
"""Side-by-side test of nebox expand and unexpand against GNU coreutils.
Usage: tests/expand_compare.py path/to/nebox [random-cases] [seed]
Random lines of spaces, tabs, backspaces and text under random tab lists
(single sizes, lists, "/N", "+N", obsolete -N and -N,M forms), -i, -a,
--first-only, several files and lines continuing across files. Output,
diagnostics (minus "Try --help") and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 600
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='expand-compare-')


def rand_text():
    out = []
    for _ in range(rng.choice([1, 3, 8])):
        line = ''.join(rng.choice([' ', ' ', '  ', '\t', '\t', 'a', 'bc', 'defgh', '\b', 'x y']) for _ in range(rng.choice([0, 2, 6, 12])))
        out.append(line)
    t = '\n'.join(out)
    if rng.random() < 0.8:
        t += '\n'
    return t.encode()


def rand_tabs():
    r = rng.random()
    if r < 0.3:
        return str(rng.choice([1, 2, 3, 4, 8, 13]))
    stops = sorted(set(rng.randint(1, 30) for _ in range(rng.choice([1, 2, 3]))))
    s = ','.join(map(str, stops))
    if r < 0.5:
        s += rng.choice([',/4', ',+3', ' /5', ' +2'])
    if rng.random() < 0.05:
        s = rng.choice(['0', '3,2', '2,2', 'x', '/4,/5', '+4,/5', '4/', '1,+2,3', '99999999999999999999999'])
    return s


def rand_case():
    for f in ('a', 'b'):
        with open(os.path.join(d, f), 'wb') as fh:
            fh.write(rand_text())
    files = rng.choice(['a', 'a b', '-', 'a - b', 'nofile a'])
    prog = rng.choice(['expand', 'unexpand'])
    opts = []
    if rng.random() < 0.6:
        opts.append("-t '%s'" % rand_tabs())
    if prog == 'expand':
        if rng.random() < 0.3:
            opts.append('-i')
        if rng.random() < 0.1:
            opts.append(rng.choice(['-4', '-3,7', '-12']))
    else:
        if rng.random() < 0.3:
            opts.append('-a')
        if rng.random() < 0.2:
            opts.append('--first-only')
        if rng.random() < 0.1:
            opts.append(rng.choice(['-4', '-3,7', '-1 -2']))
    pre = 'cat b | ' if '-' in files.split() else ''
    return '%s@%s %s %s | od -c' % (pre, prog, ' '.join(opts), files)


def run(cmd, which):
    c = cmd
    for a in ('unexpand', 'expand'):
        c = c.replace('@' + a, (NEBOX + ' ' + a) if which == 'nebox' else a)
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


cases = []
for _ in range(CASES):
    c = rand_case()
    cases.append((c, {f: open(os.path.join(d, f), 'rb').read() for f in ('a', 'b')}))
bad = 0
for c, snap in cases:
    for f, data in snap.items():
        with open(os.path.join(d, f), 'wb') as fh:
            fh.write(data)
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            print('  files:', snap)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:400] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:400] if isinstance(y, bytes) else y))
print('expand_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
