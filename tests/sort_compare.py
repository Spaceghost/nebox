#!/usr/bin/env python3
"""Side-by-side test of nebox sort against GNU sort 9.1 (C locale).
Usage: tests/sort_compare.py path/to/nebox [random-cases] [seed]
Fixed cases cover every option and diagnostic of sort.c: keys and their
parse errors, obsolete +POS1 -POS2 keys (with _POSIX2_VERSION and
POSIXLY_CORRECT), -R with a fixed --random-source, --debug annotations and
warnings, --files0-from, -m (with --batch-size's intermediate merges and
-o naming an input), -c/-C/--check, -o, -s, -u, -z, -t, -S, -T,
--parallel, --batch-size, --compress-program, -y, read and write errors.
Random cases mix integers, floats, exponents, hex floats, inf/nan, -0,
human sizes, month names, versions and words with random global and
per-key orderings, keys, -t, -s, -u, -c, -m, -R, --debug and the
incompatible combinations. Output, diagnostics (minus "Try --help") and
exit status must match. Fixtures live under /dev/shm."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 600
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
base_env = dict(os.environ, LC_ALL='C')
for k in ('POSIXLY_CORRECT', '_POSIX2_VERSION', 'TMPDIR'):
    base_env.pop(k, None)
d = tempfile.mkdtemp(prefix='sort-compare-', dir='/dev/shm' if os.path.isdir('/dev/shm') else None)
TOKENS = ['0', '-0', '+0', '1', '10', '2', '-3', '3.5', '-3.50', '1e3', '1E-2', '.5', '0x10', '0x1p4', 'inf', '-inf',
          'nan', 'NaN', '-nan', 'abc', '', ' 7', '  12', '1k', '2K', '3M', '1G', '1.5T', 'jan', 'Feb', ' MAR', 'apr x',
          'December', 'sep', 'JUNE', 'ju', 'm', '1.2.10', '1.2.9', 'v2', 'a-1.0', 'file10.txt', 'file9.txt', 'Zebra', 'apple',
          'apple ', '_x', '9' * 25, '1,5', '1e400', '-1e-400', '1\x802', '\x80' + '5', 'a\tb', '\x01c', 'b\x7f']


def write(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data.encode('latin-1') if isinstance(data, str) else data)


# GNU compares two NaNs under -g by the bytes of the whole long double,
# six of which are padding that sort.c's dead memset leaves uninitialized,
# so the outcome depends on the stack (-g -u keeps two "nan" lines, -k1,1g
# sorts them by the last resort). Cases that compare by -g get no NaNs.
NAN_TOKENS = ('nan', 'NaN', '-nan')


def rand_line(tokens):
    n = rng.choice([1, 1, 2, 3])
    sep = rng.choice([' ', ' ', ':', '\t'])
    return sep.join(rng.choice(tokens) for _ in range(n))


def rand_file(name, tokens=TOKENS):
    lines = [rand_line(tokens) for _ in range(rng.choice([1, 3, 8, 20]))]
    write(name, '\n'.join(lines) + '\n')


def rand_case():
    files = ['in']
    opts = []
    for _ in range(rng.choice([0, 1, 1, 2])):
        opts.append(rng.choice(['-g', '-M', '-n', '-h', '-V', '-f', '-b', '-d', '-i', '-r', '-s', '-u', '-R',
                                '--general-numeric-sort', '--month-sort', '--sort=month', '--sort=general-numeric',
                                '--sort=numeric', '--sort=version', '--sort=h', '--sort=random']))
    if rng.random() < 0.5:
        for _ in range(rng.choice([1, 1, 2])):
            f1 = rng.randint(1, 3)
            mods = ''.join(rng.sample('bdfghiMnrRV', rng.choice([0, 1, 1, 2])))
            spec = '%d%s' % (f1, mods)
            if rng.random() < 0.3:
                spec = '%d.%d%s' % (f1, rng.randint(1, 3), mods)
            if rng.random() < 0.4:
                spec += ',%d%s%s' % (rng.randint(f1, 3), rng.choice(['', '', '.2']), rng.choice(['', 'b', 'g', 'M', 'n']))
            opts += ['-k', spec]
        if rng.random() < 0.4:
            opts += ['-t', rng.choice([':', ' ', '\t'])]
    if rng.random() < 0.15:
        opts.append('--debug')
    if any(o.startswith('-R') or o == '--sort=random' or (len(o) > 1 and o[0].isdigit() and 'R' in o) for o in opts):
        opts.append('--random-source=rs')
    general = any(o in ('-g', '--general-numeric-sort', '--sort=general-numeric') or (o[:1].isdigit() and 'g' in o)
                  for o in opts)
    tokens = [t for t in TOKENS if t not in NAN_TOKENS] if general else TOKENS
    rand_file('in', tokens)
    r = rng.random()
    if r < 0.05:
        opts.append(rng.choice(['-c', '-C']))
    elif r < 0.15:
        rand_file('in2', tokens)
        rand_file('in3', tokens)
        opts.append('-m')
        files = ['in', 'in2', 'in3']
        if rng.random() < 0.5:
            opts.append('--batch-size=2')
    elif r < 0.2:
        opts.append(rng.choice(['-S', '--parallel=']) + rng.choice(['1', '2', '100']))
    return {'args': opts + files}


def run(case, which):
    env = dict(base_env)
    env.update(case.get('env', {}))
    if 'sh' in case:
        cmd = (NEBOX + ' sort') if which == 'nebox' else 'sort'
        p = subprocess.run(['sh', '-c', case['sh'].replace('@sort', cmd)], cwd=d, env=env, capture_output=True,
                           timeout=60, stdin=subprocess.DEVNULL)
    else:
        argv = ([NEBOX, 'sort'] if which == 'nebox' else ['sort']) + case['args']
        stdin = case.get('stdin')
        p = subprocess.run(argv, cwd=d, env=env, capture_output=True, timeout=60,
                           input=stdin.encode('latin-1') if isinstance(stdin, str) else stdin,
                           stdin=None if stdin is not None else subprocess.DEVNULL)
    out = p.stdout
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    if case.get('help') and which == 'gnu':
        out = out[:out.index(b'\nGNU coreutils online help')]
    return p.returncode, out, err


# Fixtures.
write('words', 'pear\napple\nfig\nApple\nbanana\napple\n\nfig\n')
write('nums', '10\n9\n-1\n2.5\n1e3\n0x10\n 7\n\n-0\n+3\n')
write('in', '3\n1\n2\n')
write('a', 'a\nc\ne\ne\n')
write('b', 'b\nd\ne\nf\n')
write('unsorted', 'q\nb\nz\na\n')
write('dup', 'a 1\nb 1\nA 1\nc 2\na 1\n')
write('fields', 'x:3:b\ny:1:a\nz:2:c\nw:1:b\n')
write('ws', '  b 2\n\ta 1\n c  3\n')
write('nonl', 'z\ny')
write('empty', '')
write('zdata', 'b\0a\nx\0c\0')
write('hi', '1\x802\n13\n11\n\x8012\n')
write('rs', bytes(rng.randrange(256) for _ in range(64)))
write('rs2', bytes(rng.randrange(256) for _ in range(16)))
write('shortrs', b'12345678')
write('f0', b'a\0b\0')
write('f0nl', b'a\0words')
write('f0dash', b'a\0-\0')
write('f0empty', b'a\0\0b\0')
write('f0none', b'')
write('f0bad', b'a\0nosuch\0')
for i in range(7):
    write('m%d' % i, ''.join('%s\n' % x for x in rng.sample(['k', 'c', 'x', 'a', 'm', 'b', 'q', 'e'], 4)))
os.mkdir(os.path.join(d, 'dir'))
write('noread', 'x\n')
os.chmod(os.path.join(d, 'noread'), 0)

S = lambda *a, **kw: dict(kw, args=list(a))
FIXED = [
    # orderings and keys
    S('words'), S('-r', 'words'), S('-f', 'words'), S('-fu', 'words'), S('-u', 'words'), S('-s', '-f', 'words'),
    S('-n', 'nums'), S('-g', 'nums'), S('-h', 'nums'), S('-gr', 'nums'), S('-nu', 'nums'), S('-n', 'hi'),
    S('-h', 'hi'), S('-g', 'hi'), S('-k1,1', '-u', 'dup'), S('-k1,1f', '-u', 'dup'), S('-k2n', 'dup'),
    S('-s', '-k2,2', 'dup'), S('-u', '-k2,2', 'dup'), S('-t:', '-k2n', '-k3', 'fields'), S('-t:', '-k2,2r', 'fields'),
    S('-k2b', 'ws'), S('-b', 'ws'), S('ws'), S('-k1.2,1.3', 'ws'), S('-k1.2b,1.3b', 'ws'), S('-d', 'words'),
    S('-i', 'hi'), S('-M', stdin='jan\nFEB\n mar\nxyz\n\n'), S('-V', stdin='a1\na10\na2\n.\n..\n.a\n~\n'),
    S('-z', 'zdata'), S('-zr', 'zdata'), S('nonl', 'a'), S('nonl', 'nonl'), S('empty'), S('-', 'a', stdin='zz\n'),
    S('-t', '\\0', '-k2', stdin='a\0b\nc\0a\n'), S('-k2,1', 'dup'), S('-k3,2n', 'dup'),
    S('-k', '+2', 'dup'), S('-k', ' 2', 'dup'), S('-k', '99999999999999999999', 'dup'),
    S('-k1,1.99999999999999999999', 'dup'), S('-u', '-k1,1.99999999999999999999', 'dup'),
    S('-k2.18446744073709551615', stdin='xxxx yy\naaaa bb\nzzzz aa\n'), S('-k2.18446744073709551614,2', stdin='xxxx yy\naaaa bb\n'),
    S('--debug', '-k2.18446744073709551615', stdin='xxxx yy\naaaa bb\n'), S('--debug', '-k1,1.18446744073709551615', stdin='xxxx yy\n'),
    # key and option errors
    S('-k0', 'in'), S('-k1.0', 'in'), S('-k1,0', 'in'), S('-k1.x', 'in'), S('-k1,x', 'in'), S('-kx', 'in'),
    S('-k', '', 'in'), S('-k', '-1', 'in'), S('-k1,1.2.3', 'in'), S('-k1b2', 'in'), S('-k1,2.x', 'in'),
    S('-nR', 'in'), S('-dn', 'in'), S('-Mg', 'in'), S('-hV', 'in'), S('-k1,1Mh', 'in'), S('-k1nR', 'in'),
    S('-k1dfiVR', '--random-source=rs', 'in'), S('-n', '-g', '-k1,1r', 'in'), S('-t', 'ab', 'in'), S('-t', '', 'in'),
    S('-t', 'a', '-t', 'b', 'in'), S('-t', 'a', '-t', 'a', 'in'), S('-x', 'in'), S('--bogus', 'in'),
    S('--s', 'in'), S('--sort=bogus', 'in'), S('--sort=', 'in'), S('--sort=r', '--random-source=rs', 'in'), S('--sort=gen', 'nums'),
    S('-k'), S('-o'), S('-o', 'x', '-o', 'y', 'in'), S('-o', 'o1', '-o', 'o1', 'in'),
    S('--compress-program=gzip', 'in'), S('--compress-program=gzip', '--compress-program=xz', 'in'),
    S('--compress-program=gzip', '--compress-program=gzip', 'in'),
    # -c, -C, --check
    S('-c', 'words'), S('-C', 'words'), S('-c', 'a'), S('-cu', 'a'), S('-c', 'b'), S('-c', '-k2,2', 'dup'),
    S('-cu', '-k2,2', 'dup'), S('--check', 'unsorted'), S('--check=quiet', 'unsorted'),
    S('--check=silent', 'unsorted'), S('--check=diagnose-first', 'unsorted'), S('--check=d', 'unsorted'),
    S('--check=bogus', 'unsorted'), S('--check=', 'unsorted'), S('-c', '-C', 'a'), S('-C', '--check', 'a'),
    S('-c', '-c', 'unsorted'), S('-c', 'a', 'b'), S('-c', '-o', 'x', 'a'), S('-C', '-o', 'x', 'a'),
    S('-c', 'nosuch'), S('-c', 'dir'), S('-c', stdin='b\na\n'), S('-cz', stdin='b\nx\0a\0'),
    S('-c', 'empty'), S('-c', '-n', 'nums'), S('-c', '--files0-from=f0'), S('-c', 'nonl'),
    # -m
    S('-m', 'a', 'b'), S('-mu', 'a', 'b'), S('-m', 'unsorted', 'a'), S('-m', '-r', 'b', 'a'), S('-m', 'a', 'empty', 'b'),
    S('-m', '-k1,1', '-s', 'dup', 'a'), S('-m', '-', 'a', stdin='b\nz\n'), S('-m', 'a', 'dir'), S('-m', 'nosuch', 'a'),
    S('-m', '--batch-size=2', *['m%d' % i for i in range(7)]), S('-m', '--batch-size=3', *['m%d' % i for i in range(7)]),
    S('-mu', '--batch-size=2', *['m%d' % i for i in range(5)]), S('-m', *['m%d' % i for i in range(7)]),
    S('-m', '--debug', 'a', 'b'), S('-m', 'nonl', 'a'),
    {'sh': 'cp a x; @sort -m -o x x b; echo $?; cat x'}, {'sh': 'cp a x; @sort -m -o x b x x; echo $?; cat x'},
    {'sh': 'cp a x; @sort -m -o x - b < x; echo $?; cat x'}, {'sh': 'cp a x; @sort -mu -o x b x; echo $?; cat x'},
    {'sh': 'printf "zz\\n" > x; @sort -m -o x a dir; echo $?; cat x'},
    # -o
    {'sh': 'cp unsorted x; @sort -o x x; echo $?; cat x'}, {'sh': 'cp unsorted x; @sort -o x a x; cat x'},
    {'sh': 'printf "zzzzzz\\n" > x; @sort -o x a; cat x'}, {'sh': 'cp unsorted x; @sort -o x nosuch; echo $?; cat x'},
    {'sh': 'rm -f nx; @sort -o nx empty; echo $?; ls nx; wc -c < nx'}, S('-o', 'dir', 'a'),
    S('-o', 'nodir/x', 'a'), {'sh': 'cp unsorted x; @sort -o x dir; echo $?; cat x'},
    # -R with a fixed random source
    S('-R', '--random-source=rs', 'words'), S('-R', '--random-source=rs2', 'words'), S('-Ru', '--random-source=rs', 'words'),
    S('-Rf', '--random-source=rs', 'words'), S('-Rr', '--random-source=rs', 'words'), S('-R', '-s', '--random-source=rs', 'dup'),
    S('-k2R', '--random-source=rs', 'dup'), S('-k1,1R', '-k2n', '--random-source=rs', 'dup'), S('--sort=random', '--random-source=rs', 'nums'),
    S('-R', '--random-source=shortrs', 'words'), S('-R', '--random-source=dir', 'words'), S('-R', '--random-source=nosuch', 'words'),
    S('--random-source=nosuch', 'words'), S('--random-source=rs', '--random-source=rs2', 'words'),
    S('--random-source=rs', '--random-source=rs', '-R', 'words'), S('-RV', '--random-source=rs', 'words'),
    S('-Rd', '--random-source=rs', 'words'), S('-R', '-c', '--random-source=rs', 'words'), S('-R', '--random-source=rs', '-z', 'zdata'),
    {'sh': '@sort -R words | @sort | cksum'},
    # --debug
    S('--debug', '-k2,1', stdin='a b c\nx y\n'), S('--debug', '-k3,1', stdin='a b c\nx y\n'), S('--debug', '-k3,1n', stdin='a b c\nx y\n'),
    S('--debug', '-k1.4,1.2', stdin='abcdef\n'), S('--debug', '-k2', stdin=' 1\x01\x80\xff2 b\n\tx\ty\n'),
    S('--debug', '-k1b', stdin=' 1\x01\x80\xff2 b\n\tx\ty\n'), S('--debug', '-g', stdin=' \x0b5 x\n  -1e3x\nnan\n'),
    S('--debug', '-n', stdin='  12 b\n 3k x\n-5.5e3 z\n-\n.\n'), S('--debug', '-h', '-k1,1', stdin='  12 b\n 3k x\n-5.5e3 z\n1Kx\n'),
    S('--debug', '-g', '-s', stdin='  12 b\n 3k x\n-5.5e3 z\n'), S('--debug', '-M', '-u', stdin=' jan b\n FEBx x\nmay\n'),
    S('--debug', '-r', '-k1,1', 'in'), S('--debug', '-r', '-s', '-k1,1', 'in'), S('--debug', '-n', '-k1,1r', '-k2b', 'in'),
    S('--debug', '-t.', '-k1,1n', 'in'), S('--debug', '-t.', '-k1n', 'in'), S('--debug', '-t-', '-k1n', 'in'),
    S('--debug', '-t+', '-k1g', 'in'), S('--debug', '-t+', '-k1n', 'in'), S('--debug', '+1', '-2', 'in'),
    S('--debug', '+1.2', '-3.4', 'in'), S('--debug', '+0', '-1b', 'in'), S('--debug', '+2', 'in'), S('--debug', '-z', 'zdata'),
    S('--debug', '-c', 'in'), S('--debug', '-C', 'in'), S('--debug', '-o', 'x', 'in'), S('--debug', '-k1,1', '-k2,2', '-u', 'dup'),
    S('--debug', '-b', '-k1,1', '-d', '-f', 'dup'), S('--debug', '-b', 'ws'), S('--debug', '-bn', '-r', 'ws'),
    S('--debug', '-k1bn,1', 'ws'), S('--debug', '-k1.2b,1.3', 'ws'), S('--debug', '-k1,1.3', 'ws'), S('--debug', '-k2.2,2.3', 'ws'),
    S('--debug', '-k2b,2.3', 'ws'), S('--debug', '-k1,1.3', '-t:', 'fields'), S('--debug', '-dfiVR', '--random-source=rs', 'in'),
    S('--debug', '-k1,1', '-r', '-u', 'in'), S('--debug', '-rs', 'in'), S('--debug', '-k1,1', '-M', '-n', 'in'),
    S('--debug', '-t:', '-k2,2n', '-k1', 'fields'), S('--debug', '-k2n,2', '-k3n', 'fields'), S('--debug', 'words'),
    S('--debug', '-u', 'words'), S('--debug', '-f', '-k1', '-k2', 'dup'), S('--debug', '-k1', '-b', '-r', '-f', '-s', 'dup'),
    S('--debug', '-i', '-k1', '-d', 'dup'), S('--debug', '-h', '-k1', '-g', '-k2', 'dup'), S('--debug', '-V', 'words'),
    S('--debug', '-k2,2.0n', 'dup'), S('--debug', '-k1.2,1.3n', 'dup'), S('--debug', '-k1,1.2n', 'dup'),
    S('--debug', '-t', '\\0', '-k2', stdin='a\0b\nc\0a\n'), S('--debug', '-k1.3', stdin='\t\tx\n  y\n'),
    # obsolete +POS1 -POS2 keys
    S('+1', 'dup'), S('+1', '-2', 'dup'), S('+0', '-1', 'dup'), S('+0.1', '-1.2', 'dup'), S('+1n', 'dup'), S('+1', '-2n', 'dup'),
    S('+1', '-2x', 'dup'), S('+1', '-2.x', 'dup'), S('+x', 'dup'), S('+', 'dup'), S('+1.x', 'dup'), S('+1z', 'dup'),
    S('+0', '-0', 'dup'), S('-r', '+1', '-2', 'dup'), S('dup', '+1'),
    S('+1', 'dup', env={'_POSIX2_VERSION': '200112'}), S('+1', '-2', 'dup', env={'_POSIX2_VERSION': '200112'}),
    S('+1', 'dup', env={'_POSIX2_VERSION': '199209'}), S('+1', 'dup', env={'_POSIX2_VERSION': 'x'}),
    S('+1', '-2', 'dup', env={'_POSIX2_VERSION': '200112', 'POSIXLY_CORRECT': '1'}),
    S('+1', '-2', 'dup', env={'POSIXLY_CORRECT': '1'}),
    S('dup', '-r', env={'POSIXLY_CORRECT': '1'}), S('-r', 'dup', 'a', env={'POSIXLY_CORRECT': '1'}),
    {'sh': '@sort dup -o x; echo $?; cat x', 'env': {'POSIXLY_CORRECT': '1'}},
    {'sh': '@sort dup -ox; echo $?; cat x', 'env': {'POSIXLY_CORRECT': '1'}},
    {'sh': '@sort dup -o x; echo $?; cat x', 'env': {'POSIXLY_CORRECT': '1', '_POSIX2_VERSION': '200112'}},
    S('-c', 'a', '-o', 'x', env={'POSIXLY_CORRECT': '1'}), S('a', '-o', env={'POSIXLY_CORRECT': '1'}),
    S('a', '--', 'b'), S('--', '-r'),
    # --files0-from
    S('--files0-from=f0'), S('--files0-from=f0nl'), S('--files0-from=f0dash'), S('--files0-from=f0empty'),
    S('--files0-from=f0none'), S('--files0-from=f0bad'), S('--files0-from=nosuch'), S('--files0-from=dir'),
    S('--files0-from=f0', 'a'), S('--files0-from=-', stdin='b\0a\0'), S('--files0-from=-', stdin='-\0'),
    S('-m', '--files0-from=f0'), S('--files0-from=f0', '--files0-from=f0nl'),
    # -S, -T, --parallel, --batch-size, -y
    S('-S', '10', 'in'), S('-S', '10%', 'in'), S('-S', '10b', 'in'), S('-S', '10k', 'in'), S('-S', '1M', 'in'),
    S('-S', '10E', 'in'), S('-S', '20E', 'in'), S('-S', '10x', 'in'), S('--buffer-size=10%x', 'in'),
    S('-S', '1000000000000000000%', 'in'), S('-S', '99999999999999999999', 'in'), S('-S', '', 'in'), S('-S', '-1', 'in'),
    S('-S', 'K', 'in'), S('-S', '%', 'in'), S('-S', ' 5', 'in'), S('-S', '+5', 'in'), S('-S', '5bb', 'in'),
    S('--buffer-size=1', 'in'), S('-S', '10', '-S', '20', 'in'), S('-S1K', 'in'),
    S('-T', 'dir', 'in'), S('-T', 'nosuch', 'in'), S('-T', 'a', '-T', 'b', 'in'), S('--temporary-directory=dir', 'in'),
    S('--parallel=0', 'in'), S('--parallel=1', 'in'), S('--parallel=8', 'in'), S('--parallel=x', 'in'),
    S('--parallel=1x', 'in'), S('--parallel=99999999999999999999999', 'in'), S('--parallel=-1', 'in'),
    S('--parallel=99999999999999999999999', 'empty'), S('--parallel=99999999999999999999999', 'nonl'),
    S('--parallel=99999999999999999999999', '-m', 'a', 'b'), S('--parallel=99999999999999999999999', '-c', 'a'),
    S('--batch-size=1', 'in'), S('--batch-size=2', 'in'), S('--batch-size=100000', 'in'), S('--batch-size=1x', 'in'),
    S('--batch-size=x', 'in'), S('--batch-size=-1', 'in'), S('--batch-size=99999999999999999999', 'in'),
    S('--batch-size=4294967298', 'in'), S('--batch-size=1021', 'in'), S('--batch-size=1022', 'in'),
    S('-y', 'in'), S('-y0', 'in'), S('-y', '100', 'in'), S('-y', 'in', 'a'), S('in', '-y'), S('-y', '', 'in'),
    S('-ry', '5', 'in'),
    # inputs and outputs that fail
    S('nosuch'), S('noread'), S('dir'), S('a', 'dir'), S('-', stdin=None), S('a', 'nosuch', 'dir'),
    {'sh': '@sort - < dir'}, {'sh': '@sort a > /dev/full; echo $?'}, {'sh': 'seq 10000 > big; @sort big > /dev/full; echo $?'},
    {'sh': '@sort -o /dev/full a; echo $?'}, {'sh': '@sort -o /dev/full big; echo $?'}, {'sh': '@sort a >&-; echo $?'},
    {'sh': '@sort --debug a > /dev/full; echo $?'}, {'sh': '@sort -m a b > /dev/full; echo $?'},
    {'sh': 'seq 100000 | @sort -m - | head -1'}, {'sh': '(echo b; echo a; seq 100000) | @sort -c; echo $?'},
    # --help
    {'args': ['--help'], 'help': True}, {'args': ['-n', '--help', '--bogus'], 'help': True},
    S('--bogus', '--help'),
    # the old fixed cases
    S('-g', stdin='nan\n-nan\nNaN\n1\nx\n-inf\n'), S('-M', stdin='JAN\nfeb\n mar\nxyz\n\n'), S('-g', '-n', 'in'),
    S('-M', '-h', 'in'), S('-n', '-d', 'in'), S('-V', '-i', 'in'), S('-k1,1gM', 'in'), S('-gM', 'in'), S('-k1g', '-k2M', 'in'),
]

cases = list(FIXED)
nfixed = len(cases)
for _ in range(CASES):
    c = rand_case()
    c['files'] = {n: open(os.path.join(d, n), 'rb').read() for n in ('in', 'in2', 'in3') if n in c['args']}
    cases.append(c)
bad = 0
write('in', '3\n1\n2\n')
for i, c in enumerate(cases):
    if 'files' in c:
        for n, data in c['files'].items():
            write(n, data)
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 15:
            print('MISMATCH:', c.get('sh') or c['args'], c.get('env', ''))
            if c.get('stdin') is not None:
                print('  stdin:', repr(c['stdin'][:200]))
            for name, data in c.get('files', {}).items():
                print('  %s: %r' % (name, data[:300]))
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:400] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:400] if isinstance(y, bytes) else y))
print('sort_compare: %d cases (%d fixed, %d random), %d mismatches' % (len(cases), nfixed, len(cases) - nfixed, bad))
os.chmod(os.path.join(d, 'noread'), 0o600)
shutil.rmtree(d)
sys.exit(1 if bad else 0)
