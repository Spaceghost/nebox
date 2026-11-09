#!/usr/bin/env python3
"""Side-by-side test of nebox free against procps-ng 4.0.2 free.
Usage: tests/free_compare.py path/to/nebox [random-cases]
/proc/meminfo changes between runs, so values are compared on fixed
snapshots: inside a private user and mount namespace (unshare -rm) a
fixture file is bound over /proc/meminfo and both programs read it. The
fixtures are a copy of the live file and synthetic ones (MemAvailable
missing, above MemTotal, MemFree above MemTotal, Low/High fields,
CommitLimit below Committed_AS, values that overflow when scaled, signs,
lines without a colon, no final newline, NUL bytes, duplicate keys, more
than 8191 bytes, an empty file) with every unit and display option and
-c/-s repeats; then random values with random options. On the live file
only the stable MemTotal/SwapTotal columns are compared exactly and the
rest with digits masked. Option errors, --help, output to /dev/full.
stdout, stderr and exit status must match; -V differs by design (nebox's
line) and only its status is compared."""
import os, random, re, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 300
d = tempfile.mkdtemp(prefix='free-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
rnd = random.Random(5)
NS = ['unshare', '-m'] if os.geteuid() == 0 else ['unshare', '-rm']

live = open('/proc/meminfo', 'rb').read()
FIX = {'live': live}


def mem(**kw):
    keys = ['MemTotal', 'MemFree', 'MemAvailable', 'Buffers', 'Cached', 'SwapCached', 'Shmem', 'SReclaimable',
            'SwapTotal', 'SwapFree', 'CommitLimit', 'Committed_AS', 'LowTotal', 'LowFree', 'HighTotal', 'HighFree']
    base = dict(MemTotal=16000000, MemFree=3000000, MemAvailable=9000000, Buffers=200000, Cached=5000000,
                SwapCached=1000, Shmem=400000, SReclaimable=300000, SwapTotal=8000000, SwapFree=7000000,
                CommitLimit=16000000, Committed_AS=12000000)
    base.update(kw)
    return ''.join('%s:%s%s kB\n' % (k, ' ' * max(1, 16 - len(k)), base[k]) for k in keys if base.get(k) is not None).encode()


FIX['basic'] = mem()
FIX['noavail'] = mem(MemAvailable=None)
FIX['availbig'] = mem(MemAvailable=20000000)
FIX['freebig'] = mem(MemAvailable=20000000, MemFree=17000000)
FIX['lohi'] = mem(LowTotal=900000, LowFree=100000, HighTotal=15000000, HighFree=2000000)
FIX['hifree'] = mem(LowTotal=900000, LowFree=950000, HighTotal=100, HighFree=200)
FIX['commitneg'] = mem(CommitLimit=1000, Committed_AS=5000000)
FIX['huge'] = mem(MemTotal=18014398509481983, MemFree=18014398509481000, SwapTotal=2 ** 63, SwapFree=2 ** 62)
FIX['max'] = mem(MemTotal=2 ** 64 - 1, MemFree=99999999999999999999999, MemAvailable=-5, Buffers='+12')
FIX['small'] = mem(MemTotal=1, MemFree=0, MemAvailable=1, Buffers=0, Cached=0, Shmem=0, SReclaimable=0,
                   SwapTotal=0, SwapFree=0, CommitLimit=0, Committed_AS=0)
FIX['round'] = mem(MemTotal=1048576, MemFree=1023, MemAvailable=1024, Buffers=1025, Cached=10239, Shmem=10240,
                   SReclaimable=102399, SwapTotal=1073741824, SwapFree=1048063, CommitLimit=999, Committed_AS=1000)
FIX['round2'] = mem(MemTotal=976562, MemFree=9765, MemAvailable=97, Buffers=976, Cached=9536, Shmem=95367,
                    SReclaimable=953674, SwapTotal=9765625, SwapFree=99, CommitLimit=104857, Committed_AS=1048575)
FIX['nocolon'] = b'MemTotal: 1000 kB\nbroken line\nMemFree: 300 kB\nSwapTotal: 50 kB\n'
FIX['nonl'] = b'MemTotal: 1000 kB\nMemFree: 300 kB'
FIX['nul'] = b'MemTotal: 1000 kB\nMemF\0ree: 300 kB\nSwapTotal: 50 kB\n'
FIX['dup'] = b'MemTotal: 1000 kB\nMemTotal: 2000 kB\nMemFree: 300\nMemFree:\n55\nShmem:x\nBuffers:   7 trailing\n'
FIX['spaces'] = b' MemTotal: 1000 kB\nMemTotal : 5\nMemTotal:\t\t 4242 kB\nSwapFree: -3 kB\n'
FIX['bigfile'] = b''.join(b'Filler%d: %d kB\n' % (k, k) for k in range(700)) + b'MemTotal: 777 kB\n'
FIX['empty'] = b''
FIX['onlykey'] = b'MemTotal:'
for k, v in FIX.items():
    open(os.path.join(d, 'm_' + k), 'wb').write(v)

OPTS = ['', '-b', '-k', '-m', '-g', '--tera', '--peta', '--kilo', '--mega', '--giga', '--tebi', '--pebi', '-h', '--si',
        '-h --si', '-l', '-t', '-v', '-w', '-hltvw', '-b -l -t -v -w', '--si -m', '--si -b', '--si -l -t -v', '-h -w -t',
        '--human --lohi --total --committed --wide', '-g -h', '--peta -h --si', '--bytes --wide', '--kibi', '--mebi',
        '--gibi', '-c 3 -s 0.01', '-c 2 -s 0,01 -t', '--count=2 --seconds=0.001', '-c1', '-s 0.01 -c 2 -w']
CASES = []
for fx in FIX:
    if fx == 'live':
        continue
    for o in OPTS:
        CASES.append(('ns', fx, '@ ' + o))
for fx in ['live']:
    for o in OPTS:
        CASES.append(('ns', fx, '@ ' + o))
for a in ['-L', '--line', '-b -k', '-m -m', '--kilo --mega', '-k --tebi', '-s 0', '-s -1', '-s x', "-s ''", '-s 1x',
          '-s 1.5x', '-s 1.2.3', '-s .', '-s " "', '-s 0.0000001', '-s +0.5 -c 1', '-s " 1" -c 1', '-s 1, -c 1', '-c 0',
          '-c -1', '-c x', "-c ''", '-c 5x', '-c 99999999999999999999', '-c 2147483648', '-c 4294967297 -s 0.01',
          '-c " 1"', '-c +1', '-c', '-s', 'x', '-- x', '--', '-x', '--bogus', '--he', '--help', '--h', '-V', '--version',
          '--help x', '-V x', '--help > /dev/full; echo $?', '> /dev/full; echo $?', '-c 2 -s 0.01 > /dev/full; echo $?',
          '-V > /dev/full; echo $?', '-bh', '-hb', '--count=1 --human', '--seconds', '--si=1', '--wide=x']:
    CASES.append(('ns', 'basic', '@ ' + a))
CASES.append(('live', None, '@'))
CASES.append(('live', None, '@ -t -l -v -w'))
CASES.append(('live', None, '@ -b -t'))
CASES.append(('live', None, '@ -h'))
CASES.append(('live', None, '@ -s 0.05 | head -n 4'))
CASES.append(('ns', 'basic', 'timeout 0.25 @ -s 0.1 | head -n 8'))
NOVERSION = {'@ -V', '@ --version', '@ -V x'}

for k in range(NRAND):
    vals = {}
    for key in ['MemTotal', 'MemFree', 'MemAvailable', 'Buffers', 'Cached', 'Shmem', 'SReclaimable', 'SwapTotal',
                'SwapFree', 'CommitLimit', 'Committed_AS', 'LowTotal', 'LowFree', 'HighTotal', 'HighFree']:
        if rnd.random() < 0.85:
            vals[key] = rnd.choice([0, 1, 999, 1023, 1024, 1025, rnd.randint(0, 10 ** 4), rnd.randint(0, 10 ** 7),
                                    rnd.randint(0, 10 ** 9), rnd.randint(0, 10 ** 12), rnd.randint(0, 2 ** 64 - 1)])
    name = 'r%d' % k
    open(os.path.join(d, 'm_' + name), 'wb').write(''.join('%s: %d kB\n' % kv for kv in vals.items()).encode())
    opts = rnd.sample(['-h', '--si', '-l', '-t', '-v', '-w', rnd.choice(['-b', '-k', '-m', '-g', '--tera', '--peta',
                       '--kilo', '--mega', '--giga', '--tebi', '--pebi'])], rnd.randint(0, 4))
    CASES.append(('ns', name, '@ ' + ' '.join(opts)))

LIVE_MASK = re.compile(rb'[0-9]+(\.[0-9]+)?')


def run(c, which):
    mode, fx, cmd = c
    prog = 'free' if which == 'gnu' else NEBOX + ' free'
    sh = cmd.replace('@', prog)
    if mode == 'ns':
        sh = 'mount --bind %s/m_%s /proc/meminfo && %s' % (d, fx, sh)
        argv = NS + ['sh', '-c', sh]
    else:
        argv = ['bash', '-c', sh]
    p = subprocess.run(argv, cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    out = p.stdout
    if mode == 'live':
        # MemTotal and SwapTotal hold still; the other columns are masked
        lines = []
        for ln in out.split(b'\n'):
            f = ln.split()
            if f and f[0] in (b'Mem:', b'Swap:') and len(f) > 1:
                lines.append(f[0] + b' ' + f[1] + b' ' + LIVE_MASK.sub(b'N', b' '.join(f[2:])))
            else:
                lines.append(LIVE_MASK.sub(b'N', b' '.join(f)))
        out = b'\n'.join(lines)
    return p.returncode, out, p.stderr


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if c[2] in NOVERSION:
        g, n = (g[0], b'', g[2]), (n[0], b'', n[2])
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:400]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:400]))
print('free_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
