#!/usr/bin/env python3
"""Side-by-side test of nebox rm against GNU coreutils rm.
Usage: tests/rm_compare.py path/to/nebox
Each case gets a fresh fixture tree (nested directories, symlinks, files
and directories without write or read permission, odd names); stdout,
diagnostics and prompts (minus "Try" lines), exit status and the tree left
behind must match. Prompts are answered through stdin, with
---presume-input-tty where a terminal is needed."""
import os, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
# On tmpfs readdir order depends only on creation order, so the two
# fixtures list alike (ZFS, for one, salts its directory hashes).
d = tempfile.mkdtemp(prefix='rm-compare-', dir='/dev/shm' if os.access('/dev/shm', os.W_OK) else None)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)

SETUP = r"""
mkdir -p t/a/b/c t/e empty ro/sub nr wp
printf x > t/f1; printf x > t/a/f2; printf x > t/a/b/f3; : > t/a/b/c/f4
printf x > f; : > zero; printf x > g; printf x > h; printf x > i
ln -s f lf; ln -s nowhere dangling; ln -s t lt
printf x > ro/r1; printf x > ro/sub/r2; chmod 555 ro/sub
printf x > nr/n1; chmod 0 nr
printf x > wp/w1; chmod 444 wp/w1; printf x > wpf; chmod 444 wpf
mkdir wpd; chmod 555 wpd; mkdir wpe; printf x > wpe/k; chmod 555 wpe
printf x > -- '-dash'; printf x > 'sp ace'; printf x > $'nl\nx'
mkfifo fifo
"""

CASES = [
    '@rm f', '@rm f g h', '@rm nonexistent', '@rm -f nonexistent', '@rm', '@rm -f', '@rm ""', '@rm -f ""',
    '@rm t', '@rm -d t', '@rm -d empty', '@rm -r t', '@rm -R t', '@rm -rv t', '@rm -v f zero lf',
    '@rm -rf t nonexistent', '@rm -r t/', '@rm -r t//', '@rm -r t///', '@rm -rv t//', '@rm -r .', '@rm -r ..',
    '@rm -r t/.', '@rm -r t/..', '@rm -rf ./', '@rm -rf .//', '@rm -rf t/./', '@rm -rf t/../', '@rm -rf ..x', '@rm -rf .x', '@rm -r ./t', '@rm -d .', '@rm .', '@rm lf dangling lt',
    '@rm -r lt', '@rm -r lt/', '@rm -rv lt/', '@rm lt/', '@rm -d lt/', '@rm fifo', '@rm -v fifo',
    '@rm -r ro', '@rm -rf ro', '@rm -rv ro', '@rm -r nr', '@rm -rf nr', '@rm -d nr', '@rm -r wp', '@rm wpf',
    '@rm -f wpf', '@rm -r wpd', '@rm -r wpe', '@rm -rf wpe', '@rm -- -dash', '@rm -dash', '@rm -x',
    '@rm --bogus', '@rm -- "sp ace" $\'nl\\nx\'', '@rm -v "sp ace" $\'nl\\nx\'',
    "printf 'y\\n' | @rm -i f", "printf 'n\\n' | @rm -i f", "printf 'yes\\n' | @rm -i f", "printf 'Y' | @rm -i f",
    "@rm -i f < /dev/null", "printf ' y\\n' | @rm -i f", "printf 'y\\nn\\ny\\n' | @rm -i f g h",
    "printf 'y\\ny\\ny\\ny\\ny\\ny\\ny\\ny\\ny\\n' | @rm -ri t", "printf 'y\\nn\\ny\\ny\\ny\\ny\\ny\\ny\\n' | @rm -ri t",
    "printf 'n\\n' | @rm -ri t", "printf 'y\\ny\\n' | @rm -ri empty", "printf 'y\\n' | @rm -di empty",
    "printf 'y\\n' | @rm -i t", "printf 'y\\n' | @rm -i lf", "printf 'y\\n' | @rm -i dangling",
    "printf 'y\\n' | @rm -i zero fifo", "printf 'y\\n' | @rm -i nonexistent", "printf 'y\\n' | @rm -fi f",
    "printf 'y\\n' | @rm -if f", "printf 'y\\n' | @rm -I f g h", "printf 'y\\n' | @rm -I f g h i",
    "printf 'n\\n' | @rm -I f g h i", "printf 'y\\n' | @rm -rI t", "printf 'n\\n' | @rm -rI t f",
    "printf 'y\\n' | @rm --interactive f", "printf 'y\\n' | @rm --interactive=always f",
    "printf 'y\\n' | @rm --interactive=once f g h i", "printf 'y\\n' | @rm --interactive=never f",
    "printf 'y\\n' | @rm --interactive=n f", "printf 'y\\n' | @rm --interactive=o f g h i",
    "printf 'y\\n' | @rm --interactive=a f", "@rm --interactive=bogus f", "@rm --interactive= f",
    "printf 'y\\n' | @rm ---presume-input-tty wpf", "printf 'n\\n' | @rm ---presume-input-tty wpf",
    "printf 'y\\n' | @rm ---presume-input-tty -f wpf", "printf 'y\\ny\\ny\\n' | @rm ---presume-input-tty -r wp",
    "printf 'y\\ny\\n' | @rm ---presume-input-tty -r wpd", "printf 'y\\ny\\ny\\n' | @rm ---presume-input-tty -r wpe",
    "printf 'y\\n' | @rm ---presume-input-tty lf f", "printf 'y\\n' | @rm ---presume-input-tty nonexistent",
    "printf 'y\\ny\\ny\\ny\\n' | @rm ---presume-input-tty -ri ro", "printf 'y\\n' | @rm ---presume-input-tty wpd",
    "printf 'y\\ny\\n' | @rm ---presume-input-tty -d wpd", "printf 'y\\n' | @rm -i ---presume-input-tty wpf",
    "printf 'y\\nn\\nrest\\n' > ans; { @rm -i f g; cat; } < ans", "printf 'y\\n' > ans; { @rm -I f g h i; cat; } < ans",
    '@rm --no-preserve-root -r t', '@rm --no-pres -r t', '@rm --no-preserve-roo -r t', '@rm --preserve-root -r t',
    '@rm --preserve-root=all -r t', '@rm --preserve-root=bogus -r t', '@rm --preserve-root= -r t',
    '@rm --one-file-system -r t', '@rm --one-file-system t', '@rm -r --dir t', '@rm --recursive --verbose t',
    '@rm --force nonexistent', '@rm --verb f', '@rm --re t', '@rm --d empty', '@rm --i f < /dev/null',
    '@rm -v f > /dev/full; echo $?', 'cd t && @rm -r ../t; echo $?', '@rm -r t t', '@rm -rv t/a t',
    '@rm -r t/a/b t/a', '@rm -r t/a t/a/b', 'chmod 0 t/a; @rm -r t', 'chmod 0 t/a; @rm -rf t',
    'chmod 300 t/a; @rm -r t', 'chmod 100 t/a; @rm -rv t', 'chmod 500 t/a; @rm -rv t', 'chmod 600 t/a; @rm -r t',
]


def snapshot(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns.sort()
        rel = os.path.relpath(dp, root)
        for n in sorted(fns + [x for x in dns if os.path.islink(os.path.join(dp, x))]):
            out.append(os.path.join(rel, n))
        for n in dns:
            if not os.path.islink(os.path.join(dp, n)):
                out.append(os.path.join(rel, n) + '/')
    return '\n'.join(sorted(out)).encode()


def run(cmd, which):
    wd = os.path.join(d, which)
    if os.path.exists(wd):
        subprocess.run(['chmod', '-R', 'u+rwx', wd])
        shutil.rmtree(wd)
    os.makedirs(wd)
    subprocess.run(['bash', '-c', SETUP], cwd=wd, check=True)
    c = cmd.replace('@rm', (NEBOX + ' rm') if which == 'nebox' else 'rm')
    p = subprocess.run(['bash', '-c', c], cwd=wd, env=env, capture_output=True, timeout=60, stdin=subprocess.DEVNULL)
    subprocess.run(['chmod', '-R', 'u+rwx', wd])
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err, snapshot(wd)


bad = 0
for c in CASES:
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        print('MISMATCH:', c)
        for name, x, y in zip(('status', 'stdout', 'stderr', 'files'), g, n):
            if x != y:
                print('  %s gnu:   %r' % (name, x if isinstance(x, int) else x[:600]))
                print('  %s nebox: %r' % (name, y if isinstance(y, int) else y[:600]))
print('rm_compare: %d cases, %d mismatches' % (len(CASES), bad))
subprocess.run(['chmod', '-R', 'u+rwx', d])
shutil.rmtree(d)
sys.exit(1 if bad else 0)
