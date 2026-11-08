#!/usr/bin/env python3
"""Side-by-side test of nebox printf against GNU coreutils printf.
Usage: tests/printf_compare.py path/to/nebox [random-cases]
Fixed argument vectors (escapes, %b, %q, '*' widths, character constants,
numeric diagnostics, format reuse) plus random directives with random
flags, widths, precisions, length modifiers and arguments. stdout, stderr
and exit status must match. Run without a shell so GNU's binary is used,
not a shell builtin."""
import os, random, subprocess, sys

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
GNU = '/usr/bin/printf'

CASES = [
    [], ['--'], ['--', 'x\\n'], ['-x'], ['%d\\n', '1', '2', '3'], ['%s-%s\\n', 'a', 'b', 'c'], ['x\\n', 'extra', 'more'],
    ['%d', '0x1f'], ['%d', '010'], ['%d', '-0x10'], ['%d', ' 5'], ['%d', '5 '], ['%d', 'abc'], ['%d', '12abc'], ['%d', ''],
    ['%d', '99999999999999999999'], ['%d', '-99999999999999999999'], ['%u', '-1'], ['%x', '-1'], ['%o', '18446744073709551616'],
    ['%d', "'a"], ['%d', '"b'], ['%d', "'abc"], ['%d', "'"], ['%x', "'\xff"], ['%f', "'A"], ['%c', ''], ['%c', 'hello'],
    ['%5c|%-5c|', 'a', 'b'], ['%s', ''], ['%.2s', 'hello'], ['%10.3s|', 'hello'], ['%-10s|', 'x'], ['%*d|', '5', '42'],
    ['%-*d|', '5', '42'], ['%*d|', '-5', '42'], ['%.*d|', '3', '7'], ['%.*d|', '-3', '7'], ['%*.*f|', '10', '2', '3.14159'],
    ['%*d', 'x', '1'], ['%*d', '99999999999', '1'], ['%.*d', '99999999999', '1'], ['%*d'], ['%.*f', '2'], ['%*s|'],
    ['%i', '017'], ['%#o %#x %#X', '8', '255', '255'], ['%+d % d', '5', '5'], ['%05d|%-05d', '42', '42'], ['%ld %lld %hd %jd %zd %td', '1', '2', '3', '4', '5', '6'],
    ['%Lf %lf %hf', '1', '2', '3'], ['%hhd', '300'], ['%f', '1e5000'], ['%f', '-1e5000'], ['%g', '1e-5000'], ['%e', '1e-4950'],
    ['%f', 'inf'], ['%f', '-INF'], ['%f', 'nan'], ['%F', 'infinity'], ['%g', '0x1p-3'], ['%a', '1'], ['%A', '0.1'], ['%.3a', '1'],
    ['%a', '0'], ['%La', '-2.5'], ['%e', '123.456'], ['%E', '0'], ['%.0e', '5'], ['%#.0f', '3'], ['%g', '100000'], ['%g', '1000000'],
    ['%G', '1e-10'], ['%#g', '1'], ['%.20g', '0.1'], ['%f', '1.5x'], ['%f', ''], ['%f', '.'], ['%f', '1,5'], ["%'d", '1234567'],
    ["%'f", '1234.5'], ['%Id', '5'], ["%'s", 'x'], ['%#d', '1'], ['%#c', 'a'], ['%0s', 'a'], ['%.3c', 'a'], ['%#s', 'a'],
    ['%z'], ['%'], ['%5'], ['%-'], ['%.'], ['%l'], ['%y', 'x'], ['%5.2y'], ['%%'], ['%%%d%%', '3'], ['a%sb', 'x', 'y'],
    ['%b', 'a\\nb'], ['%b', '\\0101\\101'], ['%b', '\\c', 'x'], ['%b|%b', 'x\\cy', 'z'], ['%b'], ['%b', '\\x41\\x4g\\xg'],
    ['%b', '\\u0041'], ['%b', '\\u00e9'], ['%b', '\\q\\'], ['%q', 'a b'], ['%q', ''], ['%q', "it's"], ['%q', 'a\nb'], ['%q', '~x'],
    ['%q', 'a=b'], ['%q', '\x01\x7f\xff'], ['%q|%q', 'a', '$x'], ['%10q|', 'x'],
    ['\\a\\b\\e\\f\\n\\r\\t\\v\\"\\\\'], ['\\101\\1012\\0101'], ['\\x41\\x414'], ['\\x'], ['\\xz'], ['\\u0041'], ['\\u004'], ['\\U00000041'],
    ['\\u00e9|\\U0001F600|\\U00110000|\\u0024\\u0040\\u0060'], ['\\u0041z'], ['\\u0000'], ['\\ud800'], ['\\U0000DFFF'], ['\\u009f'], ['\\u00a0'],
    ['\\q'], ['abc\\'], ['ab\\cde'], ['%s\\c%s', 'a', 'b'], ['%d\\n', 'x', '2', 'y'], ['%d %d\\n', '1'], ['%s', 'a', 'b'],
    ['%5%|'], ['%-5%|'], ['%d %s %f %c %x\\n', '1', 'two', '3', 'four', '5', '6', 'seven'], ['plain'], ['\\0'], ['%c', '\\0'],
    ['%s%c%s', 'a', '', 'b'], ['%.0s|', 'abc'], ['%.s|', 'abc'], ['%.d|', '0'], ['%.0d|', '0'], ['%+.3d', '-5'],
    ['%5.1f|%-8.3e|%08.2f', '3.14159', '2.5', '-1.5'], ['%x %X %o', '0xdeadbeef', '0XFF', '0777'], ['%d', '0x'], ['%d', '+'], ['%d', '-'],
    ['%d', '0b101'], ['%u', '+5'], ['%d', '9223372036854775807'], ['%d', '9223372036854775808'], ['%u', '18446744073709551615'],
    ['%f', '0x1.8p1'], ['%f', '1e400'], ['%Lg', '1.18973149535723176502e+4932'], ['%g', '4e-4951'], ['%.30f', '1'],
    ['%1000d|', '5'], ['%.600f', '1'], ['%-600s|', 'x'],
]


def rand_arg(rnd):
    k = rnd.random()
    if k < 0.3:
        return str(rnd.randint(-100000, 100000))
    if k < 0.4:
        return rnd.choice(['0x', '0X', '0', '-0x', '+0']) + format(rnd.randint(0, 10**6), 'x')
    if k < 0.6:
        return repr(rnd.uniform(-1e6, 1e6)) if rnd.random() < 0.5 else '%.*e' % (rnd.randint(0, 8), rnd.uniform(-1, 1) * 10 ** rnd.randint(-300, 300))
    if k < 0.65:
        return rnd.choice(["'a", '"Z', "'", "'xy", '\'"'])
    if k < 0.75:
        return rnd.choice(['', 'abc', '12x', ' 7', 'inf', '-nan', '1e', '.5', '5.', '-.', '0x1p4', '1e-400', '1e999', str(2**64), str(-2**63 - 1)])
    return ''.join(rnd.choice('abcXYZ 019%-\\.') for _ in range(rnd.randint(0, 6)))


def rand_case(rnd):
    parts = []
    args = []
    for _ in range(rnd.randint(1, 4)):
        if rnd.random() < 0.2:
            parts.append(rnd.choice(['x', ' ', '\\n', '\\t', '\\101', '\\x41', '-', '\\\\']))
            continue
        d = '%' + ''.join(rnd.choice("-+ #0'") for _ in range(rnd.choice([0, 0, 1, 2])))
        r = rnd.random()
        if r < 0.15:
            d += '*'; args.append(str(rnd.randint(-20, 20)))
        elif r < 0.5:
            d += str(rnd.randint(0, 20))
        r = rnd.random()
        if r < 0.15:
            d += '.*'; args.append(str(rnd.randint(-3, 12)))
        elif r < 0.45:
            d += '.' + str(rnd.randint(0, 12)) if rnd.random() < 0.9 else '.'
        d += rnd.choice(['', '', '', 'l', 'll', 'h', 'L', 'j', 'z'])
        d += rnd.choice('diouxXfFeEgGaAcs' + 'diuxfegs')
        parts.append(d)
        args.append(rand_arg(rnd))
    if rnd.random() < 0.2:
        args.append(rand_arg(rnd))
    return [''.join(parts)] + args


def run(argv, which):
    cmd = ([NEBOX, 'printf'] if which == 'nebox' else [GNU]) + argv
    p = subprocess.run(cmd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(GNU.encode() + b':', b'printf:')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


rnd = random.Random(11)
cases = CASES + [rand_case(rnd) for _ in range(NRAND)]
bad = known = 0
LIMIT = b'cannot perform formatted output: Value too large for defined data type'
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n and LIMIT in n[2] and LIMIT not in g[2]:
        known += 1  # nelibc refuses widths/precisions above 100000 (README)
        continue
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('printf_compare: %d cases, %d mismatches, %d over nelibc\'s width/precision limit' % (len(cases), bad, known))
sys.exit(1 if bad else 0)
