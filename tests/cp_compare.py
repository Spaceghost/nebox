#!/usr/bin/env python3
"""Side-by-side test of nebox cp against GNU coreutils cp.
Usage: tests/cp_compare.py path/to/nebox
Each case runs on a fresh fixture on tmpfs (modes, hard links, symlinks,
a fifo, sparse and large files, xattrs, fixed old timestamps, unreadable
and unwritable files and directories). stdout, diagnostics and prompts
(minus "Try" lines), exit status and the resulting tree must match: names,
types, permission bits, sizes, contents, link targets, hard-link groups,
user xattrs, allocated blocks of sparse files, and timestamps that predate
the run (new files' times are just "new")."""
import hashlib, os, shutil, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='cp-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C')
for k in ('POSIXLY_CORRECT', 'VERSION_CONTROL', 'SIMPLE_BACKUP_SUFFIX'):
    env.pop(k, None)
SETUP = r"""
umask 022
mkdir -p src/sub/deep dst e
printf hello > src/f; printf world > src/sub/g; printf deep > src/sub/deep/h; : > src/empty
chmod 640 src/f; chmod 4755 src/sub/g; chmod 700 src/sub/deep
ln src/f src/hl; ln -s f src/sl; ln -s ../src/sub src/dl; ln -s nowhere src/dangling; ln -s sub src/sub/self
mkfifo src/fifo
seq 1 60000 > src/big
truncate -s 1M src/sparse; printf data | dd of=src/sparse bs=1 seek=500000 conv=notrunc 2>/dev/null
head -c 65536 /dev/zero > src/zeros
printf old > dst/f; printf old > dst/x; printf old > 'dst/x~'; mkdir dst/d; printf old > dst/hl
printf ro > ro; chmod 444 ro; mkdir rodir; printf q > rodir/q; chmod 555 rodir; printf u > unreadable; chmod 000 unreadable
printf a > a; printf b > b; ln -s a la; ln -s b lb; mkdir -p p/q/r; printf deep > p/q/r/s
touch -d '2020-02-03 04:05:06.789' src/f src/sub/g src/big src/sparse a b
touch -h -d '2019-01-01' src/sl src/dangling; touch -d '2018-03-04' src/sub src/sub/deep src/sub/deep/h src
"""
XATTR = os.access('/dev/shm', os.W_OK)
CUTOFF = time.time() - 3600

CASES = [
    '@cp src/f n', '@cp src/f dst', '@cp src/f dst/f', '@cp src/f src/sub/g dst', '@cp src/f src/sub/g n',
    '@cp src/f', '@cp', '@cp src dst', '@cp -r src dst', '@cp -R src n', '@cp -r src/ n', '@cp -r src/. n',
    '@cp -a src n', '@cp -a src dst', '@cp -av src n', '@cp -rv src n', '@cp -rP src n', '@cp -rL src n',
    '@cp -rH src/dl n', '@cp -rL src/dl n', '@cp -r src/dl n', '@cp src/sl n', '@cp -P src/sl n', '@cp -d src/sl n',
    '@cp src/dangling n', '@cp -P src/dangling n', '@cp -L src/dangling n', '@cp -r src/fifo n',
    '@cp -a src/fifo n', '@cp --copy-contents -r src/f n', '@cp src/sub n', '@cp -p src/f n', '@cp -p src/sub/g n',
    '@cp --preserve src/f n', '@cp --preserve=mode src/f n', '@cp --preserve=timestamps src/f n',
    '@cp --preserve=ownership src/f n', '@cp --preserve=links -r src n', '@cp --preserve=xattr src/f n',
    '@cp --preserve=all src/f n', '@cp --preserve=context src/f n', '@cp --preserve=bogus src/f n',
    '@cp --preserve=mode,timestamps src/f n', '@cp -a --no-preserve=mode src n', '@cp -a --no-preserve=timestamps src/f n',
    '@cp -a --no-preserve=links src n', '@cp --no-preserve=all -a src n', '@cp --no-preserve=mode src/sub/g n',
    '@cp -l src/f n', '@cp -l src/f dst', '@cp -rl src n', '@cp -s src/f n', '@cp -s /etc/hostname n',
    '@cp -s src/f dst/new', '@cp -rs src n', '@cp -sl src/f n', '@cp -n src/f dst/f', '@cp -n src/f dst',
    '@cp -i src/f dst/f < /dev/null', "printf 'y\\n' | @cp -i src/f dst/f", "printf 'n\\n' | @cp -i src/f dst/f",
    "printf 'y\\n' | @cp -i src/f ro", "printf 'y\\n' | @cp -fi src/f ro", "printf 'y\\n' | @cp -i src/f n",
    "printf 'y\\ny\\n' | @cp -i src/f src/sub/g dst", '@cp src/f ro', '@cp -f src/f ro', '@cp --remove-destination src/f ro',
    '@cp src/f rodir/q', '@cp -f src/f rodir/q', '@cp src/f rodir/new', '@cp unreadable n', '@cp -r src rodir',
    '@cp -u src/f dst/f', '@cp -u dst/f src/f', '@cp -u a b', '@cp -u b a', '@cp -uv src/f dst/f', '@cp -ru src dst',
    '@cp -b src/f dst/f', '@cp -bv src/f dst/f', '@cp --backup=numbered src/f dst/f', '@cp --backup=t -v src/f dst/x',
    '@cp --backup=existing -v src/f dst/x', '@cp --backup=simple -S .bak -v src/f dst/f', '@cp -b src/f dst',
    '@cp -fb dst/f dst/f', '@cp -fbv a a', '@cp -b a a', '@cp a a', '@cp a ./a', '@cp -f a a', '@cp la a',
    '@cp -P la a', '@cp -P la lb', '@cp --backup=simple dst/x~ dst/x', '@cp -bn src/f dst', '@cp -v src/f src/f dst',
    '@cp src/f src/./f dst', '@cp -r src src dst', '@cp -t dst src/f src/sub/g', '@cp -t nodir src/f',
    '@cp -t src/f a', '@cp -t dst -t e a', '@cp -T src/f dst', '@cp -T src dst', '@cp -rT src dst', '@cp -T a b extra',
    '@cp -T -t dst a', '@cp a b nodir', '@cp a b c', '@cp a nodir/x', '@cp a dst/', '@cp a n/', '@cp -r src n/',
    '@cp --parents src/sub/g dst', '@cp --parents -v src/sub/deep/h dst', '@cp --parents -p src/sub/deep/h dst',
    '@cp --parents -a src/sub dst', '@cp --parents src/f n', '@cp --parents ./src/f dst', '@cp --parents src/f/ dst',
    '@cp --parents p/q/r/s dst', '@cp --parents -r p dst', '@cp --strip-trailing-slashes -r src/ n',
    '@cp --sparse=always src/sparse n', '@cp --sparse=never src/sparse n', '@cp --sparse=auto src/sparse n',
    '@cp --sparse=always src/zeros n', '@cp --sparse=bogus src/f n', '@cp src/sparse n', '@cp --reflink src/f n',
    '@cp --reflink=always src/f n', '@cp --reflink=never src/big n', '@cp --reflink=auto src/big n',
    '@cp --reflink --sparse=never src/f n', '@cp --attributes-only src/f dst/f', '@cp --attributes-only -p src/f n',
    '@cp -x -r src n', '@cp -Z src/f n', '@cp --context=x src/f n', '@cp --bogus', '@cp -q a b', '@cp --verb a n',
    '@cp -rv src/sub dst/d', '@cp -r src/sub/self n', '@cp -rL src/sub n', '@cp -r src/sub src/sub/deep',
    '@cp -r src src/sub', '@cp -r src src', '@cp -r . dst', 'cd src/sub && @cp -r .. ../../n', '@cp -rv p p/q', '@cp src/big n',
    '@cp -v a n > /dev/full; echo $?', 'chmod 0 src/sub/deep; @cp -r src n; chmod 700 src/sub/deep',
    '@cp -r src/sub/deep n; ls n', 'mkdir n; @cp -r src/sub n; @cp -r src/sub n', '@cp a dst/d', '@cp -r src/sub dst/f',
    'ln -s n dlink; @cp a dlink', 'ln -s n dlink; POSIXLY_CORRECT=1 @cp a dlink', '@cp -l src/sub n',
    '@cp -rl src/sub n', '@cp -H src/sl n', '@cp -rd src n', '@cp -a src/hl src/f dst', '@cp -d src/hl src/f dst',
    '@cp --preserve=links src/hl src/f dst', '@cp src/hl src/f dst', '@cp -R --link src/sub n',
]
if XATTR:
    CASES += ['setfattr_ok=1; python3 -c "import os; os.setxattr(\'src/f\', \'user.k\', b\'v\')" && @cp --preserve=xattr src/f n',
              'python3 -c "import os; os.setxattr(\'src/f\', \'user.k\', b\'v\')" && @cp -a src/f n',
              'python3 -c "import os; os.setxattr(\'src/f\', \'user.k\', b\'v\')" && @cp src/f n',
              'python3 -c "import os; os.setxattr(\'src/sub\', \'user.d\', b\'w\')" && @cp -a src n']


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
                out.append('%s -> %s %s' % (rel, os.readlink(p), mt))
                continue
            try:
                xa = sorted((k, os.getxattr(p, k)) for k in os.listxattr(p) if k.startswith('user.'))
            except OSError:
                xa = []
            line = '%s %o %d:%d %s %s' % (rel, st.st_mode, st.st_uid, st.st_gid, mt, xa)
            if os.path.isfile(p):
                try:
                    data = open(p, 'rb').read()
                    line += ' %d %s' % (len(data), hashlib.sha1(data).hexdigest()[:10])
                except OSError:
                    line += ' unreadable'
                if 'sparse' in n or 'zeros' in n:
                    line += ' blocks=%d' % st.st_blocks
                groups.setdefault(st.st_ino, []).append(rel)
            out.append(line)
    for g in groups.values():
        if len(g) > 1:
            out.append('hardlinks ' + ' '.join(sorted(g)))
    return '\n'.join(sorted(out)).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        subprocess.run(['chmod', '-R', 'u+rwx', wd])
        shutil.rmtree(wd)
    os.makedirs(wd)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True)
    c = cmd.replace('@cp', (NEBOX + ' cp') if which == 'nebox' else 'cp')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    subprocess.run(['chmod', '-R', 'u+rwx', wd])
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    snap = snapshot(wd)
    return p.returncode, p.stdout, err, snap


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
print('cp_compare: %d cases, %d mismatches (uid %d)' % (len(CASES), bad, os.getuid()))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d)
sys.exit(1 if bad else 0)
