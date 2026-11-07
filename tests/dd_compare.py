#!/usr/bin/env python3
"""Side-by-side test of `nebox dd` against GNU dd (coreutils).
Usage: tests/dd_compare.py path/to/nebox [random-cases] [seed]
Each case runs one shell command twice in fresh copies of a fixture
directory, once with GNU dd and once with nebox dd, and compares standard
output, standard error, the exit status and every file left behind. The
timing part of the statistics line ("..., 0.000123 s, 1.2 MB/s") is the
only thing masked."""
import hashlib, os, random, re, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 300
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C', TZ='UTC')
env.pop('POSIXLY_CORRECT', None)
root = tempfile.mkdtemp(prefix='dd-compare-')
fix = os.path.join(root, 'fixture')
os.mkdir(fix)
frng = random.Random(7)
with open(os.path.join(fix, 'text'), 'w') as f:
    for i in range(300):
        f.write(' '.join(frng.choice(['alpha', 'Beta', 'GAMMA', 'delta', '', 'x' * frng.randrange(0, 90)])
                         for _ in range(frng.randrange(0, 6))) + '\n')
with open(os.path.join(fix, 'bin'), 'wb') as f:
    f.write(bytes(frng.randrange(256) for _ in range(70001)))
with open(os.path.join(fix, 'zeros'), 'wb') as f:
    f.write(b'\0' * 20000 + b'end' + b'\0' * 9000)
with open(os.path.join(fix, 'odd'), 'wb') as f:
    f.write(b'abcdefg')
with open(os.path.join(fix, 'empty'), 'wb') as f:
    pass
with open(os.path.join(fix, 'recs'), 'wb') as f:
    f.write(b'short    record  ' + b'x' * 20 + b'      ' + b'last   ')
with open(os.path.join(fix, 'out'), 'wb') as f:
    f.write(b'0123456789' * 50)
os.mkdir(os.path.join(fix, 'adir'))

TIMING = re.compile(rb'copied, [0-9.e+-]+ s, [^\n]*')


def tree(d):
    out = []
    for dp, dn, fn in os.walk(d):
        dn.sort()
        for n in sorted(fn):
            p = os.path.join(dp, n)
            st = os.stat(p)
            h = hashlib.sha1()
            if st.st_size <= (16 << 20):
                with open(p, 'rb') as f:
                    h.update(f.read())
            out.append((os.path.relpath(p, d), h.hexdigest(), st.st_size,
                        st.st_blocks if 'sparse' in n else 0))
    return out


def run(cmd, which):
    d = os.path.join(root, which)
    if os.path.exists(d):
        shutil.rmtree(d)
    shutil.copytree(fix, d)
    dd = 'dd' if which == 'gnu' else NEBOX + ' dd'
    c = cmd.replace('DD', dd)
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=60)
    err = TIMING.sub(b'copied, T', p.stderr).replace(NEBOX.encode() + b' dd', b'dd')
    return p.returncode, p.stdout, err, tree(d)


FIXED = [
    'DD if=text of=o', 'DD if=text', 'DD < text', 'DD if=bin of=o bs=1000 count=7',
    'DD if=bin of=o ibs=300 obs=7000', 'DD if=bin of=o bs=4096 skip=3 count=2',
    'DD if=bin of=o ibs=1 skip=70000', 'DD if=bin of=o skip=1000', 'DD if=odd of=o skip=2 bs=3',
    'DD if=odd bs=3 count=2 status=noxfer', 'DD if=odd status=none', 'DD if=odd status=progress',
    'DD if=empty of=o', 'DD if=odd of=out seek=3 bs=4', 'DD if=odd of=out seek=3 bs=4 conv=notrunc',
    'DD if=odd of=out conv=notrunc', 'DD if=odd of=out', 'DD if=odd of=newf seek=5',
    'DD if=odd of=out seek=2000', 'DD if=text conv=ucase', 'DD if=text conv=lcase',
    'DD if=odd conv=swab', 'DD if=odd conv=swab bs=2', 'DD if=odd conv=swab ibs=3 obs=1',
    'DD if=text cbs=20 conv=block', 'DD if=text cbs=8 conv=block,sync', 'DD if=recs cbs=10 conv=unblock',
    'DD if=recs cbs=10 conv=unblock,ucase', 'DD if=text conv=ebcdic cbs=40', 'DD if=text conv=ibm cbs=40',
    'DD if=text conv=ebcdic cbs=40 of=e; DD if=e conv=ascii cbs=40', 'DD if=odd conv=ebcdic', 'DD if=bin conv=ascii',
    'DD if=odd bs=5 conv=sync', 'DD if=odd ibs=5 obs=3 conv=sync', 'DD if=odd cbs=4 bs=5 conv=sync,block',
    'DD if=zeros of=sparse bs=4096 conv=sparse', 'DD if=zeros of=sparse bs=512 conv=sparse,notrunc',
    'DD if=zeros of=sparse2 bs=1000 count=5 conv=sparse', 'DD if=odd of=out conv=excl',
    'DD if=odd of=newf conv=nocreat', 'DD if=odd of=out conv=nocreat', 'DD if=odd of=out conv=excl,nocreat',
    'DD if=odd conv=block,unblock', 'DD if=odd conv=lcase,ucase', 'DD if=odd conv=ascii,ebcdic',
    'DD if=odd conv=foo', 'DD if=odd conv=sync,foo,bar', 'DD if=odd iflag=foo', 'DD if=odd oflag=fullblock',
    'DD if=odd iflag=binary', 'DD if=odd oflag=cio', 'DD if=odd status=bogus', 'DD if=odd status=none,noxfer',
    'DD if=odd status=noxfer,none', 'DD foo=bar', 'DD foo', 'DD if=odd bs=0', 'DD if=odd bs=-1',
    'DD if=odd bs=abc', 'DD if=odd bs=1x', 'DD if=odd bs=2x3', 'DD if=odd bs=0x3', 'DD if=odd bs=00x3 count=1',
    'DD if=odd bs=1k', 'DD if=odd bs=1kB', 'DD if=odd bs=1KiB', 'DD if=odd bs=1K', 'DD if=odd bs=1kiB',
    'DD if=odd bs=K', 'DD if=odd bs=1b', 'DD if=odd bs=1w', 'DD if=odd bs=3c', 'DD if=odd bs=1MB count=1',
    'DD if=odd bs=99999999999999999999', 'DD if=odd bs=9223372036854775807', 'DD if=odd count=99999999999999999999',
    'DD if=odd skip=1E', 'DD if=odd bs=+3', 'DD if=odd bs=" 3"', 'DD if=odd bs=1Z',
    'DD if=bin bs=100 count=3B', 'DD if=bin bs=100 count=250B', 'DD if=bin bs=100 skip=150B count=1',
    'DD if=bin bs=100 iflag=skip_bytes,count_bytes skip=50 count=75', 'DD if=odd of=out bs=3 seek=4B',
    'DD if=odd of=out bs=3 oflag=seek_bytes seek=5', 'DD if=bin count=1KB', 'DD if=bin bs=10 count=2x3B',
    'DD if=bin bs=10 count=2Bx3B', 'DD if=odd count=0', 'DD if=nofile', 'DD if=odd of=nodir/x',
    'DD if=adir', 'DD if=odd iflag=directory', 'DD if=adir iflag=directory count=0', 'DD if=adir iflag=directory',
    'DD if=odd of=adir', 'DD if=odd iflag=nofollow', 'DD if=odd bs=2 iflag=fullblock count=2',
    'cat bin | DD bs=4096 count=3 iflag=fullblock of=o', 'cat odd | DD bs=2 skip=1',
    'cat bin | DD of=o bs=1000 skip=2 count=2 iflag=fullblock', 'cat odd | DD of=o ibs=1 skip=10',
    'DD if=odd of=/dev/null', 'DD if=/dev/zero of=o bs=1000 count=3', 'DD if=/dev/zero bs=1M count=3 of=/dev/null',
    'DD if=/dev/zero bs=1000 count=1001 of=/dev/null', 'DD if=/dev/zero bs=1 count=1 of=/dev/null',
    'DD if=/dev/zero bs=1024 count=1 of=/dev/null', 'DD if=/dev/zero bs=999 count=1 of=/dev/null',
    'DD if=/dev/zero bs=1 count=0 of=/dev/null', 'DD if=/dev/zero bs=999999 count=1 of=/dev/null',
    'DD if=/dev/zero bs=1048575 count=1 of=/dev/null', 'DD if=/dev/zero bs=1048577 count=1 of=/dev/null',
    'DD if=/dev/zero bs=1047552 count=1 of=/dev/null', 'DD if=/dev/zero bs=1048064 count=1 of=/dev/null',
    'DD if=/dev/zero bs=9950 count=1 of=/dev/null', 'DD if=/dev/zero bs=9949 count=1 of=/dev/null',
    'DD if=odd of=out iflag=append', 'DD if=odd of=out oflag=append conv=notrunc', 'DD if=odd oflag=sync,dsync of=o',
    'DD if=odd of=o conv=fsync', 'DD if=odd of=o conv=fdatasync', 'DD if=odd iflag=nocache of=o',
    'DD if=odd oflag=nocache of=o', 'DD if=odd iflag=nocache count=0', 'cat odd | DD iflag=nocache count=0',
    'DD if=odd iflag=direct,nocache', 'DD if=odd of=o oflag=direct', 'DD if=bin of=o bs=4096 iflag=direct oflag=direct',
    'DD if=odd -x', 'DD --foo', 'DD -- if=odd', 'DD -- -x', 'DD - ', 'DD --version=1', 'DD if=odd of=out seek=1 bs=99999999999999',
    'DD if=odd bs=3 count=1 skip=2B', 'DD if=odd iseek=2 bs=1', 'DD if=odd of=out oseek=2 bs=1 conv=notrunc',
    'DD if=odd skip=1x', 'DD if=odd if=text count=1', 'DD if= ', 'DD of= if=odd',
    "DD if='a b'", "DD if=\"it's\"", "DD if='a:b'", "DD if=\"$(printf 'x\\ty')\"", "DD if=odd of=\"$(printf 'n\\nb')/o\"",
    'DD if=odd conv=swab,sync ibs=4 obs=3', 'DD if=text conv=unblock cbs=0', 'DD if=text conv=block',
    'DD if=text bs=7 conv=unblock cbs=3 count=4',
]

CONVS = ['ucase', 'lcase', 'swab', 'sync', 'notrunc', 'block', 'unblock', 'ebcdic', 'ascii', 'ibm', 'sparse', 'noerror']


def rand_size():
    return rng.choice(['1', '2', '3', '7', '16', '100', '512', '1000', '4096', '1k', '2b', '3w', '5000'])


def rand_case():
    parts = ['DD']
    src = rng.choice(['text', 'bin', 'odd', 'empty', 'zeros', 'recs'])
    piped = rng.random() < 0.2 and src not in ('bin', 'zeros')
    if not piped:
        parts.append('if=' + src)
    if rng.random() < 0.6:
        parts.append('of=' + rng.choice(['o', 'out']))
    r = rng.random()
    if r < 0.4:
        parts.append('bs=' + rand_size())
    elif r < 0.8:
        if rng.random() < 0.7:
            parts.append('ibs=' + rand_size())
        if rng.random() < 0.7:
            parts.append('obs=' + rand_size())
    if rng.random() < 0.4:
        parts.append('cbs=' + rng.choice(['1', '3', '10', '40']))
    for k in ('count', 'skip', 'seek'):
        if rng.random() < 0.35:
            parts.append('%s=%d%s' % (k, rng.randrange(0, 40), rng.choice(['', '', 'B'])))
    if rng.random() < 0.5:
        parts.append('conv=' + ','.join(rng.sample(CONVS, rng.choice([1, 1, 2, 3]))))
    if rng.random() < 0.3:
        parts.append('iflag=' + ','.join(rng.sample(['fullblock', 'count_bytes', 'skip_bytes'], rng.choice([1, 2]))))
    if rng.random() < 0.15:
        parts.append('oflag=seek_bytes')
    parts.append('status=' + rng.choice(['none', 'noxfer', 'none', 'noxfer']) if rng.random() < 0.5 else '')
    cmd = ' '.join(p for p in parts if p)
    if piped:
        cmd = 'cat %s | %s' % (src, cmd)
    if 'of=' not in cmd:
        cmd += ' | od -An -tx1 | tail -3'
    return cmd


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 15:
            print('MISMATCH:', c)
            for name, a, b in zip(('status', 'stdout', 'stderr', 'tree'), g, n):
                if a != b:
                    print('  %s gnu:   %r' % (name, a if not isinstance(a, bytes) else a[:400]))
                    print('  %s nebox: %r' % (name, b if not isinstance(b, bytes) else b[:400]))
print('dd_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(root)
sys.exit(1 if bad else 0)
