#!/usr/bin/env python3
"""Side-by-side test of nebox test and [ against GNU coreutils.
Usage: tests/test_compare.py path/to/nebox [random-cases]
Random argument vectors drawn from operators, parentheses, integers
(huge, negative, padded, invalid), strings and fixture files, run through
/usr/bin/test and /usr/bin/[ and nebox: exit status and diagnostics must
match."""
import os, random, subprocess, sys, tempfile, shutil

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
d = tempfile.mkdtemp(prefix='test-compare-')
env = dict(os.environ, LC_ALL='C')
subprocess.run(['bash', '-c', 'printf x > f; : > e; mkdir dir; ln -s f lf; ln -s nowhere dl; mkfifo p; chmod 4755 f; '
                'ln f hf; touch -d 2000-01-01 old; chmod 1777 dir; printf y > ro; chmod 444 ro'], cwd=d, check=True)
VOCAB = ['!', '(', ')', '-a', '-o', '=', '==', '!=', '-eq', '-ne', '-lt', '-le', '-gt', '-ge', '-nt', '-ot', '-ef',
         '-n', '-z', '-e', '-f', '-d', '-s', '-L', '-h', '-p', '-u', '-g', '-k', '-r', '-w', '-x', '-O', '-G', '-N', '-t',
         '-S', '-b', '-c', '-l', '-q', '', 'a', 'b', '0', '1', '-1', '+1', ' 7 ', '007', '-0', '99999999999999999999999',
         '-99999999999999999999', '1x', 'f', 'e', 'dir', 'lf', 'dl', 'p', 'hf', 'old', 'ro', 'nonexistent', ']']
FIXED = [[], ['a'], [''], ['!'], ['!', ''], ['-n'], ['-z', ''], ['a', '=', 'a'], ['(', 'a', ')'], ['(', '!', 'a', ')'],
         ['!', '!', 'a'], ['-l', 'abc', '-eq', '3'], ['3', '-eq', '-l', 'abc'], ['-l', 'ab', '-lt', '-l', 'abc'],
         ['-l', 'a', '-nt', 'b'], ['1', '-eq', '1', '-a', '2', '-gt', '1'], ['(', '1', '-eq', '1', ')', '-o', 'x'],
         ['(', '('], [')'], ['a', '-a'], ['-t', '1'], ['-t', '99999999999999999999'], ['f', '-ef', 'hf'], ['f', '-nt', 'old'],
         ['old', '-ot', 'f'], ['nonexistent', '-ot', 'f'], ['-x', 'dir'], ['--help'], ['--version'], ['-', 'a'], ['a', '-x', 'b']]
rnd = random.Random(3)
CASES = [(f, w) for f in FIXED for w in ('test', '[')]
for _ in range(NRAND):
    args = [rnd.choice(VOCAB) for _ in range(rnd.choice([1, 2, 3, 3, 4, 4, 5, 6, 7]))]
    CASES.append((args, rnd.choice(['test', '['])))


def run(args, which, form):
    if which == 'gnu':
        cmd = ['/usr/bin/' + form] + args + ([']'] if form == '[' else [])
    else:
        cmd = [NEBOX, form] + args + ([']'] if form == '[' else [])
    p = subprocess.run(cmd, cwd=d, env=env, capture_output=True, timeout=20, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(b'/usr/bin/', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    out = p.stdout if not (args and args[0] in ('--help', '--version')) else b''
    return p.returncode if out == p.stdout else 'help', out, err


bad = 0
for args, form in CASES:
    if form == '[' and args in (['--help'], ['--version']):
        continue
    g = run(args, 'gnu', form)
    n = run(args, 'nebox', form)
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH: %s %r' % (form, args))
            print('  gnu:   %r' % (g,))
            print('  nebox: %r' % (n,))
print('test_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
