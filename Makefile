# nebox: Nelua multicall binary linked against libnelibc-standalone.
# The native AArch64 build uses GCC. Other supported Linux builds use Zig.
NELUA ?= nelua
ZIG ?= zig
ZIGFLAGS ?= -mcpu=x86_64
NELIBC ?= ../nelibc
ARCH ?= $(shell uname -m)
ifeq ($(ARCH),aarch64)
NEBOX_CC := gcc -mno-outline-atomics
NELIBC_TARGET := lib-standalone-aarch64-gcc
NELIBC_LIB ?= $(NELIBC)/build/libnelibc-standalone-aarch64-gcc.a
NELIBC_LDFLAGS = -Wl,-u,_start,--gc-sections $(NELIBC_LIB) -lgcc
else
NEBOX_CC := $(ZIG) cc $(ZIGFLAGS)
NELIBC_TARGET := lib-standalone-zig
NELIBC_LIB ?= $(NELIBC)/build/libnelibc-standalone-zig.a
NELIBC_LDFLAGS = -Wl,--whole-archive $(NELIBC_LIB) -Wl,--no-whole-archive
endif
# Nelua's binary cache keys on the generated C and the command line, not on
# the archive given in --ldflags: the archive's checksum goes into the C
# flags so that a rebuilt nelibc is linked instead of a cached binary.
NELIBC_STAMP = $(shell sha256sum $(NELIBC_LIB) 2>/dev/null | cut -c1-16)
OUT ?= $(if $(THESEUS_FLAGS),build-theseus,build)$(if $(strip $(PCRE2_LIB)),-pcre2)
NM ?= nm

# Opt in to Theseus early boot with a checkout and the Spaceghost Nelua fork.
ifneq ($(strip $(THESEUS)),)
THESEUS_FLAGS := -L $(THESEUS)/src -D THESEUS_BOOT=true
endif

SOURCES := src/nebox.nelua $(wildcard src/nebox/*.nelua) $(wildcard src/nebox/applets/*.nelua) $(wildcard src/nebox/awk/*.nelua) $(wildcard src/nebox/sh/*.nelua)

SOURCES += $(if $(THESEUS_FLAGS),$(THESEUS)/src/theseus/earlyboot.nelua)

CFLAGS := -DNELIBC_STANDALONE -nostdlib -static -no-pie -fno-pie -fno-stack-protector \
  -ffreestanding -fno-builtin -fno-sanitize=all -Wl,-e,_start -Wl,--build-id=none \
  -I$(NELIBC)/include \
  -DNEBOX_NELIBC_STAMP=$(NELIBC_STAMP)
LDFLAGS := $(NELIBC_LDFLAGS) -Wl,--strip-all

# Optional 8-bit PCRE2 archive built for the standalone libc environment.
ifneq ($(strip $(PCRE2_LIB)),)
PCRE2_STAMP := $(shell sha256sum $(PCRE2_LIB) 2>/dev/null | cut -c1-16)
PCRE2_FLAGS := -D NEBOX_PCRE2=true
PCRE2_CFLAGS := -DPCRE2_CODE_UNIT_WIDTH=8 -DNEBOX_PCRE2_STAMP=$(PCRE2_STAMP) $(if $(PCRE2_INCLUDE),-I$(PCRE2_INCLUDE))
PCRE2_LDFLAGS := $(PCRE2_LIB)
endif


.PHONY: all nebox nebuild test test-nebuild clean

all: nebox

nebox: $(OUT)/nebox

$(OUT)/nebox: $(SOURCES) Makefile $(NELIBC_LIB) $(PCRE2_LIB) | $(OUT)
	$(NELUA) -r -L src $(THESEUS_FLAGS) $(PCRE2_FLAGS) --cc '$(NEBOX_CC)' --cflags='$(CFLAGS) $(PCRE2_CFLAGS)' --ldflags='$(PCRE2_LDFLAGS) $(LDFLAGS)' -o $@ src/nebox.nelua
	@test -z "$$($(NM) -u $@)" || { echo "undefined symbols:"; $(NM) -u $@; exit 1; }
	@echo "built $@ ($$(stat -c %s $@) bytes, static, no host libc)"

nebuild: $(OUT)/nebuild

$(OUT)/nebuild: tools/nebuild.nelua src/nebuild/sys.nelua Makefile $(NELIBC_LIB) | $(OUT)
	$(NELUA) -r -L src --cc '$(NEBOX_CC)' --cflags='$(CFLAGS)' --ldflags='$(NELIBC_LDFLAGS)' -o $@ tools/nebuild.nelua
	@undefined=$$($(NM) -u $@) && test -z "$$undefined" || { echo "$$undefined"; exit 1; }

test-nebuild: $(OUT)/nebuild
	python3 tests/nebuild.py $(abspath $(OUT)/nebuild)

$(OUT):
	mkdir -p $(OUT)

$(NELIBC_LIB):
	$(MAKE) -C $(NELIBC) $(NELIBC_TARGET) NELUA="$(NELUA)" ZIG=$(ZIG)

.PHONY: applet-coverage applet-parity update-applet-coverage

applet-coverage: $(OUT)/nebox
	@python3 tools/applet_coverage.py $(abspath $<)

applet-parity: $(OUT)/nebox
	@python3 tools/applet_coverage.py $(abspath $<) --require-complete

update-applet-coverage: $(OUT)/nebox
ifneq ($(strip $(THESEUS)),)
	$(error The checked-in coverage report uses the standalone build)
endif
	@python3 tools/applet_coverage.py $(abspath $<) > $(OUT)/applet-coverage.md
	@cp $(OUT)/applet-coverage.md docs/APPLET-COVERAGE.md

test: $(OUT)/nebox
ifeq ($(strip $(THESEUS)),)
	python3 tools/applet_coverage.py $(abspath $<) --check-report
endif
	sh tests/run.sh $(abspath $(OUT)/nebox)
	python3 tests/setsid.py $(abspath $(OUT)/nebox)
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
	python3 tests/kill_compare.py $(abspath $(OUT)/nebox)
	python3 tests/hostname_compare.py $(abspath $(OUT)/nebox)

clean:
	rm -rf $(OUT)
