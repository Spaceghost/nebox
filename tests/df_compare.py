#!/usr/bin/env python3
"""Side-by-side test of nebox df against GNU coreutils df.
Usage: tests/df_compare.py path/to/nebox
Both read the same live mount table; a case whose output differs is rerun
up to four times, since busy file systems (the root's usage) change between
runs, and counts as a mismatch only if it never matches. Output,
diagnostics (minus "Try --help") and exit status must match."""
import os, re, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
d = tempfile.mkdtemp(prefix='df-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
open(os.path.join(d, 'f'), 'w').write('x')
os.symlink('f', os.path.join(d, 'lnk'))
env = dict(os.environ, LC_ALL='C', D=d)
for k in ('POSIXLY_CORRECT', 'DF_BLOCK_SIZE', 'BLOCK_SIZE', 'BLOCKSIZE'):
    env.pop(k, None)

BASE = ['', '-a', '-l', '-i', '-h', '-H', '-k', '-m', '-P', '-T', '-aT', '-ai', '-ah', '-hT', '-PT', '-Pi', '-Ph',
        '--total', '-a --total', '-h --total', '-i --total', '-T --total', '--output', '--output --total',
        '--output=source', '--output=target,source', '--output=size,used,avail,pcent', '--output=file,target',
        '--output=itotal,iused,iavail,ipcent', '--output=fstype', '-h --output', '-H --output=size,avail',
        '-k --output=size', '--sync', '--no-sync', '-v', '--local --print-type', '--portability --total']
CASES = []
for b in BASE:
    CASES += ['@df %s' % b, '@df %s -x zfs' % b, '@df %s / /dev/shm $D/f' % b]
for t in ['tmpfs', 'devtmpfs', 'zfs', 'proc', 'sysfs', 'bogus', 'none']:
    CASES += ['@df -t %s' % t, '@df -x %s' % t, '@df -a -t %s' % t, '@df -T -t %s -t devtmpfs' % t, '@df -F %s' % t]
for bs in ['1', '1K', '1k', '1KB', '1KiB', 'K', 'KB', 'KiB', 'M', 'MB', 'MiB', 'G', "'1", "'K", '1000', '4096', '512',
           '0x400', '010', '3', '7K', 'x', '1x', '0', '-1', '', 'human-readable', 'si', 'h', 's', 'hu', 'Y', '1Y',
           '99999999999999999999', '1E', '9E', '2kB', '1.5K', ' 1K', 'k1']:
    CASES += ["@df -B '%s' -x zfs" % bs, "@df --block-size='%s' /dev/shm" % bs, "@df -B '%s' --total -x zfs" % bs]
for var in ['DF_BLOCK_SIZE', 'BLOCK_SIZE', 'BLOCKSIZE']:
    for v in ['1K', 'human-readable', 'si', "'1", 'x', '10x', '', '0', 'MB', '512']:
        CASES.append("%s='%s' @df -x zfs" % (var, v))
CASES += [
    'POSIXLY_CORRECT=1 @df -x zfs', 'POSIXLY_CORRECT=1 @df -P -x zfs', 'POSIXLY_CORRECT=1 @df -k -x zfs',
    'DF_BLOCK_SIZE=1K BLOCK_SIZE=1M @df -x zfs', 'BLOCK_SIZE=1M @df -B 1K -x zfs', 'DF_BLOCK_SIZE=1M @df -P -x zfs',
    '@df /', '@df /dev', '@df /dev/null', '@df /dev/zero /dev/full', '@df /proc', '@df /sys', '@df /run /run/lock',
    '@df /proc/self', '@df .', '@df $D', '@df $D/f $D/lnk', '@df nonexistent', '@df / nonexistent /dev/shm',
    '@df -a /dev/null', '@df -i /dev/shm /proc', '@df -t tmpfs /dev/shm /', '@df -x tmpfs /dev/shm /',
    '@df -l /', '@df --output=file $D/f /dev/shm', '@df --output=file,source,target /proc /sys .',
    '@df -t tmpfs -x tmpfs', '@df -t a -t b -x b -x a', '@df -t zfs -x zfs /', '@df -i -h', '@df -i -P',
    '@df --output -i', '@df -i --output', '@df -T --output', '@df --output -T', '@df -P --output',
    '@df --output -P', '@df --output=bogus', '@df --output=source,source', '@df --output=size,', '@df --output=',
    '@df --output=source --output=target', '@df --bogus', '@df -q', '@df --tot', '@df --out=pcent',
    '@df --block-size', '@df -t', '@df -x', '@df -h -B 1K -x zfs', '@df -B 1K -h -x zfs', '@df -m -k -x zfs',
    '@df -a -x proc -x sysfs -x devpts', '@df -a --output=source,fstype,target', '@df -ai --total',
    '@df / > /dev/full; echo $?', '@df -t bogus /', '@df $D/f nonexistent2 -t tmpfs',
]


def run(cmd, which):
    c = cmd.replace('@df', (NEBOX + ' df') if which == 'nebox' else 'df')
    p = subprocess.run(['bash', '-c', c], cwd=d, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    # /dev/shm is shared with other test writers, so its used/available/inode
    # counts (and Use%) move between the two runs: mask the digits of its rows
    out = b'\n'.join(re.sub(rb'\d', b'#', l) if l.rstrip().endswith(b'/dev/shm') else l
                      for l in p.stdout.split(b'\n'))
    return p.returncode, out, err


bad = 0
for c in CASES:
    for attempt in range(5):
        g = run(c, 'gnu')
        n = run(c, 'nebox')
        if g == n:
            break
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:900]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:900]))
print('df_compare: %d cases, %d mismatches' % (len(CASES), bad))
subprocess.run(['rm', '-rf', d])
sys.exit(1 if bad else 0)
