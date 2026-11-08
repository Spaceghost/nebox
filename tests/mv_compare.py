#!/usr/bin/env python3
"""Side-by-side test of nebox mv against GNU coreutils mv.
Usage: tests/mv_compare.py path/to/nebox
Each case runs on a fresh fixture on tmpfs with a second directory, $FAR,
on another file system when one is available (cross-device moves copy and
then remove the source). stdout, diagnostics and prompts (minus "Try"
lines), exit status and both trees must match: names, types, modes,
sizes, contents, link targets, hard-link groups and pre-existing
timestamps."""
import hashlib, os, shutil, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='mv-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
far_root = tempfile.mkdtemp(prefix='mv-compare-far-', dir='/var/tmp' if os.access('/var/tmp', os.W_OK) else None)
CROSS = os.stat(d).st_dev != os.stat(far_root).st_dev
env = dict(os.environ, LC_ALL='C')
for k in ('POSIXLY_CORRECT', 'VERSION_CONTROL', 'SIMPLE_BACKUP_SUFFIX'):
    env.pop(k, None)
SETUP = r"""
umask 022
mkdir -p src/sub/deep dst/d e
printf hello > src/f; printf world > src/sub/g; printf deep > src/sub/deep/h
chmod 640 src/f; chmod 4755 src/sub/g
ln src/f src/hl; ln -s f src/sl; ln -s nowhere src/dangling; mkfifo src/fifo
printf a > a; printf b > b; ln -s a la; ln -s b lb; printf c > c
printf old > dst/f; printf old > dst/x; printf old > 'dst/x~'; mkdir dst/nonempty; printf q > dst/nonempty/q
printf ro > ro; chmod 444 ro; mkdir rodir; printf q > rodir/q; chmod 555 rodir; mkdir emptyd
touch -d '2020-02-03 04:05:06.789' src/f src/sub/g a b c; touch -d '2018-03-04' src/sub src/sub/deep src
"""
CUTOFF = time.time() - 3600
CASES = [
    '@mv a n', '@mv a b', '@mv a dst', '@mv a b dst', '@mv a b n', '@mv a', '@mv', '@mv src n', '@mv src dst',
    '@mv src dst/d', '@mv src/ n', '@mv src/f n/', '@mv a dst/f', '@mv -v a b', '@mv -v a dst', '@mv -v src n',
    '@mv -f a ro', '@mv a ro < /dev/null', "printf 'y\\n' | @mv -i a b", "printf 'n\\n' | @mv -i a b",
    "printf 'y\\n' | @mv -i a ro", "printf 'n\\n' | @mv -i a ro", '@mv -n a b', '@mv -n a n', '@mv -nf a b',
    '@mv -fn a b', '@mv -fi a b < /dev/null', '@mv -u a b', '@mv -u b a', 'touch -d 2030-01-01 b; @mv -u a b',
    '@mv -uv a b', '@mv -b a b', '@mv -bv a b', '@mv --backup=numbered -v a dst/x', '@mv --backup=t a dst/f',
    '@mv -S .bak -v a b', '@mv -b a a', '@mv a a', '@mv a ./a', '@mv la a', '@mv la lb', '@mv -b la lb',
    '@mv src/hl src/f', '@mv src/f src/hl', '@mv src/sl src/f', '@mv -b src/sl src/f', '@mv --backup=simple dst/x~ dst/x',
    '@mv src src/sub', '@mv src src/sub/deep/n', '@mv src .', '@mv . n', '@mv .. n', '@mv src/sub/deep src',
    '@mv src dst/f', '@mv a dst/nonempty', '@mv emptyd dst/nonempty', '@mv emptyd dst/d', '@mv -v emptyd dst/d',
    '@mv -T a dst', '@mv -T emptyd dst/d', '@mv -T src dst', '@mv -T a b c', '@mv -t dst a b', '@mv -t nodir a',
    '@mv -t a b', '@mv -t dst -t e a', '@mv -T -t dst a', '@mv a b nodir', '@mv a b c', '@mv a nodir/x',
    '@mv nonexistent n', '@mv nonexistent a dst', '@mv a rodir', '@mv rodir/q n', '@mv src/fifo n',
    '@mv --strip-trailing-slashes src/ n', '@mv --strip-trailing-slashes a/ n', '@mv a/ n', '@mv -bn a b',
    '@mv -Z a n', '@mv --context a n', '@mv --bogus', '@mv -q a b', '@mv --verb a n', '@mv --backup=bogus a b',
    '@mv -v a n > /dev/full; echo $?', '@mv a a dst', '@mv -v a b c dst', 'ln a dst/a; @mv a dst',
    'ln -s dst lnd; @mv a lnd', 'ln -s dst lnd; @mv a lnd/', 'mkdir -p n/src; printf z > n/src/z; @mv src n',
    'mkdir -p n/src; @mv src n', '@mv src/sub src/sub/deep/x',
]
if CROSS:
    CASES += [
        '@mv a $FAR', '@mv -v a $FAR', '@mv a $FAR/n', '@mv -v src $FAR', '@mv src $FAR/n', '@mv -v src/sub $FAR',
        '@mv src/sl src/dangling src/fifo src/hl src/f $FAR', '@mv -v src/hl src/f $FAR', '@mv a b $FAR',
        'cp -a src $FAR/src; @mv src $FAR', 'mkdir $FAR/src; @mv -v src $FAR', 'printf x > $FAR/a; @mv -v a $FAR',
        "printf x > $FAR/a; printf 'n\\n' | @mv -i a $FAR", 'printf x > $FAR/a; @mv -bv a $FAR', '@mv -u a $FAR',
        'printf x > $FAR/a; touch -d 2030-01-01 $FAR/a; @mv -uv a $FAR', 'chmod 0 src/sub/deep; @mv src $FAR; chmod -R u+rwx src $FAR',
        '@mv rodir $FAR', 'chmod 755 rodir; chmod 444 rodir/q; @mv rodir $FAR', '@mv $FAR/../nonexistent a',
        'printf q > $FAR/q; @mv -v $FAR/q .', 'mkdir $FAR/dir; printf q > $FAR/dir/q; @mv -v $FAR/dir .',
    ]


def snapshot(root):
    out = []
    groups = {}
    for dp, dns, fns in os.walk(root):
        for n in sorted(dns + fns):
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            mt = st.st_mtime_ns if st.st_mtime < CUTOFF else 'new'
            if os.path.islink(p):
                out.append('%s -> %s' % (rel, os.readlink(p)))
                continue
            line = '%s %o %s' % (rel, st.st_mode, mt)
            if os.path.isfile(p):
                try:
                    data = open(p, 'rb').read()
                    line += ' %d %s' % (len(data), hashlib.sha1(data).hexdigest()[:10])
                except OSError:
                    line += ' unreadable'
                groups.setdefault(st.st_ino, []).append(rel)
            out.append(line)
    for g in groups.values():
        if len(g) > 1:
            out.append('hardlinks ' + ' '.join(sorted(g)))
    return '\n'.join(sorted(out)).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    far = os.path.join(far_root, which)
    for p in (wd, far):
        if os.path.exists(p):
            subprocess.run(['chmod', '-R', 'u+rwx', p])
            shutil.rmtree(p)
        os.makedirs(p)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True)
    c = cmd.replace('@mv', (NEBOX + ' mv') if which == 'nebox' else 'mv')
    e = dict(env, FAR=far)
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=e, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    for q in (wd, far):
        subprocess.run(['chmod', '-R', 'u+rwx', q])
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(far.encode(), b'$FAR')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    out = p.stdout.replace(far.encode(), b'$FAR')
    return p.returncode, out, err, snapshot(wd) + b'\n--far--\n' + snapshot(far)


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, n):
            if x != y:
                if name == 'files':
                    xs, ys = set(x.split(b'\n')), set(y.split(b'\n'))
                    print('  files gnu only:   %r' % sorted(xs - ys)[:8])
                    print('  files nebox only: %r' % sorted(ys - xs)[:8])
                else:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:700]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:700]))
print('mv_compare: %d cases, %d mismatches (cross-device: %s, uid %d)' % (len(CASES), bad, CROSS, os.getuid()))
for p in (d, far_root):
    subprocess.run(['chmod', '-R', 'u+rwx', p])
    shutil.rmtree(p)
sys.exit(1 if bad else 0)
