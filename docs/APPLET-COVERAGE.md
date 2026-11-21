# Applet coverage

The target includes every applet declared by BusyBox 1.38.0 or Toybox 0.8.15, including aliases and optional commands. The two multiplexer names are excluded.

Registered names come from the selected Nebox binary’s `--list` output. The checked-in report uses the standalone build. Individual applet tests cover flags, output and exit status.

| Upstream catalog | Registered | Missing | Total |
|---|---:|---:|---:|
| Both projects | 114 | 158 | 272 |
| BusyBox only | 3 | 164 | 167 |
| Toybox only | 3 | 82 | 85 |
| Union | 120 | 404 | 524 |

## Missing applets

### Both projects

`[[`, `addgroup`, `adduser`, `arp`, `arping`, `ascii`, `bash`, `bc`, `blkdiscard`, `blkid`, `blockdev`, `bootchartd`, `brctl`, `bunzip2`, `bzcat`, `cal`, `chattr`, `chcon`, `chrt`, `chvt`, `cpio`, `crc32`, `crond`, `crontab`, `deallocvt`, `delgroup`, `deluser`, `devmem`, `dmesg`, `dos2unix`, `dumpleases`, `eject`, `fallocate`, `fdisk`, `flock`, `freeramdisk`, `fsck`, `fsfreeze`, `fsync`, `ftpget`, `ftpput`, `getenforce`, `getfattr`, `getopt`, `getty`, `halt`, `hexedit`, `httpd`, `hwclock`, `i2cdetect`, `i2cdump`, `i2cget`, `i2cset`, `i2ctransfer`, `ifconfig`, `init`, `inotifyd`, `insmod`, `ionice`, `ip`, `ipaddr`, `ipcrm`, `ipcs`, `iplink`, `iproute`, `iprule`, `iptunnel`, `killall`, `killall5`, `klogd`, `last`, `linux32`, `load_policy`, `logger`, `login`, `losetup`, `lsattr`, `lsof`, `lspci`, `lsusb`, `makedevs`, `man`, `mdev`, `microcom`, `mkpasswd`, `mkswap`, `modinfo`, `modprobe`, `more`, `mountpoint`, `nbd-client`, `nc`, `netcat`, `netstat`, `nologin`, `nsenter`, `openvt`, `partprobe`, `passwd`, `pgrep`, `pidof`, `ping`, `ping6`, `pivot_root`, `pkill`, `pmap`, `poweroff`, `ps`, `readahead`, `reboot`, `renice`, `reset`, `restorecon`, `rfkill`, `rmmod`, `route`, `rtcwake`, `runcon`, `setenforce`, `setfattr`, `sha3sum`, `shred`, `stty`, `su`, `sulogin`, `swapoff`, `swapon`, `switch_root`, `sysctl`, `syslogd`, `taskset`, `tcpsvd`, `telnet`, `telnetd`, `tftp`, `tftpd`, `time`, `top`, `traceroute`, `traceroute6`, `ts`, `tunctl`, `udpsvd`, `unix2dos`, `unshare`, `usleep`, `uudecode`, `uuencode`, `uuidgen`, `vconfig`, `vi`, `vmstat`, `w`, `watch`, `watchdog`, `wget`, `xxd`, `xzcat`

### BusyBox only

`acpid`, `add-shell`, `adjtimex`, `ar`, `ash`, `bbconfig`, `beep`, `bzip2`, `chat`, `chpasswd`, `chpst`, `conspy`, `cryptpw`, `cttyhack`, `dc`, `depmod`, `devfsd`, `dhcprelay`, `dnsd`, `dpkg`, `dpkg-deb`, `dumpkmap`, `ed`, `envdir`, `envuidgid`, `ether-wake`, `fakeidentd`, `fatattr`, `fbset`, `fbsplash`, `fdflush`, `fdformat`, `fgconsole`, `findfs`, `flash_eraseall`, `flash_lock`, `flash_unlock`, `flashcp`, `fsck.minix`, `fstrim`, `ftpd`, `fuser`, `getsebool`, `hdparm`, `hush`, `ifdown`, `ifenslave`, `ifplugd`, `ifup`, `inetd`, `iostat`, `ipcalc`, `ipneigh`, `kbd_mode`, `less`, `linux64`, `linuxrc`, `loadfont`, `loadkmap`, `logread`, `lpd`, `lpq`, `lpr`, `lsblk`, `lsscsi`, `lzcat`, `lzma`, `lzop`, `lzopcat`, `makemime`, `matchpathcon`, `mesg`, `mim`, `minips`, `mkdosfs`, `mke2fs`, `mkfs.ext2`, `mkfs.minix`, `mkfs.reiser`, `mkfs.vfat`, `mpstat`, `mt`, `nameif`, `nanddump`, `nandwrite`, `nmeter`, `nslookup`, `ntpd`, `nuke`, `pipe_progress`, `popmaildir`, `powertop`, `pscan`, `pstree`, `raidautorun`, `rdate`, `rdev`, `readprofile`, `reformime`, `remove-shell`, `resize`, `resume`, `rpm`, `rpm2cpio`, `run-init`, `run-parts`, `runlevel`, `runsv`, `runsvdir`, `rx`, `script`, `scriptreplay`, `seedrng`, `selinuxenabled`, `sendmail`, `sestatus`, `setarch`, `setconsole`, `setfiles`, `setfont`, `setkeycodes`, `setlogcons`, `setpriv`, `setsebool`, `setserial`, `setuidgid`, `showkey`, `slattach`, `smemcap`, `softlimit`, `ssl_client`, `ssl_server`, `start-stop-daemon`, `sv`, `svc`, `svlogd`, `svok`, `tc`, `tree`, `ttysize`, `tune2fs`, `ubiattach`, `ubidetach`, `ubimkvol`, `ubirename`, `ubirmvol`, `ubirsvol`, `ubiupdatevol`, `udhcpc`, `udhcpc6`, `udhcpd`, `uevent`, `uncompress`, `unit`, `unlzma`, `unlzop`, `unxz`, `unzip`, `vlock`, `volname`, `wall`, `whois`, `xz`, `zcip`

### Toybox only

`-bash`, `-sh`, `-toysh`, `.`, `:`, `acpi`, `alias`, `break`, `cd`, `chsh`, `command`, `continue`, `count`, `declare`, `demo_many_options`, `demo_number`, `demo_scankey`, `demo_utf8towc`, `dhcp`, `dhcp6`, `dhcpd`, `eval`, `exec`, `exit`, `export`, `file`, `fstype`, `getconf`, `gitcheckout`, `gitclone`, `gitfetch`, `gitinit`, `gitremote`, `gpiodetect`, `gpiofind`, `gpioget`, `gpioinfo`, `gpioset`, `groupadd`, `groupdel`, `hello`, `help`, `host`, `iconv`, `iorenice`, `iotop`, `jobs`, `local`, `log`, `logpath`, `mcookie`, `memeater`, `mix`, `nbd-server`, `nbd_client`, `nbd_server`, `oneit`, `prlimit`, `pwgen`, `readelf`, `return`, `sendevent`, `set`, `shift`, `skeleton`, `skeleton_alias`, `sntp`, `source`, `strace`, `toysh`, `trap`, `type`, `uclampset`, `ucsicontrol`, `ulimit`, `umask`, `unalias`, `unicode`, `unset`, `useradd`, `userdel`, `wait`

## Registered applets

### Both projects

`[`, `arch`, `awk`, `base32`, `base64`, `basename`, `cat`, `chgrp`, `chmod`, `chown`, `chroot`, `cksum`, `clear`, `cmp`, `comm`, `cp`, `cut`, `date`, `dd`, `df`, `diff`, `dirname`, `dnsdomainname`, `du`, `echo`, `egrep`, `env`, `expand`, `expr`, `factor`, `false`, `fgrep`, `find`, `fold`, `free`, `grep`, `groups`, `gunzip`, `gzip`, `hd`, `head`, `hexdump`, `hostid`, `hostname`, `id`, `install`, `kill`, `link`, `ln`, `logname`, `ls`, `lsmod`, `md5sum`, `mkdir`, `mkfifo`, `mknod`, `mktemp`, `mount`, `mv`, `nice`, `nl`, `nohup`, `nproc`, `od`, `paste`, `patch`, `printenv`, `printf`, `pwd`, `pwdx`, `readlink`, `realpath`, `rev`, `rm`, `rmdir`, `sed`, `seq`, `setsid`, `sh`, `sha1sum`, `sha256sum`, `sha384sum`, `sha512sum`, `shuf`, `sleep`, `sort`, `split`, `stat`, `strings`, `sync`, `tac`, `tail`, `tar`, `tee`, `test`, `timeout`, `touch`, `tr`, `true`, `truncate`, `tsort`, `tty`, `umount`, `uname`, `uniq`, `unlink`, `uptime`, `wc`, `which`, `who`, `whoami`, `xargs`, `yes`, `zcat`

### BusyBox only

`sum`, `unexpand`, `users`

### Toybox only

`csplit`, `fmt`, `sha224sum`

## Additional Nebox names

`b2sum`, `basenc`, `dir`, `dircolors`, `domainname`, `join`, `nisdomainname`, `nsh`, `pathchk`, `pinky`, `vdir`, `ypdomainname`
