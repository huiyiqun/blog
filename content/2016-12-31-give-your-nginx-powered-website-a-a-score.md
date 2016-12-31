Title:    让你的nginx网站得到A+
Date:     2016-12-31 13:32:07
slug:     give-your-nginx-powered-website-a-a-score
Category: Ops

# 起因

最近用 github 的 [student pack](https://education.github.com/pack) 领了 [namecheap](https://www.namecheap.com/) 的一年免费域名，并且把博客迁移到了新的域名下。

最初是想直接用 github.io CNAME一下，然而问题在于就没有 https 了。忍了一个月，实在是忍无可忍，自己找了台VPS自己跑。正好服务器也一直空着，没跑什么东西。

之前折腾了一下SSL的相关配置，正好趁机总结一下。

# 安装部署

服务器用的是 archlinux，安装nginx和certbot的方式如下：

```
~> sudo pacman -Syu
~> sudo pacman -S nginx-mainline certbot-nginx
```

# nginx 配置

将 nginx 配置的 server block 改成如下内容：

```nginx
server {
    listen      80 default_server;
    listen      [::]:80 default_server;
    server_name <domain_name>;
    root        /path/to/your/site;
}
```

启动 nginx：

```
~> sudo systemctl enable nginx --now
```

接着签证书：

```
~> sudo certbot --nginx
```

certbot会修改nginx配置，因此需要以root身份运行。另外这个nginx插件会读nginx配置判断域名，因此在nginx配置的`server_name`处应该填入完整的域名。
接着会有一个交互式的界面确认一些信息，顺序填写就好。

最后重启nginx：

```
~> sudo systemctl restart nginx
```

# nginx 调优

这个时候 https 应该已经配置好了，不过强迫症表示在 [ssllabs](https://www.ssllabs.com/ssltest/analyze.html) 只能拿到B不太开心。

关于如何调优，在[这里](https://raymii.org/s/tutorials/Strong_SSL_Security_On_nginx.html)有完整的介绍，下面是我对 nginx 配置作的改动：

1. 把`listen 443 ssl;`改成`listen 443 ssl http2;`：添加 HTTP/2 支持。
2. 加上 `listen [::]:443 ssl http2`：certbot 的 nginx 似乎没有考虑到 IPv6 的支持，所以缺了这一行。
3. 将`ssl_ciphers`改成`"EECDH+AESGCM:EDH+AESGCM:AES256+EECDH:AES256+EDH"`：表示不想支持IE6。
4. 加上`Strict-Transport-Security "max-age=63072000; includeSubdomains; ";`这一行：HSTS（如果不想把http重定向加到https可以不加）。
5. 自制一个dhparam，加到配置里。

接着重启 nginx 即可，现在能拿到 A+ 了，在[这里](https://tools.keycdn.com/http2-test)也能测试到有 http2 支持了。
