#!/usr/bin/env python3
"""Side-by-side test of nebox shuf against GNU coreutils shuf.
Usage: tests/shuf_compare.py path/to/nebox
--random-source makes both deterministic, so outputs are compared byte for
byte, including the reservoir-sampling path (inputs over 8 MiB with -n).
Diagnostics (minus "Try --help"), exit status and files left must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='shuf-compare-')
R = os.path.join(d, 'in')
os.makedirs(R)
rnd = random.Random(1234)
open(os.path.join(R, 'rs'), 'wb').write(bytes(rnd.getrandbits(8) for _ in range(1 << 20)))
open(os.path.join(R, 'rs3'), 'wb').write(b'\x07\xff\x80')
open(os.path.join(R, 'zero'), 'wb').write(b'\0' * 4096)
open(os.path.join(R, 'ones'), 'wb').write(b'\xff' * 4096)
open(os.path.join(R, 'words'), 'w').write('alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\neta\ntheta\niota\nkappa\n')
open(os.path.join(R, 'nonl'), 'w').write('one\ntwo\nthree')
open(os.path.join(R, 'nul'), 'wb').write(b'a\0bb\0ccc\0dddd')
open(os.path.join(R, 'empty'), 'w').write('')
open(os.path.join(R, 'nums'), 'w').write(''.join('%d\n' % i for i in range(1, 5001)))
open(os.path.join(R, 'big'), 'w').write(''.join('row %07d padding padding\n' % i for i in range(380000)))
env = dict(os.environ, LC_ALL='C', R=R)
env.pop('POSIXLY_CORRECT', None)

RS = '--random-source=$R/rs'
CASES = []
for opts in ['', '-n 3', '-n 1', '-n 0', '-n 10', '-n 20', '-r -n 15', '-z', '-n 2 -n 5']:
    CASES += ['@shuf %s %s $R/words' % (RS, opts), '@shuf %s %s $R/nonl' % (RS, opts)]
CASES += [
    '@shuf %s $R/nums | md5sum' % RS, '@shuf %s -n 4000 $R/nums | md5sum' % RS, '@shuf %s -r -n 3000 $R/nums | md5sum' % RS,
    '@shuf %s -n 5 $R/big' % RS, '@shuf %s -n 1000 $R/big | md5sum' % RS, '@shuf %s -n 380000 $R/big | md5sum' % RS,
    '@shuf %s -n 400000 $R/big | md5sum' % RS, 'cat $R/big | @shuf %s -n 5' % RS, '@shuf %s -r -n 5 $R/big' % RS,
    '@shuf %s $R/big | md5sum' % RS,
    '@shuf %s -i 1-10' % RS, '@shuf %s -i 5-5' % RS, '@shuf %s -i 0-0' % RS, '@shuf %s -i 1-0' % RS, '@shuf %s -i 3-1' % RS,
    '@shuf %s -i 1-1000 -n 7' % RS, '@shuf %s -i 1-100000 | md5sum' % RS, '@shuf %s -i 0-4294967295 -n 5' % RS,
    '@shuf %s -i 0-18446744073709551614 -n 5' % RS, '@shuf %s -i 0-18446744073709551615 -n 5' % RS,
    '@shuf %s -i 1-200000 -n 3' % RS, '@shuf %s -i 100-200 -r -n 12' % RS, '@shuf %s -i 1-3 -z' % RS,
    '@shuf %s -i 10' % RS, '@shuf %s -i -5' % RS, '@shuf %s -i 1-x' % RS, '@shuf %s -i x-3' % RS, '@shuf %s -i 1-2-3' % RS,
    '@shuf %s -i 1--3' % RS, '@shuf %s -i " 1- 3"' % RS, '@shuf %s -i +1-+3' % RS, '@shuf -i 1-2 -i 1-2',
    '@shuf %s -e a b c d e f' % RS, '@shuf %s -e' % RS, '@shuf %s -e -n 2 a b c' % RS, '@shuf %s -e -r -n 9 x y' % RS,
    '@shuf %s -e -r' % RS, '@shuf %s -r -n 3 $R/empty' % RS, '@shuf %s $R/empty' % RS, '@shuf %s -z -e a b c' % RS,
    '@shuf %s -z $R/nul' % RS, '@shuf %s -n 2 -z $R/nul' % RS,
    '@shuf --random-source=$R/rs3 -i 1-100', '@shuf --random-source=$R/rs3 -i 1-2', '@shuf --random-source=$R/rs3 $R/words',
    '@shuf --random-source=$R/zero -i 1-1000 -n 5', '@shuf --random-source=$R/ones -i 1-1000 -n 3; echo $?',
    '@shuf --random-source=$R/ones -i 1-256 -n 3', '@shuf --random-source=$R/empty -i 1-5', '@shuf --random-source=$R -i 1-5',
    '@shuf --random-source=/nonexistent -i 1-5', '@shuf --random-source=/nonexistent -n 0 $R/words',
    '@shuf --random-source=/nonexistent -i 1-1', '@shuf --random-source=/nonexistent -r -n 0 -i 1-5',
    '@shuf --random-source=$R/rs --random-source=$R/rs -i 1-5', '@shuf --random-source=$R/rs --random-source=$R/zero -i 1-5',
    '@shuf %s -n x $R/words' % RS, '@shuf %s -n -1 $R/words' % RS, '@shuf %s -n 99999999999999999999999 $R/words' % RS,
    '@shuf %s -n 3k $R/words' % RS, '@shuf %s -e -i 1-3' % RS, '@shuf %s $R/words $R/nonl' % RS, '@shuf %s -i 1-3 extra' % RS,
    '@shuf %s /nonexistent' % RS, '@shuf %s -o out $R/words; cat out' % RS, 'cp $R/words w; @shuf %s -o w w; cat w' % RS,
    '@shuf %s -o out -o out -i 1-3; cat out' % RS, '@shuf -o a -o b -i 1-3', '@shuf %s -o /nodir/x -i 1-3' % RS,
    '@shuf %s - < $R/words' % RS, '@shuf --bogus', '@shuf -q', '@shuf --rand=$R/rs -i 1-4', '@shuf --head=2 %s -i 1-9' % RS,
    '@shuf -i 1-5 | sort -n', '@shuf -e a b c | sort', '@shuf -n 0 -i 1-5', 'seq 50 | @shuf | sort -n | md5sum',
    '@shuf %s -i 1-5 > /dev/full; echo $?' % RS,
]


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    c = cmd.replace('@shuf', (NEBOX + ' shuf') if which == 'nebox' else 'shuf')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(R.encode(), b'R')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err, sorted(os.listdir(wd))


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, (int, list)) else x[:300]))
                print('  %s nebox: %r' % (name, y if isinstance(y, (int, list)) else y[:300]))
print('shuf_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
