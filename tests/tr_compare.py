#!/usr/bin/env python3
"""Side-by-side test of nebox tr against GNU tr.
Usage: tests/tr_compare.py path/to/nebox [random-cases] [seed]
Random set specifications drawn from tr's grammar (characters, ranges,
[:class:], [=c=], [c*n], [c*], escapes) under random options translate,
delete and squeeze random input; output, every diagnostic line and the
exit status must match."""
import os, random, subprocess, sys

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 500
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
CLASSES = ['alnum', 'alpha', 'blank', 'cntrl', 'digit', 'graph', 'lower', 'print', 'punct', 'space', 'upper', 'xdigit']
INPUT = bytes(range(256)) + b'Hello, World! aaa  bbb\t\tccc\n\n\nzzz 123 \\ [x] -_- ' * 3


def rand_char():
    r = rng.random()
    if r < 0.6:
        return rng.choice('abcxyzABCXYZ019 -_.')
    if r < 0.8:
        return rng.choice(['\\n', '\\t', '\\\\', '\\0', '\\101', '\\7', '\\400', '\\-', '\\[', '\\]', '\\*'])
    return rng.choice(['[', ']', '*', ':', '=', '-'])


def rand_elem(in_s2):
    r = rng.random()
    if r < 0.35:
        return rand_char()
    if r < 0.55:
        a, b = sorted(rng.sample('abcdefghxyzABCDEFXYZ0123456789', 2))
        if rng.random() < 0.1:
            a, b = b, a
        return a + '-' + b
    if r < 0.7:
        c = rng.choice(CLASSES + (['upper', 'lower'] * 3 if in_s2 else [])) if rng.random() < 0.95 else 'bogus'
        return '[:%s:]' % c
    if r < 0.78:
        return '[=%s=]' % rng.choice(['a', 'b', 'ab', '', '*'])
    if r < 0.95:
        n = rng.choice(['', '', '3', '0', '010', '9', 'x', '08', '99999999999999999999999'])
        return '[%s*%s]' % (rng.choice('abxZ\n-'), n)
    return rng.choice(['[', '[:', '[::]', '[==]', '[a', 'a-', '-a'])


def rand_spec(in_s2=False):
    return ''.join(rand_elem(in_s2) for _ in range(rng.choice([0, 1, 1, 2, 3])))


def sq(s):
    return "'" + s.replace("'", "'\\''") + "'"


def rand_case():
    opts = ''.join(rng.sample('cdst', rng.choice([0, 0, 1, 1, 2])))
    if rng.random() < 0.05:
        opts += 'C'
    n = rng.choice([1, 2, 2, 2])
    args = [sq(rand_spec())] + ([sq(rand_spec(True))] if n == 2 else [])
    return ('-' + opts + ' ' if opts else '') + ' '.join(args)


FIXED = ["a-z A-Z", "'[:lower:]' '[:upper:]'", "'[:upper:]' '[:lower:]'", "-d '[:digit:]'", "-s ' '", "-cs '[:alnum:]' '\\n'",
         "-d", "", "a", "a b c", "-d a b", "-ds a b", "-s a b", "abc 'x[y*]z'", "'a-z' '[A*]'", "'a-z' '[A*5]'",
         "'[:upper:][:digit:]' '[:lower:]'", "'[:digit:]' '[:lower:]'", "'[:lower:]' 'a-z'", "'[:lower:]' '[:upper:][:digit:]'",
         "-c '[:alpha:]' x", "-c '[:alpha:]' xy", "-c 'a' '[x*]'", "-t abc xy", "abc ''", "-t abc ''", "'' x",
         "'[=a=]' x", "a '[=a=]'", "'[:foo:]' x", "'[::]' x", "'[==]' x", "'[=ab=]' x", "'[a*x]' x", "a '[a*x]'",
         "'[a*]' x", "a '[b*][c*]'", "-d 'a' '[b*]'", "'z-a' x", "'\\400' x", "'\\' x", "'a\\' x", "'\\q' x",
         "-C abc x", "--delete abc", "--squeeze-repeats a", "--complement --delete a", "--truncate-set1 abc x",
         "-A abc x", "'[a-z]' x", "'a-z' '[:upper:]'", "'[:alpha:]' '[:upper:]'", "-s '[:upper:]' '[:lower:]'",
         "'\\0-\\377' x", "'[x*999999999999999999999999]' a", "a '[x*0]'", "'ab' '[x*010]'", "'a' '[x*08]'"]
cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    res = []
    for exe in ('tr', NEBOX + ' tr'):
        p = subprocess.run(['sh', '-c', '%s %s' % (exe, c)], input=INPUT, env=env, capture_output=True, timeout=30)
        err = p.stderr.replace(NEBOX.encode() + b' ', b'')
        err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
        res.append((p.returncode, p.stdout, err))
    if res[0] != res[1]:
        bad += 1
        if bad <= 12:
            print('MISMATCH: tr', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), res[0], res[1]):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
print('tr_compare: %d cases, %d mismatches' % (len(cases), bad))
sys.exit(1 if bad else 0)
