#!/usr/bin/env python3
"""Side-by-side test of nebox chown/chgrp against GNU coreutils.
Usage: tests/chown_compare.py path/to/nebox
Each case runs on a fresh fixture on tmpfs; stdout, diagnostics (minus
"Try" lines), exit status and every file's uid:gid must match. As an
ordinary user most changes fail with EPERM and the messages are what is
compared; run as root, ownership really changes."""
import os, pwd, grp, re, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='chown-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
ME = pwd.getpwuid(os.getuid()).pw_name
MG = grp.getgrgid(os.getgid()).gr_name
U, G = os.getuid(), os.getgid()
SETUP = r"""
mkdir -p t/a/b t/e nr
printf x > t/f1; printf x > t/a/f2; printf x > t/a/b/f3; printf x > f; printf x > g
ln -s f lf; ln -s t lt; ln -s nowhere dangling; ln -s ../t t/a/up
printf x > nr/x; chmod 0 nr; ln -s / lroot
"""
SPECS = [ME, '%s:' % ME, '%s:%s' % (ME, MG), ':%s' % MG, ':', '', str(U), '%d:%d' % (U, G), '+%d' % U, '+%d:+%d' % (U, G),
         '%s.%s' % (ME, MG), '%s.' % ME, 'nosuchuser', ':nosuchgroup', 'nosuchuser:', '0', '0:0', ':0', 'root',
         'root:root', '4294967295', '4294967294', '4294967296', '-1', 'x:', '%s:x' % ME, '1x', 'daemon', 'nobody:nogroup']
CASES = []
for s in SPECS:
    CASES += ["@chown '%s' f" % s, "@chown -v '%s' f lf" % s, "@chown -c '%s' f" % s, "@chown -f '%s' f nonexistent" % s]
for o in ['', '-v', '-c', '-f', '-R', '-Rv', '-Rc', '-Rf', '-Rh', '-Rhv', '-RHv', '-RLv', '-RPv', '-Rv --dereference',
          '-RHv --dereference', '-h -v', '--dereference -v', '-v --from=%s' % ME, '-v --from=:%s' % MG,
          '-v --from=%s:%s' % (ME, MG), '-v --from=root', '-v --from=:root', '-Rv --from=%s' % ME, '-Rv --from=0:0',
          '-v --from=nosuch', '-v --from=%s.%s' % (ME, MG), '-v --from=', '-v --from=:']:
    CASES += ['@chown %s %s t lf lt dangling' % (o, ME), '@chown %s %s:%s t/f1 t/a' % (o, ME, MG),
              '@chown %s root t/f1 lf' % o, '@chgrp %s %s t lf lt dangling' % (o.replace('--from=', '--x='), MG)]
CASES += [
    '@chown', '@chown %s' % ME, '@chown --reference=f', '@chown --reference=f g', '@chown -v --reference=f g lf',
    '@chown --reference=nonexistent g', '@chown -R --dereference %s t' % ME, '@chown -RL --dereference -v %s t' % ME,
    '@chown -Rv %s nr' % ME, '@chown -Rvf %s nr' % ME, '@chown -v %s nr' % ME, '@chown -Rv %s nr/x' % ME,
    '@chown -v %s nonexistent' % ME, '@chown -v %s ""' % ME, '@chown -Rv %s t nonexistent t/a' % ME,
    '@chown -R --preserve-root %s /' % ME, '@chown -RH --preserve-root %s lroot' % ME,
    '@chown -RL --preserve-root -v %s lt' % ME, '@chown --no-preserve-root -v %s f' % ME,
    '@chown --bogus %s f' % ME, '@chown -x %s f' % ME, '@chown --verb %s f' % ME, '@chown --from %s' % ME,
    '@chgrp', '@chgrp %s' % MG, '@chgrp -v %s f lf' % MG, '@chgrp -v %d f' % G, '@chgrp -v nosuchgroup f',
    '@chgrp -v "" f', '@chgrp -v 4294967295 f', '@chgrp -v 4294967296 f', '@chgrp -v +%d f' % G, '@chgrp -v root f',
    '@chgrp -c root f', '@chgrp -cf root f', '@chgrp --reference=f -v g', '@chgrp --reference=nonexistent g',
    '@chgrp -Rv %s t' % MG, '@chgrp -RHv %s lt' % MG, '@chgrp -RLv %s lt' % MG, '@chgrp -Rhv %s lt' % MG,
    '@chgrp --from=x %s f' % MG, '@chgrp -v %s nonexistent' % MG, '@chgrp -v %s. f' % MG,
    '@chown -v %s f > /dev/full; echo $?' % ME,
]


def snapshot(root):
    out = []
    for dp, dns, fns in os.walk(root):
        for n in sorted(dns + fns):
            p = os.path.join(dp, n)
            st = os.lstat(p)
            out.append('%s %d:%d' % (os.path.relpath(p, root), st.st_uid, st.st_gid))
    return '\n'.join(sorted(out)).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        subprocess.run(['chmod', '-R', 'u+rwx', wd])
        shutil.rmtree(wd)
    os.makedirs(wd)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True)
    c = cmd.replace('@chown', (NEBOX + ' chown') if which == 'nebox' else 'chown')
    c = c.replace('@chgrp', (NEBOX + ' chgrp') if which == 'nebox' else 'chgrp')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
    subprocess.run(['chmod', '-R', 'u+rwx', wd])
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    out = p.stdout
    # When a symlink can't be dereferenced GNU describes the failed change
    # "from" an uninitialized stat buffer; mask that field for such files.
    for m in re.finditer(rb"cannot dereference '([^']*)'", err):
        name = re.escape(m.group(1))
        out = re.sub(rb"(failed to change (?:ownership|group) of '" + name + rb"' from )\S+( to )", rb"\1?\2", out)
    return p.returncode, out, err, snapshot(wd)


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:700]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:700]))
print('chown_compare: %d cases, %d mismatches (uid %d)' % (len(CASES), bad, os.getuid()))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d)
sys.exit(1 if bad else 0)
