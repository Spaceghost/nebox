# Applet queue

The queue covers 37 commands. Each entry stays open until the native applet
builds against standalone Nelibc and its tests pass in the Linux x86-64
container. Compare behavior with BusyBox and Toybox where each supplies the
applet. Record differences in the Nebox documentation and test the public
CLI through both multicall dispatch and installed links.

## 1. Archives

Start with gzip streams and tar, which Cascadia's installer and package
workflows already exercise. Share the gzip decoder across all three
entry points.

### Installer path

- [x] `gzip` — create and validate gzip streams, including stdin/stdout.
- [x] `gunzip` — extract files and streams with gzip trailer validation.
- [x] `zcat` — decode gzip inputs to stdout and handle concatenated members.
- [x] `tar` — list, create and extract tar, including gzip-compressed archives.

### Other formats

- [ ] `cpio` — read and write newc archives for initramfs.
- [ ] `bzip2` — compress, decompress and verify bzip2 streams.
- [ ] `unzip` — list and extract ZIP entries, including deflate.
- [ ] `xzcat` — stream xz data to stdout.

Test truncation, malformed headers and archive paths, links, and extraction
outside the target directory. Run the Cascadia installer archive smoke
test before selecting Nebox's tar and gzip as package providers.

## 2. User accounts

Build account database locking, atomic updates, and UID/GID allocation
together. Exercise the Alpine nginx account-creation flags in a disposable
Cascadia root. Test password and session operations against a private account
database in the guest.

### Account database

- [ ] `adduser` — create a user and support system accounts and group membership.
- [ ] `addgroup` — create a group and add a user to an existing group.
- [ ] `deluser` — remove accounts and honor explicit home deletion.
- [ ] `delgroup` — remove groups or membership and protect primary groups.
- [ ] `passwd` — update and lock password entries with consistent permissions.

### Sessions

- [ ] `login` — authenticate and initialize a new TTY session.
- [ ] `su` — switch identities and launch a shell with the selected environment.

## 3. Networking

Share address parsing across inspection and socket commands. Exercise
configuration in isolated network namespaces with local peers.

### Interface and address management

- [ ] `ip` — inspect and configure links, addresses, and routes via Netlink.
- [ ] `ifconfig` — inspect interfaces and apply the common address and link flags.
- [ ] `udhcpc` — acquire, renew and release a lease against an isolated DHCP server.

### Diagnostics and clients

- [ ] `ping` — handle ICMP echo, limits and deadlines for IPv4 and IPv6.
- [ ] `nslookup` — query the resolver or a selected server.
- [ ] `wget` — download HTTP and HTTPS, with redirects and certificate checks.
- [ ] `nc` — connect and listen with TCP/UDP and expose useful timeouts.

## 4. Processes and logs

Share a procfs reader and process selection across the process tools.
Exercise the log sender and receiver on a private Unix socket.

### Processes

- [ ] `ps` — report process state with common filters and output columns.
- [ ] `top` — refresh process and system statistics in interactive and batch modes.
- [ ] `pgrep` — match process names and command lines with stable exit codes.
- [ ] `pkill` — reuse process selection and signal matching processes.
- [ ] `pidof` — find process IDs by executable name or path.

### Logs

- [ ] `logger` — send messages with facility, priority, and tag.
- [ ] `syslogd` — receive local messages and write them with safe socket permissions.

## 5. Boot and devices

Use disposable QEMU guests for PID 1, console, module, device, and power
operations. Verify error paths in addition to successful boot and shutdown.

### Devices and diagnostics

- [ ] `mdev` — scan sysfs and handle device events with rule-driven permissions.
- [ ] `modprobe` — resolve module aliases and dependencies and load or unload them.
- [ ] `lsmod` — list loaded modules and their dependencies.
- [ ] `dmesg` — read and format kernel messages and report permission failures.

### Console and lifecycle

- [ ] `getty` — configure a TTY and hand off to login.
- [ ] `switch_root` — switch mounts and execute init from the new root as PID 1.
- [ ] `reboot` — request a reboot through init and qualify the direct mode in QEMU.
- [ ] `poweroff` — request shutdown through init and verify the guest powers off.
