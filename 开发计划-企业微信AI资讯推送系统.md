# AI 日报系统 — 项目文档

## 一、项目概述

一套**全自动、零操作**的 AI 资讯日报系统。每天自动采集 AI 行业新闻与论文解读，经 LLM 智能摘要后生成精美网页日报，并配有语音播报功能。老板打开网址即可阅读或收听，**无需安装任何软件、无需 VPN**。

| 项目 | 信息 |
|------|------|
| **GitHub 仓库** | `https://github.com/trytrytry2026/ai-daily-push` |
| **日报网址** | `https://trytrytry2026.github.io/ai-daily-push/` |
| **自动运行时间** | 每天北京时间 08:00 |
| **开发语言** | Python 3.11+ |
| **运行平台** | GitHub Actions（免费） |
| **网页托管** | GitHub Pages（免费） |
| **LLM 服务** | DeepSeek API |
| **语音合成** | Edge TTS（微软晓晓，女声） |

---

## 二、功能清单

### 已实现

- **AI 资讯模块**（15 条/天）
  - 优先采集：36氪、虎嗅、钛媒体、猎云网
  - 补充采集：机器之心、IT之家、百度资讯
  - 智能过滤：关键词匹配、质量过滤、URL 日期校验、SimHash 去重、公司多样性控制
  - LLM 生成一句话标题 + 精简描述，信息密度高、不标题党
  - 热度排序，优先源加权
  - 至少 5 条 AI 应用深度类资讯

- **AI 论文解读模块**（最多 10 篇/天，近 1 周内）
  - 来源：机器之心 / 量子位 RSS + Bing 搜索 + Google 搜索 + 百度搜索（四引擎）
  - **两级过滤策略**：严格模式（要求"论文/paper/arxiv"等强信号词）→ 如 <5 篇自动降级到宽松模式（弱信号词 + 可信来源 AI 文章）
  - 排除纯产品新闻、股票、医疗等无关内容
  - LLM 精炼摘要，点击可跳转原文（中文网站）

- **语音播报**
  - 使用 Edge TTS `zh-CN-XiaoxiaoNeural` 女声
  - 自动生成当日全部内容的 MP3 音频
  - 网页内嵌播放器，支持播放/暂停、进度条、倍速切换（1x/1.25x/1.5x/2x）

- **网页日报**
  - 响应式设计，手机/电脑自适应
  - 紧凑型顶部 Header，内嵌 SVG 科技感图形（电路节点、网格线、光晕）
  - 分模块展示：「AI 资讯」蓝色渐变标题卡片、「AI 论文解读」紫色渐变标题卡片
  - 新闻卡片支持排名角标、来源标签、点击跳转原文
  - 往期归档，自动保留最近 90 天日报

- **全自动运行**
  - GitHub Actions 每天 UTC 00:00（北京时间 08:00）自动触发
  - 也支持手动触发（GitHub Actions → Run workflow）
  - 生成的页面自动提交到仓库 → GitHub Pages 自动部署

### 未实现（可扩展）

- 钉钉群机器人推送（代码未接入，可后续增加）
- 搜索历史新闻
- 个性化关键词订阅
- 热点实时预警
- AI 周报汇总

---

## 三、技术架构

```
START (每天 08:00 自动触发)
  │
  ├─ 1. 新闻采集（并行多源）
  │     ├─ 36氪 API
  │     ├─ 虎嗅 / 钛媒体 / 猎云网 RSS（优先源）
  │     ├─ 百度资讯搜索
  │     └─ 机器之心 / IT之家 RSS（补充源）
  │
  ├─ 2. 论文采集（四引擎并行）
  │     ├─ 机器之心 / 量子位 RSS
  │     ├─ Bing 搜索（海外服务器更稳定）
  │     ├─ Google 搜索（兜底）
  │     └─ 百度搜索（国内搜索引擎）
  │
  ├─ 3. 新闻过滤 Pipeline
  │     ├─ URL 日期校验（丢弃明显过时文章）
  │     ├─ 时间过滤（严格 24 小时内）
  │     ├─ 关键词匹配（行业词 + 公司词）
  │     ├─ 质量过滤（排除股评/自媒体/标题党）
  │     ├─ SimHash 文本去重
  │     ├─ 公司多样性控制（同一公司最多 2 条）
  │     └─ 热度排序 + 优先源加权 → 取 Top 15
  │
  ├─ 4. 论文两级过滤
  │     ├─ 负面词排除（股票/体育/医疗等）
  │     ├─ 严格模式：要求标题含"论文/paper/arxiv/论文解读"
  │     ├─ 宽松模式（兜底）：弱信号词（研究发现/实验表明/开源模型等）
  │     │   或来自可信来源（机器之心/量子位）的 AI 相关文章
  │     └─ 相关度评分排序 → 取 Top 10
  │
  ├─ 5. LLM 摘要（DeepSeek API）
  │     ├─ 新闻：生成一句话标题 + 精简描述
  │     └─ 论文：精炼中文摘要
  │
  ├─ 6. 语音合成（Edge TTS）
  │     └─ 生成完整播报 MP3
  │
  ├─ 7. 网页生成（Jinja2 模板）
  │     ├─ 日报页面（含音频播放器、SVG 科技感 Header）
  │     └─ 首页归档更新
  │
  └─ 8. 自动部署
        ├─ Git commit & push 到 GitHub
        └─ GitHub Pages 自动部署上线
END
```

---

## 四、项目目录结构

```
ai-daily-push/
├── .github/
│   └── workflows/
│       └── daily-push.yml              # GitHub Actions 定时任务 + GitHub Pages 部署
├── src/
│   ├── collector/                       # 数据采集模块
│   │   ├── base.py                     # 采集器抽象基类
│   │   ├── rss_collector.py            # RSS 通用采集器（虎嗅/钛媒体/猎云网/机器之心/IT之家）
│   │   ├── web_collector.py            # 网页采集器（36氪 API + 百度资讯搜索）
│   │   └── cn_paper_collector.py       # 论文采集器（RSS + Bing + Google + 百度，四引擎）
│   ├── filter/                          # 过滤 & 去重模块
│   │   └── pipeline.py                 # 完整过滤流水线
│   ├── summarizer/                      # LLM 摘要模块
│   │   ├── deepseek.py                 # 新闻摘要（DeepSeek API）
│   │   └── paper_summarizer.py         # 论文摘要精炼
│   ├── ranker/                          # 排序模块
│   │   └── hot_ranker.py              # 热度评分 + 优先源加权
│   ├── generator/                       # 网页生成模块
│   │   └── page_builder.py            # Jinja2 渲染 HTML + 归档管理
│   ├── audio/                           # 语音合成模块
│   │   └── tts_generator.py           # Edge TTS 生成 MP3
│   ├── config.py                        # 全局配置（关键词/数据源/阈值/BASE_PATH）
│   └── models.py                        # 数据模型（RawArticle / ProcessedArticle）
├── templates/
│   ├── daily.html                       # 日报页面 Jinja2 模板（SVG Header + 渐变模块标题）
│   └── index.html                       # 首页归档模板
├── site/                                # 生成的静态站点（自动部署到 GitHub Pages）
│   ├── index.html                      # 首页
│   ├── archive.json                    # 归档索引
│   ├── audio/                          # 语音 MP3 文件
│   │   └── 2026-03-20.mp3
│   └── 2026/03/20.html                # 日报页面
├── main.py                              # 主入口
├── requirements.txt                     # Python 依赖
├── .env.example                         # 环境变量模板
├── .gitignore
└── README.md
```

---

## 五、关键配置说明

### 5.1 关键词（`src/config.py`）

```python
# 行业关键词 — 新闻必须命中至少一个
INDUSTRY_KEYWORDS = ["AI应用", "大模型", "智能体", "Agent", "算力", "AIGC", ...]

# 公司关键词 — 命中则加分
COMPANY_KEYWORDS = ["华为", "英伟达", "阿里", "腾讯", "字节", "百度", "小米", "OpenAI", ...]

# 优先新闻源 — 排序时额外加权
PRIORITY_SOURCES = ["36氪", "虎嗅", "钛媒体", "猎云网"]
```

如需新增关注的公司或领域，直接在 `config.py` 中修改对应列表即可。

### 5.2 数量控制

| 参数 | 值 | 位置 |
|------|-----|------|
| 新闻条数上限 | 15 | `config.py → MAX_NEWS_COUNT` |
| 论文条数上限 | 10 | `config.py → MAX_PAPER_COUNT` |
| 总字符上限 | 3000 | `main.py → _truncate_to_limit()` |
| 新闻时间窗口 | 24 小时 | `main.py → since = now - timedelta(hours=24)` |
| 论文时间窗口 | 7 天 | `main.py → since_papers = now - timedelta(days=7)` |

### 5.3 数据源

| 类型 | 来源 | 采集方式 | 优先级 |
|------|------|----------|--------|
| 新闻 | 36氪 | API | 优先 |
| 新闻 | 虎嗅 | RSS | 优先 |
| 新闻 | 钛媒体 | RSS | 优先 |
| 新闻 | 猎云网 | RSS | 优先 |
| 新闻 | 百度资讯 | 搜索抓取 | 补充 |
| 新闻 | 机器之心 | RSS | 补充 |
| 新闻 | IT之家 | RSS | 补充 |
| 论文 | 机器之心 | RSS | 主要 |
| 论文 | 量子位 | RSS | 主要 |
| 论文 | Bing | 搜索抓取 | 补充（海外稳定） |
| 论文 | Google | 搜索抓取 | 补充（兜底） |
| 论文 | 百度搜索 | 搜索抓取 | 补充 |

> 新闻数据源均为国内可直接访问，无需 VPN。  
> 论文采集在 GitHub Actions（海外服务器）上运行，故使用 Bing/Google 确保稳定性，最终展示链接为中文网站。

---

## 六、环境变量

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | 是 | DeepSeek API Key，用于 LLM 摘要生成 |
| `BASE_PATH` | 否 | GitHub Pages 项目路径前缀（如 `/ai-daily-push`） |

在 GitHub 仓库的 **Settings → Secrets and variables → Actions** 中配置 `DEEPSEEK_API_KEY`。  
`BASE_PATH` 已在 GitHub Actions workflow 文件中直接设置。

---

## 七、日常运维

### 7.1 正常运行

系统完全自动化，正常情况下无需任何操作：

| 角色 | 日常操作 | 频率 |
|------|----------|------|
| **老板** | 打开收藏的网址看日报 | 想看就看 |
| **你** | 无需操作 | 全自动 |

### 7.2 异常排查

如果某天日报没更新：

1. 打开 GitHub 仓库 → **Actions** 标签页
2. 查看最近一次运行的状态
   - ✅ 绿色 = 成功
   - ❌ 红色 = 失败，点击查看日志定位问题
3. 常见原因及处理：

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| 新闻为空 | 数据源网站改版或临时故障 | 等待恢复，或调整采集器代码 |
| 论文为空 | 所有四个引擎均无结果（极少见） | 检查 Actions 日志，放宽过滤条件 |
| LLM 摘要失败 | DeepSeek API 余额不足或服务异常 | 充值或等待恢复，系统会降级为原始标题 |
| 语音生成失败 | Edge TTS 服务临时不可用 | 页面正常生成，仅无语音，等待恢复 |
| Git push 失败 | 并发推送冲突 | 工作流已内置 3 次重试机制 |
| GitHub Pages 部署失败 | 服务临时异常 | 重新触发 Actions 即可 |

### 7.3 手动触发

如需临时重新生成日报：

1. 打开 GitHub 仓库 → **Actions** → 左侧 **AI Daily Report**
2. 点击 **Run workflow** → **Run workflow**
3. 等待 2-3 分钟，刷新日报网址查看结果

---

## 八、如何更新系统

### 8.1 修改关键词/数量等配置

1. 编辑 `src/config.py` 中的对应变量
2. 提交并推送到 GitHub：
   ```powershell
   cd "C:\Users\Laptop\Desktop\推送新闻"
   git add .
   git commit -m "update: 调整关键词配置"
   git pull --rebase origin main
   git push
   ```
3. 下次自动运行时即生效，或手动触发立即生效

### 8.2 修改页面样式

编辑 `templates/daily.html` 中的 HTML/CSS，同样提交推送后生效。

### 8.3 新增数据源

1. 在 `src/collector/` 下新建采集器类，继承 `BaseCollector`
2. 在 `main.py` 的 `_collect_and_process_news()` 中添加到采集器列表
3. 提交推送

### 8.4 调整自动运行时间

编辑 `.github/workflows/daily-push.yml` 中的 cron 表达式：

```yaml
schedule:
  - cron: '0 0 * * *'  # UTC 00:00 = 北京时间 08:00
```

cron 格式：`分 时 日 月 星期`（UTC 时间），北京时间 = UTC + 8。

示例：
- 北京时间 07:00 → `cron: '0 23 * * *'`（前一天 UTC 23:00）
- 北京时间 09:00 → `cron: '0 1 * * *'`

---

## 九、每月成本

| 项目 | 费用 | 说明 |
|------|------|------|
| GitHub Actions | ¥0 | 免费额度 2000 分钟/月，本项目每天约 3 分钟 |
| GitHub Pages | ¥0 | 免费静态站点托管 |
| Edge TTS 语音 | ¥0 | 微软免费服务 |
| DeepSeek API | **约 ¥10-30** | 每天约 25 条摘要，费用极低 |
| **月总成本** | **约 ¥10-30** | 唯一的持续支出就是 LLM API |

> DeepSeek API 极其便宜，10 块钱可以用很久。如余额不足，登录 https://platform.deepseek.com/ 充值即可。

---

## 十、注意事项

1. **所有新闻链接必须国内可访问**：系统已排除所有海外源，仅采集国内网站。如发现某条链接无法打开，属于原网站个别文章问题，不影响整体。

2. **论文模块展示的是"论文解读"**：不是直接展示英文论文，而是采集国内科技媒体（机器之心、量子位）对 AI 论文的中文解读文章。采集使用四引擎（RSS + Bing + Google + 百度），并通过两级过滤策略确保稳定性。

3. **语音播报依赖网络**：Edge TTS 需要 GitHub Actions 运行环境能访问微软服务。如果语音偶尔生成失败，不影响页面正常展示。

4. **GitHub Actions 有免费额度**：每月 2000 分钟，本项目每天用约 3 分钟，一个月不到 100 分钟，远远够用。

5. **GitHub Pages 域名**：使用 `trytrytry2026.github.io/ai-daily-push/`。如需自定义域名可在 GitHub 仓库 Settings → Pages 中设置（需额外购买域名，约 ¥50/年）。

6. **数据源可能改版**：RSS 源和网站 API 可能随时间变化。如某个源长期无法采集，需要更新对应的采集器代码。论文模块四引擎冗余设计使得单个源故障不影响整体。

7. **DeepSeek API Key 安全**：API Key 存储在 GitHub Secrets 中，不会出现在代码里。不要将 `.env` 文件提交到仓库。

---

## 十一、Python 依赖

```
feedparser>=6.0.0      # RSS 解析
requests>=2.31.0       # HTTP 请求
jinja2>=3.1.0          # HTML 模板引擎
openai>=1.0.0          # DeepSeek API 客户端（兼容 OpenAI SDK）
python-dotenv>=1.0.0   # 环境变量加载
edge-tts>=6.1.0        # 微软 Edge TTS 语音合成
```

---

## 十二、风险 & 应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 数据源网站改版 | 部分采集失败 | 7 个新闻源冗余设计，单源故障不影响整体 |
| RSS 链接失效 | 部分源不可用 | 有百度搜索作为兜底采集 |
| 论文采集为空 | 无论文展示 | 四引擎冗余（RSS/Bing/Google/百度）+ 两级过滤降级 |
| DeepSeek API 不可用 | 无法生成摘要 | 系统会捕获异常，页面仍可生成（内容较粗） |
| Edge TTS 不可用 | 无语音播报 | 页面正常展示，仅缺少音频 |
| GitHub Pages 访问波动 | 国内偶尔较慢 | 可备选切换到阿里云 OSS（约 ¥1/月） |
| GitHub Actions 超时 | 当天日报未生成 | 内置超时控制 + 重试；可手动触发重新生成 |
| 新闻内容质量波动 | 个别低质内容 | 多层过滤 + LLM 质量把关，持续优化过滤规则 |

---

## 十三、更新记录

| 日期 | 变更 |
|------|------|
| 2026-03-19 | 项目初始化，Vercel 部署 |
| 2026-03-19 | 新增论文解读模块、语音播报功能 |
| 2026-03-20 | 从 Vercel 迁移到 GitHub Pages（解决国内访问问题） |
| 2026-03-20 | 论文采集新增 Bing + Google 搜索引擎，两级过滤策略 |
| 2026-03-20 | 页面 Header 改为 SVG 科技感设计，模块标题改为渐变色卡片 |
