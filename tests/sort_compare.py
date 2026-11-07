#!/usr/bin/env python3
"""Side-by-side test of nebox sort against GNU sort (C locale).
Usage: tests/sort_compare.py path/to/nebox [random-cases] [seed]
Random lines mixing integers, floats, exponents, hex floats, inf/nan, -0,
human sizes, month names, versions and words, with random global and
per-key orderings (-b -d -f -g -h -i -M -n -r -V), keys, -t, -s, -u, -c,
and the incompatible combinations. Output, diagnostics (minus "Try
--help") and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 600
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='sort-compare-')
TOKENS = ['0', '-0', '+0', '1', '10', '2', '-3', '3.5', '-3.50', '1e3', '1E-2', '.5', '0x10', '0x1p4', 'inf', '-inf',
          'nan', 'NaN', '-nan', 'abc', '', ' 7', '  12', '1k', '2K', '3M', '1G', '1.5T', 'jan', 'Feb', ' MAR', 'apr x',
          'December', 'sep', 'JUNE', 'ju', 'm', '1.2.10', '1.2.9', 'v2', 'a-1.0', 'file10.txt', 'file9.txt', 'Zebra', 'apple',
          'apple ', '_x', '9' * 25, '1,5', '1e400', '-1e-400']


def rand_line():
    n = rng.choice([1, 1, 2, 3])
    sep = rng.choice([' ', ' ', ':', '\t'])
    return sep.join(rng.choice(TOKENS) for _ in range(n))


def rand_case():
    lines = [rand_line() for _ in range(rng.choice([1, 3, 8, 20]))]
    with open(os.path.join(d, 'in'), 'w') as f:
        f.write('\n'.join(lines) + '\n')
    opts = []
    for _ in range(rng.choice([0, 1, 1, 2])):
        opts.append(rng.choice(['-g', '-M', '-n', '-h', '-V', '-f', '-b', '-d', '-i', '-r', '-s', '-u',
                                '--general-numeric-sort', '--month-sort', '--sort=month', '--sort=general-numeric',
                                '--sort=numeric', '--sort=version', '--sort=h']))
    if rng.random() < 0.5:
        for _ in range(rng.choice([1, 1, 2])):
            f1 = rng.randint(1, 3)
            mods = ''.join(rng.sample('bdfghiMnrV', rng.choice([0, 1, 1, 2])))
            spec = '%d%s' % (f1, mods)
            if rng.random() < 0.4:
                spec += ',%d%s' % (rng.randint(f1, 3), rng.choice(['', 'b', 'g', 'M', 'n']))
            opts.append('-k ' + spec)
        if rng.random() < 0.4:
            opts.append(rng.choice(["-t ':'", "-t ' '"]))
    if rng.random() < 0.05:
        opts.append('-c')
    return '@sort %s in' % ' '.join(opts)


FIXED = ['printf "nan\\n-nan\\nNaN\\n1\\nx\\n-inf\\n" | @sort -g', 'printf "JAN\\nfeb\\n mar\\nxyz\\n\\n" | @sort -M',
         '@sort -g -n in', '@sort -M -h in', '@sort -n -d in', '@sort -V -i in', '@sort -k1,1gM in',
         '@sort --sort=bogus in', '@sort --sort= in', '@sort -gM in', '@sort -k1g -k2M in']


def run(cmd, which):
    c = cmd.replace('@sort', (NEBOX + ' sort') if which == 'nebox' else 'sort')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


with open(os.path.join(d, 'in'), 'w') as f:
    f.write('3\n1\n2\n')
cases = [(c, None) for c in FIXED]
for _ in range(CASES):
    c = rand_case()
    cases.append((c, open(os.path.join(d, 'in')).read()))
bad = 0
for c, data in cases:
    if data is not None:
        with open(os.path.join(d, 'in'), 'w') as f:
            f.write(data)
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            if data:
                print('  in:', repr(data[:300]))
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
print('sort_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
