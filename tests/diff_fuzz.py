#!/usr/bin/env python3
"""Differential test of `nebox diff` against GNU diff on random inputs.
Usage: tests/diff_fuzz.py path/to/nebox [cases] [seed]
Small alphabets make repeated lines common, which exercises the parts of GNU
diff's algorithm that choose between equally short edit scripts
(discard_confusing_lines, the middle snake, shift_boundaries)."""
import os, random, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
FLAGS = [[], ['-u'], ['-U1'], ['-U0'], ['-c'], ['-C2'], ['-e'], ['-b'], ['-w', '-u'], ['-i'], ['-B', '-u'], ['-B']]
d = tempfile.mkdtemp(prefix='diff-fuzz-')
a, b = os.path.join(d, 'a'), os.path.join(d, 'b')
env = dict(os.environ, TZ='UTC', LC_ALL='C')


def rand_file(rng):
    alpha = rng.choice(['ab', 'abc', 'abcdef', 'abcdefghijklmnop'])
    n = rng.choice([0, 1, 2, 5, 10, 30, 80])
    lines = []
    for _ in range(n):
        w = ''.join(rng.choice(alpha) for _ in range(rng.choice([0, 1, 1, 2])))
        if rng.random() < 0.1:
            w = rng.choice([' ', '  ']) + w + rng.choice(['', ' ', '\t'])
        if rng.random() < 0.05:
            w = w.upper()
        lines.append(w)
    text = '\n'.join(lines)
    if lines and rng.random() < 0.85:
        text += '\n'
    return text


def mutate(rng, text):
    lines = text.split('\n')
    for _ in range(rng.choice([1, 2, 4, 8])):
        op = rng.random()
        i = rng.randrange(len(lines) + 1)
        if op < 0.4:
            lines.insert(i, rng.choice(['a', 'b', 'c', 'x', '', 'a b']))
        elif op < 0.7 and lines:
            del lines[min(i, len(lines) - 1)]
        elif lines:
            lines[min(i, len(lines) - 1)] = rng.choice(['z', 'a', 'B', ' a', ''])
    return '\n'.join(lines)


fails = 0
byflag = {}
for n in range(CASES):
    t0 = rand_file(rng)
    t1 = mutate(rng, t0) if rng.random() < 0.8 else rand_file(rng)
    for p, t in ((a, t0), (b, t1)):
        with open(p, 'w') as f:
            f.write(t)
        os.utime(p, ns=(1767323045123456789, 1767323045123456789))
    for flags in FLAGS:
        ref = subprocess.run(['diff'] + flags + [a, b], capture_output=True, env=env)
        got = subprocess.run([NEBOX, 'diff'] + flags + [a, b], capture_output=True, env=env)
        if ref.stdout != got.stdout or ref.returncode != got.returncode:
            fails += 1
            byflag[' '.join(flags)] = byflag.get(' '.join(flags), 0) + 1
            if fails <= 5:
                print('FAIL case %d flags %s' % (n, flags))
                print('  a=%r' % t0)
                print('  b=%r' % t1)
                print('  ref(%d)=%r' % (ref.returncode, ref.stdout[:400]))
                print('  got(%d)=%r' % (got.returncode, got.stdout[:400]))
if byflag: print('mismatches by flags:', byflag)
print('diff fuzz: %d cases x %d flag sets, %d mismatches' % (CASES, len(FLAGS), fails))
sys.exit(1 if fails else 0)
