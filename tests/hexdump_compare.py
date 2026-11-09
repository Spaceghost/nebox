#!/usr/bin/env python3
"""Side-by-side test of nebox hexdump/hd against util-linux 2.38.1 hexdump.
Usage: tests/hexdump_compare.py path/to/nebox [random-cases]
Fixtures on /dev/shm: text, all byte values, repeated blocks, zeros, IEEE
floats and doubles, NUL-separated strings, odd lengths, an empty file and
one over 64 KiB, -f format files and a directory. Fixed cases cover every
option (short and long, -L/--color modes, hd), the default and canned
formats, the -e/-f format language (iteration and byte counts, every
conversion and flag, %_a/%_A in d/o/x, %_c/%_p/%_u, escapes and the escape
quirk, %s precision rules, trailing blank removal, end-of-data padding,
_L color units with values, strings, offsets, ranges and inversion), -s/-n
with size suffixes, '*' suppression, several and missing files, standard
input (with the stream offset glibc leaves at exit), skipping on pipes, write errors and every diagnostic. Random cases
build -e format strings from grammar pieces over random inputs with
-s/-n/-v. stdout, stderr and exit status must match."""
import os, random, shutil, struct, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 500
d = tempfile.mkdtemp(prefix='hexdump-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
env.pop('TERM', None)
rnd = random.Random(47)
fl = [0.0, -0.0, 1.0, -1.5, 3.14159, 1e-45, 3.4028235e38, float('inf'), float('-inf'), float('nan'), 0.1, -2.5e-10]
dbl = [0.0, -0.0, 1.0, 0.1, 1/3, 5e-324, 1.7976931348623157e308, float('inf'), float('nan'), -1e100, 6.02214076e23, 12345.678]
F = {
    't': b'Hello, world!\nThe quick brown fox\tjumps\x00over\x07the lazy dog.\r\n\x0b\x0c\x08\x1b\x7f\x80\xff',
    'all': bytes(range(256)),
    'rep': b'A' * 64 + b'B' * 16 + b'A' * 48 + b'C' * 5,
    'rep2': b'\0' * 100,
    'rep3': b'xy' * 64,
    'f4': b''.join(struct.pack('<f', x) for x in fl),
    'f8': b''.join(struct.pack('<d', x) for x in dbl),
    'fbig': b''.join(struct.pack('<d', x) for x in [1.8e19, 2.0**64, -1e20, 1.2345678901234568e23, 1e300, -1e300, 2.5, float('inf'), float('-inf')]),
    'odd': bytes(rnd.getrandbits(8) for _ in range(37)),
    'one': b'x',
    'e': b'',
    'big': bytes(rnd.getrandbits(8) for _ in range(70000)),
    'bigz': b'\0' * 70000 + b'end',
    'str': b'ab\0abc\0abcd\0\x01xyzw\0\x80hello world\0tail',
    'w': b'alpha\nbeta\ngamma\ndelta\nalpha\n',
    'fmt1': b'# canonical\n"%08.8_Ax\\n"\n\n   "%08.8_ax  " 8/1 "%02x " "  " 8/1 "%02x "\n"  |" 16/1 "%_p" "|\\n"\n',
    'fmt2': b'4/1 "%3d" "\\n"\n  # comment\n\t\n"%_Ad\\n"\n',
    'fmt3': b'"%07.7_ax " 8/2 "%04x " "\\n"\n4/1 "%q"\n',
    'fmt4': b'1/1 "%02x"\n3 "x"\n',
    'fmt5': b'  "%_ad" bogus\n',
    'fmt6': b'"%07.7_Ax\\n"\n"%07.7_ax " 16/1 "%_u " "\\n"',
    'fmt7': b'"ab\0cd" 1/1 "%x"\n1/1 "%02x\\n"\n',
}
for k, v in F.items():
    open(os.path.join(d, k), 'wb').write(v)
os.mkdir(os.path.join(d, 'dir'))

E = lambda s: "-e '" + s + "'"
CASES = [
    # canned formats and options
    't', '-b t', '-c t', '-C t', '-d t', '-o t', '-x t', '-b all', '-c all', '-C all', '-d all', '-o all', '-x all', 'all',
    '-C -x t', '-b -c -d t', '-x -C -e \'"%_Ad\\n"\' t', '--one-byte-octal t', '--one-byte-char t', '--canonical t',
    '--two-bytes-decimal t', '--two-bytes-octal t', '--two-bytes-hex t', '--canon t', '--two t', '--no-squeezing rep',
    '-C odd', '-c odd', '-d odd', '-x one', '-C one', 'one', '-C e', 'e', '-c e', '-e \'"%_Ad\\n"\' e', '-C big', '-x big',
    '-C bigz', '-v -C bigz -n 200', '-C rep', '-v -C rep', '-C rep2', '-v rep2', 'rep2', '-C rep3', '-c rep3', '-C w', '-C str',
    # length and skip
    '-n 5 -C t', '-n 0 -C t', '-n 0 nonexistent', '-n 1 t', '-n 17 -C all', '-n 1K -C big', '-n 1KiB -x big', '-n 1KB -C big',
    '-n 0x10 -C t', '-n 010 -C all', '-n 1.5K -C big', '-n 1.5 t', '-n 1. t', '-n 1.0 t', '-n abc t', '-n -1 t', '-n "" t',
    '-n " 5" -C t', '-n +5 -C t', '-n 99999999999999999999999 t', '-n 5ZiB t', '-n 18446744073709551615 -C t', '-n 3m t',
    '-n 2MB -C t', '-n 1Q t', '-n 1KiBx t', '-n 0.5k -C big', '-n 1.05k -C big', '-n 1.25G e',
    '-s 5 -C t', '-s 0 -C t', '-s 100 -C t', '-s 1000 -C t t', '-s 70 -C t t', '-s 66000 -C big', '-s 1k -n 32 -C big',
    '-s 0x8000000000000000 t', '-s 0x7fffffffffffffff t', '-s abc t', '-s 3 -C e t', '-s 3 -C dir t', '-s 3 dir',
    '-s 5 -n 5 -C t', '-s 64 -C rep', '-s 10 -x t', '--skip=5 --length=10 -C t', '--skip 5 --length 10 -x t',
    '-s 2 -C < t', '-s 200 -C < t', '-s 3 /dev/zero -n 20 -C',
    # files and input
    '-C t one', '-C t nonexistent one', 'nonexistent', 'nonexistent nonexistent2', '-s 1 nonexistent', '-C dir', '-C dir t',
    '-C < t', '-C < dir', '-C -- < dir', '-n 4 -C < dir', '-C - < t', '-C -- t', '-C t -- -x', '-C e e e', '-C t e one',
    'cat t | {HX} -C', 'cat big | {HX} -x', 'cat t | {HX} -s 3', '({HX} -n 4 -C; cat) < t', 'cat t | ({HX} -n 4 -C; cat)',
    't > /dev/full; echo $?', '-C big > /dev/full; echo $?', '-C one > /dev/full; echo $?', '-n 4096 -e \'"x"1/1 "%c"\' /dev/zero > /dev/full; echo $?',
    # options and errors
    '-z t', '--bogus t', '--c t', '-e', '-n', '-s', '-f', '--format', '-h', '--help', '-V', '--version', '-hV', '-Vh', '-zh', '-h -z',
    '-f nonexistent t', '-f dir t', '-f fmt1 t', '-f fmt2 t', '-f fmt3 t', '-f fmt4 t', '-f fmt5 t', '-f fmt6 all', '-f fmt7 t',
    '-f fmt1 -f fmt6 t', '--format-file=fmt2 t', '-e \'"%q"\' -z', '-z -e \'"%q"\'', '-e \'"%q"\' t -h', '-n abc -e \'"x\'',
    '-L t', '-Lnever t', '-Lalways -C t', '-L=always t', '--color t', '--color=auto t', '--color=never t', '--color=always t',
    '--color=ALWAYS t', '--color=bogus t', '--color= t', '-Lx t', '--color always t',
    # format language
    E('"%_ad"'), E('"%_Ad"'), E('1/1 "%02x"'), E('1/1 "%02x "'), E('16/1 "%02x " "\\n"'), E('16/1 "%02x "') + ' ' + E('"\\n"'),
    E('"%07.7_ax " 16/1 "%3_c " "\\n"') + ' all', E('"%07.7_ax " 16/1 "%_u " "\\n"') + ' all', E('16/1 "%_p" "\\n"') + ' all',
    E('16/1 "%-5_u|" "\\n"') + ' all', E('16/1 "%5_c|" "\\n"') + ' all', E('8/1 "%#5_u|" "\\n"') + ' all', E('16/1 "%c" "\\n"') + ' all',
    E('4/4 "%08x " "\\n"') + ' all', E('4/4 "%11d " "\\n"') + ' all', E('4/4 "%u " "\\n"') + ' all', E('4/4 "%#o " "\\n"') + ' all',
    E('2/8 "%x " "\\n"') + ' all', E('2/8 "%d " "\\n"') + ' all', E('2/8 "%#llx " "\\n"') + ' all', E('8/2 "%+6d" "\\n"') + ' all',
    E('16/1 "%4d" "\\n"') + ' all', E('16/1 "%4i" "\\n"') + ' all', E('8/2 "%X" "\\n"') + ' all', E('/1 "%5.3x|" "\\n"') + ' t',
    E('"%e\\n"') + ' f8', E('"%f\\n"') + ' f8', E('"%g\\n"') + ' f8', E('"%E\\n"') + ' f8', E('"%G\\n"') + ' f8',
    E('/8 "%.3e\\n"') + ' f8', E('/4 "%e\\n"') + ' f4', E('/4 "%+.2f\\n"') + ' f4', E('/4 "%#g\\n"') + ' f4', E('/4 "%-14.5G|\\n"') + ' f4',
    E('1/8 "%20.10e|" "\\n"') + ' f8', E('/2 "%e"') + ' f8', E('/3 "%d"') + ' t', E('/16 "%x"') + ' t', E('/2 "%c"') + ' t',
    E('/2 "%_c"') + ' t', E('/2 "%_p"') + ' t', E('/2 "%_u"') + ' t', E('/4 "%f"') + ' f4',
    E('"%s"') + ' t', E('"%5s"') + ' t', E('"%.5s|"') + ' t', E('"%-8.3s|" "\\n"') + ' str', E('2/4 "%.4s|" "\\n"') + ' str',
    E('/4 "%.4s|" "\\n"') + ' str', E('/4 "%4.2s|" "\\n"') + ' str', E('3/2 "%.2s." "\\n"') + ' w', E('"%.0s|" "\\n"') + ' t',
    E('"%.2s%.3s|\\n"') + ' w', E('"%.s"') + ' t', E('"%%"') + ' t', E('"%q"') + ' t', E('"%l"') + ' t',
    E('"%ld"') + ' t', E('"%_x"') + ' t', E('"%_aq"') + ' t', E('"%_Aq"') + ' t', E('"%_"x') + ' t', E('"%*d"') + ' t', E('"%1$d"') + ' t',
    E('"%-5.3.4d" "\\n"') + ' t', E('/4 "%-5.3.4d" "\\n"') + ' t', E('/4 "%d %d"') + ' t', E('/4 "%_ad %d"') + ' t',
    E('/4 "%d %_ad"') + ' t', E('/1 "%_ad:%02x\\n"') + ' t', E('4/1 "%02x" "%_ad"') + ' t', E('"abc') + ' t', E('abc"') + ' t',
    E('3x "%d"') + ' t', E('3/x "%d"') + ' t', E('3/1x "%d"') + ' t', E('/1x "%d"') + ' t', E('3') + ' t', E('3/') + ' t', E('"x" 3') + ' t',
    E('99999999999999999999/1 "%x"') + ' t', E('0/1 "%x"') + ' t', E('0 "%x"') + ' t', E('2 "%x"') + ' t', E('2/1 "%x "') + ' t',
    E('3 "%02x " "\\n"') + ' t', E('/1 "%02x"') + ' t', E('1/1 "%02x" 2/1 " %02x"') + ' t', E('""') + ' t', E('"\\n"') + ' t',
    E('"abc"') + ' t', E('/4 "abc"') + ' t', E('4/1 "abc" "%02x\\n"') + ' t', E('"\\a\\b\\f\\n\\r\\t\\v\\q\\\\"') + ' -n 1 t',
    E('1/1 "\\tX%02x\\n"') + ' t', E('1/1 "%02x\\\\n"') + ' t', E('1/1 "%02x\\n\\t|"') + ' t', E('"\\x%02x\\n"') + ' t',
    E('"%_Ax\\n" "%_Ao\\n"') + ' t', E('"%_Ad %_Ax\\n"') + ' t', E('"%10.6_Ad|%-8_Ax|%#_Ao\\n"') + ' t', E('"%_Ad\\n" 1/1 "%x"') + ' t',
    E('"%#_ax %02x\\n"') + ' t', E('"%+8.4_ad|%-6_ao|" 4/1 "%02x" "\\n"') + ' t', E('"%_ax" 8/1 " %02x" "\\n"') + ' odd',
    E('8/1 "%02x " "|%_ad|" "\\n"') + ' odd', E('"%_Ad\\n" 4/1 "%02x " "\\n"') + ' odd', E('8/1 "%02x " "\\n"') + ' ' + E('"%_Ax\\n"') + ' odd',
    E('4/1 "%02x " "\\n"') + ' ' + E('8/1 "%c" "\\n"') + ' odd', E('4/2 "%04x " "\\n"') + ' odd', E('4/2 "%04x" "  "') + ' odd',
    E('5/4 "%-9x|" "\\n"') + ' odd', E('3/1 "%3_u" " " 2/1 "%3_c" "\\n"') + ' odd', E('16/1 "%3_u" "\\n"') + ' t',
    E('16/1 "%02x " "\\n"') + ' -s 3 -n 30 rep', E('16/1 "%02x " "\\n"') + ' rep', E('32/1 "%c" "\\n"') + ' rep',
    E('"%07.7_ax " 8/1 "%02x " "\\n"') + ' rep', E('"%07.7_Ax\\n"') + ' ' + E('"%07.7_ax " 8/1 "%02x " "\\n"') + ' rep',
    E('"%07.7_Ax\\n"') + ' ' + E('"%07.7_ax " 8/1 "%02x " "\\n"') + ' -v rep', E('"%_Ad\\n"') + ' -s 5 t', E('"%_Ad\\n"') + ' -s 500 t',
    E('"%_Ad\\n"') + ' -n 0 t', E('"%_Ad\\n"') + ' rep2', E('16/1 "%02x" "\\n"') + ' ' + E('"%_Ad\\n"') + ' rep2',
    E('"%08.8_Ax\\n"') + ' -s 4 -n 0 t', E('1/1 "%02x"') + ' ' + E('"%_Ax\\n"') + ' -n 0 -s 3 t',
    E('/8 "%#.0f|" "\\n"') + ' fbig', E('/8 "%#25.f|" "\\n"') + ' fbig', E('/8 "%#-26.0F|" "\\n"') + ' fbig',
    E('/8 "%#+030.0f|" "\\n"') + ' fbig', E('"%# .0f|" "\\n"') + ' fbig', E('/8 "%#.0e|%#.0g|%.0f" "\\n"') + ' fbig',
    # colors
    '--color=always ' + E('16/1 "%02x_L[red] " "\\n"') + ' t',
    '--color=never ' + E('16/1 "%02x_L[red] " "\\n"') + ' t',
    '-L ' + E('16/1 "%02x_L[red] " "\\n"') + ' t',
    '--color=always ' + E('16/1 "%02x_L[red:0x41,green:0x42,blue] " "\\n"') + ' all',
    '--color=always ' + E('16/1 "%02x_L[!red:0x41,lightgreen] " "\\n"') + ' all',
    '--color=always ' + E('16/1 "%02x_L[red:0101,yellow:0x7f,white:0x7e] " "\\n"') + ' all',
    '--color=always ' + E('16/1 "%_p_L[magenta@3-6,cyan@20] " "\\n"') + ' all',
    '--color=always ' + E('16/1 "%_p_L[bold@0-40] " "\\n"') + ' all',
    '--color=always ' + E('4/4 "%08x_L[red@4-11,blue:0x03020100] " "\\n"') + ' all',
    '--color=always ' + E('/4 "%08x_L[red:0x04030201] " "\\n"') + ' all',
    '--color=always ' + E('/2 "%04x_L[red:abc] " "\\n"') + ' all',
    '--color=always ' + E('"%_ad_L[red:0x10,green] " 16/1 "%02x" "\\n"') + ' all',
    '--color=always ' + E('"%_ad_L[red:0x10] " 16/1 "%02x" "\\n"') + ' all',
    '--color=always ' + E('"%_ad_L[!red:0x10] " 16/1 "%02x" "\\n"') + ' all',
    '--color=always ' + E('"%_Ad_L[red]\\n"') + ' t',
    '--color=always ' + E('"%_Ad_L[red:0x5c]\\n"') + ' t',
    '--color=always ' + E('/3 "%.3s_L[red:llo@2-4,blue:Hel] " "\\n"') + ' t',
    '--color=always ' + E('/2 "%.2s_L[red:wo@7-8] "') + ' t',
    '--color=always ' + E('/2 "%.2s_L[red:ab@] "') + ' t',
    '--color=always ' + E('/2 "%.2s_L[red:abc] "') + ' t',
    '--color=always ' + E('/1 "%c_L[red:x@3-1]"') + ' t',
    '--color=always ' + E('/1 "%c_L[purple]"') + ' t',
    '--color=always ' + E('/1 "%c_L[lightgray]"') + ' t',
    '--color=always ' + E('/1 "%c_L[reset,reverse]"') + ' t',
    '--color=always ' + E('/1 "%c_L[red:0xzz]"') + ' t',
    '--color=always ' + E('/1 "%c_L[red:0x]"') + ' t',
    '--color=always ' + E('/1 "%c_L[red:09]"') + ' t',
    '--color=always ' + E('/1 "%c_L[red@99999999999999999999999]"') + ' t',
    '--color=always ' + E('/1 "%c_L[red"') + ' t',
    '--color=always ' + E('/1 "%c_Lred]"') + ' t',
    '--color=never ' + E('/1 "%c_L[red"') + ' t',
    '--color=never ' + E('/1 "%c_Lred] x] y" "\\n"') + ' t',
    '--color=always ' + E('/1 "%c_L[red] x] y" "\\n"') + ' t',
    '--color=always ' + E('/1 "%02x_L[green:0x41]" "\\n"') + ' -n 20 t',
    '--color=always -C t',
]
for a, b in [('black', 'blink'), ('blue', 'bold'), ('brown', 'cyan'), ('darkgray', 'gray'), ('green', 'halfbright'),
             ('lightblue', 'lightcyan'), ('lightgreen', 'lightmagenta'), ('lightred', 'magenta'), ('red', 'reset'),
             ('reverse', 'yellow'), ('white', 'Red')]:
    CASES.append('--color=always ' + E('16/1 "%02x_L[' + a + ':0x48,' + b + '] " "\\n"') + ' t')
CASES += ['hd t', 'hd -x t', 'hd', 'hd -V', 'hd --help', 'hd -z', 'hd -s 3 nonexistent', 'hd < t']


def run(c, which):
    prog = 'hexdump' if which == 'ref' else NEBOX + ' hexdump'
    if c.startswith('hd'):
        prog = 'hd' if which == 'ref' else NEBOX + ' hd'
        c = c[2:].lstrip()
    cmd = c.replace('{HX}', prog) if '{HX}' in c else prog + ' ' + c
    if which != 'ref':
        cmd = 'ulimit -v 3000000; ' + cmd
    try:
        p = subprocess.run(['bash', '-c', cmd], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return ('timeout', b'', b'')
    return p.returncode, p.stdout, p.stderr


# random -e formats from grammar pieces
TEXTS = ['', ' ', '  ', '|', ':', 'ab', '\\n', '\\t', 'x\\ty', '-', '\\\\', '[', ']', '\\v', 'z ']
PLAIN = [x for x in TEXTS if '\\' not in x]
CONVS = ['d', 'i', 'o', 'u', 'x', 'X', 'e', 'f', 'g', 'E', 'G', 'c', 's', '_c', '_p', '_u', '_ad', '_ao', '_ax', '_Ad', '_Ax', '_Ao']
BAD = ['q', '%', 'l', '_z', '_aq', 'n', 'p']


def rconv(bcnt):
    c = rnd.choice(CONVS)
    if rnd.random() < 0.02:
        c = rnd.choice(BAD)
    s = '%'
    for _ in range(rnd.choice([0, 0, 1, 2])):
        s += rnd.choice('#-+ 0')
    if rnd.random() < 0.4:
        s += str(rnd.randint(1, 14))
    if c == 's':
        if bcnt:
            if rnd.random() < 0.9:
                s += '.' + str(rnd.randint(0, bcnt))
            else:
                s += '.' + str(bcnt)
        elif rnd.random() < 0.95:
            s += '.' + str(rnd.randint(0, 6))
    elif rnd.random() < 0.3:
        s += '.' + (str(rnd.randint(0, 8)) if rnd.random() < 0.9 else '')
    return s + c


def runit():
    bcnt = 0
    pre = ''
    r = rnd.random()
    if r < 0.4:
        pre = str(rnd.randint(1, 16)) + ('/' if rnd.random() < 0.6 else ' ')
    if rnd.random() < 0.45:
        bcnt = rnd.choice([1, 1, 2, 4, 8, 4, 2, 3])
        if not pre.endswith('/'):
            pre += '/'
        pre += str(bcnt) + ' '
    body = ''
    nconv = rnd.choice([0, 1, 1, 1, 2]) if not bcnt else (1 if rnd.random() < 0.97 else 2)
    # an escape shifts the rest of the unit left (escape() copies only the
    # escaped characters), so no conversion may follow one: that would leave
    # a '%' at the end of the string, which the C code reads past
    for _ in range(nconv):
        body += rnd.choice(PLAIN) + rconv(bcnt)
    body += rnd.choice(TEXTS)
    return pre + '"' + body + '"'


NAMES = list(F.keys())[:11]
for k in range(NRAND):
    n = rnd.choice([0, 1, 3, 7, 15, 16, 17, 31, 32, 33, 64, 100, 257])
    data = bytes(rnd.choice([0, 0x41, 0x20, 0x0a, rnd.getrandbits(8)]) for _ in range(n))
    if rnd.random() < 0.3 and n:
        data = data[:8] * (n // 8 + 1)
    name = 'r%d' % k
    open(os.path.join(d, name), 'wb').write(data)
    opts = []
    for _ in range(rnd.choice([1, 1, 1, 2, 2, 3])):
        fmt = ' '.join(runit() for _ in range(rnd.choice([1, 1, 2, 3])))
        opts.append("-e '" + fmt + "'")
    if rnd.random() < 0.15: opts.append(rnd.choice(['-C', '-x', '-c', '-b', '-d', '-o']))
    if rnd.random() < 0.25: opts.append('-s %d' % rnd.randint(0, 40))
    if rnd.random() < 0.25: opts.append('-n %d' % rnd.randint(0, 60))
    if rnd.random() < 0.2: opts.append('-v')
    if rnd.random() < 0.1: opts.append('--color=always')
    files = [name]
    if rnd.random() < 0.1: files.append(rnd.choice(NAMES))
    CASES.append(' '.join(opts + files))

bad = 0
for c in CASES:
    g = run(c, 'ref')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for nm, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s ref:   %r' % (nm, x if isinstance(x, (int, str)) else x[:400]))
                    print('  %s nebox: %r' % (nm, y if isinstance(y, (int, str)) else y[:400]))
print('hexdump_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
