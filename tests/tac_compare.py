#!/usr/bin/env python3
"""Side-by-side test of nebox tac against GNU coreutils tac.
Usage: tests/tac_compare.py path/to/nebox [random-cases]
Fixed cases plus random inputs (records longer than the 8 KiB read size,
missing final separators, multi-byte and regex separators, -b), read from
files and from pipes. stdout, diagnostics (minus "Try" lines) and exit
status must match."""
import os, random, subprocess, sys, tempfile, shutil

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 300
d = tempfile.mkdtemp(prefix='tac-compare-')
env = dict(os.environ, LC_ALL='C')
open(os.path.join(d, 'f'), 'w').write('a\nb\nc\n')
open(os.path.join(d, 'nonl'), 'w').write('a\nb\nc')
open(os.path.join(d, 'e'), 'w').write('')
open(os.path.join(d, 'nl'), 'w').write('\n\n\n')
open(os.path.join(d, 'c'), 'w').write('1:2:3')
open(os.path.join(d, 'big'), 'w').write(''.join('line %d %s\n' % (i, 'x' * (i % 300)) for i in range(3000)))
open(os.path.join(d, 'longrec'), 'w').write('short\n' + 'y' * 40000 + '\nend\n' + 'z' * 20000)
open(os.path.join(d, 'nul'), 'wb').write(b'a\0bb\0c')
CASES = [
    '@tac f', '@tac nonl', '@tac e', '@tac nl', '@tac -b f', '@tac -b nonl', '@tac -s : c', '@tac -bs : c', '@tac -s xx f',
    '@tac -s "" nul', '@tac -s "" f', '@tac -r -s "[0-9]" c', '@tac -r -s "a*" f', '@tac -r -s "b\\|c" f', '@tac -r -s "" f',
    '@tac -r -s "\\(" f', '@tac -r -s "[" f', '@tac -rs "a[b" f', '@tac -rs "[^" f', '@tac -rs "[]" f', '@tac -rs "a\\)" f', '@tac -rs "[[:alpha:]]" f', '@tac -rs "^b" f', '@tac -rs "$" f', '@tac -rs "." f', '@tac -rs ".+" nonl',
    '@tac -rs "x+" f', '@tac -rs "b+" f', '@tac -rs "a?" f', '@tac -rs "{1}" f', '@tac -rs "a\\{1\\}" f', '@tac -rs "*b" f',
    '@tac big | md5sum', '@tac -b big | md5sum', '@tac longrec | md5sum', '@tac -b longrec | md5sum', '@tac -s y longrec | md5sum',
    'cat big | @tac | md5sum', 'cat longrec | @tac -b | md5sum', '@tac - < f', 'cat f | @tac - -', '@tac f f', '@tac nonexistent f',
    '@tac dir', '@tac --before f', '@tac --regex --separator=b f', '@tac --sep=b f', '@tac -x', '@tac --bogus', '@tac -s',
    'TMPDIR=/nonexistent @tac < f', 'cat f | TMPDIR=/nonexistent @tac', '@tac f > /dev/full; echo $?',
    '@tac -rs "line [0-9]*5" big | md5sum', '@tac -bs "line" big | md5sum',
]
os.mkdir(os.path.join(d, 'dir'))
rnd = random.Random(11)
for k in range(NRAND):
    alphabet = rnd.choice(['ab\n', 'abc:\n', 'a\nb\n\n', 'xyz'])
    n = rnd.choice([0, 1, 5, 50, 500, 9000, 20000])
    data = ''.join(rnd.choice(alphabet) for _ in range(n))
    name = 'r%d' % k
    open(os.path.join(d, name), 'w').write(data)
    sep = rnd.choice(['', '-s :', '-s ab', '-s "\n\n"', '-r -s "a+"', '-r -s "[ab]"', '-r -s "\\(ab\\|c\\)"', '-s b'])
    b = rnd.choice(['', '-b'])
    src = rnd.choice(['%s', '< %s', 'cat %s |'])
    if src.startswith('cat'):
        CASES.append('cat %s | @tac %s %s | od -c | md5sum' % (name, b, sep))
    else:
        CASES.append('@tac %s %s %s | od -c | md5sum' % (b, sep, (src % name)))


def run(cmd, which):
    c = cmd.replace('@tac', (NEBOX + ' tac') if which == 'nebox' else 'tac')
    p = subprocess.run(['bash', '-c', c], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 30:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('tac_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
