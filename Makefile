# nebox: Nelua multicall binary linked against libnelibc-standalone.
# Builds run inside the Incus container nelibc-writ on bak (see AGENTS.md);
# the defaults below are that container's paths.
NELUA ?= /opt/nelua/nelua
ZIG ?= /opt/zig/zig
ZIGFLAGS ?= -mcpu=x86_64
NELIBC ?= /work/nelibc
NELIBC_LIB ?= $(NELIBC)/build/libnelibc-standalone-zig.a
OUT ?= build
NM ?= nm

SOURCES := src/nebox.nelua src/nebox/sys.nelua src/nebox/util.nelua \
  src/nebox/applets/text.nelua src/nebox/applets/fs.nelua src/nebox/applets/proc.nelua

CFLAGS := -DNELIBC_STANDALONE -nostdlib -static -no-pie -fno-pie -fno-stack-protector \
  -ffreestanding -fno-builtin -fno-sanitize=all -Wl,-e,_start -Wl,--build-id=none \
  -I$(NELIBC)/include
LDFLAGS := -Wl,--whole-archive $(NELIBC_LIB) -Wl,--no-whole-archive

.PHONY: all build test clean nelibc

all: build

build: $(OUT)/nebox

$(OUT)/nebox: $(SOURCES) $(NELIBC_LIB) | $(OUT)
	$(NELUA) -r -L src --cc '$(ZIG) cc $(ZIGFLAGS)' --cflags='$(CFLAGS)' --ldflags='$(LDFLAGS)' -o $@ src/nebox.nelua
	@test -z "$$($(NM) -u $@)" || { echo "undefined symbols:"; $(NM) -u $@; exit 1; }
	@echo "built $@ ($$(stat -c %s $@) bytes, static, no host libc)"

$(OUT):
	mkdir -p $(OUT)

$(NELIBC_LIB):
	$(MAKE) -C $(NELIBC) lib-standalone-zig NELUA="$(NELUA)" ZIG=$(ZIG)

test: $(OUT)/nebox
	sh tests/run.sh $(abspath $(OUT)/nebox)

clean:
	rm -rf $(OUT)
