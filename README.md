# daily-news

一个面向个人使用场景的自动化工具：追踪 Anthropic 新文章，生成中文翻译讲解与中文音频，封装为简单视频，并可自动上传到 Bilibili。

## 项目介绍

- 发现 Anthropic 的 `news` / `research` 新文章
- 抓取正文并生成中文翻译讲解
- 生成中文音频、视频封面和 MP4 视频
- 提供本地 Web 管理界面查看文章、讲解文本和视频状态

## 启动相关

### Ubuntu 快速开始

```bash
chmod +x scripts/bootstrap-ubuntu.sh
./scripts/bootstrap-ubuntu.sh
```

### 初始化配置

```bash
cp config.example.json config.json
export DASHSCOPE_API_KEY="your-api-key"
```

如果本机没有可用的 Chromium 浏览器，再执行：

```bash
./.venv/bin/python -m playwright install chromium
```

### 登录 Bilibili

首次使用前先生成登录态：

```bash
./.venv/bin/biliup login
```

### 常用命令

仅测试，不上传：

```bash
./.venv/bin/daily-news run-once --config config.json --skip-publish
```

执行完整流程：

```bash
./.venv/bin/daily-news run-once --config config.json
```

只发现新文章：

```bash
./.venv/bin/daily-news discover --config config.json
```

启动本地后台：

```bash
./.venv/bin/daily-news serve --config config.json --host 127.0.0.1 --port 8000
```

打开：

```text
http://127.0.0.1:8000/articles
```

### 默认保存位置

- 数据库：`data\daily_news.db`
- 视频：`data\video\`
- 讲解文本：`data\summary\`

## 注意事项

- 真正自动发布前，建议先用 `--skip-publish` 跑通整条链路
- Bilibili 投稿依赖登录态、平台风控和 `biliup` 兼容性
- Anthropic 页面结构变化时，可能需要调整抓取逻辑
