Title:    带cookie的CORS
Date:     2017-3-12 01:01:10
slug:     cors-request-with-cookie
Category: Frontend

# 关于

不得不说，这其实是一个非常悲惨的故事，作为自己25岁生日的礼物，稍微惨了一点。

最近一时兴起，用Vue.js写了一个很简单的[前端项目](https://github.com/huiyiqun/iptv)，也算是希望能在离校之前给自己的学校留下一点东西。

# 起因

之前一切都很顺利，加feature，修bug，都没什么太大的困难，直到开始着手解决认证问题。

受限于各方面的限制，我写的前端所服务的后台服务是不能直接在校外访问的，然而不管是在校生还是已毕业校友都有在校外访问的需要，因此折中一下，这个服务需要认证才能访问。
认证是怎么做的呢？是一个比较传统的方案：先重定向到一个集中认证服务，登录完之后返回后台服务所在的域名，通过后台服务与认证服务交互，确认用户的登录情况，记录用户的身份，设置session，之后用cookie来识别用户的登录情况。

这部分其实与我的前端App没什么关系，因为不管是认证服务还是后台服务都是已经写好在运行的，我只要在访问后台服务的时候捕捉错误信息，正常跳转到认证服务，等待后台服务把用户重定向回来就行，因此与我来说看上去并没有什么关系。

然而问题在于，运行环境的服务器不由我管理，我也不愿意在运行环境下调试，因此我在自己的VPS和域名下部署了一套[staging环境](https://iptv.huiyiqun.me/)用于线上测试，自己开发则在本机用localhost开发，拜托运行的老师在nginx里加了CORS的HTTP headers，一切挺顺利，看上去也很合理，然而在折腾cookie的时候却出了问题。

# 兴起

虽然没有什么必须要用[Fetch API](https://fetch.spec.whatwg.org/)的理由，但是本着新东西要体验一下的原则，这个项目里还是用了`fetch`来替代`xhr`。
上面说了，认证系统是靠cookie来识别用户身份的，那么我必须保证发给后端的请求里要带上cookie，然而跨域请求显然是不会带上cookie的。
简单搜索了一下，找到了[这个](https://fetch.spec.whatwg.org/#cors-protocol-and-credentials)，简单明了。
于是加上`credentials`这个参数，结果chrome上app跑起来，用户请求被重定向到了认证服务，什么鬼。翻了一下调试工具，发现访问后台的时候没有带cookie，直接用浏览器打开后台url，却能正常访问，oookie什么都不少。

这时候我就开始郁闷了：咦，spec理解错了？

于是乎，我开始认真地看了[github的fetch polyfill文档](https://github.github.io/fetch/)，好像没差什么呀。
接着是[MDN](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch)以及[Google Developers](https://developers.google.com/web/updates/2015/03/introduction-to-fetch)，依然看不出来自己的调用方式有什么问题。

于是我开始脑洞大开，难道

> To cause browsers to send a request with credentials included.

是指把源domain的credentials带上？那岂不是密码满天飞？

这时我依稀记起了polyfill的文档里提到了`credentials`为`same-origin`时行为和`xhr`是一致的，于是我觉得有必要复习一下`xhr`的行为。

于是重新看了[MDN](https://developer.mozilla.org/en-US/docs/Web/API/XMLHttpRequest/withCredentials)，以及[这篇博客](https://quickleft.com/blog/cookies-with-my-cors/)。
结论是自己的理解没有问题。

# 发展

这个时候我已经一头雾水了，出错其实不可怕，可怕的是出错了居然没有错误信息。
这就像你写了个`int x = 1`，编译运行发现`x`里存了个`0`，开了所有warning还是什么报警都没有。

于是我觉得编译器也不能相信了：

难道是chrome的实现有问题？由于特性新，我一直非常喜欢在chrome上写前端，要是特性实现有问题，那实在太可怕了，而且搜了半天都没见着issue，实在不可理解。

难道是服务器端给的headers有问题，导致CORS实际上并没有生效？或者只是部分生效？然而没看出什么问题。

难道是我又手贱把单词敲错了？之前因为手贱坑自己的事情并不少见。

于是我打开[httpbin](https://httpbin.org)，开始各种尝试（不得不说，httpbin确实挺好用的，想要的东西基本都有，而且API简单，返回的结果里还带了很标准的CORS headers，很适合用来尝试一些东西）。

把`fetch`换成`xhr`，也没带cookie；反复对比和增删HTTP headers，始终没效果；把标准里的样例直接copy进来，以防自己敲错，依然未果。就这样，我大概从下午两三点一直折腾到了晚上十二点，精疲力尽。

# 高潮

当我都快睡着的时候，一时兴起，准备装个chrome-dev试试，安装的过程中无事，打开了尘封多年的firefox，在console里敲了几段快背下来的测试代码，结果。cookie带上了。

啥？chrome实现有bug？正好chrome-dev装好了，赶紧在chrome-dev里试了一下，依然没有带上cookie。这时候思路开始清晰了，在chrome里开了guest用户，把自己的所有配置都禁掉，一测试，cookie带上了。

我此时头都炸了，哪个傻逼插件坑了我半天！打开扩展列表，把可疑的扩展都禁掉，再试了一次，发现还是不行。打开设置，搜了一下cookie，在content settings里找到了一个打着勾的`Block third-party cookies and site data`，发现自己完全看不懂是什么意思。尝试禁用，这次终于好了。果然最后坑自己的傻逼通常都是自己。

这时才依稀想起，几年前Google似乎是问了我一下，要不要禁用什么什么cookie，避免被追踪，当时糊涂地点了是。

# 总结

1. 自己还是太年轻，换浏览器测试这样的事情都没想到；
2. 测试的时候最好还是别用自己平常用的浏览器，有些上古时期加的玄学配置容易忘记，用干净的浏览器比较好；
3. 遇到事情还是不能急，有些问题只要仔细分析一下，是可以不动手就找到一些蛛丝马迹的；
4. 解决问题要讲究效率。

# 正文

好，上面都是扯淡，看黑板。

如果你要让自己的CORS里带上cookie，完整的步骤是这样的：

1. 服务器端需要加一些headers，以nginx为例，建议用如下配置：

```nginx
add_header Access-Control-Allow-Origin $http_origin always;
add_header Access-Control-Allow-Credentials true always;
```

如果想看实例，建议看`httpbin`的。

2. 客户端需要加一些参数，比如如果是`xhr`需要设`xhr.withCredentials`为true，如果是`fetch`需要设`credentials`为`include`。
3. 确保用户的浏览器没有开`Block third-party cookies`这个选项，或者已经把你的站点加入白名单，这个可以提示用户自己去改。

这篇博客就这么点，晚安。
