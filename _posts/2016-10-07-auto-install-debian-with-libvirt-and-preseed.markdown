---
layout: post
title:  "使用libvirt和preseed自动部署运行于KVM上的Debian虚拟机"
date:   2016-10-07 15:40:30
comments: true
categories: ansible kvm libvirt preseed
---
# 前言

有一年多没有写东西了，期间还是做了不少事情，但是因为博(zi)客(ji)有(te)点(bie)丑(lan)，
什么都没有写。很多东西花了很多时间去学和折腾，回头要用到的时候又需要重新去
翻文档，实在是浪费时间，于是决定把博客续上。

之所以会需要装虚拟机，是因为TUNA最近又招了不少萌新，萌新们可能需要一台UNIX的设备来瞎折腾，
另外协会内部偶尔需要交换slide或者活动视频，大鹰主席又觉得通过“网盘”交换文件实在太羞耻，
因为我之前折腾过一下KVM，因而让我部署一台Debian的虚拟机。

本来是一件简单的重复劳动，但是基于以下理由：

1. 萌新可能把机器弄坏或者机器需要搬家
2. 以后会长可能会让我装第二个机器
3. ~~好久没折腾了感觉皮子有点紧~~

决定用ansible自动安装。整个过程花了大概两天左右，其实ansible和libvirt都还算好，文档挺齐全
的，而且实现上bug不多，但是preseed的文档少而且比较乱，经常遇到文档和实际情况不符合的情况。

# 环境

宿主机是一个Debian jessie，上面跑了各种各样的其他服务，包括且不限于docker、nginx、
私有的ldap服务等。

虚拟机依然是一个Debian jessie，上面需要部署一些基本的服务，比如基于ldap的pam模块等，方便
用户的登录。

# 宿主机

qemu本身的接口本身比较简陋，我一般是用libvirt来管理。

因此通过apt安装上`qemu-kvm`和`libvirt-bin`。
Debian上安装好包之后默认服务就启动了，因此不需要主动启动`libvirtd`，宿主机基本就配置好了。

# 虚拟机

此前安装系统都是通过`virt-install`或者封装得更严实的`virt-manager`。
`virt-manager`的安装过程基于GUI，重复安装很不方便；
`virt-install`相对要方便很多，不过感觉比较玄学，完全不知道它背后做了什么。

github上能找到的自动安装项目基本都是基于`virt-install`的，这次我想尝试直接基于`libvirt`的
xml文件配置来实现更灵活的安装过程控制。

## Network

因为使用了ansible，网络的配置是给定了一个xml文件，然后用`virt-net`模块把这个xml传进去，
网络就定义好了。

因为会长想要一个nat网络，对外只暴露一个ssh的端口，因此网络配置上选择了nat网络+DNAT的方式。

以下是我使用的xml。

```xml
<network>
  <name>nat</name>
  <forward mode="nat"/>
  <ip address="192.168.101.1" netmask="255.255.255.0">
    <dhcp>
      <range start="192.168.101.2" end="192.168.101.254" />
      <host mac="02:33:33:33:33:33" name="everest" ip="192.168.101.100" />
    </dhcp>
  </ip>
</network>
```

需要说的是dhcp这个tag里的内容，为了将虚拟机的22端口暴露到外网，最简单地做法是固定虚拟机
的ip地址。

本来我计划在这个网段中不起dhcp服务，直接通过preseed（也就是Debian的自动部署工具）来自动
配置一个静态地址，这样看上去是比较合理的。但是preseed和anaconda（CentOS的自动部署工具）
在工作流程上有一些本质的区别：

* anaconda如果配置了用kickstart（anaconda的配置）安装，那么anaconda在运行之前会先尝试
去下载指定的kickstart文件，如果下载失败会出错退出。所以如果要通过网络指定kickstart需要用
启动参数（boot parameters）`ip`来配置虚拟机的网络，然后内核把控制权交给 anaconda之后，
anaconda才能获取kickstart文件进行安装，接着根据kickstart的内容来进行安装。

* preseed则完全不同，如果配置了用preseed配置安装，preseed会把下载preseed配置作为
其工作流程的一步插到网络配置的后面，也就是说当preseed拿到配置文件的时候，它已经用默认值
（DHCP）运行完了其所有网络配置，preseed中的网络、域名等配置完全不会生效。

虽然文档中也提到了可以用启动参数的方式指定其网络配置，但是我试了一下，没有生效。并且
这个时候我对于preseed已经基本失望了。所以我决定把复杂的配置放到libvirt里，让preseed
里面的配置尽可能少。

所以这里我配了一个给guest分配“静态地址”的dhcp服务器。

## Storage

虚拟机的硬盘相对比较简单，直接用qemu-img就好了。因为了用了ansible，用了
[这里](https://github.com/ansible-provisioning/ansible-provisioning/blob/master/library/qemu_img)
一个现成的模块，放到role的library目录下就能正常工作了。

（我一般不喜欢造轮子，算优点也算缺点吧。）

接下来把目录建成`virt-pool`方便使用。

## Installing Domain

如果在物理机上安装一个新的操作系统，你需要下载一个ISO，烧到dvd或者U盘里，再调整bios里的
启动顺序。

如果需要自动化安装，在进入安装界面之后，可以找到一些快捷键，可以进入一个prompt模式，在
里面输入一些参数（一般来说等于修改启动参数），接着就能一路安装下去。

在虚拟机里其实也很类似，对于一个虚拟机，虽然安装时和安装后共享一个硬盘，但是启动顺序、
是否有ISO、有什么启动参数都完全不一样。也就是说安装中和安装后需要定义两个不完全相同的
domain。

以下是我在安装时用的xml文件：

```xml
<domain type='kvm'>
  <name>shared-guest</name>
  <memory unit='MB'>4096</memory>
  <vcpu>2</vcpu>
  <os>
    <type>hvm</type>
    <boot dev='cdrom'/>
    <kernel>/data/iso/vmlinuz</kernel>
    <initrd>/data/iso/initrd.gz</initrd>
    <cmdline>console=ttyS0 auto=true priority=critical url="http://192.168.101.1:2015/preseed-shared-guest.txt" interface=auto netcfg/dhcp_timeout=60</cmdline>
  </os>
  <devices>
    <disk type='volume' device='disk'>
      <source pool='vms' volume='shared-guest.qcow2'/>
      <target dev='hda'/>
    </disk>
    <disk type='volume' device='cdrom'>
      <driver name='qemu' type='raw'/>
      <source pool='iso' volume='debian-8.6.0-amd64-netinst.iso'/>
      <target dev='hdc' bus='ide'/>
      <readonly/>
    </disk>
    <interface type='network'>
      <source network='nat'/>
      <mac address='02:33:33:33:33:33'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
  </devices>
</domain>
```

os这个tag里的内容定义了domain的启动选项。这里boot这个tag应该没有生效，是遗留代码，主要是通过
kernel、initrd、cmdline三个参数实现了[Direct kernel boot](https://libvirt.org/formatdomain.html#elementsOSKernel)。
以此达到指定启动参数的目的。

kernel和initrd里的文件理论上应该从iso里面解出来，在这里，我偷了个懒，直接从
[这里](https://mirrors.tuna.tsinghua.edu.cn/debian/dists/jessie/main/installer-amd64/current/images/cdrom/)
下载的。

`device`这个tag里前两个`disk`分别是之前建的虚拟硬盘和下载的安装iso。

`interface`则挂载到了之前建的nat网络上，注意到mac地址需要与之前的mac地址对应。

最后的`serial`与`console`和`cmdline`里的console=ttyS0配合，这样可以通过`virsh console`
命令将标准IO和安装过程接起来，可以交互式的安装，也可以看安装进度。

关于cmdline里的其他参数，`auto=true priority=critical`保证了preseed自动安装并且不会被一
些低优先级的问题打断，比如询问hostname之类的，但是并不能跳过所有问题，比如如果preseed
里面没有设置root密码也没有选择跳过建root用户，安装过程就会停下来等用户输入root密码。

`url`指定了配置文件的url，preseed配置完网络之后会从这个地方下载配置文件。貌似也支持其他
协议，不过没有试过。

剩下两个参数应该是没什么用处的，算是遗留代码。

更多的详细信息可以看[这里](https://www.debian.org/releases/jessie/amd64/apbs02.html.en)。

当你确定安装不需要任何人工干预之后，可以把serial这个tag改成如下内容：

```xml
<serial type='file'>
  <source path="/tmp/shared-guest-serial0.log"/>
  <target port='0'/>
</serial>
```

这样libvirt会把虚拟机的ttyS0的输出接到物理机的`/tmp/shared-guest-serial0.log`这个文件。
然后通过

```
$ sudo tail -f /tmp/shared-guest-serial0.log
```

这个命令就可以查看安装进度了，但是不能进行交互了。

这样有如下两个好处：

1. console是独占的，而文件本身是共享的，多个人可以同时浏览安装进度。
2. 方便使用ansible的`wait_for`这个模块来监视安装的进度。

## Preseed

上面的启动参数里写到了，需要从物理机的http服务器上获取preseed。我用`daemon`和`caddy`配合在
宿主机上起了一个简单的http服务器，主要是考虑如何在ansible里起简单的daemon。
灵感来源于[stackoverflow](http://stackoverflow.com/a/29822700)，具体的细节就不赘述了，
感兴趣可以直接去看github看这个repo的内容。

关于Preseed，我使用了[这里](https://www.debian.org/releases/jessie/example-preseed.txt)
的模板。

有几个地方需要注意：

1. 网络配置是不会起作用的，不要白费力气了。
2. ~~不要设置`apt-setup/security_host`！如果你设置`apt-setup/security_host`为`mirror.example.com`，那么apt会尝试访问`http://mirror.example.com/`而不是`http://mirror.example.com/debian-security`，google了一下发现有一个`apt-setup/security_path`这个参数解决这个问题，但是首先example里没有，其次我加上也没有效果，应该是这个版本的bug。~~根据@zhsj提供的信息，可以把`security_path`放到`security_host`后面workaround这个问题，也就是`apt-setup/security_host=https://mirrors.tuna.tsinghua.edu.cn/debian-security`。
3. 同理也不要设置`apt-setup/non-free`和`apt-setup/contrib`，类似的问题。不过mirror settings没问题。
4. `tasksel/first`这里一定要配置，并且只留下standard，否则会给你把gnome一起装上。
5. `debian-installer/exit/poweroff`是没什么用的，最后系统还是会halt住，`virsh status`里显示的依然是running。

preseed太长，也不放在这里了，感兴趣可以去repo看。

关于不能关机的问题，我用ansible的`wait_for`监视了serial输出的日志文件，如果看到了最后几个字符就destroy。

## Installed Domain

接着整个虚拟机就安装好了，直接undefine原来的domain，然后重新定义一个domain就好，因为disk
不变，所以安装好的系统依然还在。

就像我们安装物理机时重启时会调整启动顺序，启动参数等等，这里我们需要重新定义domain。

新定义的xml如下：

```xml
<domain type='kvm'>
  <name>shared-guest</name>
  <memory unit='MB'>4096</memory>
  <vcpu>2</vcpu>
  <os>
    <type>hvm</type>
    <boot dev='hd'/>
  </os>
  <devices>
    <disk type='volume' device='disk'>
      <source pool='vms' volume='shared-guest.qcow2'/>
      <target dev='hda'/>
    </disk>
    <interface type='network'>
      <source network='nat'/>
      <mac address='02:33:33:33:33:33'/>
    </interface>
    <serial type='pty'>
      <target port='0'/>
    </serial>
    <console type='pty'>
      <target type='serial' port='0'/>
    </console>
  </devices>
</domain>
```

可以看到非常简单，启动列表里面只剩了hd，iso也被去掉了，serial的配置还原回了交互式的，
这样未来网络出问题不能ssh登录时可以通过virsh的console登录去调试。

## DNAT

为了从互联网可以直接ssh访问虚拟机，需要配一下iptables，直接看ansible脚本吧：

```yaml
- name: set up DNAT for ssh
  iptables:
    table: nat
    chain: PREROUTING
    in_interface: eth0
    protocol: tcp
    match: tcp
    destination_port: "{{ hostvars['kvm-guest']['ansible_port'] }}"
    jump: DNAT
    to_destination: 192.168.101.100:22
    comment: DNAT rule for ssh service of everest

- name: enable forwarding for ssh
  iptables:
    action: insert
    chain: FORWARD
    in_interface: eth0
    destination: 192.168.101.100
    destination_port: 22
    protocol: tcp
    jump: ACCEPT
    comment: allow ssh connection for everest to be forwarded
```

Debian是默认不会drop forward的包的，但是libvirt为NAT网络在iptables里配了两条drop规则，
所以需要在这两条规则之前加一个accept规则，这也是必须要`action: insert`的原因，不幸的是
这是ansible 2.2新加的特性，写文的时候还没有正式发布，所以安装比较麻烦。
repo的README里有一个临时的workaround。

## Post installation

写ansible的时候用了一点小技巧，安装好的虚拟机的username和password就是inventory里
的`ansible_user`和`ansible_ssh_pass`，这样在虚拟机安装完之后通过ansible可以直接
地访问虚拟机，因此简单地写一些ansible脚本，可以完成一些配置。

关于非网络的配置，在这里做比在preseed里做会更加可靠。

# NOTE

1. 上面提到的preseed的坑只适用于Debian jessie，可能不适用于其他版本，更不适用于Ubuntu。
2. 完整项目的[链接](https://github.com/tuna/playbooks/tree/master/shared-guest)。
