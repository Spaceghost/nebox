#!/usr/bin/env python3
"""Side-by-side test of nebox groups against GNU coreutils 9.1 groups.
Usage: tests/groups_compare.py path/to/nebox
The system's users (root, the caller, unknown names, numeric and empty
operands), options and option errors, --help, output to /dev/full. Then,
inside a private user and mount namespace (unshare -rm), fixture
/etc/passwd and /etc/group files bound over the real ones: users with
many supplementary groups, duplicated memberships, a primary group without
a name, a user listed in a group with its own primary gid, more than ten
groups (getgrouplist's retry), and a user missing from passwd. Run as
root, the no-operand form is also checked under setpriv with differing
real and effective gids and supplementary groups with and without names.
stdout, stderr and exit status must match; --version differs by design
(nebox's line) and only its status is compared; --help omits GNU's
closing links."""
import os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='groups-compare-', dir='/dev/shm')
os.chmod(d, 0o755)
env = dict(os.environ, LC_ALL='C')
ROOT = os.geteuid() == 0
me = subprocess.run(['id', '-un'], capture_output=True, text=True).stdout.strip()

CASES = []
for a in ['', 'root', me, 'root ' + me, 'nosuchuser', 'root nosuchuser ' + me, '0', "''", '--', '-- root', '-- -x',
          '-x', '--bogus', '--help', '--he', '--help root', 'root --help', '--version', '--vers', '--help=x', 'root -x',
          'root > /dev/full; echo $?', '> /dev/full; echo $?', '--help > /dev/full; echo $?', 'root >&-; echo $?',
          'daemon bin sys nobody', "'root '", 'ROOT']:
    CASES.append(('@ ' + a, False))
NOVERSION = {'@ --version', '@ --vers'}

# fixture account files for the namespace cases
passwd = ['root:x:0:0:root:/root:/bin/sh', 'alice:x:2001:2001::/h:/bin/sh', 'bob:x:2002:2002::/h:/bin/sh',
          'carol:x:2003:2999::/h:/bin/sh', 'dave:x:2004:2001::/h:/bin/sh', 'erin:x:2005:2005::/h:/bin/sh',
          'frank:x:2006:2006::/h:/bin/sh', 'gary:x:2007:3000::/h:/bin/sh']
group = ['root:x:0:', 'alice:x:2001:', 'bob:x:2002:', 'erin:x:2005:', 'staff:x:3000:alice,bob,dave',
         'dev:x:3001:alice,carol', 'ops:x:3002:bob,alice', 'dup:x:3003:alice,alice', 'self:x:2001:erin',
         'again:x:3001:erin', 'gone:x:4000:ghost', 'other:x:3004:dave,erin,gary']
for k in range(14):
    group.append('many%d:x:%d:frank' % (k, 5000 + k))
group.append('frank2:x:2006:frank')
open(os.path.join(d, 'passwd'), 'w').write('\n'.join(passwd) + '\n')
open(os.path.join(d, 'group'), 'w').write('\n'.join(group) + '\n')
for a in ['alice', 'bob', 'carol', 'dave', 'erin', 'frank', 'gary', 'ghost', 'alice bob carol dave erin frank gary',
          'root', '2001', 'alice ghost bob']:
    CASES.append(('@ ' + a, True))
if ROOT:
    for spec in ['--regid=0 --clear-groups', '--rgid=2001 --egid=3001 --groups=3000,3002,4000',
                 '--rgid=3000 --egid=3000 --groups=3000,3001,3000,2001', '--regid=9999 --groups=9998,3000',
                 '--rgid=2001 --egid=9999 --groups=2001', '--regid=2001 --groups=2001,2001,2001',
                 '--reuid=2001 --regid=2001 --groups=' + ','.join(str(5000 + k) for k in range(14))]:
        CASES.append(('setpriv %s @' % spec, True))
        CASES.append(('setpriv %s @ alice' % spec, True))


def run(c, which):
    cmd, ns = c
    prog = 'groups' if which == 'gnu' else NEBOX + ' groups'
    sh = cmd.replace('@', prog)
    if ns:
        sh = ('mount --bind %s/passwd /etc/passwd && mount --bind %s/group /etc/group && %s' % (d, d, sh))
        argv = ['unshare', '-m', 'sh', '-c', sh] if ROOT else ['unshare', '-rm', 'sh', '-c', sh]
    else:
        argv = ['bash', '-c', sh]
    p = subprocess.run(argv, cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    out = p.stdout
    if which == 'gnu' and b'\nGNU coreutils online help' in out:
        # --help without GNU's closing links, by design
        out = out[:out.index(b'\nGNU coreutils online help')]
    return p.returncode, out, p.stderr


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if c[0] in NOVERSION:
        g, n = (g[0], b'', g[2]), (n[0], b'', n[2])
    if g != n:
        bad += 1
        if bad <= 25:
            print('MISMATCH:', c)
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:300]))
                    print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:300]))
print('groups_compare: %d cases%s, %d mismatches' % (len(CASES), ' (as root)' if ROOT else '', bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
