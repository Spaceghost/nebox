#!/usr/bin/env python3
"""Side-by-side test of nebox timeout against GNU timeout.
Usage: tests/timeout_compare.py path/to/nebox
Exit statuses (124 to 127, 128+N, --preserve-status), -s and -k, the
process group (a grandchild is signalled too unless --foreground), signals
sent to timeout itself, a command killed by a signal (timeout re-raises
it), -v messages and option errors. Output, diagnostics (minus "Try
--help") and exit status must match."""
import os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='timeout-compare-')
CASES = [
    '@timeout 5 true; echo $?', '@timeout 5 false; echo $?', '@timeout 5 sh -c "exit 42"; echo $?',
    '@timeout 0.3 sleep 3; echo $?', '@timeout 0.3s sleep 3; echo $?', '@timeout 0.005m sleep 3; echo $?',
    '@timeout -s KILL 0.3 sleep 3; echo $?', '@timeout -s 9 0.3 sleep 3; echo $?', '@timeout -s SIGINT 0.3 sleep 3; echo $?',
    '@timeout -s int 0.3 sleep 3; echo $?', '@timeout -s 137 0.3 sleep 3; echo $?', '@timeout -s HUP 0.3 sleep 3; echo $?',
    '@timeout --preserve-status 0.3 sleep 3; echo $?', '@timeout --preserve-status -s KILL 0.3 sleep 3; echo $?',
    '@timeout -k 0.3 0.3 sh -c "trap \\"\\" TERM; sleep 3"; echo $?',
    '@timeout -v 0.3 sleep 3; echo $?', '@timeout -v -k 0.3 0.3 sh -c "trap \\"\\" TERM; sleep 3"; echo $?',
    '@timeout 0 sh -c "sleep 0.3; exit 3"; echo $?', '@timeout 5 nosuchcmd; echo $?', '@timeout 5 /etc/passwd; echo $?',
    '@timeout 5; echo $?', '@timeout; echo $?', '@timeout x true; echo $?', '@timeout -5 true; echo $?', '@timeout 1x true; echo $?',
    '@timeout 1ss true; echo $?', '@timeout -s FOO 1 true; echo $?', '@timeout -s 99 1 true; echo $?', '@timeout -k x 1 true; echo $?',
    '@timeout --bogus 1 true; echo $?', '@timeout -p 1 true; echo $?', '@timeout 1 -s KILL true; echo $?',
    '@timeout 5 sh -c "kill -USR1 \\$\\$"; echo $?', '@timeout 5 sh -c "kill -TERM \\$\\$"; echo $?',
    '@timeout 5 sh -c "kill -KILL \\$\\$"; echo $?',
    # the whole group is signalled: a background grandchild dies too
    'rm -f mark; @timeout 0.5 sh -c "(sleep 1.5; touch mark) & sleep 3"; echo $?; sleep 1.5; ls mark 2>&1',
    'rm -f mark; @timeout --foreground 0.5 sh -c "(sleep 1.5; touch mark) & sleep 3"; echo $?; sleep 1.5; ls mark 2>&1',
    # a signal sent to timeout is passed on
    '(@timeout 5 sleep 3 & p=$!; sleep 0.3; kill -TERM $p; wait $p; echo $?)',
    '(@timeout 5 sh -c "trap \\"echo got HUP; exit 7\\" HUP; sleep 3 & wait" & p=$!; sleep 0.3; kill -HUP $p; wait $p; echo $?)',
    '@timeout 5 sh -c "echo out; echo err >&2"; echo $?',
    '@timeout 1e-1 sleep 3; echo $?', '@timeout .2 sleep 3; echo $?', '@timeout 0x1 true; echo $?', '@timeout inf true; echo $?',
]


def run(cmd, which):
    c = cmd.replace('@timeout', (NEBOX + ' timeout') if which == 'nebox' else 'timeout')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
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
                print('  %s gnu:   %r' % (name, x))
                print('  %s nebox: %r' % (name, y))
print('timeout_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
