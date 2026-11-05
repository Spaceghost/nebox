# nebox agent agreement

- Branch `main`, direct pushes, no PRs unless asked, never force-push.
- Never compile or run tests on a workstation. Build and test inside a
  disposable Linux x86-64 container that has Nelua, Zig and a nelibc checkout
  with `build/libnelibc-standalone-zig.a` built. `tools/remote.sh` syncs the
  tree into such a container over ssh + incus and runs `make test` there; it
  takes the host, container and paths from `NEBOX_HOST`, `NEBOX_CONTAINER`,
  `NEBOX_DEST` and `NEBOX_NELIBC` (set them in your shell, never in the repo).
- Every applet claim in README.md must be backed by a case in `tests/run.sh`
  that passed in that container. Unsupported behavior is listed as
  unsupported, not written around.
- Nelua only in `src/`; nothing from a host libc. The binary must link with no
  undefined symbols (`make` checks `nm -u`).
- Do not run `make` in the nelibc checkout while a nelibc gate is running there.
- No machine names, host paths or credentials in the repository; machine
  values belong in environment variables.
