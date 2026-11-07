#!/usr/bin/env python3
"""GNU option-parsing parity: long options, unique abbreviations, ambiguity
and argument errors, and options after operands, for the applets that parse
through util.getopt. Usage: tests/opts_compare.py path/to/nebox
Standard output and exit status must match GNU; standard error must match
on its first line (GNU adds "Try '... --help'", nebox has no --help)."""
import os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
env = dict(os.environ, LC_ALL='C', TZ='UTC')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='opts-compare-')
def w(name, data):
    with open(os.path.join(d, name), 'w') as f:
        f.write(data)
w('a', 'one\ntwo\n\n\nthree\tx\n')
w('b', 'b 2\na 1\nc 3\na 1\n')
w('n', '10\n9\n100\n-1\n')
w('t', 'a:b:c\nd:e:f\n')
APPS = ['cat', 'cut', 'wc', 'uniq', 'tee', 'mkdir', 'rm', 'cp', 'mv', 'ln', 'touch', 'sort', 'du', 'basename',
        'dirname', 'readlink', 'realpath', 'nl', 'paste', 'fold', 'split', 'shuf', 'tr', 'truncate', 'comm', 'id',
        'uname', 'mktemp', 'stat', 'install', 'rmdir', 'timeout', 'expand', 'unexpand', 'tty', 'pwd', 'grep',
        'chown', 'chgrp']
CASES = [
    'cat --number a', 'cat --number-nonblank --show-ends a', 'cat --squeeze-blank a', 'cat --show-all a', 'cat --num a',
    'cat --n a', 'cat --show a', 'cat --show-t a', 'cat a --number', 'cat a -n', 'cat -- a -n', 'cat --foo a',
    'cat --number=3 a', 'cat --show-tabs a', 'cat -A -- a',
    'cut --fields=2 --delimiter=: t', 'cut -f 2 t --delimiter :', 'cut --characters=1-2 t', 'cut --bytes 2 t',
    'cut --only-delimited -d: -f1 a', 'cut --f 1 t',
    'cut --fields', 'cut -d: t -f2',
    'wc --lines a', 'wc --words --bytes a', 'wc --chars a', 'wc --max-line-length a', 'wc a --lines', 'wc --l a',
    'wc --li a',
    'uniq --count b', 'sort b | uniq --repeated', 'sort b | uniq --unique', 'uniq --ignore-case b', 'sort b | uniq -c --c',
    'uniq b --count',
    'echo hi | tee --append o; cat o', 'echo hi | tee o --append; cat o',
    'mkdir --parents x/y; ls -R x', 'mkdir --mode=700 m; stat -c %a m', 'mkdir x --verbose', 'mkdir --verb x',
    'touch f; rm --force f g; ls', 'mkdir -p r/s; rm --recursive r; ls', 'touch f; rm f --verbose',     'cp --recursive a b2; ls', 'cp a c --verbose', 'cp --no-clobber a b; cat b',     'cp a mv1; mv --force mv1 mv2; ls', 'mv a --verbose a2', 'mv --no-clobber a b; cat a b',
    'ln --symbolic a s; readlink s', 'ln -s a s2 --verbose',     'touch --no-create zz; ls', 'touch --date=2020-01-01 a; stat -c %Y a', 'touch a --reference=b',
    'sort --reverse b', 'sort --numeric-sort n', 'sort -n --reverse n', 'sort n --numeric', 'sort --unique b',
    'sort --key=2 b', 'sort --field-separator=: --key=2 t', 'sort --output=o b; cat o', 'sort b --re',
    'sort --stable --key=1,1 b', 'sort --ignore-case b', 'sort --human-numeric-sort n', 'sort --version-sort n',
    'sort --check b', 'sort -c b', 'sort --bogus b', 'sort --key', 'sort --dictionary-order b',
    'sort --merge b n', 'sort -k1,1 b --ignore-leading-blanks', 'sort --zero-terminated b | od -c | head -2',
    'du --summarize .', 'du --all . | sort', 'du . --max-depth=0', 'du --bytes a',
    'basename --suffix=.c x/y.c', 'basename --multiple x/a y/b', 'basename x/a.c .c --zero | od -c', 'basename -a x y --suffix=x',
    'dirname --zero x/y | od -c', 'dirname x/y z/w',
    'ln -s a sl; readlink --canonicalize sl', 'readlink --no-newline sl; echo', 'readlink sl --verbose',
    'realpath --canonicalize-missing x/../y', 'realpath --quiet nofile; echo $?',
    'nl --body-numbering=a a', 'nl --number-separator=: a', 'nl --number-width=3 a', 'nl a --number-width 2',
    'paste --serial a', 'paste --delimiters=: a t', 'paste a t --serial',
    'fold --width=3 a', 'fold --bytes --width 2 a', 'fold a --spaces --width=4',
    'split --lines=2 a p; ls p*', 'split --bytes=4 a q; ls q*', 'split a r --lines 3; ls r*', 'split --suffix-length=3 -l 2 a s; ls s*',
    'shuf --echo a | sort', 'shuf --input-range=1-3 | sort', 'shuf --head-count=0 a', 'shuf -n 1 --repeat -e x',
    'echo hello | tr --delete l', 'echo hello | tr --squeeze-repeats l', 'echo hello | tr --complement --delete l',
    'echo abc | tr abc x --delete',
    'truncate --size=3 a; cat a', 'truncate a --size 0; wc -c a', 'truncate --no-create --size=1 zz; ls',
    'sort b > b1; sort t > t1; comm b1 t1',     'id --user >/dev/null; echo $?', 'id --group >/dev/null; echo $?', 'id -u --name >/dev/null; echo $?',
    'uname --kernel-name', 'uname --sysname', 'uname --machine', 'uname --kern', 'uname --k',
    'mktemp --dry-run >/dev/null; echo $?',     'stat --format=%s a', 'stat a --format %n', 'stat --terse a | cut -d" " -f2', 'stat --dereference --format=%F a',
    'install --directory dd; ls -d dd', 'install --mode=600 a i; stat -c %a i',
    'mkdir -p e/f; rmdir --parents e/f; ls', 'mkdir g; rmdir g --verbose',
    'timeout --signal=KILL 5 true; echo $?', 'timeout 5 true --verbose; echo $?', 'timeout --kill-after=1 5 true; echo $?',
    'timeout --preserve-status 5 false; echo $?',
    'expand --tabs=4 a', 'expand --initial a', 'expand a --tabs 2', 'unexpand --all a', 'unexpand --tabs=4 a',
    'tty --silent; echo $?', 'tty --quiet; echo $?',     'grep --ignore-case ONE a', 'grep --count o a', 'grep --line-number --invert-match o a', 'grep o a --line-number',
    'grep --regexp=one --regexp two a', 'grep --fixed-strings . a', 'grep --extended-regexp "o|x" a', 'grep -E "o|x" a -c',
    'grep --files-with-matches o a b', 'grep --files-without-match o a b', 'grep --max-count=1 o a', 'grep --only-matching o a',
    'grep --word-regexp one a', 'grep --line-regexp one a', 'grep --with-filename o a', 'grep --no-filename o a b',
    'grep --quiet o a; echo $?', 'grep --silent o a; echo $?', 'grep --context=1 two a', 'grep --after-context 1 two a',
    'grep --before-context=1 three a', 'grep -1 two a', 'grep two a -1', 'grep -A1 -2 two a', 'grep -12 two a', 'grep -1 -2 two a',
    'grep -5n two a', 'grep --color=never o a', 'grep --colour=auto o a', 'grep --color o a',     'grep --line-buffered o a', 'grep --null -l o a | od -c', 'grep --recursive one . | sort', 'grep --no-messages o nofile; echo $?',
    'grep --in o a', 'grep --i o a', 'grep --fi o a', 'grep --e o a',
    'grep --regexp', 'grep --exclude', 'grep --co o a', 'grep --null-data o a | od -c | head -1',
    'chown --recursive $(id -u) .; echo $?',
    'mkdir g; rmdir --verbose g', 'mkdir -p e/f/g; rmdir -pv e/f/g', 'mkdir -p h/i; touch h/x; rmdir -p h/i; echo $?',
    'mkdir -p h/i; touch h/x; rmdir --ignore-fail-on-non-empty -p h/i; echo $?', 'rmdir nodir', 'touch f; rmdir f',
    'ln -s a sl; rmdir sl/', 'mkdir -pv p/q/r', 'mkdir -v s t', 'mkdir s; mkdir s',
    'cat -vET a', 'cat -e a', 'cat -t a', 'printf "a\\r\\nb\\r" | cat -E', 'printf "a\\r" > cr; printf "\\nb" > nl; cat -E cr nl',
    'printf "x" > p1; cat -n p1 a', 'cat -s a a', 'cat -bn a', 'printf "\\001\\177\\200\\377\\t" | cat -v',
    'printf "\\001\\177\\200\\377\\t" | cat -A', 'cat a nofile a', 'cat -n - a < b', 'cat a > o; cat o >> o; echo $?',
    'fold -w 3 a', 'fold -3 a', 'fold -b3 a', 'fold -sw 4 a', 'fold -bsw 4 a', 'fold -w 0 a', 'fold -w x a', 'fold -12 a',
    'printf "ab\\bcd\\re\\tf\\n" | fold -w 3', 'printf "ab\\bcd\\re\\tf\\n" | fold -b -w 3',
    'wc -L a', 'printf "a\\tb\\rcdef\\fgh" | wc -L', 'printf "\\001\\002x" | wc -L -w',
    'sort --check=quiet b; echo $?', 'sort --check=silent b; echo $?', 'sort --check=diagnose-first b', 'sort --check=x b',
    'timeout --preserve-status 5 false; echo $?', 'timeout -p 5 true', 'basename -- -x', 'tr -- -a b',
]

def run(cmd, which):
    if which == 'gnu':
        c = cmd
    else:
        c = cmd
        import re
        for a in sorted(APPS, key=len, reverse=True):
            c = re.sub(r'(^|[|;(] *|\$\()%s\b' % a, lambda m: m.group(1) + NEBOX + ' ' + a, c)
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        shutil.rmtree(wd)
    os.mkdir(wd)
    for f in ('a', 'b', 'n', 't'):
        shutil.copy(os.path.join(d, f), wd)
    p = subprocess.run(['sh', '-c', c], cwd=wd, env=env, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(wd.encode(), b'WD').split(b'\n')[0]
    return p.returncode, p.stdout.replace(NEBOX.encode() + b' ', b'').replace(wd.encode(), b'WD'), err

bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
print('opts_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
