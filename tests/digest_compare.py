#!/usr/bin/env python3
"""Side-by-side test of nebox's checksum applets (md5sum, sha1sum, sha224sum,
sha256sum, sha384sum, sha512sum, b2sum, cksum, sum) against GNU coreutils.
Usage: tests/digest_compare.py path/to/nebox [random-cases] [seed]
Fixed cases cover every algorithm at block-boundary sizes, the output forms,
check mode (tagged, untagged, OpenSSL-style, reversed BSD, escaped names,
malformed lines) and the diagnostics; random cases build check files from
mutated real output. Standard output, standard error and exit status must
match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 300
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='digest-compare-')
APPS = ['md5sum', 'sha1sum', 'sha224sum', 'sha256sum', 'sha384sum', 'sha512sum', 'b2sum', 'cksum', 'sum']


def w(name, data):
    with open(os.path.join(d, name), 'wb') as f:
        f.write(data)


frng = random.Random(5)
SIZES = [0, 1, 3, 55, 56, 57, 63, 64, 65, 111, 112, 113, 127, 128, 129, 255, 256, 1000, 65535, 65536, 65537, 200003]
for n in SIZES:
    w('f%d' % n, bytes(frng.randrange(256) for _ in range(n)))
w('abc', b'abc')
w('text', b'hello world\n')
w('a b', b'space\n')
w('back\\slash', b'bs\n')
w('new\nline', b'nl\n')
w('cr\rname', b'cr\n')
w('star*', b'star\n')
os.mkdir(os.path.join(d, 'adir'))


def run(cmd, which):
    if which == 'gnu':
        c = cmd.replace('@', '')
    else:
        c = cmd
        for a in sorted(APPS, key=len, reverse=True):
            c = c.replace('@' + a, NEBOX + ' ' + a)
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=60)
    return p.returncode, p.stdout, p.stderr.replace(NEBOX.encode() + b' ', b'')


FIXED = []
allf = ' '.join('f%d' % n for n in SIZES)
for a in APPS:
    FIXED += ['@%s %s abc text' % (a, allf), '@%s < f1000' % a, 'cat f65537 | @%s' % a, '@%s - < abc' % a,
              '@%s nofile abc adir' % a, '@%s --help | head -1' % a, '@%s --bogus' % a, '@%s -x' % a]
for a in APPS[:7]:
    FIXED += ['@%s --tag abc text' % a, '@%s -b abc' % a, '@%s -t abc' % a, '@%s -z abc text | od -c' % a,
              "@%s 'a b' 'back\\slash' \"$(printf 'new\\nline')\" \"$(printf 'cr\\rname')\" 'star*'" % a,
              "@%s --tag 'back\\slash' \"$(printf 'new\\nline')\"" % a,
              "@%s -z \"$(printf 'new\\nline')\" | od -c" % a,
              '@%s --tag --text abc' % a, '@%s -c --tag abc' % a, '@%s -c -b abc' % a, '@%s --status abc' % a,
              '@%s --quiet abc' % a, '@%s -w abc' % a, '@%s --strict abc' % a, '@%s --ignore-missing abc' % a,
              '@%s -c -z abc' % a,
              '%s abc text f0 > ck; @%s -c ck' % (a, a), '%s abc text > ck; @%s --quiet -c ck' % (a, a),
              '%s --tag abc text > ck; @%s -c ck' % (a, a), '%s abc text > ck; @%s --status -c ck; echo $?' % (a, a),
              "%s 'a b' 'back\\slash' \"$(printf 'new\\nline')\" \"$(printf 'cr\\rname')\" > ck; @%s -c ck" % (a, a),
              "%s --tag 'back\\slash' \"$(printf 'new\\nline')\" > ck; @%s -c ck" % (a, a),
              "%s abc > ck; echo junk >> ck; echo '# comment' >> ck; @%s -c ck" % (a, a),
              "%s abc > ck; echo junk >> ck; @%s -c -w ck" % (a, a),
              "%s abc > ck; echo junk >> ck; @%s -c --strict ck" % (a, a),
              "%s abc nofile 2>/dev/null > ck; %s abc | sed 's/abc/nofile/' > ck; @%s -c ck" % (a, a, a),
              "%s abc | sed 's/abc/nofile/' > ck; %s text >> ck; @%s -c --ignore-missing ck" % (a, a, a),
              "%s abc | sed 's/abc/nofile/' > ck; @%s -c --ignore-missing ck" % (a, a),
              "%s abc | sed 's/^./0/' > ck; @%s -c ck" % (a, a),
              "%s abc | tr a-f A-F > ck; @%s -c ck" % (a, a),
              "%s abc | sed 's/  / */' > ck; @%s -c ck" % (a, a),
              "%s abc | sed 's/$/\\r/' > ck; @%s -c ck" % (a, a),
              "%s --tag abc | sed 's/ (/(/; s/) = /)= /' > ck; @%s -c ck" % (a, a),
              "%s --tag abc | sed 's/ = /=/' > ck; @%s -c ck" % (a, a),
              "%s --tag abc | sed 's/$/ /' > ck; @%s -c ck" % (a, a),
              "%s abc | awk '{print $1 \" \" $2}' > ck; @%s -c ck" % (a, a),
              "%s abc text | awk '{print $1 \" \" $2}' > ck; %s abc >> ck; @%s -c -w ck" % (a, a, a),
              "printf '' > ck; @%s -c ck" % a, '@%s -c nofile' % a, '@%s -c adir' % a,
              "%s abc > ck; @%s -c < ck" % (a, a), "%s - < abc > ck; @%s -c < ck" % (a, a),
              "%s abc > ck; @%s -c ck ck" % (a, a)]
FIXED += ['@b2sum -l 256 abc text', '@b2sum -l 8 abc', '@b2sum -l 504 f128', '@b2sum -l 12 abc', '@b2sum -l 0 abc',
          '@b2sum -l 520 abc', '@b2sum -l x abc', '@b2sum -l 99999999999999999999999 abc', '@b2sum --tag -l 128 abc',
          'b2sum -l 128 abc text > ck; @b2sum -c ck', 'b2sum --tag -l 128 abc text > ck; @b2sum -c ck',
          'b2sum --tag -l 128 abc > ck; b2sum abc >> ck; b2sum -l 16 text >> ck; @b2sum -c ck',
          "b2sum --tag -l 128 abc | sed 's/-128/-0x80/' > ck; @b2sum -c ck",
          "b2sum --tag -l 128 abc | sed 's/-128/-12/' > ck; @b2sum -c ck",
          "b2sum -l 128 abc | sed 's/^./xx/' > ck; @b2sum -c ck"]
for alg in ['bsd', 'sysv', 'crc', 'md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512', 'blake2b', 'sm3']:
    FIXED += ['@cksum -a %s %s abc' % (alg, allf), '@cksum -a %s < abc' % alg, '@cksum --algorithm=%s --untagged abc text' % alg,
              '@cksum -a %s -z abc | od -c' % alg]
    if alg not in ('bsd', 'sysv', 'crc'):
        FIXED += ['cksum -a %s abc text > ck; @cksum -c ck' % alg, 'cksum -a %s abc text > ck; @cksum -a %s -c ck' % (alg, alg),
                  'cksum -a %s --untagged abc > ck; @cksum -a %s -c ck' % (alg, alg),
                  'cksum -a %s --untagged abc > ck; @cksum -c ck' % alg]
FIXED += ['@cksum -a crc -c abc', '@cksum -a sysv -c abc', '@cksum -a foo abc', '@cksum -a md abc', '@cksum -l 128 abc',
          '@cksum -a blake2b -l 128 abc', '@cksum -a blake2b -l 128 --untagged abc', '@cksum -a sha1 -l 128 abc',
          'cksum -a blake2b -l 128 abc > ck; cksum -a sm3 text >> ck; cksum -a md5 abc >> ck; @cksum -c ck',
          'cksum abc > ck; @cksum -c ck', '@cksum -b abc', '@cksum -t abc', '@cksum --untagged abc', '@cksum --tag abc',
          'sum abc > ck; @cksum -c ck', '@sum -r abc text', '@sum -s abc text', '@sum --sysv f200003', '@sum -rs abc',
          '@sum -sr abc', '@sum --sys abc', '@sum -c abc', '@sum < f65537', '@sum - < abc', '@sum -- abc']


def rand_case():
    a = rng.choice(APPS[:7] + ['cksum'])
    files = rng.sample(['abc', 'text', 'f0', 'f64', 'f1000', 'nofile', "'a b'", "'back\\slash'"], rng.choice([1, 2, 3]))
    gen = a + ' ' + rng.choice(['', '--tag ', '-b ']) if a != 'cksum' else 'cksum ' + rng.choice(['-a md5 ', '-a sha256 ', '-a blake2b ', '-a sm3 --untagged ', '-a sha1 '])
    muts = ["s/^./0/", "s/ /  /", "s/(/ (/", "s/$/x/", "s/^/ /", "s/^/\\\\/", "s/[a-f]/G/", "s/  /\\t/", "s/ \\*/  /", "1d"]
    sed = ';'.join(rng.sample(muts, rng.choice([0, 1, 1, 2])))
    opts = ' '.join(rng.sample(['--quiet', '--status', '-w', '--strict', '--ignore-missing'], rng.choice([0, 1, 2])))
    if a == 'cksum' and rng.random() < 0.5:
        opts += ' ' + gen.split(' ', 1)[1].replace('--untagged ', '')
    cmd = '%s%s > ck 2>/dev/null; ' % (gen, ' '.join(files))
    if sed:
        cmd += "sed -i '%s' ck; " % sed
    cmd += '@%s -c %s ck; echo "exit $?"' % (a, opts)
    return cmd


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 15:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:600] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:600] if isinstance(y, bytes) else y))
print('digest_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
