Read `AGENTS.md`; it is binding. Build and test only via `tools/remote.sh`
(container `nelibc-writ` on bak). Sources: `src/nebox.nelua` (dispatch),
`src/nebox/sys.nelua` (nelibc imports), `src/nebox/util.nelua` (I/O, options),
`src/nebox/applets/{text,fs,proc}.nelua`. Tests: `tests/run.sh`.
