#!/usr/bin/env python3
"""Side-by-side test of nebox factor against GNU coreutils factor.
Usage: tests/factor_compare.py path/to/nebox [random-cases]
Fixed operands (0, 1, primes and prime powers at the 32/64/127/128-bit
edges, Carmichael numbers and strong pseudoprimes, leading zeros, '+',
spaces, invalid operands, options), standard input token splitting, and
random numbers: uniform below 2^64 and products of random primes up to
about 2^200. stdout, stderr and exit status must match. Cofactors whose
smallest prime is near 2^56 or more are left out: past 2^128 GNU takes
over a minute on them (2^128+1: 84 s) and nebox longer."""
import os, random, subprocess, sys

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 600
env = dict(os.environ, LC_ALL='C')
GNU = '/usr/bin/factor'


def isprime(n):
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2; s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47, 53):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def randprime(rnd, bits):
    while True:
        n = rnd.getrandbits(bits) | (1 << (bits - 1)) | 1
        if isprime(n):
            return n


A = [['0'], ['1'], ['2'], ['3'], ['4'], ['12'], ['360'], ['1001'], ['4294967291'], ['4294967296'], ['4294967297'],
     ['18446744073709551615'], ['18446744073709551616'], ['18446744073709551557'], ['18446744073709551614'],
     [str(2**127 - 1)], [str(2**127)], [str(2**128 - 1)], [str(2**128)], [str(2**128 + 3)], [str(2**64 + 1)], [str(3**80)],
     [str(2**200)], ['561'], ['41041'], ['3215031751'], ['3825123056546413051'], ['318665857834031151167461'],
     ['3317044064679887385961981'], [str(1000000007 * 998244353)], [str((2**61 - 1) * (2**31 - 1))], [str((2**61 - 1) ** 2)],
     [str(4294967291 ** 2)], [str(4294967291 ** 3)], [str((2**89 - 1) * 3)], [str(65537 ** 5)], [str(65521 * 65519 * 2**70)],
     ['007'], ['+12'], ['  12'], ['  +12'], ['+ 12'], ['++12'], ['12 '], ['-12'], ['-1'], [''], ['abc'], ['1a'], ['0x10'],
     ['1.5'], ['12', 'x', '13'], ['--', '-5'], ['-5'], ['--help'], ['--bogus'], ['---debug'], ['5', '-x'], ['000000000000000000000000000000012'],
     ['99999999999999999999999999999999999999']]
CASES = [(a, None) for a in A] + [
    ([], b'12 13\n14\t15\n\n  16  '), ([], b''), ([], b'   \n'), ([], b'12\r\n'), ([], b'5 x 7'), ([], b'+5 -5'),
    ([], b'18446744073709551617 340282366920938463463374607431768211459\n'), ([], b'1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16'),
    ([], b'12\x0b13\x0c14'), ([], b'00 +0'),
    ([], (' '.join(str(k) for k in range(1, 300)) + ' ' + str(2**130 + 5) + ' 7 8 ' + str(2**127) + ' 9').encode()),
    ([str(k) for k in range(1000, 1100)] + [str(2**127 + 1)] + [str(k) for k in range(5, 60)] + [str(2**127 - 1), str(3**90)], None),
]
rnd = random.Random(19)
for _ in range(NRAND):
    k = rnd.random()
    if k < 0.4:
        n = rnd.getrandbits(rnd.randint(1, 64))
    elif k < 0.6:
        n = rnd.getrandbits(rnd.randint(65, 128))
        # keep the cofactor small enough for Pollard rho in both
        n = 1
        for _ in range(rnd.randint(1, 6)):
            n *= randprime(rnd, rnd.randint(2, 30))
        n *= randprime(rnd, rnd.randint(2, 60))
    else:
        n = 1
        for _ in range(rnd.randint(1, 8)):
            n *= randprime(rnd, rnd.randint(2, 34))
        if rnd.random() < 0.5:
            n *= randprime(rnd, rnd.randint(40, 120))
    CASES.append(([str(n)], None))


def run(argv, stdin, which):
    cmd = ([NEBOX, 'factor'] if which == 'nebox' else [GNU]) + argv
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=120,
                       input=stdin if stdin is not None else b'', stdin=None)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(GNU.encode() + b':', b'factor:')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


SHELL = ['yes 12 | @ | head -3', '@ < /', 'echo 6 | @ > /dev/full', '@ 6 > /dev/full', '@ 6 7 x 8 > /dev/full']
bad = 0
for c in SHELL:
    res = []
    for which in ('gnu', 'nebox'):
        cmd = c.replace('@', GNU if which == 'gnu' else NEBOX + ' factor')
        p = subprocess.run(['bash', '-c', cmd + '; echo "status=${PIPESTATUS[*]}"'], env=env, capture_output=True, timeout=60)
        res.append((p.stdout, p.stderr.replace(NEBOX.encode() + b' ', b'').replace(GNU.encode() + b':', b'factor:')))
    if res[0] != res[1]:
        bad += 1
        print('MISMATCH:', c, res)
for argv, stdin in CASES:
    if argv in (['--help'], ['---debug']):
        n = run(argv, stdin, 'nebox')
        if n[0] != 1 or n[1] != b'':
            bad += 1; print('MISMATCH (unsupported):', argv, n)
        continue
    g = run(argv, stdin, 'gnu')
    n = run(argv, stdin, 'nebox')
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', argv, stdin)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('factor_compare: %d cases, %d mismatches' % (len(CASES) + len(SHELL), bad))
sys.exit(1 if bad else 0)
