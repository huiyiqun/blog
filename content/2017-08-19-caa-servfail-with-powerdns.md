Title:    PowerDNS 上 CAA 记录返回 SERVFAIL 的问题
Date:     2017-8-19 23:22:00
slug:     caa-servfail-with-powerdns
Category: Ops

# 起因

之前搭了一个 IPSec 的 VPN，为了避免需要在客户端导入根证书，使用了 Let's Enrypt 来签署免费证书。这样客户端不用导入自签名的根证书就能正常地认证，用起来很舒服。

今天早上起来发现 VPN 登录不了了，看了一下日志，发现是因为证书过期了，上服务器更新证书，certbot 报 "SERVFAIL looking up CAA for example.com"，之前 certbot 也报过类似的错误，但是其实是其他错误导致的，不过这次经过反复尝试，以及用 dig 测试：

dig -t TYPE257 example.com

发现我的 PowerDNS 确实是返回了一个 SERVFAIL。

# 调查

首先我的 PowerDNS 其实很久没动了，为啥之前可以正常地签证书、更新证书呢。原因是上个月 Let's Encrypt 发布了一个 [申明](https://community.letsencrypt.org/t/caa-servfail-changes/38298)，宣布其更新了对 CAA 记录的支持。

什么是 CAA 记录呢，它全称是 [Certification Authority Authorization](https://en.wikipedia.org/wiki/DNS_Certification_Authority_Authorization)，用于申明只允许特定的 CA 为域名发布证书。在 CA 发布证书的过程中，CA 机构应该检查这个域名的 CAA 记录，如果某个域名存在 CAA 记录，但是 CA 机构的域名不在这个列表里，就应该停止签发证书。CAA 记录是可选的，如果权威 DNS 不返回 CAA 记录则说明任何 CA 机构都可以为该域名发布证书。

之前 Let's Encrypt 对于 CAA 查询的策略是，如果权威 DNS 返回 SERVFAIL，则认为该服务器不支持 CAA，则跳过 CAA 的检查。但是这样显然是有一些隐患的，权威 DNS 返回 SERVFAIL 不一定是因为 DNS 服务器不支持，也有可能是因为 DNS 出现了问题（或者被恶意攻击），在这样的场景下，Let's Encrypt 有可能会错误地签发不应该签发的证书。

因此，在确认大部分 DNS 服务提供者都支持 CAA 记录之后，Let's Encrypt 修改了自身的策略，当权威 DNS 返回 SERVFAIL 的时候则直接拒绝签发证书。不过我的 DNS 是自己在 CentOS 7 上建的 PowerDNS，看起来它并不支持 CAA。

# 解决方案1

上服务器检查了一下 pdns 的版本，是从 EPEL 安装的 3.4.8，而 EPEL 中最新的版本是 3.4.11。根据 PowerDNS 的 [changelog](https://doc.powerdns.com/md/authoritative/upgrading/) 来看，从 4.0.0 开始 PowerDNS 才开始支持 CAA 记录。

所幸 PowerDNS 自己的[软件仓库](https://repo.powerdns.com/)中已经有了 4.0 版本的 pdns，直接添加软件源，`yum update` 一下就有了 pdns 4.0.4。

不过奇怪的是 CAA 请求依然得到的是 SERVFAIL。之后我又尝试了 master 分支的 pdns，结果依然。

# 解决方案2

既然如此，那就添加一个 CAA 记录试试吧。Poweradmin 有一个 [issue](https://github.com/poweradmin/poweradmin/issues/302) 中提到了这个 [PR](https://github.com/poweradmin/poweradmin/pull/291) 已经添加了 CAA 记录的支持，而这个 PR 已经被 merge 了。不过 poweradmin 的上一个 release 还是 2014 年发布的，至今已经有 3 年没有发布新版本了。无它，从 master 分支下载代码，在 poweradmin 里已经可以添加 CAA 记录了。

根据 [RFC](https://tools.ietf.org/html/rfc6844#section-5.1)，CAA 记录由两部分组成：一个 flags 和 一个 tag 对。flags 是一个比特，当前只有最高位被用于 Issuer Critical，代表这个 tag 对的重要性，即如果 CA 不理解这个 tag 对，应该停止签证书（1）或忽略这个 tag 对（0）。需要注意的是 Issuer Critical 是最高位，因此实际上的 flags 应该分别是 128 或 0，

当前支持的 tag 包括：issue issuewild iodef。

issue 表示允许 CA 机构签署证书，issuewild 表示允许 CA 机构签署 wildcard 证书，iodef 表示签署证书时通过指定的方式通知域名持有者。

Let's Encrypt 暂时还不支持 wildcard，所以 issuewild 暂时没什么意义；iodef 是可选的，并且[据说](https://community.letsencrypt.org/t/caa-setup-for-lets-encrypt/9893/3) Let's Encrypt 还不支持 iodef。

综上，在 Poweradmin 里添加一个 CAA 记录，context 填入 `128 issue "letsencrypt.org"` 即可。关于这个 CAA 记录的域名，根据 Let's Encrypt 的[文档](https://letsencrypt.org/docs/caa/)，可以放到需要签证书域名的父域名下，Let's Encrypt 会进行递归查询。另外 CA 域名必须填 letsencrypt.org，这个在文档中也有提到。

接下来重新运行 `certbot renew`，续命成功！

# 解决方案3

虽然问题解决了，我还是不满足，为什么 4.0.4 的 Powerdns 依然返回 SERVFAIL 呢？根据[这里](https://community.letsencrypt.org/t/caa-servfail-changes/38298/2)来看，Powerdns 4.0.4 已经彻底解决了 CAA 请求 SERVFAIL 的问题。翻了一下日志，发现大量错误：

```
Backend error: GSQLBackend unable to list metadata: Could not prepare statement: select content from domains, domainmetadata where domainmetadata.domain_id=domains.id and name=? and domainmetadata.kind=?: Table 'powerdns.domainmetadata' doesn't exist
```

对比了一下数据库里的 table 列表和 pdns-mysql-backend 带的 schema 里的 table 列表，发现缺了不少表，不过有意思的是，其他查询依然能够正常进行。于是补上了所有缺的表，删掉了之前添加的 CAA 记录，经过测试，发现这时候返回的状态变成了 NOERROR。

综上，所有的问题都解决了，如果遇到类似的问题，可以作为一个参考。

至于为啥数据库缺表，这个 Powerdns 是其他人装的，这件事就无从考证了。
