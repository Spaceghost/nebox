#!/usr/bin/env python3
"""Side-by-side test of nebox ls (and dir, vdir) against GNU coreutils 9.1.
Usage: tests/ls_compare.py path/to/nebox [random-cases [seed]]
One fixture on tmpfs (/dev/shm, so that -U and -f see a stable directory
order) holds every file type, odd names, symlinks (dangling, looping, to
directories), hard links, unreadable and unsearchable directories, a
directory loop, POSIX ACLs and fixed timestamps (old, recent, future, with
nanoseconds, years that do not fit). Fixed cases cover every option, long
option, environment variable and diagnostic; random cases combine options.
A few cases run on a pseudo-terminal, where ls defaults to -C, -q and
shell-escape quoting and takes its width from the terminal. Run as root,
files also get other owners and a file capability. Compared: stdout,
diagnostics (minus "Try" lines) and exit status."""
import os, pty, random, select, shutil, socket, struct, subprocess, sys, tempfile, time, fcntl, termios

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 400
ROOT = os.geteuid() == 0
d = tempfile.mkdtemp(prefix='ls-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
F = os.path.join(d, 'fx')
os.makedirs(F)
env = dict(os.environ, LC_ALL='C', TZ='UTC')
for k in ('POSIXLY_CORRECT', 'QUOTING_STYLE', 'TIME_STYLE', 'BLOCK_SIZE', 'BLOCKSIZE', 'LS_BLOCK_SIZE', 'LS_COLORS',
          'COLUMNS', 'TABSIZE', 'TERM', 'COLORTERM'):
    env.pop(k, None)


def sh(c):
    subprocess.run(['bash', '-c', c], cwd=F, check=True, env=env)


now = int(time.time())
RECENT = now - 20 * 86400
FUTURE = now + 400 * 86400
sh(r"""
mkdir -p t/sub/deep/er t/emptyd t/.hdir names vers ext big loop/a/b
printf 'hello\n' > t/reg; : > t/empty; printf 'x%%.0s' {1..1500} > t/kb; head -c 70000 /dev/zero > t/k70
truncate -s 5G t/sparse; truncate -s 1M t/meg; printf '#!/bin/sh\n' > t/exe; chmod 755 t/exe
printf s > t/suid; chmod 4755 t/suid; printf g > t/sgid; chmod 2750 t/sgid; printf G > t/sgidnx; chmod 2640 t/sgidnx
mkdir t/sticky t/otherw t/stickyow; chmod 1755 t/sticky; chmod 777 t/otherw; chmod 1777 t/stickyow
chmod 4644 t/empty
ln -s reg t/lreg; ln -s sub t/ldir; ln -s nowhere t/dangle; ln -s self t/self; ln -s ../t/exe t/lexe
ln -s /dev/null t/lnull; ln -s sub/deep t/ldeep; ln -s lreg t/llreg
mkfifo t/fifo; ln t/reg t/hard; ln t/reg t/hard2
printf b > t/back~; printf b > t/.dotback~; printf h > t/.hidden; printf r > t/README
printf z > t/sub/f1; printf zz > t/sub/f2; ln -s ../reg t/sub/up; printf q > t/sub/deep/er/leaf
mkdir t/noread t/nosearch; printf a > t/nosearch/inner; ln -s x t/nosearch/il; chmod 0 t/noread; chmod 600 t/nosearch
printf x > 'names/sp ace'; printf x > "names/q'uote"; printf x > $'names/nl\nname'; printf x > $'names/tab\tx'
printf x > 'names/$dollar'; printf x > $'names/\001ctl'; printf x > $'names/hi\xff'; printf x > 'names/"dq"'
printf x > 'names/back\\slash'; printf x > 'names/-dash'; printf x > 'names/#hash'; printf x > 'names/~tilde'
printf x > 'names/a:b'; printf x > 'names/star*'; printf x > 'names/eq='; printf x > 'names/pipe|'; printf x > 'names/at@'
printf x > 'names/gt>'; printf x > 'names/plain'; printf x > 'names/{brace}'; printf x > 'names/{'; printf x > 'names/semi;'
printf x > $'names/del\x7f'; printf x > $'names/esc\033[1m'; printf x > 'names/?q'; printf x > "names/'"
printf x > 'names/a b c d e f g h'; printf x > names/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz
mkdir $'names/dir\nnl' 'names/dir:colon'; printf x > $'names/dir\nnl/in'; printf x > 'names/dir:colon/in'
ln -s $'tar\nget' names/lnk; ln -s "it's" names/lnk2
for f in file1 file10 file2 file02 file1.10 file1.9 a.1.2 a.1.10 a~ a.tar.gz .v1 .v10 '' ; do [ -n "$f" ] && printf x > "vers/$f"; done
for f in a.c b.C c.h d.tar.gz e.TAR.GZ f.jpg G.JPG h.mp3 i .j k. l.c.bak m.sh n.Z o.txt; do printf x > "ext/$f"; done
chmod 755 ext/m.sh ext/n.Z
for i in $(seq 1 60); do printf x > "big/f$i"; done; for i in 1 22 333 4444 55555; do printf y > "big/w$i"; done
ln -s ../.. loop/a/b/up; ln -s ../a loop/a/b/again
touch -d '2001-02-03 04:05:06.123456789' t/reg t/hard t/kb t/sub/f1
touch -d '2001-02-03 04:05:06.5' t/empty t/k70; touch -d '1901-12-14 00:00:00' t/meg
touch -d @-1 t/exe; touch -d @0 t/fifo; touch -d @%d t/sparse t/sgid t/sub; touch -d @%d t/suid t/README t/sub/f2
touch -d '2001-02-03 04:05:06.123456789' t/sgidnx; touch -d @99999999999 t/back~
touch -h -d '2002-01-01' t/lreg t/dangle t/ldir; touch -h -d @%d t/self
touch -a -d '2010-06-07 08:09:10' t/reg t/kb t/empty; touch -a -d @%d t/k70
""" % (RECENT, FUTURE, FUTURE, RECENT + 3600))
# a timestamp whose year does not fit in an int, if tmpfs keeps it
subprocess.run(['touch', '-d', '@67768036191676800', os.path.join(F, 't/.hidden')], env=env, stderr=subprocess.DEVNULL)
s = socket.socket(socket.AF_UNIX)
s.bind(os.path.join(F, 't/sock'))
s.close()
# a POSIX access ACL (user 4242 r--) and a default ACL on a directory
ACL = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', t, p, i) for t, p, i in
                                      [(1, 6, 0xffffffff), (2, 4, 4242), (4, 4, 0xffffffff),
                                       (0x10, 4, 0xffffffff), (0x20, 4, 0xffffffff)])
HAVE_ACL = True
try:
    os.makedirs(os.path.join(F, 'acl/dd'))
    with open(os.path.join(F, 'acl/fa'), 'w') as fh:
        fh.write('a')
    with open(os.path.join(F, 'acl/plain'), 'w') as fh:
        fh.write('p')
    os.setxattr(os.path.join(F, 'acl/fa'), 'system.posix_acl_access', ACL)
    os.setxattr(os.path.join(F, 'acl/dd'), 'system.posix_acl_default', ACL)
except OSError:
    HAVE_ACL = False
HAVE_CAP = False
if ROOT:
    sh("mkdir own; for u in 0 1000 4242 65534; do printf x > own/u$u; chown $u:$u own/u$u; done; "
       "chown 4242:0 own/u4242; chown 0:4242 own/u0; chown 54321:54320 own/u1000")
    try:
        r = subprocess.run(['setcap', 'cap_net_raw+ep', os.path.join(F, 'own/u0')], env=env, capture_output=True)
        HAVE_CAP = r.returncode == 0
    except OSError:
        pass
    subprocess.run(['bash', '-c', 'mknod own/blk b 259 70000 && mknod own/chr c 4 5'], cwd=F, env=env,
                   stderr=subprocess.DEVNULL)
# reading symlinks and directories updates their atimes once under
# relatime; do it now so the first run does not change what the second sees
sh("ls -laRU . > /dev/null 2>&1; find . -type l -exec readlink {} + > /dev/null 2>&1; ls -laRUL t > /dev/null 2>&1; true")

OPERANDS = ['t', 't/reg', 't/lreg', 't/ldir', 't/dangle', 't/self', 't/sub', 't/fifo', 't/sock', 't/exe', 't/empty',
            '/dev/null', 'names', 'vers', 'ext', 't/noread', 't/nosearch', 'nonexistent', 't/ldeep', '.', 't/sparse',
            'acl', 'big', 'loop']
CASES = []
FORMATS = ['', '-1', '-C', '-x', '-m', '-l', '-g', '-o', '-n', '-lG', '-gG', '--format=commas', '--format=across',
           '--format=vertical', '--format=single-column', '--format=verbose', '--format=long', '--format=horizontal']
for fm in FORMATS:
    for extra in ['', '-a', '-i', '-s', '-F', '-is', '-p', '--file-type', '-Q', '-b', '-q', '-A -r', '-S', '-t',
                  '-h -s', '-isF -w 50', '-U', '-X', '-v', '-Z', '--author', '-N', '-T 0 -w 60', '-k -s']:
        CASES.append('@ls %s %s t' % (fm, extra))
for fm in FORMATS:
    CASES += ['@ls %s names' % fm, '@ls %s -b names' % fm, '@ls %s -Q names' % fm, '@ls %s -q names' % fm,
              '@ls %s vers ext' % fm, '@ls %s -w 30 big' % fm, '@ls %s -w 0 big' % fm, '@ls %s -T 3 -w 100 big' % fm,
              '@ls -d %s t t/sub t/reg names' % fm, '@ls %s -R t/sub' % fm]
for q in ['literal', 'shell', 'shell-always', 'shell-escape', 'shell-escape-always', 'c', 'c-maybe', 'escape',
          'locale', 'clocale']:
    for fm in ['', '-l', '-x -w 70', '-C -w 50', '-m', '-1 -F', '-l --file-type', '-lR', '-ls -i']:
        CASES.append('@ls --quoting-style=%s %s names' % (q, fm))
    CASES += ['QUOTING_STYLE=%s @ls names' % q, 'QUOTING_STYLE=%s @ls -l names t/lreg' % q,
              '@ls --quoting-style=%s -q names' % q, '@ls --quoting-style=%s -Rd names names/dir*' % q,
              'QUOTING_STYLE=%s @ls -N names' % q, '@ls --quoting-style=%s --indicator-style=file-type names t' % q]
CASES += ['QUOTING_STYLE=bogus @ls names', 'QUOTING_STYLE=sh @ls names', 'QUOTING_STYLE=c-m @ls names',
          'QUOTING_STYLE= @ls names', '@ls --quoting-style=bogus', '@ls --quoting-style=sh', '@ls --quoting-style=c- names',
          '@ls --show-control-chars -q names', '@ls -q --show-control-chars names', '@ls --hide-control-chars names',
          '@ls --escape --literal names', '@ls --quote-name names', '@ls -b -Q names', '@ls -Q -b names']
# sorting
for so in ['-t', '-S', '-X', '-v', '-U', '-f', '-c', '-u', '-ct', '-ut', '-lc', '-lu', '-lct', '-lut', '-tr', '-Sr', '-Xr',
           '-vr', '-Ur', '-fr', '--sort=none', '--sort=time', '--sort=size', '--sort=extension', '--sort=version',
           '--sort=width', '--sort=width -r', '--sort=time --time=atime', '--time=ctime', '--time=status',
           '--time=access', '--time=use', '--time=birth', '--time=creation', '-l --time=birth', '-lt --time=birth',
           '--group-directories-first', '--group-directories-first -r', '--group-directories-first -S',
           '--group-directories-first -U', '--group-directories-first -t -r', '-f -l', '-l -f', '-f -s', '-s -f',
           '-fa', '-fA', '-f --color=always', '-tS', '-St', '-vX', '-Xv', '-U -1', '-U -1 -i', '-U -1 -s', '-U -R',
           '-U -1 -F', '-U -C', '-f -i -1', '-f -d', '-c --full-time', '-u --full-time']:
    CASES += ['@ls %s t' % so, '@ls %s vers ext' % so, '@ls -1 %s t t/reg t/kb t/sub t/empty t/meg' % so]
CASES += ['@ls --sort=bogus', '@ls --sort=', '@ls --sort=s', '@ls --sort=ti t', '@ls --time=bogus', '@ls --time=c t',
          '@ls --time=a -l t', '@ls --sort', '@ls --time', '@ls -l --sort=v vers', '@ls --sort=e ext']
# filtering
for fl in ['-a', '-A', '-B', '-aB', '-AB', '-I "f*"', '-I "*" -a', '-I "*~"', '--ignore=sub', '--ignore=".*"',
           '-I "[st]*" -I "*e*"', '--hide="*e*"', '--hide="*e*" -a', '--hide="*e*" -A', '--hide=sub -I reg',
           '-I "\\*"', '-I "[!a-r]*"', '-I "*[[:digit:]]*"', '-I "[]x]*"', '-I "["', '--hide=.hidden -a',
           '-I ""', '-I "?"', '-I "*.*"', '--hide="*" --hide=x', '-B -I ".h*" -a']:
    CASES += ['@ls %s t' % fl, '@ls -1 %s vers ext' % fl]
# operands, dereferencing, errors
for dr in ['', '-L', '-H', '--dereference-command-line-symlink-to-dir', '-d', '-l', '-lL', '-lH', '-F', '-FL',
           '-p', '-lF', '-i', '-iL', '-R', '-RL', '-s', '-sL', '--color=always -l', '-dL', '-dH', '-lH -F',
           '-l --dereference-command-line-symlink-to-dir', '-ld --dereference-command-line-symlink-to-dir',
           '-L --file-type', '-lL --file-type', '-Z', '-lZ', '-ZL']:
    CASES += ['@ls %s t/lreg t/ldir t/dangle t/self t/lexe t/lnull t/ldeep t/llreg' % dr,
              '@ls %s t/ldir' % dr, '@ls %s t/dangle' % dr, '@ls %s t/self' % dr,
              '@ls %s t/nosearch' % dr, '@ls %s t/noread t/reg' % dr]
CASES += [
    '@ls', '@ls .', '@ls -a', '@ls -R', '@ls -Ra t', '@ls -R t loop', '@ls -RL loop', '@ls -RL t/ldir t/sub',
    '@ls -RL t', '@ls -RLl loop', '@ls -R loop/a/b/again', '@ls -RL loop/a/b/again', '@ls -RH loop/a/b/again',
    '@ls nonexistent', '@ls nonexistent t/reg', '@ls t/reg nonexistent t/sub', '@ls ""', '@ls "" t/reg',
    '@ls -l nonexistent t/reg', '@ls t/noread', '@ls -R t/noread t/sub', '@ls -l t/nosearch', '@ls t/nosearch',
    '@ls -i t/nosearch', '@ls -F t/nosearch', '@ls -1 --color=always t/nosearch', '@ls -s t/nosearch',
    '@ls -lR t', '@ls -lRa t', '@ls t t', '@ls t/reg t/reg', '@ls -U t/sub t/reg t t/empty', '@ls t/sub/', '@ls t//sub',
    '@ls t/sub/.', '@ls -R t/sub/', '@ls -R t//sub/', '@ls -R ./t/sub', '@ls /', '@ls -d /', '@ls -R / -d',
    '@ls -d .', '@ls -d', '@ls -dl', '@ls -dR t', '@ls t/ldir/', '@ls -l t/ldir/', '@ls -d t/ldir/',
    '@ls -- -dash', '@ls names/-dash', '@ls -l /dev/null /dev/zero /dev/full', '@ls -l /dev/null t/reg t/sub',
    '@ls -lh t/sparse t/meg t/k70 t/kb', '@ls -ls t/sparse t/meg t/k70 t/kb',
    '@ls t/reg/', '@ls t/reg/x', '@ls -l t/dangle/', '@ls -R t/self', '@ls -lR names', '@ls -R names',
]
# sizes and block sizes
for bs in ['-h', '--si', '-k', '--block-size=1', '--block-size=K', '--block-size=KB', '--block-size=KiB',
           '--block-size=1M', '--block-size=MB', '--block-size=1000', '--block-size=512', "--block-size=\\'1",
           "--block-size=\\'K", '--block-size=human-readable', '--block-size=si', '--block-size=h', '--block-size=s',
           '--block-size=G', '--block-size=1Y', '--block-size=3', '--block-size=0x10', '--block-size=010', '-h --si',
           '--si -h', '-h -k', '-k -h', '--block-size=K -h', '-h --block-size=K', '-k --block-size=1', '--block-size=1 -k',
           '--block-size=1G -s']:
    CASES += ['@ls -ls %s t big' % bs, '@ls -s -1 %s t' % bs, '@ls -sm %s t' % bs]
for e in ['BLOCK_SIZE=1', 'BLOCK_SIZE=M', 'BLOCK_SIZE=human-readable', 'BLOCK_SIZE=bogus', 'BLOCKSIZE=1',
          'BLOCKSIZE=K', 'LS_BLOCK_SIZE=1', 'LS_BLOCK_SIZE=si', 'LS_BLOCK_SIZE=bogus', 'LS_BLOCK_SIZE= ',
          'LS_BLOCK_SIZE=1 BLOCK_SIZE=M', 'BLOCK_SIZE=1 LS_BLOCK_SIZE=M', 'POSIXLY_CORRECT=1', 'POSIXLY_CORRECT=1 BLOCK_SIZE=1K',
          'BLOCK_SIZE=1 BLOCKSIZE=M', 'BLOCKSIZE=1 POSIXLY_CORRECT=1', "BLOCK_SIZE=\\'1", 'LS_BLOCK_SIZE=0']:
    CASES += ['%s @ls -ls t' % e, '%s @ls -lsk t' % e, '%s @ls -s1 t' % e, '%s @ls -lh t' % e]
CASES += ['@ls --block-size=x', '@ls --block-size=1Q', '@ls --block-size=99999999999999999999', '@ls --block-size=0',
          '@ls --block-size=', '@ls --block-size=-1', '@ls --block-size=1KQ', '@ls --block-s=K -l t', '@ls --block-size']
# widths, tabs, columns
for w in ['-w 0', '-w 1', '-w 2', '-w 3', '-w 7', '-w 20', '-w 39', '-w 40', '-w 79', '-w 80', '-w 81', '-w 200',
          '-w 1000', '-w 0x20', '-w 010', '-w 99999999999999999999', '--width=25', '-T 0', '-T 1', '-T 2', '-T 4',
          '-T 100', '--tabsize=5', '-w 50 -T 0', 'COLUMNS=30', 'COLUMNS=0', 'COLUMNS=x', 'COLUMNS=', 'COLUMNS=-3',
          'COLUMNS=99999999999999999999', 'COLUMNS=40 -w 60', 'TABSIZE=3', 'TABSIZE=0', 'TABSIZE=x', 'TABSIZE=',
          'TABSIZE=4 -T 2', 'TABSIZE=99999999999999999999']:
    pre = w if '=' in w and not w.startswith('-') else ''
    opt = '' if pre else w
    if pre and ' ' in pre:
        pre, opt = pre.split(' ', 1)
    for fm in ['-C', '-x', '-m', '-l', '-Ci', '-xs']:
        CASES.append('%s @ls %s %s big t' % (pre, fm, opt))
CASES += ['@ls -w x', '@ls -w -1', '@ls -w', '@ls -w 1x', '@ls -T x', '@ls -T -1', '@ls -T 99999999999999999999999',
          '@ls -T', '@ls --width', '@ls --tabsize=1k', '@ls -w ""', '@ls -T ""']
# time styles
for ts in ['full-iso', 'long-iso', 'iso', 'locale', 'posix-full-iso', 'posix-long-iso', 'posix-iso', 'posix-locale',
           'posix-bogus', 'posix-posix-iso', '+%Y', '+%s.%N', "'+%b %e %H:%M:%S %Z %z'", "+'%Y-%m-%d'$'\\n''%H:%M'",
           "+'a'$'\\n''b'$'\\n''c'", '+', "+$'\\n'", '+%%', "'+%5b|%-5e|%_d|%^a|%#Z'", "'+%x %X %c %r %R %T %D'",
           "'+%G %g %V %U %W %j %u %w %C %y'", "'+%q %P %p %I %l %k'", "'+%:z %::z %:::z'", "'+%N %3N %-N'", "'+%Ez %Oy %Ey'",
           '+%1001Y', '+%990Y', 'f', 'l', 'i', 'bogus', '', '+%']:
    CASES += ["@ls -l --time-style=%s t" % ts, "TIME_STYLE=%s @ls -l t/reg t/sub t/meg" % ts,
              "@ls --time-style=%s t/reg" % ts]
CASES += ['@ls --full-time t', '@ls --full-time -u t', '@ls --full-time --time-style=iso t', '@ls --time-style=iso --full-time t',
          '@ls -l --full-time -1 t', '@ls --full-time -C t', 'TIME_STYLE=long-iso @ls -l --time-style=iso t',
          'TIME_STYLE=+%%s @ls --full-time t/reg', '@ls -l --time-style=+%Y t/.hidden', '@ls -l --time-style=iso t/.hidden',
          '@ls -lu --time-style=+%%s.%N t', '@ls --time-style', '@ls -l --time-sty=full t']
for tz in ['TZ=UTC0', 'TZ=EST5EDT', 'TZ=America/New_York', 'TZ=Australia/Lord_Howe', 'TZ=Asia/Kolkata', 'TZ=XYZ-5:30',
           'TZ=', 'TZ=Foo/Bar', 'TZ=Japan']:
    CASES += ['%s @ls -l t' % tz, '%s @ls --full-time t/reg t/exe t/fifo t/meg' % tz]
# colors
LSC = ['', 'di=01;34', 'di=1:ln=target', 'ln=target:or=31:mi=5', 'or=31:mi=5', 'mi=05;41', 'ex=32:*.c=33:*.C=35:*.tar.gz=31',
       '*.jpg=1:*.JPG=2', 'su=1:sg=2:tw=3:ow=4:st=5:ex=6', 'su=:sg=:tw=:ow=:st=:ex=', 'mh=44', 'mh=44:ex=', 'ca=30;41',
       'no=1', 'no=1:fi=2', 'fi=0', 'fi=00', 'fi=', 'rs=1:lc=<:rc=>', 'ec=END', 'lc=\\e[:rc=m:ec=\\e[0m', 'cl=',
       'cl=XX', 'di=\\x41\\101\\a\\b\\e\\f\\n\\r\\t\\v\\?\\_\\\\\\:\\=\\^:ln=^[^?^a', 'di=\\x', 'di=\\0', 'bogus',
       'xx=1', 'di', 'di=1:', ':::di=1', '*', '*.c', '*.c=', 'di=^', 'di=^ ', 'di=\\', 'pi=1:so=2:bd=3:cd=4:do=5',
       'ln=01;36:or=', 'ln=:or=', 'ln=target:ex=1:or=', 'ln=target:or=:mi=', 'di=1:*=2', '*sub=1', 'tw=:ow=:st=']
for c in LSC:
    q = "LS_COLORS='%s'" % c
    CASES += ['%s @ls --color=always t' % q, '%s @ls --color=always -l t' % q, '%s @ls --color -lL t/lreg t/dangle t/ldir t/self' % q,
              '%s @ls --color=always ext big -w 60' % q]
CASES += ['@ls --color=always t', 'TERM=xterm @ls --color=always t', 'TERM=xterm-256color @ls --color -l t',
          'TERM=dumb @ls --color=always t', 'TERM=con80x25 @ls --color=always t', 'TERM= @ls --color=always t',
          'COLORTERM=1 @ls --color=always t', 'COLORTERM= @ls --color=always t', 'COLORTERM=truecolor @ls --color=always -F t',
          'TERM=xterm @ls --color=auto t', 'TERM=xterm @ls --color=tty t', 'TERM=xterm @ls --color=never t',
          'TERM=xterm @ls --color=no t', 'TERM=xterm @ls --color=yes t', 'TERM=xterm @ls --color=force t',
          'TERM=xterm @ls --color=if-tty t', 'TERM=xterm @ls --color=none t', '@ls --color=bogus', '@ls --color=',
          'TERM=xterm @ls --color=al t', 'TERM=xterm @ls --color=n t', 'TERM=xterm @ls --colo t',
          'TERM=xterm @ls --color=always -R t', 'TERM=xterm @ls --color=always -x -w 40 big t',
          'TERM=xterm @ls --color=always -m -w 30 big', 'TERM=xterm @ls --color=always -C -w 20 big',
          'TERM=xterm @ls --color=always -i -s -F t', 'TERM=xterm @ls --color=always --group-directories-first t',
          'TERM=xterm @ls --color=always -lF t names', 'TERM=xterm @ls --color=always -b names',
          'TERM=xterm @ls --color=always -lL t', 'TERM=xterm @ls --color=always --hyperlink -l t',
          'TERM=xterm @ls --color=always --zero t', 'TERM=xterm @ls --zero --color=always t',
          'TERM=xterm LS_COLORS="ex=1" @ls --color=always -U -1 t', 'TERM=xterm @ls --color=always -d t/sub t/sticky',
          'TERM=xterm @ls --color=always -T 4 t', 'TERM=xterm @ls --color=always -lR t/nosearch t/noread',
          "LS_COLORS='lc=:rc=:ec=' @ls --color=always t", "LS_COLORS='lc=\\e[:rc=m' @ls --color=always t",
          "LS_COLORS='rs=0' @ls --color=always -l t", "LS_COLORS='no=0' @ls --color=always t",
          "LS_COLORS='no=00' @ls --color=always t", "LS_COLORS='no=1:ec=x' @ls --color=always -l t"]
# classify, indicators
for ind in ['-F', '--classify', '--classify=always', '--classify=yes', '--classify=force', '--classify=never',
            '--classify=no', '--classify=none', '--classify=auto', '--classify=tty', '--classify=if-tty', '-p',
            '--file-type', '--indicator-style=none', '--indicator-style=slash', '--indicator-style=file-type',
            '--indicator-style=classify', '-F -p', '-p -F', '-F --indicator-style=none', '--classify=bogus',
            '--indicator-style=bogus', '--indicator-style=c', '--indicator-style', '-F --file-type']:
    CASES += ['@ls %s t' % ind, '@ls -l %s t' % ind, '@ls -lL %s t' % ind, '@ls -Q %s names' % ind]
# hyperlinks, dired, zero, context, author
for hl in ['--hyperlink', '--hyperlink=always', '--hyperlink=never', '--hyperlink=auto', '--hyperlink=yes']:
    CASES += ['@ls %s t' % hl, '@ls %s -l t names' % hl, '@ls %s -R t/sub' % hl, '@ls %s -Q -l names' % hl,
              '@ls %s -x -w 50 names' % hl, '@ls %s t/reg ./t/sub/../reg /dev/null' % hl]
CASES += ['@ls --hyperlink=bogus', '@ls --hyperlink -lf t', '@ls -f --hyperlink t', '@ls --hyperlink --dired -l t']
for dd in ['-D', '--dired', '-lD', '-l --dired', '-lDR', '-lDa', '-lDi', '-lDs', '-lD --color=always', '-lD -Q',
           '-lD -F', '-gDG', '-D -1', '-D -C', '-nD --author', '-lDZ', '-lD --time-style=+%%n', '-D --full-time']:
    CASES += ['@ls %s t' % dd, '@ls %s names' % dd, '@ls %s t/reg t/sub names/dir*' % dd, '@ls %s -R t/sub' % dd]
CASES += ['@ls --zero t', '@ls --zero -l t', '@ls --zero -C t', '@ls -C --zero t', '@ls --zero -lR t/sub',
          '@ls --zero -m t', '@ls -m --zero t', '@ls --zero -q names', '@ls --zero -Q names', '@ls -Q --zero names',
          '@ls --zero -D t', '@ls --zero -lD t', '@ls -lD --zero t', '@ls --zero -ls t', '@ls --zero t/sub t/reg',
          '@ls --zero -x -w 20 big']
CASES += ['@ls -Z t', '@ls -lZ t', '@ls -Z -i -s t', '@ls -Zm t', '@ls -Zx -w 50 t', '@ls -lZ --author t',
          '@ls --context -d t', '@ls -l --author t', '@ls -g --author t', '@ls -o --author t', '@ls -n --author t',
          '@ls -lG --author t', '@ls --author t']
if HAVE_ACL:
    CASES += ['@ls -l acl', '@ls -ld acl/dd acl/fa acl/plain', '@ls -l acl/plain', '@ls -lZ acl', '@ls -Z acl',
              '@ls -lL acl t/lreg', '@ls -lD acl', '@ls -lR acl t/sub', '@ls -l acl t/reg']
# options and their errors
CASES += ['@ls -y', '@ls --bogus', '@ls --a', '@ls --al', '@ls --all t', '@ls --almost t', '@ls --h', '@ls --hi t',
          '@ls --hid=x t', '@ls --hide', '@ls --ignore', '@ls -I', '@ls --i t', '@ls --in t', '@ls --ind', '@ls --de t',
          '@ls --dereference t/ldir', '@ls --dereference-command t/ldir', '@ls --dereference-command-line-s t/ldir',
          '@ls --di -l t', '@ls --dir t', '@ls --directory t', '@ls --all=x', '@ls --width=', '@ls --tabsize=',
          '@ls --format=bogus', '@ls --format=', '@ls --format=v t', '@ls --format=s t', '@ls --format=l t',
          '@ls --format=c t', '@ls --format=h t', '@ls --format=a t', '@ls --format', '@ls --f t', '@ls --fi t',
          '@ls --fu t', '@ls --g t', '@ls --gr t', '@ls --k -s t', '@ls --kib -s t', '@ls --lit names', '@ls --nu t',
          '@ls --no t', '@ls --q names', '@ls --quote names', '@ls --quoting=c names', '@ls --rec t', '@ls --rev t',
          '@ls --s t', '@ls --si t', '@ls --siz t', '@ls --sh names', '@ls --so=t t', '@ls --t t', '@ls --ta=3 -C t',
          '@ls --ti=c t', '@ls --time-s=iso -l t', '@ls --z t', '@ls --ze t', '@ls --co t', '@ls --col t',
          '@ls --con t', '@ls --context=x t', '@ls --hy t', '@ls --hyp t', '@ls --au -l t', '@ls --bl=1 -s t',
          '@ls --e names', '@ls --es names', '@ls --cl t', '@ls --file-t t', '@ls --ig=reg t', '@ls --ignore-b t',
          '@ls --n t', '@ls --nu t', '@ls --num t', '@ls --r t', '@ls --sort t', '@ls -lw', '@ls -Iz -a t',
          '@ls t -l', '@ls t -- -l', '@ls -- t -l', 'POSIXLY_CORRECT=1 @ls t -l', '@ls -1lC t', '@ls -lC1 t',
          '@ls -l1 t', '@ls -1l t', '@ls -mC t', '@ls -Cm t', '@ls -xl t', '@ls -lx t', '@ls -gno t', '@ls -nl t',
          '@ls -ln t', '@ls -lgo t', '@ls -oG t', '@ls -fl t', '@ls -lf t', '@ls -RfU t', '@ls -c -u -l t',
          '@ls -u -c -l t', '@ls -lcu --full-time t', '@ls -hk -ls t', '@ls -ksh -l t', '@ls -aA t', '@ls -Aa t',
          '@ls -Bb names', '@ls -dRL t/ldir', '@ls -LH t/ldir', '@ls -HL t/ldir', '@ls -H -l t/ldir', '@ls -lH t/ldir t/lreg',
          '@ls --zero --dired', '@ls -D --zero', '@ls --dired --zero t', '@ls -Q --zero -l names',
          '@ls t > /dev/full; echo $?', '@ls -l t > /dev/full; echo $?', '@ls -R big t names > /dev/full; echo $?']
# dir and vdir
for prog in ['@dir', '@vdir']:
    CASES += ['%s t' % prog, '%s names' % prog, '%s -1 names' % prog, '%s -l t' % prog, '%s -C -w 40 big' % prog,
              '%s -N names' % prog, '%s -q names' % prog, '%s --quoting-style=c names' % prog, '%s -Q names' % prog,
              'QUOTING_STYLE=c %s names' % prog, '%s --color=always t' % prog, '%s nonexistent' % prog,
              '%s -y' % prog, '%s --sort=x' % prog, '%s -x names' % prog, '%s -m names' % prog]
if ROOT:
    CASES += ['@ls -l own', '@ls -ln own', '@ls -lg own', '@ls -lo own', '@ls -l --author own', '@ls -ls own',
              '@ls -lh own', '@ls -C own', '@ls -lU own', '@ls -lR own', '@ls -lZ own', '@ls -lD own',
              'LS_COLORS="ex=32" @ls --color=always -l own']
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 11)
POOL = ['-a', '-A', '-B', '-c', '-C', '-d', '-f', '-F', '-g', '-G', '-h', '-i', '-k', '-l', '-L', '-m', '-n', '-N', '-o',
        '-p', '-q', '-Q', '-r', '-R', '-s', '-S', '-t', '-u', '-U', '-v', '-x', '-X', '-1', '-H', '-b', '-D', '-Z',
        '--si', '--author', '--full-time', '--group-directories-first', '--file-type', '--zero', '--hyperlink',
        '--color=always', '--dereference-command-line-symlink-to-dir', '--show-control-chars', '-w 0', '-w 30',
        '-w 70', '-w 120', '-T 0', '-T 3', '-I "*e*"', '--hide="f*"', '--sort=width', '--sort=version',
        '--time=birth', '--time=atime', '--time=ctime', '--format=commas', '--format=across', '--block-size=K',
        '--block-size=1', '--block-size=MB', '--indicator-style=slash', '--quoting-style=c', '--quoting-style=shell',
        '--quoting-style=shell-escape', '--quoting-style=escape', '--quoting-style=c-maybe', '--quoting-style=locale',
        '--quoting-style=shell-always', '--time-style=iso', '--time-style=long-iso', '--time-style=+%s',
        '--time-style=full-iso', '--classify=auto']
ENVS = ['', '', '', 'TERM=xterm ', 'LS_COLORS="di=1:ln=target:or=31:mi=5:ex=32:*.c=33:mh=4:su=7" ', 'COLUMNS=50 ',
        'TABSIZE=4 ', 'QUOTING_STYLE=c ', 'BLOCK_SIZE=1 ', 'TIME_STYLE=long-iso ', 'POSIXLY_CORRECT=1 ',
        'TZ=America/New_York ']
ROPS = ['t', 'names', 'vers', 'ext', 't/sub', 't/ldir', 't/lreg', 't/dangle', 't/reg', 'big', 't/nosearch', 'loop',
        'nonexistent', 't/fifo', '/dev/null', 'acl', 't/self', '.']
for _ in range(NRAND):
    opts = ' '.join(rnd.choice(POOL) for _ in range(rnd.randint(1, 6)))
    ops = ' '.join(rnd.choice(ROPS) for _ in range(rnd.randint(0, 3)))
    CASES.append('%s@ls %s %s' % (rnd.choice(ENVS), opts, ops))


def atime_case(cmd):
    # whether the listing shows or sorts by atime (the last -c/-u/--time wins)
    t = None
    for tok in cmd.split():
        if tok.startswith('--time='):
            v = tok[7:]
            t = 'u' if v[:1] in ('a', 'u') else 'c' if v[:1] in ('c', 's') else 'b'
        elif tok.startswith('-') and not tok.startswith('--'):
            for ch in tok[1:]:
                if ch in 'wTI':
                    break
                if ch in 'cu':
                    t = ch
    return t == 'u'


def reset_atimes():
    # strictatime tmpfs: every readdir and readlink moves the atime, so
    # directories and symlinks get a fixed one before each atime run
    paths = []
    for dp, dns, fns in os.walk(F):
        paths += [(os.path.join(dp, nm), nm) for nm in dns + fns + ['.']]
    for p, nm in paths:
        if True:
            try:
                st = os.lstat(p)
                if nm == '.' or not os.path.isfile(p) or os.path.islink(p):
                    os.utime(p, ns=(1234567890123456789, st.st_mtime_ns), follow_symlinks=False)
            except OSError:
                pass


def run(cmd, which):
    if atime_case(cmd):
        reset_atimes()
    if which == 'gnu':
        c = cmd.replace('@ls', 'ls').replace('@dir', 'dir').replace('@vdir', 'vdir')
    else:
        c = cmd.replace('@ls', NEBOX + ' ls').replace('@dir', NEBOX + ' dir').replace('@vdir', NEBOX + ' vdir')
    p = subprocess.run(['bash', '-c', c], cwd=F, env=env, capture_output=True, timeout=120)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


def run_tty(cmd, which, cols):
    c = cmd.replace('@ls', 'ls' if which == 'gnu' else NEBOX + ' ls')
    m, s = pty.openpty()
    fcntl.ioctl(s, termios.TIOCSWINSZ, struct.pack('HHHH', 24, cols, 0, 0))
    p = subprocess.Popen(['bash', '-c', c], cwd=F, env=env, stdin=subprocess.DEVNULL, stdout=s,
                         stderr=subprocess.PIPE)
    os.close(s)
    out = b''
    while True:
        r, _, _ = select.select([m], [], [], 60)
        if not r:
            break
        try:
            chunk = os.read(m, 65536)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    err = p.stderr.read()
    p.wait()
    os.close(m)
    err = err.replace(NEBOX.encode() + b' ', b'')
    return p.returncode, out, err


TTY = ['@ls t', '@ls names', '@ls -l names', '@ls -1 names', '@ls big', '@ls -x big', '@ls --color=auto t',
       'TERM=xterm @ls --color=auto t', 'TERM=xterm @ls --color=tty -l t', '@ls --classify=auto t',
       '@ls --hyperlink=auto t', 'COLUMNS=30 @ls big', '@ls -w 30 big', '@ls -N names', '@ls --show-control-chars names',
       'QUOTING_STYLE=literal @ls names', '@ls -m names', '@ls -C -T 0 big', '@ls -s t', '@ls -ls t', '@ls --zero names',
       '@ls -b names', '@ls -Q names']

bad = 0
n = 0


def report(c, g, nb):
    global bad
    bad += 1
    if bad <= 40:
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr'), g, nb):
            if x != y and isinstance(x, int):
                print('  %s gnu: %r nebox: %r' % (name, x, y))
            elif x != y:
                xl, yl = x.split(b'\n'), y.split(b'\n')
                k = 0
                while k < min(len(xl), len(yl)) and xl[k] == yl[k]:
                    k += 1
                print('  %s differs at line %d of %d/%d' % (name, k + 1, len(xl), len(yl)))
                print('    gnu:   %r' % b'\n'.join(xl[k:k + 3])[:400])
                print('    nebox: %r' % b'\n'.join(yl[k:k + 3])[:400])


for c in CASES:
    n += 1
    g = run(c, 'gnu')
    nb = run(c, 'nebox')
    if g != nb:
        report(c, g, nb)
for c in TTY:
    for cols in (80, 37):
        n += 1
        g = run_tty(c, 'gnu', cols)
        nb = run_tty(c, 'nebox', cols)
        if g != nb:
            report('[tty %d] %s' % (cols, c), g, nb)
# The GNU ls under test is built without libcap, so it never colors a file
# with a capability; nebox reads security.capability as an ls built with
# libcap does. Checked on its own: only the "ca" coloring may differ.
if HAVE_CAP:
    n += 1
    c = "LS_COLORS='ca=30;41:ex=32' @ls --color=always own/u0 own/u4242"
    g, nb = run(c, 'gnu'), run(c, 'nebox')
    capped = b'\x1b[0m\x1b[30;41mown/u0\x1b[0m\n'
    if nb[0] != g[0] or nb[2] != g[2] or not nb[1].startswith(capped) or b'own/u0\n' + nb[1][len(capped):] != g[1]:
        report(c + ' (ca)', g, nb)
print('ls_compare: %d cases%s, %d mismatches' % (n, ' (as root)' if ROOT else '', bad))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d, ignore_errors=True)
sys.exit(1 if bad else 0)
