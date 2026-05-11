# daily-news

一个面向个人使用场景的自动化工具：追踪 Anthropic 新文章，生成中文摘要与中文音频，封装为简单视频，并自动上传到 Bilibili。

## 当前 MVP

- 发现 `https://www.anthropic.com/news` 新文章
- 抓取正文并提取元数据
- 通过可插拔摘要 provider 生成中文摘要和播报文案
- 通过 Edge TTS 生成中文音频
- 用固定背景图 + 音频合成简单 MP4
- 通过 `biliup` CLI 自动投稿到 Bilibili
- 用 SQLite 保存状态，避免重复处理和支持失败重试
- 提供本地 Web 管理界面，查看原文链接、AI 总结、发布状态和视频链接

## 技术选择

- **Python 3.12**
- **SQLite**：状态存储与去重
- **Qwen / DashScope compatible-mode API**：默认摘要模型
- **edge-tts**：中文配音
- **ffmpeg（通过 imageio-ffmpeg 提供）**：视频封装
- **Playwright + Chromium**：网页渲染、HTML/PDF/截图采集
- **biliup**：Bilibili 登录与投稿
- **FastAPI + Jinja2 + Uvicorn**：本地 Web 管理后台

## 安装

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
```

默认会优先复用系统已安装的 **Microsoft Edge / Google Chrome**。如果本机没有可用的 Chromium 浏览器，再额外执行：

```powershell
.\.venv\Scripts\python -m playwright install chromium
```

### Ubuntu 云端一键安装

如果你在 Ubuntu 云服务器上部署，并且拥有管理员权限，直接运行：

```bash
chmod +x scripts/bootstrap-ubuntu.sh
./scripts/bootstrap-ubuntu.sh
```

这个脚本会自动完成：

- 安装 Python / venv / pip
- 安装常用中文字体
- 安装项目 Python 依赖
- 安装 Playwright Chromium 及其 Linux 系统依赖
- 创建运行目录

完成后再执行：

```bash
cp config.example.json config.json
export DASHSCOPE_API_KEY="your-api-key"
.venv/bin/daily-news run-once --config config.json --skip-publish
```

如果你想在 Ubuntu 上设置定时任务，可以用 `crontab`，例如每小时执行一次：

```bash
crontab -e
```

加入这一行：

```cron
0 * * * * cd /path/to/daily-news && /bin/bash -lc 'export DASHSCOPE_API_KEY="your-api-key"; .venv/bin/daily-news run-once --config config.json >> logs/cron.log 2>&1'
```

如果你希望先只验证不发布，可以把命令改成：

```cron
0 * * * * cd /path/to/daily-news && /bin/bash -lc 'export DASHSCOPE_API_KEY="your-api-key"; .venv/bin/daily-news run-once --config config.json --skip-publish >> logs/cron.log 2>&1'
```

## 配置

复制 `config.example.json` 为你自己的配置文件，例如 `config.json`。

### 配置文件初始化

Windows:

```powershell
Copy-Item .\config.example.json .\config.json
```

Ubuntu / Linux:

```bash
cp config.example.json config.json
```

然后按你的实际需要修改 `config.json`，例如：

- `summarizer.provider`
- `summarizer.model`
- `publisher.enabled`
- `publisher.cookies_file`
- `max_articles_per_run`

`config.json` 已加入 `.gitignore`，不会默认进入仓库。

### 1. 配置摘要模型

默认提供两种摘要模式：

- `openai_compatible`：默认走 **阿里云百炼千问兼容接口**
- `mock`：本地烟雾测试，不调用 AI

如果你使用 `openai_compatible`，需要设置环境变量：

```powershell
$env:DASHSCOPE_API_KEY = "your-api-key"
```

默认示例配置已经指向：

- `base_url = https://dashscope.aliyuncs.com/compatible-mode/v1`
- `model = qwen-plus`

如果你想切换到别的兼容模型，也可以直接修改配置文件里的 `base_url`、`model` 和 `api_key_env`。

### 1.0 站点级摘要提示词

摘要提示词已经抽成了独立的站点配置层，当前会根据 `source_name` 自动选择不同提示词。

- `anthropic`：偏重技术细节、benchmark、工程变化与能力对比
- 其他网站：默认走通用科技摘要提示词

其中 Anthropic 当前的提示词目标是：

- **深入技术细节**
- **summary 约 1800 到 2200 个中文字符**
- 更强调模型能力、评测、工程机制、限制和实际影响

后续如果接入别的网站，只需要继续新增对应的 prompt profile，不需要重写摘要器本身。

### 1.1 网页读取方式

当前 Anthropic 页面处理已改为 **Playwright 渲染后抓取**，并默认保留：

- 渲染后的 HTML
- 页面 PDF
- 整页截图

这些产物会落到 `workspace_dir\\captures\\` 下，后续可以作为多模态分析或别的网站适配基础。

### 2. 登录 Bilibili

首次使用前先让 `biliup` 生成登录态：

```powershell
.\.venv\Scripts\biliup login
```

默认会生成 `cookies.json`。项目运行时会读取配置文件中的 `publisher.cookies_file`。

## 运行

### 仅做本地流水线验证，不上传

如果你不想调用真实千问接口，先把配置里的 `summarizer.provider` 临时改成 `mock`，再执行：

```powershell
.\.venv\Scripts\daily-news run-once --config config.example.json --skip-publish
```

### 执行完整自动上传流程

把配置里的：

- `summarizer.provider` 改成 `openai_compatible`
- `summarizer.model` 保持 `qwen-plus` 或改成你想用的千问模型
- `publisher.enabled` 设为 `true`
- `publisher.cookies_file` 指向你已登录的 `cookies.json`

然后执行：

```powershell
.\.venv\Scripts\daily-news run-once --config config.json
```

## 常用命令

```powershell
.\.venv\Scripts\daily-news discover --config config.json
.\.venv\Scripts\daily-news run-once --config config.json
.\.venv\Scripts\daily-news list --config config.json
.\.venv\Scripts\daily-news serve --config config.json --host 127.0.0.1 --port 8000
```

## Web 管理界面

启动后台：

```powershell
.\.venv\Scripts\daily-news serve --config config.json --host 127.0.0.1 --port 8000
```

然后打开：

```text
http://127.0.0.1:8000/articles
```

当前界面提供：

- 文章列表页：原文链接、摘要片段、发布状态、视频链接
- 文章详情页：完整摘要、要点、播报稿、错误信息、封面和视频入口
- 若已发布成功且拿到 BV 号，会展示 Bilibili 视频链接
- 若尚未发布，但已生成本地 MP4，会展示本地视频访问链接

## 目录结构

```text
src/daily_news/
  cli.py
  config.py
  models.py
  pipeline.py
  publishers/
  sources/
  browser/
  storage/
  summarizers/
  tts/
  video/
  web/
```

## 调度建议

在 Windows 上可用“任务计划程序”定时执行：

```powershell
.\.venv\Scripts\daily-news run-once --config C:\path\to\config.json
```

## 注意事项

- Anthropic 页面结构变化时，可能需要微调抓取逻辑
- Bilibili 投稿依赖登录态、平台风控和 `biliup` 兼容性
- 真正自动发布前，建议先用 `--skip-publish` 跑通整条链路
