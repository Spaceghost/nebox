#!/usr/bin/env python3
"""Side-by-side test of nebox kill against procps-ng 4.0.2 kill.
Usage: tests/kill_compare.py path/to/nebox
Every case runs in its own PID namespace (unshare -rpf, or unshare -pf as
root) under setsid, so signals to -1, 0, process groups or wrapped pids
reach only processes the case created: the namespace's sh (pid 1, which
ignores signals it has no handler for), a receiver (pid 2) that blocks
every signal and reports each one it takes with si_code, the sigqueue
value and the sender's pid, a sleeper in sh's process group (pid 3) and a
sleeper in its own session and group (pid 4). After the command the
sleepers are continued and their wait statuses printed. Cases: -l/-L and
--list/--table with numbers, names, exit statuses, optional arguments and
the next operand, -s/--signal, -SIGNAL and -NUMBER forms (RTMIN+N,
CLD/IO/IOT, EXIT/NULL, "--0", "-+9"), -q/--queue, negative digits taken as
process groups, pid 0 and -1, wrapped and unparsable pids, unknown options
and usage, --help, output to /dev/full. stdout, stderr, exit status and
what each process received must match; -V/--version prints nebox's line
and only its status is compared."""
import os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='kill-compare-', dir='/dev/shm')
os.chmod(d, 0o755)
env = dict(os.environ, LC_ALL='C')
ROOT = os.geteuid() == 0
NS = ['unshare', '-pf', '--kill-child'] if ROOT else ['unshare', '-rpf', '--kill-child']

RECV = r'''
import ctypes, signal, sys, time
libc = ctypes.CDLL(None, use_errno=True)
signal.pthread_sigmask(signal.SIG_BLOCK, signal.valid_signals())
out = sys.argv[2]
with open(sys.argv[1], 'w') as f:
    f.write('ready\n')
mask = (ctypes.c_ulong * 16)(*([0xffffffffffffffff] * 16))
info = ctypes.create_string_buffer(128)
class TS(ctypes.Structure):
    _fields_ = [('s', ctypes.c_long), ('ns', ctypes.c_long)]
got = []
end = time.monotonic() + 0.7
while True:
    left = end - time.monotonic()
    if left <= 0:
        break
    ts = TS(int(left), int((left - int(left)) * 1e9))
    r = libc.sigtimedwait(mask, info, ctypes.byref(ts))
    if r < 0:
        continue
    code = int.from_bytes(info.raw[8:12], 'little', signed=True)
    pid = int.from_bytes(info.raw[16:20], 'little', signed=True)
    val = int.from_bytes(info.raw[24:28], 'little', signed=True) if code == -1 else ''
    got.append('%d code=%d pid=%d %s' % (r, code, pid, val))
    with open(out, 'w') as f:
        f.write('\n'.join(got) + '\n')
'''
open(os.path.join(d, 'recv.py'), 'w').write(RECV)

# R receiver, A sleeper in sh's group, G sleeper leading its own group
SETUP = ('{ rm -f $D/r.out; mkfifo $D/fifo; python3 -I $D/../recv.py $D/fifo $D/r.out & R=$!; read x < $D/fifo; '
         'sleep 1 & A=$!; setsid sleep 1 & G=$!; until kill -0 -$G; do :; done; } 2>/dev/null; ')
# the shell's own job messages (a sleeper's "Killed") depend on timing
AFTER = ('; echo "rc=$?"; { kill -CONT $A $G; wait $A; echo "A=$?"; wait $G; echo "G=$?"; '
         'wait $R; echo "R=$?"; cat $D/r.out; } 2>/dev/null; echo "R pid=$R A pid=$A G pid=$G"')

CASES = []
LIST = ['', '-l', '-L', '--list', '--table', '-l 9', '-l 0', '-l 00', '-l 1', '-l 31', '-l 32', '-l 64', '-l 137',
        '-l 4294967305', '-l 99999999999999999999', '-l -1', '-l hup', '-l HUP', '-l sighup', '-l SIGHUP', '-l Sighup',
        '-l SIG9', '-l sig15', '-l SIG', '-l SIGx', '-l 9x', "-l ' 9'", '-l +9', "-l ''", '-l=9', '-l9', '-lHUP',
        '--list=9', '--list=KILL', '--list=', '--list 9', '--lis=TERM', '--l 9', '--li=ALRM', '-l -9', '-l -- 9',
        '9 -l', '-l 9 10', '-L 9', '-Ll', '-lL', '-lx', '-l RTMIN', '-l CLD', '-l IOT', '-l IO', '-l EXIT', '-l NULL',
        '-l STKFLT', '-l POLL', '-l 29', '-l 6', '-l 01', '-l 007', '-l 0x9', '-l 4294967296', '-l -s', '-l kill',
        '-l Kill', '-l sigKILL', '-l TERM extra', '-l "TE RM"', '-l rtmin+1', '-l 18446744073709551625',
        '-V', '--version', '-V 3', '-h', '--help', '--he', '-h 9', '9 -h', '-x', '-xyz', '--verbose', '--bogus',
        '--help=x', '--table=x', '--list=a=b', '-s', '--signal', '--sig', '--s', '-q', '--queue', '--q', '-q x 1',
        "-q '' 1", '-q 99999999999999999999 1', '-q 1x 1', "-q ' 5'", '-s KILL', '-9', '-KILL', '--', "-- ''",
        'x', "''", '1x', "' '", '99999999999999999999', '-- -99999999999999999999', '0x10', '-n 9 1', '-n',
        '-w', '-a', '-p 1', '--pid 1', '-L > /dev/full', '-l > /dev/full', '--help > /dev/full', '-l >&-',
        '-L >&-', '-Lx', '-hV', '-Vh', '-l -L', '-L -l', '-s KILL -L', '-q 5 -l', '-l -q', '-ls', '-l -s',
        '-USR1 -USR2', '-USR1 -l', '-RTMAX', '-SIGRTMAX', '-s', '--signal=', '-l "-"', '-l 128', '-l 255', '-l 256']
for a in LIST:
    CASES.append((a, False))
SIG = ['$A', '-9 $A', '-KILL $A', '-SIGKILL $A', '-sigkill $A', '-Kill $A', '-s USR1 $R', '-s usr1 $R',
       '-s SIGUSR1 $R', '--signal=USR2 $R', '--signal USR2 $R', '--sig=HUP $R', '-sUSR1 $R', '-s10 $R',
       '-n 9 $A', '-USR1 $R $A', '-s 0 $A', '-0 $A', '-EXIT $A', '-NULL $A', '-null $R', '-RTMIN $R',
       '-RTMIN+3 $R', '-rtmin+1 $R', '-SIGRTMIN+2 $R', '-RTMIN+30 $R', '-RTMIN+31 $R', '-RTMIN+93 $R',
       '-RTMIN+94 $R', '-RTMIN+-1 $R', '"-RTMIN+ 2" $R', '-93 $R', '-94 $R', '-64 $R', '-65 $R', '-s 94 $R',
       '-s 65 $R', '-s 64 $R', '-s BOGUS $R', "-s '' $R", '-s RTMAX $R', '-CLD $R', '-IO $R', '-IOT $R',
       '-POLL $R', '-STOP $A', '-CONT $A', '-TSTP $G', '-HUP $R', '-WINCH $R', '-STKFLT $R', '-PWR $R',
       '-- -$G', '-9 -- -$G', '-USR1 -$G', '-s USR1 -$G', '-s USR1 -- -$G', '-USR1 0', '-s USR1 0', '0',
       '-USR1 -1', '-s USR1 -- -1', '-- -1', '-q 42 -USR1 $R', '-q -5 -s USR2 $R', '-q 4294967298 -s USR1 $R',
       '--queue=7 -s RTMIN $R', '-q 1 -- -$G', '-q 1 -s 0 $A', '-q 1 $A', '-q 3 -q 4 -s USR1 $R', '-q7 -s USR1 $R',
       '-q 0x5 -s USR1 $R', '-q 2147483648 -s USR1 $R', '-q -2147483649 -s USR1 $R', '99999', '$A 99999 $G',
       '-s USR1 99999 $R', '4294967298', '-- -4294967294', '1', '-9 1', '-s USR1 1', '$A x $G', '-9 $A -9',
       '-9 -9 $A', '$A -l', '$A -L', '$A -h', '$A -s USR1', '-s USR1 -s USR2 $R', '-USR2 -s USR1 $R',
       '--0 $A', '-+9 $A', "'- 9' $A", '-s KILL $A $G', '$A $A', '-9 $A $A', '+$A', "' $A'", '" $A"',
       '-- $A', '-s HUP -- $R -$G', '-5x', '-1x', '-0x', '-3k', '-4z', '-9 -3', '-USR1 -2 $A', '-KILL -2',
       '-s USR1 -3', '-q 9 -USR1 -2', '-s 9 -- 3', '-l $A', '$R -s USR1 $A', '-STOP -- -$G', '-s 31 $R',
       '-SYS $R', '-s sys $R', '-15 $A -15', '-- 2', '2 -- -2', '-1 2', '-q 5 -RTMIN+1 2']
for a in SIG:
    CASES.append((a, True))
NOVERSION = {'-V', '--version', '-V 3', '-hV', '-Vh'}


def run(c, which):
    args, live = c
    prog = 'env kill' if which == 'ref' else NEBOX + ' kill'
    cmd = prog + ' ' + args
    script = (SETUP + cmd + AFTER) if live else (cmd + '; echo "rc=$?"')
    argv = NS + ['setsid', 'sh', '-c', 'D=$1; ' + script, 'sh', os.path.join(d, which + str(abs(hash(c))))]
    os.makedirs(argv[-1], exist_ok=True)
    p = subprocess.run(argv, cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


def check(c):
    r = run(c, 'ref')
    n = run(c, 'nebox')
    if c[0] in NOVERSION:
        r, n = (r[0], r[1].split(b'\n', 1)[-1], r[2]), (n[0], n[1].split(b'\n', 1)[-1], n[2])
    return c, r, n


bad = 0
with ThreadPoolExecutor(8) as ex:
    for c, r, n in ex.map(check, CASES):
        if r != n:
            bad += 1
            if bad <= 25:
                print('MISMATCH:', c)
                for name, x, y in zip(('status', 'stdout', 'stderr'), r, n):
                    if x != y:
                        print('  %s ref:   %r' % (name, x if isinstance(x, int) else x[:600]))
                        print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:600]))
print('kill_compare: %d cases%s, %d mismatches' % (len(CASES), ' (as root)' if ROOT else '', bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
