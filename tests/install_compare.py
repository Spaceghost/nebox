#!/usr/bin/env python3
"""Side-by-side test of nebox install against GNU coreutils install.
Usage: tests/install_compare.py path/to/nebox
Each case runs on a fresh fixture on tmpfs; stdout, diagnostics (minus
"Try" lines), exit status and the resulting tree (names, types, modes,
owners, sizes, contents, link targets, pre-existing timestamps) must
match. Run as root, -o/-g really change ownership."""
import grp, hashlib, os, pwd, shutil, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='install-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C')
for k in ('POSIXLY_CORRECT', 'VERSION_CONTROL', 'SIMPLE_BACKUP_SUFFIX'):
    env.pop(k, None)
ME = pwd.getpwuid(os.getuid()).pw_name
MG = grp.getgrgid(os.getgid()).gr_name
SETUP = r"""
umask 022
mkdir -p src dst/d ro
printf hello > src/f; printf world > src/g; printf exe > src/x; chmod 755 src/x; ln -s f src/sl
printf old > dst/f; printf old > dst/g; printf hello > dst/same; chmod 755 dst/same; printf old > 'dst/f~'
printf 'printf stripped > "$1"\n' > stripper; chmod 755 stripper; printf 'exit 3\n' > badstrip; chmod 755 badstrip
chmod 555 ro; printf z > afile
touch -d '2020-02-03 04:05:06.789' src/f src/g src/x
"""
CUTOFF = time.time() - 3600
CASES = [
    '@install src/f n', '@install src/f dst', '@install src/f dst/f', '@install src/f src/g dst', '@install src/f src/g n',
    '@install src/f', '@install', '@install -v src/f n', '@install -v src/f src/g dst', '@install -m 644 src/f n',
    '@install -m 4755 src/f n', '@install -m u=rw,go=r src/f n', '@install -m a+x src/f n', '@install -m bogus src/f n',
    '@install -m 0 src/f n', '@install -m 1777 src/f n', '@install --mode=600 src/x n', '@install -p src/f n',
    '@install -p -m 600 src/x n', '@install -C src/f dst/same', '@install -C -m 755 src/f dst/same', '@install -Cv src/f dst/same',
    '@install -C src/f dst/f', '@install -C -m 4755 src/f dst/same', '@install -C -p src/f n', '@install -C -s src/f n',
    '@install -b src/f dst/f', '@install -bv src/f dst/f', '@install --backup=numbered -v src/f dst/f',
    '@install -S .bak -v src/f dst/f', '@install --backup=bogus src/f dst/f', '@install -c src/f n',
    '@install -d n', '@install -d n/a/b', '@install -dv n/a/b', '@install -d -m 700 n/a/b', '@install -d -m 2775 n',
    '@install -d dst/d', '@install -dv dst/d dst/new', '@install -d afile', '@install -d afile/x', '@install -d ro/x',
    '@install -d -m 755 dst', '@install -d', '@install -d -t dst n', '@install -d -s n', '@install -dv ./n/./m//k',
    '@install -dv n/../m', '@install -D src/f n/a/b', '@install -Dv src/f n/a/b', '@install -D src/f dst/f',
    '@install -Dv -t n/a src/f src/g', '@install -D -t n src/f', '@install -D src/f afile/x', '@install -D src/f ro/a/b',
    '@install -t dst src/f src/g', '@install -t nodir src/f', '@install -t dst -t n src/f', '@install -T src/f dst',
    '@install -T src/f dst/new', '@install -T src/f a b', '@install -T -t dst src/f', '@install src/f nodir/x',
    '@install src/f src/g nodir', '@install src nodest', '@install src/sl n', '@install nonexistent n',
    '@install src/f ro/f', '@install /dev/null n', '@install -m 644 /dev/null n',
    '@install -s --strip-program=./stripper src/f n', '@install -sv --strip-program=./stripper src/f n',
    '@install -s --strip-program=./badstrip src/f n', '@install -s --strip-program=./nonexistent src/f n',
    '@install -s --strip-program=true -p src/f n', '@install --strip-program=./stripper src/f n',
    '@install -o %s src/f n' % ME, '@install -g %s src/f n' % MG, '@install -o %s -g %s src/f n' % (ME, MG),
    '@install -o %d src/f n' % os.getuid(), '@install -o nosuchuser src/f n', '@install -g nosuchgroup src/f n',
    '@install -o 4294967296 src/f n', '@install -o 0x10 src/f n', '@install -o root src/f n', '@install -g root src/f n',
    '@install -d -o root n', '@install -d -g %s -m 2770 n' % MG, '@install -Z src/f n', '@install --context=x src/f n',
    '@install --preserve-context src/f n', '@install --bogus', '@install -q src/f n', '@install --verb src/f n',
    '@install -v src/f n > /dev/full; echo $?', '@install src/f src/f', '@install src/f ./src/f',
    'ln -s n lnk; @install src/f lnk', 'ln -s nowhere lnk; @install src/f lnk', '@install src/f dst/d',
]


def snapshot(root):
    out = []
    for dp, dns, fns in os.walk(root):
        for n in sorted(dns + fns):
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            mt = st.st_mtime_ns if st.st_mtime < CUTOFF else 'new'
            if os.path.islink(p):
                out.append('%s -> %s' % (rel, os.readlink(p)))
                continue
            line = '%s %o %d:%d %s' % (rel, st.st_mode, st.st_uid, st.st_gid, mt)
            if os.path.isfile(p):
                data = open(p, 'rb').read()
                line += ' %d %s' % (len(data), hashlib.sha1(data).hexdigest()[:10])
            out.append(line)
    return '\n'.join(sorted(out)).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        subprocess.run(['chmod', '-R', 'u+rwx', wd])
        shutil.rmtree(wd)
    os.makedirs(wd)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True)
    c = cmd.replace('@install', (NEBOX + ' install') if which == 'nebox' else 'install')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    subprocess.run(['chmod', '-R', 'u+rwx', wd])
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
                if name == 'files':
                    xs, ys = set(x.split(b'\n')), set(y.split(b'\n'))
                    print('  files gnu only:   %r' % sorted(xs - ys)[:8])
                    print('  files nebox only: %r' % sorted(ys - xs)[:8])
                else:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:700]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:700]))
print('install_compare: %d cases, %d mismatches (uid %d)' % (len(CASES), bad, os.getuid()))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d)
sys.exit(1 if bad else 0)
