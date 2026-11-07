#!/usr/bin/env python3
"""Side-by-side test of nebox wc, id and touch --time against GNU coreutils.
Usage: tests/wcid_compare.py path/to/nebox [random-cases] [seed]
wc: random column options over random file sets (regular files, stdin,
directories, missing files, --files0-from lists from files and pipes,
shared file offsets); id: user operands and option conflicts; touch:
--time words. Output, diagnostics (minus "Try --help") and status match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C', TZ='UTC')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='wcid-compare-')
frng = random.Random(2)


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


w('a', b'hello world\nfoo\tbar  baz\n\x01\x02 x\ry\x0cz\n')
w('b', b''.join(b'line %d %s\n' % (i, b'w ' * frng.randrange(8)) for i in range(400)))
w('c', b'no newline at end')
w('e', b'')
w('big', bytes(frng.randrange(256) for _ in range(9000)))
w('page', b'x' * 4096)
w('nl\nname', b'1\n')
w('list', b'a\0b\0c\0')
w('list2', b'a\0\0e\0nofile\0')
w('list3', b'a\0b')
w('listdash', b'-\0a\0')
os.mkdir(os.path.join(d, 'adir'))
FILES = ['a', 'b', 'c', 'e', 'big', 'page', 'adir', 'nofile', '-', "'nl\nname'"]


def rand_case():
    opts = ''.join(rng.sample('clLmw', rng.choice([0, 1, 1, 2, 3])))
    opts = ('-' + opts) if opts else ''
    r = rng.random()
    if r < 0.15:
        lst = rng.choice(['list', 'list2', 'list3', 'listdash', '-'])
        pre = "printf 'a\\0b\\0' | " if lst == '-' else rng.choice(['', 'cat list | ', 'cat a | '])
        if pre == 'cat list | ':
            lst = '-'
        return '%s@wc %s --files0-from=%s' % (pre, opts, lst)
    files = rng.sample(FILES, rng.choice([0, 1, 1, 2, 3]))
    pre = rng.choice(['', 'cat b | ', '{ head -c 5 >/dev/null; ', ''])
    cmd = '@wc %s %s' % (opts, ' '.join(files))
    if pre.startswith('{'):
        return '{ head -c 5 >/dev/null; %s; } < b' % cmd
    return pre + cmd


FIXED = ['@wc --files0-from=list a', '@wc --files0-from=nolist', '@wc --chars --bytes a', '@wc -m a b', '@wc --debug a',
         '@wc --max-line-length a', '@wc -c page', '{ head -c 100 >/dev/null; @wc -c; } < page', '@wc -c < big',
         '@id', '@id -u', '@id -un', '@id -g', '@id -gn', '@id -G', '@id -Gn', '@id -Gz | od -c', '@id -Gnz root build | od -c',
         '@id root', '@id 0', '@id +0', '@id +root', '@id nosuch', '@id root build', '@id -u root nosuch daemon', '@id -ur',
         '@id -u -g', '@id -n', '@id -z', '@id -r', '@id -Z', '@id -a', '@id -G daemon', '@id --user --name root',
         '@id -uz root build | od -c', "@id ''", '@id 99999', '@id -gn 0',
         'touch -d 2001-01-01 t; @touch --time=atime -d 2002-02-02 t; stat -c "%X %Y" t',
         'touch -d 2001-01-01 t; @touch --time=mtime -d 2002-02-02 t; stat -c "%X %Y" t',
         'touch -d 2001-01-01 t; @touch --time=use -d 2002-02-02 t; stat -c "%X %Y" t',
         'touch -d 2001-01-01 t; @touch --time=modify -d 2002-02-02 t; stat -c "%X %Y" t',
         '@touch --time=m -d 2002-02-02 t', '@touch --time=bogus t', '@touch --time= t', '@touch -f t; ls t']


def run(cmd, which):
    c = cmd
    for a in ('wc', 'id', 'touch'):
        c = c.replace('@' + a, (NEBOX + ' ' + a) if which == 'nebox' else a)
    for f in ('t',):
        try:
            os.unlink(os.path.join(d, f))
        except FileNotFoundError:
            pass
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


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
                    print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
print('wcid_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
