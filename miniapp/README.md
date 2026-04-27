# AI 资讯雷达微信小程序

这是微信原生小程序版本，可以直接用微信开发者工具打开 `miniapp/` 目录。

## 打开方式

1. 在 Windows 上拉取 GitHub 仓库：

```powershell
git clone https://github.com/chungjl/Latest-AI-updates.git
```

2. 微信开发者工具选择：

```text
导入项目 -> 选择 Latest-AI-updates\miniapp
```

3. 没有 AppID 时选择测试号或无 AppID。

## 开发接口

当前默认接口：

```text
https://claudeinfo.cn/api
```

配置位置：

```text
app.js
```

开发阶段如果 HTTPS 还没配置好，可以临时改成：

```text
http://8.163.68.172/api
```

同时在微信开发者工具里勾选：

```text
详情 -> 本地设置 -> 不校验合法域名、web-view、TLS 版本以及 HTTPS 证书
```

正式上线前需要在微信小程序后台配置 request 合法域名：

```text
https://claudeinfo.cn
```

## 页面

- 首页：资讯列表、搜索、分类、刷新进度
- 详情：摘要、关键信号、收藏、复制原文链接
- 趋势：24 小时热度榜
- 专题：追踪专题列表
- 频道订阅：来源启用/停用
- 我的：收藏、推送、导出、数据源入口
