# nebox: Nelua multicall binary linked against libnelibc-standalone.
# Builds run in a Linux x86-64 container with Nelua and Zig (see AGENTS.md).
# Override NELUA, ZIG and NELIBC for your layout; NELIBC is a nelibc checkout
# with build/libnelibc-standalone-zig.a already built.
NELUA ?= nelua
ZIG ?= zig
ZIGFLAGS ?= -mcpu=x86_64
NELIBC ?= ../nelibc
NELIBC_LIB ?= $(NELIBC)/build/libnelibc-standalone-zig.a
OUT ?= build
NM ?= nm

SOURCES := src/nebox.nelua $(wildcard src/nebox/*.nelua) $(wildcard src/nebox/applets/*.nelua) $(wildcard src/nebox/awk/*.nelua) $(wildcard src/nebox/sh/*.nelua)

CFLAGS := -DNELIBC_STANDALONE -nostdlib -static -no-pie -fno-pie -fno-stack-protector \
  -ffreestanding -fno-builtin -fno-sanitize=all -Wl,-e,_start -Wl,--build-id=none \
  -I$(NELIBC)/include
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

clean:
	rm -rf $(OUT)
