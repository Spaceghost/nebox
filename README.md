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
cp cut date df dirname du echo env expand expr factor false find fold free
grep groups head hexdump hostname id install join kill link ln ls md5sum mkdir
mktemp mv nl nproc nsh od paste patch printenv printf pwd readlink realpath
rev rm rmdir sed seq sh sha1sum sha224sum sha256sum sha384sum sha512sum shuf
sleep sort split stat strings sum sync tac tail tee test timeout touch tr true
truncate tsort tty uname unexpand uniq unlink wc which whoami xargs yes
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
  current non-matching behavior). `\`` and `\'` match only at the ends of
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
- `grep` takes -i -v -n -b -c -l -L -q -s -H -h -r -F -E -G -w -x -o -e -f -m -z -Z
  and
  the context options -A, -B, -C and -NUM, following GNU grep 3.8's prtext:
  `--` before a group that is not adjacent to the previous output (also
  across files), -C and -NUM as a default that -A/-B override whatever the
  order (the last -C/-NUM wins; digits accumulate within one argument),
  trailing context still printed after -m stops (matching lines there are
  context lines), `-o` printing the matches of matching lines (under -v
  those are the context lines) and the separators but no other context,
  `-b` giving the offset of the line or, with -o, of the match, and no
  context for -c/-l/-q (`grep-ctx-*`). -F strings are matched as quoted
  BREs, so -F works with -o (`grep-F-o`). -f reads one pattern per line
  (an empty file gives no patterns, so nothing matches; `-f -` is standard
  input), merged with -e patterns in command-line order. -L lists files
  without a selected line; as in GNU grep 3.5 and later the exit status
  still says whether any line was selected, and of -l and -L the last one
  given wins. -z reads and writes NUL-terminated records (`.` matches a
  newline inside a record, `^`/`$` only at its ends; the `--` separator and
  -c counts still end in a newline); -Z writes a NUL after file names in
  -l/-L/-c output and line prefixes. -s silences unreadable-file messages
  but keeps exit status 2. `-o -w` prints the word without its delimiters
  (`grep-o-w`). GNU grep's long options work (`--color`/`--colour` accept
  never/auto, `--line-buffered` is accepted); -T, -P, -a/-I, --include and
  the other options nebox lacks are refused by name. Not supported:
  binary-file detection (a NUL byte does not make grep report
  "binary file matches").
- `sed` covers -n -e -f -E -s -i[SUFFIX] -z, every address form (`I` and
  `M` after a regex address), and the commands
  `{ } s y p P d D n N g G h H x a i c = l q Q r w W b t T : z F e`.
  `s` flags: g p N i/I m/M e w; replacement escapes
  `& \1..\9 \n \U \L \u \l \E`. Compared with GNU sed 4.9: `M` is
  REG_NEWLINE, so `.` and `[^...]` stop matching a newline and `^`/`$` also
  match next to embedded newlines, except under -z where only the first
  part applies (`sed-M-*`, `sed-z-M`). -z makes NUL the delimiter for input
  lines, output, N G H D P W, `=`, `l`, `i`, `c`, `w` and `F`; text from `a`
  still ends with a newline (`sed-z*`). `e COMMAND` writes the output of
  `/bin/sh -c COMMAND` at once; `e` alone and the `s///e` flag replace the
  pattern space with the output of running it, less one trailing
  delimiter; `p` before `e` prints before evaluating, after it prints the
  result; exit statuses are ignored (`sed-e-*`). A last line printed
  without its delimiter gets it when more output follows, separately for
  each `w` file and `/dev/stdout` (`sed-missing-newline`). Not supported:
  `--posix`, `--sandbox`, `--debug`, `-u`, `-l N`, `--follow-symlinks`,
  the `v` command, `R` (parsed but does nothing), and the `\dNNN \oNNN
  \xHH \cX` escapes.
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
  suffixes k K M G T P E Z Y, -V implements gnulib filevercmp. Long options
  follow GNU's table, including `--check[=quiet|silent|diagnose-first]`. No
  -M, -g, -R, --parallel, or locales.
- `df` reads mounts from /proc/self/mounts and statfs through nelibc's
  backend table; `free` reads /proc/meminfo.
- `tsort` reproduces GNU's output order (sorted zero-degree queue, successors
  in reverse input order).
- `stat` has no `%w`/birth time or device-name formatting beyond
  `%d`/`%D`/`%t`/`%T`; `%x %y %z` and the default output show local time
  with nanoseconds and `%z` offset, as GNU does (`stat-tz`).
- `xargs` runs commands with `fork`+`execvp`; no `-P`, `-L`, or `-s` limits.
- `groups`/`whoami` know only the
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
  UTC `/etc/localtime` (the test container's). An unknown zone
  (`TZ=Foo/Bar`, `TZ=:Foo`) is UTC with its leading letters as the
  abbreviation, and a `$TZDIR` that lacks the zone makes the name a POSIX
  string, both as in glibc (`date-tz-unknown-name`,
  `date-tz-tzdir-missing`). `touch` rejects a wall time that a
  DST change skips and takes the first of a repeated hour, as GNU does.
- `date` formats with GNU's nstrftime rules in the C locale: every
  conversion, the `_ - 0 + ^ #` flags, widths, `E`/`O`, `%N` (and `%-N`),
  `%q`, `%P`, `%s`, `%:z %::z %:::z` (`date-fmt-*`). `-u`, `-R`, `-r FILE`;
  `-d` reads a subset of gnulib's parse-datetime (`src/nebox/getdate.nelua`):
  `@SECONDS[.FRAC]`, `YYYY-MM-DD`, `MM/DD[/YY[YY]]`, `HH:MM[:SS[.FRAC]]`
  with `am`/`pm`, the ISO `T` form, zones `Z`/`UTC`/`UT`/`GMT`/`+HH[:MM]`
  (a signed number right after a time is its zone, as in GNU, so
  `01:30 +1 hour` means UTC+1 plus one hour), `now`/`today`/`yesterday`/
  `tomorrow`, weekdays with `next`/`last`/`this`, and relative
  `[+-]N unit [ago]` for years, months, fortnights, weeks, days, hours,
  minutes and seconds, applied in parse-datetime's order (calendar units on
  the broken-down time, then seconds; relative-only strings keep the current
  DST flag). Against GNU date 9.1 (`date-d-*`). Not understood: month names,
  ordinal words, `week` numbers, named zones other than UTC/GMT, `DST`. No
  `-I`, `--rfc-3339`, `-f`, long options, or setting the date.
- `ls` follows GNU ls 9.1 in the C locale with the options
  `-1 -a -A -B -c -C -d -F -g -G -h -i -I PATTERN -k -l -m -n -N -o -p -q
  -r -R -s -S -t -T COLS -u -v -w COLS -x -X`, permuted as getopt does:
  the last of -C -x -m -l -1 picks the format (-1 does not undo -l), the
  column layout is GNU's calculate_columns (columns at least 3 wide, filled
  down for -C and across for -x, tab stops every 8 or `-T`/`TABSIZE`),
  the width comes from -w (0 for no limit), else `COLUMNS` (an invalid
  value is ignored with GNU's warning), else 80; -s/-i fields are padded
  per listing; widths cover every command-line operand, directories
  included; only printable bytes count toward a name's width; -q shows
  them as `?`; -F marks `/ * @ | =` and, with -l, the symlink target's
  type; command-line symlinks to directories are followed unless -d, -F
  or -l; -c/-u sort by that time when -l is absent; -I uses FNM_PERIOD
  (`ls-C-*`, `ls-s*`, `ls-i-columns`, `ls-sort-X-v`, `ls-u-c`, `ls-I-B`,
  `ls-q`, `ls-lF`, `ls-l-dev`). -k changes nothing because `BLOCK_SIZE`
  and `LS_BLOCK_SIZE` are not read. Not implemented: -f and -U (directory
  order), -L and -H, -Q -b and the other quoting styles, -Z, --color and
  every long option, ACL and SELinux markers, locales. On a terminal ls
  defaults to -C with the width from COLUMNS or the terminal, but names
  are not quoted as GNU quotes them there; no case covers it (the harness
  has no terminal). `-l` shows the year instead of the time for files older than
  six months or in the future, as GNU does (`ls-l-tz`). `-l` and `id`
  resolve names by reading `/etc/passwd` and `/etc/group` directly (nelibc
  has no `getpwuid`); unknown ids print as numbers.
- `id` lists supplementary groups from `getgroups`; `-G` is supported.
- `nproc` counts the CPUs in the process affinity mask, like GNU nproc.
- `printf` (the applet and the `sh` builtin) has `%s %b %c %d %i %u %o
  %x %X %f %F %e %E %g %G %%` with flags, width and precision; no `*`
  width or precision, no `%a`, and arguments are reused until consumed.
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
