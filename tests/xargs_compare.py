#!/usr/bin/env python3
"""Side-by-side test of nebox xargs against GNU findutils 4.9.0 xargs.
Usage: tests/xargs_compare.py path/to/nebox [random-cases [seed]]
Both programs run as "xargs" from equal-length PATH directories on
/dev/shm, so the environment (and --show-limits) is the same. Fixed cases
cover input parsing (quotes, backslashes, blank lines, trailing blanks,
NUL bytes, -0, -d escapes, -E/-e), -n/-L/-l/-I/-i/-s/-x and their
warnings, -r, -t quoting, -a, --process-slot-var, -P (sorted output),
SIGUSR1/SIGUSR2, exit statuses 123-127 and the exit-time handling of
earlier failures, E2BIG retries through the __GNU_FINDUTILS_EXEC_ARG_*
test variables, --show-limits and a too-large environment under a small
stack limit, option errors, the standard-input offset left after exit,
and -p/-o through a pseudo-terminal; then random inputs with random
options. stdout, stderr and exit status must match ("Try 'xargs --help'"
lines are dropped). --help's bug-report paragraph and --version differ
by design and are not compared."""
import os, pty, random, select, shutil, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
NRAND = int(sys.argv[2]) if len(sys.argv) > 2 else 300
d = tempfile.mkdtemp(prefix='xargs-compare-', dir='/dev/shm')
for w, target in (('gnu', '/usr/bin/xargs'), ('nbx', NEBOX)):
    os.mkdir(os.path.join(d, w))
    os.symlink(target, os.path.join(d, w, 'xargs'))
base_env = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'HOME': d}


def w(name, data, mode=0o644):
    p = os.path.join(d, name)
    open(p, 'wb').write(data)
    os.chmod(p, mode)


w('args', b'#!/bin/sh\nfor a; do printf "[%s]" "$a"; done; echo\n', 0o755)
# pargs writes its line with one write, so parallel (-P) children cannot
# interleave partial lines (args does one printf per argument)
w('pargs', b'#!/bin/sh\nl=\nfor a; do l="$l[$a]"; done\nprintf "%s\\n" "$l"\n', 0o755)
w('noexec', b'#!/bin/sh\necho hi\n', 0o644)
w('words', b'alpha beta gamma\ndelta epsilon\n\nzeta eta theta iota\nkappa\n')
w('trail', b'a b \nc d\ne \n f\ng\n')
w('quotes', b'"a b" \'c d\' e\\ f "" \'\' g"h"i\n\'x\'"y"z\n')
w('unmatched1', b'a b\n"c d\ne\n')
w('unmatched2', b"a b 'c\n")
w('unmatched3', b"a b '")
w('unmatchedeof', b"a 'b c")
w('nul', b'a\0b c\0d\n')
w('nul0', b'a b\0c\nd\0\0e\0')
w('eof', b'a b\n_ c\nd\n')
w('eof2', b'a _ b\nc\n')
w('blank', b'\n\n   \n\t\n')
w('empty', b'')
w('crlf', b'a\r\nb\r\n')
w('vt', b'a\vb\fc\rd\n')
w('long', (b'x' * 200 + b' ') * 10 + b'\n')
w('many', b''.join(b'w%d ' % i for i in range(3000)) + b'\n')
w('stdin', b'one two\nthree\nstop\nfour five\n')
w('lines', b''.join(b'line %d\n' % i for i in range(1, 21)))
w('dq', b'a"b c"d e\\"f\n')
w('bs', b'a\\\nb c\\\\d\\ \ne\n')
w('hi', bytes(range(1, 256)) + b'\n')
w('special', b"x\\'y 'a b' \"it's\" '$HOME' 'a;b' 'c|d' '{' '}' '{}' '#c' 'd#' '~e' 'f~' '?' '*' '=' 'a=b' "
  b"'!' '[' ']' '^' '`' '(' ')' '<' '>' '&' '%' '@' ',' '.' '-' '+' ':' '_' 'a\tb' 'q\"q'\n")
w('special2', b"\"it's ok\" \"don't\" \"it's(x)\" \"a'b?\" \"'\" \"''\" \"a'#b\" \"#'\"\n")
os.mkdir(os.path.join(d, 'dir'))

CASES = [
    # default command, grouping
    'xargs < words', 'xargs echo < words', 'xargs ./args < words', 'xargs ./args x y < words', 'xargs < empty',
    'xargs -r < empty', 'xargs -r ./args < blank', 'xargs ./args < blank', 'xargs --no-run-if-empty echo x < empty',
    'xargs echo x < empty', 'echo | xargs ./args', 'printf "a" | xargs ./args', 'xargs ./args < crlf', 'xargs ./args < vt',
    # quoting and parsing
    'xargs ./args < quotes', 'xargs ./args < dq', 'xargs ./args < bs', 'xargs ./args < unmatched1', 'xargs ./args < unmatched2',
    'xargs ./args < unmatched3', 'xargs ./args < unmatchedeof', 'xargs -n1 ./args < unmatched1', 'xargs -x -n1 ./args < unmatched1',
    'xargs -L1 ./args < unmatched1', 'xargs ./args < nul', 'xargs -n1 ./args < nul', 'xargs -I{} ./args {} < nul',
    'xargs ./args < hi', 'xargs -0 ./args < hi', "printf 'a\\\\' | xargs ./args", "printf \"''\" | xargs ./args",
    "printf \"'' x\\n\" | xargs ./args", "printf \"x ''\" | xargs ./args", "printf \"x ''\\n\" | xargs ./args",
    "printf '\"\"\\n\"\"\\n' | xargs ./args", "printf \"'\\n\" | xargs ./args", "printf \"'\" | xargs ./args",
    'printf "\\"a" | xargs ./args', "printf 'a\\\\\\nb\\n' | xargs -L1 ./args",
    # -0 and -d
    'xargs -0 ./args < nul0', 'xargs --null -n2 ./args < nul0', 'xargs -0 ./args < words', 'xargs -0 -r ./args < empty',
    'printf "a\\0" | xargs -0 ./args', 'printf "\\0" | xargs -0 ./args', 'printf "\\0\\0" | xargs -0 ./args',
    'xargs -d x ./args < words', "xargs -d '\\n' ./args < words", "xargs -d ' ' ./args < words", "xargs -d '\\t' ./args < vt",
    "xargs -d '\\x61' ./args < words", "xargs -d '\\141' ./args < words", "xargs -d '\\0' ./args < nul0",
    "xargs -d '\\x' ./args < nul0", "xargs -d '\\x0x65' ./args < words", "xargs -d '\\x 65' ./args < words",
    "xargs -d '\\x+65' ./args < words", "xargs -d '\\x-1' ./args < words", "xargs -d '\\x100' ./args < words",
    "xargs -d '\\400' ./args < words", "xargs -d '\\377' ./args < hi", "xargs -d '\\xff' ./args < hi",
    "xargs -d \"$(printf '\\351')\" ./args < hi", "xargs -d '\\xffffffffffffffffffffff' ./args < words",
    "xargs -d '\\8' ./args < words", "xargs -d '\\xg' ./args < words", "xargs -d '\\q' ./args < words",
    "xargs -d '\\abc' ./args < hi", "xargs -d '\\\\' ./args < bs", "xargs -d ab ./args < words", "xargs -d '' ./args < words",
    "xargs -d '\\' ./args < words", "xargs -d '\\a' ./args < hi", "xargs -d '\\b' ./args < hi", "xargs -d '\\f' ./args < vt",
    "xargs -d '\\r' ./args < vt", "xargs -d '\\v' ./args < vt", "xargs -d '\\n' -E e ./args < words",
    "xargs --delimiter=e ./args < words", "xargs -d x -0 ./args < nul0", "xargs -0 -d e ./args < words",
    # -E / -e
    'xargs -E _ ./args < eof', 'xargs -E _ ./args < eof2', 'xargs -e_ ./args < eof', 'xargs --eof=_ ./args < eof',
    'xargs --eof ./args < eof', 'xargs --eof= ./args < eof', 'xargs -e ./args < eof', "xargs -E '' ./args < eof",
    'xargs -E _ -e ./args < eof', 'xargs -E c ./args < words', 'xargs -E alpha ./args < words', 'xargs -E kappa ./args < words',
    'xargs -E _ -0 ./args < eof', 'xargs -E _ -d x ./args < eof', 'xargs -E _ -I{} ./args {} < eof',
    'xargs -E _ -L1 ./args < eof', "printf '\"_\" a\\n' | xargs -E _ ./args", "printf 'a\\n_' | xargs -E _ ./args",
    'xargs -E stop ./args < stdin', 'xargs -E _ -n1 ./args < eof2',
    # -n
    'xargs -n1 ./args < words', 'xargs -n 2 ./args < words', 'xargs --max-args=3 ./args < words', 'xargs -n 100 ./args < words',
    'xargs -n0 ./args < words', 'xargs -n -1 ./args < words', 'xargs -n x ./args < words', "xargs -n '' ./args < words",
    "xargs -n ' 2' ./args < words", "xargs -n '2 ' ./args < words", 'xargs -n +2 ./args < words', 'xargs -n 0x2 ./args < words',
    'xargs -n 99999999999999999999 ./args < words', 'xargs -n -99999999999999999999 ./args < words', 'xargs -n2 -x ./args < words',
    'xargs -n 3 -s 30 ./args < words', 'xargs -n 3 -s 30 -x ./args < words', 'xargs -n 1 -r ./args < empty',
    # -L / -l
    'xargs -L1 ./args < words', 'xargs -L 2 ./args < words', 'xargs -L1 ./args < trail', 'xargs -L2 ./args < trail',
    'xargs --max-lines=2 ./args < trail', 'xargs --max-lines ./args < trail', 'xargs -l ./args < trail', 'xargs -l2 ./args < trail',
    'xargs -l0 ./args < words', 'xargs -L0 ./args < words', 'xargs -L x ./args < words', 'xargs -L -3 ./args < words',
    'xargs -L1 -0 ./args < nul0', 'xargs -L2 -d e ./args < words', 'xargs -L1 ./args < blank', 'xargs -L1 ./args < bs',
    'xargs -L1 ./args < quotes', 'xargs -L 3 -s 25 ./args < words', 'xargs -L 3 -s 25 -x ./args < words', 'xargs -L1 ./args < lines',
    'xargs -L 7 ./args < lines', "printf 'a \\\\\\n' | xargs -L1 ./args", "printf 'a\\\\ \\nb\\nc\\n' | xargs -L1 ./args",
    "printf \"'a '\\nb\\n\" | xargs -L1 ./args", "printf 'a\\t\\nb\\nc\\n' | xargs -L1 ./args",
    # mutual exclusion warnings
    'xargs -n2 -L1 ./args < words', 'xargs -L1 -n2 ./args < words', 'xargs -n2 -l ./args < words', 'xargs -l -n2 ./args < words',
    'xargs -n2 -I{} ./args {} < words', 'xargs -I{} -n2 ./args {} < words', 'xargs -I{} -n1 ./args {} < words',
    'xargs -I{} -n 1 -n 2 ./args {} < words', 'xargs -L1 -I{} ./args {} < words', 'xargs -I{} -L1 ./args {} < words',
    'xargs -l -I{} ./args {} < words', 'xargs -I{} -l ./args {} < words', 'xargs -n2 -L1 -I{} ./args {} < words',
    'xargs -i -l2 -n3 ./args {} < words', 'xargs -n3 -l2 -i ./args {} < words', 'xargs -L 2 -L 3 ./args < lines',
    # -I / -i
    'xargs -I{} ./args {} < words', 'xargs -I {} ./args x{}y {}{} < words', 'xargs -i ./args [{}] < words',
    'xargs -iX ./args X < words', 'xargs --replace ./args {} < words', 'xargs --replace=@ ./args @@ < words',
    'xargs -I{} ./args < words', 'xargs -I{} < words', 'xargs -I{} ./args {} < trail', 'xargs -I{} ./args {} < quotes',
    'xargs -I{} ./args {} < blank', 'xargs -I{} -0 ./args {} < nul0', 'xargs -I{} -d e ./args {} < words',
    'xargs -I ab ./args xaby ab < words', 'xargs -I{} {} < words', 'xargs -I{} -r ./args {} < empty',
    'xargs -I{} ./args {} < unmatched1', 'xargs -I{} -s 20 ./args {} < words', 'xargs -I{} -s 30 ./args {} {} < words',
    'xargs -I{} -s 40 ./args {}{}{}{}{} < words', 'xargs -I{} -s 12 ./args {} < words', 'xargs -I{} -s 9 ./args {} < words',
    'xargs -I{} ./args {} < long', 'xargs -I{} -x ./args {} < words', 'xargs -I abc ./args ab abc < words',
    "printf 'a{}b\\n' | xargs -I{} ./args {}", "printf '  lead\\ttab  \\n' | xargs -I{} ./args '<{}>'",
    # -s / -x
    'xargs -s 20 ./args < words', 'xargs -s 30 ./args < words', 'xargs -s 7 ./args < words', 'xargs -s 8 ./args < words',
    'xargs -s 1 ./args < words', 'xargs -s 0 ./args < words', 'xargs -s -5 ./args < words', 'xargs -s x ./args < words',
    'xargs -s 20 -x ./args < words', 'xargs -s 15 -x -n 2 ./args < words', 'xargs -s 99999999 ./args < words',
    'xargs -s 99999999999999999999 ./args < words', 'xargs -s 4096 ./args < long', 'xargs -s 300 ./args < long',
    'xargs -s 200 ./args < long', 'xargs -s 220 -x -n 1 ./args < long', 'xargs -s 50 -r ./args < empty',
    'xargs --max-chars=25 ./args < words', 'xargs -x ./args < words', 'xargs -s 20 -I{} ./args {} < empty',
    'xargs ./args < many | wc', 'xargs -s 5000 ./args < many | wc', 'xargs -n 7 -s 100 ./args < many | tail -3',
    # -t / -p printing (no prompt)
    'xargs -t ./args < words', 'xargs -t ./args < special', 'xargs -t ./args < special2', 'xargs -t ./args < hi',
    'xargs -t -0 ./args < nul0', "xargs -t ./args '' 'a b' \"it's\" < empty", 'xargs --verbose -n2 echo < words',
    'xargs -t -I{} ./args {} < words', "xargs -t '#x' < empty", "xargs -t ./args '~' '{' '}' '{}' 'a~' < empty",
    "xargs -t ./args \"$(printf 'a\\tb\\nc')\" \"$(printf '\\001\\177\\200')\" < empty",
    "xargs -t ./args \"$(printf 'x\\ny')\\\"\" \"$(printf '\\n')\" \"'$(printf '\\n')'\" < empty",
    "xargs -t ./args \"a'b$(printf '\\t')\" \"$(printf '\\t')'x$(printf '\\t')\" \"$(printf '\\001')'\" < empty",
    'xargs -t ./args < words 2>/dev/null', 'xargs -t ./args < words 2>&-; echo $?',
    # -a
    'xargs -a words ./args', 'xargs --arg-file=words -n2 ./args', 'xargs -a nonexistent ./args', 'xargs -a dir ./args',
    'xargs -a words ./args < quotes', 'xargs -a words sh -c "cat; echo \\$#" s < quotes', 'xargs -a - ./args < words',
    'xargs -a "a\'b" ./args', 'xargs -a empty -r ./args', 'xargs -a words -a quotes ./args',
    'xargs -o ./args < words', 'xargs -o -I{} ./args {} < words', 'xargs -a words -o ./args',
    'xargs sh -c "cat; echo end" < words', 'xargs -n1 sh -c "test -t 0 || read x || echo eof" < words',
    # exit statuses
    'xargs false < words', 'xargs true < words', 'xargs nosuchcommand < words', 'xargs ./noexec < words', 'xargs ./dir < words',
    "xargs '' < words", 'xargs /nonexistent/x < words', 'xargs -n1 sh -c "exit 255" < words',
    'xargs -n1 sh -c "exit 1" < words', 'xargs -n1 sh -c "exit 125" < words', 'xargs -n1 sh -c "exit 126" < words',
    'xargs -n1 sh -c "exit 127" < words', 'xargs -n1 sh -c "exit 128" < words', 'xargs -n1 sh -c "exit 254" < words',
    'xargs -n1 sh -c \'kill -TERM $$\' < words', 'xargs -n1 sh -c \'kill -KILL $$\' < words', 'xargs -n1 sh -c \'kill -INT $$\' < words',
    "printf '1\\n255\\n' | xargs -n1 sh -c 'exit $0'", "printf '0\\n255\\n1\\n' | xargs -n1 sh -c 'exit $0'",
    "printf '3\\n0\\n' | xargs -n1 sh -c 'exit $0'", "printf '1\\nx\\n' | xargs -n1 sh -c 'test $0 = x && kill $$; exit $0'",
    "printf 'true\\nnosuch\\ntrue\\n' | xargs -I{} {}", "printf 'false\\nnosuch\\n' | xargs -I{} {}",
    "printf 'false\\n./noexec\\n' | xargs -I{} {}", "printf 'false\\na\\n\"b\\n' | xargs -n1 sh -c 'exit 1'",
    "printf '1\\n2\\n' | xargs -n1 -P2 sh -c 'sleep 0.$0; exit 255'; echo $?",
    "printf '1\\n2\\n3\\n' | xargs -n1 -P3 sh -c 'sleep 0.$0; exit $0'",
    # -P, slots, signals (order-independent output)
    'xargs -P 3 -n1 ./pargs < words | sort', 'xargs -P 0 -n2 ./pargs < words | sort', 'xargs -P2 -L1 ./pargs < trail | sort',
    'xargs -P -1 ./args < words', 'xargs -P x ./args < words', 'xargs -P 2147483648 ./args < words',
    'xargs -P 2147483647 -n1 ./pargs < words | sort', 'xargs --max-procs=4 -n1 ./pargs < words | sort',
    'xargs -n1 -P1 --process-slot-var=SLOT sh -c \'echo $SLOT $0\' < words',
    'xargs -n1 -P3 --process-slot-var=SLOT sh -c \'echo $SLOT\' < words | sort | uniq -c | wc -l',
    'SLOT=9 xargs -n1 --process-slot-var=SLOT sh -c \'echo ${SLOT-unset}\' < words',
    'xargs --process-slot-var=A=B ./args < words', "xargs --process-slot-var= ./args < words",
    'xargs --process-slot ./args < words', 'xargs --process-slot-v=Q sh -c "echo \\$Q" < words',
    "xargs -n1 -P1 sh -c 'kill -USR1 $PPID; echo $0' < words | sort",
    "xargs -n1 -P2 sh -c 'kill -USR2 $PPID; echo $0' < words | sort",
    "xargs -n2 -P0 sh -c 'kill -USR2 $PPID; kill -USR1 $PPID; echo $0' < words | sort",
    # E2BIG retries via the test variables
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=4 xargs ./args < words', '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=3 xargs -t ./args < lines',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=2 xargs ./args x < words', '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=1 xargs ./args < words',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=0 xargs ./args < words', '__GNU_FINDUTILS_EXEC_ARG_LENGTH_LIMIT=20 xargs ./args < words',
    '__GNU_FINDUTILS_EXEC_ARG_LENGTH_LIMIT=40 xargs -n 5 ./args < lines', '__GNU_FINDUTILS_EXEC_ARG_LENGTH_LIMIT=5 xargs ./args < words',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=5 xargs ./args < many | wc', '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=x xargs ./args < words',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=-1 xargs ./args < words', '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=" 7z" xargs ./args < words',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=99999999999999999999999 xargs ./args < words',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT= xargs ./args < words', '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=2 xargs -I{} ./args {} < words',
    '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=3 xargs -P2 -n4 ./pargs < lines | sort',
    # limits and the environment
    'xargs --show-limits < empty', 'xargs --show-limits -s 1000 true < empty', 'xargs --show-limits -s 99999999 true < empty',
    'xargs -r --show-limits < empty', 'FOO=$(printf "%01000d" 0) xargs --show-limits < empty',
    'ulimit -s 1024; xargs --show-limits < empty', 'ulimit -s 65536; xargs --show-limits < empty',
    'ulimit -s unlimited; xargs --show-limits < empty', 'ulimit -s 256; xargs --show-limits < empty',
    'ulimit -s 256; export X=$(printf "%0120000d" 0); xargs --show-limits ./args < words',
    'ulimit -s 256; export X=$(printf "%0120000d" 0); xargs ./args < long | wc',
    'ulimit -s 256; export X=$(printf "%0125000d" 0); xargs -s 5000 ./args < words',
    'ulimit -s 256; export X=$(printf "%065000d" 0) Y=$(printf "%064000d" 0); xargs ./args < words',
    'ulimit -s 256; export X=$(printf "%065000d" 0) Y=$(printf "%064000d" 0); xargs -s 100 ./args < words',
    'ulimit -s 256; export X=$(printf "%065000d" 0) Y=$(printf "%064000d" 0); xargs -n1 -s 100 -E x ./args < words',
    # options and usage errors
    'xargs -z', 'xargs --bogus', 'xargs --max', 'xargs --max-a=1 ./args < words', 'xargs --re ./args {} < words',
    'xargs -n', 'xargs -I', 'xargs -s', 'xargs -E', 'xargs -d', 'xargs -a', 'xargs -P', 'xargs --null=x',
    'xargs --arg-file', 'xargs --show-limits=1', 'xargs -h', 'xargs -v', 'xargs --help | head -3', 'xargs --help > /dev/full',
    'xargs -- ./args -n1 < words', 'xargs ./args -n1 < words', 'xargs -rtn1 ./args < words', 'xargs -n1t ./args < words',
    'xargs -0n1 ./args < nul0', 'xargs -l1t ./args < words', 'xargs -i{}x ./args {}x < words', 'xargs -e_x ./args < eof',
    # the standard-input offset GNU leaves behind
    '(xargs -E stop ./args; cat) < stdin', '(xargs -n1 -E three ./args; echo ---; cat) < stdin',
    '(xargs nosuchcommand; cat) < stdin', '(xargs -n1 sh -c "exit 255"; cat) < stdin', '(xargs -a words ./args; cat) < stdin',
    '(xargs -E stop ./args; cat) < lines', 'cat stdin | (xargs -E stop ./args; cat)',
    '(head -c 7 >/dev/null; xargs -E stop ./args; cat) < stdin',
    '(xargs -s 10 ./args; echo $?; cat) < long', '(printf "a\\n\'b\\nc\\n" | (xargs ./args; cat))',
    # input errors
    'xargs ./args < dir', 'xargs ./args <&-', 'xargs -a words ./args <&-', 'xargs -0 ./args < dir',
    'xargs -I{} ./args {} < dir', 'xargs -r ./args < dir',
]

PTY_CASES = [
    # (command, tty input, stdin file)
    ('xargs -p ./args', b'y\nn\ny\n', 'words'),
    ('xargs -p -n1 ./args', b'y\nn\nyes\nN\nY\nx\ny\nn\nyy\n', 'words'),
    ('xargs -p ./args', b'n\nn\n', 'words'),
    ('xargs -p ./args', b'n\n', 'empty'),
    ('xargs -p -r ./args', b'n\n', 'empty'),
    ('xargs -p -n2 ./args', b'y\n\x04', 'words'),
    ('xargs -p ./args', b'\x04', 'words'),
    ('xargs --interactive -I{} ./args {}', b'y\ny\nn\ny\ny\n', 'words'),
    ('xargs -p -t -L1 ./args', b'Y\ny\ny\ny\n', 'words'),
    ('xargs -p -n1 sh -c "exit 1"', b'y\nn\nn\nn\nn\nn\nn\nn\nn\nn\nn\nn\nn\n', 'words'),
    ('xargs -o sh -c \'test -t 0 && echo tty; echo $#\'', b'', 'words'),
    ('xargs -o -n2 sh -c \'read x; echo got $x\'', b'one\ntwo\nthree\nfour\nfive\nsix\n', 'words'),
    ('xargs --open-tty -a words sh -c \'read x; echo got $x\'', b'hello\n', 'empty'),
    ('xargs --show-limits true', b'', 'words'),
]


def norm_err(err):
    return b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))


def run(cmd, which):
    env = dict(base_env, PATH=os.path.join(d, which) + ':' + base_env['PATH'])
    p = subprocess.run(['bash', '-c', cmd], cwd=d, env=env, capture_output=True, timeout=60,
                       stdin=subprocess.DEVNULL, start_new_session=True)
    return p.returncode, p.stdout, norm_err(p.stderr)


def run_pty(cmd, answers, infile, which):
    env = dict(base_env, PATH=os.path.join(d, which) + ':' + base_env['PATH'])
    outp, errp = os.path.join(d, 'pty.out'), os.path.join(d, 'pty.err')
    pid, master = pty.fork()
    if pid == 0:
        try:
            os.chdir(d)
            fd = os.open(infile, os.O_RDONLY); os.dup2(fd, 0)
            fd = os.open(outp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC); os.dup2(fd, 1)
            fd = os.open(errp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC); os.dup2(fd, 2)
            os.execve('/bin/bash', ['bash', '-c', cmd], env)
        finally:
            os._exit(99)
    # a trailing end-of-file keystroke, so that running out of answers ends
    # the prompts with GNU's read error instead of waiting
    os.write(master, answers if answers.endswith(b'\x04') else answers + b'\x04')
    deadline = time.time() + 30
    status = None
    while time.time() < deadline:
        r, _, _ = select.select([master], [], [], 0.05)
        if r:
            try:
                os.read(master, 4096)
            except OSError:
                pass
        wp, st = os.waitpid(pid, os.WNOHANG)
        if wp:
            status = st
            break
    if status is None:
        os.kill(pid, 9)
        os.waitpid(pid, 0)
        status = -1
        print('pty case timed out (%s): %s' % (which, cmd))
    os.close(master)
    rc = os.waitstatus_to_exitcode(status) if status != -1 else -1
    return rc, open(outp, 'rb').read(), norm_err(open(errp, 'rb').read())


def report(name, g, n):
    print('MISMATCH:', name)
    for label, x, y in zip(('status', 'stdout', 'stderr'), g, n):
        if x != y:
            print('  %s gnu:   %r' % (label, x if isinstance(x, int) else x[:600]))
            print('  %s nebox: %r' % (label, y if isinstance(y, int) else y[:600]))


bad = 0
total = 0
for c in CASES:
    total += 1
    g, n = run(c, 'gnu'), run(c, 'nbx')
    if g != n:
        bad += 1
        if bad <= 30:
            report(c, g, n)

for c, ans, inf in PTY_CASES:
    total += 1
    g, n = run_pty(c, ans, inf, 'gnu'), run_pty(c, ans, inf, 'nbx')
    if g != n:
        bad += 1
        if bad <= 30:
            report('[pty] %s <<< %r' % (c, ans), g, n)

# random inputs and options
rnd = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 4090)
TOKENS = ['a', 'bc', 'def', '_', 'x y', "'q r'", '"s t"', '\\ ', 'u\\v', "''", '""', '{}', 'a{}b', 'w\\\nz',
          "it\\'s", '"', "'", '\0', 'longword' * 6, 'é', '#', '~h', '$v', '*', 'k=v']
SEPS = [' ', ' ', ' ', '\t', '\n', '\n', ' \n', '\n\n', '  ', '\t\n', 'x', '\r']


def rand_input():
    out = []
    for _ in range(rnd.randint(0, 30)):
        t = rnd.choice(TOKENS)
        if t in ('"', "'", '\0') and rnd.random() < 0.7:
            t = 'm'
        out.append(t)
        out.append(rnd.choice(SEPS))
    if out and rnd.random() < 0.3:
        out.pop()
    return ''.join(out).encode('latin-1')


def rand_opts():
    opts = []
    env = ''
    cmd_i = False
    for _ in range(rnd.randint(0, 5)):
        k = rnd.randint(0, 22)
        if k == 0: opts.append('-0')
        elif k == 1: opts.append(rnd.choice(["-d x", "-d '\\n'", "-d ' '", "-d '\\t'", '-d e']))
        elif k == 2: opts.append('-n %d' % rnd.randint(1, 5))
        elif k == 3: opts.append(rnd.choice(['-L %d' % rnd.randint(1, 3), '-l', '-l2', '--max-lines=2']))
        elif k == 4: opts.append(rnd.choice(['-I{}', '-i', '-I x'])); cmd_i = True
        elif k == 5: opts.append('-s %d' % rnd.choice([1, 10, 15, 20, 25, 30, 40, 60, 100, 4096]))
        elif k == 6: opts.append('-x')
        elif k == 7: opts.append('-r')
        elif k == 8: opts.append('-t')
        elif k == 9: opts.append(rnd.choice(['-E _', '-e_', '-e', '-E bc', "'--eof=x y'"]))
        elif k == 10: opts.append('-P 1')
        elif k == 11: env = '__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT=%d ' % rnd.randint(1, 6)
        elif k == 12: env = '__GNU_FINDUTILS_EXEC_ARG_LENGTH_LIMIT=%d ' % rnd.randint(1, 40)
        elif k == 13: opts.append('-n %d' % rnd.randint(1, 3))
        elif k == 14: opts.append('-s %d' % rnd.randint(1, 50))
        elif k == 15: opts.append('-L 1')
        elif k == 16: opts.append('--max-args=%d' % rnd.randint(1, 4))
    cmds = ['./args', './args p', 'echo', "sh -c 'printf \"(%s)\" \"$@\"; echo; [ $# -lt 3 ]' s",
            "sh -c 'echo $#; exit $(($# % 4 == 3 ? 255 : 0))' s"]
    cmd = rnd.choice(cmds)
    if cmd_i or rnd.random() < 0.1:
        cmd = rnd.choice(['./args {} a{}b', './args x {}{}', './args {}', './args x'])
    return env + 'xargs ' + ' '.join(opts) + ' ' + cmd


for i in range(NRAND):
    total += 1
    w('rin', rand_input())
    c = rand_opts() + ' < rin'
    g, n = run(c, 'gnu'), run(c, 'nbx')
    if g != n:
        bad += 1
        if bad <= 30:
            report('%s   input=%r' % (c, open(os.path.join(d, 'rin'), 'rb').read()), g, n)

print('xargs_compare: %d cases (%d fixed, %d pty, %d random), %d mismatches' %
      (total, len(CASES), len(PTY_CASES), NRAND, bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
