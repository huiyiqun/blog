Title:      不活跃的openssh连接被“冻结”的问题
Date:       2016-10-21 11:08:50
slug:       openssh-freeze-inactive-session
Category:   Ops

# 起因
最近做的两个项目都是跑在CentOS上的，前者是CentOS 6，现在用的是CentOS 7。一个让人
非常恼火的问题是，调试或者看日志的时候，如果开了一个ssh连接，然后另开个窗口，去
跑个ansible或者是改下代码什么的，时间稍微长一点，切回来的时候就会发现ssh连接被
“冻结”了：敲键盘没有回显，同时连接也不会中断。最初我以为这是CentOS设置的某个安全
特性，避免连接被劫持之类的。但是时间长了之后觉得这个特性实在是有点烦，于是我准备
disable这个“特性”。


# 解决
简单地说，在笔记本上的ssh配置（如果是linux，在`~/.ssh/config`）上加上如下配置即可

```
Host *
    TCPKeepAlive yes
    ServerAliveInterval 15
    ServerAliveCountMax 3
```

# 解释
就像之前说的，我最初以为是CentOS上有某种玄学安全特性，所以我把服务器上的
`/etc/ssh/sshd_config`取到本地看了一遍，然而并没有，接着我又看了一遍iptables
的filter表，依然没有找到这样的安全配置。

那么这个“冻结”究竟发生在哪呢？

从TCP开始分析。TCP以下的IP层是不会有问题的，因为只要地址是对的，那么包永远都能送
达。TCP层本身是没有超时中断这一概念的，也就是说只要TCP里的数据发到对方并且被正常
ACK之后，TCP就认为这个连接是好的，之后如果没有新的数据需要传输，TCP两端同时静默
不管多久，TCP都不会认为这个连接有问题，除非收到了RST或FIN，那么连接才会被中断。

然后TCP之上就是ssh了，既然TCP和ssh就没有设计超时中断，为什么我的ssh连接会中断呢？

在Google的时候一个回答启发了我（找不到链接了），虽然两边同时静默不会影响TCP的连
接，但是由于现在的网络中常常会有NAT，比如家用的无线路由器等，NAT为了保证动态的
端口与端口/主机映射关系，会维护一张端口映射表，这张映射表一般会有一个超时时间，
当一个TCP连接长时间处于不活跃状态时，NAT会从这个映射表中删除该表项，之后就不再
知道这个映射关系，接下来的TCP数据也不能继续传输了，也就出现了这个“冻结”的状态。

为了验证NAT的存在，可以用`ss`来验证，ssh到服务器之后，运行`ss -nt`，再在本地运
行，对比二者的端口和地址，来确定你与服务器之间是否有NAT。

ssh的TCPKeepAlive这个选项的解释如下：

```
     TCPKeepAlive
             Specifies whether the system should send TCP keepalive messages to
             the other side.  If they are sent, death of the connection or crash
             of one of the machines will be properly noticed.  However, this
             means that connections will die if the route is down temporarily,
             and some people find it annoying.

             The default is “yes” (to send TCP keepalive messages), and the
             client will notice if the network goes down or the remote host dies.
             This is important in scripts, and many users want it too.

             To disable TCP keepalive messages, the value should be set to “no”.
```

简单说，它的本意是为了保证即使在静默的情况下，也能发现对端主机或者网络出现了问
题，实现方式在[这里](http://tldp.org/HOWTO/TCP-Keepalive-HOWTO/overview.html)
有详细解释，这是一种比较通用的做法。

然而它的一个副作用是，即使ssh隧道中没有流量，在tcp中依然有“空的数据流”流过，因此
NAT的端口映射表也不会因为超时而被删除，“冻结”的情况也被消除了。

文档里面也提到了，TCPKeepAlive会导致网络临时出问题时连接会中断，让人觉得很烦，
针对这种情况，可以把ServerAliveCountMax和ServerAliveInterval的数值调大，一般来
说，ServerAliveInterval只要低于NAT映射表的超时时间即可，ServerAliveCountMax则
可以直接改成一个非常大的值，连接中断也不会触发了。

我的配置中把这三个选项写到了客户端这边，实际上OpenSSH的服务器端也有类似的选项，
可以实现类似的效果，但是需要在每台服务器上都写上，这样太过麻烦，因此选择了写
到客户端。
