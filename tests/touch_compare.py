#!/usr/bin/env python3
"""Side-by-side test of nebox touch against GNU coreutils touch.
Usage: tests/touch_compare.py path/to/nebox
Each case runs on a fresh fixture on tmpfs with TZ=UTC0; stdout,
diagnostics (minus "Try" lines), exit status and every entry's existence,
mode, atime and mtime (nanoseconds) must match. Cases whose times depend
on the moment they run (now, relative dates) compare times to the minute,
or as "new" when they are within the last day."""
import os, shutil, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='touch-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C', TZ='UTC0')
for k in ('POSIXLY_CORRECT', '_POSIX2_VERSION'):
    env.pop(k, None)
SETUP = r"""
printf x > f; printf y > g; ln -s f sl; ln -s nowhere dangling; mkdir dir; printf r > ro; chmod 444 ro
mkdir rodir; chmod 555 rodir
touch -d '2001-02-03 04:05:06.123456789' f g dir ro; touch -h -d '1999-12-31 23:59:59' sl dangling
"""
CASES = [
    '@touch -t 202001020304 n', '@touch -t 202001020304.05 n', '@touch -t 2001020304 n', '@touch -t 01020304 n',
    '@touch -t 7001020304 n', '@touch -t 6901020304 n', '@touch -t 1901020304 n', '@touch -t 202002300000 n',
    '@touch -t 202013010000 n', '@touch -t 202001012460 n', '@touch -t 201612312359.60 n', '@touch -t 202001010000.60 n',
    '@touch -t 2020010100 n', '@touch -t 20200101000 n', '@touch -t 202001010000.5 n', '@touch -t 202001010000.ab n',
    '@touch -t 2020010100001 n', '@touch -t abcd n', '@touch -t "" n', '@touch -t 202001020304.05.06 n',
    '@touch -d "2020-01-02 03:04:05" n', '@touch -d "2020-01-02 03:04:05.987654321" n', '@touch -d @0 n',
    '@touch -d @-1 n', '@touch -d @1234567890.5 n', '@touch -d "1970-01-01 00:00:00 UTC" n', '@touch -d "bogus date" n',
    '@touch -d "2020-02-30" n', '@touch -d "12/25/2019" n', '@touch -d "25 Dec 2019 10:00" n', '@touch -d "2019-12-25T10:00:00Z" n',
    '@touch -d "Dec 25, 2019 3pm" n', '@touch -d 17-jun-1992 n', '@touch -d jun-17-1992 n', '@touch -d 20190704 n',
    '@touch -d "sept. 3 2001" n', '@touch -d "jan. 5 2020 11:30pm" n', '@touch -d "3 feb 99" n', '@touch -d "Dec 25 2019 13pm" n',
    '~@touch -d 2019 n', '~@touch -d 1530 n', '~@touch -d "dec 25 19" n', '~@touch -d "3 pm" n',
    '@touch -r f n', '@touch -r sl n', '@touch -h -r sl n', '@touch -r nonexistent n', '@touch -r f -d "+1 day" n',
    '@touch -r f -d "-2 hours" g', '@touch -a -r f -d "1 day ago" g', '@touch -m -r f -d "+1 week" g',
    '@touch -r f -t 202001010000 n', '@touch -d now -t 202001010000 n', '@touch -a -t 202001010000 f',
    '@touch -m -t 202001010000 f', '@touch -am -t 202001010000 f', '@touch --time=atime -t 202001010000 f',
    '@touch --time=access -t 202001010000 f', '@touch --time=use -t 202001010000 f', '@touch --time=mtime -t 202001010000 f',
    '@touch --time=modify -t 202001010000 f', '@touch --time=bogus f', '@touch --time=a f', '@touch --time= f',
    '@touch -c -t 202001010000 n', '@touch -c -t 202001010000 f', '@touch -h -t 202001010000 sl', '@touch -h -t 202001010000 dangling',
    '@touch -t 202001010000 dangling', '@touch -c -t 202001010000 dangling', '@touch -h -t 202001010000 n',
    '@touch -t 202001010000 dir', '@touch -t 202001010000 ro', '@touch -t 202001010000 rodir/n', '@touch -c -t 202001010000 rodir/n',
    '@touch -t 202001010000 nodir/n', '@touch -t 202001010000 - > out; ls out', '@touch -t 202001010000 f g n',
    '@touch -f -t 202001010000 n', '@touch', '@touch -t 202001010000', '@touch --bogus f', '@touch -q f',
    '@touch --no-create -t 202001010000 n', '@touch --date=@86400 n', '@touch --reference=f n', '@touch --no-deref -t 202001010000 sl',
    '_POSIX2_VERSION=199209 @touch 01020304 f', '_POSIX2_VERSION=199209 @touch 0102030405 f', '_POSIX2_VERSION=199209 @touch 01020304 f g',
    '_POSIX2_VERSION=199209 POSIXLY_CORRECT=1 @touch 0102030469 f', '_POSIX2_VERSION=199209 @touch 0102030468 f',
    '_POSIX2_VERSION=200112 @touch 01020304 f', '@touch 01020304 f', '_POSIX2_VERSION=199209 @touch -d @5 01020304 f',
    '_POSIX2_VERSION=x @touch 01020304 f', '_POSIX2_VERSION=199209 @touch 01020304',
    '~@touch n', '~@touch f', '~@touch -a f', '~@touch -m f', '~@touch -d now f', '~@touch -a -d now f',
    '~@touch -d "1 day ago" n', '~@touch -d tomorrow n', '~@touch -d "next monday" n', '~@touch -c n f',
    '~@touch ro', '~@touch rodir/x', '~@touch dir', '~@touch -h sl', '~@touch sl', '~@touch - > out',
]


def snapshot(root, coarse):
    out = []
    now = time.time()
    for n in sorted(os.listdir(root)):
        p = os.path.join(root, n)
        st = os.lstat(p)
        def t(ns):
            if abs(now - ns / 1e9) < 86400:
                return 'new'
            return ns // 60000000000 if coarse else ns
        out.append('%s %o %s %s' % (n, st.st_mode, t(st.st_atime_ns), t(st.st_mtime_ns)))
    return '\n'.join(out).encode()


def run(cmd, which):
    coarse = cmd.startswith('~')
    cmd = cmd.lstrip('~')
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        subprocess.run(['chmod', '-R', 'u+rwx', wd])
        shutil.rmtree(wd)
    os.makedirs(wd)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True, env=env)
    c = cmd.replace('@touch', (NEBOX + ' touch') if which == 'nebox' else 'touch')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    subprocess.run(['chmod', '-R', 'u+rwx', wd])
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err, snapshot(wd, coarse)


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:600]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:600]))
print('touch_compare: %d cases, %d mismatches (uid %d)' % (len(CASES), bad, os.getuid()))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d)
sys.exit(1 if bad else 0)
