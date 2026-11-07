#!/usr/bin/env python3
"""Side-by-side test of nebox base64, base32 and basenc against GNU coreutils.
Usage: tests/basenc_compare.py path/to/nebox [random-cases] [seed]
Fixed cases cover options and diagnostics; random cases encode random data
of block-boundary sizes with random wrap widths, then decode it after
random damage (inserted newlines, garbage, cut padding, case changes) with
and without -i. Standard output, standard error and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 300
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='basenc-compare-')
APPS = ['basenc', 'base64', 'base32']
ENCS = ['base64', 'base64url', 'base32', 'base32hex', 'base16', 'base2msbf', 'base2lsbf', 'z85']


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


frng = random.Random(3)
for n in [0, 1, 2, 3, 4, 5, 7, 8, 12, 40, 3071, 3072, 3073, 4199, 4200, 4201, 5120, 30719, 30720, 30721, 70000]:
    w('d%d' % n, bytes(frng.randrange(256) for _ in range(n)))
w('text', b'hello world\n')
os.mkdir(os.path.join(d, 'adir'))


def run(cmd, which):
    c = cmd
    if which == 'nebox':
        for a in APPS:
            c = c.replace('@' + a, NEBOX + ' ' + a)
    else:
        c = c.replace('@', '')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=60)
    return p.returncode, p.stdout, p.stderr.replace(NEBOX.encode() + b' ', b'')


FIXED = []
for app, encs in (('base64', ['']), ('base32', ['']), ('basenc', ['--' + e for e in ENCS])):
    for e in encs:
        a = '@%s %s' % (app, e)
        for n in [0, 1, 2, 3, 4, 5, 7, 8, 12, 40, 3071, 3072, 3073, 4200, 30720, 30721, 70000]:
            FIXED.append('%s d%d | od -c | tail -3' % (a, n))
            FIXED.append('%s %s d%d | %s -d | cmp - d%d; echo $?' % (app, e, n, a, n))
        FIXED += ['%s -w 0 d40' % a, '%s -w 1 d5' % a, '%s -w 7 d40' % a, '%s --wrap=3 d12' % a, '%s -w -1 d5' % a,
                  '%s -w x d5' % a, '%s -w 99999999999999999999999 d40' % a, '%s -w " +5" d12' % a, '%s -w 5k d12' % a,
                  '%s nofile' % a, '%s adir' % a, '%s -d adir' % a, '%s d1 d2' % a, '%s < text' % a, '%s - < text' % a,
                  '%s --help | head -2' % a, '%s -x' % a, '%s --bogus' % a,
                  "printf 'garbage!' | %s -d" % a, "printf 'garbage!' | %s -d -i" % a,
                  "%s %s text | tr -d '\\n' | %s -d" % (app, e, a), "%s %s d40 | %s -d -w 3 | od -c | tail -2" % (app, e, a)]
FIXED += ['@basenc d5', '@basenc --base64 --base32 text', '@basenc --base6 text', '@basenc --base2 text', '@basenc --z85 d5',
          '@basenc --z85 d8', 'printf "abcd" | @basenc --z85 -d', 'printf "%%%%%%%%%%" | @basenc --z85 -d',
          'printf "00000\\n00000" | @basenc --z85 -d | od -c', 'printf "+/==" | @basenc --base64url -d',
          'printf "-_==" | @basenc --base64url -d | od -c', 'printf "+/==" | @basenc --base64url -d -i | od -c',
          'printf "0v" | @basenc --base16 -d', 'printf "0A0" | @basenc --base16 -d', 'printf "0a" | @basenc --base16 -d',
          'printf "0101" | @basenc --base2msbf -d', 'printf "01010101\\n1" | @basenc --base2lsbf -d | od -c',
          'printf "YQ" | @base64 -d', 'printf "YQ=" | @base64 -d', 'printf "YQ==YQ==" | @base64 -d', 'printf "YQ==\\nYQ==" | @base64 -d',
          'printf "Y\\nQ\\n=\\n=" | @base64 -d', 'printf "YWJj\\r\\n" | @base64 -d', 'printf "YWJj" | @base64 -d -i',
          'printf "ME======" | @base32 -d', 'printf "ME=====" | @base32 -d', 'printf "me======" | @base32 -d', 'printf "MFRGG" | @base32 -d']

ALPH = {'base64': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=',
        'base32': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567='}


def rand_case():
    app = rng.choice(APPS)
    e = '--' + rng.choice(ENCS) if app == 'basenc' else ''
    n = rng.choice([0, 1, 2, 3, 4, 5, 8, 12, 40, 3071, 3072, 3073, 4199, 4200, 4201, 5120, 30720, 30721, 70000])
    if e == '--z85':
        n -= n % 4
    if rng.random() < 0.5:
        wopt = '-w %d' % rng.choice([0, 1, 3, 4, 5, 8, 60, 76, 4096])
        return '@%s %s %s d%d | md5sum' % (app, e, wopt, n)
    ww = rng.choice([0, 3, 4, 7, 8, 76])
    p = subprocess.run(['sh', '-c', '%s %s -w %d d%d' % (app, e, ww, n)], cwd=d, env=env, capture_output=True)
    data = bytearray(p.stdout)
    for _ in range(rng.choice([0, 0, 1, 2, 5])):
        if not data:
            break
        i = rng.randrange(len(data) + 1)
        op = rng.random()
        if op < 0.3:
            data[i:i] = b'\n'
        elif op < 0.5:
            data[i:i] = rng.choice([b'!', b' ', b'=', b'\r', b'\t', b'*', b'-', b'_', b'a', b'Z', b'0'])
        elif op < 0.7 and i < len(data):
            del data[i]
        elif i < len(data):
            data[i] = rng.randrange(33, 127)
    w('enc', bytes(data))
    opt = rng.choice(['-d', '-d', '-d -i', '--decode --ignore-garbage'])
    return '@%s %s %s enc | md5sum' % (app, e, opt)


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
            if 'enc ' in c:
                print('  enc:', open(os.path.join(d, 'enc'), 'rb').read()[:200])
print('basenc_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
