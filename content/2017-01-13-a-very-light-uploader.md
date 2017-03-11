Title:    一个非常轻量级的HTTP上传工具
Date:     2017-01-13 13:32:07
slug:     a-very-light-http-uploader
Category: Ops

# 起因

最近项目需要，需要提供一个http的接口，让用户可以通过浏览器上传文件。本来是一件很简单的事情，不需要认证，也不需要支持断点续传，只要能够上传就可以了，
以为肯定用nginx就能支持。然而一番调研下来发现这一件事情并没有想象中那么简单，不过庆幸的是，最终我还是用nginx+一个简单的Python脚本搞定了这件事情。

主要参考了[这篇博客](https://coderwall.com/p/swgfvw/nginx-direct-file-upload-without-passing-them-through-backend)，
里面提到的其他解决方案包括一些三方扩展，然而添加扩展需要重新编译打包nginx，不到万不得已我还是不太愿意。

最后一个解决方案是用`nginx_http_core_module`里的[client\_body\_in\_file\_only](https://nginx.org/en/docs/http/ngx_http_core_module.html#client_body_in_file_only)。
下面的方案就是围绕这个选项实现一个轻量的上传工具。

# 背景

根据这篇博客里的说法，如果不设置这个特性，nginx会把用户请求整个存到硬盘，再将这个文件传给后端，后端再根据自己实现的逻辑解析这个文件，得到想要的东西。
对于上传任务，后端一般会从body中解析出文件，分别存储到硬盘，再放回结果给nginx。

需要注意到，这里有两个问题：

1. 我想要的上传器是十分简单的，既不需要验证，也不需要一个请求上传多个文件，因此实际上整个body就是一个文件，如果我把body从文件里读出来，再写到另一个硬盘，
那么客户端会很奇怪地发现，为什么我发完最后一段数据之后服务器就没响应了？实际上服务器在做一个非常傻的重io操作。
2. 既然我想实现一个简单的上传器，如果要我去实现一个非常复杂的后端，解析用户请求，考虑异步操作，依赖三方库，简直不可想象，那么其实nginx的性能优势完全没有发挥出来。

另外如果你需要认证的话，还有一些其他问题，比如用户验证是在nginx接收完所有用户数据之后才进行的，用户可能会等10分钟上传一个大文件，然后收到一个403，
想想都觉得头大，由于和我的需求不相关，这里就不讨论这个问题了，大家可以参考上面引用的博客。

# 解决方案

## 后端

首先是对原英文博客的解决方案的一个类似配置，去掉了认证，用`if`替换了原来的`limit_except`:

```nginx
location /upload/ {
    if ($request_method != POST) {
        return 405;
    }

    client_body_temp_path      /srv/nginx/;
    client_body_in_file_only   on;
    client_body_buffer_size    128k;
    client_max_body_size       2000M;

    proxy_pass_request_headers on;
    proxy_set_body             off;
    proxy_redirect             off;
    proxy_pass                 http://127.0.0.1:8000;
}
```

好，以上配置应该能让nginx把文件存储到/srv/nginx/下了，有两个问题：

1. 文件名是随机的数字，之后无法分辨用户本来上传的是哪个文件。
2. 这个后端怎么办呢？如果去掉proxy\_pass，nginx会把这个请求当做GET处理，去找静态文件，但是这样我们就失去了继续处理这个文件的可能性。

因此我认为合理的解决方案是在nginx把文件存储到临时目录下之后，由一个后端作一下`mv`，而`mv`这个操作在同一个文件系统下是十分廉价的，基本可以认为开销可以忽略。
本着简单高(cu)效(bao)的原则，我用`Python3`的内置http服务器实现了这样一个后端。这个脚本性能应该不会有多好，但是考虑到正常情况下这个API并发数不会很高，
我觉得是可以接受的。

代码如下：

```python3
import logging
import os
import shutil
import urllib

from os import path
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger('file-saver')

os_tmp_dir = os.environ.get('OS_TMP_DIR', '/tmp/os/tmp')

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        tmp_file = self.headers['X-TMP-FILE']
        token = urllib.parse.unquote(self.headers['X-TOKEN'])
        original_name = urllib.parse.unquote(self.headers['X-ORIGINAL-NAME'])
        if not (tmp_file and
                token and '/' not in token and
                original_name and '/' not in original_name):
            print(tmp_file, token, original_name)
            self.send_response(400)
            self.end_headers()
            return
        dest_file = path.join(os_tmp_dir, token, original_name)
        try:
            os.rename(tmp_file, dest_file)
        except FileNotFoundError:
            logger.info('Invalid token: {}'.format(token))
            self.send_response(400)
            self.end_headers()
            return

        self.send_response(200)
        self.end_headers()

httpd = HTTPServer(("127.0.0.1", 8000), Handler)
httpd.serve_forever()
```

(最近YCM坏了，写得有点奇怪，凑活吧。）

我希望文件被存到一个二级目录下，即`<root>/<token>/<original_name>`，这里取了个巧，让nginx替我解析路径，这样不用在代码里解析，因此nginx的配置需要改成：

```nginx
location ~ ^/upload/([^/]+)/([^/]+)$ {

    set $token $1;
    set $original $2;

    if ($request_method != POST) {
        return 405;
    }

    client_body_temp_path      /srv/nginx/;
    client_body_in_file_only   on;
    client_body_buffer_size    128k;
    client_max_body_size       2000M;

    proxy_pass_request_headers on;
    proxy_set_header           X-TMP-FILE $request_body_file;
    proxy_set_header           X-TOKEN $token;
    proxy_set_header           X-ORIGINAL-NAME $original;
    proxy_set_body             off;
    proxy_redirect             off;
    proxy_pass                 http://127.0.0.1:8000;
}
```

需要注意nginx配置里的`client_body_temp_path`和python脚本里的`os_tmp_dir`应该保持在同一个文件系统下，否则跨文件系统复制文件可能失败或性能很低。

如果我没有抄错代码，到这里你的上传器就可以用了，你可以：

```
~> curl --data-binary @src.txt http://example.com/upload/this-is-a-path/dest.txt -v
```

测试一下。

到了这，上传器的后端已经基本搭好了，不过如果用这个来作为web API在浏览器里调用，基本上会跪，有两个原因：

1. nginx不支持`OPTIONS`方法，浏览器的安全策略会阻止`POST`请求。
2. 一般来说这种上传器都是'Software as a Service'吧，那么必须要解决CORS。

完整的nginx配置如下：

```nginx
location ~ ^/upload/([^/]+)/([^/]+)$ {
    set $token $1;
    set $original $2;
    add_header 'Access-Control-Allow-Methods' 'POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Headers' 'Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type' always;
    add_header 'Access-Control-Max-Age' 1728000 always;
    add_header X-Frame-Options "DENY";

    if ($request_method = 'OPTIONS') {
        add_header 'Content-Type' 'text/plain charset=UTF-8';
        add_header 'Content-Length' 0;
        add_header 'Access-Control-Allow-Methods' 'POST, OPTIONS' always;
        add_header 'Access-Control-Allow-Origin' '*' always;
        add_header 'Access-Control-Allow-Headers' 'Keep-Alive,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type' always;
        add_header 'Access-Control-Max-Age' 1728000 always;
        add_header X-Frame-Options "DENY";
        return 204;
    }
    if ($request_method !~ ^(POST|OPTIONS)$) {
        return 405;
    }

    client_body_temp_path      /srv/nginx/;
    client_body_in_file_only   on;
    client_body_buffer_size    128k;
    client_max_body_size       2000M;

    proxy_pass_request_headers on;

    proxy_set_header           X-TMP-FILE $request_body_file;
    proxy_set_header           X-TOKEN $token;
    proxy_set_header           X-ORIGINAL-NAME $original;
    proxy_set_body             off;
    proxy_redirect             off;
    proxy_pass                 http://127.0.0.1:8000;
}
```

有两点需要注意，如果对nginx配置不熟悉的话：

1. `add_header` 被重复写多遍的原因是，`add_header`继承上层block的条件是本层没有`add_header`，因此如果你加了一个`add_header`，就需要把上层的所有`add_header`全部复制过来。
2. 配置中有两个正则匹配，需要在第一次匹配之后把结果存下来，否则第二次匹配的时候会覆盖第一次的结果。

OK，后端完成了，个人感觉还是很轻而且很容易部署的，改一下nginx配置（如果你已经有一个在运行的nginx实例），再上传一个脚本，用systemd跑起来，确保它不会出错退出即可。

## 前端

贴一下效果图：

![](https://img.vim-cn.com/4c/c4429b667e525ca92b56870d34e8d2ca02adb1.jpg "上传")

关于前端我不会讲特别细，因为

1. 我觉得前端的实现是一个比较case-by-case的东西，我的代码应该不能直接使用。
2. 我前端比较弱，就不误人子弟了。

如果想实现类似的效果，可以借鉴我的经验。

最初我尝试了一下 vue.js 的 cli 工具建立的模板项目，但是我那时候对 webpack 本身就不熟悉，生成的模板看不懂，最终放弃了。
其实从一个最简单的 `webpack.conf.js` 开始写起反而比较容易，因为 `webpack.conf.js` 只需要写非常少的东西就能运行，
之后你需要加什么功能就对应地加上插件和配置，学习曲线很平缓。

当前 webpack 比较坑的是 2 还在beta，npm 直接安装会装 1，因此需要 `npm install webpack@beta`，另外 2 的文档很不全，搜到的大部分是 1 的，总的来说我觉得 2 还是用起来很舒服的，特别是rule的配置，比 1 科学。如果要查 webpack 2 的配置，权威的位置是[这里](https://webpack.js.org/)，据我观察其他都是讲 1 的。

以下是我现在的 `webpack.conf.js`：

```js
const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');

module.exports = {
  entry: ['whatwg-fetch', './src/index.js'],
  output: {
    path: './dist',
    filename: 'bundle.js',
  },
  resolve: {
    alias: {
      'vue': 'vue/dist/vue.common.js',
      'bootstrap.css': 'bootstrap/dist/css/bootstrap.css',
      'bootstrap.js': 'bootstrap/dist/js/bootstrap.js',
    },
  },
  module: {
    rules: [{
      test: /\.(vue|js)$/,
      enforce: 'pre',
      exclude: /node_modules/,
      loader: 'eslint-loader',
    }, {
      test: /\.vue$/,
      loader: 'vue-loader',
    }, {
      test: /\.js$/,
      exclude: /node_modules/,
      loader: 'babel-loader',
    }, {
      test: /\.css$/,
      loader: 'css-loader',
    }, {
      enforce: 'post',
      test: /\.css$/,
      loader: 'style-loader',
    }, {
      enforce: 'post',
      test: /\.(ttf|woff|woff2|eot|svg)/,
      loader: 'file-loader',
      options: {
        name: 'fonts/[name].[ext]',
      },
    }],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: '!pug-loader!index.pug',
    }),
    new webpack.optimize.UglifyJsPlugin(),
    new webpack.ProvidePlugin({
      $: 'jquery',
      jQuery: 'jquery',
    }),
  ],
  devtool: '#inline-source-map',
};
```

流程上大概是，以一个js作为入口，入口处使用vue-router设置整个app的route，逐层引入vue.js的单文件component作为依赖。
最后用`HtmlWebpackPlugin`这个插件来渲染模板，插入我们的js入口，作为浏览器入口。

当前有两个route，login和uploadList，uploadList包含多个uploadFile，每个uploadFile负责一个文件的上传。

UI上，直接使用了bootstrap，没什么好说的，堪堪够用。

上传部分的代码就非常简单了，因为XMLHttpRequest level 2直接提供了上传文件的支持：

```js
const xhr = new window.XMLHttpRequest();
xhr.open('POST', url, true);

// xhr.addEventListener...

xhr.send(file);
```

这里的file就是一个File。

另外在写vue.js的时候建议遵循以下原则，算是我的一点小经验：

1. 向下传数据用 `v-bind`。
2. 向上传数据用 `$emit`。
3. 共享状态存到父节点，再用上面的方式来更新和传递。
4. 谨记使用 vue.js 是为了分离数据逻辑和UI逻辑，别依赖它做多余的事情。

就会发现 vue.js 越写越顺畅。

# 总结

折腾这个东西花了我总共两个通宵的时间，虽然很累，但是顺便复习了一下vue.js，而且对webpack有了比较深的理解，感觉收获挺大的。
