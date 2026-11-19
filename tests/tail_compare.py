#!/usr/bin/env python3
"""Side-by-side test of nebox tail against GNU tail.
Usage: tests/tail_compare.py path/to/nebox [random-cases] [seed]
Random -n/-c counts (with +N, suffixes, the obsolete [+-]N[bcl] form) over
files and pipes, then scripted follow scenarios: appends, truncation,
--pid exit, -F with a rotated or removed file, a reader that goes away.
Polling comparisons explicitly disable inotify. Separate event checks use a long polling interval.
Output, diagnostics (minus "Try --help") and exit status must match."""
import os, random, select, shutil, subprocess, sys, tempfile, time

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='tail-compare-')
frng = random.Random(4)


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


def lines(n, eol=b'\n', final=True, width=30):
    out = eol.join(b'line %d %s' % (i, b'x' * frng.randrange(width)) for i in range(n))
    return out + (eol if final and n else b'')


w('small', lines(15))
w('nonl', lines(15, final=False))
w('big', lines(5000, width=80))
w('bignonl', lines(5000, final=False, width=80))
w('z', lines(20, eol=b'\0'))
w('empty', b'')
w('one', b'x')
w('blank', b'\n\n\n')
os.mkdir(os.path.join(d, 'adir'))
FILES = ['small', 'nonl', 'big', 'bignonl', 'z', 'empty', 'one', 'blank']

FIXED = ['@tail small', '@tail -n 3 small', '@tail -3 small', '@tail +3 small', '@tail -c 10 small', '@tail -n +3 small',
         '@tail -c +5 small', '@tail -n 0 small', '@tail -n +0 small', '@tail small nonl', '@tail -q small nonl', '@tail -v small',
         '@tail -n 2 small nofile nonl', '@tail adir', '@tail -n 2 -z z | od -c | tail -3', '@tail -5c small', '@tail -2l small',
         '@tail -c small', '@tail -b small | wc -c', '@tail -3b big | wc -c', '@tail -x small', '@tail -n x small',
         '@tail -n 99999999999999999999999 small', '@tail small -5', '@tail -n 1 -- -n', '@tail --lines=2 small',
         '@tail --bytes=3 small', '@tail -n 2 -- small', '@tail -5 -- small', '@tail -5 small nonl', '@tail +5 small nonl',
         '@tail -c 1k big | wc -c', '@tail -c 2b big | wc -c', '@tail -n -3 small', '@tail -n --3 small',
         '@tail --retry small', '@tail --pid=1 small', '@tail -s 0.1 small', '@tail -s x small', '@tail --follow=foo small',
         '@tail --follow= small', '@tail -F - < small', '@tail ---presume-input-pipe -n 2 small', 'timeout 1 @tail -5f small; echo $?',
         'cat big | @tail -n 3', 'cat bignonl | @tail -n 2', 'cat big | @tail -c 100', 'cat small | @tail -n +14',
         'cat small | @tail -c +200', '{ head -c 5 > /dev/null; @tail -n 2; } < small', '_POSIX2_VERSION=200112 @tail +3 small',
         '_POSIX2_VERSION=199209 @tail -c small']


def rand_case():
    f = rng.choice(FILES)
    unit = rng.choice(['n', 'n', 'c'])
    num = rng.choice(['0', '1', '2', '5', '10', '14', '15', '16', '100', '4999', '5000', '5001', '8191', '8192', '8193',
                      '70000', '1k', '2b'])
    sign = rng.choice(['', '', '+', '-'])
    opt = '-%s %s%s' % (unit, sign, num)
    if rng.random() < 0.1:
        opt += ' -z'
    form = rng.random()
    if form < 0.55:
        cmd = '@tail %s %s' % (opt, f)
    elif form < 0.85:
        cmd = 'cat %s | @tail %s' % (f, opt)
    else:
        cmd = '@tail %s < %s' % (opt, f)
    return cmd + ' | md5sum'


FOLLOW = [
    # append while following
    "cp small f; (@tail -f -n 2 f & p=$!; sleep 0.5; echo new1 >> f; sleep 1.5; echo new2 >> f; sleep 1.5; kill $p) 2>&1",
    # truncation
    "cp small f; (@tail -f -n 1 f & p=$!; sleep 0.5; : > f; echo after >> f; sleep 2; kill $p) 2>&1",
    # --pid: exits when the writer dies
    "cp small f; (sleep 1.2 & w=$!; @tail -f -n 1 -s 0.3 --pid=$w f; echo exit $?) 2>&1",
    # -F follows a rotated file
    "cp small f; (@tail -F -n 1 -s 0.3 f & p=$!; sleep 0.8; mv f f.old; echo rotated > f; sleep 1.5; kill $p) 2>&1",
    # -F with the file removed and recreated
    "cp small f; (@tail -F -n 1 -s 0.3 f & p=$!; sleep 0.8; rm f; sleep 1; echo back > f; sleep 1.5; kill $p) 2>&1",
    # --retry on a missing file with -F
    "rm -f g; (@tail -F -s 0.3 g & p=$!; sleep 0.8; echo created > g; sleep 1.5; kill $p) 2>&1",
    # -f on several files: headers when the source changes
    "cp small f; cp nonl h; (@tail -f -n 1 -s 0.3 f h & p=$!; sleep 0.8; echo A >> f; sleep 1; echo B >> h; sleep 1; kill $p) 2>&1",
    # the reader of the pipe goes away
    "cp small f; (@tail -f -n 1 -s 0.2 f | head -1; echo done) 2>&1",
    # -f on a pipe is ignored
    "(echo a; echo b) | @tail -f; echo exit $?",
    # follow by name of a missing file without --retry
    "rm -f g; (@tail -f --follow=name -s 0.3 g & p=$!; sleep 1; kill $p) 2>&1",
]


def run(cmd, which, follow=False):
    if which == 'nebox':
        c = cmd.replace('@tail', NEBOX + (' tail ---disable-inotify' if follow else ' tail'))
    elif follow:
        c = cmd.replace('@tail', 'tail ---disable-inotify')
    else:
        c = cmd.replace('@tail', 'tail')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=60)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'').replace(b'tail ---disable-inotify', b'tail')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    out = p.stdout.replace(NEBOX.encode() + b' ', b'')
    return p.returncode, out, err


cases = [(c, False) for c in FIXED + [rand_case() for _ in range(CASES)]] + [(c, True) for c in FOLLOW]
bad = 0
for c, follow in cases:
    g = run(c, 'gnu', follow)
    n = run(c, 'nebox', follow)
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:400] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:400] if isinstance(y, bytes) else y))

def event_case(follow_name):
    w('watched', b'initial\n')
    p = subprocess.Popen([NEBOX, 'tail', '-F' if follow_name else '-f',
                          '--sleep-interval=15', 'watched'],
                         cwd=d, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def expect(data):
        ready, _, _ = select.select([p.stdout], [], [], 5)
        if not ready or p.stdout.readline() != data:
            raise AssertionError('did not receive %r before the poll interval' % data)

    try:
        expect(b'initial\n')
        deadline = time.monotonic() + 5
        while True:
            proc_path = '/proc/%d/fd' % p.pid
            if 'anon_inode:inotify' in [os.readlink(os.path.join(proc_path, f)) for f in os.listdir(proc_path)]:
                # An inotify fd can exist briefly before its first watch.
                for f in os.listdir('/proc/%d/fdinfo' % p.pid):
                    with open('/proc/%d/fdinfo/%s' % (p.pid, f)) as info:
                        if 'inotify wd:' in info.read():
                            break
                else:
                    f = None
                if f is not None:
                    break
            if time.monotonic() >= deadline:
                raise AssertionError('inotify watch did not start')
            time.sleep(0.01)

        os.rename(os.path.join(d, 'watched'), os.path.join(d, 'rotated'))
        if follow_name:
            w('watched', b'replacement\n')
            expect(b'replacement\n')
        else:
            with open(os.path.join(d, 'rotated'), 'ab') as f:
                f.write(b'descriptor\n')
            expect(b'descriptor\n')
    finally:
        p.terminate()
        p.communicate(timeout=5)
        for f in ('watched', 'rotated'):
            if os.path.exists(os.path.join(d, f)):
                os.remove(os.path.join(d, f))

for follow_name in (False, True):
    try:
        event_case(follow_name)
    except (AssertionError, OSError, subprocess.TimeoutExpired) as error:
        bad += 1
        print('MISMATCH: inotify follow_name=%s: %s' % (follow_name, error))
print('tail_compare: %d cases, %d mismatches' % (len(cases) + 2, bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
