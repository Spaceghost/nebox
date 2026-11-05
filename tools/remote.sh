#!/bin/sh
# Sync this checkout into a remote Incus container and run make there as an
# unprivileged build user. Usage: tools/remote.sh [make targets...]
# Required: NEBOX_HOST (ssh target) and NEBOX_CONTAINER (incus instance).
# Optional: NEBOX_DEST (tree location in the container, default /work/nebox),
# NEBOX_NELIBC (nelibc checkout there, default /work/nelibc), NEBOX_USER
# (default build), NEBOX_NELUA / NEBOX_ZIG (compiler paths in the container).
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
: "${NEBOX_HOST:?set NEBOX_HOST to the ssh target that runs incus}"
: "${NEBOX_CONTAINER:?set NEBOX_CONTAINER to the incus instance name}"
DEST=${NEBOX_DEST:-/work/nebox}
NELIBC=${NEBOX_NELIBC:-/work/nelibc}
USER_=${NEBOX_USER:-build}
NELUA=${NEBOX_NELUA:-nelua}
ZIG=${NEBOX_ZIG:-zig}
targets=${*:-test}
cd "$ROOT"
tar cf - --exclude=build --exclude=.git . | ssh "$NEBOX_HOST" "incus exec $NEBOX_CONTAINER -- sh -c '
  mkdir -p $DEST && cd $DEST && tar xf - && chown -R $USER_ . &&
  su $USER_ -c \"cd $DEST && TMPDIR=\\\${TMPDIR:-/tmp} make $targets NELIBC=$NELIBC NELUA=\\\"$NELUA\\\" ZIG=\\\"$ZIG\\\"\"'"
