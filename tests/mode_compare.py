#!/usr/bin/env python3
"""Side-by-side test of nebox chmod and mkdir -m against GNU coreutils.
Usage: tests/mode_compare.py path/to/nebox [random-cases] [seed]
Random symbolic and octal modes (gnulib modechange grammar) are applied
under random umasks to files and directories with random starting modes;
output, diagnostics, exit status and the resulting modes must match."""
import os, random, shutil, stat, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 400
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
root = tempfile.mkdtemp(prefix='mode-compare-')


def rand_mode():
    if rng.random() < 0.2:
        return '%o' % rng.choice([0, 7, 644, 755, 4755, 2775, 1777, 7777, 600, 0o10000 if rng.random() < 0.1 else 640])
    parts = []
    for _ in range(rng.choice([1, 1, 2, 3])):
        who = ''.join(rng.sample('ugoa', rng.choice([0, 0, 1, 2])))
        ops = ''
        for _ in range(rng.choice([1, 1, 2])):
            op = rng.choice('+-=')
            r = rng.random()
            if r < 0.15:
                perm = rng.choice('ugo')
            elif r < 0.2 and not who:
                perm = '%o' % rng.choice([0, 7, 55, 644, 4755])
            else:
                perm = ''.join(rng.sample('rwxXst', rng.choice([0, 1, 2, 3])))
            ops += op + perm
        parts.append(who + ops)
    s = ','.join(parts)
    if rng.random() < 0.03:
        s += rng.choice(['q', ',', 'u', '+z'])
    return s


def setup(d):
    if os.path.exists(d):
        for dp, dn, fn in os.walk(d):
            for x in dn:
                os.chmod(os.path.join(dp, x), 0o700)
        shutil.rmtree(d)
    os.mkdir(d)
    frng = random.Random(1)
    for name in ('f', 'g'):
        p = os.path.join(d, name)
        open(p, 'w').close()
        os.chmod(p, frng.choice([0o644, 0o755, 0o600, 0o4755, 0o000, 0o777]))
    os.makedirs(os.path.join(d, 'dir/sub'))
    open(os.path.join(d, 'dir/file'), 'w').close()
    os.chmod(os.path.join(d, 'dir/file'), 0o640)
    os.symlink('f', os.path.join(d, 'link'))
    os.symlink('nowhere', os.path.join(d, 'dangling'))
    os.symlink('../f', os.path.join(d, 'dir/lnk'))


def modes(d):
    out = []
    for dp, dn, fn in os.walk(d):
        for x in sorted(dn + fn):
            p = os.path.join(dp, x)
            try:
                st = os.lstat(p)
                out.append((os.path.relpath(p, d), oct(stat.S_IMODE(st.st_mode))))
            except OSError:
                out.append((os.path.relpath(p, d), 'unreadable'))
    return sorted(out)


def run(cmd, which):
    d = os.path.join(root, which)
    setup(d)
    c = cmd
    if which == 'nebox':
        for a in ('chmod', 'mkdir'):
            c = c.replace('@' + a, NEBOX + ' ' + a)
    else:
        c = c.replace('@', '')
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30)
    # stderr as a set of lines: the two trees are separate directories whose
    # readdir order differs; GNU's "Try '... --help'" line has no nebox twin
    err = sorted(l for l in p.stderr.replace(NEBOX.encode() + b' ', b'').split(b'\n') if l and not l.startswith(b"Try '"))
    return (p.returncode, p.stdout, err, modes(d))


FIXED = ['@chmod 755 f', '@chmod -v 644 f g', '@chmod -c 644 f g', '@chmod u+x,g-w f', '@chmod a=rX dir', '@chmod -R a=rX dir',
         '@chmod -R -v go-rwx dir | sort', '@chmod g=u f', '@chmod o=g,u-w f', '@chmod -w f', '@chmod -w -x f', '@chmod -rw f g',
         '@chmod +x f', '@chmod +s f', '@chmod g+s dir', '@chmod u+s,g+s dir', '@chmod 0755 dir', '@chmod 00755 dir', '@chmod 755 dir',
         '@chmod =  f', '@chmod a= f', '@chmod 7777 f', '@chmod 17777 f', '@chmod 8 f', '@chmod u+q f', '@chmod u f', '@chmod , f',
         '@chmod -v 644 link', '@chmod -v 644 dangling', '@chmod -v 644 nofile', '@chmod -f 644 nofile', '@chmod -R -v 600 dir/lnk',
         '@chmod -Rv u+w dir | sort', '@chmod --reference=f g', '@chmod --reference=nofile g', '@chmod --reference=f 600 g',
         '@chmod', '@chmod 644', '@chmod -R --preserve-root 755 /', '@chmod -x', '@chmod -Rw f', '@chmod -v -v 600 f',
         '@chmod -c -v 600 f', '@chmod --changes u+x f', '@chmod --verbose --recursive u+x dir | sort', '@chmod +t dir', '@chmod -t dir',
         '@mkdir -m 700 m; stat -c %a m', '@mkdir -m u=rwx,g=rx m; stat -c %a m', '@mkdir -m +t m; stat -c %a m',
         '@mkdir -m 4755 m; stat -c %a m', '@mkdir -m g+s m; stat -c %a m', '@mkdir -m a-w m; stat -c %a m', '@mkdir -m x m',
         '@mkdir -pm 700 m/n/o; stat -c %a m m/n m/n/o', '@mkdir -m 777 m; stat -c %a m', 'umask 077; @mkdir -m +r m; stat -c %a m',
         'umask 077; @mkdir -m 777 m; stat -c %a m', 'umask 000; @mkdir -m go-w m; stat -c %a m']


def rand_case():
    mask = rng.choice(['022', '077', '000', '027', '002', '777'])
    m = rand_mode()
    if rng.random() < 0.25:
        return "umask %s; @mkdir -m '%s' m; stat -c %%a m" % (mask, m)
    target = rng.choice(['f', 'g', 'dir', 'f g', 'dir/sub', 'link'])
    opts = rng.choice(['', '', '-v', '-c', '-R', '-Rv', '-f'])
    cmd = "umask %s; @chmod %s -- '%s' %s" % (mask, opts, m, target)
    if 'R' in opts:
        cmd += ' | sort'
    return cmd


cases = FIXED + [rand_case() for _ in range(CASES)]
bad = 0
for c in cases:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr', 'modes'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x))
                    print('  %s nebox: %r' % (name, y))
print('mode_compare: %d cases, %d mismatches' % (len(cases), bad))
setup(os.path.join(root, 'gnu')); setup(os.path.join(root, 'nebox'))
shutil.rmtree(root)
sys.exit(1 if bad else 0)
