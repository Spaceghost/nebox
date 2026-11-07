#!/usr/bin/env python3
"""Side-by-side test of `nebox join` against GNU join (coreutils).
Usage: tests/join_compare.py path/to/nebox [random-cases] [seed]
Fixed cases cover options, diagnostics and the obsolete argument forms;
random cases join small files with repeated keys (sorted, or occasionally
not) under random option sets. Standard output, standard error and the exit
status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='join-compare-')


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


w('a', b'1 apple red\n2 banana yellow\n3 cherry red\n5 elder\n')
w('b', b'1 one\n2 two\n2 deux\n4 four\n5 five x y\n')
w('c', b'a,1,x\nb,,y\nc,3\n')
w('d', b'a,A\nc,C\nd,D\n')
w('h1', b'id name\n1 x\n2 y\n')
w('h2', b'id val\n2 v2\n3 v3\n')
w('u', b'b 1\na 2\nc 3\n')
w('u2', b'a x\nb y\nc z\n')
w('blank', b'  1   lead   spaces  \n\t2\tt\n3 \n')
w('ci1', b'Apple 1\nbanana 2\n')
w('ci2', b'apple x\nBANANA y\n')
w('z1', b'1 a\x002 b\x00')
w('z2', b'1 A\x002 B\x00')
w('nonl1', b'1 a\n2 b')
w('nonl2', b'1 A\n2 B')
w('empty', b'')
w('tabs', b'k1\tv1\tw1\nk2\t\tw2\n')
w('tabs2', b'k1\tq1\nk2\tq2\n')

FIXED = [
    'J a b', 'J -a1 a b', 'J -a2 a b', 'J -a1 -a2 a b', 'J -v1 a b', 'J -v2 a b', 'J -v1 -v2 a b',
    'J -o 1.2,2.2 a b', 'J -o 0,2.2,1.3 a b', "J -o '1.1 2.2' a b", 'J -o 1.2 -o 2.2 a b',
    'J -e X -o 1.3,2.3 a b', 'J -e X -a1 -o 0,1.2,2.2 a b', 'J -a1 -a2 -e - -o auto a b', 'J -o auto a b',
    'J -t, c d', 'J -t, -a1 -e EMPTY -o 0,1.2,2.2 c d', 'J -t, -o auto -e Q -a2 c d',
    'J -1 2 -2 1 b a', 'J -j 1 a b', 'J -j1 a b', 'J -j2 a b', 'J -j 2 a b', 'J -1 1 -2 1 a b',
    'J -1 2 -1 2 a b', 'J -1 2 -1 3 a b', 'J -1 0 a b', 'J -1 x a b', 'J -1 99999999999999999999999 a b',
    'J -o 3.1 a b', 'J -o 1x a b', 'J -o 0.1 a b', 'J -o 1.0 a b', 'J -o 1.,2.1 a b', 'J -o 1.1,,2.1 a b',
    'J -a 3 a b', 'J -a x a b', 'J -e A -e B a b', 'J -e A -e A a b', 'J -t ab c d', 'J -t , -t ; c d',
    'J -t , -t , c d', "J -t '' a b", "J -t '\\0' a b", 'J --header h1 h2', 'J --header -a1 -a2 h1 h2',
    'J --header -o auto h1 h2', 'J --header empty h2', 'J u u2', 'J --check-order u u2', 'J --nocheck-order u u2',
    'J -a1 u u2', 'J --check-order a b', 'J -i ci1 ci2', 'J --ignore-case ci1 ci2', 'J ci1 ci2',
    'J -z z1 z2', 'J --zero-terminated -a1 z1 z2', 'J nonl1 nonl2', 'J empty b', 'J b empty', 'J -a1 b empty',
    'J -a2 b empty', 'J blank blank', 'J -o auto blank blank', 'J -t "$(printf "\\t")" tabs tabs2',
    'J -t "$(printf "\\t")" -o auto -e NA tabs tabs2', 'J a', 'J', 'J a b c', 'J -o 1.1 a b 2.1',
    'J -o 1.1 a b 2.2 x', 'J -j1 a b 2', 'J -j2 2 a b', 'J -j1 2 a b', 'J --foo a b', 'J -x a b', 'J -a',
    'J --he a b', 'J --h a b', 'J --header=1 h1 h2', 'J --check a b', 'J nofile b', 'J a nofile', 'J - -',
    'cat a | J - b', 'cat b | J a -', 'J -- a b', 'J -- -a1 b', 'J a b --', 'J a -- b', 'J -a1 -- a b',
    "J 'x y' b", 'J -v 3 a b', 'J -1 1 -j 2 a b', 'J -j 1 -j 2 a b',
]


def rand_file(n, alpha, sep, fields):
    keys = sorted(rng.choice(alpha) * rng.choice([1, 1, 2]) for _ in range(n))
    if rng.random() < 0.12 and len(keys) > 1:
        i = rng.randrange(len(keys) - 1)
        keys[i], keys[i + 1] = keys[i + 1], keys[i]
    lines = []
    for k in keys:
        fs = [k] + [rng.choice(['p', 'q', 'rr', '', 'S']) for _ in range(rng.choice(fields))]
        if sep == ' ':
            s = ' '.join(f for f in fs if f) if rng.random() < 0.8 else '  '.join(fs)
        else:
            s = sep.join(fs)
        lines.append(s)
    data = '\n'.join(lines) + ('\n' if lines and rng.random() < 0.9 else '')
    return data.encode()


def rand_case():
    sep = rng.choice([' ', ' ', ',', ':'])
    alpha = rng.choice(['ab', 'abc', 'abcdef', 'aAbB'])
    w('r1', rand_file(rng.choice([0, 1, 3, 6, 12]), alpha, sep, [0, 1, 2, 3]))
    w('r2', rand_file(rng.choice([0, 1, 3, 6, 12]), alpha, sep, [0, 1, 2]))
    opts = []
    if sep != ' ':
        opts.append('-t' + sep)
    for _ in range(rng.choice([0, 1, 2])):
        opts.append(rng.choice(['-a1', '-a2', '-v1', '-v2', '-i', '--check-order', '--nocheck-order',
                                '-e@', '-o auto', '-o 0,1.2,2.2', '-o 2.1,1.1', '-1 2', '-2 2', '-j 1',
                                '--header']))
    return 'J %s r1 r2' % ' '.join(opts)


def run(cmd, which):
    j = 'join' if which == 'gnu' else NEBOX + ' join'
    p = subprocess.run(['sh', '-c', cmd.replace('J', j, 1) if cmd.startswith('J') else cmd.replace(' J ', ' ' + j + ' ')],
                       cwd=d, env=env, capture_output=True, timeout=30)
    return p.returncode, p.stdout, p.stderr


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    if c.startswith('J') or ' J ' in c:
        pass
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            for name, a, b in zip(('status', 'stdout', 'stderr'), g, n):
                if a != b:
                    print('  %s gnu:   %r' % (name, a))
                    print('  %s nebox: %r' % (name, b))
            if 'r1' in c:
                print('  r1:', open(os.path.join(d, 'r1'), 'rb').read())
                print('  r2:', open(os.path.join(d, 'r2'), 'rb').read())
print('join_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
