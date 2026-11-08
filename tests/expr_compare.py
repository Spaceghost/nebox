#!/usr/bin/env python3
"""Side-by-side test of nebox expr against GNU coreutils expr.
Usage: tests/expr_compare.py path/to/nebox [random-cases]
Fixed argument vectors (bignum arithmetic, truncating division, string and
integer comparisons, short-circuit | and &, the keywords, '+' quoting,
regex matches with and without \\( \\), regex and syntax errors) plus
random expressions over integers, strings and operators. stdout, stderr
and exit status must match."""
import os, random, subprocess, sys

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
env = dict(os.environ, LC_ALL='C')
GNU = '/usr/bin/expr'
B = '123456789012345678901234567890'
CASES = [
    [], ['--'], ['--', '5'], ['--help'], ['--he'], ['--v'], ['--foo'], ['-x'], ['-5'], ['--', '--help'], ['-'], ['5', '-x'],
    ['1', '+', '2'], ['10', '-', '20'], ['3', '*', '4'], ['7', '/', '2'], ['-7', '/', '2'], ['7', '/', '-2'], ['-7', '%', '2'],
    ['7', '%', '-2'], ['1', '/', '0'], ['1', '%', '0'], ['a', '+', '1'], ['1', '+', ''], ['+1', '+', '1'], ['-', '+', '1'],
    [B, '*', B], [B, '+', '1'], ['-' + B, '-', B], [B, '/', '7'], [B, '%', '97'], ['0' * 30 + '12', '+', '0'], ['-0', '+', '0'],
    ['99999999999999999999', '*', '-99999999999999999999'], [B, '/', '-' + B], ['00', '*', '5'],
    ['1', '<', '2'], ['10', '<', '9'], ['10', '<', '9a'], ['abc', '<', 'abd'], ['a', '=', 'a'], ['a', '==', 'a'], ['01', '=', '1'],
    ['-0', '=', '0'], ['a', '!=', 'b'], ['b', '>=', 'a'], ['', '<', 'a'], [B, '>', '9' * 29], ['-1', '<', '-01'],
    ['0', '|', '5'], ['0', '|', '0'], ['', '|', ''], ['a', '|', 'b'], ['0', '&', '5'], ['3', '&', '5'], ['3', '&', ''],
    ['0', '&', '1', '/', '0'], ['1', '|', '1', '/', '0'], ['0', '&', 'a', ':', '\\('], ['1', '|', 'x', '+', '1'],
    ['abc', ':', 'a'], ['abc', ':', 'b'], ['abc', ':', '.*'], ['abc', ':', '\\(.*\\)'], ['abc', ':', 'x\\(.*\\)'],
    ['abc', ':', '\\(a\\)\\(b\\)'], ['abc', ':', '\\(x\\)*'], ['aaa', ':', 'a\\{2\\}'], ['aaa', ':', 'a\\+'], ['ab', ':', 'a\\?b'],
    ['ab', ':', 'a\\|b'], ['ab', ':', '^a'], ['a^b', ':', 'a^b'], ['ab$', ':', 'ab$'], ['ab', ':', 'ab$'], ['*a', ':', '*a'],
    ['a', ':', '\\('], ['a', ':', '\\)'], ['a', ':', '['], ['a', ':', 'a\\{1'], ['a', ':', 'a\\{x\\}'], ['a', ':', '\\'],
    ['a', ':', '\\1'], ['aa', ':', '\\(a\\)\\1'], ['b', ':', '[z-a]'], ['a', ':', '[^'], ['a', ':', '[a'], ['a', ':', '[]'], ['a', ':', 'a\\{1,'], ['a', ':', 'a\\{1x\\}'], ['a', ':', 'a\\{1x'],
    ['a', ':', 'a\\{\\}'], ['aa', ':', 'a\\{,2\\}'], ['a', ':', 'a\\{,\\}'], ['a', ':', 'a\\{2,1\\}'], ['a', ':', 'a\\{1,2,3\\}'], ['a' * 300, ':', 'a\\{300\\}'],
    ['a', ':', 'a\\{32768\\}'], ['a', ':', 'a\\{32767\\}'], ['a', ':', 'a\\{99999999999\\}'], ['a', ':', 'a\\{1\\,2\\}'], ['a', ':', '\\(a\\)\\)'], ['b', ':', '[a-c]'], ['a.b', ':', 'a\\.b'],
    ['a\nb', ':', 'a.b'], ['a\nb', ':', 'a[^x]b'], ['x', ':', '[[:alpha:]]'], ['x', ':', '[[:bogus:]]'], ['ab', ':', 'a\\{1,0\\}'],
    ['abc', ':', '\\(b\\)'], ['', ':', ''], ['', ':', '\\(\\)'], ['a', ':', 'a', ':', '1'], ['5', ':', '5', '+', '1'],
    ['match', 'abc', 'a.'], ['match', 'abc', '\\(.\\)'], ['match', 'abc'], ['length', 'abc'], ['length', ''], ['length'],
    ['length', 'length'], ['length', '+', 'length'], ['+', 'length'], ['+'], ['index', 'abc', 'cb'], ['index', 'abc', ''],
    ['index', 'abc', 'x'], ['index', '', 'a'], ['substr', 'hello', '2', '3'], ['substr', 'hello', '0', '3'],
    ['substr', 'hello', '5', '9'], ['substr', 'hello', '6', '1'], ['substr', 'hello', '-1', '2'], ['substr', 'hello', '2', '-1'],
    ['substr', 'hello', 'a', '1'], ['substr', 'hello', '1', '99999999999999999999999'], ['substr', 'hello', '1'],
    ['substr', 'hello', '18446744073709551615', '1'], ['substr', 'hello', '1', '18446744073709551615'], ['substr', 'hello', '1', '18446744073709551614'],
    ['(', '1', '+', '2', ')', '*', '3'], ['(', '1'], ['(', '1', 'x'], [')'], ['(', ')'], ['1', '+'], ['1', '+', '('], ['1', '2'],
    ['(', '(', '5', ')', ')'], ['length', '(', 'abc', ')'], ['1', '+', '2', '*', '3'], ['2', '*', '3', '+', '4', '<', '11'],
    ['index', 'x'], ['substr'], ['a', ':'], ['1', '|'], ['1', '&'], ['1', '<'], ['match'], ['index'], ['0'], ['00'], ['-0'], [''],
    ['abc'], ['length', '12', '+', '1'], ['(', 'length', ')'], ['match', 'match', 'match'], ['substr', 'abc', '1', '1', 'x'],
    ['5', '=', '5', '=', '1'], ['a', '<', 'b', '<', '2'], ['+', '+'], ['+', '(', ')'], ['1', '-', '-1'], ['1', '-', '-'],
]
WORDS = ['0', '1', '2', '-1', '7', '00', '-0', '10', '-12', '3', B, '-' + B, 'a', 'abc', '', 'b', '5x', '+', '(', ')', 'length',
         'match', 'index', 'substr', ':', '.*', '\\(.\\)', 'a*', '[ab]']
OPS = ['|', '&', '<', '<=', '=', '==', '!=', '>=', '>', '+', '-', '*', '/', '%', ':']


def rand_expr(rnd, depth=0):
    r = rnd.random()
    if depth > 3 or r < 0.35:
        return [rnd.choice(WORDS[:18])]
    if r < 0.5:
        return ['('] + rand_expr(rnd, depth + 1) + [')']
    if r < 0.6:
        kw = rnd.choice(['length', 'match', 'index', 'substr', '+'])
        n = {'length': 1, 'match': 2, 'index': 2, 'substr': 3, '+': 1}[kw]
        out = [kw]
        for _ in range(n):
            out += [rnd.choice(WORDS[:18])]
        return out
    return rand_expr(rnd, depth + 1) + [rnd.choice(OPS)] + rand_expr(rnd, depth + 1)


def run(argv, which):
    cmd = ([NEBOX, 'expr'] if which == 'nebox' else [GNU]) + argv
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(GNU.encode() + b':', b'expr:')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


rnd = random.Random(3)
cases = CASES + [rand_expr(rnd) + ([rnd.choice(WORDS)] if rnd.random() < 0.1 else []) for _ in range(NRAND)]
bad = 0
for c in cases:
    if c in (['--help'], ['--he'], ['--v']):
        n = run(c, 'nebox')
        if n[0] != 2 or n[1] != b'':
            bad += 1
            print('MISMATCH (unsupported help):', c, n)
        continue
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('expr_compare: %d cases, %d mismatches' % (len(cases), bad))
sys.exit(1 if bad else 0)
