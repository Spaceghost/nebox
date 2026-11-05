# nebox

A toybox-style multicall binary written in Nelua and linked against
[nelibc](https://github.com/Spaceghost/nelibc)'s standalone profile. One
static x86-64 Linux executable, no host libc, no undefined symbols; each
applet is chosen from `argv[0]` (a hard or symbolic link named after the
applet) or from the first operand (`nebox cat FILE`).

## Build and test

Builds and tests run only inside the Incus container `nelibc-writ` on bak,
where nelibc is checked out at `/work/nelibc` with
`build/libnelibc-standalone-zig.a` already built:

```sh
tools/remote.sh          # sync, build, run tests/run.sh in the container
tools/remote.sh build    # build only
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
[ base64 basename cat chgrp chmod chown cksum cmp comm cp cut date dirname du
echo env expand expr factor false fold grep groups head hostname id kill link
ln ls md5sum mkdir mktemp mv nl nproc paste printenv printf pwd readlink
realpath rev rm rmdir seq sha1sum sha256sum sleep sort split stat strings sync
tac tail tee test timeout touch tr true truncate tty unexpand uname uniq unlink
wc which whoami xargs yes
```

`nebox --list` prints the names; `nebox --install [-s] DIR` creates one link
per applet in `DIR`.

## Known limits

Stated here rather than worked around:

- `grep` and `expr` use nebox's own regex engine (`src/nebox/regex.nelua`):
  POSIX BRE and ERE with brackets, classes, intervals, groups, alternation,
  back-references, and the GNU `\w \W \s \S \b \B \< \>` escapes. Matching
  is leftmost-first (backtracking), not POSIX leftmost-longest, which only
  differs for alternations whose branches are prefixes of each other. No
  multibyte locales. `grep` has no `-A/-B/-C` context or `-z`.
- `du` prints entries in sorted name order; GNU prints in directory order.
- `stat` shows times in UTC and has no `%w`/birth time or device-name
  formatting beyond `%d`/`%D`/`%t`/`%T`.
- `xargs` runs commands with `fork`+`execvp`; no `-P`, `-L`, or `-s` limits.
- `timeout` polls the child every 2 ms rather than using signals; `-k` is
  accepted but ignored.
- `mktemp` draws names from `getrandom`; `groups`/`whoami` know only the
  current process.
- `date` prints UTC. nelibc has no zone database, so there is no local time.
  `-d` understands only `@SECONDS`; setting the date is unsupported.
- `ls` prints one entry per line in every mode (no columns). `-l` and `id`
  resolve names by reading `/etc/passwd` and `/etc/group` directly (nelibc
  has no `getpwuid`); unknown ids print as numbers.
- `id` reports only the primary group.
- `nproc` counts the CPUs in the process affinity mask, like GNU nproc.
- `sort` offers `-r -n -u -f -o`; no `-k` keys or field separators.
- `tr` has ranges, `-c`, `-d`, `-s`, and backslash escapes; no `[:class:]`.
- `seq` is integer-only.
- `tail` has no `-f`.
- `chmod` takes octal modes and `[ugoa][+-=][rwxXst]` lists.
- `test` has no parentheses; `-a`/`-o` bind loosest, in that order.
- `mv` across filesystems copies then removes; `cp -a` is `-rp`.

Everything in the applet list has at least one passing case in
`tests/run.sh`; see the test names for the exact flags covered. The result
of the last container run is recorded in the commit message of each commit
that changed behavior.
