#!/usr/bin/env python3
"""Side-by-side test of nebox od against GNU coreutils od.
Usage: tests/od_compare.py path/to/nebox [random-cases]
Fixtures on /dev/shm: text, all byte values, repeated blocks, IEEE single,
double and x87 values (zeros, subnormals, inf, nan, extremes), odd
lengths and a file over 64 KiB. Fixed cases cover every -t type and size,
the old letters, -A, -j/-N with multipliers, -S, -v, -w, --endian,
--traditional and the old offset operands, standard input from files and
pipes (with -N leaving the rest of a shared pipe), several files, missing
files, write errors and option errors; random cases combine random types,
widths, skips and limits. stdout, stderr and exit status must match."""
import os, random, shutil, struct, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 500
d = tempfile.mkdtemp(prefix='od-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
GNU = '/usr/bin/od'
rnd = random.Random(23)
fl = [0.0, -0.0, 1.0, -1.5, 3.14159, 1e-45, 1.17549435e-38, 3.4028235e38, float('inf'), float('-inf'), float('nan'), 0.1, 123456.789, -2.5e-10]
dbl = [0.0, -0.0, 1.0, 0.1, 1/3, 5e-324, 2.2250738585072014e-308, 1.7976931348623157e308, float('inf'), float('nan'), -1e100, 6.02214076e23]
def x87(m, se):
    return struct.pack('<QH', m, se) + b'\0' * 6
ld = [x87(0, 0), x87(1 << 63, 0x3fff), x87(0xc000000000000000, 0xbfff), x87(1, 0), x87(1 << 63, 0x7fff), x87(0xc000000000000000, 0x7fff),
      x87(0xffffffffffffffff, 0x7ffe), x87(0xaaaaaaaaaaaaaaaa, 0x3ffd), x87(1 << 63, 1), x87(0x8000000000000001, 0x4000)]
F = {
    't': b'Hello, world!\nThe quick brown fox\tjumps\x00over\x07the lazy dog.\r\n',
    'all': bytes(range(256)),
    'rep': b'A' * 64 + b'B' * 16 + b'A' * 48 + b'C' * 5,
    'rep2': b'\0' * 100,
    'f4': b''.join(struct.pack('<f', x) for x in fl),
    'f8': b''.join(struct.pack('<d', x) for x in dbl),
    'f16': b''.join(ld),
    'odd': bytes(rnd.getrandbits(8) for _ in range(37)),
    'one': b'x',
    'e': b'',
    'big': bytes(rnd.getrandbits(8) for _ in range(70000)),
    'str': b'ab\0abc\0abcd\0\x01xyzw\0\x80hello world\0tail',
}
for k, v in F.items():
    open(os.path.join(d, k), 'wb').write(v)
os.mkdir(os.path.join(d, 'dir'))
CASES = [
    't', '-c t', '-a t', '-b t', '-d t', '-o t', '-x t', '-s t', '-i t', '-l t', '-e f8', '-f f4', '-D t', '-O t', '-X t', '-H t',
    '-F f8', '-I t', '-L t', '-B t', '-h t', '-An -tx1 t', '-tx1z t', '-tc -tx1 t', '-ta -to1 -td1 t', '-tx2z odd', '-tu8 -tx8 big -N 64',
    '-td1 all', '-td2 all', '-td4 all', '-td8 all', '-tu1 all', '-tu2 all', '-tu4 all', '-tu8 all', '-to1 all', '-to2 all', '-to4 all',
    '-to8 all', '-tx1 all', '-tx2 all', '-tx4 all', '-tx8 all', '-tdC all', '-tdS all', '-tdI all', '-tdL all', '-tc all', '-ta all',
    '-tf4 f4', '-tfF f4', '-tf8 f8', '-tfD f8', '-tfL f16', '-tf16 f16', '-tf f8', '-tfF -tx4 f4', '-tf4 all', '-tf8 all', '-tfL all',
    '-tfL -tx1 f16', '--endian=big -tx2 all', '--endian=little -tx4 all', '--endian=big -tf8 f8', '--endian=big -tf4 f4', '--endian=b -tx2 t',
    '--endian=x t', '-td3 t', '-td16 t', '-tf2 t', '-tf5 t', '-tq t', '-t t', '-tx1q t', '-td99999999999999999999 t', '-tx1 -tq -tc t',
    '-Ad t', '-Ax t', '-Ao t', '-An t', '-Aq t', '-A dx t', '-j5 t', '-j 0x10 t', '-j 1k big', '-j b big', '-j 3 -N 7 t', '-N 0 t', '-N 1 t',
    '-N 100 t', '-N 2k big', '-j 1000 t', '-j x t', '-N x t', '-j 18446744073709551615 -N 2 t', '-j 5 t t', '-j 70 t t', '-j 66000 big t',
    '-v rep', 'rep', '-tx1 rep', 'rep2', '-v rep2', '-w4 t', '-w t', '-w0 t', '-w3 t', '-w3 -tx2 t', '-w 5 t', '-wx t', '-w8 -tfL f16',
    '-w12 -tx4z t', '-S t', '-S 4 str', '-S2 str', '--strings str', '--strings=5 str', '-S 3 -N 20 str', '-S 3 -j 3 str', '-S 3 -tx1 str',
    '-Sx str', '-S0 str', 't +10', 't 10', 't +0x10', 't +10.', 't 10.', 't +1b', 't +1B', '+5 < t', '-c t +5', '-c t 5',
    '--traditional t 10', '--traditional t 10 20', '--traditional t 10. 100', '--traditional -An t 4 0', '--traditional t t',
    '--traditional t 1 2 3', '--traditional +4 < t', '-Ax --traditional t 4 8', 't e', 'e', 'e t', 'nonexistent', 't nonexistent t',
    'dir', 'dir t', '-c < t', '- < t', 't - < one', '-c -', '--bogus t', '-y t', '--format=x1 t', '--read-bytes=4 t', '--skip-bytes=4 t',
    '--address-radix=x t', '--output-duplicates rep', '--width=8 t', '--width t', '--for=x1 t',
    'cat t | @ -c', 'cat big | @ -tx1 -N 10', '(@ -N 4 -c; cat) < t', 'cat t | (@ -N 4 -c; cat)', 'cat t | @ -j 10 -c', 'cat big | @ -j 65000 -tx1',
    't > /dev/full; echo $?', '-tx1 big > /dev/full; echo $?', '-S str > /dev/full; echo $?',
]


def run(c, which):
    prog = GNU if which == 'gnu' else NEBOX + ' od'
    cmd = c.replace('@', prog) if '@' in c else prog + ' ' + c
    p = subprocess.run(['bash', '-c', cmd], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(GNU.encode(), b'od')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


TYPES = ['a', 'c', 'd1', 'd2', 'd4', 'd8', 'u1', 'u2', 'u4', 'u8', 'o1', 'o2', 'o4', 'o8', 'x1', 'x2', 'x4', 'x8', 'f4', 'f8', 'fL', 'dC', 'xS', 'oI', 'uL']
OLD = list('abcdDefFhHiIlLoOsxX')
for k in range(NRAND):
    n = rnd.choice([0, 1, 7, 16, 31, 32, 33, 64, 100, 257])
    data = bytes(rnd.choice([0, 0x41, rnd.getrandbits(8)]) for _ in range(n))
    if rnd.random() < 0.3 and n:
        data = data[:16] * (n // 16 + 1)
    name = 'r%d' % k
    open(os.path.join(d, name), 'wb').write(data)
    opts = []
    for _ in range(rnd.randint(0, 3)):
        if rnd.random() < 0.75:
            t = rnd.choice(TYPES) + ('z' if rnd.random() < 0.15 else '')
            opts.append('-t' + t)
        else:
            opts.append('-' + rnd.choice(OLD))
    if rnd.random() < 0.3: opts.append('-A' + rnd.choice('doxn'))
    if rnd.random() < 0.3: opts.append('-j%d' % rnd.randint(0, 40))
    if rnd.random() < 0.3: opts.append('-N%d' % rnd.randint(0, 60))
    if rnd.random() < 0.25: opts.append('-w%d' % rnd.choice([1, 2, 4, 8, 12, 16, 24, 32, 5]))
    if rnd.random() < 0.15: opts.append('-v')
    if rnd.random() < 0.15: opts.append('--endian=big')
    CASES.append(' '.join(opts + [name]))

# r134 holds a pseudo-denormal long double (exponent 0, integer bit set):
# glibc's printf ignores the integer bit (3.05e-4932), nelibc reads the
# value as the FPU does (6.42e-4932, as musl prints it). README notes it.
KNOWN = {'-txS -to4 -tfL -An r134'}
bad = known = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n and c in KNOWN:
        known += 1
        continue
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:400]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:400]))
print('od_compare: %d cases, %d mismatches, %d known (pseudo-denormal)' % (len(CASES), bad, known))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
