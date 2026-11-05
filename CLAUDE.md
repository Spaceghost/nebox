Read `AGENTS.md`; it is binding. Build and test only via `tools/remote.sh`
(a container with Nelua, Zig and nelibc; see the env vars in AGENTS.md).
Sources: `src/nebox.nelua` (dispatch), `src/nebox/sys.nelua` (nelibc imports),
`src/nebox/util.nelua` (I/O, options), `src/nebox/regex.nelua` (BRE/ERE
engine), `src/nebox/applets/*.nelua`. Tests: `tests/run.sh`.
