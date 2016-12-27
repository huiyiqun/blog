---
layout: post
title: "多媒体学习小记"
date: "2016-10-31 16:07:23 +0800"
comments: true
---

# 起因

实验室最近想要对视频站点的重编码和重采样进行逆向分析，保证水印信息能够在这个过程中存活。本来我觉得这是一个很容易的工作，
毕竟我们有ffprobe可以直接用，感觉ffprobe再diff一下就可以了。然而问题在于，之前虽然上过流媒体课，也折腾过nginx-rtmp-module，
但是对于视频流的很多更细节的实现，所以借着这个机会，想更深入地对多媒体的编码存储进行一下更深入
地学习。

# Aspect Ratio

在ffprobe的输出里一般会看到display\_aspect\_ratio和sample\_aspect\_ratio，而且数字上比较奇怪。

[这里](http://forum.videohelp.com/threads/323530-please-explain-SAR-DAR-PAR)有一个浅显简单的解释，简单说来就是：

$$ Frame Aspect Ratio = Storage Aspect Ratio $$

$$ Sample Aspect Ratio = Pixel Aspect Ratio $$

画面上实际显示的高宽比是Display Aspect Ratio，计算公式如下：

$$ Display Aspect Ratio = Frame Aspect Ratio \times Sample Aspect Ratio $$

# tbr tbn tbc

关于这三个参数，[邮件列表](http://ffmpeg-users.933282.n4.nabble.com/What-does-the-output-of-ffmpeg-mean-tbr-tbn-tbc-etc-td941538.html)里有讨论，
但是实际讲的比较模糊，所以我决定还是直接看[代码](https://github.com/FFmpeg/FFmpeg/blob/0c0da45f0fc0626d12796f017918800f735512c8/libavformat/dump.c#L496)。


    int fps = st->avg_frame_rate.den && st->avg_frame_rate.num;
    int tbr = st->r_frame_rate.den && st->r_frame_rate.num;
    int tbn = st->time_base.den && st->time_base.num;
    int tbc = st->codec->time_base.den && st->codec->time_base.num;

    if (fps || tbr || tbn || tbc)
        av_log(NULL, AV_LOG_INFO, "%s", separator);

    if (fps)
        print_fps(av_q2d(st->avg_frame_rate), tbr || tbn || tbc ? "fps, " : "fps");
    if (tbr)
        print_fps(av_q2d(st->r_frame_rate), tbn || tbc ? "tbr, " : "tbr");
    if (tbn)
        print_fps(1 / av_q2d(st->time_base), tbc ? "tbn, " : "tbn");
    if (tbc)
        print_fps(1 / av_q2d(st->codec->time_base), "tbc");


这里用到了四个有理数，libav里有理数的定义在[这](https://github.com/FFmpeg/FFmpeg/blob/415f907ce8dcca87c9e7cfdc954b92df399d3d80/libavutil/rational.h)，
其中den为分母，num为分子，这里的`fps`、`tbr`、`tbn`、`tbc`四个变量分别代指对应的数据是否为合法的值（分子分母都不为0）。

所以实际的输出是来自于下面的print，
其中`print_fps`的定义在[这](https://github.com/FFmpeg/FFmpeg/blob/0c0da45f0fc0626d12796f017918800f735512c8/libavformat/dump.c#L120)，
`av_q2d`的定义在[这](https://github.com/FFmpeg/FFmpeg/blob/415f907ce8dcca87c9e7cfdc954b92df399d3d80/libavutil/rational.h#L104)。

`av_q2d`实际是简单地把有理数转为双精度浮点数。`print_fps`就更简单了，就是一个不带回车的print，后面那么复杂的判断主要是为了在数据间加上逗号。

所以关键在于`st->avg_frame_rate`、`st->r_frame_rate`、`st->time_base`及`st->codec->time_base`这四个变量的含义，
它们的描述在[文档](https://ffmpeg.org/doxygen/3.1/structAVStream.html#a946e1e9b89eeeae4cab8a833b482c1ad)里都有。
由于没有深读代码，我也没有自信翻译这些文档，还是直接看英文原文吧。

# cheatsheet

* 从视频中取出每一帧

```
ffmpeg -i <input> frame_%d.bmp
```
