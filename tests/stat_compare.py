#!/usr/bin/env python3
"""Side-by-side test of nebox stat against GNU coreutils stat.
Usage: tests/stat_compare.py path/to/nebox [random-cases]
One fixture (file types, modes, odd names, symlinks, fixed timestamps
including negative and nanosecond ones) is shared by both, then fixed cases
and random format strings (flags, widths, precisions on every directive)
are compared: stdout, diagnostics (minus "Try --help") and exit status.
stat -f free counts are compared on /sys and /proc only: on a live root
file system or the shared tmpfs they change between the two runs."""
import os, random, shutil, socket, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 400
d = tempfile.mkdtemp(prefix='stat-compare-')
F = os.path.join(d, 'fx')
os.makedirs(F)
env = dict(os.environ, LC_ALL='C', TZ='UTC')
env.pop('POSIXLY_CORRECT', None)
env.pop('QUOTING_STYLE', None)


def sh(c):
    subprocess.run(['bash', '-c', c], cwd=F, check=True, env=env)


sh("printf 'hello\\n' > reg; : > empty; mkdir dir; ln -s reg lnk; ln -s nowhere dangling; mkfifo fifo; "
   "printf x > 'sp ace'; printf x > \"q'uote\"; printf x > $'nl\\nname'; printf x > 'tab\tx'; printf x > '$dollar'; "
   "printf x > $'\\001ctl'; printf x > $'hi\\xff'; ln -s $'nl\\nname' lnk2; printf x > '\"dq\"'; printf x > 'back\\\\slash'; "
   "chmod 4755 reg; chmod 1777 dir; chmod 2640 empty; chmod 0 'sp ace'; "
   "touch -d '2021-03-04 05:06:07.123456789' reg; touch -d '1969-12-31 23:59:58.5' empty; "
   "touch -d '@-1' 'sp ace'; touch -d '@0' fifo; touch -d '0999-01-01' \"q'uote\"; touch -h -d '2000-01-01' lnk; "
   "mkdir -p deep/a/b; ln reg hard")
# readlink updates a symlink's atime once under relatime; do it now so the
# first stat run does not change what the second sees.
sh("readlink lnk dangling lnk2 > /dev/null")
s = socket.socket(socket.AF_UNIX)
s.bind(os.path.join(F, 'sock'))
s.close()
FILES = ['reg', 'empty', 'dir', 'lnk', 'dangling', 'fifo', 'sock', "'sp ace'", "\"q'uote\"", "$'nl\\nname'",
         "$'tab\\tx'", "'$dollar'", "$'\\001ctl'", "$'hi\\xff'", 'lnk2', "'\"dq\"'", "'back\\slash'",
         '/dev/zero', '/', '.', 'deep/a/b', 'hard', 'nonexistent']

CASES = []
for f in FILES:
    CASES += ['@stat %s' % f, '@stat -L %s' % f, '@stat -t %s' % f, '@stat -c %%N %s' % f, '@stat -L -c %%N %s' % f]
# Free block and inode counts (%a %f %d, and the default -f output) are
# only compared on /sys and /proc: the fixture's tmpfs is shared with other
# writers, whose files change them between the two runs.
for f in ['/sys', '/dev/null', 'nonexistent', '-', '/proc']:
    CASES += ['@stat -f %s' % f, '@stat -f -t %s' % f]
for f in ['reg', 'dir']:
    CASES += ["@stat -f -c '%%n %%i %%l %%t %%T %%s %%S %%b %%c' %s" % f]
DIR = 'nNdDiaAfFhuUgGmsrRtTBbowWxXyYzZC'
FSDIR = 'naibfdlsStTcz'
for c in DIR:
    CASES.append("@stat -c '[%%%s]' reg dir lnk fifo /dev/zero" % c)
    CASES.append("@stat -L -c '[%%%s]' lnk dangling" % c)
for c in FSDIR:
    CASES.append("@stat -f -c '[%%%s]' %s/sys" % (c, '' if c in 'afd' else '. '))
for q in ['literal', 'shell', 'shell-always', 'shell-escape', 'shell-escape-always', 'c', 'c-maybe', 'escape',
          'locale', 'clocale', 'sh', 'c-m', 'bogus', '']:
    CASES.append("QUOTING_STYLE=%s @stat -c '%%N|%%n' %s" % (q, ' '.join(FILES[:19])))
CASES += [
    "@stat -c '%-5N|' reg", "QUOTING_STYLE=c @stat -c '%-20N|' 'sp ace'", "@stat --printf='%n\\n' reg",
    "@stat --printf='a\\tb\\x41\\x4g\\101\\7777\\q\\\"\\\\%%\\n' reg", "@stat --printf='end\\' reg",
    "@stat -c 'a\\tb\\n' reg", "@stat -c '%' reg", "@stat -c '%5' reg", "@stat -c '%5%' reg", "@stat -c '%%' reg",
    "@stat -c '%-.3%' reg", "@stat -c '%Hd %Ld %Hr %Lr %H %L %Hx %Lq' /dev/null", "@stat -f -c '%Hd %Lr' .",
    "@stat -c '%.3X %.0Y %.9Z %.12X %.X %10.3X|%-10.3X|%010.3X|%+.2X|% .2X' reg empty 'sp ace' fifo",
    "@stat -c '%3.1Y|%2.9Y|%13.9Y|%14.9Y|%-14.9Y|%015.4Y|%-015.4Y|%#5Y' empty reg",
    "@stat -c '%.1Y %.2Y %.10Y %Y %W %.3W' empty", "@stat -c \"%'s %'10i %'X\" reg",
    "@stat -c '%#a %#o %#x %#f %#D %05a %-5a| %+5a %I5s %0-8s|' reg dir",
    "@stat -c '%.4s %.4n %8.2n| %-8.2F| %010s %.0s|%.0i|' reg empty",
    "@stat -c %s - < reg", "@stat -c %F - < /dev/null", "@stat - < dir", "@stat -L - < reg", "@stat -c %n - < reg",
    "@stat", "@stat -c", "@stat --bogus reg", "@stat -x reg", "@stat --cached=never -c %s reg",
    "@stat --cached=always -c %s reg", "@stat --cached=def -c %s reg", "@stat --cached=bogus reg",
    "@stat --cached= reg", "@stat --format=%s --printf=%n reg", "@stat --printf=%s -c %n reg",
    "@stat -c %s reg nonexistent empty", "@stat -c '%m' reg dir / /proc /dev/null lnk dangling nonexistent",
    "@stat -L -c '%m' lnk dangling", "@stat -c '%C' reg", "@stat -L -c '%C' lnk dangling",
    "@stat -c '%w|%W' reg", "@stat -f -c '%T %t' /proc /dev /sys", "@stat -c '%U %G %u %g' /dev/null /",
    "TZ=EST5EDT @stat -c '%x|%y|%z' reg empty", "TZ=XYZ-5:30 @stat -c '%y' reg 'sp ace'", "TZ=UTC0 @stat -c '%y' \"q'uote\"",
    "@stat --terse reg dir", "@stat --dereference -t lnk", "@stat --file-system --terse /", "@stat -c '%y' --format=%x reg",
    "@stat -c '' reg", "@stat --printf='' reg", "@stat -c '%Z%%%z' reg", "@stat -c '%-+ #0I12.5d|' reg",
]
rnd = random.Random(7)
for _ in range(NRAND):
    parts = []
    for _ in range(rnd.randint(1, 4)):
        flags = ''.join(rnd.choice("'-+ #0") for _ in range(rnd.choice([0, 0, 1, 2])))
        w = str(rnd.randint(0, 25)) if rnd.random() < 0.6 else ''
        p = ('.' + (str(rnd.randint(0, 12)) if rnd.random() < 0.8 else '')) if rnd.random() < 0.4 else ''
        parts.append('%' + flags + w + p + rnd.choice(DIR.replace('m', '').replace('C', '')))
    fl = rnd.choice(['', '-L '])
    fmt = '|'.join(parts).replace("'", "'\\''")
    CASES.append("@stat %s-c '%s' reg empty dir lnk fifo 'sp ace' /dev/zero" % (fl, fmt))


def run(cmd, which):
    c = cmd.replace('@stat', (NEBOX + ' stat') if which == 'nebox' else 'stat')
    p = subprocess.run(['bash', '-c', c], cwd=F, env=env, capture_output=True, timeout=60)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 40:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:500]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:500]))
print('stat_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
