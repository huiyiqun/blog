Title:    异步Python学习笔记
Date:     2016-12-08 10:29:03
slug:     async-python-note
Category: Python

# About

一般来说说到Python都会说这是一种十分低效的语言，慢等等，然而之前用Gevent做了一个restful，发现其实性能还不错。

其实Python很慢这一点当然是不错的，不适合直接用来作复杂算法的实现。但是当我们需要实现Web服务器等软件时，
性能的瓶颈实际并不在CPU上，多数时间我们都在等待IO，如果IO需要1s，这个时候你用Python实现一段代码运行需要0.01s，
和你用C实现一段代码运行需要0.0001s有什么可感知的区别吗？

所以最重要的是如何地让用户请求不阻塞，充分地让IO跑满。最早人们通过多进程来解决这个问题，后来发现进程实在是太笨重，
转而使用线程来解决这个问题，但是线程切换对于大量短时io依然过重。所以最后人们转而开始强调并发，不再强调并行，
也就是所谓的异步。 这就是为什么Python这样的有PIL存在的，单进程执行语言，在web开发上依然能有一席之地的原因。
所以要用Python高效的实现服务，良好地异步是必不可少的。

Python 3.4 新加了[asyncio](https://docs.python.org/3/library/asyncio.html)，一直很感兴趣，但是也没时间去深入研究。

最近在实验室需要做一个FTP，[pyftpdlib](https://github.com/giampaolo/pyftpdlib)是一个十分优秀的FTP服务器实现，
其本身的实现是基于异步的，同时也支持线程和进程模型。当然考虑到性能问题，最后肯定需要采用异步模型。
但是在这里我遇到了一个问题，pyftpdlib本身有自己的异步IO loop，如果强行上gevent的monkey\_patch有可能导致各种奇怪的bug？

基于这个考虑，我决定系统地对Python的整个异步生态了解一遍，以下是一些笔记。

因为我用Python时间也不算特别长，所以特别久远的异步实现，像twisted我就不提了。
下面主要是围绕asyncio出现之前比较流行的gevent和现在官方实现的asyncio进行分析。

# greenlet

[greenlet](https://greenlet.readthedocs.io/en/latest/)是Gevent的依赖之一，它实现了一种叫"tasklet"的微线程。

官网上的两个例子很适合理解，我就摘抄到这里了：


    from greenlet import greenlet

    def test1():
        print 12
        gr2.switch()
        print 34

    def test2():
        print 56
        gr1.switch()
        print 78

    gr1 = greenlet(test1)
    gr2 = greenlet(test2)
    gr1.switch()


这个例子很简单，首先定义了两个函数作为`greenlet`的入口，在外部定义两个`greenlet`，然后`switch`到`gr1`，
这个时候`gr1`会`switch`到`gr2`，然后`gr2`重新`switch`到`gr1`，`gr1`结束退出，整个程序结束退出。
程序运行的输出如下：


    12
    56
    34


我们可以看到：

1. 程序依然是串行执行的，并没有任何并行存在。
2. 我们成功的在两个函数的串行执行之间进行了切换，也就是所谓的协程。
3. 在API的结构上，很像线程，但是没有线程的隐式切换。

主意到，78并没有被输出，因为`gr2.switch`只被调用了一次，因此`switch`出`gr2`之后就不会再进去了。

如果在程序的最后加上`gr2.switch()`，就能看到78输出了.

Greenlet的另一个例子更有实用价值一些，假设你写了一个console程序：


    def process_commands(*args):
        while True:
            line = ''
            while not line.endswith('\n'):
                line += read_next_char()
            if line == 'quit\n':
                print "are you sure?"
                if read_next_char() != 'y':
                    continue    # ignore the command
            process_command(line)


你想把它变成一个GUI程序，然而GUI框架一般是基于事件的，所以应该如何从read\_next\_char里读到下一个字符，
同时又不阻塞执行呢？一般我们采用多线程，让UI线程和上面的线程进行线程间同步。但是写过多线程的同学应该都知道，
锁的数量多了之后很容易把程序弄得一团糟。

一个解决方法是使用greenlet：


    def event_keydown(key):
             # jump into g_processor, sending it the key
        g_processor.switch(key)

    def read_next_char():
            # g_self is g_processor in this simple example
        g_self = greenlet.getcurrent()
            # jump to the parent (main) greenlet, waiting for the next key
        next_char = g_self.parent.switch()
        return next_char

    g_processor = greenlet(process_commands)
    g_processor.switch(*args)   # input arguments to process_commands()

    gui.mainloop()


代码整个和多线程很类似，但是由于greenlet采用了显式的context切换，所以完全没有必要存在锁。

需要注意到的是上面用到了gevent的parent。parent默认会指向创建这个greenlet的greenlet，
上面的`g_processor`是在最外层定义的，那么它的parent应该是谁呢？

在greenlet的语境里，认为程序开始运行时在主greenlet里（类似于主线程和主进程的概念），所以在最外层创建的greenlet，
其parent就是主greenlet(main)。

parent除了用于方便索引外，另一个意义在于当greenlet退出时会自动switch到它的parent。比如：


    from greenlet import greenlet

    def test1():
        print 12
        gr2.switch()
        print 34
        return '1 return'

    def test2():
        print 56
        print 78
        return '2 return'

    gr1 = greenlet(test1)
    gr2 = greenlet(test2)
    print gr1.switch()


`gr2`退出之后自动switch到其parent，也就是main，因此main中的`gr1.switch`返回了test2的返回值，整个输出如下：


    12
    56
    78
    2 return


# libev

[libev](http://software.schmorp.de/pkg/libev.html)是gevent的另一个依赖。最初的时候gevent使用的是libevent，
后来换成了libev。

libevent和libev从功能上来看差距不大，主要是对操作系统层面的一些系统提供统一的封装。在linux上，
它们都使用了epoll作为底层的基础。在[设计理念](http://stackoverflow.com/a/13999821)上，libev更倾向于UNIX哲学，
而libevent则提供了完整的事件驱动编程框架。

[这里](https://www.ibm.com/developerworks/aix/library/au-libev/)有一些libev和libevent的例子，基本上就是：

1. 注册回调函数。
2. 启动主循环，监测事件。

# gevent

[gevent](http://www.gevent.org/)基于了上面介绍的greenlet和libev。

1. 将Python标准库中的一部分阻塞调用重写为异步调用，并保持API一致，以便运行时直接替换(monkey\_patch)。
2. 实现了TCP/UDP/HTTP/WSGI服务器。
3. 加强了DNS查询的性能。

它的运行过程大概是：

1. main greenlet
2. 任意gevent API被调用
3. 查找Hub greenlet；若不存在，则创建一个
4. Hub greenlet调用libev监听事件，进行调度

一般来说，在程序开头执行如下代码：

    from gevent import monkey
    monkey.patch_all()

你的程序就已经运行在gevent之下了，之后你就可以像使用线程和进程一样使用Greenlet了。

或者对于服务器而言，你可以基于gevent提供的服务器实现具体的逻辑，接着简单地start等待事件（比如用户链接）
来调用你的回调就好了。

gevent用Greenlet来替代线程和进程作为调度单位，一方面缓解了线程和进程在较高的并发场景下开销大，切换速度慢
等问题。另一方面用Greenlet来代替线程+锁实现协程，更加的高效。

但是Gevent的问题在于实际上只有一个线程在执行，所以如果你的某个Greenlet长时间占用CPU，那么Hub没法进入CPU进行调度，
那么用户请求就被阻塞了。不过这个对于习惯了事件驱动编程的Javascript、QT的同学应该都不是问题。

总的来说，gevent在非并行的Python上实现了原本不支持的异步编程，对于实现高并发服务器来说十分友好。

从架构角色的角度来说，我觉得可以这么说，gevent在Python层面上基于libev实现了libevent的角色。

__asyncio的内容晚些再补__
