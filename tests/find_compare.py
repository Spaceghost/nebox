#!/usr/bin/env python3
"""Side-by-side test of nebox find against GNU findutils 4.9.0 find.
Usage: tests/find_compare.py path/to/nebox [random-cases [seed]]
Both programs run as "find" from equal-length PATH directories, in the C
locale with TZ fixed, over one fixture on tmpfs (/dev/shm: fts sees the
same directory order in both runs): every file type, odd names (newlines,
tabs, backslashes, bytes above 127), symlinks (to files and directories,
dangling, self-loops, two-link loops, directory loops for -L), hard links,
setuid/setgid/sticky bits, unreadable and unsearchable directories, a path
longer than PATH_MAX, sparse files, and timestamps fixed in the past,
relative to now (for -mtime/-mmin/-daystart) and in the future. Fixed
cases cover every option, test, action and operator with their warnings
and errors, -D tree/opt/search/stat/rates/exec/time output (PIDs and
clock-derived times masked), -O0..-O3 reordering, -files0-from, -ok/-okdir
answers on standard input, -exec/-execdir with ";" and "+" (including
batches past 128 KiB), -fprint/-fprintf/-fls files (their contents are
compared), -delete on a scratch tree rebuilt before each run; then random
expressions. Cases that read or test access times reset them before each
run. Compared: stdout, stderr, exit status and the output files. As root,
some files also get owners without names (-nouser, -nogroup, -ls)."""
import os, pty, random, re, select, shutil, socket, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 2000
ONLY = os.environ.get('FIND_COMPARE_ONLY')
SEED = int(sys.argv[3]) if len(sys.argv) > 3 else 4242
ROOT = os.geteuid() == 0
d = tempfile.mkdtemp(prefix='find-compare-', dir='/dev/shm')
for w, target in (('gnu', '/usr/bin/find'), ('nbx', NEBOX)):
    os.mkdir(os.path.join(d, w))
    os.symlink(target, os.path.join(d, w, 'find'))
F = os.path.join(d, 'fx')
O = os.path.join(d, 'out')
DEL = os.path.join(d, 'del')
os.mkdir(F)
base_env = {'LC_ALL': 'C', 'TZ': 'UTC0', 'HOME': d, 'O': O, 'D': DEL}


def sh(c, cwd=F):
    subprocess.run(['bash', '-c', c], cwd=cwd, check=True, env=dict(base_env, PATH='/usr/bin:/bin'))


NOW = int(time.time())
H = 3600
DAY = 86400
sh(r"""
mkdir -p t/sub/deep/er t/emptyd t/.hdir names loop/a/b many tm acc perm
printf 'hello\n' > t/reg; : > t/empty; printf 'x%%.0s' {1..1500} > t/kb; head -c 70000 /dev/zero > t/k70
truncate -s 5G t/sparse; truncate -s 1M t/meg; printf '#!/bin/sh\necho exe\n' > t/exe; chmod 755 t/exe
printf s > t/suid; chmod 4755 t/suid; printf g > t/sgid; chmod 2750 t/sgid; printf G > t/sgidnx; chmod 2640 t/sgidnx
mkdir t/sticky t/otherw; chmod 1755 t/sticky; chmod 777 t/otherw; chmod 4644 t/empty
ln -s reg t/lreg; ln -s sub t/ldir; ln -s nowhere t/dangle; ln -s self t/self; ln -s loopb t/loopa; ln -s loopa t/loopb
ln -s /dev/null t/lnull; ln -s sub/deep t/ldeep; ln -s lreg t/llreg; ln -s reg/x t/lnotdir
mkfifo t/fifo; ln t/reg t/hard; ln t/reg t/hard2
printf h > t/.hidden; printf z > t/sub/f1; printf zz > t/sub/f2; ln -s ../reg t/sub/up; printf q > t/sub/deep/er/leaf
mkdir t/noread t/nosearch t/noread/inner 2>/dev/null; printf a > t/nosearch/inner; ln -s x t/nosearch/il; mkdir t/nosearch/sd
chmod 0 t/noread; chmod 600 t/nosearch
printf x > 'names/sp ace'; printf x > "names/q'uote"; printf x > $'names/nl\nname'; printf x > $'names/tab\tx'
printf x > $'names/\001ctl'; printf x > $'names/hi\xff'; printf x > 'names/"dq"'; printf x > 'names/back\\slash'
printf x > 'names/-dash'; printf x > 'names/star*'; printf x > 'names/[br]'; printf x > 'names/?q'; printf x > 'names/UPPER'
printf x > 'names/lower'; printf x > $'names/del\x7f'; printf x > 'names/a.b.c'; printf x > 'names/.dot'
mkdir $'names/dir\nnl'; printf x > $'names/dir\nnl/in'; ln -s $'tar\nget' names/lnk
ln -s ../.. loop/a/b/up; ln -s ../a loop/a/b/again; ln -s . loop/dot
for i in $(seq 1 40); do printf x > "many/f$i"; done
printf r > perm/r400; chmod 400 perm/r400; printf w > perm/w200; chmod 200 perm/w200; printf x > perm/x100; chmod 100 perm/x100
printf a > perm/a777; chmod 777 perm/a777; printf n > perm/n000; chmod 000 perm/n000; printf g > perm/g070; chmod 070 perm/g070
printf o > perm/o007; chmod 007 perm/o007; printf s > perm/s6755; chmod 6755 perm/s6755; mkdir perm/d711; chmod 711 perm/d711
mkdir perm/d1777; chmod 1777 perm/d1777; printf u > perm/u4000; chmod 4000 perm/u4000
touch -d '2001-02-03 04:05:06.123456789' t/reg t/hard t/kb t/sub/f1
touch -d '2001-02-03 04:05:06.5' t/empty t/k70; touch -d '1969-12-31 23:59:59' t/meg
touch -d @-1 t/exe; touch -d @0 t/fifo; touch -d @99999999999 t/suid
touch -h -d '2002-01-01' t/lreg t/dangle t/ldir
""")
for name, off in (('m0', -0.5 * H), ('m1', -1.5 * DAY), ('m2', -2.5 * DAY), ('m10', -10.5 * DAY),
                  ('m200', -200.5 * DAY), ('fut', 3.5 * DAY), ('n5', -5.5 * 60), ('n30', -30.5 * 60),
                  ('n90', -90.5 * 60), ('fmin', 10.5 * 60)):
    p = os.path.join(F, 'tm', name)
    open(p, 'w').write(name)
    os.utime(p, (NOW + off, NOW + off))
os.utime(os.path.join(F, 'tm'), (NOW - 7 * DAY, NOW - 7 * DAY))
# access times: fixed, reset before each run of a case that looks at them
ATIMES = {'a0': -0.5 * H, 'a1': -1.5 * DAY, 'a3': -3.5 * DAY, 'afut': 3.5 * DAY, 'afut9': 9.5 * DAY, 'amin': -12.5 * 60}
for name in ATIMES:
    open(os.path.join(F, 'acc', name), 'w').write(name)
s = socket.socket(socket.AF_UNIX)
s.bind(os.path.join(F, 't/sock'))
s.close()
# a path longer than PATH_MAX
cwd = os.getcwd()
os.chdir(F)
os.mkdir('long')
os.chdir('long')
for i in range(22):
    nm = ('L%02d' % i) * 50
    os.mkdir(nm)
    os.chdir(nm)
open('bottom', 'w').write('b')
os.chdir(cwd)
if ROOT:
    sh('printf o > t/owned4242; chown 4242:4343 t/owned4242; printf o > t/gonly; chown 0:4343 t/gonly; '
       'mkdir t/odir; chown 4242 t/odir')
# many long names for -exec + batches
os.mkdir(os.path.join(F, 'batch'))
for i in range(3000):
    open(os.path.join(F, 'batch', 'n%04d_' % i + 'x' * 40), 'w').close()
# past fts's inode-sort threshold (sorted only off tmpfs, or with -L where
# fts cannot ask fstatfs) and past its readdir batch of 100000 entries
for nm, cnt in (('big', 10050), ('huge', 100010)):
    os.mkdir(os.path.join(F, nm))
    for i in range(cnt):
        os.close(os.open(os.path.join(F, nm, 'e%06d' % ((i * 7919) % cnt)), os.O_CREAT | os.O_WRONLY, 0o644))
# files0 lists
open(os.path.join(F, 'list0'), 'wb').write(b't/reg\0t/sub\0names\0')
open(os.path.join(F, 'list0empty'), 'wb').write(b't/reg\0\0t/sub')
open(os.path.join(F, 'list0none'), 'wb').write(b'')
open(os.path.join(F, 'list0bad'), 'wb').write(b'nosuch\0t/reg\0')


def reset_atimes():
    for dp, dns, fns in os.walk(F):
        # reading an unsearchable directory would move its atime for good
        dns[:] = [x for x in dns if os.access(os.path.join(dp, x), os.X_OK)]
        for nm in os.listdir(dp) + ['.']:
            p = os.path.join(dp, nm)
            try:
                st = os.lstat(p)
                a = NOW - 400 * DAY
                if os.path.basename(dp) == 'acc' and nm in ATIMES:
                    a = NOW + ATIMES[nm]
                os.utime(p, (a, st.st_mtime), follow_symlinks=False)
            except OSError:
                pass


def make_del():
    subprocess.run(['chmod', '-R', 'u+rwx', DEL], stderr=subprocess.DEVNULL)
    shutil.rmtree(DEL, ignore_errors=True)
    for sub in ('a/b/c', 'a/e', 'f', 'keep/x'):
        os.makedirs(os.path.join(DEL, sub))
    for f in ('a/1', 'a/b/2', 'a/b/c/3', 'f/4', 'top', 'keep/x/5'):
        open(os.path.join(DEL, f), 'w').write(f)
    os.symlink('top', os.path.join(DEL, 'ltop'))
    os.chmod(os.path.join(DEL, 'keep'), 0o500)


CASES = []


def add(cmd, **kw):
    CASES.append((cmd, kw))


# start points, traversal, symlink modes -----------------------------------
for c in ['find', 'find .', 'find t', 'find t/', 'find t//', 'find ./t', 't', 'find t names loop',
          'find t/reg t/sub', 'find /dev/null', 'find nosuch', 'find nosuch t/reg', "find ''", "find '' t/reg",
          'find t/lreg', 'find t/ldir', 'find t/ldir/', 'find t/dangle', 'find t/self', 'find t/loopa',
          'find -P t/ldir', 'find -H t/ldir', 'find -L t/ldir', 'find -H t/lreg t/dangle t/self',
          'find -L t', 'find -H t', 'find -L loop', 'find -L t/self', 'find -L t/loopa', 'find -L t/dangle',
          'find -L t/lnotdir', 'find -H t/lnotdir', 'find -L names', 'find -L -P t/ldir', 'find -P -L t/ldir',
          'find -L t/sub -follow', 'find t -follow', 'find t/sub -follow -name up', 'find -- t', 'find -L -- t/ldir',
          'find -- -L t', 'find long', 'find long -name bottom', 'find -L long -type f', 'find many',
          'find t/noread', 'find t/nosearch', 'find t/noread t/nosearch -depth', 'find t/nosearch -type f',
          'find t/nosearch -name inner', 'find t/nosearch -print -type d', 'find / -maxdepth 0', 'find // -maxdepth 0',
          'find /. -maxdepth 0', 'find .. -maxdepth 0', 'find t/sub/.. -maxdepth 1', 'find t/. -maxdepth 1',
          'find -L t/sub/up t/ldeep', 'find t -xdev -maxdepth 1', 'find t -mount -maxdepth 1',
          'find t -noleaf', 'find t -ignore_readdir_race',
          'find t -noignore_readdir_race', 'find t -maxdepth 1 -ignore_readdir_race -print']:
    add(c)
for c in ['find big', 'find -L big', 'find -H big', 'find big -name "e0000*"', 'find -L big -printf "%f %i\\n"',
          'find huge | head -3; find huge | tail -3; find huge | wc -l', 'find -L huge | md5sum', 'find huge | md5sum',
          'find -L big -D search -name x 2>&1 | head -20', 'find huge -maxdepth 0 -empty -o -type f -name e099999']:
    add(c)
# depth options
for c in ['find t -maxdepth 0', 'find t -maxdepth 1', 'find t -maxdepth 2 -mindepth 2', 'find t -mindepth 1',
          'find t -mindepth 9', 'find t -maxdepth -1', 'find t -maxdepth x', 'find t -maxdepth 1x', "find t -maxdepth ''",
          'find t -maxdepth', 'find t -maxdepth 99999999999', 'find t -maxdepth +1', 'find t -mindepth 2147483648',
          'find t -depth', 'find t -d', 'find t -depth -maxdepth 1', 'find t -mindepth 1 -depth -print0',
          'find t -mindepth 2 -print0', 'find t -maxdepth 1 -depth -mindepth 1', 'find -maxdepth 0',
          'find t/sub -depth -name deep -prune', 'find t -warn -name reg -maxdepth 1', 'find t -name reg -maxdepth 1 -warn',
          'find t -warn -type f -mindepth 1', 'find t -warn -print -depth', 'find t -warn -d', 'find t -warn -xdev -mount',
          'find t -warn -daystart -follow -regextype emacs -name x', 'find t -nowarn -name x -maxdepth 1',
          'find t -warn -nowarn -name x -maxdepth 1', 'find -warn -maxdepth 1 t', 'find t -warn -noleaf -name x',
          'find t -warn \\( -maxdepth 1 \\)', 'find t -warn ! -maxdepth 1', 'find t -warn -files0-from list0']:
    add(c)
# expression syntax and errors
for c in ['find t -a', 'find t !', 'find t -not', 'find t \\(', 'find t \\)', 'find t \\( \\)', 'find t -name x \\)',
          'find t ! -o -print', 'find t -true -a', 'find t \\( -not \\)', 'find t \\( -true -a \\)', 'find t -o',
          'find t ,', 'find t -print ,', 'find t -print , -name reg', 'find t -name reg , -print',
          'find t \\( -name reg \\) \\)', 'find t \\( \\( -true \\)', 'find t -name reg -print \\( -o \\)',
          'find t -foo', 'find t -name', 'find t -type', 'find t reg', 'find t -name reg t', 'find t -name reg sub',
          'find t -print names', 'find t ! ! -name reg', 'find t -name reg -o -name sub -print',
          'find t \\( -name reg -o -name sub \\) -print', 'find t -name reg -or -name f1', 'find t -not -name "*e*"',
          'find t -name reg -and -type f', 'find t -name reg -a -type f -o -type l', 'find t -type l , -type p',
          'find t -true , -false', 'find t -false , -true', 'find t ! \\( -type f -o -type d \\)',
          'find t -noop', 'find t ---noop', 'find t --noop', 'find t -', 'find t -newerXY x', 'find t -printf',
          'find t -exec', 'find t -exec ";"', 'find t -exec echo', 'find t -ok', 'find t -fprint', 'find t -fprintf $O/x',
          'find t \\!', 'find t \\(x', 'find t ")x"', 'find t ",x"', 'find \\! t', 'find \\( t', 'find ")" t', 'find , t',
          'find t -maxdepth 1 \\( -print \\)', 'find t -name reg -print -print']:
    add(c)
# -O and -D
for o in ['-O0', '-O1', '-O2', '-O3', '-O4', '-O9', '-O', '-Ox', '-O1x', '-O99999', '-O65535', '-O65536',
          '-O-1', '-O 3', '-O3 -O0']:
    add('find %s t -name "*e*" -type f -o -type d -print' % o)
for o in ['-O0', '-O1', '-O2', '-O3']:
    for e in ['-name x -o -type l -o -size +1 -print', '! -type f -o -type d', '-type d -o -size 0 -name "*m*"',
              '-perm -100 -name "e*" -type f -inum 1 -links 2', '-name "*e*" -regex ".*b.*" -empty -ls',
              '-print -name reg -fstype tmpfs -type f', '-lname "*e*" -o -nouser -o -readable -o -samefile t/reg']:
        add('find %s -D opt t %s' % (o, e))
        add('find %s -D tree t %s' % (o, e))
        add('find %s -D rates t %s' % (o, e))
for c in ['find -D tree t', 'find -D tree t -name reg -o -size +2k', 'find -D tree t -print0',
          'find -D tree t -maxdepth 1 -name reg', 'find -D tree t -daystart -name reg', 'find -D tree t -name x -daystart',
          'find -D tree t -files0-from list0', 'find -D tree -files0-from list0 -name reg',
          "find -D tree t -printf '%p\\n%A\\101x'", 'find -D tree t -size +3k -type f', 'find -D tree t -newermt @0',
          'find -D tree t -newer t/reg -exec echo {} +', 'find -D tree t -follow -regextype grep -nowarn -warn',
          'find -D tree t -inum 5 -links -2 -uid +3 -gid 0', 'find -D tree t ! -name reg , -prune',
          'find -D search t/sub', 'find -D search -L t/sub', 'find -D search t/noread t/nosearch', 'find -D search -depth t/sub',
          'find -D search t/dangle t/self -L', 'find -D stat t/sub', 'find -D stat t -type f -newer t/reg',
          'find -D stat -L t/sub t/dangle', 'find -D stat -H t/lreg t/ldir', 'find -D stat t -samefile t/reg',
          'find -D stat t -xtype l', 'find -D stat t -inum 3', 'find -D stat t/sub -printf "%i %y %Y\\n"',
          'find -D rates t -name reg', 'find -D rates t -print -o -print', 'find -D help', 'find -D bogus t -maxdepth 0',
          "find -D '' t", 'find -D', 'find -D tree,stat t/sub', 'find -D ,tree,, t/sub', 'find -D stat,bogus t/sub',
          'find -D exec t/sub -exec true {} \\;', 'find -D exec t/sub -exec true {} +', 'find -D exec t/sub -execdir echo {} +',
          'find -D all t/sub', 'find -D time t -maxdepth 0', 'find -D tree t -mtime 1', 'find -D tree t -mmin -3 -amin +2',
          'find -D opt t -fstype nosuchfs', 'find -O1 -D opt t -fstype nosuchfs', 'find -D opt t -fstype tmpfs',
          'find -D tree -O3 t \\( -name a -o -name b \\) -a \\( -type f -o -type d \\)',
          'find -D opt t -name a -o -name b -o -type f , -name c -print']:
    add(c, mask=True)
# names and paths
for p in ['reg', '"*e*"', '"[a-f]*"', '"[!a-f]*"', '"[^a-f]*"', '"*[[:digit:]]"', '"[[:upper:]]*"', '"*[[:punct:]]*"',
          '"\\*"', '"star\\*"', '"*\\"', '"[br]"', '"\\[br]"', '"[[]br]"', '"[]]"', '"[]a]*"', '"[!]]*"', '"[a-]*"',
          '"[z-a]*"', '"?q"', '"\\?q"', '"*.*"', '".*"', '"*"', '"t"', '"sub/"', '"/"', '"[[:alpha:]"', '"[[:foo:]]*"',
          '"[[=a=]]*"', '"[[.a.]]*"', '"[[.-.]]*"', '"[[.a.]-z]*"', '"[a-[.z.]]*"', '"*[[:space:]]*"', '"*[[:cntrl:]]*"',
          '"[[:lower:]]*"', '"[[:xdigit:]]*"', '"a*b*c"', '"*a*b*c*d*e*f*"', '"**"', '"*?"', '"???"', '"[\\]]"',
          '"[\\!]*"', '"[[:"', '"[a"', '"\\"', '"[[:alpha:]-z]*"', '"[--0]*"']:
    add('find t names -name %s' % p)
    add('find t names -iname %s' % p)
for p in ['"t/sub*"', '"*/sub/*"', '"t/*/f1"', '"*e*"', '"t/sub/"', '"t/"', '"T/SUB*"', '"*[!/]"', '"*/.*"', '"./t*"',
          '"*/[[:upper:]]*"', '"*\\n*"', '"names/*"']:
    for t in ['-path', '-ipath', '-wholename', '-iwholename']:
        add('find t names %s %s' % (t, p))
add('find t/ -path t/')
add('find t/ -ipath T/')
add('POSIXLY_CORRECT=1 find t -path "t/sub/"')
add('find t -warn -name "t/reg"')
add('find t -warn -iname "a/b" -name c/d')
add('find t -lname "*e*"')
add('find t -ilname "*E*"')
add('find t -lname "*" -type f')
add('find -L t -lname "*"')
add('find names -lname "*nl*"')
add('find t/nosearch -lname x')
# regular expressions and -regextype
REGEXES = ['".*e.*"', '"t/s.*"', '".*/[a-f].*"', '".*\\(eg\\|ub\\).*"', '".*(eg|ub).*"', '".*e+.*"', '".*e\\+.*"',
           '".*e?g"', '".*e\\?g"', '".*[[:digit:]]"', '".*[0-9]"', '".*/f[12]"', '".*/f\\{1\\}[12]"', '".*/f{1}[12]"',
           '".*\\(.\\)\\1.*"', '"\\(.*\\)/\\1"', '".*\\w"', '".*\\W.*"', '".*\\bsub\\b.*"', '"^t.*"', '".*g$"', '"t.*$"',
           '"t/^.*"', '".*$/.*"', '"*t.*"', '"+t.*"', '"t.*\\"', '"t.*["', '"t.*\\("', '"t.*\\)"', '"t.*)"', '"t.*("',
           '".*{"', '".*\\{"', '".*e{2,1}.*"', '".*e\\{,2\\}g"', '".*[z-a]"', '".*[a-"', '"(t|n).*"', '"\\(t\\|n\\).*"',
           '"t/[^/]*"', '"t/.*\\."', '".*\\\'"', '"\\`t.*"', '".*\\<reg"', '".*g\\>"', '".*[[:alpha:]]\\{3\\}"',
           '".*[\\]]"', '".*[\\\\]"', '".*\\s.*"', '"names/.*"', '"names/[^n]*"', '"names/.*\\n.*"', '"names/nl.name"',
           '"t/R.*"', '".*\\T"', '".*\\t"', '"[T]/.*"', '"t/[[:upper:]]*"', '""', '"x**"', '"a|*b"', '"(*b)"', '"()"']
for rt in ['', '-regextype findutils-default', '-regextype emacs', '-regextype posix-basic', '-regextype posix-extended',
           '-regextype posix-egrep', '-regextype egrep', '-regextype grep', '-regextype awk', '-regextype gnu-awk',
           '-regextype posix-awk', '-regextype ed', '-regextype sed', '-regextype posix-minimal-basic']:
    for r in REGEXES:
        add('find t names %s -regex %s' % (rt, r))
    for r in REGEXES[:20]:
        add('find t names %s -iregex %s' % (rt, r))
add('find t -regextype bogus -regex x')
add('find t -regextype')
add('find t -regex x -regextype posix-extended -regex "t|x"')
# types
for t in ['f', 'd', 'l', 'p', 's', 'b', 'c', 'f,d', 'l,p,s', 'd,f,l', 'D', 'x', 'f,', 'fd', 'f,f', "''", ',f', 'f,,d']:
    add('find t /dev/null -type %s' % t)
    add('find t /dev/null -xtype %s' % t)
    add('find -L t /dev/null -xtype %s' % t)
    add('find -L t /dev/null -type %s' % t)
add('find -H t/lreg t/ldir t/dangle -type l')
add('find -H t/lreg t/ldir t/dangle -xtype l')
# sizes and numbers
for s in ['0', '-1', '+0', '+1', '1', '1c', '6c', '-7c', '+6c', '2b', '3', '1k', '-2k', '+1k', '2k', '69k', '+68k',
          '1M', '-2M', '+1M', '5G', '-6G', '+4G', '3w', '+3w', 'k', '1x', "''", '+-1', '-+1', ' 1', '1 ', '++1',
          '18446744073709551616', '99999999999999999999k', '0x10', '1.5k']:
    add('find t -size %s' % s)
for n in ['links', 'inum', 'uid', 'gid']:
    for v in ['1', '+1', '-2', '2', '+0', '-0', 'x', "''", '1x', '-+1', '18446744073709551615', '18446744073709551616',
              '+999', '-1001', '1000', '0']:
        add('find t -%s %s' % (n, v))
add('find t -inum $(stat -c %i t/reg)')
add('find t -inum +$(stat -c %i t/reg) -inum -$(( $(stat -c %i t/reg) + 3 ))')
add('find t -samefile t/reg')
add('find t -samefile t/hard2 -printf "%p %n\\n"')
add('find t -samefile t/lreg')
add('find -L t -samefile t/lreg')
add('find -H t -samefile t/lreg')
add('find t -samefile nosuch')
add('find t -samefile')
add('find t -samefile t/sub -prune')
# users and groups
for u in ['build', 'root', '1000', '0', '4242', 'nosuch', "''", '99999999999', '1x', 'x1', '-1', '+1']:
    add('find t -user %s' % u)
    add('find t -group %s' % u)
add('find t -nouser')
add('find t -nogroup')
add('find t -nouser -o -nogroup -ls')
add('find t -printf "%u %g %U %G\\n"')
# permissions and access
for m in ['644', '-644', '/644', '755', '-755', '/755', '4755', '-4000', '/4000', '-2000', '/6000', '1755', '-1000',
          'u+x', '-u+x', '/u+x', 'u=rwx,go=rx', '-u=r', '/u=w,g=w', 'a+r', '-a+r', '/a+w', 'g=u', '-g=u', '+7', '+0644',
          '-', '/', '000', '/000', '-000', '/u-w', '/a-rwx', 'o+t', '-o+t', '-u+s', '/g+s', 'x', '999', '-u+X', '+r',
          'u=', '-=', '/=']:
    add('find t perm -perm %s' % m)
for a in ['-readable', '-writable', '-executable', '! -readable', '-readable -writable', '-executable -type d']:
    add('find t perm %s' % a)
add('find -L t -readable')
add('find t -fstype tmpfs')
add('find t -fstype ext4')
add('find -O1 t -fstype ext4')
add('find t /proc/self/stat -fstype proc')
add('find t -maxdepth 1 -printf "%F\\n"')
add('find t -context x')
add('find t -context')
add('find t/sub -printf "%Z|\\n"')
add('find t -empty')
add('find t -empty -type d')
add('find t ! -empty -type f')
add('find t/noread -empty')
add('find -L t -empty')
add('find t -false')
add('find t -true')
add('find t -true -o -false -print')
# times
for t in ['-mtime', '-mmin', '-ctime', '-cmin']:
    for v in ['0', '-1', '+0', '1', '+1', '2', '-3', '+10', '10', '-11', '200', '+199', '1.5', '-1.5', '+0.5', '0.25',
              'x', "''", '--1', '+-1', '-+1', ' 1', '1e1', '0x1', 'inf', '-inf', 'nan', '1e300', '+30', '-30', '5', '-6',
              '30', '31', '90', '+89', '-91']:
        add('find tm %s %s' % (t, v))
        add('find tm -daystart %s %s' % (t, v))
add('find tm -mtime 0 -daystart -mtime 0')
add('find tm -daystart -daystart -mmin -100')
add('find tm -mmin -10 -mtime 0')
for t in ['-atime', '-amin', '-used']:
    for v in ['0', '-1', '+0', '1', '+1', '3', '-4', '+2', '9', '+8', '1.5', 'x', '-12', '+12', '13', '-13']:
        add('find acc %s %s' % (t, v), atime=True)
        add('find acc -daystart %s %s' % (t, v), atime=True)
add('find acc -printf "%p %A@ %AY %Ak\\n"', atime=True)
add('find acc -anewer acc/a1', atime=True)
add('find acc -neweraa acc/a3 -o -newerma acc/a1', atime=True)
add('find acc -newerat @%d' % (NOW - 2 * DAY), atime=True)
add('find acc -type f -printf "%a|%A+\\n"', atime=True)
for ref in ['t/reg', 't/kb', 't/empty', 'tm/m1', 'tm/m10', 'tm/fut', 'nosuch', 't/lreg', 't/dangle']:
    add('find t tm -newer %s' % ref)
    add('find -L t tm -newer %s' % ref)
    add('find t tm -cnewer %s' % ref)
for xy in ['mm', 'mc', 'cm', 'cc', 'ma', 'ca', 'am', 'ac', 'mB', 'Bm', 'Bt', 'tm', 'tt', 'mx', 'xm', 'mmm', 'm']:
    add('find t tm -newer%s t/reg' % xy)
for dt in ['@0', '@981173106', '@981173106.2', '@981173106.123456789', '2001-02-03', '"2001-02-03 04:05:06"',
           '"2001-02-03 04:05:06.123456789"', '"2001-02-03 04:05:07 UTC"', '1970-01-01', 'bogus', "''", '"1 day ago"',
           '"next year"', '@-1', '"TZ=\\"America/New_York\\" 2001-02-02 23:05"', '2001-02-03T04:05:06Z']:
    add('find t tm -newermt %s' % dt)
    add('find t tm -newerct %s -o -print' % dt)
add('find t -newermt')
add('find t -newer')
add('find t -anewer')
# -printf
FMTS = ['%p\\n', '%f\\n', '%h\\n', '%H|%P\\n', '%d %y %Y\\n', '%s %k %b\\n', '%m %M\\n', '%#m %04m %-5m|\\n',
        '%i %n\\n', '%u %g %U %G\\n', '%l\\n', '%t\\n', '%T@ %T+\\n', '%TY-%Tm-%Td %TH:%TM:%TS %Tz %TZ\\n',
        '%Ta %TA %Tb %TB %Tc %TC %TD %Te %TF %Tg %TG %Th %TI %Tj %Tk %Tl %Tn %Tp %TP %Tr %TR %Ts %Tt %TT %Tu %TU %TV %Tw %TW %Tx %TX %Ty\\n',
        '%T%\\n', '%TN %Tq %T: %T_ %T- %TE %TO %T0 %T#|\\n', '%T', '%Tk', '%C@\\n', '%Ck\\n', '%c\\n',
        '%B@ %Bk %BT|\\n', '%D\\n', '%S\\n', '%10p|%-10f|%.3f|\\n', '%5.2s|%-6d|%+d|% d|%5d\\n',
        '%#d %0d %#s %+s %#y\\n', '%%\\n', '%5%|\\n', 'a%%b%%%%\\n', '%z\\n', '%5z|\\n', '%{', '%[', '%(', '%',
        '%5', '%-', '%.', 'abc', '\\a\\b\\f\\n\\r\\t\\v\\\\|', '\\0|\\00|\\000|\\0000|\\101\\777\\8\\9\\n',
        '\\q\\w\\n', 'x\\', 'x\\c', '%p\\cdead', '\\c', '%p%%%p\\n', '%P\\0', '%f/%h/%P\\n', '%-3y%3Y|\\n',
        '%l|%y|%Y\\n', '[%s] [%k] [%b]\\n', '%A', '%Ax\\n', '%a', '%ZZ', '%Tz%Tl\\n', '%T@%T@\\n',
        '%M %10M|%-12M|\\n', '%i %10i|\\n', '%.0p|%.1p|\\n', '%1$s', '%*d\\n', '%hd\\n', '%lld\\n']
for fm in FMTS:
    add("find t -maxdepth 2 -printf '%s'" % fm, atime='%A' in fm or '%a' in fm)
add("find long names -printf '%p|%f|%h|%d|%P\\n'")
add("find t/ t// t/sub/ -printf '%p|%f|%h|%H|%P|%d\\n'")
add("find / -maxdepth 0 -printf '%p|%f|%h|%P\\n'")
add("find // -maxdepth 0 -printf '%p|%f|%h|%P\\n'")
add("find -L t loop -maxdepth 3 -printf '%p %y %Y %l\\n'")
add("find t -maxdepth 1 -printf '%Y\\n' -name lnotdir")
add("find t/nosearch -printf '%p %y %Y %s\\n'")
add("find t -printf '%p ' -printf '%s\\n'")
add("find t -maxdepth 1 -printf '%CY-%Cm|%Cs|%Cc\\n' -type f")
add("find tm -printf '%p %TY %Tj %TU %TV\\n'")
add("TZ=America/New_York find t -maxdepth 1 -printf '%t %TZ %Tz %T+ %C+\\n'")
add("TZ=Asia/Kolkata find t -maxdepth 1 -printf '%t %TZ %Tz %Tc\\n'")
add("TZ=EST5EDT find t -maxdepth 1 -printf '%TZ %Tz\\n'")
# -print0, -ls, -fprint and friends
for c in ['find t -print0', 'find names -print0', 'find t -ls', 'find names -ls', 'find -L t -ls', 'find long -ls',
          'find t/sub -ls -ls', 'find perm -ls', 'POSIXLY_CORRECT=1 find t -ls', 'find tm -ls', 'find /dev/null -ls',
          'find t -fls $O/l', 'find t -fprint $O/p', 'find t -fprint0 $O/p0', 'find t -fprintf $O/f "%p %s\\n"',
          'find t -fprint $O/p -fprint $O/p', 'find t -fprint $O/p -fprint0 $O/p -name reg',
          'find t -fprint /dev/stdout', 'find t -fprint /dev/stderr', 'find t -fprintf /dev/stderr "%f\\n"',
          'find t -fls /dev/stdout -name reg', 'find t -fprint /nonexistent/x', 'find t -fprint $O',
          'find t -name nomatch -fprint $O/empty', 'find t -fprint $O/x -quit', 'find t -false -fprint $O/never',
          'find t -fprint $O/a -name reg -fprint $O/b', 'find t -fprint0', 'find t -fls',
          'find t -fprint $O/z -fprint $O/y -fprint $O/x -fprint $O/w', 'find t/sub -print -fprint /dev/stdout']:
    add(c)
# -exec, -execdir, -ok, -okdir
for c in ['find t/sub -exec echo {} \\;', 'find t/sub -exec echo {} +', 'find t/sub -exec echo x{}y {}{} \\;',
          'find t/sub -exec echo \\{\\} + -name f1', 'find t/sub -exec echo a b {} +', 'find t/sub -exec echo {} x +',
          'find t/sub -exec echo {} {} +', 'find t/sub -exec echo {}x +', 'find t/sub -exec echo {} + -exec echo {} +',
          'find t/sub -exec false \\;', 'find t/sub -exec false {} +', 'find t/sub -exec true {} +',
          'find t/sub -exec false \\; -print', 'find t/sub -exec sh -c "exit 3" \\; -o -print',
          "find t/sub -exec sh -c 'kill -9 $$' \\;", "find t/sub -exec sh -c 'kill -15 $$' sh {} +",
          'find t/sub -exec nosuchcmd \\;', 'find t/sub -exec nosuchcmd {} +', 'find t/sub -exec ./nosuch \\;',
          "find t/sub -exec '' \\;", 'find t/sub -exec t/noexec \\;', 'find t/sub -exec ; -print',
          'find t/sub -exec echo ;', 'find t/sub -exec {} \\;', 'find t/sub -exec echo {} + ";"',
          'find t/sub -exec echo {} \\; -exec echo second {} \\;', 'find t/sub -exec echo + \\;',
          'find t/sub -exec echo {} + -quit', 'find t/sub -exec echo {} \\; -quit', 'find t/sub -print -exec echo {} +',
          'find batch -exec sh -c \'echo $#\' sh {} +', 'find batch -name "n00*" -exec sh -c \'echo $# "$1"\' sh {} +',
          'find t/sub -execdir echo {} \\;', 'find t/sub -execdir echo {} +', 'find t/sub -execdir pwd \\;',
          'find t/sub -execdir sh -c "pwd; echo \\"$@\\"" sh {} +', 'find t -maxdepth 2 -execdir echo {} +',
          'find / -maxdepth 0 -execdir echo {} \\;', 'find . -maxdepth 0 -execdir echo {} \\;',
          'find t/sub/ -maxdepth 0 -execdir echo {} \\;', 'find -L t/ldir -execdir echo {} \\;',
          'find t/sub -execdir {} \\;', 'find t/sub -execdir echo {} {} +', 'find t/sub -execdir false {} +',
          'PATH=.:$PATH find t/sub -execdir echo {} \\;', 'PATH=$PATH: find t/sub -execdir echo {} \\;',
          'PATH=$PATH::/x find t/sub -okdir echo {} \\;', 'PATH=rel:$PATH find t/sub -execdir echo {} \\;',
          'PATH= find t/sub -execdir echo {} \\;', 'PATH=.:$PATH find t/sub -exec echo {} \\;',
          'find t/sub -exec sh -c "ls -l /proc/self/fd | wc -l" \\;', 'find t/sub -exec sh -c "cat >/dev/null; echo ok" \\;',
          'find t/sub -name f1 -exec sh -c "read x; echo got=\\$x" \\;', 'find t/sub -exec echo {} + -fprint $O/both',
          '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=2 find t/sub -exec echo {} +',
          '__GNU_FINDUTILS_EXEC_ARG_LENGTH_LIMIT=x find t/sub -exec echo {} \\;']:
    add(c, stdin=b'line\n')
add('find t/sub -ok echo {} \\;', stdin=b'y\nn\nyes\nY\nno\n')
add('find t/sub -ok echo {} \\;', stdin=b'')
add('find t/sub -ok echo {} \\; -print', stdin=b'n\ny\n')
add('find t/sub -okdir echo {} \\;', stdin=b'y\ny\ny\ny\ny\n')
add('find t/sub -ok echo {} +', stdin=b'y\n')
add('find t/sub -ok sh -c "cat; echo ok" \\;', stdin=b'y\nsecret\n')
add('find t/sub -okdir {} \\;', stdin=b'y\n')
add('find -files0-from - -ok echo {} \\;', stdin=b't/reg\0')
add('find -files0-from list0 -ok echo {} \\;', stdin=b'y\ny\n')
add('find -files0-from list0 -ok echo {} \\; < list0', stdin=b'')
add('find t/sub -exec echo {} \\; -ok echo {} \\;', stdin=b'y\n\n')
# -files0-from
for c in ['find -files0-from list0', 'find -files0-from list0 -name reg', 'find -files0-from list0empty',
          'find -files0-from list0none', 'find -files0-from list0bad', 'find -files0-from nosuch', 'find -files0-from t',
          'find -files0-from list0 t', 'find t -files0-from list0', 'find -files0-from', 'find -files0-from - < list0',
          'printf "t/sub\\0\\0t/reg" | find -files0-from -', 'printf "" | find -files0-from -',
          'find -files0-from list0 -files0-from list0bad', 'find -files0-from list0 -print0',
          'find -files0-from list0 -maxdepth 0', 'find -files0-from /dev/null']:
    add(c)
# -prune, -quit, -delete
for c in ['find t -name sub -prune', 'find t -name sub -prune -o -print', 'find t -prune', 'find t -depth -prune',
          'find t -prune -depth', 'find t -name sub -prune , -print', 'find t -type d -prune -o -type f -print',
          'find t t/sub -name sub -prune -o -print', 'find t -quit', 'find t -name sub -quit', 'find t nosuch -quit',
          'find nosuch t -quit', 'find t -print -quit', 'find t -name reg -print -quit -o -print',
          'find t/noread -quit', 'find t -false -quit', 'find t -maxdepth 1 -prune -print']:
    add(c)
for c in ['find $D -delete', 'find $D -name 1 -delete', 'find $D -name a -delete', 'find $D -type f -delete',
          'find $D -depth -name x -delete', 'find $D -name a -prune -delete', 'find $D -depth -name a -prune -delete',
          'find $D -delete -print', 'find $D -print -delete', 'find $D/top $D/ltop -delete', 'find $D/ltop -L -delete',
          'find -L $D -delete', 'find $D/keep -delete', 'cd $D && find . -delete', 'cd $D && find -delete',
          'cd $D && find . -name top -delete', 'find $D -name 3 -delete -o -print', 'find $D -ignore_readdir_race -delete',
          'find $D/nosuch -delete', 'find $D -mindepth 2 -delete', 'find $D -maxdepth 1 -name f -delete',
          'find $D -delete -name keep', 'find $D/a/b -delete -quit']:
    add(c + '; find $D | sort', delete=True)
# exit statuses and diagnostics
for c in ['find t nosuch; echo $?', 'find nosuch t/reg -name x; echo $?', 'find t/noread; echo $?',
          'find t -name reg -o -print >/dev/full; echo $?', 'find t -maxdepth 0 > /dev/full; echo $?',
          'find t -maxdepth 0 -fprint /dev/full; echo $?', 'find batch -print >/dev/full; echo $?',
          'find t -maxdepth 0 >&-; echo $?', 'find t -printf "%p\\c" >/dev/full; echo $?',
          'find t -maxdepth 0 -fprintf /dev/full "%p"; echo $?', 'FIND_BLOCK_SIZE=1 find t; echo $?',
          'find -L t/self t/loopa t/dangle; echo $?', 'find t/dangle -L; echo $?', 'find t/sub -exec false {} + ; echo $?',
          'find t/sub -exec false {} \\; ; echo $?', 'find t/sub -quit -exec false {} +; echo $?',
          'find t/sub -name f1 -exec false {} + -quit; echo $?']:
    add(c)
add('find --version | head -1 | sed "s/(.*//"', nover=True)
add('find --help | head -40')
add('find -help | head -3')
add('find t --help | head -3')
add('find -version | sed -n 2p', nover=True)
# odd names
for c in ['find names', 'find names -name "*\n*"', 'find names -printf "%p|%f\\n"', 'find names -print0',
          'find names -ls', 'find names -exec echo {} \\;', 'find names -execdir echo {} +', 'find names -lname "*"',
          'find names -regex ".*\\(ctl\\|del\\).*"', "find names -name $'*\\xff'", 'find names -fprint $O/n',
          'find names -fls $O/nl']:
    add(c)
if ROOT:
    for c in ['find t -user 4242', 'find t -uid 4242', 'find t -group 4343', 'find t -nouser', 'find t -nogroup',
              'find t -nouser -ls', 'find t -name "o*" -ls', 'find t -name "o*" -printf "%u %g %U %G\\n"',
              'find t/noread t/nosearch', 'find t/noread t/nosearch -ls', 'find perm -readable', 'find perm -writable',
              'find perm -executable', 'find t -name "*own*" -ls -fls $O/root']:
        add(c)

NFIXED = len(CASES)
# random expressions --------------------------------------------------------
rnd = random.Random(SEED)
PATS = ['"*e*"', 'reg', '"f?"', '"[a-m]*"', '"*.*"', 'sub', '"*[0-9]"', '"S*"', '"*"', '"[!s]*"']
TESTS = ['-name %P', '-iname %P', '-path "t/s*"', '-ipath "*/SUB*"', '-regex ".*e.*"', '-iregex ".*[A-F].*"',
         '-type f', '-type d', '-type l', '-type p,s', '-xtype f', '-xtype l', '-size +0', '-size -2', '-size 1k',
         '-size +1M', '-empty', '-perm -444', '-perm /111', '-perm 644', '-links 1', '-links +1', '-newer t/reg',
         '-newer tm/m10', '-mtime +1', '-mtime -3', '-mmin -60', '-user build', '-group build', '-uid +0',
         '-gid -2000', '-samefile t/reg', '-lname "*e*"', '-readable', '-writable', '-executable', '-true', '-false',
         '-fstype tmpfs', '-nouser', '-nogroup', '-inum +0', '-newermt @0', '-cmin -100', '-ilname "*SUB*"']
ACTS = ['-print', '-print0', '-ls', '-prune', '-printf "%p %y %s\\n"', '-printf "[%f|%h|%d]\\n"',
        '-printf "%m %M %n\\n"', '-printf "%Y %l\\n"', '-fprint $O/r', '-exec echo {} \\;', '-exec echo X {} +',
        '-execdir echo {} \\;', '-printf "%T@ %k\\n"', '-fprintf $O/q "%P\\n"']
OPTS = ['', '', '', '-maxdepth 1', '-maxdepth 2', '-mindepth 1', '-mindepth 2 -maxdepth 3', '-depth', '-xdev',
        '-noleaf', '-ignore_readdir_race']
LEAD = ['', '', '', '-L', '-H', '-P', '-O0', '-O1', '-O3', '-L -O3', '-H -O0']
STARTS = ['t', 't/sub', 'names', 'tm', 't perm', 'loop', 't/lreg t/ldir', 't/dangle t/self', 'many', 't/nosearch']


def rexpr(depth):
    k = rnd.random()
    if depth > 3 or k < 0.45:
        return rnd.choice(TESTS).replace('%P', rnd.choice(PATS)) if rnd.random() < 0.8 else rnd.choice(ACTS)
    if k < 0.6:
        return '! ' + rexpr(depth + 1)
    if k < 0.7:
        return '\\( %s \\)' % rexpr(depth + 1)
    op = rnd.choice(['', '-a', '-o', '-o', ',', '-and', '-or'])
    return '%s %s %s' % (rexpr(depth + 1), op, rexpr(depth + 1))


for _ in range(NRAND):
    e = rexpr(0)
    if rnd.random() < 0.05:
        e += ' -quit'
    if rnd.random() < 0.03:
        e = rnd.choice(['\\(', '\\)', '-a', '!']) + ' ' + e
    CASES.append(('find %s %s %s %s' % (rnd.choice(LEAD), rnd.choice(STARTS), rnd.choice(OPTS), e), {}))


NEXPR = len(CASES) - NFIXED
# random -printf formats, regular expressions and glob patterns
FPIECES = ['a', 'Z', ' ', '|', '/', '-', '0', '9', '%', '\\\\', '\\n', '\\t', '\\0', '\\12', '\\101', '\\777', '\\c',
           '\\q', '\\x', '\\8', '\\']
FDIRS = 'abcdDfFgGhHiklmMnpPsStuUyYZ%zq{[(' + "ABCT"
TCHARS = 'aAbBcCdDeFgGhHIjklmMnpPrRsStTuUVwWxXyYzZ%@+NqE-0_'
def stray_percent(fm):
    # scan as insert_fprintf does: does an unrecognized escape keep a '%'?
    i = 0
    while i < len(fm):
        c = fm[i]
        if c == '\\':
            if i + 1 >= len(fm) or fm[i + 1] == 'c':
                return False
            if fm[i + 1] == '%':
                return True
            i += 2
            while fm[i - 1] in '01234567' and i < len(fm) and fm[i] in '01234567':
                i += 1
            continue
        if c == '%':
            i += 1
            if i < len(fm) and fm[i] == '%':
                i += 1
                continue
            while i < len(fm) and fm[i] in '-+ #':
                i += 1
            while i < len(fm) and fm[i].isdigit():
                i += 1
            if i < len(fm) and fm[i] == '.':
                i += 1
                while i < len(fm) and fm[i].isdigit():
                    i += 1
            if i < len(fm) and fm[i] in 'ABCT':
                i += 1
            i += 1
            continue
        i += 1
    return False


for _ in range(NRAND // 4):
    fm = ''
    for _ in range(rnd.randint(1, 6)):
        if rnd.random() < 0.55:
            fl = ''.join(rnd.choice('-+ #0') for _ in range(rnd.choice([0, 0, 1, 2])))
            wd = rnd.choice(['', '', '3', '12', '05'])
            pr = rnd.choice(['', '', '.2', '.0', '.'])
            c = rnd.choice(FDIRS)
            fm += '%' + fl + wd + pr + c
            if c in 'ABCT':
                fm += rnd.choice(TCHARS)
        else:
            fm += rnd.choice(FPIECES)
    fm = fm.replace("'", '')
    # an odd backslash before % leaves a stray conversion in the text GNU
    # hands to printf with the directive's one argument: undefined behaviour
    if stray_percent(fm):
        continue
    # readlink moves a symlink's atime
    if re.search(r'%[-+ #0-9.]*[aA]', fm) and re.search(r'%[-+ #0-9.]*l', fm):
        continue
    CASES.append(("find t/sub t/lreg t/dangle t/fifo -printf '%s\\n'" % fm,
                  {'atime': re.search(r'%[-+ #0-9.]*[aA]', fm) is not None}))
RPIECES = ['.', '*', '+', '?', '\\(', '\\)', '(', ')', '|', '\\|', '[a-z]', '[^0-9]', '[[:alpha:]]', '{2}',
           '\\{1,2\\}', '{,3}', '^', '$', '\\w', '\\W', '\\<', '\\>', '\\b', '\\1', 'a', 'e', 's', 't', '/',
           '\\.', '[]a]', '[a-]', '\\', '[', ']', '{', '}', '\\{', '\\}', 'E', '[[:upper:]]', '\\`', "\\'",
           '\\s', '[\\]]', '[.]', '.*', '.*', '\\n']
RTYPES = ['', '', 'findutils-default', 'emacs', 'posix-basic', 'posix-extended', 'posix-egrep', 'egrep', 'grep',
          'awk', 'gnu-awk', 'posix-awk', 'ed', 'sed', 'posix-minimal-basic']
for _ in range(NRAND // 4):
    rx = ''.join(rnd.choice(RPIECES) for _ in range(rnd.randint(1, 7)))
    rt = rnd.choice(RTYPES)
    CASES.append(("find t names %s %s '%s'" % ('-regextype ' + rt if rt else '', rnd.choice(['-regex', '-iregex']),
                                              rx.replace("'", '')), {}))
GPIECES = ['*', '?', '[a-z]', '[!x]', '[^e]', '\\*', 'e', 'r', 'g', 'E', '[[:upper:]]', '[', ']', '-', '\\', '[]',
           '[!]', 'u', '/', '.', '[[:', ':]]', '[a-', '\\[', 's', 't', '**', '[[.e.]]', '[[=g=]]', '[e-g]']
for _ in range(NRAND // 4):
    gp = ''.join(rnd.choice(GPIECES) for _ in range(rnd.randint(1, 5)))
    CASES.append(("find t names %s '%s'" % (rnd.choice(['-name', '-iname', '-path', '-ipath', '-lname', '-ilname']),
                                           gp.replace("'", '')), {}))


MASKS = [(re.compile(rb'PID=\d+'), b'PID=N'), (re.compile(rb'\b\d{9,11}\b'), b'T'),
         (re.compile(rb'[A-Z][a-z]{2} [A-Z][a-z]{2} [ \d]\d \d\d:\d\d:\d\d \d{4}'), b'DATE')]


def run(cmd, which, kw):
    shutil.rmtree(O, ignore_errors=True)
    os.mkdir(O)
    if kw.get('delete'):
        make_del()
    if kw.get('atime'):
        reset_atimes()
    env = dict(base_env, PATH='%s/%s:/usr/bin:/bin' % (d, which))
    p = subprocess.run(['bash', '-c', cmd], cwd=F, env=env, input=kw.get('stdin', b''), capture_output=True, timeout=120)
    out, err = p.stdout, p.stderr
    files = []
    for nm in sorted(os.listdir(O)):
        fp = os.path.join(O, nm)
        files.append((nm, open(fp, 'rb').read() if os.path.isfile(fp) else b'<dir>'))
    if kw.get('mask'):
        for rx, rep in MASKS:
            out, err = rx.sub(rep, out), rx.sub(rep, err)
    if kw.get('nover'):
        out = b''
    return p.returncode, out, err, files


bad = 0
n = 0


def report(c, g, nb):
    global bad
    bad += 1
    if bad <= 40:
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, nb):
            if x == y:
                continue
            if isinstance(x, int) or isinstance(x, list):
                print('  %s gnu: %r nebox: %r' % (name, x, y))
                continue
            xl, yl = x.split(b'\n'), y.split(b'\n')
            k = 0
            while k < min(len(xl), len(yl)) and xl[k] == yl[k]:
                k += 1
            print('  %s differs at line %d of %d/%d' % (name, k + 1, len(xl), len(yl)))
            print('    gnu:   %r' % b'\n'.join(xl[k:k + 3])[:400])
            print('    nebox: %r' % b'\n'.join(yl[k:k + 3])[:400])


def run_tty(cmd, which, stdin_tty):
    env = dict(base_env, PATH='%s/%s:/usr/bin:/bin' % (d, which))
    m, s = pty.openpty()
    p = subprocess.Popen(['bash', '-c', cmd], cwd=F, env=env, stdin=s if stdin_tty else subprocess.DEVNULL, stdout=s,
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
    return p.returncode, out, err


TTY = ['find names', 'find names -printf "%p|%f|%h\\n"', 'find names -print0', 'find names -ls',
       'find names -fprint /dev/stdout', 'find t/sub -printf "%p" -printf "\\n"', 'find t -name x -maxdepth 1',
       'find t -warn -name a/b', 'find t -maxdepth 0 -d']
for c in TTY:
    for st in (False, True):
        if ONLY and ONLY not in c:
            continue
        n += 1
        g = run_tty(c, 'gnu', st)
        nb = run_tty(c, 'nbx', st)
        if g != nb:
            report('[tty%s] %s' % (' stdin' if st else '', c), g, nb)

for c, kw in CASES:
    if ONLY and ONLY not in c:
        continue
    n += 1
    g = run(c, 'gnu', kw)
    nb = run(c, 'nbx', kw)
    if g != nb:
        report(c, g, nb)
    elif ONLY:
        print('SAME:', c)
        print(g[1][:3000].decode('latin1'), g[2][:2000].decode('latin1'))
print('find_compare: %d cases (%d fixed, %d pty, %d random expressions, %d random formats/regexes/patterns)%s, '
      '%d mismatches' % (n, NFIXED, 2 * len(TTY), NEXPR, len(CASES) - NFIXED - NEXPR, ' (as root)' if ROOT else '', bad))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d, ignore_errors=True)
sys.exit(1 if bad else 0)
