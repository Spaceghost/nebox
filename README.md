# nebox

A toybox-style multicall binary written in Nelua and linked against
[nelibc](https://github.com/Spaceghost/nelibc)'s standalone profile. One
static x86-64 Linux executable, no host libc, no undefined symbols; each
applet is chosen from `argv[0]` (a hard or symbolic link named after the
applet) or from the first operand (`nebox cat FILE`).

## Build and test

Needs Nelua ([Spaceghost/nelua-lang](https://github.com/Spaceghost/nelua-lang)),
Zig (`zig cc`), GNU coreutils as the test reference, and a
[nelibc](https://github.com/Spaceghost/nelibc) checkout with its standalone
archive built. Builds and tests are meant to run in a Linux x86-64 container,
not on a workstation:

```sh
git clone https://github.com/Spaceghost/nelibc ../nelibc
make -C ../nelibc lib-standalone-zig
make NELIBC=../nelibc          # build/nebox
make NELIBC=../nelibc test     # tests/run.sh
```

`tools/remote.sh` does the same inside a remote Incus container: it tars the
tree over ssh and runs `make` there, reading the target from `NEBOX_HOST`,
`NEBOX_CONTAINER`, `NEBOX_DEST` and `NEBOX_NELIBC`:

```sh
NEBOX_HOST=buildbox NEBOX_CONTAINER=nelua tools/remote.sh        # sync, build, test
NEBOX_HOST=buildbox NEBOX_CONTAINER=nelua tools/remote.sh build  # build only
```

`make` compiles `src/nebox.nelua` with Nelua (release mode) through
`zig cc -nostdlib -static`, links the whole nelibc standalone archive, and
fails if `nm -u` reports anything. `make test` installs applet links in a
temp dir and runs every case in `tests/run.sh`: each `same` case executes
one shell command twice from identical fixture trees, once with the
container's coreutils and once with nebox first on `PATH`, and compares
stdout, exit status, and the resulting directory tree.

## Applets

```
[ awk b2sum base32 base64 basename basenc cat chgrp chmod chown cksum cmp comm
cp cut date df dir dirname du echo env expand expr factor false find fold free
grep groups hd head hexdump hostname id install join kill link ln ls md5sum mkdir
mktemp mv nl nproc nsh od paste patch printenv printf pwd readlink realpath
rev rm rmdir sed seq sh sha1sum sha224sum sha256sum sha384sum sha512sum shuf
sleep sort split stat strings sum sync tac tail tee test timeout touch tr true
truncate tsort tty uname unexpand uniq unlink vdir wc which whoami xargs yes
```

`nebox --list` prints the names; `nebox --install [-s] DIR` creates one link
per applet in `DIR`.

## Known limits

Stated here rather than worked around:

- Option parsing follows glibc `getopt_long` (`util.getopt`) for the applets
  listed in `src/nebox/longopts.nelua` and for grep, fold and the coreutils
  ports: options may come after operands unless POSIXLY_CORRECT is set or
  GNU stops at the first operand (basename, tr, timeout, xargs, awk, which),
  long options accept unique abbreviations with glibc's ambiguity rules, and
  a GNU long option nebox does not implement is refused by name ("option
  '--x' is not supported") rather than misparsed. No applet has `--help` or
  `--version` except the coreutils ports. `tests/opts_compare.py` checks 233
  invocations against GNU (output, status, first diagnostic line).
- `chmod` follows GNU chmod.c over a port of gnulib's `modechange.c`
  (`src/nebox/modechange.nelua`): octal and symbolic modes with the umask
  applied when no "who" is given, `u=g`-style copies, `X`, `s`, `t`,
  "-w"-style modes mixed with options, `--reference`, `-R` (readdir order,
  symlinks untouched), `-c`, `-f`, `-v` messages and the "new permissions
  are ..." warning. `mkdir -m` follows mkdir.c and gnulib make_dir_parents
  (umask handling, special bits, `-p` ancestors with u+wx); `install -m` and
  `find -perm` take symbolic modes too. `tests/mode_compare.py`: 4118 random
  cases against GNU, 0 mismatches.
- `tr` is a port of GNU coreutils 9.1 `src/tr.c` in the C locale: escapes
  (with the ambiguous-octal and trailing-backslash warnings), ranges,
  `[:class:]`, `[=c=]`, `[c*n]`/`[c*]` with octal or decimal counts, `-c -C
  -d -s -t`, string2 padding, `[:upper:]`/`[:lower:]` alignment and every
  validation message. `tests/tr_compare.py`: 6116 random specs against GNU,
  0 mismatches.
- `cut` ports cut.c and set-fields.c (-b -c -f -d -s -n -z, --complement,
  --output-delimiter, GNU's list syntax and messages, `-d $'\n'`); `uniq`
  ports uniq.c (-c -d -D[=METHOD] -u -i -f -s -w -z, --group[=METHOD], the
  obsolete -N and +N forms, the OUTPUT operand). `tests/cutuniq_compare.py`:
  3045 random cases against GNU, 0 mismatches.
- `head` ports head.c: GNU's count suffixes, `-n -N`/`-c -N` with its seekable
  and pipe strategies (bounded memory on pipes, the file offset left just
  after the output so `{ head -n 2; cat; } < f` works), -q -v -z, and the
  obsolete `-N[bkmclqvz]` first argument. `tests/head_compare.py`: 1550 cases
  against GNU, 0 mismatches.
- `tail` ports tail.c: `-n`/`-c` with suffixes and `+N`, the obsolete
  `[+-]N[bcl][f]` form (with GNU's _POSIX2_VERSION rules), GNU's file and
  pipe strategies, -q -v -z, and following: `-f`, `-F`/`--follow=name`,
  `--retry`, `--pid`, `-s`, `--max-unchanged-stats`, truncation, rotation,
  removal and reappearance messages, and exit when a piped reader goes away.
  It always polls, as GNU does with `---disable-inotify` (GNU uses inotify
  when it can). `tests/tail_compare.py`: 662 cases including scripted
  follow scenarios against GNU, 0 mismatches.
- `nl`, `comm` and `paste` port nl.c, comm.c and paste.c: nl's styles
  (`a t n pBRE`), -v -i -p -l -s -w -n -d with GNU's in-place delimiter
  quirk and section handling; comm's -123 -z --check-order --nocheck-order
  --output-delimiter (empty means NUL) --total and order warnings; paste's
  -d escapes (\0 for none), -s, -z and repeated "-" operands sharing stdin.
  `tests/nlcp_compare.py`: 6022 random cases against GNU, 0 mismatches.
- `timeout` ports timeout.c: its own process group (or `--foreground`), an
  interval timer and `sigsuspend`, signals forwarded to the command and its
  group followed by CONT, `-k`, `-s` with coreutils' operand2sig (names,
  numbers, exit statuses like 137), `-v`, `--preserve-status`, GNU's exit
  statuses, and re-raising the signal that killed the command with core
  dumps disabled (RLIMIT_CORE). Signal names come from `src/nebox/sig.nelua`
  (gnulib sig2str/str2sig). `tests/timeout_compare.py`: 44 cases, 0
  mismatches.
- `tee` ports tee.c (-a -i -p, `--output-error[=warn|warn-nopipe|exit|exit-nopipe]`,
  unbuffered writes, SIGPIPE ignored only when asked); `mktemp` ports
  mktemp.c with gnulib gen_tempname (-d -p/--tmpdir[=DIR] -q -t -u
  --suffix, getrandom names, GNU's template checks). `util.argmatch` is
  gnulib's XARGMATCH. `tests/teemktemp_compare.py`: 47 cases, 0 mismatches.
- `split` ports split.c: -l/-b/-C, the obsolete -NUMBER, -n N, K/N,
  l/[K/]N and r/[K/]N (round robin with per-file buffering and the EMFILE
  fallback), -a with GNU's automatic suffix widening (`zaaa`), -d/-x and
  `--numeric-suffixes`/`--hex-suffixes=FROM`, `--additional-suffix`, -e, -u,
  -t (including `\0`), `--filter` (`$SHELL -c` with `$FILE`, SIGPIPE blocked,
  exit/signal reporting), `--verbose`, the input-overwrite check and
  gnulib xdectoumax size parsing (`util.xdectoumax`). One deliberate
  difference: GNU 9.1 indexes `--hex-suffixes=FROM` letters past its
  alphabet (undefined behavior); nebox uses the digit's value.
  `tests/split_compare.py`: 135 cases, 0 mismatches.
- `shuf` ports shuf.c with gnulib randint.c, randperm.c (including the
  sparse map for small samples of huge ranges) and randread.c: -e, -i, -n
  (smallest wins, overflow ignored), -o after input is read (in-place
  shuffles work), -r, -z, and `--random-source=FILE` consuming FILE's bytes
  exactly as GNU does, so outputs match GNU byte for byte, reservoir
  sampling for inputs over 8 MiB included. The source is opened only when
  a draw is possible, as in GNU. Without it, bytes come from getrandom
  (GNU seeds ISAAC from getrandom). `tests/shuf_compare.py`: 97 cases, 0
  mismatches.
- `stat` ports stat.c as GNU builds it on Linux (statx): -L, -f, -c,
  `--printf` with its escapes and warnings, -t, `--cached`; every file and
  file-system directive with make_format's per-directive flag filtering
  (including the in-place edit that leaves a stray `s` after `%+6N`'s link
  target), out_epoch_sec's width/precision rules for `%X`-style times,
  negative and pre-1000 timestamps as nstrftime writes them, `%N` under
  `QUOTING_STYLE` (literal unless a `-c`/`--printf` format names `%N`, as in
  GNU), `%m` via find_mount_point and find_bind_mount, `%C` from the
  security.selinux attribute, `%w`/`%W` birth times. New shared modules:
  `src/nebox/quotearg.nelua` (gnulib quotearg_buffer_restyled, all ten
  styles), `src/nebox/mountlist.nelua` (/proc/self/mountinfo with ME_DUMMY
  and ME_REMOTE) and `src/nebox/fstype.nelua` (stat.c's 132 file-system
  magic numbers, generated). SELinux detection is `/sys/fs/selinux/enforce`
  rather than libselinux. `tests/stat_compare.py`: 274 fixed cases plus 400
  random format strings over a shared fixture, 0 mismatches (1500 random
  also run clean).
- `rm` ports rm.c and remove.c over a traversal that hands remove.c's
  logic what gnulib fts (FTS_CWDFD|FTS_NOSTAT|FTS_PHYSICAL) would: lazily
  stat'ed operands with trailing slashes trimmed to one, readdir order,
  d_type instead of a stat for non-directories, FTS_DNR for unreadable
  directories, ancestors marked so their removal is declined quietly. -d,
  -f, -i, -I, `--interactive=WHEN`, -r, -v, `--one-file-system`,
  `--preserve-root[=all]`, `--no-preserve-root` (unabbreviated only),
  `---presume-input-tty`; prompts read replies as gnulib yesno does and give
  unread input back to a seekable stdin. `tests/rm_compare.py`: 134 cases
  on tmpfs fixtures, 0 mismatches (readdir order on ZFS differs between
  identical trees, so the fixtures live on tmpfs). Not exercised by the
  tests: the refusal to remove `/` (not run, for safety), the inode-order
  sort past 10000 entries, and `--one-file-system` across a real mount
  point. Paths are used whole, so names longer than PATH_MAX fail where fts
  would cope.
- `ln` ports ln.c with gnulib force-link.c: hard and symbolic links, -d/-F,
  -f, -i, -L/-P, -n, -r (relpath over canonical names, now shared as
  `canon.relpath`), -s, -t/-T, -v, the atomic first attempt, the "same
  file" and "will not overwrite just-created" checks, replacement through a
  temporary name renamed over the old link, and un-backup when the new link
  fails. Backups (-b, `--backup=CONTROL`, -S, `VERSION_CONTROL`,
  `SIMPLE_BACKUP_SUFFIX`) come from `src/nebox/backup.nelua`, a port of
  gnulib backupfile.c (numbered names found by scanning the directory, with
  its string arithmetic) for cp, mv and install to share.
  `tests/ln_compare.py`: 149 cases, 0 mismatches.
- `df` ports df.c over the mountinfo reader, gnulib fsusage (statfs) and
  `src/nebox/human.nelua`, a port of gnulib human.c (integer arithmetic
  when block sizes divide, long double otherwise, ceiling/floor/nearest
  rounding, autoscaling, SI and IEC suffixes, human_options with
  `--block-size`, `DF_BLOCK_SIZE`, `BLOCK_SIZE`, `BLOCKSIZE` and
  `POSIXLY_CORRECT`). All options including `--output[=FIELDS]`, `--total`,
  -t/-x/-F; the duplicate-device filter, over-mount detection, device-node
  and FILE lookups, UUID device names resolved, GNU's column widths.
  `util.xstrtoumax_base` (strtoumax base 0) and `util.xstrtol_msg` are the
  shared number parser and its xstrtol_fatal messages. `tests/df_compare.py`:
  357 cases against the container's live mount table (rerun when a busy file
  system's usage moves between the two runs), 0 mismatches.
- `du` ports du.c over a traversal that gives process_file what gnulib fts
  gives it (FTS_NOSTAT entries re-stat'ed as with FTS_AGAIN, -P/-L/-D/-H,
  -x, cycle detection under -L, FTS_DNR after the preorder visit), with
  hard links counted once, `--exclude`/-X as gnulib exclude.c matches
  (literal patterns as strings, wildcard ones through nelibc fnmatch, at
  every '/' boundary), `--files0-from`, `--threshold`, `--inodes`, `--time`
  and `--time-style`/`TIME_STYLE` through the nstrftime port, sizes through
  human.nelua, and GNU's bare "write error" after a failed per-line flush.
  `tests/du_compare.py`: 238 cases, 0 mismatches. Not exercised: the inode
  sort past 10000 entries and the cycle warning, which needs a bind-mount
  loop.
- `chown` and `chgrp` port chown.c, chgrp.c and chown-core.c with gnulib
  userspec.c over `src/nebox/fts.nelua`, a shared iterator modeled on
  gnulib fts_read/fts_build/fts_stat (PHYSICAL, LOGICAL, COMFOLLOW, NOSTAT,
  XDEV, DEFER_STAT, cycle detection for LOGICAL and TIGHT_CYCLE_CHECK,
  SKIP/AGAIN, DNR/ERR). -c -f -h -v -R -H -L -P, `--dereference`, `--from`,
  `--reference`, `--preserve-root`, restricted_chown's fchown path under
  `--from`, every describe_change message (including "retained as" showing
  the old owner, as GNU's printf arguments do). One deliberate difference:
  when a symlink can't be dereferenced GNU describes the failed change from
  an uninitialized stat buffer; nebox shows the link's own owner.
  `tests/chown_compare.py`: 273 cases, 0 mismatches, run both as an
  ordinary user and as root.
- `cp` ports cp.c over `src/nebox/copy.nelua`, a port of copy.c and
  cp-hash.c that mv and install will share: copy_internal's same-file,
  overwrite, update and backup rules (backup.rename for numbered names),
  copy_reg with copy_file_range, FICLONE reflinks, SEEK_DATA/SEEK_HOLE
  extent copies and hole punching for `--sparse`, the dangling-symlink
  refusal, directories copied in inode order as gnulib savedir sorts them,
  hard links preserved through the dev/ino map, special files, ownership,
  mode and timestamp preservation with GNU's temporary restrictive modes,
  and user/trusted xattrs copied as libattr does under /etc/xattr.conf's
  defaults. Every cp option, including `--parents` (make_dir_parents_private
  and re_protect), `--attributes-only`, `--copy-contents`, `--no-preserve`,
  `--remove-destination` and `--strip-trailing-slashes`. Not supported:
  SELinux contexts (`-Z`/`--context` warn as GNU does without SELinux) and
  ACLs beyond copying a source's system.posix_acl_* attribute; `--update`
  compares nanosecond timestamps without gnulib utimecmp's resolution
  probing.
  `tests/cp_compare.py`: 175 cases on tmpfs, 0 mismatches as an ordinary
  user and as root.
- `mv` ports mv.c over copy.nelua, with remove.c's rm () (exported from the
  rm port as `nebox_rm_for_mv`) removing the source after a cross-device
  copy: -b -f -i -n -S -t -T -u -v, `--strip-trailing-slashes`, the initial
  RENAME_NOREPLACE attempt for two operands, copy-into-self handling.
  `tests/mv_compare.py`: 116 cases, 22 of them across file systems (tmpfs to
  ZFS), 0 mismatches as an ordinary user and as root.
- `install` ports install.c over copy.nelua with gnulib mkancesdirs,
  make_dir_parents and dirchownmod (whole paths instead of savewd's chdir
  walk, the failing-component message included): -b -c -C -d -D -g -m -o
  -p -s -S -t -T -v, `--strip-program`, need_copy's comparisons, the strip
  child, umask 0. `--preserve-context` and `-Z`/`--context` warn as GNU does
  without SELinux. `tests/install_compare.py`: 100 cases, 0 mismatches as an
  ordinary user and as root.
- `touch` ports touch.c with gnulib posixtm.c (-t, and the obsolete
  MMDDhhmm[YY] operand when `_POSIX2_VERSION` is below 200112) and
  parse_datetime (`util.getdate`) for -d, relative to the -r file's times
  when both are given: -a -c -d -f -h -m -r -t `--time`, "-" for standard
  output, "-d now" treated as no date. -d is the parse-datetime port
  described under `date`, -t and the operand use its glibc mktime port.
  `tests/touch_compare.py`: 113
  cases, 0 mismatches.
- `truncate` ports truncate.c: -c -o -r -s with the < > / % + - modifiers,
  sizes through the new `util.xdectoimax` (gnulib's signed xdectoimax),
  reference sizes, the overflow and division-by-zero checks.
  `tests/truncate_compare.py`: 167 cases, 0 mismatches.
- `echo` ports echo.c: options only when every character after '-' is e, E
  or n ("-neE" is options, "--" and "-x" are text), POSIXLY_CORRECT's
  leading "-n" rule, and its escape table (\c, \e, \xHH, \NNN and \0NNN).
- `nproc`, `sleep` and `printenv` port nproc.c (gnulib's OMP_NUM_THREADS
  and OMP_THREAD_LIMIT rules, the affinity mask, /sys/devices/system/cpu for
  `--all`), sleep.c (C-locale strtod numbers including inf and hex floats,
  one s/m/h/d suffix, endless sleep for infinity) and printenv.c (-0, "a=b"
  operands skipped). `tests/smallcore_compare.py`: 68 cases, 0 mismatches.
- `tac` ports tac.c: -b, -r, -s, tac_seekable's backward scan with the
  separator kept in front of the buffer as a sentinel and the buffer
  doubling for long records, non-seekable input and terminals copied to a
  temporary file in $TMPDIR first. -r searches backward the way glibc
  re_search does with re_syntax_options 0 (Emacs syntax, translated for
  nebox's engine: \( \) \| groups, + and ? operators, no intervals or
  character classes, context-dependent anchors, glibc's wording for a
  pattern ending in "[" ); one difference remains: [^...] does not match a
  newline. `tests/tac_compare.py`: 55 fixed cases plus 300 random inputs
  from files and pipes, 0 mismatches.
- `tsort` ports tsort.c: Knuth's algorithm over the items in strcmp order
  (the in-order walk of GNU's balanced tree), successor lists newest first,
  each cycle listed on standard error before a relation is dropped to break
  it, read errors taken as end of input. `tests/tsort_compare.py`: 19 fixed
  cases plus 400 random graphs, 0 mismatches.
- `test` and `[` port test.c: POSIX's one-to-four-argument rules, -a/-o
  expressions with parentheses and !, integer comparisons on decimal
  strings of any length (gnulib strintcmp, `-l STRING` lengths), -nt -ot
  -ef, every unary file test (euidaccess for -r -w -x), status 2
  diagnostics. The shell's `test` builtin keeps dash's messages
  (`sh_builtin_test`). `tests/test_compare.py`: 62 fixed and 3000 random
  argument vectors through both forms, 0 mismatches (8000 random also run
  clean).
- `env` ports env.c: -i and `-`, -u applied after all options, NAME=VALUE
  through putenv, -0, -C, -v debug messages, -S split strings (quotes,
  \_ \c and the C escapes, ${VARNAME}, # comments, GNU's errors)
  re-scanned as options, and --default-signal, --ignore-signal,
  --block-signal and --list-signal-handling over signals 1..64 (32 and 33
  skipped the way glibc's sigaction refuses them).
  `tests/env_compare.py`: 124 cases, signals checked through
  --list-signal-handling and the child's /proc/self/status, 0 mismatches.
  One difference: an operand with an empty name ("=x") fails, because
  nelibc's putenv refuses it with EINVAL as musl does (glibc adds it).
- `expr` ports expr.c: the same recursive-descent evaluator, short-circuit
  `|` and `&` that skip arithmetic and regex errors, arbitrary-precision
  integers (a decimal bignum in place of GMP) with truncating `/` and `%`,
  strintcmp comparisons, `match`/`substr`/`index`/`length` and `+`
  quoting, anchored BRE matches with GNU's syntax bits (empty ranges,
  `\{,n\}`, RE_DUP_MAX 32767) and glibc's compile messages, exit
  statuses 0-3 (a match over nebox's thread bound fails with status 3 where
  GNU backtracks for hours). `tests/expr_compare.py`: 175 fixed and 3000 random
  expressions, 0 mismatches.
- `factor` keeps factor.c's interface and output over its own factoring:
  operands of any length (digits after spaces and one '+'), standard input
  read token by token as it arrives, GNU's lbuf (numbers below 2^127 are
  written in 512-byte line batches, larger ones at once, so the output
  order through a pipe is GNU's). Below 2^64: trial division,
  deterministic Miller-Rabin, Pollard-Brent with mulq/divq; up to 2^128:
  Montgomery arithmetic; beyond: a base-2^32 bignum. Primality above 2^64
  is Miller-Rabin over 25 prime bases, not GNU's Lucas proof, and the
  bignum path is slower than GMP. `tests/factor_compare.py`: 72 fixed and
  600 random numbers up to about 2^200 plus pipe and write-error cases,
  0 mismatches.
- `cmp` ports GNU diffutils 3.8 cmp.c: -b, -i SKIP and SKIP1:SKIP2 (with
  gnulib's suffixes and bases), -l with its column width, -n, -s, the SKIP
  operands, lseek or read-and-discard skipping, the same-name, same-inode
  and (with -s) different-size shortcuts, silence when standard output is
  /dev/null, POSIX's "differ: char" message in the C locale, every "EOF
  on" form and stdio's write-error messages. `tests/cmp_compare.py`: 110
  fixed and 400 random cases, 0 mismatches.
- `sort` ports sort.c in the C locale (`src/nebox/applets/sort.nelua`):
  keys from begfield/limfield with GNU's inheritance of global options,
  -b -d -f -g -h -i -M -n -R -r -V and `--sort=WORD` (strnumcmp, where a
  0x80 byte counts as the thousands separator as it does in GNU's C
  locale; filevercmp; strtold; getmonth; -R as the MD5 of the key under a
  state seeded from 16 bytes of `--random-source` or getrandom, so a given
  source gives GNU's order), the last-resort comparison unless -s or -u,
  the same stable merge sort, -u keeping the first line of an equal run,
  -c/-C/`--check=` with GNU's disorder report, -m through mergefps
  (streamed, ties to the earlier file, `--batch-size` intermediate merges
  done in memory with GNU's grouping, an output that is also an input
  copied first), -o created before and truncated after the input is read,
  -t (`\0`, multi-character and incompatible tabs), -z, obsolete `+POS1
  -POS2` keys under GNU's `_POSIX2_VERSION`/POSIXLY_CORRECT rules,
  `--files0-from`, every key-parse and ordering-incompatibility message,
  `--debug` (key underlining with mbsnwidth's C-locale widths, and the
  zero-width, leading-blank, multi-field numeric, field-separator, ignored
  option and `-r` warnings), and GNU's "open failed", "cannot read",
  "read failed", "write failed"/"fflush failed" plus "write error"
  messages and statuses. `tests/sort_compare.py`: 340 fixed and 500 random
  cases, 0 mismatches (5 more runs of 3000 random cases with other seeds
  also gave 0). Differences:
  - nebox sorts in memory in one thread and never makes temporary files.
    -S (size suffixes and `%` of physical memory), -T, `--parallel`,
    `--batch-size` and `--compress-program` are validated with GNU's
    messages and limits but change nothing else, except that
    `--batch-size` shapes -m as in GNU and a huge `--parallel` runs out of
    memory where GNU does (allocating GNU's per-thread merge structures).
    GNU spills inputs larger than its buffer to temporary files and merges
    them; that gives the same output whenever the ordering is consistent,
    but a compress program is never run, so a missing one is not reported.
  - Only the C locale: `--debug` always reports simple byte comparison.
  - Two NaNs under -g: GNU memcmps the whole 16-byte long double, whose six
    padding bytes its compiler leaves uninitialized (sort.c's memset is a
    dead store), so their order and whether -u merges them depend on the
    stack; nebox compares the ten value bytes. nelibc's strtold also keeps
    no `nan(...)` payload and accepts `-` inside the parentheses, so such
    NaNs order differently from glibc's. nelibc's strtold reports no
    conversion for `0x` without hex digits; sort converts it as `0`, as
    glibc does.
  - A character offset that overflowed (2^64 - k) makes GNU's pointer
    arithmetic step back k bytes; nebox does the same within the line but
    stops at its start where GNU reads the bytes before it.
  - `--help` omits GNU's closing links; `--version` prints nebox's line.
- `od` ports od.c: every -t type and size (d o u x as C S I L or 1 2 4 8,
  f as F D L or 4 8 16, a, c, the z trailer), the old-style letters, -A,
  -j and -N with od's multipliers, -S, -v, -w, --endian, --traditional
  and the old [+]OFFSET[.][b] [LABEL] operands, GNU's padding of mixed
  types, '*' for repeated blocks, skipping by size arithmetic, lseek or
  reading, gnulib ftoastr for floats (the shortest %g that reads back),
  and unbuffered reading under -N so a shared pipe keeps its rest.
  `tests/od_compare.py`: 170 fixed and 500 random cases, 0 mismatches
  but one known case: a pseudo-denormal long double (exponent 0 with the
  integer bit set) prints as the FPU reads it, where glibc's printf drops
  the integer bit.
- `hexdump` (and `hd`, which is `hexdump -C` plus any other options) ports
  util-linux 2.38.1 hexdump.c, hexdump-parse.c, hexdump-display.c and
  hexdump-conv.c (`src/nebox/applets/hexdump.nelua`, C locale): -b -c -C
  -d -o -x and the default format, the whole -e/-f format language
  (iteration and byte counts, %d %i %o %u %x %X %e %f %g %E %G %c %s with
  every flag, width and precision passed to snprintf as hexdump rewrites
  them, %_a/%_A in d/o/x, %_c %_p %_u, escape() including its quirk of
  not copying unescaped characters after an escape, the last unit
  repeated to fill the block, the trailing-blank cut on the last
  iteration, blank padding past the end of data), `_L[...]` color units
  (names, values, strings, offsets and ranges, `!`) under -L/--color with
  util-linux's terminal-colors.d enable/disable scoring and a terminfo
  "colors" check for auto mode, -n/-s with parse_size suffixes and
  fractions, -v and '*' suppression, files opened as freopen() does (a
  failed operand closes stdin: "all input file arguments failed"), stdio's
  buffered reads, fseek's skip and the offset glibc leaves on stdin at
  exit, every diagnostic, --help/--version and close_stdout's write-error
  rules. glibc's printing of an unknown conversion (a second '.' in a
  byte-count unit, a format that ends inside a conversion) is emulated in
  hexdump because nelibc's snprintf prints nothing for it, and so is the
  '.' that glibc keeps in `%#.0f` for |x| >= 2^64 and nelibc drops.
  `tests/hexdump_compare.py`: 356 fixed cases and 3000 random -e formats
  over random inputs with -s/-n/-v, 0 mismatches. Differences, all where
  the C code is undefined:
  - A '%' (with only flag/width characters) or `%_a`/`%_A` at the very end
    of a format unit, which the C code can produce through escape()'s
    quirk, makes it read past the string into the heap; nebox reads zeros
    and then an `A` there (the common case on the reference: "bad
    conversion character %A"), the reference's bytes vary with the heap.
  - `%s` with a byte count and no or a larger precision reads past the
    block when the data has no NUL; nebox reads zeros there.
  - A width, precision or count that overflows a long makes the C code
    dereference NULL; nebox kills itself with SIGSEGV at the same point.
  - A color range wider than 4 bytes on a value condition overruns an int
    in color_cond(); nebox compares 4 bytes. A range on an address unit
    (byte count 0) loops forever in the C code; nebox stops cloning.
  - A value condition on a `%_A` unit dereferences NULL in the C code;
    nebox kills itself with SIGSEGV.
  - -n with a value of 2^63 or more (a negative ssize_t other than -1)
    makes the C fread overrun the block; nebox reads without a limit.
  - A size ending in a '.' with no digits after it ("1.", "1.0") reads
    the byte after the argument's NUL in parse_size(); nebox takes it as
    non-NUL, which gives the reference's usual "Invalid argument".
  - With no operand and a read error on stdin, the C code names
    `argv[optind - 1]`; nebox uses the last argument, or the applet name
    for argv[0].
- `rev` ports util-linux 2.38.1 text-utils/rev.c in the C locale, where
  glibc's fgetws takes bytes 0-127 as characters and fails with EILSEQ on
  any other byte: the BUFSIZ buffer that doubles for long lines and stays
  doubled (each doubling tried as an untouched allocation, so an
  impossible one fails with "cannot allocate N bytes" as xrealloc does),
  wcslen deciding the length so a NUL cuts the line and pulls the next
  one in, lines starting with NUL dropped, the in-place reversal and
  fputws up to the first NUL (which shows what a failed read left in the
  buffer), "FILE: LINES: strerror" for conversion and read errors, "cannot
  open", SIGINT/SIGTERM exiting 0, close_stdout's "write error" (with
  strerror only when the last flush failed; EBADF ignored), --help, and
  -V/--version. util-linux 2.38.1 has no -0/--zero, so neither does nebox.
  `tests/rev_compare.py`: 93 fixed and 400 random cases, 0 mismatches.
  Differences:
  - `--version` prints nebox's line.
  - Memory past what was read is taken to be zero, as fresh glibc heap
    and mmap memory is; where glibc's realloc hands back reused memory,
    the bytes a failed read exposes can differ.
  - A buffer size that wraps size_t (some 50 NUL-merged lines without an
    address-space limit) is undefined in rev.c; nebox stops reading.
- `strings` ports GNU binutils 2.40 binutils/strings.c with libiberty's
  expandargv/buildargv: the whole file by default (-a, and "-" before
  later files; "-" never means standard input), -d with BFD's ELF reader
  (elf_object_p's header and section-table checks, bfd_section_from_shdr's
  choice and order of sections, the corrupt e_shstrndx warning, a file
  with no loaded section scanned whole), -T (BFD tries every target when
  the named one does not match; `binary` takes the whole file as one
  section; an unknown name scans the whole file), -e s/S/b/l/B/L with
  get_char/unget_part_char, -w, -n/--bytes and -NUM through strtoul with
  base 0 and the unsigned-int truncation (`-n 4294967297` is 1, `-n -1`
  never prints), -NUM read back from getopt's permuted argv as strings.c
  does (`strings f1 -3` takes 1 from "f1"; `-5a` reads "trings"), -t
  o/d/x and -o, -f, -s, -U d/l/e/i/x/h with print_unicode_stream's and
  print_unicode_buffer's walks and their quirks (`locale` prints the lead
  byte only, `escape` prints 4-byte sequences with GNU's arithmetic, a
  string starting at a put-back byte gets GNU's address 2^32 - 1 too
  large), empty -t/-e arguments judged by the byte after them in argv's
  memory, @file response files (quotes, backslashes, nesting, the 2000-file
  limit, directories, files removed when empty), every usage path on
  stdout or stderr, binutils' file messages, stdio buffering and no
  write-error check. `tests/strings_compare.py`: 1048 fixed and 400 random
  cases (ELF executables, objects, a shared library, a big-endian ELF32,
  broken ELF headers, an archive, UTF-8/16/32 text), 0 mismatches.
  Differences:
  - `-v`/`-V`/`--version` print nebox's line; the usage on stdout has no
    bug-report line.
  - -d recognizes ELF only. Files BFD reads as PE/COFF, S-records,
    Intel/Tektronix hex, PDB or LTO plugin objects are scanned whole.
    ELF section types BFD rejects or warns about, invalid section-name
    offsets, sections that extend past the end of the file and BFD's
    other diagnostics for malformed ELF are not reproduced.
  - An empty -t/-e argument from a response file reads heap memory in
    GNU; nebox treats it as followed by a non-NUL byte.
  - `-n` values at or near 2^32 make GNU's buffers overflow (malloc of
    size+1 or 4*size+1 wraps); nebox allocates as needed.
- `groups` ports GNU coreutils 9.1 groups.c and group-list.c over nelibc's
  getpwnam/getpwuid/getgrgid/getgrouplist: the current process (real and
  effective gid, then getgroups through gnulib mgetgroups) or "NAME : "
  and each user's groups, "'x': no such user", "cannot find name for
  group ID N" with the number printed, status 1 for either, write errors,
  --help without GNU's closing links and --version with nebox's line.
  `tests/groups_compare.py`: 40 cases as a user and 54 as root, including
  fixture passwd/group files bound in a private mount namespace and
  setpriv-set real/effective/supplementary gids, 0 mismatches.
- `which` ports the debianutils 5.7 which script as dash runs it: dash's
  getopts for `-a` ("Illegal option -X" and the usage line, status 2;
  `--` ends options, `-` and the first name stop them), `[ -f ] && [ -x ]`
  with faccessat(AT_EACCESS), PATH split as dash splits it with IFS=:
  after the script's trailing-colon fix (empty elements are ".", an
  empty PATH searches nothing, an unset one uses dash's default), -a,
  status 1 when a name is missing or none is given, each line written at
  once, a write error as dash's "printf: I/O error" with status 1, and a
  non-empty KSH_VERSION failing the script's `print` with status 127.
  debianutils 5.7 has no -s. `tests/which_compare.py`: 81 cases, 0
  mismatches. One difference: the script names itself by the path dash
  was given ($0, normally /usr/bin/which); nebox says `which`.
- `sync` ports GNU coreutils 9.1 sync.c: sync(2) without operands; per
  file an O_RDONLY|O_NONBLOCK open (O_WRONLY when that fails, reporting the
  first errno), O_NONBLOCK cleared, then fsync, -d/--data fdatasync or
  -f/--file-system syncfs; "error opening", "couldn't reset non-blocking
  mode", "error syncing" and "failed to close", the -d/-f conflict and
  "--data needs at least one argument", --help without GNU's closing links
  and --version with nebox's line. `tests/sync_compare.py`: 182 cases as
  a user and as root (FIFOs, sockets, devices, /proc, unreadable files),
  0 mismatches. Whether data reaches the disk is not observable there and
  was not tested.
- `free` ports procps-ng 4.0.2 src/free.c and the meminfo.c reader: one
  read of up to 8191 bytes of /proc/meminfo parsed as meminfo.c parses it
  (a line without a colon ends parsing, strtoul after the colon, the last
  duplicate wins), its derived values (MemAvailable falling back to
  MemFree, used as total minus available or free, buff/cache with
  SReclaimable, Low* defaulting to Mem*, clamped used columns), scale_size
  in the same types (kB times 1024 as long long, float bases, -h's "%.1f"
  of a float rounded half to even), -b -k -m -g --tera --peta --kilo
  --mega --giga --tebi --pebi with "Multiple unit options don't make
  sense.", -h --si -l -t -v -w, -s (strtod_nol_or_err, '.' or ',') and -c
  with their messages, int truncation and repeats, usage on stderr for
  bad options and operands, the error for an empty file (the one for a
  missing file is ported but untested),
  --help, and close_stdout's "write error". procps-ng 4.0.2 has no
  -L/--line. `tests/free_compare.py`: 836 fixed and 300 random cases on
  fixture files bound over /proc/meminfo in a private mount namespace
  (plus the live file with changing columns masked), 0 mismatches.
  Differences:
  - -V/--version prints nebox's line.
  - procps re-reads the file when a second boundary passes between two
    fields of one report; nebox reads once per report.
- `xargs` ports GNU findutils 4.9.0 xargs.c and buildcmd.c
  (`src/nebox/applets/xargs.nelua`, C locale): read_line's quote,
  backslash, blank-line and trailing-blank (-L/-l continuation) rules, the
  NUL warning and the unmatched-quote errors, read_string for -0 and -d
  (with GNU's `\a`..`\v`, `\\`, octal and hex escapes and their messages;
  a delimiter byte above 127 never matches, as in GNU where it is a
  negative char), -E/-e, the command line built in an ARG_MAX-derived
  buffer exactly as buildcmd.c builds it (the default 128 KiB, -s with its
  range messages, -n, -L/-l, -x, the argument-count limit, -I/-i insertion
  and "command too long", the "cannot fit single argument" and "argument
  list too long" errors), the mutual-exclusion warnings, --show-limits from
  sysconf(_SC_ARG_MAX) and the environment size (and "environment is too
  large for exec"), E2BIG retries with update_limit's bisection (also
  driven by the `__GNU_FINDUTILS_EXEC_ARG_COUNT_LIMIT`/`_LENGTH_LIMIT` test
  variables), -r, -t and -p with quotearg's shell-escape quoting (including
  its quirk of starting a re-scanned argument inside `$'...'`), the
  /dev/tty prompt, -a, -o, -P with slots, --process-slot-var and
  SIGUSR1/SIGUSR2, and exit statuses 123/124/125/126/127 with GNU's
  messages. GNU's two exit handlers run on every exit path: waiting for
  all children may replace the status (an earlier failure turns a later
  127 or 124 into 123), a child that exits 255 while they run exits
  through the nested handler, a seekable standard input is left just
  after the last byte xargs consumed, and read errors on it are reported
  as "error closing file". A child that fails before exec (-o without a
  terminal, an invalid test variable) trips the same `getpid () ==
  parent` assertion and SIGABRT that GNU's does. `tests/xargs_compare.py`:
  359 fixed cases, 14 through a pseudo-terminal (-p answers, -o) and 300
  random inputs with random options, 0 mismatches (5 more runs of 1500
  random cases with other seeds also gave 0). Differences:
  - `--help` omits GNU's bug-report paragraph; `--version` prints nebox's
    line.
  - nelibc's execvp searches PATH for an empty command name; xargs fails
    that name with ENOENT itself, as glibc's execvp does.
- `find` ports GNU findutils 4.9.0 find (`src/nebox/applets/find.nelua`,
  C locale): ftsfind.c's traversal over a port of gnulib fts as find opens
  it (`src/nebox/gfts.nelua`: FTS_CWDFD's virtual working directory and
  descriptor ring, FTS_NOSTAT with d_type, FTS_TIGHT_CYCLE_CHECK,
  FTS_VERBATIM, -H/-L/-P, -xdev, readdir order with the inode sort past
  10000 entries where fstatfs is not tmpfs/NFS/CIFS (always under -L) and
  batches of 100000 entries), so output order, paths longer than PATH_MAX,
  unreadable and unsearchable directories, symlink loops and directory
  loops come out as in GNU; parser.c with every option, test and action,
  its argument checks and messages and the warnings (global options after
  tests, -d, `/` in -name, -path ending in `/`, -perm /000, -warn/-nowarn,
  enabled when standard input is a terminal); tree.c's precedence parser,
  the implicit `( ... ) -print`, cost and success-rate estimates, -O0..-O3
  reordering and arm swaps (so the order of evaluation, and with it stat
  calls and diagnostics, is GNU's), `-D tree`, `opt`, `search`, `stat`,
  `rates`, `exec`, `time`, `all` and `help`; pred.c's tests (-amin/-atime/
  -cmin/-ctime/-mmin/-mtime/-used with fractions and -daystart, -newer,
  -anewer, -cnewer, -newerXY with parse_datetime dates, -perm through
  modechange, -size units and rounding, -user/-group/-uid/-gid/-nouser/
  -nogroup, -readable/-writable/-executable, -fstype from the mount list,
  -links, -inum, -samefile, -type/-xtype lists, -empty, -lname/-ilname/
  -name/-iname/-path/-ipath/-wholename/-iwholename through a port of
  glibc's fnmatch (`src/nebox/fnmatch.nelua`), -regex/-iregex through
  `regex.compile_syntax`, which reads every glibc syntax bit of the 13
  -regextype names as re_compile_pattern does, RE_ICASE included); the
  actions -print, -print0, -printf/-fprintf (every directive, flag, width,
  escape and warning, format_date's nanosecond insertion, glibc strftime's
  conversions), -fprint/-fprint0/-fls with sharefile's one stream per file
  and close order, -ls (listfile.c's growing columns), -exec/-execdir/-ok/
  -okdir with `;` and `+` through a per-predicate port of buildcmd.c (128
  KiB batches, the `__GNU_FINDUTILS_EXEC_ARG_*` test variables, execdir
  batches flushed when the depth changes, PATH safety checks, the -ok
  prompt and yesno on standard input, -ok/-okdir children started with
  standard input closed as GNU's open_safer leaves it),
  -delete with its implied -depth and the -prune conflict, -prune, -quit;
  -files0-from; the exit status (1 after any diagnostic, -exec `+`
  failures) and close_stdout at exit. `tests/find_compare.py`: 2686 fixed
  cases, 18 on a pseudo-terminal, 2000 random expressions and 1487 random
  -printf formats, regular expressions and patterns against GNU, 0
  mismatches; as root (other owners, unreadable directories readable)
  6205 cases, 0 mismatches. Differences:
  - `--help` omits GNU's bug-report paragraph; `--version` prints nebox's
    line and GNU's "Features enabled" line.
  - No SELinux: -context is refused as GNU refuses it with SELinux
    disabled, and `%Z` reads the `security.selinux` attribute directly.
    No birth times (glibc's stat has none), as in GNU on Linux.
  - A backslash before `%` that is not an escape leaves a stray conversion
    in the text GNU passes to printf with the directive's single argument
    (undefined behavior); nebox passes the same text to nelibc's snprintf,
    so such output can differ.
  - Output files get a 4096-byte buffer; glibc sizes it from st_blksize, so
    two streams writing to one file (`-fprint /dev/fd/1` beside stdout)
    can interleave differently.
  - `src/nebox/fts.nelua` (used by chown and grep) walks whole paths without
    FTS_CWDFD, and xargs keeps its single-instance buildcmd; find has its
    own ports of both.
  - Not exercised by the tests: fts failing to return to a parent
    directory, readdir errors in mid-directory, the "environment is too
    large" and fork failures, and -ok on a terminal.
- `readlink` and `realpath` port readlink.c, realpath.c and relpath.c over
  a port of gnulib's `canonicalize_filename_mode` (`src/nebox/canonicalize.nelua`):
  -e -f -m, -L -P -s, -n -q -v -z, `--relative-to`/`--relative-base`, GNU's
  trailing "/", "/." and "/.." checks and symlink-loop detection.
  `tests/realpath_compare.py`: 2042 random cases over a symlink fixture, 0
  mismatches.
- `wc` ports wc.c (C locale): -c and -m as separate columns in GNU's order,
  compute_number_width, `--files0-from`, the bytes-only path that honours
  the file offset, counts printed after read errors. `id` ports id.c and
  group-list.c over nelibc's passwd/group functions: USER operands, -u -g
  -G -n -r -z, GNU's conflicts (no SELinux, so -Z is refused as on a
  non-SELinux kernel). `touch --time=WORD` and `-f` are accepted.
  `tests/wcid_compare.py`: 1546 cases, 0 mismatches.
- `expand` and `unexpand` port expand.c, unexpand.c and expand-common.c:
  tab lists with `/N` and `+N`, the obsolete `-N` forms, -i, -a,
  `--first-only`, lines continuing across files. `tests/expand_compare.py`:
  2000 random cases, 0 mismatches.
- `cat` follows GNU cat.c (-b -e -n -s -t -u -v -A -E -T; numbering,
  squeezing and a pending CR carry across files; "input file is output
  file"); `fold` follows fold.c (-b, -s, -w, obsolete -NUM); `rmdir` follows
  rmdir.c (-p, -v, --ignore-fail-on-non-empty); `mkdir -v` reports each
  directory; `wc -L` measures tabs and control characters as GNU does.
- `awk` is POSIX.1-2017 awk (`src/nebox/awk/`: lexer, parser to a tree,
  tree-walking interpreter): all statement forms, range patterns, every
  `getline` form, `print`/`printf` with `>` `>>` `|` and `close()`,
  `system()`, user functions with array-by-reference and recursion,
  CONVFMT/OFMT, numeric strings, `RS=""` paragraph mode, `-F -f -v`,
  `var=value` operands, ENVIRON/ARGV, and the POSIX builtins. The reference
  in `tests/awk.sh` is GNU Awk 5.2.1 `--posix` (mawk 1.3.4 as a second
  opinion); the regex engine is the shared `src/nebox/regex.nelua`.
  Extensions kept because gawk --posix accepts them: `nextfile`,
  `delete array`, `length(array)`, printf `*` width/precision.
  Not supported: every other GNU extension (`**`, `fflush`, `gensub`,
  `strftime`, `systime`, `BEGINFILE`, `IGNORECASE`, `-e`, long options),
  a regex `RS` (only the first character of RS is used),
  locales and multibyte characters (strings are bytes, collation is byte
  order), `[/]` inside a regex literal (the first unescaped `/` ends it),
  and hexadecimal/`inf`/`nan` spellings in numeric strings (they are
  strings; gawk treats "0x1A" as 26). Choices where references disagree:
  every error exits 2 (gawk exits 1 for syntax errors and division by
  zero); `cmd | getline` increments NR as the POSIX table says (gawk and
  mawk do not); `substr` truncates its arguments and clamps a start below
  1 to 1 without shortening the length (gawk --posix and the One True AWK;
  mawk shortens); a field past NF compares as the empty string, as gawk and
  mawk do, not as the uninitialized value; `system()` and `close()` of a
  pipe return the exit status (gawk --posix returns the raw wait status);
  an empty FS or split separator splits into characters (undefined in
  POSIX; gawk --posix keeps the record whole for FS but splits for
  `split()`); unknown string escapes drop the backslash (gawk; mawk keeps
  it); `srand()` reports 1 before the first call (gawk) and `rand()` is an
  xorshift64* generator, so its sequence matches no other awk. Memory for
  string temporaries is not reclaimed until exit; records and fields are
  views into a reused buffer.
- `nsh` is `sh` under its own name with friendlier defaults when the
  environment does not set them: a colored PS1 showing the current
  directory's name (`~` at `$HOME`), history in
  `${XDG_STATE_HOME:-~/.local/state}/nsh/history`, and
  `${XDG_CONFIG_HOME:-~/.config}/nsh/rc` as `ENV` when it exists.
- `sh` is a POSIX.1-2017 shell (`src/nebox/sh/`: lexer,
  parser to a tree, tree-walking interpreter). `tests/sh.sh` compares it
  with dash 0.5.12 and pins, as `expect`/`shx` cases, the places where
  nebox follows POSIX or a deliberate choice instead. Implemented: `-c`,
  `-s`, script operands and scripts on standard input (read no further
  than the command being run); options `-a -b -C -e -f -h -n -u -v -x` and
  their `-o` names (`-b`, `-h`, `ignoreeof` and `nolog` are accepted and
  have no effect; dash rejects `-h`); the whole
  grammar (pipelines, `!`, `&&`/`||`, `&`, subshells, brace groups, `if`,
  `while`, `until`, `for`, `case`, functions, here-documents including
  `<<-`, every redirection operator and `noclobber`); aliases; every
  parameter expansion form (`${x:-w}` ... `${x%%p}`, `${#x}`, applied per
  field to `$@`), command substitution in both forms, 64-bit arithmetic
  expansion with all C operators and assignments, tilde expansion, field
  splitting and pathname expansion; the special built-ins (`: . break
  continue eval exec exit export readonly return set shift times trap
  unset`) and the regular ones a shell must provide (`alias cd command
  echo false getopts hash kill pwd read test [ true type umask unalias
  wait`, plus `printf` through the `printf` applet); traps, `set -e`
  exceptions, `$!`/`wait` for asynchronous lists, `LINENO`, and
  diagnostics as `sh: line N: ...`. Interactive use (`-i`, or no command
  operand with a terminal on stdin and stderr; `src/nebox/sh/interactive.nelua`
  and `lineedit.nelua`, tested on a pseudo-terminal by
  `tests/sh_interactive.py`): PS1 (parameter, command and arithmetic
  expansion, then `!`) and PS2 prompts on stderr; errors that end a
  non-interactive shell return to the prompt (POSIX 2.8.1); SIGINT ends the
  command being typed or run, SIGTERM and SIGQUIT are ignored; `ENV` is run
  at startup; history in `HISTFILE` (default `~/.sh_history`, `HISTSIZE`
  entries, default 1000; a line equal to the previous one or starting with a
  space is not recorded); a line editor with emacs keys (motion by character
  and word, kill and yank with consecutive kills joined, transpose, clear),
  Up/Down history, Ctrl-R incremental search, Tab completion of commands
  (built-ins, functions, aliases, reserved words, `PATH`), file names and
  `$NAME`s, bracketed paste and lines wrapping past the terminal width.
  Character width is one column per code point (no wide or combining
  characters). Job control (`-m`, `set -o monitor`; on by default in an
  interactive shell with a terminal): each pipeline, subshell or external
  command the shell forks is a job in its own process group, and the
  foreground one owns the terminal; ^Z stops it (status 148) and the shell
  takes the terminal back with its own modes, restoring the job's modes on
  `fg`; `jobs [-l|-p]`, `fg`, `bg`, `kill %job` and `wait %job` take `%N`,
  `%+`/`%%`, `%-`, `%PREFIX` and `%?TEXT`; background jobs are reported
  (`[1]+  Done ...`, bash's layout) before the next prompt; ^C on a
  foreground job also ends the rest of the command line; `exit` or ^D with
  stopped jobs warns once, and leaving sends them SIGHUP and SIGCONT. A
  job's text is its command line. Without a terminal `-m` changes nothing;
  `fg`/`bg` with no job say `No current job`, status 2, as dash does.
  Unimplemented: `fc`, vi mode; `ulimit`;
  locales and multibyte characters (bytes only, C-locale classes and byte
  order for globbing). Not POSIX and refused: `local`, `;&` in `case`,
  `${!name}` and other bash expansions (an invalid `${...}` is reported
  when it is expanded, as dash does). Choices where dash differs:
  `"${@#p}"`/`"${@%p}"` apply to every positional parameter (dash: only the
  first); `command -v ./x` prints an absolute pathname; `read` without a
  name is an error and there is no `REPLY`; `kill -l` lists names from HUP
  and accepts several operands; traps on KILL and STOP are refused; `\x`
  in a `printf` format is a hexadecimal escape; `cd` with HOME unset or
  empty does nothing and succeeds (implementation-defined; dash does the
  same); OPTIND inside a group like `-ab` already names the next argument,
  as in dash. `echo` is the XSI echo (escapes always, `-n` only first).
- `sed`, `expr`, `awk` and `find -regex` use nebox's own regex engine
  (`src/nebox/regex.nelua`; grep runs its own parsers' trees on the same
  matcher, find's -regextype names go through `regex.compile_syntax`): POSIX BRE and ERE with brackets, named classes,
  intervals, groups, alternation, back-references, and the GNU
  `\w \W \s \S \b \B \< \>` escapes. Matching is a Pike VM with GNU (glibc)
  leftmost-longest semantics: the earliest start wins, then the longest match
  (`re-alt-prefix-*`, `re-expr-longest`); subexpression spans are those of
  the first path, in alternative order, that reaches that match, so
  `(a|ab)(c|bcd)(d*)` on `abcd` gives `[a][bcd][]` as GNU does rather than
  the strict POSIX `[ab][cd][]` (`re-alt-groups*`); an empty iteration of a
  repeated group never overwrites an earlier capture (`re-star-group-*`,
  `re-empty-branch*`); back-references match the span chosen that way
  (`re-backref-*`). `sed s///g` skips an empty match that is adjacent to the
  previous match and does not count it for `s///N` (`re-sed-g-empty*`,
  `re-sed-n-empty`). Programs without back-references run in time linear in
  the line length (`re-pathological`). Programs with back-references are
  bounded to 65536 simultaneous states and stop with "pattern too complex"
  (grep exit 2, sed exit 4, expr exit 2) where GNU keeps searching
  (`re-too-complex*`; `re-pathological-backref` stays within the bound).
  Not implemented: multibyte locales (bytes only; `-i` folds ASCII; the test
  harness runs in the C locale, so this has no case), and outside grep and
  sed equivalence classes `[=a=]` and collating symbols `[.a.]` (grep's
  parsers take single-character ones as glibc does, `grep-equiv`; sed's
  through `regex.compile_posix`). sed compiles through
  `regex.compile_posix`, a port of glibc's regcomp.c parser (peek_token,
  parse_reg_exp, parse_branch, parse_expression, parse_dup_op,
  parse_bracket_exp) for RE_SYNTAX_POSIX_BASIC and _EXTENDED with sed's
  bits (RE_UNMATCHED_RIGHT_PAREN_ORD, RE_NO_GNU_OPS, RE_LIMITED_OPS):
  glibc's messages in glibc's order (`a**`, `a*\{2\}` and a leading `\{`
  are invalid in a BRE, a leading `*` `+` `?` `{` or one after an anchor
  in an ERE; a back-reference must name a group completed before its
  alternation or earlier in its own branch), C-locale `[.c.]` and `[=c=]`,
  `\n` and `\t` as the letters, ranges checked after case folding under
  `I`. Programs built that way also follow three glibc matching rules: an
  empty first iteration of a repeated group is recorded, a path whose last
  stretch passes an anchor loses to an equally long one that does not, and
  in an ERE `^` and `$` inside the pattern match beside a newline the
  match itself consumes (see `sed` for what is not reproduced). `\`` and `\'` match only at the ends of
  the subject, as in GNU regex (`sed-buffer-anchors`); `.` and `[^...]`
  match a newline unless REG_NEWLINE is in effect (sed's `M` flag).
- `patch` follows GNU patch 2.7.6 (read from its source): unified,
  context and normal diffs, several files per patch; each hunk is placed by
  GNU's locate_hunk (its line plus the previous offset, then outward, then
  with up to `-F` (2) lines of context ignored at each end, never more than
  the hunk has); a first hunk that only fits reversed is reported and `-N`
  skips, `-t` assumes `-R`, `-f` applies, otherwise GNU's questions are asked
  on `/dev/tty` (defaults without one); creating an existing file or deleting
  a missing one asks the same way. Rejects are regenerated as GNU does
  (unified for unified patches, context for context and normal ones, line
  numbers shifted by the hunks applied before); a backup `FILE.orig` is made
  with `-b` or whenever a hunk needed an offset or fuzz or failed (GNU's
  default `--backup-if-mismatch`); an empty result of a deleting patch, or
  with `-E`, removes the file. Names come from the headers with `-p N`
  components stripped (the base name without `-p`), choosing among old, new
  and `Index:` names as GNU does. Options `-b -E -f -F N -i -N -o -p -r -R -s
  -t -d --dry-run` and their long forms. `tests/patch_fuzz.py` compares
  output, status, result, reject and backup files with GNU patch on random
  patches and perturbed targets (2,000 cases, no difference; `make test` runs
  200). Not supported: ed scripts (`-e`), `-D`, `-l`, `--merge`, `--posix`,
  git diffs (renames, modes, binary), version control lookups.
- `dd` is a port of GNU coreutils 9.1 `src/dd.c` (read from its source):
  every operand (`iseek`/`oseek` too), conversion and flag, GNU's number
  syntax (`b c w k K M G T P E Z Y`, `kB`/`KiB` second suffixes, a `B`
  suffix meaning bytes, one `x` multiplication and the `0x` warning), `bs=`
  copying each read as it came while `ibs`/`obs` gather partial reads,
  skipping by `lseek` or by reading, `conv=sparse` with the final
  `ftruncate`, `oflag=direct`'s unaligned last write, `iflag=nocache`
  advice, the statistics lines with gnulib `human_readable` rounding,
  `status=progress`, and statistics on SIGUSR1 (not under `POSIXLY_CORRECT`)
  and SIGINT. Diagnostics use GNU's wording and shell-escape quoting.
  `tests/dd_compare.py` runs 154 fixed cases plus random ones against GNU dd
  and compares output, diagnostics, exit status and the files left behind
  (only the timing part of the statistics is masked); SIGUSR1, SIGINT and
  progress output were compared by hand. `--help` is shorter than GNU's;
  the rate uses double rather than long double arithmetic.
- `join` is a port of GNU coreutils 9.1 `src/join.c` in the C locale: byte
  comparison (`-i` folds ASCII), blank-run or single-character (`-t`, `-t ''`,
  `-t '\0'`) fields with GNU's empty trailing field, `-a -v -e -o` (with
  `-o auto` and the obsolete `-j1 ARG` and `-o` list continuation operand
  rules), `-1 -2 -j`, `--header`, `-z`, the order checks and GNU's
  diagnostics. Long options go through `util.getopt`, a port of glibc's
  `getopt_long` (abbreviations, ambiguity and argument errors, the three
  operand orderings). `tests/join_compare.py` runs 96 fixed and random cases
  against GNU join: 1596 cases, 0 mismatches.
- `md5sum`, `sha1sum`, `sha224sum`, `sha256sum`, `sha384sum`, `sha512sum`,
  `b2sum`, `cksum` and `sum` are one port of GNU coreutils 9.1 `src/digest.c`
  (with `sum.c` and `cksum.c`'s output), over streaming MD5, SHA-1, SHA-2,
  BLAKE2b (any `-l` length), SM3, CRC and BSD/System V sums in
  `src/nebox/digest.nelua`: `--tag`, `-z`, file-name escaping, check mode with
  GNU's line parser (untagged, tagged, OpenSSL-style, reversed BSD, escaped
  names, BLAKE2b lengths), `--ignore-missing --quiet --status --strict -w`,
  `cksum -a`/`--untagged`, `sum -r`/`-s`. Like coreutils 9.1, `cksum`'s CRC
  treats a read error (a directory) as end of file. `cksum --debug` is
  accepted and prints nothing (GNU names its CRC implementation).
  `tests/digest_compare.py`: 1989 cases against GNU, 0 mismatches.
- `base64`, `base32` and `basenc` port GNU coreutils 9.1 `src/basenc.c` with
  gnulib's `base64.c`/`base32.c`: GNU's encode and decode block sizes, the
  gnulib decode state machines (newlines anywhere, padding rules, output up
  to the first invalid character), `-i`, `-w`, and basenc's base64url,
  base32hex, base16, base2msbf, base2lsbf and z85. `tests/basenc_compare.py`:
  2588 cases (random data with damaged encodings) against GNU, 0 mismatches.
- `diff` follows GNU diffutils 3.8's algorithm step by step (`find_identical_ends`
  on bytes with horizon lines, `discard_confusing_lines`, the middle-snake
  `compareseq` with its cost cut-off, `shift_boundaries`), so its edit
  scripts are GNU's: `tests/diff_fuzz.py` compares the output with GNU diff
  on random inputs over small alphabets for 12 option sets (24,000
  comparisons with no difference before this was written down; `make test`
  runs 200 cases x 12), and 40,000-line inputs with heavy changes match as
  well. Formats: normal, context (-c, -C N; headers in the C locale's
  `%a %b %e %T %Y`), unified (-u, -U N; ISO 8601 times with nanoseconds and
  zone offset), ed (-e; a missing final newline is supplied and reported,
  status 2, as GNU does). Options -i -b -w -B -a -N -q -s -r; `-` is standard
  input; a directory and a file compare the file of the same name; directory
  comparison prints `Only in`, `Common subdirectories`, `File ... is a ...
  while file ... is a ...` and `diff OPTIONS a/x b/x` headers. Binary files
  (a NUL byte) are reported as differing unless -a. Not supported: long
  options (`--label` and the rest), -p/-F function headers, -y side by side,
  -t/-T, -I, -x/-X, -l, -n (RCS), -D (ifdef), --minimal and
  --speed-large-files.
- `grep` ports GNU grep 3.8 (`src/nebox/applets/grep.nelua`, C locale) as
  Debian's grep 3.8-5 builds it, which is the reference: its two behaviour
  patches are kept (the `stray \` warnings appear only when
  `DEB_GREP_ENABLE_STRAY_BACKSLASH_WARN` is set, and a newline after the
  last pattern without a back-reference adds no empty alternative,
  Debian #1029235). Ported as written: get_nondigit_option and every
  option and long option with glibc getopt_long's messages, the pattern
  table (duplicate patterns dropped, `FILE:LINE:` prefixes for compile
  errors from -f files), try_fgrep_pattern and the -F/-G switches,
  the early exits (`-m 0`, `-v ''`, -f of an empty file), the page-aligned
  buffer with its 96 KiB first read, growth for long lines and the
  SEEK_DATA skipping of NUL runs, binary detection per buffer (NULs, or a
  hole found with SEEK_HOLE) with zap_nuls, "binary file matches" on
  standard error, -a/-I/`--binary-files`, prtext/prpending context and
  group separators (`--group-separator`, `--no-group-separator`), -o, -c,
  -l/-L/-q and the -s/-q status rules, -b, -n, -T with its offset width,
  -Z/-z, `--label`, `--line-buffered`, -u's warning, `--color` with
  GREP_COLORS (every capability, `rv`, `ne`, parsing stopped at the first
  malformed byte) and the deprecated GREP_COLOR with its warning,
  "input file is also the output", standard output to /dev/null,
  finalize_input (what -m and -q leave of a seekable standard input, a
  pipe drained), devices (-D, FIFOs and sockets skipped in recursion),
  directories (-d, "Is a directory"), and -r/-R through the gnulib fts port
  (`src/nebox/fts.nelua`) in directory order with "recursive directory
  loop" warnings, `--include`/`--exclude`/`--exclude-from`/`--exclude-dir`
  as gnulib exclude.c's hashed and fnmatch segments (anchored for names
  found in the walk, any suffix after `/` for command-line names). Standard
  output is buffered as glibc's stdio does, so write errors (`/dev/full`)
  are reported, or not, where GNU reports them. Patterns are compiled as
  GEAcompile does: each line through a port of glibc regcomp's parser
  (its messages, per line; with -i the pattern and subject are read through
  toupper as glibc does), then all lines, wrapped in the -w/-x "motif",
  through a port of dfa.c's lexer and parser (its warnings, its
  `[:space:]` and other errors, its own reading of constructs where it and
  glibc disagree). The dfa.c tree selects lines; the glibc trees give
  back-references, the -w retry loop of EGexecute and the -o/--color match
  spans, so a line can be selected with nothing printed by -o exactly where
  GNU does that. Both trees run on the Pike VM of `src/nebox/regex.nelua`;
  -F runs kwsearch.c's Fexecute over a leftmost-longest keyword search.
  `tests/grep_compare.py`: 604 fixed cases and 3000 random patterns,
  options and inputs, 0 mismatches (3 more runs of 3000 random cases with
  other seeds also gave 0). Differences:
  - -P is refused as by a GNU grep built without PCRE ("Perl matching not
    supported in a --disable-perl-regexp build", status 2).
  - `--help` omits GNU's bug-report paragraph; `--version` prints nebox's
    line.
  - Only the C locale: no multibyte characters or encoding errors, so a
    byte above 127 never makes a file binary (as in GNU's C locale).
  - A pattern with back-references that needs more than 65536 simultaneous
    states stops with "pattern too complex" (status 2) where GNU keeps
    searching (`re-too-complex`). Back-references are matched exactly
    (every capture assignment is tried); glibc's backtracking matcher is not
    reproduced where it would answer otherwise.
  - The size of each read after the first 96 KiB depends on the page
    alignment of the buffer's address, nebox's from nelibc's malloc and
    GNU's from glibc's; where the two differ, so does the point at which a
    NUL past the first read turns a file binary, and so which lines before
    it are printed (the fixtures with such a NUL agree). From a pipe this
    depends on the writer's timing in both.
- `sed` ports GNU sed 4.9 (sed.c, compile.c, execute.c, regexp.c,
  debug.c and utils.c; `src/nebox/applets/sed.nelua`) for the C locale.
  The script is read byte by byte as compile.c reads it, so every
  diagnostic has GNU's wording and its "-e expression #N, char M:" or
  "file F line L:" position (an unclosed `{` reports where it was opened,
  run-time errors such as "no previous regular expression" report char 0),
  and GNU's exit statuses: 1 for usage and script errors, 2 when an input
  could not be read (it overrides a `q`/`Q` code), 4 for run-time
  failures, and the `q N`/`Q N` code as exit() truncates it (-1 meaning
  none). Ported as written: every command, `v` with strverscmp, `L`
  accepted and then fatal at run time ("INTERNAL ERROR: Bad cmd L"), `e`
  (popen of `/bin/sh -c`, the command cut at its first NUL, its text
  then NUL-terminated as `--debug` shows), `F` ("-" for standard input), `z`;
  every address form with execute.c's range rules (`0,/re/`,
  `first~step`, `addr,+N`, `addr,~N`, a line-number end that is already
  past, `$` opening later files to see whether they hold data, `0r`); `s`
  with setup_replacement's parsing (`& \0-\9 \n \U \L \u \l \E`, a
  pending `\u` carried past an empty group, case conversion that turns
  bytes above 127 into 0xff as glibc's C locale does), the empty regex
  meaning the last regex used, checked when it runs, the numbered and `g`
  flags with GNU's empty-match rule, `p` before and after `e`, `w`, `I`,
  `M`; normalize_text's escapes (`\a \f \n \r \t \v`, `\dNNN \oNNN \xHH
  \cX` with GNU's digit limits, a produced `&` or `\` staying literal in a
  replacement but keeping its meaning in a regex, `\c\\`, bracket
  contents left alone under --posix and POSIXLY_CORRECT); `a`, `i`, `c`
  one-liners and `a\` text (leading blanks kept after `a\`, text continued
  into the next -e, an unterminated last line kept raw); `#n` on the first
  line of the first script; the missing-newline rule kept per output;
  `w /dev/stdout`, `w /dev/stderr` and `R /dev/stdin` using the standard
  streams (not under POSIXLY_CORRECT), `R` reading a line per execution,
  w files opened (truncated) at compile time; `-i` with a `*` in the suffix
  replaced by the operand as given (so `-i'bak/*'` on `d/f` renames to
  `bak/d/f`), the temporary made by mkstemp beside the file under umask
  077 and given its mode and owner, non-regular files refused (a
  terminal is refused too, untested); `--follow-symlinks` (gnulib's follow_symlink, also for `F`), `-s`
  (hold space and ranges reset per file), `-z`, `-u`, `-l N` and `COLS`
  (atoi, so `-l 1` breaks before every character and `-l 0` never),
  `--posix` and POSIXLY_CORRECT (their syntax bits, unknown commands and
  one-address checks, `N` at end of input not printing), `--sandbox`,
  `--debug` (debug.c's program dump and trace, with its quirks: `:(null)`
  for a label compiled before --debug, octal of a sign-extended byte),
  `-b`, `--help`, and getopt_long's option handling and messages. Input
  and output go through stdio-like buffers of glibc's size (st_blksize up
  to 8192, line buffered on a terminal), so a write error is reported by
  the same call with GNU's message ("couldn't write 3 items to stdout",
  "couldn't flush stdout", "<unknown>" for a w file flushed at close,
  "couldn't close stdout" when it was closed) and a seekable standard
  input is left just after the last line consumed, as glibc's exit leaves
  it. Regular expressions
  go through `regex.compile_posix`, a port of glibc's regcomp parser for
  RE_SYNTAX_POSIX_BASIC/EXTENDED with sed's bits (see the regex entry),
  and GNU's dfa diagnostic "character class syntax is [[:space:]], not
  [:space:]" (fatal unless POSIXLY_CORRECT is set) is reproduced.
  `tests/sed_compare.py` (1389 fixed cases and 3000 random scripts in
  `make test`) compares stdout, stderr, status and every file left
  behind against GNU sed: 0 mismatches; six more runs of 8000 random
  scripts with other seeds also gave 0. Differences:
  - `--version` prints nebox's line.
  - GNU's matching is glibc's regexec behind GNU's dfa; nebox runs its
    Pike VM with the glibc rules that are known (leftmost-longest, the
    capture choices in the regex entry, an empty first iteration of a
    repeated group recorded, a path that ends just after an anchor losing
    to one that does not, so `s/(b)$|(b)/[\1|\2]/` gives `[|b]` in both,
    and in an ERE a `^` or `$` inside the pattern matching beside a newline
    the match itself consumes, so `N;s/x$\n/Y/` substitutes in both).
    Not reproduced: glibc's choice of capture spans through its NFA node
    numbering when equally long alternatives match in ways not covered
    above; groups that match only through an anchor under repetition or a
    back-reference (`s/\(\B\)*\1\+/x/` matches in nebox, never in GNU);
    back-references to a group under repetition, where glibc's
    back-reference matcher also tries iterations its final registers drop
    (`s/,\?\(0\?x*\)*\1/\//` turns `,0` into `/` in GNU, `/0` in nebox);
    a `^` inside a group repeated by `+`, which makes glibc miss matches
    when registers are needed (`s/\(^.*\)\+A/x/` does nothing in GNU);
    the spans glibc reports around a mid-pattern ERE anchor next to a
    newline; and addresses with `M` and no back-reference, which GNU's dfa
    decides alone: it accepts a repeated anchor (`/a\B\?$/M` matches `a`
    in GNU; glibc and nebox read the `\?` as a literal `?`) and takes
    `` \` `` and `\'` as line anchors there. The random scripts keep
    anchors out of groups, back-references away from repeated groups and
    buffer anchors out of `M` addresses for these reasons.
  - A program with back-references can exceed nebox's thread bound and
    stops with "pattern too complex" (exit 4), as in the regex entry.
- `df` reads mounts from /proc/self/mounts and statfs through nelibc's
  backend table.
- `whoami` knows only the current process.
- Local time (`date`, `stat`, `ls -l`, `diff -u` headers, `touch -d`/`-t`)
  comes from nelibc's `localtime_r` (and `mktime`, except in `date` and
  `touch`, which use a port of glibc's mktime over localtime_r): TZif zone files, POSIX TZ
  strings (`EST5EDT`, `<+0530>-5:30`, `NZST-12NZDT,M9.5.0,M4.1.0/3`), and
  `/etc/localtime` when TZ is unset. A relative zone name is looked up
  under `$TZDIR` or `/usr/share/zoneinfo` first, as glibc does (`TZ=Japan`
  reads the zone file, not a POSIX string). Cases compare against GNU with
  explicit TZ values, DST transitions (America/New_York, the half-hour
  Australia/Lord_Howe), historical offsets with seconds and years from -1199 to
  2147483647 (`date-tz-*`, `touch-tz*`). Unset TZ is only exercised with a
  UTC `/etc/localtime` (the test container's). An unknown zone
  (`TZ=Foo/Bar`, `TZ=:Foo`) is UTC with its leading letters as the
  abbreviation, and a `$TZDIR` that lacks the zone makes the name a POSIX
  string, both as in glibc (`date-tz-unknown-name`,
  `date-tz-tzdir-missing`). `touch` rejects a wall time that a
  DST change skips and takes the first of a repeated hour, as GNU does.
- `date` ports GNU coreutils 9.1 date.c in the C locale
  (`src/nebox/applets/date.nelua`) over a port of gnulib's
  parse-datetime.y (`src/nebox/getdate.nelua`, which `touch -d` also uses):
  every option and long option (-d -f -I[FMT] `--rfc-3339` -R and its
  aliases -r `--resolution` -s -u and its aliases `--debug`), argmatch's
  messages for -I and `--rfc-3339`, the "multiple output formats",
  mutually-exclusive, print-and-set, extra-operand and missing-'+' errors,
  -f FILE or - read line by line with "invalid date" for each bad line (a
  line ends at a NUL for the parser, as in C), the MMDDhhmm[[CC]YY][.ss]
  operand through posixtm, clock_settime for -s and the operand with the
  date printed whatever the outcome, `%-N` and `--resolution` from
  gettime_res, show_date's "time ... is out of range", and close_stdout's
  write error (with or without an errno, as close_stream decides).
  Formatting is the nstrftime port (`date-fmt-*`). The parser is
  hand-written from the bison grammar: the same productions, bison's shift
  in the grammar's 31 conflicts and its default reductions, so `--debug`
  reports items, unknown words and the "stopped at" text in GNU's order.
  yylex, lookup_word and its tables (local zone abbreviations from the zone
  now and in the next three quarters, military letters with no J and T as
  the ISO separator, the 19-character word buffer, the period-dropping
  retry), the `TZ="..."` prefix with its escapes, relative items with
  ago/hence, this/next/last and ordinal words, decimal seconds, `@N`,
  digits_to_date_time, time_zone_hhmm, to_hour, to_tm_year, every
  overflow check and parse_datetime_body's steps and `--debug` lines are
  ported as written. mktime is a port of the glibc 2.36 / gnulib mktime.c
  that GNU date calls (its process-wide offset guess, spring-forward gaps,
  a requested tm_isdst) over nelibc's localtime_r, and zones switch TZ as
  gnulib's time_rz does. `tests/date_compare.py`: 3512 fixed cases (every
  option and error, about 600 grammar strings plain and with `--debug`
  under several TZ values, DST edges in New York, a POSIX-rule zone and
  Lord Howe, far years and the time_t limits) and 3000 random strings
  built from grammar pieces and character fuzz, 0 mismatches; four more
  seeds with 12000 random strings each also gave 0. -f with 100000 lines
  (30000 with `--debug` or invalid lines) stayed near 8 MB resident.
  Differences:
  - glibc applies a POSIX TZ rule (a TZ string such as
    `EST5EDT,M3.2.0,M11.1.0`, or a zone file's footer after its last
    transition) only from 1970, so earlier times are standard time there,
    and its rule arithmetic overflows int past year 5885487; nelibc applies
    the rule in every year. The test reruns such cases (about 1% of the
    random strings) in Asia/Tokyo.
  - `--help` omits GNU's closing links; `--version` prints nebox's line.
  - -s and the operand were compared as an unprivileged user only ("cannot
    set date: Operation not permitted", the date still printed, status
    1); actually setting the clock is untested.
- `ls`, `dir` and `vdir` port GNU coreutils 9.1 `src/ls.c` in the C locale
  (`src/nebox/applets/ls.nelua`): every option and long option with
  getopt_long's abbreviation rules and ls's XARGMATCH/argmatch messages
  (exit 1) and line-width, tab-size, block-size and time-style errors
  (exit 2); `dir` defaults to -C and escape quoting, `vdir` to -l. Ported
  as written: gobble_file's stat/lstat decisions (-L, -H,
  `--dereference-command-line-symlink-to-dir` and the default of following
  command-line symlinks to directories unless -d, -F or -l), d_type use,
  "cannot access" entries shown with `?` fields, print_dir with the -R
  dev/ino loop check ("not listing already-listed directory") and its
  marker entries, the -1 -U streaming case, extract_dirs_from_files, the
  sort variants (-t -S -X -v -U -f -r, `--sort=width`, `--time=`
  atime/ctime/birth through statx, `--group-directories-first`) over
  gnulib's mpsort, calculate_columns and the -C/-x/-m printers with tab
  indentation, print_long_format's column widths, the "total" line,
  recent/old timestamps (six months, future times, years that do not fit
  printed as seconds), `--time-style` (full-iso, long-iso, iso, locale,
  `+FORMAT` with the two-format newline form, `TIME_STYLE`, `posix-`) over
  the nstrftime port, block sizes (-h, `--si`, -k, `--block-size`,
  `LS_BLOCK_SIZE`, `BLOCK_SIZE`, `BLOCKSIZE`, `POSIXLY_CORRECT`), quoting
  through gnulib quotearg (every `--quoting-style`, -b -Q -N, `QUOTING_STYLE`,
  -q and `--show-control-chars`, outer-quote alignment, the indicator
  characters quoted under `--file-type`/-F), `--dired` offsets, `--zero`,
  `--hyperlink` (file:// URLs with the escaped host name), -Z, `--author`,
  ACL `+` markers from the POSIX ACL xattrs as gnulib's file_has_acl reads
  them, and `LS_COLORS` (get_funky_string's escapes including its `^?`
  quirk, extensions, `ln=target`, `or`, `mi`, `mh`, `su`/`sg`/`tw`/`ow`/`st`,
  `ec`/`lc`/`rc`/`rs`/`cl`, the "unrecognized prefix" and "unparsable value"
  diagnostics; with `LS_COLORS` unset, ls.c's built-in colors when
  `COLORTERM` is set or `TERM` matches a dircolors TERM line). On a
  terminal it defaults to -C, -q and shell-escape quoting with the width
  from TIOCGWINSZ. `tests/ls_compare.py`: 2464 fixed cases (46 of them on a
  pseudo-terminal) and 400 random option combinations against GNU ls, dir
  and vdir, 0 mismatches as an ordinary user; run as root (other owners,
  unknown ids, a file capability) 2878 cases, 0 mismatches; a run of 2500
  random cases with another seed also gave 0. Differences:
  - `--help` and `--version` are refused as unsupported options (status 2).
  - `ca`: nebox colors files that have a `security.capability` attribute,
    as an ls built with libcap does; the GNU ls in the test container is
    built without libcap and never does. The root run checks that this is
    the only difference for such a file.
  - SELinux contexts are the raw `security.selinux` attribute (no
    libselinux translation, no SMACK); without one, -Z shows `?` and -l no
    `.` marker, as GNU does on a system without SELinux.
  - Only the C locale: no multibyte widths, `locale` and `posix-` styles
    give the C formats, names compare bytewise.
  - Files are examined with stat/lstat; statx (with AT_NO_AUTOMOUNT) is
    used only for birth times, so listing an automount point may trigger it.
  - The color restore on SIGINT/SIGTSTP is ported but untested: the test
    pseudo-terminal is not a controlling terminal.
  - User and group names come from nelibc's getpwuid/getgrgid.
- `nproc` counts the CPUs in the process affinity mask, like GNU nproc.
- `printf` (the applet and the `sh` builtin) ports printf.c: escapes
  including \u/\U (gnulib's \uXXXX fallback in the C locale), `%b`, `%q`,
  every flag, `*` widths and precisions, length modifiers dropped and
  intmax_t / long double conversions, character constants, strtoimax /
  strtold diagnostics, format reuse and the excess-argument warning; `%a`
  ports glibc's x87 printf_fphex (1 prints as 0x8p-3). \c and fatal errors
  end the call, not the shell. `tests/printf_compare.py`: 177 fixed and
  2000 random argument vectors (precisions past 100000 included), 0
  mismatches.
- `seq` follows GNU seq 9.1: long double operands (decimal, exponent, hex,
  `inf`), output precision from the fraction digits of FIRST and INCREMENT
  (`%Lg` for hex operands), the extra last number when it prints as LAST
  (`seq 0 0.1 1` ends with `1.0`), `-w` widths for floating operands, `-f`
  with one `e f g a E F G A` conversion and `%%`, `-s` strings, the long
  options, and exact decimal counting for integer operands with a step up
  to 200 (`seq 18446744073709551614 18446744073709551617`, `seq 1 inf`)
  (`seq-*`). One difference, from nelibc's printf: `-f %a` prints the
  normalized `0x1p+0` where glibc prints `0x8p-3` (`seq-f-hexfloat`); both
  are valid C. No `--help`/`--version`.
- `test` has no parentheses; `-a`/`-o` bind loosest, in that order.
- `mv` across filesystems copies then removes; `cp -a` is `-rp`.

Everything in the applet list has at least one passing case in
`tests/run.sh`; see the test names for the exact flags covered. The result
of the last container run is recorded in the commit message of each commit
that changed behavior.
