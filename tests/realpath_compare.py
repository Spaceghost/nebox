#!/usr/bin/env python3
"""Side-by-side test of nebox readlink and realpath against GNU coreutils.
Usage: tests/realpath_compare.py path/to/nebox [random-cases] [seed]
A fixture with relative, absolute, dangling and looping symlinks and a
25-link chain; random operands mix ".", "..", repeated and trailing
slashes, files used as directories and missing components. Output, every
diagnostic line and exit status must match (the fixture path is masked)."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 600
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
root = tempfile.mkdtemp(prefix='realpath-compare-')
d = os.path.join(root, 'fx')
os.makedirs(os.path.join(d, 'a/b/c'))
os.makedirs(os.path.join(d, 'x/y'))
open(os.path.join(d, 'a/file'), 'w').close()
open(os.path.join(d, 'a/b/c/deep'), 'w').close()
os.symlink('b', os.path.join(d, 'a/lb'))
os.symlink('../x', os.path.join(d, 'a/lx'))
os.symlink(os.path.join(d, 'x/y'), os.path.join(d, 'abs'))
os.symlink('nowhere', os.path.join(d, 'dangling'))
os.symlink('loop2', os.path.join(d, 'loop1'))
os.symlink('loop1', os.path.join(d, 'loop2'))
os.symlink('self', os.path.join(d, 'self'))
os.symlink('a/file', os.path.join(d, 'lfile'))
os.symlink('a/b/c/../../file', os.path.join(d, 'ldots'))
os.symlink('/', os.path.join(d, 'lroot'))
prev = 'a'
for i in range(25):
    os.symlink(prev, os.path.join(d, 'ch%d' % i))
    prev = 'ch%d' % i
os.symlink('ldir/../a', os.path.join(d, 'lpar'))
os.symlink('x/y', os.path.join(d, 'ldir'))
NAMES = ['a', 'b', 'c', 'x', 'y', 'file', 'deep', 'lb', 'lx', 'abs', 'dangling', 'loop1', 'self', 'lfile', 'ldots', 'lroot',
         'ch24', 'ch19', 'ch21', 'lpar', 'ldir', 'missing', '.', '..', '']


def rand_path():
    parts = [rng.choice(NAMES) for _ in range(rng.choice([1, 1, 2, 3, 4]))]
    p = rng.choice(['', '', '/', '//']).join(['']) + '/'.join(parts)
    if rng.random() < 0.15:
        p = p.replace('/', '//', 1)
    if rng.random() < 0.15:
        p += rng.choice(['/', '/.', '/..', '//'])
    if rng.random() < 0.05:
        p = d + '/' + p
    return p or '.'


def rand_case():
    if rng.random() < 0.35:
        opt = rng.choice(['', '-f', '-e', '-m', '-v', '-fv', '-ev', '-mv', '-n', '-z', '-q'])
        files = ' '.join("'%s'" % rand_path() for _ in range(rng.choice([1, 1, 2])))
        return '@readlink %s %s | od -c | head -4' % (opt, files) if '-z' in opt else '@readlink %s %s' % (opt, files)
    opts = rng.choice(['', '', '-e', '-m', '-L', '-P', '-s', '-q', '-e -L', '-m -s', '-L -m'])
    if rng.random() < 0.25:
        opts += " --relative-to='%s'" % rand_path()
    if rng.random() < 0.15:
        opts += " --relative-base='%s'" % rand_path()
    files = ' '.join("'%s'" % rand_path() for _ in range(rng.choice([1, 1, 2, 3])))
    return '@realpath %s %s' % (opts, files)


FIXED = ['@readlink', '@realpath', '@readlink a lb', '@readlink -n lb lx', '@readlink -n lb', '@readlink -f ch24',
         '@realpath ch24', '@realpath -e ch24/b', '@realpath loop1', '@realpath -m loop1', '@realpath -m loop1/x',
         '@realpath -e loop1', '@realpath self', '@realpath -m self/x/..', '@realpath dangling', '@realpath -e dangling',
         '@realpath dangling/x', '@realpath -m dangling/x', '@realpath a/file/', '@realpath a/file/.', '@realpath a/file/..',
         '@realpath -m a/file/', '@realpath lfile/', '@realpath --relative-to=x a/file', '@realpath --relative-to=a/b/c a/file x',
         '@realpath --relative-base=a a/file x/y', '@realpath --relative-to=a --relative-base=a/b a/b/c x',
         '@realpath --relative-to=a/b --relative-base=a a/b/c a/file x', '@realpath -e --relative-to=a/file a',
         '@realpath --relative-to=missing/x a', '@realpath -z a x | od -c', '@realpath lroot', '@realpath lroot/..',
         '@realpath //a', '@realpath -L lpar', '@realpath -P lpar', '@realpath -s lpar', '@readlink -v nofile', '@readlink --foo',
         '@realpath ""', '@readlink -f ""', '@realpath / // ///']


def run(cmd, which):
    c = cmd.replace('@readlink', (NEBOX + ' readlink') if which == 'nebox' else 'readlink')
    c = c.replace('@realpath', (NEBOX + ' realpath') if which == 'nebox' else 'realpath')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout.replace(d.encode(), b'FX'), err.replace(d.encode(), b'FX')


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 15:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:300]))
                    print('  %s nebox: %r' % (name, y[:300]))
print('realpath_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(root)
sys.exit(1 if bad else 0)
