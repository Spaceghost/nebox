#!/usr/bin/env python3
"""Side-by-side test of nebox strings against GNU binutils 2.40 strings.
Usage: tests/strings_compare.py path/to/nebox [random-cases]
Fixtures on /dev/shm: text, random binary, UTF-8 (valid 2/3/4-byte
sequences, stray continuation bytes, truncated sequences at the end of a
file), UTF-16/32 in both byte orders with odd tails, whitespace runs, and
ELF files (executables, a static binary, a shared library, relocatable
objects, a big-endian ELF32, an ELF without section headers, one with a
corrupt e_shstrndx, a truncated one, a core-type header, an archive).
Every option and spelling (-a -d -f -n --bytes -NUM -t o/d/x -o -w -e
s/S/b/l/B/L -s -U d/l/e/i/x/h -T -h -H -v -V), getopt's permutation as
it affects -NUM, empty -t/-e arguments, the bad-option and bad-argument
usage, "-" between files, missing files, directories, ENOTDIR, @file
response files (quotes, backslashes, nesting, whitespace-only, missing,
directories, endless recursion), standard input, and random inputs with
random options. stdout, stderr and exit status must match; -v/-V print
nebox's line by design, so only their status is compared, and the usage
on stdout omits GNU's bug-report line."""
import os, random, re, shutil, struct, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 400
d = tempfile.mkdtemp(prefix='strings-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
rnd = random.Random(3)
F = {
    'text': b'hello world\nab\nabc\nabcd\n\tTabbed line\r\nfin',
    'bin': bytes(rnd.getrandbits(8) for _ in range(5000)),
    'ws': b'a b\tc\nd\re\x0bf\x0cg  h\n\n\n   \t\t\x00xyzw\x00',
    'utf8': 'héllo wörld \U0001F600 end 中文字 ok\n'.encode() + b'\xc3x \xe2\x82 \xf0\x9f\x98 abc\x80\x80def'
            + b'\xff\xfe abcde \xc3\xa9\xc3\xa9\xc3\xa9\xc3\xa9\n\xf8\x88\x80\x80\x80 tail\xc3',
    'utf8b': 'abécééé \U0001F600\U0001F600\U0001F600\U0001F600 xy€z'.encode() + b'\xe2\x82\xac\xe2',
    'u16le': 'hello wide\x00 world\n'.encode('utf-16-le') + b'\x41',
    'u16be': 'hello wide world\n'.encode('utf-16-be') + b'\x00\x41\x00',
    'u32le': 'hello quad world\n'.encode('utf-32-le') + b'\x41\x00\x00',
    'u32be': 'hello quad world\n'.encode('utf-32-be') + b'\x00\x00',
    'mixed16': b'\x00a\x00b\x00c\x00d\x00e' + b'a\x00b\x00c\x00d\x00' + b'\x00\x00\x00z\x00z\x00z\x00z',
    'empty': b'',
    'short': b'abc',
    'nl': b'\n' * 10,
    'hi': bytes(range(128, 256)) * 3 + b'abcd' + bytes(range(256)),
    'long': b'y' * 20000 + b'\x00' + b'z' * 3,
}


def elf32be():
    # a minimal big-endian ELF32 relocatable object: .data, .rodata(alloc), .comment, .bss, .shstrtab
    names = b'\0.data\0.rodata\0.comment\0.bss\0.shstrtab\0'
    data = b'big endian data\0more\0'
    ro = b'readonly strings\0xyzzy\0'
    com = b'comment not loaded\0'
    off = 52
    blobs = []
    secs = []
    for nm, typ, flags, blob in [(1, 1, 3, data), (7, 1, 2, ro), (15, 1, 0, com), (24, 8, 3, b''), (29, 3, 0, names)]:
        secs.append((nm, typ, flags, off, len(blob) if typ != 8 else 64))
        blobs.append(blob)
        off += len(blob)
    shoff = (off + 3) & ~3
    body = b''.join(blobs) + b'\0' * (shoff - off)
    hdr = b'\x7fELF\x01\x02\x01' + b'\0' * 9 + struct.pack('>HHIIIIIHHHHHH', 1, 8, 1, 0, 0, shoff, 0, 52, 0, 0, 40, 6, 5)
    sh = b'\0' * 40
    for nm, typ, flags, o, sz in secs:
        sh += struct.pack('>IIIIIIIIII', nm, typ, flags, 0, o, sz, 0, 0, 1, 0)
    return hdr + body + sh


F['be32.o'] = elf32be()
noshdr = bytearray(open('/bin/true', 'rb').read())
noshdr[0x28:0x30] = b'\0' * 8   # e_shoff
noshdr[0x3c:0x40] = b'\0' * 4   # e_shnum, e_shstrndx
F['noshdr'] = bytes(noshdr)
badidx = bytearray(open('/bin/true', 'rb').read())
badidx[0x3e:0x40] = struct.pack('<H', 1)
F['badidx'] = bytes(badidx)
core = bytearray(open('/bin/true', 'rb').read())
core[0x10:0x12] = struct.pack('<H', 4)
F['core'] = bytes(core)
F['trunc'] = open('/bin/true', 'rb').read()[:3000]
F['half'] = open('/bin/true', 'rb').read()[:20000]
for k, v in F.items():
    open(os.path.join(d, k), 'wb').write(v)
for name, src in [('true', '/bin/true'), ('crt1.o', '/usr/lib/x86_64-linux-gnu/crt1.o'),
                  ('crti.o', '/usr/lib/x86_64-linux-gnu/crti.o'), ('libc', '/usr/lib/x86_64-linux-gnu/libc.so.6'),
                  ('nonshared.a', '/usr/lib/x86_64-linux-gnu/libc_nonshared.a'), ('nebox', NEBOX)]:
    if os.path.exists(src):
        shutil.copy(src, os.path.join(d, name))
        F[name] = None
os.mkdir(os.path.join(d, 'dir'))
open(os.path.join(d, 'noread'), 'wb').write(b'secret string\n')
os.chmod(os.path.join(d, 'noread'), 0)
# response files
R = {
    'r1': b'-n 3 text',
    'r2': b'-t x "short" \'ws\'',
    'r3': b'-f @r1 text',
    'r4': b'  \n\t ',
    'r5': b'-n\\ 6 a\\"b "x y" \'q"r\' text',
    'r6': b'@r6',
    'r7': b'-n 2\0-w text',
    'r8': b'-e l u16le "unterminated',
    'r9': b'@nosuchresp text\n-o\n',
    'r10': b'',
    'r11': b'trailing\\',
}
for k, v in R.items():
    open(os.path.join(d, k), 'wb').write(v)

FILES = [k for k in F]
CASES = []
for f in FILES:
    CASES.append('@ ' + f)
    CASES.append('@ -d ' + f)
for f in ['true', 'crt1.o', 'libc', 'be32.o', 'nebox', 'noshdr', 'badidx', 'core', 'trunc', 'half', 'nonshared.a', 'text']:
    if f in F:
        for o in ['-d -t x', '-d -f -n 8', '-d -e S', '-d -U e', '-d -U x -n 3', '-d -T elf64-x86-64', '-d -T elf32-i386',
                  '-d -T elf64-little', '-d -T elf32-big', '-d -T binary -n 6', '-d -T bogus', '-a -T bogus', '-d -T srec',
                  '-d -e l', '-d -U i', '- -d', '-d -']:
            CASES.append('@ %s %s | head -c 3000' % (o, f))
for o in ['-a', '-f', '-n 1', '-n 2', '-n 10', '-n 0x8', '-n 010', '-n " 5"', '-n +3', '--bytes=6', '--bytes 6', '-3', '-12',
          '-1 -2', '-t o', '-t d', '-t x', '-o', '-to', '--radix=d', '--radix x', '-o -t x', '-t x -o', '-w', '-w -n 2',
          '--include-all-whitespace', '-e s', '-e S', '-e b', '-e l', '-e B', '-e L', '--encoding=l', '-eb', '-s ,', "-s ''",
          '-s "<SEP>\n"', '--output-separator=--', '-f -t d -n 6', '-U d', '-U l', '-U e', '-U i', '-U x', '-U h',
          '--unicode=escape', '--unicode=hex -n 2', '-U i -n 2', '-U e -n 1', '-U x -e l', '-U e -w', '-U d -e S',
          '-e S -n 2', '-e S -w', '-T bogus', '-f -o -w -n 3 -s "|"']:
    for f in ['text', 'ws', 'utf8', 'utf8b', 'u16le', 'u16be', 'u32le', 'u32be', 'mixed16', 'hi', 'bin', 'long']:
        CASES.append('@ %s %s' % (o, f))
CASES += [
    '@ text short ws', '@ -f text short ws', '@ text - ws', '@ -d text - true', '@ -', '@ - -', '@ -- -', '@',
    '@ < text', 'cat text | @', 'cat utf8 | @ -U x', 'cat u16le | @ -e l -t d', '@ -f < text', '@ -f - < text',
    '@ nosuch', '@ text nosuch ws', '@ dir', '@ text/x', '@ noread', '@ noread text', "@ ''", '@ dir nosuch text',
    '@ -n 0 text', '@ -n x text', '@ -n 5x text', '@ -n "" text', '@ -n -1 text', '@ -n 4294967296 text',
    '@ -n 4294967297 text', '@ -n 99999999999999999999 text', '@ -n 0x text', '@ -n 08 text', '@ -0 text', '@ -0x3 text',
    '@ text -3', '@ -3 text -4', '@ -5a text', '@ -a5 text', '@ -a -5 text', '@ text -5a', '@ -f5 text ws', '@ text ws -2',
    '@ -2 -- -n', '@ -t text', '@ -t "" text', '@ -t "" ""', '@ -t xx text', '@ -t q text', '@ --radix= text',
    '@ --radix= "" text', '@ -e text', '@ -e "" text', '@ -e "" "" -n 0 text', '@ -e "" ""', '@ -e q text',
    '@ -e ss text', '@ --encoding= text', '@ -U text', '@ -U q text', '@ -U default -n 0 text', '@ --unicode=locale text',
    '@ --unicode=show text', '@ -x', '@ -x text', '@ --bogus text', '@ --b 3 text', '@ --by=3 text', '@ --d true',
    '@ --da true', '@ --e=l u16le', '@ --i text', '@ --o=. text', '@ --p text', '@ --r=d text', '@ --t=bogus text',
    '@ --u=e utf8', '@ --he', '@ --all text', '@ --data text', '@ --print-file-name text', '@ --all=x text',
    '@ -h', '@ -H', '@ --help', '@ -h text', '@ text -h', '@ -v', '@ -V', '@ --version', '@ -v -h', '@ -h -v',
    '@ -n', '@ -T', '@ -s', '@ text -e', '@ text > /dev/full; echo $?', '@ -x 2>/dev/full; echo $?',
    '@ @r1', '@ @r2', '@ @r3', '@ @r4 text', '@ @r5', '@ @r6 text', '@ @r7', '@ @r8', '@ @r9', '@ @r10 short',
    '@ @r11', '@ @nosuch', '@ @', '@ @dir', '@ text @r1', '@ -- @r1', '@ @/dev/null text', '@ @/proc/self/status',
    '@ -f @r2 @r10 text', '@ @r1 -5', '@ -5 @r1',
]
NOVERSION = {'@ -v', '@ -V', '@ --version', '@ -v -h'}

ALPHA = [b'ab \t\n\0', b'abc\x80\xc3\xa9', bytes(range(256)), b'a\0', b'\0b\0c\0\0\0d', b'xy\xe2\x82\xac\xf0\x9f\x98\x80\xc3',
         b'ab\r\x0b\x0c\n ']
for k in range(NRAND):
    alpha = rnd.choice(ALPHA)
    n = rnd.choice([0, 3, 10, 50, 300, 3000])
    data = bytes(rnd.choice(alpha) for _ in range(n))
    name = 'rand%d' % k
    open(os.path.join(d, name), 'wb').write(data)
    opts = []
    for o in rnd.sample(['-n %d' % rnd.randint(1, 8), '-e ' + rnd.choice('sSblBL'), '-w', '-t ' + rnd.choice('odx'), '-f',
                         '-U ' + rnd.choice('dlexih'), '-s ' + rnd.choice([':', "''", '"ab"']), '-%d' % rnd.randint(1, 6),
                         '-o'], rnd.randint(0, 4)):
        opts.append(o)
    if rnd.random() < 0.15:
        CASES.append('cat %s | @ %s' % (name, ' '.join(opts)))
    else:
        CASES.append('@ %s %s' % (' '.join(opts), name))


def run(c, which):
    prog = 'strings' if which == 'gnu' else NEBOX + ' strings'
    cmd = re.sub(r'(^|\| )@(?= |$)', lambda m: m.group(1) + prog, c)
    p = subprocess.run(['bash', '-c', 'ulimit -v 3000000; ' + cmd], cwd=d, env=env,
                       capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    out = p.stdout
    if which == 'gnu' and p.returncode == 0:
        # the usage on stdout omits the bug-report line, by design
        out = out.replace(b'Report bugs to <https://sourceware.org/bugzilla/>\n', b'')
    return p.returncode, out, p.stderr


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if c in NOVERSION:
        g, n = (g[0], b'', g[2]), (n[0], b'', n[2])
    if g != n:
        bad += 1
        if bad > 25:
            print('MISMATCH:', c)
        else:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('strings_compare: %d cases, %d mismatches' % (len(CASES), bad))
os.chmod(os.path.join(d, 'noread'), 0o600)
shutil.rmtree(d)
sys.exit(1 if bad else 0)
