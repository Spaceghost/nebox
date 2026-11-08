#!/usr/bin/env python3
"""Side-by-side test of nebox truncate against GNU coreutils truncate.
Usage: tests/truncate_compare.py path/to/nebox
Fresh fixture per case on tmpfs; stdout, diagnostics (minus "Try"
lines), exit status and every file's size and contents must match."""
import hashlib, os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='truncate-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C')
SETUP = r"""
head -c 1000 /dev/zero | tr '\0' a > f; head -c 5000 /dev/zero | tr '\0' b > g; : > e; mkdir dir
printf ro > ro; chmod 444 ro; mkfifo fifo; ln -s f lf; ln -s nowhere dangling
"""
SIZES = ['0', '10', '1000', '+10', '-10', '-5000', '<100', '<5000', '>100', '>5000', '/300', '%300', '/1000', '%1000',
         '1K', '1KB', '1KiB', 'k', '2m', '1G', '0x10', '010', '1x', '', ' 5', '+', '-', '< 7', '<+7', '+-7', '/0', '%0',
         '%-7', '/-300', '9223372036854775807', '9223372036854775808', '-9223372036854775808', '-9223372036854775809',
         '8E', '7E', '1Y', ' +5', '>-1', '%1', '/1']
CASES = []
for s in SIZES:
    CASES += ["@truncate -s '%s' f g e n" % s, "@truncate -o -s '%s' f" % s, "@truncate -c -s '%s' n f" % s]
CASES += [
    '@truncate f', '@truncate -s 5', '@truncate', '@truncate -r g f', '@truncate -r g -s +10 f', '@truncate -r g -s 10 f',
    '@truncate -r g -s %300 f', '@truncate -r nonexistent f', '@truncate -r dir f', '@truncate -o f',
    '@truncate -o -r g f', '@truncate -s 0 dir', '@truncate -s 0 dir/', '@truncate -s 0 nodir/x', '@truncate -s 0 n/',
    '@truncate -c -s 0 nodir/x', '@truncate -s 0 ro', '@truncate -s 0 lf', '@truncate -s 10 dangling', '@truncate -s 0 fifo',
    '@truncate -s 10 /dev/null', '@truncate --size=10 --no-create f n', '@truncate --io-blocks --size=1 f',
    '@truncate --reference=g f', '@truncate --bogus', '@truncate -q f', '@truncate --si=1 f', '@truncate -s 1 -s 2 f',
    '@truncate -o -s 3E f', '@truncate -o -s -2 f', '@truncate -s +9223372036854775807 g', '@truncate -s %9223372036854775807 g',
]


def snapshot(root):
    out = []
    for n in sorted(os.listdir(root)):
        p = os.path.join(root, n)
        st = os.lstat(p)
        line = '%s %o %d' % (n, st.st_mode, st.st_size)
        if os.path.isfile(p) and not os.path.islink(p) and st.st_size < (8 << 20):
            line += ' ' + hashlib.sha1(open(p, 'rb').read()).hexdigest()[:10]
        out.append(line)
    return '\n'.join(out).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True)
    c = cmd.replace('@truncate', (NEBOX + ' truncate') if which == 'nebox' else 'truncate')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err, snapshot(wd)


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:500]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:500]))
print('truncate_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
