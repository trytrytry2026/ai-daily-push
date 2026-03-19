# AI 日报 — 每日自动推送 AI 行业资讯

每天自动采集 AI 行业新闻，生成精美网页日报，部署到 Vercel 供浏览。

## 功能

- 多源采集：机器之心、IT之家、36氪、百度资讯等
- 智能过滤：关键词匹配、质量过滤、SimHash 去重、公司多样性控制
- LLM 摘要：DeepSeek API 自动生成一句话标题 + 精简描述
- 精美网页：响应式设计，手机电脑自适应
- 往期归档：自动保留最近 90 天日报
- 全自动运行：GitHub Actions 每天 08:00（北京时间）自动执行

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 DEEPSEEK_API_KEY

# 手动运行一次
python main.py
```

## 部署

详见 [环境准备-操作手册.md](环境准备-操作手册.md)
