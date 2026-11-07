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
[ awk base64 basename cat chgrp chmod chown cksum cmp comm cp cut date df
dirname du echo env expand expr factor false find fold free grep groups head
hexdump hostname id install kill link ln ls md5sum mkdir mktemp mv nl nproc od
paste printenv printf pwd readlink realpath rev rm rmdir sed seq sh sha1sum
sha256sum shuf sleep sort split stat strings sync tac tail tee test timeout
touch tr true truncate tsort tty unexpand uname uniq unlink wc which whoami
xargs yes
```

`nebox --list` prints the names; `nebox --install [-s] DIR` creates one link
per applet in `DIR`.

## Known limits

Stated here rather than worked around:

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
- `sh` is a non-interactive POSIX.1-2017 shell (`src/nebox/sh/`: lexer,
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
  diagnostics as `sh: line N: ...`. Unimplemented: interactive use (`-i`
  is refused; no prompts, history, `fc`, line editing or `ENV`); job control (`-m`/`set -o monitor`, `%job`
  operands, `jobs`, `bg`, `fg` report an error with status 2); `ulimit`;
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
- `grep`, `sed`, `expr` and `find -regex` use nebox's own regex engine
  (`src/nebox/regex.nelua`): POSIX BRE and ERE with brackets, named classes,
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
  harness runs in the C locale, so this has no case), equivalence classes
  `[=a=]` and collating symbols `[.a.]` (`re-equiv-unsupported` pins the
  current non-matching behavior). `grep` has no `-A/-B/-C` context or `-z`.
- `sed` covers -n -e -f -E -s -i[SUFFIX], every address form, and the
  commands `{ } s y p P d D n N g G h H x a i c = l q Q r w W b t T : z F`.
  `s` flags: g p N i/I w; replacement escapes `& \1..\9 \n \U \L \u \l \E`.
  No `e`, `M`, `-z`, or `--posix`.
- `find` has the usual tests and actions (-name -iname -path -regex -type
  -size -empty -newer -mtime -mmin -perm -user -group -links -inum -maxdepth
  -mindepth -depth -prune -print -print0 -delete -exec ; and + -quit), but
  walks directories in sorted name order; GNU uses directory order. No -L/-H,
  -printf, or -ls.
- `du` and `find` print entries in sorted name order; GNU prints in directory
  order.
- `od` supports -A -t (a c d u o x; sizes 1 2 4 8) -b -c -d -o -x -s -i -l -j
  -N -v; no floats or -w. `hexdump` offers -C -c -b -d -o -x -n -s -v only.
- `sort` takes -b -c -C -d -f -h -i -m -n -o -r -s -t -u -V -z and -k with
  `F[.C][OPTS][,F[.C][OPTS]]` positions and the modifiers b d f h i n r V,
  following GNU's key inheritance, last-resort and -u/-c rules in the C locale
  (bytes, no collation). -n compares digit strings like GNU, -h knows the
  suffixes k K M G T P E Z Y, -V implements gnulib filevercmp. No -M, -g, -R,
  --parallel, long options, or locales.
- `tail -f` polls once a second; `-F` is treated as `-f`.
- `df` reads mounts from /proc/self/mounts and statfs through nelibc's
  backend table; `free` reads /proc/meminfo.
- `tsort` reproduces GNU's output order (sorted zero-degree queue, successors
  in reverse input order).
- `stat` has no `%w`/birth time or device-name formatting beyond
  `%d`/`%D`/`%t`/`%T`; `%x %y %z` and the default output show local time
  with nanoseconds and `%z` offset, as GNU does (`stat-tz`).
- `xargs` runs commands with `fork`+`execvp`; no `-P`, `-L`, or `-s` limits.
- `timeout` polls the child every 2 ms rather than using signals; `-k` is
  accepted but ignored.
- `mktemp` draws names from `getrandom`; `groups`/`whoami` know only the
  current process.
- Local time (`date`, `stat`, `ls -l`, `diff -u` headers, `touch -d`/`-t`)
  comes from nelibc's `localtime_r`/`mktime`: TZif zone files, POSIX TZ
  strings (`EST5EDT`, `<+0530>-5:30`, `NZST-12NZDT,M9.5.0,M4.1.0/3`), and
  `/etc/localtime` when TZ is unset. A relative zone name is looked up
  under `$TZDIR` or `/usr/share/zoneinfo` first, as glibc does (`TZ=Japan`
  reads the zone file, not a POSIX string). Cases compare against GNU with
  explicit TZ values, DST transitions (America/New_York, the half-hour
  Australia/Lord_Howe), historical offsets with seconds and years from -1199 to
  2147483647 (`date-tz-*`, `touch-tz*`). Unset TZ is only exercised with a
  UTC `/etc/localtime` (the test container's). Differences from GNU: an
  unknown zone (`TZ=Foo/Bar`, `TZ=:Foo`) is UTC with the abbreviation `UTC`
  where GNU shows `Foo` (`date-tz-unknown-name`); a `$TZDIR` that lacks the
  zone falls back to `/usr/share/zoneinfo` where GNU parses the name as a
  POSIX string (`date-tz-tzdir-missing`). `touch` rejects a wall time that a
  DST change skips and takes the first of a repeated hour, as GNU does.
- `date` formats with GNU's nstrftime rules in the C locale: every
  conversion, the `_ - 0 + ^ #` flags, widths, `E`/`O`, `%N` (and `%-N`),
  `%q`, `%P`, `%s`, `%:z %::z %:::z` (`date-fmt-*`). `-u`, `-R`, `-r FILE`;
  `-d` understands only `@SECONDS`. No `-I`, `--rfc-3339`, `-f`, long
  options, or setting the date.
- `ls` prints one entry per line in every mode (no columns); sorting flags -r -t -S and -h -i -n -A are supported. `-l`
  shows the year instead of the time for files older than six months or in
  the future, as GNU does (`ls-l-tz`). `-l` and `id`
  resolve names by reading `/etc/passwd` and `/etc/group` directly (nelibc
  has no `getpwuid`); unknown ids print as numbers.
- `id` lists supplementary groups from `getgroups`; `-G` is supported.
- `nproc` counts the CPUs in the process affinity mask, like GNU nproc.
- `tr` has ranges, `[:class:]`, `[c*n]`, `-c`, `-d`, `-s`, and escapes; no equivalence classes.
- `printf` (the applet and the `sh` builtin) has `%s %b %c %d %i %u %o
  %x %X %f %F %e %E %g %G %%` with flags, width and precision; no `*`
  width or precision, no `%a`, and arguments are reused until consumed.
- `seq` is integer-only.
- `chmod` takes octal modes and `[ugoa][+-=][rwxXst]` lists.
- `test` has no parentheses; `-a`/`-o` bind loosest, in that order.
- `mv` across filesystems copies then removes; `cp -a` is `-rp`.

Everything in the applet list has at least one passing case in
`tests/run.sh`; see the test names for the exact flags covered. The result
of the last container run is recorded in the commit message of each commit
that changed behavior.
