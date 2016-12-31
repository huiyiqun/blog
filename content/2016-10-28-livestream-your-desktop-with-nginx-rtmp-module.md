Title:    用nginx-rtmp-module直播写代码
Date:     2016-10-28 15:30:40
Category: Multimedia

# 前言

前段时间用nginx-rtmp-module搭了一个直播系统，测试的时候用来直播了一下桌面，感觉评价还不错，应邀写个简单的教程。

# 服务器

## 安装

服务器端我用的是[nginx-rtmp-module](https://github.com/arut/nginx-rtmp-module)，操作系统用的是CentOS 7，部署其实很简单，
它主页上就有[教程](https://github.com/arut/nginx-rtmp-module#build)。

当然为了系统比较干净，推荐还是简单打个包，CentOS的话我推荐从[nginx的官方源](https://nginx.org/packages/centos/7/SRPMS/)下载
源码包，在configure的参数上加一条`--add-module=/path/to/nginx-rtmp-module`即可。

如果是archlinux的话可以考虑用[aur的里的包](https://aur.archlinux.org/packages/nginx-rtmp)。

## 基本配置

nginx的基本配置可以参考如下:

```
user  nginx;
worker_processes  1;

error_log  /var/log/nginx/error.log warn;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}

rtmp {
    server {
        listen 1935;
        application live {
            live on;
            drop_idle_publisher 10s;

            pull <src.url> name=<src.name> static;
        }
    }
}
```

如果单纯想用rtmp作推流和播放的话，以上的配置就足够了，pull可以让nginx-rtmp-module自动从其他地址拖流在本地播放，
如果不需要可以去掉。

如果服务器有SELinux的话，可以考虑关掉，主要是因为1935这个端口号。

## 认证与动态拉流

这里有两个问题，第一是任何一个知道这个url的用户都可以向这个地址推流，第二是拉流的地址是固定好的，如果你临时起意
想从某个地址拉流，那么你必须修改这个配置文件并且重启nginx（注意reload是无效的，因为rtmp是一个有状态的长连接，
reload并不能让nginx切到新的配置，这个算是nginx-rtmp-module的bug吧）。

nginx-rtmp-module提供了一个方案是[notify](https://github.com/arut/nginx-rtmp-module/wiki/Directives#notify)，
也就是采用回调的方式对用户的身份进行验证，同时也允许你动态定义从什么地址动态拉流。

简单说来就是，每当有一个播放或推流请求时，nginx-rtmp-module都会向你指定的地址发送一个http请求，并带上一些参数，
如请求类型（connect, play, publish等），请求地址，url（会带上rtmp的参数）。针对服务器返回的值，nginx-rtmp-module
会采用不同的行为。2xx会正常放行，3xx会从另一个地址拖流，其他返回值则使这个请求被中断。接下来就完全由的你想象来决定
你的rtmp服务器有什么样的访问控制了。

另外在连接断开的时候也有类似的[回调请求](https://github.com/arut/nginx-rtmp-module/wiki/Directives#on_play_done)，
但是服务器的返回值不会对nginx-rtmp-module的行为造成影响。可以用来记录在线人数，播放时长等。

相关的配置如下：


```
...

rtmp {
    server {
        listen 1935;
        application live {
            live on;
            drop_idle_publisher 10s;

            on_play http://127.0.0.1/live_control/play;
            on_play_done http://127.0.0.1/live_control/play_done;
            on_publish http://127.0.0.1/live_control/publish;
            on_publish_done http://127.0.0.1/live_control/publish_done;
        }
    }
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    #tcp_nopush     on;

    keepalive_timeout  65;

    #gzip  on;

    server {
        location /live_control {
            proxy_pass <live_control_url>;
            proxy_redirect off;
            proxy_set_header Host $host;
            proxy_ssl_verify on;
            proxy_ssl_verify_depth 3;
            proxy_ssl_trusted_certificate /etc/pki/ca-trust/extracted/pem/tls-ca-bundle.pem;
            allow 127.0.0.1;
            deny  all;
        }
    }
}
```

需要注意的是，nginx-rtmp-module的所有回调都不支持https，所以如果想用https在远端作控制需要用http在本地中转一次。

# Dash与HLS

rtmp虽然是一种老牌的流媒体协议，但是它存在一些固有的问题。比如对现有的CDN基础设施不友好，相对于HTTP更复杂，
有状态。现在的流媒体也有倾向于采用HTTP协议来进行流媒体传输的趋势。但是HTTP协议存在延时大的问题，算是各有利弊。

nginx-rtmp-module内置了对hls和dash的支持。其中hls我用了一段时间，感觉还好，dash没用过，我就不评价了。

其实hls的支持也很简单，就是简单地进行了切片。如果需要转码、多码率等功能，需要自己用push和
[exec\_push](https://github.com/arut/nginx-rtmp-module/wiki/Directives#exec_push)拼一下，我之前试的时候效果并
不好，所以不太推荐，当然也可能是我之前机器不太好（因为ffmpeg可能会吃掉所有CPU，机器好不好影响挺大的）。

hls的配置如下

```
...

rtmp {
    server {
        listen 1935;
        application live {
            live on;
            drop_idle_publisher 10s;

            hls on;
            hls_path /tmp/hls;
            hls_fragment 3s;
        }
    }
}


http {

    ...

    server {

        location /hls {
            types {
                application/vnd.apple.mpegurl m3u8;
            }

            root /tmp;
            add_header Cache-Control no-cache;

            # To avoid issues with cross-domain HTTP requests
            add_header Access-Control-Allow-Origin *;
        }

        location ~* ^/hls/.*\.m3u8$ {
            types {
                application/vnd.apple.mpegurl;
            }
            root /tmp;
            expires -1; # disable cache
        }

        location ~* ^/hls/.*\.ts$ {
            types {
                video/mp2t ts;
            }
            root /tmp;
            expires @5m;
        }
    }
}
```

简单说，nginx-rtmp-module会帮你把hls切好，你需要自己用http服务器把它服务出去。

## 状态监视

之前说了可以用notify实现在线人数监视，不过这个也不那么可靠（毕竟HTTP请求失败了nginx-rtmp-module不会重试），另外
相对也挺复杂的。其实nginx-rtmp-module内置了一个状态信息。

配置如下：

```
...

http {

    ...

    server {
        location / {
            rtmp_stat all;
            rtmp_stat_stylesheet stat.xsl;
            allow <your-network>;
            deny all;
        }

        location /stat.xsl {
            root /srv/stat;
        }
    }
}
```

简单地在nginx的http配置里加上rtmp\_stat就可以了，会返回一个xml文件，如果你想在浏览器里比较舒服地看这个xml文件，
可以从[这里](https://github.com/arut/nginx-rtmp-module/blob/master/stat.xsl)下载xsl文件放到服务器上，并且加上
后面的配置。最后如果不想被围观，可以加上acl。（如果你已经写了一个回调http服务器的话，也可以用
[这个模块](https://nginx.org/en/docs/http/ngx_http_auth_request_module.html)，效果拔群。

## Alternative

我在接触直播之后用的第一rtmp服务器就是nginx-rtmp-module，感觉用起来还不错，就一直用下来的。前天讨论的时候感谢
@typcn 童鞋指出了，nginx-rtmp-module的一些问题：

1. 没有修 pts，只是简单复制，兼容性差
2. 没有GOP重传，用户加入之后拿到的第一帧不是关键帧，导致用户开始播放后，会有数秒的黑屏，直到收到下一个IDR帧

他的原话是

> nginx-rtmp 是最差的 rtmp 服务器：

他指出的2我已经验证过了。即使如此，我觉得nginx-rtmp也有一些可圈可点之处：

1. 在直播的过程中，不可避免的还是会用到http服务（认证、HLS、状态），nginx作为久经考验的http服务器，还是值得信赖的。
既然会用上nginx，能all-in-one的话还是不错的，而且配置也能放在一起，比较方便维护。
2. 文档质量很高。nginx-rtmp-module的[reference](https://github.com/arut/nginx-rtmp-module/wiki/Directives)非常
清晰，结构清楚。

@typcn 和 @youngcow 老师相对于 nginx-rtmp-module 都更推荐 srs。感兴趣的可以去尝试。

# 客户端

现在我们已经有一个能正常运转的rtmp服务器了，接下来需要的是是从本地把桌面的视频和音频通过rtmp发到服务器上。

这是我在Linux下用的命令：

```
~> ffmpeg -video_size 1920x1080 -framerate 25 -f x11grab -i :0.0+0,0 -f pulse -ac 2 -i default -f flv -codec:v libx264 -preset slow -crf 22 -x264opts keyint=100:min-keyint=20:scenecut=-1 -codec:a aac "rtmp://{{server_ip}}/live/tuna"
```

1. `-video_size 1920x1080 -framerate 25 -f x11grab -i :0.0+0,0`从我的X服务器屏幕上抓了1920x1080的视频。
2. `-f pulse -ac 2 -i default`从我的pulseaudio服务器把音频抓了出来。理论上从alsa抓也可以，但是我没有成功。arch下如果要从pulseaudio抓音频的话，只需要装pulseaudio这个包，重启一下机器，然后装pavucontrol，运行上面的命令之后在pavucontrol的record这个tab下就会看到我们的流，选择一个合适声卡就可以了。
3. `-codec:v libx264 -preset slow -crt 22 -codec:a aac`编码成h264和aac。这是nginx-rtmp-module官方支持的编码。
4. `-x264opts keyint=100:min-keyint=20:scenecut=-1`是为了避免 @typcn 提出的问题2，也就是故意在视频中插入较多的关键 帧，减少黑屏的出现，相应的也会增高码率。
5. 最后是rtmp的url，因为我们用了rtmp的默认端口，可以不用写端口号，live是application的名字，tuna则是channel的名字。

其他操作系统的用户可以参照[这里](https://trac.ffmpeg.org/wiki/Capture/Desktop)。
