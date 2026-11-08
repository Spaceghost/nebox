#!/usr/bin/env python3
"""Side-by-side test of nebox du against GNU coreutils du.
Usage: tests/du_compare.py path/to/nebox
A fixture on tmpfs (nested directories, hard links, symlinks including a
loop, a sparse file, unreadable and unsearchable directories, fixed
timestamps) is shared by both; outputs on live /dev are rerun when they
differ, as entries there come and go. Output, diagnostics (minus "Try"
lines) and exit status must match."""
import os, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='du-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C', TZ='UTC')
for k in ('POSIXLY_CORRECT', 'DU_BLOCK_SIZE', 'BLOCK_SIZE', 'BLOCKSIZE', 'TIME_STYLE'):
    env.pop(k, None)
SETUP = r"""
mkdir -p t/a/b/c t/e t/f.d nr nx
head -c 5000 /dev/zero > t/f1; head -c 100000 /dev/zero > t/a/f2; printf x > t/a/b/f3; : > t/a/b/c/empty
ln t/f1 t/hl1; ln t/a/f2 t/e/hl2; ln -s f1 t/sl; ln -s ../.. t/a/b/loop; ln -s nowhere t/dangle
truncate -s 10M t/sparse; printf y > t/f.d/inner; printf z > 't/sp ace'; printf w > t/.hidden
head -c 3000 /dev/zero > nr/x; chmod 0 nr; printf q > nx/y; chmod 600 nx
ln -s t tl; printf 't\0t/a\0' > list0; printf 't\0\0t/e' > listz; printf 'f1\n*.d  \n\n  \n' > excl
touch -d '2020-01-02 03:04:05.5' t/f1 t/a/f2; touch -d '2019-05-06 07:08:09' t/a/b/f3 t/e
touch -h -d '2018-01-01' t/sl t/a/b/loop t/dangle; touch -d '2021-06-07' t/a/b/c t/a/b/c/empty t/f.d t/f.d/inner
touch -d '2017-01-01' t/sparse 't/sp ace' t/.hidden t/hl1 t/a/b t/a t/f.d
touch -d '2016-01-01' t
"""
subprocess.run(['bash', '-c', SETUP], cwd=d, check=True)
CASES = []
for o in ['', '-a', '-s', '-c', '-ac', '-b', '-k', '-m', '-h', '--si', '-B 1', '-B K', '-B 1KB', '-B 512', '-B 1000',
          '--apparent-size', '--apparent-size -a', '-l', '-al', '-S', '-aS', '-Sc', '-d 0', '-d 1', '-d 2', '-d 1 -a',
          '--max-depth=0', '-0', '-a0', '--inodes', '--inodes -a', '--inodes -S', '-x', '-L', '-La', '-D', '-H',
          '-P', '-L -P', '-P -L', '-t 4096', '-t -4096', '-t 1K', '-t -1K', '-t 100000', '-at 8K', '-t 0',
          '--time', '-a --time', '--time=atime', '--time=ctime -s', '--time=status -s', '--time=use -s',
          '--time --time-style=full-iso', '--time --time-style=iso', '--time --time-style=+%s.%N',
          '--time --time-style=long-iso -a', '--time --time-style=+%Y%n%H', '--exclude=f1', '--exclude=*.d',
          '--exclude=a', '--exclude=t/a', '--exclude="*a/b*"', '-a --exclude=f?', '--exclude=t', '-X excl -a',
          '-a --exclude=f\\1', '--exclude=[fe]* -a', '-c -s -h', '-sch --apparent-size', '-b -S -a']:
    CASES += ['@du %s t' % o, '@du %s t t/a' % o]
CASES += [
    '@du', '@du -s', '@du .', '@du -a .', '@du t/', '@du t//', '@du t///', '@du -a t/a/', '@du tl', '@du -D tl',
    '@du -H tl', '@du -L tl', '@du -a tl', '@du -Ds tl t', '@du t tl', '@du -L t tl', '@du t/sl', '@du -L t/sl',
    '@du t/dangle', '@du -L t/dangle', '@du -D t/dangle', '@du nonexistent', '@du t nonexistent t/a', '@du ""',
    '@du t "" t/a', '@du nr', '@du -a nr', '@du nx', '@du -a nx', '@du -s nr nx t', '@du t/f1 t/hl1', '@du -l t/f1 t/hl1',
    '@du t/hl1 t', '@du -a t/a t', '@du t t', '@du -l t t', '@du t/a t/a/b', '@du t/a/b t/a',
    '@du --files0-from=list0', '@du --files0-from=listz', '@du --files0-from=- < list0', '@du --files0-from=nofile',
    '@du --files0-from=list0 t', "printf '-\\0t' | @du --files0-from=-", "printf 't' | @du --files0-from=-",
    "printf '' | @du --files0-from=-", '@du --files0-from=t', '@du -X nofile t', '@du -X excl -X excl t',
    '@du -d x t', '@du -d -1 t', '@du -d 99999999999999999999 t', '@du -d 0x2 t', '@du -s -d 0 t', '@du -s -d 1 t',
    '@du -as t', '@du -t x t', '@du -t -0 t', '@du -t 1x t', '@du --threshold=99999999999999999999 t',
    '@du -t 0x1000 t', '@du -t 010 t', '@du -B x t', '@du --block-size=1x t', '@du -B 0 t',
    '@du --time=bogus t', '@du --time --time-style=bogus t', '@du --time-style=iso t', 'TIME_STYLE=iso @du --time t',
    'TIME_STYLE=locale @du --time t', 'TIME_STYLE=posix-iso @du --time t', 'TIME_STYLE=posix-posix-full-iso @du --time t',
    "TIME_STYLE=$'+%Y\\nX' @du --time t", 'TIME_STYLE=bogus @du --time t', 'DU_BLOCK_SIZE=1M @du t',
    'DU_BLOCK_SIZE=human @du t', 'BLOCK_SIZE=512 @du t', 'DU_BLOCK_SIZE=1K BLOCK_SIZE=1M @du -s t',
    'POSIXLY_CORRECT=1 @du -s t', 'POSIXLY_CORRECT=1 @du -sk t', "DU_BLOCK_SIZE=\\'1 @du -s t", '@du --inodes -b t',
    '@du --inodes --apparent-size -s t', '@du --bogus', '@du -q', '@du --ap t', '@du --max=1 t', '@du --sum t',
    '@du --no-d -s tl', '@du --deref-args tl', '@du --dereference-a tl', '@du t > /dev/full; echo $?',
    '@du -sx /dev', '@du -x /dev/shm/. -s', '@du -s /dev/null', '@du -a /dev/null t/f1',
]


def run(cmd, which):
    c = cmd.replace('@du', (NEBOX + ' du') if which == 'nebox' else 'du')
    p = subprocess.run(['bash', '-c', c], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


bad = 0
for c in CASES:
    for attempt in range(3 if '/dev' in c else 1):
        g = run(c, 'gnu')
        n = run(c, 'nebox')
        if g == n:
            break
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:700]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:700]))
print('du_compare: %d cases, %d mismatches' % (len(CASES), bad))
subprocess.run(['chmod', '-R', 'u+rwx', d])
subprocess.run(['rm', '-rf', d])
sys.exit(1 if bad else 0)
