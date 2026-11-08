#!/usr/bin/env python3
"""Side-by-side test of nebox env against GNU coreutils env.
Usage: tests/env_compare.py path/to/nebox
Covers -i/-, -u, NAME=VALUE, -0, -C, -v, -S split strings (quotes,
escapes, ${VAR}, comments, errors), the signal options (checked through
--list-signal-handling and the child's /proc/self/status) and exec
failures; stdout, stderr and exit status must match. The '_' variable bash
sets to the command path is dropped from printed environments. Known
difference: "=x" (an empty name) is refused by nelibc putenv (EINVAL, as
musl does) where glibc adds it."""
import os, subprocess, sys, tempfile, shutil

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='env-compare-')
env = dict(os.environ, LC_ALL='C', XV='x  y', EMPTYV='')
env.pop('UNSET_X', None)
open(os.path.join(d, 'args'), 'w').write('#!/bin/sh\nfor a; do printf "[%s]\\n" "$a"; done\n')
os.chmod(os.path.join(d, 'args'), 0o755)
os.mkdir(os.path.join(d, 'dir'))
open(os.path.join(d, 'noexec'), 'w').write('x\n')

CASES = [
    '@env -i', '@env -i A=B C=D', '@env -i A=B A=C', '@env -i A=', '@env - A=1', '@env -i - A=1',
    '@env -i -0 A=1 B=2', '@env --null -i A=1', '@env A=1 | grep ^A=', '@env | wc -l',
    '@env -u HOME | grep -c ^HOME=', '@env -u HOME -u PATH -i X=1', '@env -u a=b', "@env -u ''", '@env --unset=XV | grep -c XV',
    '@env -uXV | grep -c XV', '@env -i A=1 /usr/bin/printenv A', '@env -i A=1 -- printenv', '@env -- -i',
    '@env -i A=1 ./args x y', '@env -C / pwd', '@env -C /nonexist pwd', '@env -C /', '@env -C', '@env --chdir=dir pwd',
    '@env -0 true', '@env -i nonexistentcmd', '@env -i ./dir', '@env ./noexec', "@env -i 'echo hi'", "@env 'no such'",
    '@env -x', '@env --bogus', '@env -u', '@env --nul', '@env --i', '@env "-i echo"', "@env -i$'\\t'x", '@env --help=x',
    '@env -i A=1 > /dev/full; echo $?', '@env -i --block-signal=INT', '@env -i --list-signal-handling',
    # -S
    "@env -S'./args a b'", "@env -S'./args \"a b\" c'", "@env -S\"./args 'x\\ny'\"", "@env -S'./args \"x\\ny\"'",
    r"@env -S'./args a\_b'", r"@env -S'./args \"a\_b\"'", r"@env -S'./args a\cb c'", r"@env -S'./args \"a\cb\"'",
    r"@env -S'./args a #b c'", r"@env -S'./args a#b c'", r"@env -S'./args \#a'", r"@env -S'./args \$a \\ \'q'",
    r"@env -S'./args ${XV}'", r"@env -S'./args \"${XV}\"'", r"@env -S'./args a${UNSET_X}b'", r"@env -S'./args ${UNSET_X}'",
    r"@env -S'./args \"${UNSET_X}\"'", r"@env -S'./args $XV'", r"@env -S'./args ${1x}'", r"@env -S'./args ${XV'",
    r"@env -S'./args \q'", "@env -S'./args \\'", "@env -S'./args \"a'", "@env -S\"./args 'a\"", "@env -S''",
    "@env -S' ' ./args z", "@env -S'-i A=1 ./args'", "@env -i -S'A=1 B=2'", "@env -S'-u HOME' ./args q",
    "@env -S'-S./args\\_x' y", "@env -S'./args' a b", "@env -S \"./args '' \\\"\\\"\"", r"@env -S'./args \f\n\r\t\v' | od -c",
    "@env -S'./args \\'a\\\\b\\'\\''", r"@env -S'./args \"\\\"\" \"\\\\\"'", "@env -S'./args \\'\\'x'",
    "@env --split-string='./args 1 2'", "@env -S\"./args\t\tq\"", r"@env -S'./args ${EMPTYV}x'",
    # -v
    '@env -v -i A=1 ./args q', '@env -v -C / ./args', '@env -v -u X -i', '@env -v -u XV ./args', "@env -vS'A=1 ./args x'",
    r"@env -vS'./args ${XV} ${UNSET_X}'", "@env -v -S'./args \"a b\"' tail", '@env --debug -i', '@env -v -i nonexist',
    "@env -v -i -S''",
    # signals
    '@env --list-signal-handling true', '@env --ignore-signal=PIPE --list-signal-handling true',
    '@env --ignore-signal=INT,TERM --list-signal-handling true', '@env --ignore-signal= --list-signal-handling true',
    '@env --ignore-signal=FOO true', '@env --ignore-signal=0 true', '@env --ignore-signal=SIGHUP,hup,1 --list-signal-handling true',
    '@env --ignore-signal=9 true', '@env --default-signal=STOP true', '@env --ignore-signal=,,USR2, --list-signal-handling true',
    '@env --default-signal --list-signal-handling true', '@env --ignore-signal --list-signal-handling true',
    '@env --block-signal --list-signal-handling true', '@env --block-signal=INT,USR1 --list-signal-handling true',
    '@env --block-signal=INT --default-signal=INT --list-signal-handling true', '@env --block-signal --default-signal=TERM --list-signal-handling true',
    '@env --default-signal --block-signal=HUP --list-signal-handling true', '@env -v --ignore-signal=PIPE true',
    '@env -v --ignore-signal true', '@env -v --default-signal true', '@env -v --block-signal=RTMIN+1,RTMAX-2,64 --list-signal-handling true',
    '@env -v --block-signal true', '@env --block-signal=USR1 grep SigBlk /proc/self/status', '@env --ignore-signal=USR1 grep SigIgn /proc/self/status',
    '@env --default-signal=INT grep SigIgn /proc/self/status', '@env --ignore-signal=USR1 sh -c \'kill -USR1 $$; echo alive\'',
    '@env --block-signal=EXIT true', '@env --ignore-signal=137 --list-signal-handling true', '@env --block-signal=65 true',
    '@env --ignore-signal=CLD,IOT,POLL --list-signal-handling true', '@env --ignore-sig=QUIT --list-signal-handling true',
    '@env --block-signal=X,INT true', '@env --ignore-signal=INT,X true',
]


def run(cmd, which):
    c = cmd.replace('@env', (NEBOX + ' env') if which == 'nebox' else 'env')
    p = subprocess.run(['bash', '-c', c], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    out = p.stdout
    for sep in (b'\n', b'\0'):
        if (sep + b'_=') in (sep + out):
            out = sep.join(l for l in out.split(sep) if not l.startswith(b'_='))
    return p.returncode, out, err


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:400]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:400]))
print('env_compare: %d cases, %d mismatches' % (len(CASES), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
