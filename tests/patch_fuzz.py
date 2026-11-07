#!/usr/bin/env python3
"""Differential test of `nebox patch` against GNU patch 2.7.6.
Usage: tests/patch_fuzz.py path/to/nebox [cases] [seed]
Each case makes a random file A and an edited copy B, writes their diff
(unified, context or normal, from GNU diff), perturbs A into the target
(lines added at the top for offsets, context lines changed for fuzz, a
changed line edited so a hunk fails, or B itself for a reversed patch), then
runs both patch programs on copies of the target with one option set and
compares standard output, exit status, the patched file and the reject file.
Standard input is /dev/null and there is no terminal, so the questions GNU
patch asks take their defaults in both."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 300
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
FORMATS = [['-u'], ['-U1'], ['-c'], []]
OPTIONS = [[], ['-N'], ['-t'], ['-f'], ['-F0'], ['-F1'], ['-s'], ['--dry-run'], ['-R'], ['-b']]
env = dict(os.environ, LC_ALL='C', TZ='UTC')
root = tempfile.mkdtemp(prefix='patch-fuzz-')


def rand_lines(n):
    alpha = rng.choice(['ab', 'abcd', 'abcdefghijklmnop'])
    return [''.join(rng.choice(alpha) for _ in range(rng.choice([1, 2, 3]))) for _ in range(n)]


def edit(lines):
    out = list(lines)
    for _ in range(rng.choice([1, 2, 3])):
        if not out:
            out.append('new')
            continue
        i = rng.randrange(len(out))
        op = rng.random()
        if op < 0.35:
            out[i] = out[i] + 'X'
        elif op < 0.65:
            out.insert(i, 'ins' + str(rng.randrange(100)))
        else:
            del out[i]
    return out


def write(path, lines, nonl=False):
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + ('' if nonl or not lines else '\n'))


fails = 0
for n in range(CASES):
    a = rand_lines(rng.choice([5, 12, 30]))
    b = edit(a)
    fmt = rng.choice(FORMATS)
    d = os.path.join(root, 'c%d' % n)
    os.makedirs(d)
    write(os.path.join(d, 'a'), a)
    write(os.path.join(d, 'b'), b)
    p = subprocess.run(['diff'] + fmt + ['a', 'b'], cwd=d, capture_output=True, env=env).stdout
    if not p:
        continue
    open(os.path.join(d, 'p.diff'), 'wb').write(p)
    # the target
    kind = rng.random()
    t = list(a)
    if kind < 0.25:
        t = ['top%d' % i for i in range(rng.choice([1, 3, 7]))] + t
    elif kind < 0.45 and t:
        i = rng.randrange(len(t))
        t[i] = t[i] + 'F'
    elif kind < 0.55:
        t = list(b)
    elif kind < 0.6 and t:
        t = t[:-1]
    opts = rng.choice(OPTIONS)
    operand = [] if fmt else ['t']
    results = []
    for tool in ('gnu', 'nb'):
        w = os.path.join(d, tool)
        os.makedirs(w)
        # unified and context diffs name a; normal diffs get the operand t
        write(os.path.join(w, 'a' if fmt else 't'), t)
        cmd = (['patch'] if tool == 'gnu' else [NEBOX, 'patch']) + opts + operand
        r = subprocess.run(cmd, cwd=w, stdin=open(os.path.join(d, 'p.diff'), 'rb'),
                           capture_output=True, env=env)
        files = {}
        for name in sorted(os.listdir(w)):
            files[name] = open(os.path.join(w, name), 'rb').read()
        results.append((r.stdout, r.returncode, files))
    if results[0] != results[1]:
        fails += 1
        if fails <= 4:
            print('FAIL case %d fmt %s opts %s' % (n, fmt, opts))
            print('  patch: %r' % p[:300])
            print('  target: %r' % t)
            for label, (out, rc, files) in zip(('gnu', 'nebox'), results):
                print('  %s rc=%d out=%r' % (label, rc, out[:300]))
                for k, v in files.items():
                    print('    %s: %r' % (k, v[:200]))
    shutil.rmtree(d)
print('patch fuzz: %d cases, %d mismatches' % (CASES, fails))
sys.exit(1 if fails else 0)
