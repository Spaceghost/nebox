#!/usr/bin/env python3
"""Side-by-side test of nebox split against GNU coreutils split.
Usage: tests/split_compare.py path/to/nebox
Each case runs in a fresh directory holding the same inputs; stdout,
diagnostics (minus "Try --help"), exit status and every file left behind
(name and contents) must match."""
import hashlib, os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='split-compare-')
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
env.pop('SHELL', None)

INPUTS = {
    'nums': ''.join('%d\n' % i for i in range(1, 2501)),
    'words': 'alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\neta\ntheta\niota\nkappa\n',
    'nonl': 'one\ntwo\nthree',
    'long': 'short\n' + 'x' * 5000 + '\n' + 'tiny\n' + 'y' * 300 + '\nend',
    'nul': 'a\0bb\0ccc\0dddd\0',
    'empty': '',
    'one': 'x',
    'big': ''.join('line %06d of the big input\n' % i for i in range(60000)),
}

CASES = [
    '@split nums', '@split -l 7 words', '@split -l7 words p.', '@split --lines=3 words w',
    '@split -3 words', '@split -1 -2 words', '@split -12 nums', '@split -l 0 words', '@split -l x words',
    '@split -l 1k words', '@split -l -1 words', '@split -l 99999999999999999999999 words',
    '@split -b 10 words', '@split -b 1K nums', '@split -b 1KB nums', '@split -b 1KiB nums', '@split -b 2k big',
    '@split -b 1x nums', '@split -b 0 nums', '@split -b b nums', '@split -b 1kk nums',
    '@split -C 12 words', '@split -C 100 long', '@split -C 7 long', '@split -C 4096 long', '@split -C 3 nonl',
    '@split -C 1 words', '@split -C 64k big', '@split --line-bytes=20 nums',
    '@split -n 3 words', '@split -n 7 nums', '@split -n 20 one', '@split -n 0 words', '@split -n 2/3 words',
    '@split -n 3/3 nums', '@split -n 4/3 words', '@split -n 0/3 words', '@split -n /3 words',
    '@split -n l/3 words', '@split -n l/5 long', '@split -n l/2/3 words', '@split -n l/3/3 nums',
    '@split -n l/1/5 long', '@split -n l/4/5 long', '@split -n r/3 words', '@split -n r/2/3 words',
    '@split -n r/4 nonl', '@split -u -n r/2/3 nums | head -3', '@split -e -n 20 words', '@split -e -n l/20 words',
    '@split -e -n r/20 words', '@split -n 3 empty', '@split -e -n 3 empty', '@split -n  r/3 words',
    '@split -n x words', '@split -n l/x words', '@split -n r/2/x words',
    'cat words | @split -n 3', 'cat words | @split -n l/3', 'cat words | @split -n r/3', 'cat words | @split -l 3 - in.',
    '@split -a 1 -l 1 words', '@split -a 1 -l 1 nums; echo $?', '@split -a 4 -b 100 nums', '@split -a 0 words',
    '@split -l 1 nums', '@split -l 1 -d nums', '@split -l 1 -x nums', '@split -d -n 12 words', '@split -a 1 -n 30 nums',
    '@split --numeric-suffixes=5 -l 2 words', '@split --numeric-suffixes=05 -l 2 words', '@split --numeric-suffixes=9 -l 2 words',
    '@split --numeric-suffixes=99 -l 1 words', '@split --numeric-suffixes=x words', '@split --hex-suffixes=19 -l 1 words',
    '@split --hex-suffixes=g words', '@split -a 2 --numeric-suffixes=123 words', '@split --numeric-suffixes=3 -n 5 words',
    '@split --numeric-suffixes=3 -n 12 words', '@split -d -l 1 -a 1 words; echo $?',
    '@split --additional-suffix=.txt -l 4 words', '@split --additional-suffix=a/b words', '@split --additional-suffix= -l 4 words',
    '@split -l 3 words pre --additional-suffix=.s',
    '@split -t "\\0" -l 2 nul', '@split -t a -l 1 words', '@split -t ab words', '@split -t "" words', '@split -t a -t b words',
    '@split -t a -t a -l 2 words', '@split -t "\\0" -n l/2 nul', '@split -t "\\0" -n r/3 nul', '@split -t "\\0" -C 6 nul',
    '@split --verbose -l 4 words', '@split --verbose -n r/2 words', '@split --verbose -n 2/3 words',
    "@split --filter='cat > $FILE.f' -l 4 words", "@split --filter='wc -c' -n 3 words", "@split --filter='head -c 2' -b 4 words",
    "@split --filter='exit 3' -l 4 words; echo $?", "@split --filter='kill -TERM $$' -l 4 words; echo $?",
    "@split --filter='head -1 >/dev/null' -l 2000 big; echo $?", "@split --filter=true -b 1000 big; echo $?",
    "@split --filter='head -c 1' -n r/3 nums", "@split --verbose --filter='cat > /dev/null' -l 4 words",
    "@split --filter=x -n 2/3 words", "@split -e --filter='cat > $FILE' -n 20 words",
    '@split -l 2 -b 3 words', '@split -n 2 -C 3 words', '@split -3 -l 2 words', '@split -l 2 -3 words',
    '@split words p extra', '@split nofile', '@split -l 2 words /nodir/x; echo $?', '@split --bogus', '@split -q',
    '@split --number', '@split --verb words', '@split --numeric words', 'ln -s words xaa; @split -l 3 xaa; echo $?',
    '@split -l 3 words; @split -l 2 words; ls', '@split ---io-blksize=1 -C 5 long', '@split ---io-blksize=3 -n l/4 words',
    '@split ---io-blksize=7 -n 3/4 nums | head -c 50', '@split ---io-blksize=0 words', '@split -b 7 -n 3 words',
    '@split -n 5 /dev/null', '@split -n 2 /dev/zero; echo $?', 'echo hi | @split -n 1/2', 'printf "" | @split -n r/2/2',
    '@split -l 1000 big; ls | tail -2', '@split -l 500 big; ls | tail -3', '@split -b 1 nonl', '@split -C 2 nonl',
]


def snapshot(wd):
    out = []
    for f in sorted(os.listdir(wd)):
        if f in INPUTS:
            continue
        p = os.path.join(wd, f)
        if os.path.islink(p):
            out.append('%s -> %s' % (f, os.readlink(p)))
        elif os.path.isfile(p):
            b = open(p, 'rb').read()
            out.append('%s %d %s' % (f, len(b), hashlib.sha1(b).hexdigest()[:12]))
        else:
            out.append(f + '/')
    return '\n'.join(out).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.makedirs(wd)
    for k, v in INPUTS.items():
        open(os.path.join(wd, k), 'w').write(v)
    c = cmd.replace('@split', (NEBOX + ' split') if which == 'nebox' else 'split')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(wd.encode(), b'WD')
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
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:400]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:400]))
print('split_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
