#!/usr/bin/env python3
"""Side-by-side test of nebox cut and uniq against GNU coreutils.
Usage: tests/cutuniq_compare.py path/to/nebox [random-cases] [seed]
Random field/byte lists, delimiters and options run over random inputs
(lines with and without delimiters, empty lines, a missing final newline,
NUL-terminated records); output, every diagnostic line (minus GNU's
"Try --help" line) and exit status must match."""
import os, random, shutil, subprocess, sys, tempfile

NEBOX = os.path.abspath(sys.argv[1])
CASES = int(sys.argv[2]) if len(sys.argv) > 2 else 500
rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 20261107)
env = dict(os.environ, LC_ALL='C')
env.pop('POSIXLY_CORRECT', None)
d = tempfile.mkdtemp(prefix='cutuniq-compare-')


def rand_lines(sep):
    lines = []
    for _ in range(rng.choice([0, 1, 3, 8, 20])):
        n = rng.choice([0, 1, 1, 2, 3, 5])
        fields = [''.join(rng.choice('abAB c') for _ in range(rng.choice([0, 1, 2, 3]))) for _ in range(n)]
        lines.append(sep.join(fields))
    eol = rng.choice(['\n', '\n', '\n', '\0'])
    text = eol.join(lines)
    if lines and rng.random() < 0.8:
        text += eol
    return text.encode()


def rand_list():
    parts = []
    for _ in range(rng.choice([1, 1, 2, 3])):
        a, b = rng.randint(1, 6), rng.randint(1, 6)
        parts.append(rng.choice([str(a), '%d-%d' % (min(a, b), max(a, b)), '-%d' % a, '%d-' % a]))
    s = rng.choice([',', ' ']).join(parts)
    if rng.random() < 0.05:
        s = rng.choice(['0', '3-1', '-', 'x', '1-2-3', '', '1,,2', '99999999999999999999999'])
    return s


def cut_case():
    sep = rng.choice(['\t', ':', ' ', ','])
    with open(os.path.join(d, 'in'), 'wb') as f:
        f.write(rand_lines(sep))
    mode = rng.choice(['-f', '-f', '-b', '-c'])
    opts = [mode + ' ' + "'" + rand_list() + "'"]
    if mode == '-f':
        if sep != '\t' or rng.random() < 0.2:
            opts.append("-d '%s'" % sep)
        if rng.random() < 0.3:
            opts.append('-s')
    if rng.random() < 0.2:
        opts.append('--complement')
    if rng.random() < 0.2:
        opts.append("--output-delimiter='%s'" % rng.choice(['|', '--', '']))
    if rng.random() < 0.15:
        opts.append('-z')
    if rng.random() < 0.05:
        opts.append(rng.choice(['-d xy', '-s', '-n', '-d ""']))
    rng.shuffle(opts)
    return '@cut %s in' % ' '.join(opts)


def uniq_case():
    lines = []
    for _ in range(rng.choice([0, 1, 4, 10, 25])):
        w = rng.choice(['a', 'A', 'b', 'x a', 'y a', ' a', 'a b c', 'ab', 'Ab', ''])
        lines.extend([w] * rng.choice([1, 1, 2, 3]))
    eol = '\0' if rng.random() < 0.1 else '\n'
    text = eol.join(lines) + (eol if lines and rng.random() < 0.85 else '')
    with open(os.path.join(d, 'in'), 'wb') as f:
        f.write(text.encode())
    opts = []
    for _ in range(rng.choice([0, 1, 2, 3])):
        opts.append(rng.choice(['-c', '-d', '-u', '-D', '--all-repeated=prepend', '--all-repeated=separate', '-D=none',
                                '-i', '-f 1', '-s 1', '-w 1', '-w 2', '-f1 -s1', '--group', '--group=both',
                                '--group=append', '--group=prepend', '-2', '-1', '--skip-fields=2', '-z'] if eol == '\n' else
                               ['-c', '-d', '-u', '-D', '-z', '-i', '-f 1']))
    if eol == '\0':
        opts.append('-z')
    return '@uniq %s in' % ' '.join(opts)


FIXED = ['@cut', '@cut -f', '@cut -f 1 -b 2 in', '@cut -b 1 -d : in', '@cut -c 1 -s in', '@cut -f 1 -d ab in',
         '@cut -f 0 in', '@cut -f 3-1 in', '@cut -f - in', '@cut -f 1-2-3 in', '@cut -f x in', '@cut -b 99999999999999999999999 in',
         '@cut -f 1 nofile', '@cut -f 1 in nofile in', '@cut -f 2 -d "" in', "@cut -f 1 -d '\n' in", "@cut -f 2 -d '\n' in",
         '@cut -f 3000000000,2 -d : in', '@cut --fields=1 --delimiter=: in', '@cut -c 2- in', '@cut -b -2 --output-delimiter=X in',
         '@uniq nofile', '@uniq in out; cat out', '@uniq in out extra', '@uniq -c -D in', '@uniq --group -c in', '@uniq --group -u in',
         '@uniq --all-repeated=x in', '@uniq --group=b in', '@uniq --group= in', '@uniq -f x in', '@uniq -s -1 in', '@uniq -w 1k in',
         '@uniq +1 in', '_POSIX2_VERSION=199209 @uniq +1 in', '_POSIX2_VERSION=200112 @uniq +1 in', '@uniq +x in', '@uniq -- in', '@uniq -1 -2 in', '@uniq -f 1 -2 in', '@uniq -2 -f 1 in',
         'POSIXLY_CORRECT=1 @uniq in -c', '@uniq in -c', '@uniq - < in', '@uniq --check-chars=1 --skip-chars 1 in']


def run(cmd, which):
    c = cmd.replace('@cut', NEBOX + ' cut').replace('@uniq', NEBOX + ' uniq') if which == 'nebox' else cmd.replace('@', '')
    for f in ('out',):
        try:
            os.unlink(os.path.join(d, f))
        except FileNotFoundError:
            pass
    p = subprocess.run(['sh', '-c', c], cwd=d, env=env, capture_output=True, timeout=30)
    err = p.stderr.replace(NEBOX.encode() + b' ', b'')
    err = b'\n'.join(l for l in err.split(b'\n') if not l.startswith(b"Try '"))
    return p.returncode, p.stdout, err


with open(os.path.join(d, 'in'), 'wb') as f:
    f.write(b'a:b:c\nd e\n\n1\t2\t3\nno-delim\nx:y')
cases = []
for c in FIXED:
    cases.append((c, None))
for _ in range(CASES):
    c = cut_case() if rng.random() < 0.5 else uniq_case()
    cases.append((c, open(os.path.join(d, 'in'), 'rb').read()))
bad = 0
for c, data in cases:
    if data is not None:
        with open(os.path.join(d, 'in'), 'wb') as f:
            f.write(data)
    g = run(c, 'gnu')
    n = run(c, 'nebox')
    if g != n:
        bad += 1
        if bad <= 12:
            print('MISMATCH:', c)
            if data is not None:
                print('  in:', data[:200])
            for name, x, y in zip(('status', 'stdout', 'stderr'), g, n):
                if x != y:
                    print('  %s gnu:   %r' % (name, x[:300] if isinstance(x, bytes) else x))
                    print('  %s nebox: %r' % (name, y[:300] if isinstance(y, bytes) else y))
print('cutuniq_compare: %d cases, %d mismatches' % (len(cases), bad))
shutil.rmtree(d)
sys.exit(1 if bad else 0)
