Title:      archlinux上用systemd-networkd与hostapd配置无线ap
Date:       2016-10-08 17:21:11
slug:       syst-networkd-and-hostapd.md
Category:   Ops

# 环境

这套配置我现在运行在了两个地方，一个是我家里的minipc上，当软路由用，另一个则是我实验室的
PC，因为实验室的公共Wifi效果实在不能让人满意，决定自己在PC上插两个USB无线网卡当无线路由器用。

环境上用的都是Archlinux。

这是minipc上的无线网卡：

```
$ lsusb
Bus 002 Device 002: ID 148f:5572 Ralink Technology, Corp. RT5572 Wireless Adapter

$ lspci
01:00.0 Ethernet controller: Realtek Semiconductor Co., Ltd. RTL8111/8168/8411 PCI Express Gigabit Ethernet Controller(rev 06)
```

这是实验室PC上的无线网卡：

```
~> lsusb
Bus 003 Device 002: ID 0bda:8178 Realtek Semiconductor Corp. RTL8192CU 802.11n WLAN Adapter
Bus 003 Device 003: ID 148f:5572 Ralink Technology, Corp. RT5572 Wireless Adapter
```

比较推荐Ralink的这个[网卡](https://gist.github.com/huiyiqun/9c9b00631768bc5b31971235462eba62)，京东上49块，
驱动在主线内核里，支持2.4Ghz/5Ghz，稳定性也不错。

软件版本上：

```
~> systemctl --version
systemd 231
+PAM -AUDIT -SELINUX -IMA -APPARMOR +SMACK -SYSVINIT +UTMP +LIBCRYPTSETUP +GCRYPT +GNUTLS +ACL +XZ +LZ4 +SECCOMP +BLKID +ELFUTILS +KMOD +IDN

~> hostapd -v
hostapd v2.6
User space daemon for IEEE 802.11 AP management,
IEEE 802.1X/WPA/WPA2/EAP/RADIUS Authenticator
Copyright (c) 2002-2016, Jouni Malinen <j@w1.fi> and contributors
```

# Hostapd

如果提到hostapd，大概会有人觉得`create_ap`会更好用一些。我承认，你抱着笔记本回家过年，年夜饭
桌上有人需要临时用一下ap，`create_ap`确实是一个十分有效的工具，但是如果是自己实验室或寝室的
长期使用的ap，`create_ap`显得有点笨重，它把dns、dhcp以及路由的配置都糅合进去了。对于复杂的网络
配置，我认为并不比hostapd简单。

hostapd的配置其实比较简单，顺着默认的配置文件读一遍就基本知道该怎么配了，我也没有配多个ssid的需求，
配置起来就更简单了。

折腾的地方主要在systemd配置。hostapd自己提供了一个service文件，但是它有两个问题：

1. 不支持同时运行多个hostapd实例
2. Unit写着After network.target，这样导致了hostapd启动的时候网络配置已经结束了，这里有一个坑，后面再说。
实际上hostapd不同于其他网络服务，它并不需要网络访问，也不需要听socket，只需要网卡初始化即可。

因此修改之后的service应该是：

```
[Unit]
Description=Hostapd IEEE 802.11 AP, IEEE 802.1X/WPA/WPA2/EAP/RADIUS Authenticator
After=sys-subsystem-net-devices-%i.device
BindsTo=sys-subsystem-net-devices-%i.device
Before=network.target systemd-networkd.service

[Service]
ExecStart=/usr/bin/hostapd /etc/hostapd/%i.conf
ExecReload=/bin/kill -HUP $MAINPID

[Install]
WantedBy=multi-user.target
```

%i会替换成对应的interface名，`After=network.target`改成了`Before=network.target systemd-networkd.service`，
这样systemd-networkd会等hostapd启动之后才会运行。

`After=`保证了hostapd运行时网卡已经启动了。`BindsTo=`则保证网卡被拔掉之后hostapd自动关闭。

之后把interface对应的配置文件写到`/etc/hostapd/<interface>.conf`。

禁用系统自带的service：

```
$ sudo systemctl mask hostapd
```

启用新的service：

```
$ sudo systemctl enable hostapd@<interface> --now
```

如果service运行不出错，interface就已经正常起来了，这个时候你的手机已经能搜到这个ap了，但是现在是连不上的，
因为网卡没有配置ip，也没有配置dhcp。

这些工作都交给systemd-networkd了。


# 关于systemd-networkd

systemd-networkd用了有一段时间了，不太适合经常变化的网络，但是对于网络状况比较固定
但是网络环境比较复杂的机器还是挺适合的，比如soft ap。

systemd-networkd一个比较舒服的地方是，你可以简单的把所有的网络配置都写在一个统一的地方，
而不用写在各种各样的`up.sh`里，这样也免得弄乱。

我曾经遇到过一个问题，我的一台跳板机器上配了一个openvpn，在openvpn的`up.sh`里配置了一套
玄学路由，后来家昌喵配了另一个VPN，需要这套玄学路由，居然把他的VPN的up脚本直接写到了我的
`up.sh`里，最后网络变得一团糟。

后来跳板机迁移，我在up.sh里就写了ip link xxx up。其他的配置都扔到了systemd.network里，这样
思路就清晰多了，玄学路由也被拆了出来。

对于systemd-networkd来说，它不在乎你的interface来自于vpn，有线网卡还是无线网卡，只要interface
up了，它就将配置写进去。这样能让我专注于网络拓扑本身，而不是它的接入方式。

如果仅仅只有一个无线网卡需要配置，那么直接写一个systemd.network配置就可以了。但是我的两个pc
都有两个网卡，而且我希望这个两个网卡的ap接入的是同一个子网（大多数市面上的无线路由器都是这样的），
因此需要用网桥把两个interface接到一起。

systemd-networkd在最近的版本里已经支持了网桥，只需要在`/etc/systemd/network/`下放一个netdev文件，
如br0.netdev：

```
[NetDev]
Name=br0
Kind=bridge
```

接着用一个network文件(如ap.network)来配置interface加入到这个网桥里。

```
[Match]
Name=xxxx
Name=yyyy

[Network]
Bridge=br0
```

Name 是你希望加入到这个网络中的网卡的interface名，也可以通过mac地址等其他方式来配置。

在自动启动的过程中，有可能会出现一个问题，就是systemd-networkd启动并且配置网桥并且将interface加入到
网桥的时候hostapd还没起来，这个时候的网卡不能加入到bridge里，github上有一个
[issue](https://github.com/systemd/systemd/issues/936)。Before `systemd-networkd.service`解决了这个问题，
但是我感觉可能导致系统的启动时间变长，因为调度顺序上，hostapd被提前了，After `network.service`的服务需要
阻塞等待hostapd，anyway，我并没有实际感受到任何区别。

这样restart systemd-networkd之后就发现网卡已经加入到新建的bridge里了。这个时候直接配置这个bridge就可以了。
依然通过一个network文件(如br0.network)来配置。

```
[Match]
Name=br0

[Network]
Address=192.168.233.1/24
DHCPServer=yes
IPForward=yes
IPMasquerade=yes

[DHCPServer]
PoolOffset=100
PoolSize=100
DNS=192.168.233.1
EmitRouter=yes
EmitTimezone=yes
```

配置已经很好懂，我给dhcp的地址池留了100个地址，方便未来可能会要配静态地址，100个地址对于我的usb网卡也差不多到
极限了。

DNS将连接设备的DNS解析器指向给定地址。

EmitRouter让连接上这个wifi的设备把默认路由设置成ap，也就是192.168.233.1，EmitTimeZone则会向设备广播时区。

有趣的是IPForward和IPMasquerade这两个选项，他们会分别替你打开sysctl里的forwarding以及在iptables里加入SNAT规则。
其中IPMasquerade隐含了IPForward，为了verbose，我还是都写上了。一方面比较省事，最重要的是，这个比脚本可读很多。

这样，网络部分的配置就完成了。

# DNS

上面可以看到，我在PC上配置了一个DNS服务器，用的是dnsmasq，配置比较简单，也没出什么奇怪的问题。如果需要科学上网，
可以配合[dnsmasq-china-list](https://github.com/felixonmars/dnsmasq-china-list)以及VPN使用。

VPN怎么配就不讲了。顺带一提，VPN的网络配置也是放在systemd-networkd里的。
