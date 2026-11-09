# nebox: Nelua multicall binary linked against libnelibc-standalone.
# Builds run in a Linux x86-64 container with Nelua and Zig (see AGENTS.md).
# Override NELUA, ZIG and NELIBC for your layout; NELIBC is a nelibc checkout
# with build/libnelibc-standalone-zig.a already built.
NELUA ?= nelua
ZIG ?= zig
ZIGFLAGS ?= -mcpu=x86_64
NELIBC ?= ../nelibc
NELIBC_LIB ?= $(NELIBC)/build/libnelibc-standalone-zig.a
# Nelua's binary cache keys on the generated C and the command line, not on
# the archive given in --ldflags: the archive's checksum goes into the C
# flags so that a rebuilt nelibc is linked instead of a cached binary.
NELIBC_STAMP = $(shell sha256sum $(NELIBC_LIB) 2>/dev/null | cut -c1-16)
OUT ?= build
NM ?= nm

SOURCES := src/nebox.nelua $(wildcard src/nebox/*.nelua) $(wildcard src/nebox/applets/*.nelua) $(wildcard src/nebox/awk/*.nelua) $(wildcard src/nebox/sh/*.nelua)

CFLAGS := -DNELIBC_STANDALONE -nostdlib -static -no-pie -fno-pie -fno-stack-protector \
  -ffreestanding -fno-builtin -fno-sanitize=all -Wl,-e,_start -Wl,--build-id=none \
  -I$(NELIBC)/include \
  -DNEBOX_NELIBC_STAMP=$(NELIBC_STAMP)
LDFLAGS := -Wl,--whole-archive $(NELIBC_LIB) -Wl,--no-whole-archive -Wl,--strip-all

.PHONY: all nebox test clean

all: nebox

nebox: $(OUT)/nebox

$(OUT)/nebox: $(SOURCES) Makefile $(NELIBC_LIB) | $(OUT)
	$(NELUA) -r -L src --cc '$(ZIG) cc $(ZIGFLAGS)' --cflags='$(CFLAGS)' --ldflags='$(LDFLAGS)' -o $@ src/nebox.nelua
	@test -z "$$($(NM) -u $@)" || { echo "undefined symbols:"; $(NM) -u $@; exit 1; }
	@echo "built $@ ($$(stat -c %s $@) bytes, static, no host libc)"

$(OUT):
	mkdir -p $(OUT)

$(NELIBC_LIB):
	$(MAKE) -C $(NELIBC) lib-standalone-zig NELUA="$(NELUA)" ZIG=$(ZIG)

test: $(OUT)/nebox
	sh tests/run.sh $(abspath $(OUT)/nebox)
	python3 tests/sh_interactive.py $(abspath $(OUT)/nebox)
	python3 tests/diff_fuzz.py $(abspath $(OUT)/nebox) 200
	python3 tests/patch_fuzz.py $(abspath $(OUT)/nebox) 200 < /dev/null
	python3 tests/dd_compare.py $(abspath $(OUT)/nebox) 300
	python3 tests/join_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/digest_compare.py $(abspath $(OUT)/nebox) 300
	python3 tests/basenc_compare.py $(abspath $(OUT)/nebox) 300
	python3 tests/opts_compare.py $(abspath $(OUT)/nebox)
	python3 tests/mode_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/tr_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/cutuniq_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/head_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/tail_compare.py $(abspath $(OUT)/nebox) 300
	python3 tests/nlcp_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/timeout_compare.py $(abspath $(OUT)/nebox)
	python3 tests/teemktemp_compare.py $(abspath $(OUT)/nebox)
	python3 tests/split_compare.py $(abspath $(OUT)/nebox)
	python3 tests/shuf_compare.py $(abspath $(OUT)/nebox)
	python3 tests/stat_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/rm_compare.py $(abspath $(OUT)/nebox)
	python3 tests/ln_compare.py $(abspath $(OUT)/nebox)
	python3 tests/df_compare.py $(abspath $(OUT)/nebox)
	python3 tests/du_compare.py $(abspath $(OUT)/nebox)
	python3 tests/chown_compare.py $(abspath $(OUT)/nebox)
	python3 tests/cp_compare.py $(abspath $(OUT)/nebox)
	python3 tests/mv_compare.py $(abspath $(OUT)/nebox)
	python3 tests/install_compare.py $(abspath $(OUT)/nebox)
	python3 tests/touch_compare.py $(abspath $(OUT)/nebox)
	python3 tests/truncate_compare.py $(abspath $(OUT)/nebox)
	python3 tests/smallcore_compare.py $(abspath $(OUT)/nebox)
	python3 tests/tac_compare.py $(abspath $(OUT)/nebox) 300
	python3 tests/tsort_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/test_compare.py $(abspath $(OUT)/nebox) 3000
	python3 tests/env_compare.py $(abspath $(OUT)/nebox)
	python3 tests/printf_compare.py $(abspath $(OUT)/nebox) 2000
	python3 tests/expr_compare.py $(abspath $(OUT)/nebox) 3000
	python3 tests/factor_compare.py $(abspath $(OUT)/nebox) 600
	python3 tests/cmp_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/od_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/hexdump_compare.py $(abspath $(OUT)/nebox) 3000
	python3 tests/realpath_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/sort_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/wcid_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/expand_compare.py $(abspath $(OUT)/nebox) 500
	python3 tests/xargs_compare.py $(abspath $(OUT)/nebox) 300
	python3 tests/ls_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/find_compare.py $(abspath $(OUT)/nebox) 2000
	python3 tests/date_compare.py $(abspath $(OUT)/nebox) 3000
	python3 tests/grep_compare.py $(abspath $(OUT)/nebox) 3000
	python3 tests/sed_compare.py $(abspath $(OUT)/nebox) 3000
	python3 tests/rev_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/strings_compare.py $(abspath $(OUT)/nebox) 400
	python3 tests/groups_compare.py $(abspath $(OUT)/nebox)
	python3 tests/which_compare.py $(abspath $(OUT)/nebox)
	python3 tests/sync_compare.py $(abspath $(OUT)/nebox)
	python3 tests/free_compare.py $(abspath $(OUT)/nebox) 300

clean:
	rm -rf $(OUT)
