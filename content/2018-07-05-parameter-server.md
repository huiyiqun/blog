Title:    分布式机器学习之参数服务器
Date:     2018-07-05 19:00:00
slug:     parameter-server
Category: Paper

# 关于
最近结束了在清华的硕士，到了一家互联网公司上班，前段时间看论文，发现快速扫论文
并且记笔记，等看完之后再扫一遍的方式挺有效的
（特别是对于之前没有接触过的领域）。因此打算继续沿用这个方法继续看一些论文。

因此打算新开一个 Category 用于放笔记。所以这个系列主要是读论文的读书笔记。虽然
最后会稍微整理一下，但是不保证全对，也不保证很清楚。因为这个部分算是学习的副
产品吧。

# 论文
Parameter Server 是分布式机器学习中一种很常见的架构，通过 Parameter Server
来实现参数同步等过程，使得计算可以分布到不同的计算单元甚至不同的机器。
Parameter Server 有各种不同的实现（或者是约束），用于不同的应用场景。

这篇博客主要关注的是
《Scaling Distributed Machine Learning with the Parameter Server》这篇论文，
讲的是当时的Parameter Server的实现以及一些设计上的考虑。

除此之外还打算看一下
《More Effective Distributed ML via a Stale Synchronous Parallel Parameter Server》
这篇论文，主要是对 Stale Synchronization Parallel （SSP）这一类实现的介绍。
我对它的设计的考虑很感兴趣。
