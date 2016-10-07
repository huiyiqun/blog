---
layout: post
title:  "使用Ansible自动部署运行于KVM虚拟机上的Debian"
date:   2016-10-07 15:40:30
categories: ansible kvm libvirt preseed
---
# 前言

有一年多没有写东西了，期间还是做了不少事情，但是因为博(zi)客(ji)有(que)点(shi)丑(lan)。
什么都没有写，然而很多东西因为没有记下来，所以渐渐地都忘了，回头要用到的时候又需要重新去
翻文档，实在是有点费事。于是决定把博客续上。

之所以会需要装虚拟机，是因为TUNA最近又招了不少萌新，萌新们可能需要一台UNIX的设备来瞎折腾，
另外协会内部偶尔需要交换slide或者活动视频，大鹰主席又觉得通过“网盘”交换文件实在太羞耻，
因为我之前折腾过一下KVM，因而让我部署一台Debian的虚拟机。

本来是一件挺简单但是比较麻烦的事情，但是基于以下理由：

1. 萌新可能把机器弄坏或者机器需要搬家
2. 以后会长可能会让我装第二个机器
3. ~~好久没折腾了感觉皮子有点紧~~

决定用ansible自动安装。（花了大概两天左右才让整个系统比较顺畅地跑起来）

（在此安利一下ansible，可读性比较高，又相对其他自动化工具又更简单一些）

以下是一些流水账，避免以后忘了。如果能帮到别人那真是太巧了。

# 宿主机

首先需要装一些必要的包：`qemu-kvm`和`libvirt-bin`。
为了用ansible的`virt`模块，把`python-libvirt`和`python-lxml`也装上。

```yaml
- name: install required packages
  apt: name={{item}}
  with_items:
    - qemu-kvm
    - libvirt-bin
    - python-libvirt
    - python-lxml
```

Debian里装完软件默认是启动的，所以可以不用`service`模块来启动`libvirtd`，习惯性地
写了一下，也更保险一些（比如有人上去关了？）

接着建用来存ISO和虚拟机硬盘的目录，接着下载安装光盘，创建qcow2。

创建qcow2这里说一下，ansible官方的模块里并没有qemu-img的，所以需要直接用`command`模块，
不过幸运的是，[这里](https://github.com/ansible-provisioning/ansible-provisioning/blob/master/library/qemu_img)
有一个现成的模块，这个项目本身已经不太活跃了，不过这个模块还能用。直接放到role的library
目录下就能用了。

之前用ansible安装CentOS的时候用的是`virt-install`，这个有几个问题：

1. `virt-install` 并没有对应的ansible模块，只能直接用`command`。
2. `virt-install` 可控性相对差一些，需要不少hack。

之前看github里很多人也是用`virt-install`装的，这里算一个尝试吧。

CentOS里的自动部署系统叫kickstart，对应的Debian里的叫preseed。preseed的文档相对
挺少的，而且Debian的各个版本之间也有一些细微的差别，更别说Ubuntu了，我装的Debian
版本是jessie，查找的资料里面最具有参考价值的是：

1. https://www.debian.org/releases/jessie/amd64/apbs02.html.en
2. https://www.debian.org/releases/jessie/example-preseed.txt

其中jessie的appendix里信息量其实挺大的，但是感觉写得比较混乱，得静下心来读才能
看明白。

总的来说，在安装的过程中指定preseed文件实现自动安装的方式有两种：

1. iso启动之后按Tab，然后输入auto <各种参数> ，或者在iso启动后选Automated install。
这两者实际是等价的
2. 通过启动参数(boot parameters)将preseed的uri传给installer。

显然，前一种方式依然需要人工干预，因此我选择了第二种方式。

那么现在的问题是，我怎么才能把启动参数传给installer呢？显然应该是通过domain的定义。
翻了一下[libvirt的文档](https://libvirt.org/formatdomain.html#elementsOS)，为了能够
在启动的过程中给出启动参数，我选择了`Direct Kernel boot`(这里可能并不是最好的方式，
不过最终work)。因此需要直接拿到kernel和initrd，这里为了方便，我就没有从iso里面取，
而是直接从[这里](https://mirrors.tuna.tsinghua.edu.cn/debian/dists/jessie/main/installer-amd64/current/images/cdrom/)
下载了。

最终的启动参数如下：
```
console=ttyS0 auto=true priority=critical url="http://192.168.101.1:2015/preseed-shared-guest.txt" interface=auto netcfg/dhcp_timeout=60
```

* `console` 是为了installer能把安装过程发送到ttyS0，然后通过libvirt映射到物理机
* `auto=true priority=critical` 能保证installer开始自动安装而不是等待用户操作，priority这里坑了我很久，如果只有auto安装能自动开始，但是一旦有需要用户输入的地方就会停下来。
* `url`指定preseed的url，如果preseed在initrd里应该用`file=`，也有比较老的文档说应该是`url=file:///`，都没有试过，因为重新打包initrd太麻烦了。
* 最后两个参数其实没什么用，不加也行。

接着把iso和硬盘都挂上，把网卡配好，吧serial和console配好，就能够开始自动安装了。

关于preseed如何serve的问题，考虑到host上可能有正在跑的nginx，决定用小巧玲珑的
[caddy](https://caddyserver.com/)，下载解压都不用说，我这里想用ansible自动化，怎么
并行化和关闭服务成了问题，一番搜索在[这里](http://stackoverflow.com/a/29822700)找到
了解决方案。

`daemon`这个工具还是挺好用的，可以给命名，也支持stop。

如下两个命令可以实现运行和结束`caddy`

```
$ daemon -n caddy -- /opt/caddy/caddy -conf=/tmp/Caddyfile
$ daemon -n caddy --stop
```

有意思的是，如果你要执行的命令及其父目录有一些不合适的权限的话，`daemon`会拒绝启动。
这种情况确实有一些安全问题，之前在git的邮件列表里讨论过，这里就不展开了。

未完待续。。。
