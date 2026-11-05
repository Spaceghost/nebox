#!/bin/sh
# Sync this checkout into the nelibc-writ container on bak and run make there
# as the unprivileged build user. Usage: tools/remote.sh [make targets...]
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
HOST=${NEBOX_HOST:-bak}
CONTAINER=${NEBOX_CONTAINER:-nelibc-writ}
DEST=${NEBOX_DEST:-/work/nebox}
targets=${*:-test}
cd "$ROOT"
tar cf - --exclude=build --exclude=.git . | ssh "$HOST" "incus exec $CONTAINER -- sh -c '
  mkdir -p $DEST && cd $DEST && tar xf - && chown -R build . &&
  su build -c \"cd $DEST && HOME=/home/build TMPDIR=/work/tmp make $targets NELUA=\\\"/opt/nelua/nelua --cache-dir /work/nelua-cache\\\"\"'"
