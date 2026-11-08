#!/usr/bin/env python3
"""Side-by-side test of nebox nproc, sleep and printenv against GNU
coreutils. Usage: tests/smallcore_compare.py path/to/nebox
stdout, diagnostics (minus "Try" lines) and exit status must match."""
import os, subprocess, sys, tempfile, shutil

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='smallcore-compare-')
env = dict(os.environ, LC_ALL='C', A='1', B='x=y', EMPTY='')
CASES = [
    '@nproc', '@nproc --all', '@nproc --ignore=1', '@nproc --ignore=1000', '@nproc --ignore=x', '@nproc --ignore=-1',
    '@nproc --ignore=', '@nproc --ign=2', '@nproc x', '@nproc -x', '@nproc --bogus',
    'OMP_NUM_THREADS=3 @nproc', 'OMP_NUM_THREADS=3 @nproc --all', 'OMP_NUM_THREADS=3,4 @nproc', 'OMP_NUM_THREADS=" 5 " @nproc',
    'OMP_NUM_THREADS=x @nproc', 'OMP_NUM_THREADS=0 @nproc', 'OMP_THREAD_LIMIT=2 @nproc', 'OMP_NUM_THREADS=9 OMP_THREAD_LIMIT=4 @nproc',
    'OMP_THREAD_LIMIT=2 @nproc --all', 'OMP_NUM_THREADS=3 @nproc --ignore=2', 'c=$(taskset -pc $$ | sed "s/.*: //;s/[-,].*//"); taskset -c $c @nproc',
    '@sleep 0', '@sleep 0.01', '@sleep .001', '@sleep 0x0.1p-8', '@sleep 1e-3', '@sleep 0s 0m 0h 0d', '@sleep 0.001s',
    '@sleep 1x', '@sleep x', '@sleep', '@sleep ""', '@sleep -1', '@sleep -- -1', '@sleep --', '@sleep 1ss', '@sleep nan',
    '@sleep 1 x 2', '@sleep " 0"', '@sleep "0 "', '@sleep 0,5', '@sleep 1e999999 & p=$!; sleep 0.2; kill $p; wait $p; echo $?',
    '@sleep inf & p=$!; sleep 0.2; kill $p; wait $p; echo $?', '@sleep infinity & p=$!; sleep 0.2; kill $p; wait $p; echo $?',
    '@sleep 0.2 & p=$!; sleep 0.05; kill -STOP $p; kill -CONT $p; wait $p; echo $?', '@sleep --bogus', '@sleep -x 1',
    '@printenv A', '@printenv B', '@printenv A B', '@printenv A NOPE', '@printenv NOPE', '@printenv EMPTY', '@printenv A=1',
    '@printenv B=x=y', '@printenv -0 A B', '@printenv --null A', '@printenv -0 | tr "\\0" "\\n" | grep -c .',
    '@printenv | grep -c .', '@printenv -i A', '@printenv -u A', '@printenv -x', '@printenv --bogus', '@printenv -- A',
    'env A=2 A=3 @printenv A', '@printenv "" ', '@printenv A > /dev/full; echo $?',
]


def run(cmd, which):
    if which == 'gnu':
        c = cmd.replace('@nproc', 'nproc').replace('@sleep', '/usr/bin/sleep').replace('@printenv', 'printenv')
    else:
        c = cmd.replace('@nproc', NEBOX + ' nproc').replace('@sleep', NEBOX + ' sleep').replace('@printenv', NEBOX + ' printenv')
    p = subprocess.run(['bash', '-c', c], cwd=d, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(b'/usr/bin/', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:400]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:400]))
print('smallcore_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
