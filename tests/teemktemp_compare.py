#!/usr/bin/env python3
"""Side-by-side test of nebox tee and mktemp against GNU coreutils.
Usage: tests/teemktemp_compare.py path/to/nebox
mktemp's random characters are masked (each becomes R) before comparing;
created files' types and modes are compared too. Output, diagnostics
(minus "Try --help") and exit status must match."""
import os, re, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='teemktemp-compare-')
env = dict(os.environ, LC_ALL='C', TMPDIR=os.path.join(d, 'tmpd'))
env.pop('POSIXLY_CORRECT', None)
CASES = [
    'echo hi | @tee a b; cat a b', 'echo hi | @tee -a a; echo there | @tee -a a; cat a', 'echo x | @tee; echo $?',
    'echo hi | @tee - ; ls -- -', 'echo hi | @tee nodir/x; echo $?', 'echo hi | @tee -p nodir/x a; echo $?; cat a',
    'echo hi | @tee --output-error=exit nodir/x a; echo $?; cat a 2>&1', 'echo hi | @tee --output-error=warn nodir/x; echo $?',
    'echo hi | @tee --output-error=w x; echo $?', 'echo hi | @tee --output-error=bogus x; echo $?', 'echo hi | @tee --output-error=exit-n x; echo $?',
    'seq 100000 | @tee a | head -1; echo ${PIPESTATUS[1]}',
    '(seq 100000 | @tee a; echo "tee $?" >&2) | head -1',
    '(seq 100000 | @tee -p a; echo "tee $?" >&2) | head -1',
    '(seq 100000 | @tee --output-error=warn a; echo "tee $?" >&2) | head -1',
    '(seq 100000 | @tee --output-error=exit a; echo "tee $?" >&2) | head -1',
    'echo hi | @tee -i a; cat a', 'echo hi | @tee --bogus', 'echo hi | @tee -x',
    '@mktemp', '@mktemp -d; ls -ld "$TMPDIR"/tmp.* | cut -c1-10', '@mktemp fooXXX', '@mktemp fooXX', '@mktemp foo',
    '@mktemp -u fooXXXX; ls', '@mktemp -p . barXXXXXX', '@mktemp --tmpdir barXXXXXX', '@mktemp --tmpdir=sub barXXX',
    'mkdir sub; @mktemp --tmpdir=sub barXXX', '@mktemp -t bazXXXXXX', 'TMPDIR= @mktemp -t -p . bazXXXXXX',
    '@mktemp -t a/bXXXX', '@mktemp -p . /abs/XXXX', '@mktemp --suffix=.txt fooXXXX', '@mktemp --suffix=.txt foo',
    '@mktemp --suffix=a/b fooXXX', '@mktemp fooXXX.txt', '@mktemp fooXXXbar/x', '@mktemp a b', '@mktemp -q nodir/XXXX; echo $?',
    '@mktemp nodir/XXXX; echo $?', '@mktemp -d nodir/XXXX; echo $?', 'f=$(@mktemp fooXXXXXX); stat -c "%A %s" $f',
    'f=$(@mktemp -d fooXXXXXX); stat -c "%A" $f', '@mktemp -V | head -c 6', '@mktemp XXXXXX/', '@mktemp --dry-run --directory zXXX; ls',
]


def mask(b):
    return re.sub(rb'(tmp\.|foo|bar|baz|z|b)([A-Za-z0-9]{3,})', lambda m: m.group(1) + b'R' * len(m.group(2)), b)


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    os.makedirs(os.path.join(d, 'tmpd'), exist_ok=True)
    for f in os.listdir(os.path.join(d, 'tmpd')):
        p = os.path.join(d, 'tmpd', f)
        shutil.rmtree(p) if os.path.isdir(p) else os.unlink(p)
    c = cmd.replace('@tee', (NEBOX + ' tee') if which == 'nebox' else 'tee')
    c = c.replace('@mktemp', (NEBOX + ' mktemp') if which == 'nebox' else 'mktemp')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(wd.encode(), b'WD')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    out = p.stdout.replace(wd.encode(), b'WD')
    return p.returncode, mask(out), mask(err)


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x[:300]))
                print('  %s nebox: %r' % (name, y[:300]))
print('teemktemp_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
