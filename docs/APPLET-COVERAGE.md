# Applet coverage

The target includes every applet declared by BusyBox 1.38.0 or Toybox 0.8.15, including aliases and optional commands. The two multiplexer names are excluded.

The standalone Nebox binary reports executable applets through `--list`. Toybox also declares shell-only commands. Nebox checks these using `command -v` inside its own shell with an unusable PATH. A name is covered when every dispatch form declared upstream is present. Individual tests exercise behavior and options.

| Upstream catalog | Covered | Missing | Total |
|---|---:|---:|---:|
| Both projects | 118 | 154 | 272 |
| BusyBox only | 4 | 163 | 167 |
| Toybox only | 26 | 59 | 85 |
| Union | 148 | 376 | 524 |

## Applet names

A dash in a Nebox column means neither upstream requires that form.

| Applet | BusyBox | Toybox | Nebox executable | Nebox shell |
|---|:---:|:---:|---|---|
| `-bash` |  | yes | Missing | — |
| `-sh` |  | yes | Missing | — |
| `-toysh` |  | yes | Missing | — |
| `.` |  | shell | — | Builtin |
| `:` |  | shell | — | Builtin |
| `[` | yes | yes | Registered | — |
| `[[` | yes | shell | Missing | Missing |
| `acpi` |  | yes | Missing | — |
| `acpid` | yes |  | Missing | — |
| `add-shell` | yes |  | Missing | — |
| `addgroup` | yes | yes | Missing | — |
| `adduser` | yes | yes | Missing | — |
| `adjtimex` | yes |  | Missing | — |
| `alias` |  | shell | — | Builtin |
| `ar` | yes |  | Missing | — |
| `arch` | yes | yes | Registered | — |
| `arp` | yes | yes | Missing | — |
| `arping` | yes | yes | Missing | — |
| `ascii` | yes | yes | Missing | — |
| `ash` | yes |  | Missing | — |
| `awk` | yes | yes | Registered | — |
| `base32` | yes | yes | Registered | — |
| `base64` | yes | yes | Registered | — |
| `basename` | yes | yes | Registered | — |
| `bash` | yes | yes | Missing | — |
| `bbconfig` | yes |  | Missing | — |
| `bc` | yes | yes | Missing | — |
| `beep` | yes |  | Missing | — |
| `blkdiscard` | yes | yes | Missing | — |
| `blkid` | yes | yes | Missing | — |
| `blockdev` | yes | yes | Missing | — |
| `bootchartd` | yes | yes | Missing | — |
| `brctl` | yes | yes | Missing | — |
| `break` |  | shell | — | Builtin |
| `bunzip2` | yes | yes | Missing | — |
| `bzcat` | yes | yes | Missing | — |
| `bzip2` | yes |  | Missing | — |
| `cal` | yes | yes | Missing | — |
| `cat` | yes | yes | Registered | — |
| `cd` |  | shell | — | Builtin |
| `chat` | yes |  | Missing | — |
| `chattr` | yes | yes | Missing | — |
| `chcon` | yes | yes | Missing | — |
| `chgrp` | yes | yes | Registered | — |
| `chmod` | yes | yes | Registered | — |
| `chown` | yes | yes | Registered | — |
| `chpasswd` | yes |  | Missing | — |
| `chpst` | yes |  | Missing | — |
| `chroot` | yes | yes | Registered | — |
| `chrt` | yes | yes | Missing | — |
| `chsh` |  | yes | Missing | — |
| `chvt` | yes | yes | Missing | — |
| `cksum` | yes | yes | Registered | — |
| `clear` | yes | yes | Registered | — |
| `cmp` | yes | yes | Registered | — |
| `comm` | yes | yes | Registered | — |
| `command` |  | shell | — | Builtin |
| `conspy` | yes |  | Missing | — |
| `continue` |  | shell | — | Builtin |
| `count` |  | yes | Missing | — |
| `cp` | yes | yes | Registered | — |
| `cpio` | yes | yes | Missing | — |
| `crc32` | yes | yes | Missing | — |
| `crond` | yes | yes | Missing | — |
| `crontab` | yes | yes | Missing | — |
| `cryptpw` | yes |  | Missing | — |
| `csplit` |  | yes | Registered | — |
| `cttyhack` | yes |  | Missing | — |
| `cut` | yes | yes | Registered | — |
| `date` | yes | yes | Registered | — |
| `dc` | yes |  | Missing | — |
| `dd` | yes | yes | Registered | — |
| `deallocvt` | yes | yes | Missing | — |
| `declare` |  | shell | — | Missing |
| `delgroup` | yes | yes | Missing | — |
| `deluser` | yes | yes | Missing | — |
| `demo_many_options` |  | yes | Missing | — |
| `demo_number` |  | yes | Missing | — |
| `demo_scankey` |  | yes | Missing | — |
| `demo_utf8towc` |  | yes | Missing | — |
| `depmod` | yes |  | Missing | — |
| `devfsd` | yes |  | Missing | — |
| `devmem` | yes | yes | Missing | — |
| `df` | yes | yes | Registered | — |
| `dhcp` |  | yes | Missing | — |
| `dhcp6` |  | yes | Missing | — |
| `dhcpd` |  | yes | Missing | — |
| `dhcprelay` | yes |  | Missing | — |
| `diff` | yes | yes | Registered | — |
| `dirname` | yes | yes | Registered | — |
| `dmesg` | yes | yes | Missing | — |
| `dnsd` | yes |  | Missing | — |
| `dnsdomainname` | yes | yes | Registered | — |
| `dos2unix` | yes | yes | Missing | — |
| `dpkg` | yes |  | Missing | — |
| `dpkg-deb` | yes |  | Missing | — |
| `du` | yes | yes | Registered | — |
| `dumpkmap` | yes |  | Missing | — |
| `dumpleases` | yes | yes | Missing | — |
| `echo` | yes | yes | Registered | — |
| `ed` | yes |  | Missing | — |
| `egrep` | yes | yes | Registered | — |
| `eject` | yes | yes | Missing | — |
| `env` | yes | yes | Registered | — |
| `envdir` | yes |  | Missing | — |
| `envuidgid` | yes |  | Missing | — |
| `ether-wake` | yes |  | Missing | — |
| `eval` |  | shell | — | Builtin |
| `exec` |  | shell | — | Builtin |
| `exit` |  | shell | — | Builtin |
| `expand` | yes | yes | Registered | — |
| `export` |  | shell | — | Builtin |
| `expr` | yes | yes | Registered | — |
| `factor` | yes | yes | Registered | — |
| `fakeidentd` | yes |  | Missing | — |
| `fallocate` | yes | yes | Missing | — |
| `false` | yes | yes | Registered | — |
| `fatattr` | yes |  | Missing | — |
| `fbset` | yes |  | Missing | — |
| `fbsplash` | yes |  | Missing | — |
| `fdflush` | yes |  | Missing | — |
| `fdformat` | yes |  | Missing | — |
| `fdisk` | yes | yes | Missing | — |
| `fgconsole` | yes |  | Missing | — |
| `fgrep` | yes | yes | Registered | — |
| `file` |  | yes | Missing | — |
| `find` | yes | yes | Registered | — |
| `findfs` | yes |  | Missing | — |
| `flash_eraseall` | yes |  | Missing | — |
| `flash_lock` | yes |  | Missing | — |
| `flash_unlock` | yes |  | Missing | — |
| `flashcp` | yes |  | Missing | — |
| `flock` | yes | yes | Missing | — |
| `fmt` |  | yes | Registered | — |
| `fold` | yes | yes | Registered | — |
| `free` | yes | yes | Registered | — |
| `freeramdisk` | yes | yes | Missing | — |
| `fsck` | yes | yes | Missing | — |
| `fsck.minix` | yes |  | Missing | — |
| `fsfreeze` | yes | yes | Missing | — |
| `fstrim` | yes |  | Missing | — |
| `fstype` |  | yes | Missing | — |
| `fsync` | yes | yes | Registered | — |
| `ftpd` | yes |  | Missing | — |
| `ftpget` | yes | yes | Missing | — |
| `ftpput` | yes | yes | Missing | — |
| `fuser` | yes |  | Missing | — |
| `getconf` |  | yes | Missing | — |
| `getenforce` | yes | yes | Missing | — |
| `getfattr` | yes | yes | Missing | — |
| `getopt` | yes | yes | Missing | — |
| `getsebool` | yes |  | Missing | — |
| `getty` | yes | yes | Missing | — |
| `gitcheckout` |  | yes | Missing | — |
| `gitclone` |  | yes | Missing | — |
| `gitfetch` |  | yes | Missing | — |
| `gitinit` |  | yes | Missing | — |
| `gitremote` |  | yes | Missing | — |
| `gpiodetect` |  | yes | Missing | — |
| `gpiofind` |  | yes | Missing | — |
| `gpioget` |  | yes | Missing | — |
| `gpioinfo` |  | yes | Missing | — |
| `gpioset` |  | yes | Missing | — |
| `grep` | yes | yes | Registered | — |
| `groupadd` |  | yes | Missing | — |
| `groupdel` |  | yes | Missing | — |
| `groups` | yes | yes | Registered | — |
| `gunzip` | yes | yes | Registered | — |
| `gzip` | yes | yes | Registered | — |
| `halt` | yes | yes | Missing | — |
| `hd` | yes | yes | Registered | — |
| `hdparm` | yes |  | Missing | — |
| `head` | yes | yes | Registered | — |
| `hello` |  | yes | Missing | — |
| `help` |  | yes | Missing | — |
| `hexdump` | yes | yes | Registered | — |
| `hexedit` | yes | yes | Missing | — |
| `host` |  | yes | Missing | — |
| `hostid` | yes | yes | Registered | — |
| `hostname` | yes | yes | Registered | — |
| `httpd` | yes | yes | Missing | — |
| `hush` | yes |  | Missing | — |
| `hwclock` | yes | yes | Missing | — |
| `i2cdetect` | yes | yes | Missing | — |
| `i2cdump` | yes | yes | Missing | — |
| `i2cget` | yes | yes | Missing | — |
| `i2cset` | yes | yes | Missing | — |
| `i2ctransfer` | yes | yes | Missing | — |
| `iconv` |  | yes | Missing | — |
| `id` | yes | yes | Registered | — |
| `ifconfig` | yes | yes | Missing | — |
| `ifdown` | yes |  | Missing | — |
| `ifenslave` | yes |  | Missing | — |
| `ifplugd` | yes |  | Missing | — |
| `ifup` | yes |  | Missing | — |
| `inetd` | yes |  | Missing | — |
| `init` | yes | yes | Missing | — |
| `inotifyd` | yes | yes | Missing | — |
| `insmod` | yes | yes | Missing | — |
| `install` | yes | yes | Registered | — |
| `ionice` | yes | yes | Missing | — |
| `iorenice` |  | yes | Missing | — |
| `iostat` | yes |  | Missing | — |
| `iotop` |  | yes | Missing | — |
| `ip` | yes | yes | Missing | — |
| `ipaddr` | yes | yes | Missing | — |
| `ipcalc` | yes |  | Missing | — |
| `ipcrm` | yes | yes | Missing | — |
| `ipcs` | yes | yes | Missing | — |
| `iplink` | yes | yes | Missing | — |
| `ipneigh` | yes |  | Missing | — |
| `iproute` | yes | yes | Missing | — |
| `iprule` | yes | yes | Missing | — |
| `iptunnel` | yes | yes | Missing | — |
| `jobs` |  | shell | — | Builtin |
| `kbd_mode` | yes |  | Missing | — |
| `kill` | yes | yes | Registered | — |
| `killall` | yes | yes | Missing | — |
| `killall5` | yes | yes | Missing | — |
| `klogd` | yes | yes | Missing | — |
| `last` | yes | yes | Missing | — |
| `less` | yes |  | Missing | — |
| `link` | yes | yes | Registered | — |
| `linux32` | yes | yes | Missing | — |
| `linux64` | yes |  | Missing | — |
| `linuxrc` | yes |  | Missing | — |
| `ln` | yes | yes | Registered | — |
| `load_policy` | yes | yes | Missing | — |
| `loadfont` | yes |  | Missing | — |
| `loadkmap` | yes |  | Missing | — |
| `local` |  | shell | — | Builtin |
| `log` |  | yes | Missing | — |
| `logger` | yes | yes | Missing | — |
| `login` | yes | yes | Missing | — |
| `logname` | yes | yes | Registered | — |
| `logpath` |  | yes | Missing | — |
| `logread` | yes |  | Missing | — |
| `losetup` | yes | yes | Missing | — |
| `lpd` | yes |  | Missing | — |
| `lpq` | yes |  | Missing | — |
| `lpr` | yes |  | Missing | — |
| `ls` | yes | yes | Registered | — |
| `lsattr` | yes | yes | Missing | — |
| `lsblk` | yes |  | Missing | — |
| `lsmod` | yes | yes | Registered | — |
| `lsof` | yes | yes | Missing | — |
| `lspci` | yes | yes | Missing | — |
| `lsscsi` | yes |  | Missing | — |
| `lsusb` | yes | yes | Missing | — |
| `lzcat` | yes |  | Missing | — |
| `lzma` | yes |  | Missing | — |
| `lzop` | yes |  | Missing | — |
| `lzopcat` | yes |  | Missing | — |
| `makedevs` | yes | yes | Missing | — |
| `makemime` | yes |  | Missing | — |
| `man` | yes | yes | Missing | — |
| `matchpathcon` | yes |  | Missing | — |
| `mcookie` |  | yes | Registered | — |
| `md5sum` | yes | yes | Registered | — |
| `mdev` | yes | yes | Missing | — |
| `memeater` |  | yes | Missing | — |
| `mesg` | yes |  | Missing | — |
| `microcom` | yes | yes | Missing | — |
| `mim` | yes |  | Missing | — |
| `minips` | yes |  | Missing | — |
| `mix` |  | yes | Missing | — |
| `mkdir` | yes | yes | Registered | — |
| `mkdosfs` | yes |  | Missing | — |
| `mke2fs` | yes |  | Missing | — |
| `mkfifo` | yes | yes | Registered | — |
| `mkfs.ext2` | yes |  | Missing | — |
| `mkfs.minix` | yes |  | Missing | — |
| `mkfs.reiser` | yes |  | Missing | — |
| `mkfs.vfat` | yes |  | Missing | — |
| `mknod` | yes | yes | Registered | — |
| `mkpasswd` | yes | yes | Missing | — |
| `mkswap` | yes | yes | Missing | — |
| `mktemp` | yes | yes | Registered | — |
| `modinfo` | yes | yes | Missing | — |
| `modprobe` | yes | yes | Missing | — |
| `more` | yes | yes | Missing | — |
| `mount` | yes | yes | Registered | — |
| `mountpoint` | yes | yes | Missing | — |
| `mpstat` | yes |  | Missing | — |
| `mt` | yes |  | Missing | — |
| `mv` | yes | yes | Registered | — |
| `nameif` | yes |  | Missing | — |
| `nanddump` | yes |  | Missing | — |
| `nandwrite` | yes |  | Missing | — |
| `nbd-client` | yes | yes | Missing | — |
| `nbd-server` |  | yes | Missing | — |
| `nbd_client` |  | yes | Missing | — |
| `nbd_server` |  | yes | Missing | — |
| `nc` | yes | yes | Missing | — |
| `netcat` | yes | yes | Missing | — |
| `netstat` | yes | yes | Missing | — |
| `nice` | yes | yes | Registered | — |
| `nl` | yes | yes | Registered | — |
| `nmeter` | yes |  | Missing | — |
| `nohup` | yes | yes | Registered | — |
| `nologin` | yes | yes | Missing | — |
| `nproc` | yes | yes | Registered | — |
| `nsenter` | yes | yes | Missing | — |
| `nslookup` | yes |  | Missing | — |
| `ntpd` | yes |  | Missing | — |
| `nuke` | yes |  | Missing | — |
| `od` | yes | yes | Registered | — |
| `oneit` |  | yes | Missing | — |
| `openvt` | yes | yes | Missing | — |
| `partprobe` | yes | yes | Missing | — |
| `passwd` | yes | yes | Missing | — |
| `paste` | yes | yes | Registered | — |
| `patch` | yes | yes | Registered | — |
| `pgrep` | yes | yes | Missing | — |
| `pidof` | yes | yes | Registered | — |
| `ping` | yes | yes | Missing | — |
| `ping6` | yes | yes | Missing | — |
| `pipe_progress` | yes |  | Missing | — |
| `pivot_root` | yes | yes | Missing | — |
| `pkill` | yes | yes | Missing | — |
| `pmap` | yes | yes | Missing | — |
| `popmaildir` | yes |  | Missing | — |
| `poweroff` | yes | yes | Missing | — |
| `powertop` | yes |  | Missing | — |
| `printenv` | yes | yes | Registered | — |
| `printf` | yes | yes | Registered | — |
| `prlimit` |  | yes | Missing | — |
| `ps` | yes | yes | Missing | — |
| `pscan` | yes |  | Missing | — |
| `pstree` | yes |  | Missing | — |
| `pwd` | yes | yes | Registered | — |
| `pwdx` | yes | yes | Registered | — |
| `pwgen` |  | yes | Missing | — |
| `raidautorun` | yes |  | Missing | — |
| `rdate` | yes |  | Missing | — |
| `rdev` | yes |  | Missing | — |
| `readahead` | yes | yes | Missing | — |
| `readelf` |  | yes | Missing | — |
| `readlink` | yes | yes | Registered | — |
| `readprofile` | yes |  | Missing | — |
| `realpath` | yes | yes | Registered | — |
| `reboot` | yes | yes | Missing | — |
| `reformime` | yes |  | Missing | — |
| `remove-shell` | yes |  | Missing | — |
| `renice` | yes | yes | Missing | — |
| `reset` | yes | yes | Missing | — |
| `resize` | yes |  | Missing | — |
| `restorecon` | yes | yes | Missing | — |
| `resume` | yes |  | Missing | — |
| `return` |  | shell | — | Builtin |
| `rev` | yes | yes | Registered | — |
| `rfkill` | yes | yes | Missing | — |
| `rm` | yes | yes | Registered | — |
| `rmdir` | yes | yes | Registered | — |
| `rmmod` | yes | yes | Missing | — |
| `route` | yes | yes | Missing | — |
| `rpm` | yes |  | Missing | — |
| `rpm2cpio` | yes |  | Missing | — |
| `rtcwake` | yes | yes | Missing | — |
| `run-init` | yes |  | Missing | — |
| `run-parts` | yes |  | Missing | — |
| `runcon` | yes | yes | Missing | — |
| `runlevel` | yes |  | Missing | — |
| `runsv` | yes |  | Missing | — |
| `runsvdir` | yes |  | Missing | — |
| `rx` | yes |  | Missing | — |
| `script` | yes |  | Missing | — |
| `scriptreplay` | yes |  | Missing | — |
| `sed` | yes | yes | Registered | — |
| `seedrng` | yes |  | Missing | — |
| `selinuxenabled` | yes |  | Missing | — |
| `sendevent` |  | yes | Missing | — |
| `sendmail` | yes |  | Missing | — |
| `seq` | yes | yes | Registered | — |
| `sestatus` | yes |  | Missing | — |
| `set` |  | shell | — | Builtin |
| `setarch` | yes |  | Missing | — |
| `setconsole` | yes |  | Missing | — |
| `setenforce` | yes | yes | Missing | — |
| `setfattr` | yes | yes | Missing | — |
| `setfiles` | yes |  | Missing | — |
| `setfont` | yes |  | Missing | — |
| `setkeycodes` | yes |  | Missing | — |
| `setlogcons` | yes |  | Missing | — |
| `setpriv` | yes |  | Missing | — |
| `setsebool` | yes |  | Missing | — |
| `setserial` | yes |  | Missing | — |
| `setsid` | yes | yes | Registered | — |
| `setuidgid` | yes |  | Missing | — |
| `sh` | yes | yes | Registered | — |
| `sha1sum` | yes | yes | Registered | — |
| `sha224sum` |  | yes | Registered | — |
| `sha256sum` | yes | yes | Registered | — |
| `sha384sum` | yes | yes | Registered | — |
| `sha3sum` | yes | yes | Missing | — |
| `sha512sum` | yes | yes | Registered | — |
| `shift` |  | shell | — | Builtin |
| `showkey` | yes |  | Missing | — |
| `shred` | yes | yes | Missing | — |
| `shuf` | yes | yes | Registered | — |
| `skeleton` |  | yes | Missing | — |
| `skeleton_alias` |  | yes | Missing | — |
| `slattach` | yes |  | Missing | — |
| `sleep` | yes | yes | Registered | — |
| `smemcap` | yes |  | Missing | — |
| `sntp` |  | yes | Missing | — |
| `softlimit` | yes |  | Missing | — |
| `sort` | yes | yes | Registered | — |
| `source` |  | shell | — | Missing |
| `split` | yes | yes | Registered | — |
| `ssl_client` | yes |  | Missing | — |
| `ssl_server` | yes |  | Missing | — |
| `start-stop-daemon` | yes |  | Missing | — |
| `stat` | yes | yes | Registered | — |
| `strace` |  | yes | Missing | — |
| `strings` | yes | yes | Registered | — |
| `stty` | yes | yes | Missing | — |
| `su` | yes | yes | Missing | — |
| `sulogin` | yes | yes | Missing | — |
| `sum` | yes |  | Registered | — |
| `sv` | yes |  | Missing | — |
| `svc` | yes |  | Missing | — |
| `svlogd` | yes |  | Missing | — |
| `svok` | yes |  | Missing | — |
| `swapoff` | yes | yes | Missing | — |
| `swapon` | yes | yes | Missing | — |
| `switch_root` | yes | yes | Missing | — |
| `sync` | yes | yes | Registered | — |
| `sysctl` | yes | yes | Missing | — |
| `syslogd` | yes | yes | Missing | — |
| `tac` | yes | yes | Registered | — |
| `tail` | yes | yes | Registered | — |
| `tar` | yes | yes | Registered | — |
| `taskset` | yes | yes | Missing | — |
| `tc` | yes |  | Missing | — |
| `tcpsvd` | yes | yes | Missing | — |
| `tee` | yes | yes | Registered | — |
| `telnet` | yes | yes | Missing | — |
| `telnetd` | yes | yes | Missing | — |
| `test` | yes | yes | Registered | — |
| `tftp` | yes | yes | Missing | — |
| `tftpd` | yes | yes | Missing | — |
| `time` | yes | yes | Missing | — |
| `timeout` | yes | yes | Registered | — |
| `top` | yes | yes | Missing | — |
| `touch` | yes | yes | Registered | — |
| `toysh` |  | yes | Missing | — |
| `tr` | yes | yes | Registered | — |
| `traceroute` | yes | yes | Missing | — |
| `traceroute6` | yes | yes | Missing | — |
| `trap` |  | shell | — | Builtin |
| `tree` | yes |  | Missing | — |
| `true` | yes | yes | Registered | — |
| `truncate` | yes | yes | Registered | — |
| `ts` | yes | yes | Missing | — |
| `tsort` | yes | yes | Registered | — |
| `tty` | yes | yes | Registered | — |
| `ttysize` | yes |  | Registered | — |
| `tunctl` | yes | yes | Missing | — |
| `tune2fs` | yes |  | Missing | — |
| `type` |  | shell | — | Builtin |
| `ubiattach` | yes |  | Missing | — |
| `ubidetach` | yes |  | Missing | — |
| `ubimkvol` | yes |  | Missing | — |
| `ubirename` | yes |  | Missing | — |
| `ubirmvol` | yes |  | Missing | — |
| `ubirsvol` | yes |  | Missing | — |
| `ubiupdatevol` | yes |  | Missing | — |
| `uclampset` |  | yes | Missing | — |
| `ucsicontrol` |  | yes | Missing | — |
| `udhcpc` | yes |  | Missing | — |
| `udhcpc6` | yes |  | Missing | — |
| `udhcpd` | yes |  | Missing | — |
| `udpsvd` | yes | yes | Missing | — |
| `uevent` | yes |  | Missing | — |
| `ulimit` |  | yes | Missing | — |
| `umask` |  | shell | — | Builtin |
| `umount` | yes | yes | Registered | — |
| `unalias` |  | shell | — | Builtin |
| `uname` | yes | yes | Registered | — |
| `uncompress` | yes |  | Missing | — |
| `unexpand` | yes |  | Registered | — |
| `unicode` |  | yes | Missing | — |
| `uniq` | yes | yes | Registered | — |
| `unit` | yes |  | Missing | — |
| `unix2dos` | yes | yes | Missing | — |
| `unlink` | yes | yes | Registered | — |
| `unlzma` | yes |  | Missing | — |
| `unlzop` | yes |  | Missing | — |
| `unset` |  | shell | — | Builtin |
| `unshare` | yes | yes | Missing | — |
| `unxz` | yes |  | Missing | — |
| `unzip` | yes |  | Missing | — |
| `uptime` | yes | yes | Registered | — |
| `useradd` |  | yes | Missing | — |
| `userdel` |  | yes | Missing | — |
| `users` | yes |  | Registered | — |
| `usleep` | yes | yes | Registered | — |
| `uudecode` | yes | yes | Missing | — |
| `uuencode` | yes | yes | Missing | — |
| `uuidgen` | yes | yes | Registered | — |
| `vconfig` | yes | yes | Missing | — |
| `vi` | yes | yes | Missing | — |
| `vlock` | yes |  | Missing | — |
| `vmstat` | yes | yes | Missing | — |
| `volname` | yes |  | Missing | — |
| `w` | yes | yes | Missing | — |
| `wait` |  | shell | — | Builtin |
| `wall` | yes |  | Missing | — |
| `watch` | yes | yes | Missing | — |
| `watchdog` | yes | yes | Missing | — |
| `wc` | yes | yes | Registered | — |
| `wget` | yes | yes | Missing | — |
| `which` | yes | yes | Registered | — |
| `who` | yes | yes | Registered | — |
| `whoami` | yes | yes | Registered | — |
| `whois` | yes |  | Missing | — |
| `xargs` | yes | yes | Registered | — |
| `xxd` | yes | yes | Missing | — |
| `xz` | yes |  | Missing | — |
| `xzcat` | yes | yes | Missing | — |
| `yes` | yes | yes | Registered | — |
| `zcat` | yes | yes | Registered | — |
| `zcip` | yes |  | Missing | — |

## Additional Nebox names

`b2sum`, `basenc`, `dir`, `dircolors`, `domainname`, `join`, `nisdomainname`, `nsh`, `pathchk`, `pinky`, `vdir`, `ypdomainname`
