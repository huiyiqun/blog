Title:    在三星Galaxy S4上chroot方式安装Archlinux Arm
Date:     2015-04-05 12:20:00
Category: android

# 前言
入手 Galaxy S4 已经几个月了，我手里这款是 I9508，也就是移动3G定制版，除了制式以外其他
硬件和 I9505（也就是 Galaxy S4 国际版）是一样的。因此搭了 I9505 的东风，装上了
[cm12](http://forum.xda-developers.com/galaxy-s4/i9505-orig-develop/rom-cyanogenmod-12-t2943934)，
作者最近还编译了
[cm12.1](http://forum.xda-developers.com/galaxy-s4/i9505-orig-develop/exclusive-antaresone-alucard24-s-t3066696)，
等 Xposed 可以用到 Android 5.1 之后就可以装上了。

# 硬件
进入正题，首先看一下硬件的情况：

```
(notebook)$ adb shell df
Filesystem               Size     Used     Free   Blksize
/dev                   905.5M    48.0K   905.5M   4096
/sys/fs/cgroup         905.5M    12.0K   905.5M   4096
/mnt/asec              905.5M     0.0K   905.5M   4096
/mnt/obb               905.5M     0.0K   905.5M   4096
/system                  2.7G   970.1M     1.7G   4096
/firmware               86.0M    11.5M    74.4M   16384
/firmware-mdm           86.0M    49.8M    36.2M   16384
/efs                    13.4M     4.2M     9.2M   4096
/cache                   2.0G   448.4M     1.6G   4096
/data                    9.1G     6.0G     3.1G   4096
/mnt/shell/emulated      9.1G     6.0G     3.1G   4096
/mnt/ntfs              905.5M     0.0K   905.5M   4096
```

```
(notebook)$ adb shell cat /proc/cpuinfo
Processor	: ARMv7 Processor rev 0 (v7l)
processor	: 0
BogoMIPS	: 13.53

processor	: 1
BogoMIPS	: 13.53

processor	: 2
BogoMIPS	: 13.53

processor	: 3
BogoMIPS	: 13.53

Features	: swp half thumb fastmult vfp edsp neon vfpv3 tls vfpv4 idiva idivt vfpd32 
CPU implementer	: 0x51
CPU architecture: 7
CPU variant	: 0x1
CPU part	: 0x06f
CPU revision	: 0

Hardware	: SAMSUNG JF
Revision	: 000b
Serial		: 0000b74100006515
```

```
(notebook)$ adb shell uname -m
armv7l
```

# 准备分区

`/data/` 容量实在是大得不行，我就决定直接把系统装到 `/data/` 里了。

手机当然要 root，否则`/data/`目录不可读。

```
(notebook)$ adb shell
$ su
#
```

我给`archlinux`开了1G的空间，可能有点不太够。

```
# mkdir -p /data/linux
# busybox dd if=/dev/zero of=/data/linux/archlinux.img bs=1M count=0 seek=1024
# mkfs.ext2 -F /data/linux/archlinux.img
# mkdir -p /data/mnt/archlinux
# mount /data/linux/archlinux.img /data/mnt/archlinux
```

# 系统文件

这样空间都准备好了，接下来把`Archlinux Arm`的文件系统下载下来，本来是想直接在
`Android`里面用`wget`下，不过报下面的错：

```
error: only position independent executables (PIE) are supported.
```

Google 了一下，好像是ndk的原因，`busybox`里的`wget`也有另外一个问题，貌似不能正确地
把域名解析为IP地址。

因此在我的笔记本里下载文件，再用adb传到手机里。

用的是`Tsinghua TUNA`的镜像，有`IPv4`和`IPv6`的接入。

```
(notebook)$ wget http://mirrors.tuna.tsinghua.edu.cn/archlinuxarm/os/ArchLinuxARM-armv7-latest.tar.gz
(notebook)$ adb push ArchLinux-armv7-latest.tar.gz /sdcard/
```

这里下的是`armv7`的版本，[镜像站](http://mirrors.tuna.tsinghua.edu.cn/archlinuxarm/os/)里也有别的版本，
不过别的我也不认识，不知道有什么区别，总之`armv7`这个版本是可以用。

```
# cd /data/mnt/archlinux
# tar xfz /sdcard/ArchLinuxARM-armv7-latest.tar.gz
```

大概是因为CPU的原因，速度非常慢。在我电脑上解压这个文件大概几十秒，在我手机上用了有快两小时吧。23333

# chroot

解压好之后就可以开始正式`chroot`了。

```
# mount -o bind /sys /data/mnt/archlinux/sys
# mount -o bind /proc /data/mnt/archlinux/proc
# mount -o bind /dev /data/mnt/archlinux/dev
# mount -t devpts devpts /data/mnt/archlinux/dev/pts
# chroot /data/mnt/archlinux su -
```

# fix

此后就已经在`Archlinux`里了，不过还要处理几个问题：

* 环境变量

此时的`$PATH`等环境变量还是 Android 里的，导入 Archlinux 的环境变量
```
. /etc/profile
```

* `ld`报错

```
ERROR: ld.so: object 'libsigchain.so' from LD_PRELOAD cannot be preloaded: ignored.
```

好像没什么影响，就是看着很烦。

```
unset LD_PRELOAD
```

* 不能访问网络

参照[这个页面](http://archlinuxarm.org/forum/viewtopic.php?f=9&t=4611)，在`/etc/group`
中加入如下内容：

```
inet:x:3003:root
net_raw:x:3004:root
```
