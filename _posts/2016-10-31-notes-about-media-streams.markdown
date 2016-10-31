---
layout: post
title: "多媒体学习小记"
date: "2016-10-31 16:07:23 +0800"
comments: true
---

# 起因

实验室最近想要对视频站点的重编码和重采样进行逆向分析，保证水印信息能够在这个过程中存活。本来我觉得这是一个很容易
的工作，毕竟我们有ffprobe可以直接用，感觉ffprobe再diff一下就可以了。然而问题在于，之前虽然上过流媒体课，也折腾过
nginx-rtmp-module，但是对于视频流的很多更细节的实现，所以借着这个机会，想更深入地对多媒体的编码存储进行一下更深入
地学习。

# Aspect Ratio

在ffprobe的输出里一般会看到display\_aspect\_ratio和sample\_aspect\_ratio，而且数字上比较奇怪。

[这里](http://forum.videohelp.com/threads/323530-please-explain-SAR-DAR-PAR)有一个浅显简单的解释：

Frame Aspect Ratio == Storage Aspect Ratio
Sample Aspect Ratio == Pixel Aspect Ratio

画面上实际显示的高宽比是Display Aspect Ratio，计算公式如下：

$$ Display Aspect Ratio = Frame Aspect Ratio * Sample Aspect Ratio $$
