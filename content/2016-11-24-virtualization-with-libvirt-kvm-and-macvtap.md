Title:     基于libvirt kvm macvtap的虚拟化解决方案
Date:      2016-11-24 09:02:24
slug:      virtualization-with-libvirt-kvm-and-macvtap
Category:  Ops

## 前言

这其实是很早以前折腾的东西，但是感觉网上的资料不是很清楚，现在补一下，以免以后想不起来。

## macvlan 与 macvtap

其实之所以会用macvtap来做网络端口复用是因为libvirt默认用了它，后来折腾的过程中看了代码，理解了原理，
才明白它相比于以前的bridge方案确实有一些优势，如果虚拟机的流量确实很大，可以用这套方案，来减少物理机的CPU和
网卡的压力。

macvtap与macvlan实际上是内核里面的两个特性，用于在物理网卡后面接一些虚拟端口，复用物理端口，但是利用了网卡
的一个较新的特性，所以从性能上来说比纯虚拟交换性能更高，属于一种半虚拟化方案。

macvlan实际上和虚拟机并不是紧耦合的，你也可以在自己的机器上开一个macvlan做试验：

```
~> sudo ip link add link eno1 type macvlan
```

__注意把eno1替换成你的物理端口名__

好了，你现在有一个macvlan0了，你可以试试

```
~> sudo ip link set macvlan0 up
~> sudo dhcpcd macvlan0
```

如果你的网络里有slaac或dhcp6，那么你应该能顺利地拿到IPv6地址。如果你的网络里有dhcp，那么你应该能顺利地拿到IPv4
地址。

你应该会注意到，macvlan端口的mac地址与物理端口的mac地址是不同的。

macvtap实际上是在macvlan创建的虚拟端口后面接了一个字符设备，方便某些场景（比如虚拟机）。

### macvlan实现

以下是macvlan的实现中用到的数据结构：

```
 +------------------------------------------------------------------------------------------------+
 |                                                                                                |
 |                         +------------------------------------------------------------------+   |
 |                         |                    +---------------+                             |   |
 |  register_rx_handler    |               +---->macvlan_device0|                             |   |
 |        +----------------------+         |    +---------------+    +-------------------+    |   |
 |        |                |     |         |    |    priv_data+------>       vlan0       |    |   |
 |        |                | +---+----+    |    |               |    +-------------------+    |   |
 |   +----v-------+        +->  port  |    |    |               |    |    lowerdevice+------------+
 +---> phy_device |          +--------+    |    |               |    |                   |    |
     +------------+          |passthru|    |    |               |    |         port+----------+
                             |        |    |    |               |    |                   |
                             |  vlans+-----+    |               |    |         mode      |
                             |        |    |    |               |    |                   |
                             +--------+    |    |               |    |                   |
                                           |    +---------------+    |                   |
                                           |                         |                   |
                                           |    +---------------+    +-------------------+
                                           +---->macvlan_device1|
                                           |    +---------------+
                                           |
                                           |    +---------------+
                                           +---->macvlan_device2|
                                                +---------------+
```

对于每一个物理设备phy\_device，在第一个macvlan设备创建的时候，会创建一个port，
它会注册一个rx\_handler来处理phy\_device收到的frame，再将其分发给macvlan设备。

如果macvlan工作在passthru模式上，那么port上只允许attach一个macvlan\_device，否则会维护一个vlans列表，
每一个成员对应该物理设备下的一个macvlan设备。

如果你对于网卡驱动开发比较熟悉的话，这里的macvlan\_device就是网卡设备所对应的数据结构了。
它的priv\_data里存了一些指针，用于访问phy\_device和port。

为什么说macvlan用到了物理网卡的特性呢？我们都知道，除非在网卡上设置了promisc、allmulti等flag，
否则网卡只会把符合mac地址的包传到总线上，操作系统不会收到其他包，因此内核不需要花费大量的CPU时间来处理中断，
把不相关的包drop掉。而新的网卡不仅支持根据其本身的mac地址来过滤包，还支持操作系统主动向其添加白名单，
让指定的包通过网卡的过滤，送到操作系统。

macvlan实际上就是利用了这个特性，主动把macvlan设备上的过滤列表添加到物理设备的过滤列表里，
依然利用物理网卡来过滤不相关的包，同时又放行了macvlan设备所需要的包。一般来说现在的网卡都支持这个特性，
如果不支持这个特性，macvlan基本上就没什么优势了（这是我认为的，首先我没有这样的设备，其次我没有读过bridge的代码，
因此不一定准确）。

__NOTE: ldd3里对于网卡接口的描述已经过时了，特别是多播部分的set\_multicast\_list这个接口，实际已经改名字了。__

_macvlan设备是支持串联的，你可以在macvlan设备上挂载macvlan设备。在内核模块里，
它会把新的macvlan设备直接挂到物理设备的port上，因此性能上不会有损失。_

## 虚拟化方案

libvirt 和 KVM 都是比较成熟的方案，这里就不赘述了。下面说一下三者配合的时候遇到的一些问题。

### 虚拟机里收不到多播包

上面macvlan的介绍里已经提过了，macvlan设备的过滤列表是会同步到物理设备上的，所以问题在于虚拟机里的网卡上的过滤
列表如何同步到物理机上的macvlan设备。

libvirt的这个
[commit](https://libvirt.org/git/?p=libvirt.git;a=commit;h=d70cc1fa7219b347a301e132bb927f41958b372d)里添加了
相应的支持，原理上是通过监听qemu的NIC\_RX\_FILTER\_CHANGED事件，进行同步。

与此同时，在这个
[commit](https://libvirt.org/git/?p=libvirt.git;a=commit;h=07450cd42951d5007ab28d8e522f65d948181674)里设置了
一个开关，只有trustGuestRxFilters被设置为yes时上面的机制才会工作。

[这里](https://libvirt.org/formatdomain.html#elementsNICS)对于trustGuestRxFilters有一些介绍，简而言之，为了让
虚拟机收到多播包，你需要：

1. libvirt版本大于1.2.10
2. trustGuestRxFilters=yes
3. 虚拟机的网卡model用virtio（其他model不支持）

如果你的环境不支持上面的需求，可以简单地workaround一下：在物理机上设置macvtap网卡的allmulticast flag：

```
~> ip link set macvtap0 allmulticast on
```

__把macvtap0替换成你的macvtap端口__

这样虚拟机就可以收到所有多播的包了。但是一方面对性能有影响，另一方面存在一些安全隐患。

最新版本的macvlan实现会在自己被打开allmutlicast时自动打开物理网卡的allmulticast，
如果你打开macvtap设备的allmulti之后依然收不到多播的包，可能是内核不够新，
可以尝试手动开一下物理网卡的allmulticast。

### 虚拟机之间及物理机与虚拟机的通信

macvlan有bridge、VEPA、private、passthru 4种工作模式，其中private和passthru我没用过，
这里主要讲另外两种。

VEPA(Virtual Edge Port Aggregator)是默认的工作模式，它的初衷是希望由物理的交换机来进行所有包交换，
这样可以在交换机上统一配置DHCP filtering之类的策略。

因此这个模式下的macvlan会把所有的包都扔到外部端口上去，期待交换机进行包交换，
把目的地址为本机机器的包再传回来。很多交换机考虑安全原因（防止包打环）是不支持这样的行为的，
但是一些较新的交换机上有这样一个特性，叫hairpin、VEPA或者802.1Qbg。

bridge模式则考虑到某些情况下需要更高效的macvlan之间的通信，因此会在内存中进行包交换，提高速度。

但是无论哪种模式，在没有外部交换机的支持的情况下，都是不可能支持物理端口到macvlan端口的包交换的。
上面的原理部分已经提到了，macvlan的port是在物理端口注册了一个rx\_handler，
它只会对物理端口收到的包进行处理，而物理端口发出去的包macvlan是不会看到的。

private模式我没有细看，但应该是drop掉了目的端口为其他macvlan端口的包。

综上，结论如下：

* 对于有交换机支持的网络中，使用VEPA模式和bridge模式都可以实现物理机与虚拟机之间的所有通信。
* 在无交换机支持的网络中，
    - 使用VEPA模式，虚拟机之间及物理机与虚拟机之间不能进行任何形式的通信；
    - 使用bridge模式，虚拟机之间可以正常通信，虚拟机与物理机不能正常通信。

### IPv6 DAD出错

DAD(Duplicate Address Detection)的相关过程在[rfc2462](https://tools.ietf.org/html/rfc2462#section-5.4)。

IPv6的DAD工作方式是向特定的多播组发送Neighbor Solicitation，在一段时间内看是否收到Neighbor Solicitation或者
Neighbor Advertisement，如果收到了，认为出现了地址冲突，这个地址就不会被使用。

我们实际遇到的情况是，虚拟机的发送的Neighbor Solicitation会立刻被自己收到，因此地址始终都处于冲突状态。

这里其实比较奇怪，因为刚刚看
[代码](https://github.com/torvalds/linux/blob/e76d21c40bd6c67fd4e2c1540d77e113df962b4d/drivers/net/macvlan.c#L295)
的时候发现，macvlan是不会把macvlan端口发出来的包又送回到原端口的，
有可能是因为当时调试的时候开了allmulticast或者promisc，
__进一步确认需要再看一下代码__。
