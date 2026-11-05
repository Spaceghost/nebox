# nebox agent agreement

- Branch `main`, direct pushes, no PRs unless asked, never force-push.
- Never compile or run tests on the workstation. Build and test inside the
  Incus container `nelibc-writ` on bak: `tools/remote.sh` syncs the tree to
  `/work/nebox` and runs `make test` there as the `build` user, against the
  nelibc checkout at `/work/nelibc` (`build/libnelibc-standalone-zig.a`).
- Every applet claim in README.md must be backed by a case in `tests/run.sh`
  that passed in that container. Unsupported behavior is listed as
  unsupported, not written around.
- Nelua only in `src/`; nothing from a host libc. The binary must link with no
  undefined symbols (`make` checks `nm -u`).
- Do not run `make` in `/work/nelibc` while a nelibc gate is running there.
