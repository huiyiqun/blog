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
Parameter Server 有各种不同的一致性模型，用于不同的应用场景。

这篇博客主要关注的是
《Scaling Distributed Machine Learning with the Parameter Server》这篇论文，
讲的是当时的Parameter Server的实现以及一些设计上的考虑。

除此之外还打算看一下
《More Effective Distributed ML via a Stale Synchronous Parallel Parameter Server》
这篇论文，主要是对 Stale Synchronization Parallel （SSP）这一种一致性模型的介
绍。我对它的设计很感兴趣。

# 参数服务器

参数服务器的设计主要是考虑了：

1. 参数服务器作为分布式学习的通用模块，将它抽象出来单独实现有利于使得应用相关
的代码更加简介。
2. 另一方面主要是考虑作为一个通用的模块，优化它对于所有的机器学习算法都能有
增益。

对于参数服务器，作者提出了以下五点关键特征：

* 高效传输
* 灵活的一致性模型
* 弹性扩展
* 错误快速恢复
* 易用性
