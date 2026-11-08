#!/usr/bin/env python3
"""Side-by-side test of nebox grep against GNU grep 3.8 (Debian's 3.8-5).
Usage: tests/grep_compare.py path/to/nebox [random-cases [seed]]
Fixtures on tmpfs (/dev/shm, so that -r sees a stable directory order):
text, case and punctuation files, CR-LF lines, files without a final
newline, binary data (NULs early, late, past the first 96 KiB read, a file
whose hole makes it binary), NUL-separated records, pattern files with
invalid and duplicate lines, and a tree with symlinks (to files,
directories, nowhere, a loop), a FIFO, unreadable files and directories
(when not run as root) and names for --include/--exclude/--exclude-dir.
Fixed cases cover every option and long option, binary-file handling,
context and group separators, -o/-c/-l/-L/-q/-s status rules, --color
with GREP_COLORS and GREP_COLOR, -T, -Z/-z, devices, -r/-R traversal,
standard input (pipes, seekable files and what -m leaves of them), the
dfa.c warnings and errors and glibc's compile errors per pattern line,
and write errors; random cases combine patterns, options and inputs.
Compared: stdout, stderr and exit status. -P, which nebox refuses, is
checked against the --disable-perl-regexp message only."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 3000
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 38
ROOT = os.geteuid() == 0
d = tempfile.mkdtemp(prefix='grep-compare-', dir='/dev/shm')
env = dict(os.environ, LC_ALL='C')
for k in ('GREP_COLOR', 'GREP_COLORS', 'TERM', 'POSIXLY_CORRECT', 'DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN'):
    env.pop(k, None)
GNU = 'grep'


def sh(c):
    subprocess.run(['bash', '-c', c], cwd=d, check=True, env=env)


W = lambda name, data: open(os.path.join(d, name), 'wb').write(data)
W('words', b'alpha\nbeta\ngamma\ndelta\nepsilon\nzeta\neta\ntheta\niota\nkappa\nlambda\nmu\n')
W('case', b'Apple\napple\nAPPLE\nbanana\nBanana split\ncherry pie\n')
W('text', b'The quick brown fox\njumps over the lazy dog.\n\nfoo bar baz\nfoo_bar foo-bar\n'
          b'a+b=c (x|y) [z] {w}\nback\\slash and $dollar ^caret\n123 4567 89\ntab\there\n'
          b'  leading spaces\ntrailing spaces  \nfoofoo foo\nend\n')
W('crlf', b'one\r\ntwo\r\nthree\r\n')
W('nonl', b'first\nsecond\nlast without newline')
W('empty', b'')
W('blank', b'\n\n\na\n\n')
W('bin1', b'text line\nmatch here\n\x00binary part\nmatch again\n')
W('bin2', b'\x00\x01\x02match\nmore match\n')
W('bin3', b'no nul here\nmatch\n')
W('z1', b'one\ntwo\x00three\x00match\nhere\x00last')
W('high', b'caf\xe9\n\xff\xfe match\nplain\n')
big = b''.join(b'line %d %s\n' % (i, b'match' if i % 997 == 0 else b'filler') for i in range(12000))
W('big', big)
W('bignul', big + b'\x00tail match\n')
W('bignul2', big[:60000] + b'\x00' + big[60000:])
W('pats', b'alpha\nbet.\n\nalpha\nzeta\n')
W('longline', b'short\n' + b'x' * 250000 + b' match\nafter\n')
W('zeros', b'\0' * 230000 + b'xmatch\0tail\0')
W('badpats', b'ok\n[\nfine\na\\{1\n\\(\n')
W('pempty', b'')
W('pnl', b'\n')
W('pfix', b'a.b\nc*d\n')
W('dots', b'a.b\naxb\nc*d\ncd\nccd\n')
W('excl', b'*.c\n\n  b*  \nsub\n')
sh(r"""
dd if=/dev/zero of=hole bs=1k count=0 seek=300 2>/dev/null
printf 'match at start\n' | dd of=hole conv=notrunc 2>/dev/null
head -c 102400 big > holetail; truncate -s 300k holetail
mkdir -p tree/sub/deep tree/.hid tree/skipme tree/sub/skipme
printf 'match a\n' > tree/a.txt; printf 'match b\n' > tree/b.c; printf 'nomatch\n' > tree/c.txt
printf 'match deep\n' > tree/sub/deep/d.h; printf 'match sub\n' > tree/sub/e.txt
printf 'match hidden\n' > tree/.hid/h.txt; printf 'match skip\n' > tree/skipme/s.txt
printf 'match subskip\n' > tree/sub/skipme/t.txt; printf 'match\0bin\n' > tree/sub/bin.dat
ln -s a.txt tree/link.txt; ln -s sub tree/dirlink; ln -s nowhere tree/dangle; ln -s .. tree/sub/loop
mkdir fdir; mkfifo fdir/fifo; printf 'match f\n' > fdir/f
printf 'match ro\n' > tree/noperm; chmod 0 tree/noperm
mkdir tree/noread; printf 'match x\n' > tree/noread/x; chmod 0 tree/noread
mkdir -p t2; printf 'match\n' > t2/x.TXT; printf 'match\n' > 't2/[x].txt'; printf 'match\n' > 't2/y*.txt'
mkdir -p rl/a; printf 'match\n' > rl/a/f; ln -s ../rl rl/a/up
""")

CASES = [
    # basics
    'a words', '-i APPLE case', '-v a words', '-n a words', '-c a words', '-l a words case text', '-L a words case text',
    '-q a words; echo $?', '-q zzz words; echo $?', '-H a words', '-h a words case', 'a words case', '-s a nofile; echo $?',
    'a nofile words; echo $?', '-w foo text', '-x beta words', '-x -e beta -e eta words', '-w -e foo -e bar text',
    '-o o text', '-on o text', '-ob o text', '-b a words', '-bn e words', '-c -v "" words', '-v -c "" words; echo $?',
    '-c "" empty', '"" empty; echo $?', '"" blank | od -c', '-n "" blank', '-v "" blank; echo $?', '-c -v x blank',
    '-m 2 a words', '-m 0 a words; echo $?', '-m 1 -c a words', '-m 1 -A 2 a words', '-m -1 a words', '-v -m 2 a words',
    '-m x a words', '-m 99999999999999999999999 a words | head -2', '-y apple case', '--no-ignore-case -i apple case',
    '-i --no-ignore-case apple case', '-e alpha -e beta words', '-e alpha -ebeta words', '--regexp=mu words',
    '-F a.b dots', '-F -x a.b dots', '-F -w a dots', '-F -e a.b -e "c*d" dots', '-F -o -e c -e cd dots',
    '-F -i -e A.B -e CD dots', '-F -w -e cd -e c dots', '-F -x -e cd -e ccd dots', '-F "" dots | head -2',
    '-G "a.b" dots', '-E "c*d" dots', '-E "a|c" dots', 'beta words words', '-r beta words', '-ri BETA words',
    '-lc a words case', '-Lc a words case', '-lL a words case', '-Ll a words case', '-cq a words; echo $?',
    '-lq a words; echo $?', '-n -m1 a words case', '--count a words', '--files-with-matches a words case',
    '--files-without-match a words case', '--max-count=1 a words', '--line-number a words', '--byte-offset a words',
    '--with-filename a words', '--no-filename a words case', '--null -l a words case | od -c', '-Z -c a words case | od -c',
    '-Z -n a words case | od -c', '-lZ zzz words; echo $?', '-LZ zzz words | od -c', '--quiet a words; echo $?',
    '--silent a words; echo $?', '--no-messages a nofile; echo $?', '-sq a nofile words; echo $?', '-q a nofile words; echo $?',
    '-q zzz nofile words; echo $?', '-sq zzz nofile; echo $?', '--invert-match a words', '--word-regexp foo text',
    '--line-regexp beta words', '--only-matching foo text', '--ignore-case apple case', '--fixed-strings a.b dots',
    '--extended-regexp "a|c" dots', '--basic-regexp "a\\|c" dots', '--text match bin1', '--binary match bin1',
    '--unix-byte-offsets a words', '-u -b a words', '--initial-tab a words', '-T -n a words', '-T -H -n -b a words',
    '-T -c a words', '-T a words', '-T -n "" blank', '-Tn a words case', '-T -o -n o text', '-T -H a - < words',
    '--label=LBL -H a < words', '--label=LBL -c a - words < case', '--label LBL -l a - < words', '-H a < words',
    '-c a - - < words', '--line-buffered a words', '-U a crlf', '--binary o crlf', '-c o crlf', '--version | head -1 | cut -c1-4',
    # context
    '-A1 beta words', '-B1 beta words', '-C1 beta words', '-1 beta words', '-2 -n eta words', '-A1 -B2 -n eta words',
    '-C1 a words', '-C1 -v a words', '-A1 -m2 a words', '-B1 -m2 -n a words', '-C2 -c a words', '-nA1 a words case',
    '-A0 a words', '-B0 eta words', '-C0 eta words', '--group-separator=XX -A1 eta words', '--group-separator= -A1 eta words',
    '--no-group-separator -A1 eta words', '--group-separator=XX --no-group-separator -A1 eta words',
    '--no-group-separator --group-separator=YY -A1 eta words', '-A 1 -B 1 -o a words', '-C1 -on e words',
    '-A1 x text text', '-B1 -H foo text', '--context=1 beta words', '--after-context=1 beta words',
    '--before-context 1 beta words', '-A x beta words', '-A -1 beta words', '-A -0 beta words', '-C " 1" beta words',
    '-C "1 " beta words', '-A 99999999999999999999 beta words', '-12 beta words | head -3', '-1 -2 eta words',
    '-12x beta words', '-01 beta words', '-1A0 beta words', '-0000000000000000000000001 beta words',
    '-1234567890123456789012 beta words', '-C1 -A3 beta words', '-A3 -C1 beta words', '-v -C1 "[a-l]" words',
    '-c -A2 a words', '-l -A2 a words', '-z -A1 . z1 | od -c', '-A2 match big | head -20', '-B3 -n match big | tail -5',
    # binary
    'match bin1; echo $?', 'match bin2; echo $?', 'match bin3', '-c match bin1', '-c match bin2', '-o match bin1',
    '-n match bin1', '-a match bin1 | od -c', '--binary-files=text match bin2 | od -c', '-I match bin1; echo $?',
    '--binary-files=without-match match bin1 bin3; echo $?', '-l match bin1 bin2 bin3', '-L match bin1 bin2 bin3',
    '-q match bin1; echo $?', '-v zzz bin1; echo $?', '-c -v zzz bin1', 'binary bin1; echo $?', '-c "" bin1',
    '-m1 match bin1', 'here bin1', 'zzz bin1; echo $?', '--binary-files=x a words', '-H match bin1 bin3',
    'match big | wc -l', '-c match bignul', 'match bignul | tail -2', 'tail bignul; echo $?', '-c match bignul2',
    'match bignul2 | tail -1', 'match < bignul | tail -2', 'match hole; echo $?', '-c match hole', '-a -c match hole',
    'match holetail | tail -1', '-b -o match longline', '-c x longline', '-n after longline', '-b match big | tail -2',
    '-z -b match zeros | od -c', '-z -c match zeros', '-z -n tail zeros | od -c', '-z -c "" zeros', '-z -v -c x zeros',
    '-a -c x zeros', '-c x zeros', 'cat longline | @ -b match | cut -c1-20', '-c line holetail', 'cat bignul | @ -c match', 'cat bin1 | @ match',
    '-z match z1 | od -c', '-zc . z1', '-zn e z1 | od -c', '-z "^t" z1 | od -c', '-z "e$" z1 | od -c', '-z -o "t.." z1 | od -c',
    '-z "two.three" z1; echo $?', '-z -v e z1 | od -c', '-zb match z1 | od -c', '-zl match z1 words | od -c',
    '-z x bin1 | od -c', '-za match bin1 | od -c', 'caf high', '-c "[^a-z]" high', '-o "[[:print:]]*" high',
    'x empty; echo $?', '-c x empty', '-L x empty', '-v x empty; echo $?', 'last nonl', '-c . nonl', '-v first nonl',
    '-o "t$" nonl', '-n -A1 second nonl', '-b last nonl', '-x "last without newline" nonl',
    # regex syntax and diagnostics
    '"a.p" words', '"^a" words', '"a$" words', '"\\(al\\|be\\)" words', '"p\\{2\\}" case', '-E "p{2}" case',
    '-E "^(a|b)" words', '-E "a+" words', '-E "ta?" words', '"ta\\?" words', '"t\\+a" words', '-E "a{1,2}" words',
    '-o -E "[[:upper:]]+" case', '-o "[[:digit:]]\\+" text', '-o "\\w\\+" text', '-o "\\W" text', '-o "\\s" text | od -c',
    '-o "\\S\\+" text', '"\\bfoo\\b" text', '"foo\\B" text', '"\\<foo" text', '"foo\\>" text', '-o "\\`foo" text',
    "-o \"foo\\\\'\" text", '-E "(foo)\\1" text', '"\\(foo\\)\\1" text', '-o "\\(o\\)\\1" text', '-E "(a)(b)?\\2" words',
    '-e "[" words', '-e "[a" words', '-e "[[:alpha:" words', '-e "[[:foo:]]" words', '-e "[:space:]" words',
    '-e "[[:space:]x" words', '-e "\\(" words', '-e "\\)" words', '-E "(" words', '-E ")" text', '-E "a)" text',
    '-e "a\\{1" words', '-e "a\\{1,2" words', '-e "a\\{2,1\\}" words', '-E "a{2,1}" words', '-E "a{1" words',
    '-E "a{,2}" words', '-e "a\\{,2\\}" words', '-E "a{99999}" words', '-e "a\\{99999\\}" words', '-e "\\{1\\}a" words',
    '-E "{1}a" words', '-E "*a" words', '-E "+a" words', '-E "?a" words', '-E "a|*b" words', '-E "(*a)" words',
    '"*a" words', '"^*a" words', '-E "^*a" words', '-e "\\1" words', '-e "\\(a\\)\\2" words', '-E "()" words | head -2',
    '"\\(\\)" words | head -2', '-e "\\\\" words', '-e "a\\\\" words', '-e "\\\\" text', '-e "z-a" words',
    '-e "[z-a]" words', '-e "[a-]" words', '-e "[]a]" words', '-e "[^]a]" words', '-e "[a-z-0]" words',
    '-e "[[.a.]]" words', '-e "[[.ab.]]" words', '-e "[[=a=]]" words', '-e "[[=ab=]]" words', '-e "[[.-.]a]" words',
    '-o -e "[[:alpha:]-z]" words', '-e "[a" -e "b[" words', '-f badpats words', '-f badpats -e "[" words',
    '-e "[" -f badpats words', '-f pats words', '-f pats -e beta -e alpha words', '-f pempty words; echo $?',
    '-v -f pempty words | head -2', '-f pnl words | head -2', '-c -f pnl words', '-f nofile words', '-f tree words',
    '-F -f pfix dots', '-f pfix dots', '-x -f pempty words; echo $?', '-w -f pempty -c words', 'cat pats | @ -f - words',
    '-e a -f pempty words | head -2', '-E -w "a|b" words', '-w "a.*" text', '-w "o*" text', '-wo "o*" text', '-x -o "be.." words',
    '-ix -o "APPLE" case', '-iw apple case', '-w -c "" text', '-x -c "" text', '-ow "" text; echo $?',
    '-w -e "\\(-a\\)*" text; echo $?', '-io "\\a" words; echo $?', '-o -E "{1}a" words', '-e a -e "\\(b\\)\\1" words',
    '-i "[Z-a]" words', '"[Z-a]" words', '-i "[a-z]" case | head -2', '-o -i "[0-z]" text | head -3', '-i "[[:upper:]]" case',
    '-i "[^a]" words | head -3', '"a$\\)" words', '-E "a$)" words', '"a$)" text', '-x -E "(alpha)|(beta)" words',
    '-w -E "eta|zeta" words', '-c "\\(a\\)\\1*" words', '-o "\\(.\\)\\1" text', '-E -o "(.)(.)\\2\\1" text',
    '-e "x\\|" words | head -2', '-e "\\|x" words | head -2', '-E "x|" words | head -2', '-E "(|x)" words | head -2',
    '-E "a**" words | head -2', '-E "a+*?" words | head -2', '"a\\{0\\}" words | head -2', '"a\\{0\\}b" words',
    '"a\\{0,0\\}*" words | head -1', '-E "a{0}{1}b" words', '-o "e\\{2,\\}" text', '-o "o\\{1,2\\}" text',
    '-E "a{1,2}{2}" words', '"\\(a\\|b\\)*c" words', '-X grep a words', '-X egrep "a|b" words', '-X fgrep a.b dots',
    '-X awk "a|b" words', '-X gawk "a|b" words', '-X posixawk "a|b" words', '-X foo a words', '-E -F a words',
    '-G -G a words', '-E -X egrep a words', '-F -G a words', '-E -E a words',
    # warnings
    '-E "*a" words', 'DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN=1 @ "\\a" words', 'DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN=1 @ -E "\\%" words',
    'DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN=1 @ "\\-x" words', 'DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN=1 @ "a\\ " words',
    'DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN=1 @ -F "\\a" words', '"\\a" words', '-e "\\-x" words', '"\\-a" words',
    # colors
    '--color=always a words', '--color=always -i apple case', '--color=always -n -H a words', '--color=always -o a words',
    '--color=always -v a words', '--color=always -C1 eta words', '--color=always -c a words', '--color=always -l a words case',
    '--color=always -b -T a words', '--color=always "" words | head -2', '--color=always "x*" text | head -3',
    '--color=always o crlf', '--color=always -w foo text', '--color=always -x beta words', '--color=always -F -e c -e cd dots',
    '--colour=always a words', '--color=never a words', '--color=auto a words', '--color a words', '--color=bogus a words | head -1',
    '--color=ALWAYS a words', '--color=yes a words', '--color=force a words', '--color=tty a words', '--color=none a words',
    'GREP_COLORS="ms=01;32" @ --color=always a words', 'GREP_COLORS="mt=01;34:fn=33:ln=31:bn=30:se=35" @ --color=always -Hnb a words',
    'GREP_COLORS="sl=1:cx=2" @ --color=always -C1 eta words', 'GREP_COLORS="sl=1:cx=2:rv" @ --color=always -v -C1 eta words',
    'GREP_COLORS="ne" @ --color=always a words', 'GREP_COLORS="mc=01;33" @ --color=always -v -C1 eta words',
    'GREP_COLORS="ms=:mc=" @ --color=always a words', 'GREP_COLORS="sl=7" @ --color=always o crlf',
    'GREP_COLORS="ms=x1" @ --color=always a words', 'GREP_COLORS="=1:ms=32" @ --color=always a words',
    'GREP_COLORS="ms=1=2" @ --color=always a words', 'GREP_COLORS="zz=1:ms=33" @ --color=always a words',
    'GREP_COLOR="1;32" @ --color=always a words', 'GREP_COLOR="1;32" GREP_COLORS="mt=1;33" @ --color=always a words',
    'GREP_COLOR="1;32" GREP_COLORS="ms=1;33" @ --color=always a words', 'GREP_COLOR="xx" @ --color=always a words',
    'GREP_COLOR="1;32" GREP_COLORS="mt" @ --color=always a words', 'GREP_COLOR="1;32" @ a words',
    'GREP_COLORS="sl=1" @ --color=always -o a words', 'GREP_COLORS="cx=1:rv" @ --color=always a words',
    '--color=always -z match z1 | od -c',
    # files, directories, devices
    'a tree; echo $?', '-s a tree; echo $?', '-d skip a tree words; echo $?', '-d read a tree; echo $?', '-d recurse match tree',
    '-d bogus a tree', '-d re match tree | head -2', '--directories=skip a tree', '-r match tree', '-R match tree',
    '-r match tree/sub', '-r -h match tree', '-r -c match tree', '-r -l match tree', '-r -L match tree',
    '-r --include="*.txt" match tree', '-r --include="*.txt" --include="*.c" match tree', '-r --exclude="*.txt" match tree',
    '-r --exclude="*.txt" --include="a*" match tree', '-r --include="a*" --exclude="*.txt" match tree',
    '-r --exclude-dir=skipme match tree', '-r --exclude-dir=sub match tree', '-r --exclude-dir="s*" match tree',
    '-r --exclude-dir=sub/ match tree', '-r --exclude-dir=tree match tree', '-r --exclude-dir=. match .',
    '-r --exclude-dir="*" match tree', '-r --include=a.txt match tree', '--include="*.c" match tree/a.txt tree/b.c',
    '--exclude="*.c" match tree/a.txt tree/b.c', '--exclude="tree/*.c" match tree/a.txt tree/b.c',
    '--exclude=b.c match tree/a.txt tree/b.c', '--exclude="a\\*" match tree/a.txt', '-r --exclude-from=excl match tree',
    '-r --exclude-from=nofile match tree', '-r --include="[ab].*" match tree', '-r --exclude="*.[tT][xX][tT]" match t2',
    '-r --exclude="\\[x\\].txt" match t2', '-r --exclude="[x].txt" match t2', '-r --exclude="y\\*.txt" match t2',
    '-r --include="*.TXT" match t2', '-r match .  | sort | head -5', 'cd tree && @ -r match', 'cd tree && @ -r match .',
    'cd tree && @ -r match sub', 'cd tree && @ -r match ./sub', 'cd tree && @ -r --exclude-dir=sub match',
    'cd tree && @ -R --exclude-dir=. match | head -3', 'cd tree && @ -rl match', 'cd tree && @ -rc match',
    '-r match tree/a.txt', '-r match tree/a.txt tree/b.c', '-rH match tree/a.txt', '-r match - < words; echo $?',
    '-r match tree/link.txt', '-r match tree/dirlink', '-r match tree/dangle', 'match tree/dangle', '-R match tree/dangle',
    'match fdir/fifo -D skip; echo $?', '-r match fdir', '-r -c match fdir', '-D skip -r match fdir', '-D skip match tree/a.txt', '-D read -r match tree | head -2', '-D bogus a words',
    'a /dev/null; echo $?', '-c a /dev/null', '-L a /dev/null', '-D skip a /dev/null; echo $?', '-D skip a < /dev/null; echo $?',
    '-R match rl', '-r match rl', '-R -c match rl', '--devices=skip -r match tree | head -3', 'match tree/noperm',
    '-s match tree/noperm; echo $?', '-r match tree/noread', '-q match tree/noperm words; echo $?', '-L match tree/noperm',
    '-r --exclude=noperm match tree/noperm', '-r match tree/noread/x', 'a words > out; @ a out words >> out; echo $?; cat out',
    'a words > out2; @ -m1 a out2 >> out2; echo $?', 'a words > out3; @ -q a out3 >> out3; echo $?',
    'a words > out4; @ -l a out4 >> out4; echo $?', 'a words > /dev/null; echo $?', '-c a words > /dev/null; echo $?',
    'zzz words nofile > /dev/null; echo $?', '-m1 a words > /dev/null; echo $?',
    'a words > /dev/full; echo $?', '-q a words > /dev/full; echo $?', 'a big > /dev/full; echo $?', '-c a big > /dev/full; echo $?',
    '-l a words > /dev/full; echo $?', 'a big nofile > /dev/full; echo $?', '-c a words words words > /dev/full; echo $?',
    # standard input
    'printf "x\\ny\\n" | @ x', 'printf "x\\ny\\n" | @ -c .', 'printf "x\\ny" | @ y', 'printf "" | @ x; echo $?',
    '(@ -m1 a; cat) < words', '(@ -m2 -A1 a; cat) < words', '(@ -q a; cat) < words', '(@ -l a; cat) < words',
    '(@ -c a; cat) < words', '(@ zzz; cat) < words', '(@ -m1 a -; cat) < words', '(@ -m1 -v a; cat) < words',
    'cat words | (@ -m1 a; cat)', '- < words', 'a - words < case', 'a - - < words', '--label=x -H a - < words',
    # option parsing
    '', 'a', '-k a words', '"-)" words', '"-]" words', '-a"(" words', '--foo a words', '--regexp', '-e', '--exclude', '--colo=always a words | head -1',
    '--line a words', '--no a words', '--help | head -3', '--help a | sed -n 60,70p', 'a words -n', 'a -- -n words; echo $?',
    '-- -a words; echo $?', '-e -a words; echo $?', 'POSIXLY_CORRECT=1 @ a words -n; echo $?', '-P a words',
    '--perl-regexp a words', '-E -P a words', '-V | head -1 | cut -c1-5', '-c --binary-files text match bin1',
    '-ihn APPLE case', '-nh -e a -e e words case | head -4', '-Hhc a words', '-hHc a words', '-rh match tree/sub',
    '-Lv a words case', '-lv a words case', '-cv a words case', '-ov a words; echo $?', '-onv a words; echo $?',
    '-o -C1 "o.." text', '-o -b -A1 b text', '-oc o text', '-ol o text words', '-oq o text; echo $?', '-o "" words; echo $?',
    '-o -v "" words; echo $?', '--null-data -c . z1', '--line-regexp -F alpha words', '--null -c a words',
]

TOK = ['a', 'b', 'o', 'e', 'f', 't', '.', '*', '\\.', '^', '$', '[a-f]', '[^a]', '[[:alpha:]]', '\\w', '\\W', '\\b', '\\<',
       '\\>', '\\(', '\\)', '\\|', '\\{1,2\\}', '\\{2\\}', '\\?', '\\+', ' ', '-', '_', 'x', 'oo', '\\1', '[]a]', '[a-]',
       '\\s', '\\S', 'A', 'E', '9', '[0-9]', '[.]', '\\{0,1\\}', '\\B', '[[:space:]]', '[[:upper:]]', '[[:punct:]]']
ETOK = ['a', 'b', 'o', 'e', 'f', 't', '.', '*', '\\.', '^', '$', '[a-f]', '[^a]', '[[:alpha:]]', '\\w', '\\W', '\\b', '\\<',
        '\\>', '(', ')', '|', '{1,2}', '{2}', '?', '+', ' ', '-', '_', 'x', 'oo', '\\1', '[]a]', '[a-]', '\\s', 'A', 'E',
        '9', '[0-9]', '{,2}', '{1', '\\B', '[[:space:]]', '()', '(a|)', '[[:upper:]]']
FTOK = ['a', 'b', 'o', 'e', 'foo', 'ba', '.', '*', ' ', '-', '_', 'x', 'oo', 'A', 'E', '9', '\\', '[', 'ab', 'r']
CH = ['a', 'b', 'o', 'e', 'f', 'oo', 'foo', 'bar', ' ', '-', '_', '.', 'x', 'A', 'E', 'B', '9', '*', '(', ')', '|',
      '\\', '[', ']', '{', '}', '\t', 'ab', 'ba', 'ee', '\r', 'Foo', 'aa', 'abab', '\xe9', '1}', ':']


RAW = list('ab.*+?{}()[]^$|\\-,012:=_ Ax') + ['\\(', '\\)', '\\{', '\\}', '\\|', '[:', ':]', '[[:alpha:]]', '\\1', '\\2',
                                          '\\w', '\\<', '\\>', '\\b', '[^', '[.', '.]', '[=', '=]', '\\`', "\\'"]


def shq(s):
    return "'" + s.replace("'", "'\\''") + "'"


rnd = random.Random(SEED)
for k in range(NRAND):
    lines = []
    for _ in range(rnd.randint(0, 8)):
        lines.append(''.join(rnd.choice(CH) for _ in range(rnd.randint(0, 6))))
    data = '\n'.join(lines)
    if lines and rnd.random() < 0.8:
        data += '\n'
    if rnd.random() < 0.05:
        data = data.replace('o', '\0', 1)
    fn = 'r%d' % k
    W(fn, data.encode('latin-1'))
    mode = rnd.choice(['G', 'G', 'G', 'E', 'E', 'F'])
    toks = {'G': TOK, 'E': ETOK, 'F': FTOK}[mode]
    pats = []
    chaos = rnd.random() < 0.35 and mode != 'F'
    for _ in range(rnd.choice([1, 1, 1, 1, 2, 2, 3])):
        if chaos:
            pats.append(''.join(rnd.choice(RAW) for _ in range(rnd.randint(0, 8))))
        else:
            pats.append(''.join(rnd.choice(toks) for _ in range(rnd.randint(0, 4))))
    opts = ['-' + mode] if mode != 'G' or rnd.random() < 0.3 else []
    for o in rnd.sample(['-i', '-v', '-w', '-x', '-o', '-n', '-b', '-c', '-l', '-L', '-q', '-H', '-h', '-z', '-a',
                         '-A1', '-B1', '-C1', '-m1', '-m2', '--color=always', '-T', '-Z', '-s', '-u', '-y'],
                        rnd.randint(0, 4)):
        opts.append(o)
    if len(pats) == 1 and rnd.random() < 0.7:
        args = opts + [shq(pats[0])]
    elif rnd.random() < 0.5:
        args = opts + ['-e ' + shq(p) for p in pats]
    else:
        W(fn + 'p', ('\n'.join(pats) + '\n').encode('latin-1'))
        args = opts + ['-f', fn + 'p']
    if rnd.random() < 0.04:
        args = ['-r'] + [rnd.choice(['--include=*.txt', '--exclude=*.c', '--exclude-dir=sub', '--include=a*',
                                     '--exclude=[ab]*', '--exclude-dir=s*', '-h', '-l', '-c'])
                         for _ in range(rnd.randint(0, 3))] + ['-e', shq(pats[0]), 'tree', 'fdir']
    else:
        args.append(fn)
        if rnd.random() < 0.15:
            args.append('words')
    CASES.append(' '.join(args) + '; echo $?')


def run(c, which):
    prog = GNU if which == 'gnu' else NEBOX + ' grep'
    cmd = c.replace('@', prog) if '@' in c else prog + ' ' + c
    try:
        p = subprocess.run(['bash', '-c', cmd], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return ('timeout', b'', b'')
    return p.returncode, p.stdout, p.stderr


def strip_help(out):
    i = out.find(b'\nReport bugs to:')
    return out[:i + 1] if i >= 0 else out


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if '--help' in c or '--color=bogus' in c:
        g = (g[0], strip_help(g[1]), g[2])
    if '-P' in c.split() or '--perl-regexp' in c:
        want = b'grep: Perl matching not supported in a --disable-perl-regexp build\n'
        if n[0] != 2 or n[1] != b'' or n[2] != want:
            bad += 1
            print('MISMATCH (-P):', c, n)
        continue
    if ROOT and ('noperm' in c or 'noread' in c):
        continue
    if g != n:
        bad += 1
        if bad <= 40:
            print('MISMATCH:', c, flush=True)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if not isinstance(x, bytes) else x[:400]))
                    print('  %s nebox: %r' % (name, y if not isinstance(y, bytes) else y[:400]), flush=True)
print('grep_compare: %d cases, %d mismatches' % (len(CASES), bad))
sh('chmod -R u+rwx tree')
shutil.rmtree(d)
sys.exit(1 if bad else 0)
