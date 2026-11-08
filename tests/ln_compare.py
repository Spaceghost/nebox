#!/usr/bin/env python3
"""Side-by-side test of nebox ln against GNU coreutils ln.
Usage: tests/ln_compare.py path/to/nebox
Each case runs on a fresh fixture; stdout, diagnostics (minus "Try"
lines), exit status and the resulting tree (names, types, link targets,
hard-link groups and contents) must match."""
import os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='ln-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C')
for k in ('POSIXLY_CORRECT', 'VERSION_CONTROL', 'SIMPLE_BACKUP_SUFFIX'):
    env.pop(k, None)

SETUP = r"""
mkdir -p dir/sub other deep/a/b
printf A > a; printf B > b; printf C > c; printf X > dir/x; printf O > other/a
ln -s a sa; ln -s dir sdir; ln -s nowhere dangling; ln a hl
printf old > old; printf 1 > 'old.~1~'; printf 9 > 'old.~9~'; printf z > bk; printf z > 'bk.~99~'
printf q > 'sp ace'; mkdir 'dir/a'
"""

CASES = [
    '@ln a n', '@ln -s a n', '@ln a', '@ln -s deep/a/b', '@ln a b', '@ln -f a b', '@ln -s a b', '@ln -sf a b',
    '@ln a dir', '@ln a b c dir', '@ln a b dir/sub', '@ln -s a b c dir', '@ln -t dir a b', '@ln -t dir', '@ln -t nodir a',
    '@ln -t a b', '@ln -t dir -t other a', '@ln -T a dir', '@ln -T a newname', '@ln -T a', '@ln -T a b c', '@ln -T -t dir a b',
    '@ln', '@ln -s', '@ln nonexistent n', '@ln -s nonexistent n', '@ln dir n', '@ln -d dir n', '@ln -F dir n',
    '@ln a sdir', '@ln -n a sdir', '@ln -nf a sdir', '@ln -sn a sdir', '@ln -snf a sdir', '@ln -snf b sa',
    '@ln a dir/a', '@ln -f a dir/a', '@ln a dir/sub/', '@ln -s a dir//', '@ln -s a/ n', '@ln b/ n', '@ln -s b dir/sub///',
    '@ln -v a n', '@ln -sv a n', '@ln -sfv b a', '@ln -fv b a', '@ln -v a b c dir', '@ln -sv ../a dir/up',
    '@ln -f a a', '@ln -f a ./a', '@ln -f a hl', '@ln -f hl a', '@ln -sf a a', '@ln -sfn a a', '@ln -s a a',
    '@ln -fb a hl', '@ln -b a b', '@ln -bv a b', '@ln -b a newn', '@ln -S .bak a b', '@ln -S .bak -v a b',
    '@ln --suffix=x/y -b a b', '@ln --backup=numbered a old', '@ln --backup=t -v a old', '@ln --backup=existing a old',
    '@ln --backup=nil -v a b', '@ln --backup=simple a old', '@ln --backup=never -v a old', '@ln --backup=none a b',
    '@ln --backup=off -f a b', '@ln --backup=bogus a b', '@ln --backup=n a b', '@ln --backup=nu -v a old',
    '@ln --backup=numbered -v a bk', 'VERSION_CONTROL=numbered @ln -bv a old', 'VERSION_CONTROL=bogus @ln -b a b',
    'VERSION_CONTROL=simple SIMPLE_BACKUP_SUFFIX=.orig @ln -bv a b', 'SIMPLE_BACKUP_SUFFIX=a/b @ln -bv a b',
    'SIMPLE_BACKUP_SUFFIX= @ln -bv a b', '@ln -b -s a sa', '@ln -bsv b sa', '@ln --backup=numbered -sv b sa',
    '@ln -bf a a', '@ln -b a dir', '@ln -bv a b c other', '@ln -fv a b c other',
    '@ln -r a n', '@ln -sr a n', '@ln -srv a dir/sub/n', '@ln -srv dir/x deep/a/b/n', '@ln -sr /etc/passwd n',
    '@ln -srv a b dir', '@ln -sr nonexistent dir/sub/n', '@ln -srv ../a dir/n', '@ln -srf b a', '@ln -sr a sdir/n',
    '@ln -srT dir/x deep/n', '@ln -s -r -t dir a b',
    "printf 'y\\n' | @ln -i a b", "printf 'n\\n' | @ln -i a b", "printf 'y\\nn\\n' | @ln -i a b c other",
    "printf 'y\\n' | @ln -si a b", "printf 'y\\n' | @ln -iv a b", "printf 'y\\n' | @ln -fi a b", "printf 'y\\n' | @ln -if a b",
    "@ln -i a b < /dev/null", "printf 'y\\n' | @ln -i a newname", "printf 'y\\n' | @ln -ib a b",
    '@ln -L sa n', '@ln -P sa n', '@ln -L dangling n', '@ln -P dangling n', '@ln --logical sa n', '@ln --physical sa n',
    '@ln -LP sa n', '@ln -PL sa n', '@ln -sL a n',
    '@ln -f a b b dir', '@ln -f a a dir', '@ln -f dir/x other/x dir', '@ln a a dir', '@ln -f a hl dir',
    '@ln -fb a a other', '@ln --backup=numbered -f a a other', '@ln -sf a a other', '@ln -f c a b other; ls other',
    '@ln --bogus', '@ln -x a b', '@ln --verb a n', '@ln --sym a n', '@ln --rel -s a n', '@ln --target=dir a', '@ln --no-t a n',
    '@ln -s "" n', '@ln -s a ""', '@ln "" n', '@ln -sv "sp ace" "n m"', '@ln -v a "sp ace"', '@ln -fv a "sp ace"',
    '@ln -s a nodir/n', '@ln a nodir/n', '@ln a b nodir', '@ln -s a b c nodir', '@ln a b dangling', '@ln a b sa',
    'chmod 555 dir; @ln a dir/n; chmod 755 dir', 'chmod 555 dir; @ln -fb a dir/x; chmod 755 dir',
    'chmod 555 dir; @ln -sf a dir/x; chmod 755 dir', '@ln -v a n > /dev/full; echo $?',
]


def snapshot(root):
    out = []
    groups = {}
    for dp, dns, fns in os.walk(root):
        for n in sorted(fns + dns):
            p = os.path.join(dp, n)
            rel = os.path.relpath(p, root)
            st = os.lstat(p)
            if os.path.islink(p):
                out.append('%s -> %s' % (rel, os.readlink(p)))
            elif os.path.isdir(p):
                out.append(rel + '/')
            else:
                groups.setdefault(st.st_ino, []).append(rel)
                out.append('%s %r' % (rel, open(p, 'rb').read()))
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
    c = cmd.replace('@ln', (NEBOX + ' ln') if which == 'nebox' else 'ln')
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
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:700]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:700]))
print('ln_compare: %d cases, %d mismatches' % (len(CASES), bad))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d)
sys.exit(1 if bad else 0)
