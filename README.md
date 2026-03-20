# AI 日报 — 每日自动生成 AI 行业资讯 + 论文解读 + 语音播报

每天自动采集 AI 行业新闻和论文解读，经 LLM 智能摘要后生成精美网页日报，配有语音播报功能。

**在线访问：** https://trytrytry2026.github.io/ai-daily-push/

## 功能

- **AI 资讯**：采集 36氪/虎嗅/钛媒体/猎云网/机器之心/IT之家/百度资讯，每日 15 条精选
- **AI 论文解读**：四引擎采集（RSS + Bing + Google + 百度），两级过滤，每日最多 10 篇
- **语音播报**：Edge TTS 女声（晓晓），支持倍速播放
- **智能过滤**：关键词匹配、质量过滤、SimHash 去重、公司多样性控制
- **LLM 摘要**：DeepSeek API 生成一句话标题 + 精简描述
- **精美界面**：SVG 科技感 Header、渐变色模块标题、响应式卡片排版
- **往期归档**：自动保留最近 90 天日报
- **全自动运行**：GitHub Actions 每天 08:00（北京时间）自动执行

## 快速开始

```bash
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY
python main.py
```

## 技术栈

- Python 3.11+ / Jinja2 / DeepSeek API / Edge TTS
- GitHub Actions（定时任务）/ GitHub Pages（静态托管）
- RSS + Bing/Google/百度搜索（数据采集）

## 文档

- [项目文档](开发计划-企业微信AI资讯推送系统.md) — 完整项目说明、架构、配置、运维指南
- [操作手册](环境准备-操作手册.md) — 环境搭建和部署步骤
