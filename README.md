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
[ basename cat chmod cp cut date dirname echo env false grep head hostname
id kill ln ls mkdir mv nl nproc printenv printf pwd readlink rev rm rmdir
seq sleep sort sync tail tee test touch tr true uname uniq wc which yes
```

`nebox --list` prints the names; `nebox --install [-s] DIR` creates one link
per applet in `DIR`.

## Known limits

Stated here rather than worked around:

- `grep` matches fixed strings only. `-E`/`-G` exit 2 with a message.
- `date` prints UTC. nelibc has no zone database, so there is no local time.
  `-d` understands only `@SECONDS`; setting the date is unsupported.
- `ls` prints one entry per line in every mode (no columns), and `-l` shows
  numeric uid/gid: nelibc has no `getpwuid`/`getgrgid`.
- `id` prints numeric ids and only the primary group.
- `sort` offers `-r -n -u -f -o`; no `-k` keys or field separators.
- `tr` has ranges, `-c`, `-d`, `-s`, and backslash escapes; no `[:class:]`.
- `seq` is integer-only.
- `tail` has no `-f`.
- `chmod` takes octal modes and `[ugoa][+-=][rwxXst]` lists.
- `test` has no parentheses; `-a`/`-o` bind loosest, in that order.
- `mv` across filesystems copies then removes; `cp -a` is `-rp`.

Everything in the applet list has at least one passing case in
`tests/run.sh`; see the test names for the exact flags covered. Status of
the last container run is recorded in the commit messages, not here.
