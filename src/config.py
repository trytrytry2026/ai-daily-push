import os
from dotenv import load_dotenv

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
SITE_BASE_URL = os.getenv("SITE_BASE_URL", "")
BASE_PATH = os.getenv("BASE_PATH", "")

INDUSTRY_KEYWORDS = [
    "AI应用", "大模型", "智能体", "Agent", "算力",
    "AIGC", "多模态", "RAG", "具身智能", "AI芯片",
    "人工智能", "机器学习", "深度学习", "自然语言处理",
    "GPT", "LLM", "Transformer", "生成式AI",
]

COMPANY_KEYWORDS = [
    "华为", "英伟达", "NVIDIA", "阿里", "腾讯",
    "字节", "抖音", "钉钉", "支付宝", "百度",
    "小米", "OpenAI", "谷歌", "Google", "Grok",
    "xAI", "Meta", "微软", "Microsoft", "DeepSeek",
    "智谱", "月之暗面", "Kimi", "MiniMax", "零一万物",
    "商汤", "科大讯飞", "昆仑万维",
]

NEGATIVE_KEYWORDS = [
    "股票", "涨停", "跌停", "利好", "利空", "概念股",
    "龙头股", "牛股", "基金", "理财", "炒股",
    "个人观点", "本文仅代表",
]

PRIORITY_RSS_FEEDS = {
    "虎嗅": "https://www.huxiu.com/rss/0.xml",
    "钛媒体": "https://www.tmtpost.com/feed",
    "猎云网": "https://www.lieyunwang.com/feed",
}

SECONDARY_RSS_FEEDS = {
    "机器之心": "https://www.jiqizhixin.com/rss",
    "IT之家": "https://www.ithome.com/rss/",
}

PRIORITY_SOURCES = ["36氪", "虎嗅", "钛媒体", "猎云网"]

MAX_NEWS_COUNT = 10
MIN_APP_DEPTH_COUNT = 3   # 至少 3 条 AI 应用/深度分析类新闻
MAX_PAPER_COUNT = 10
MAX_TOTAL_CHARS = 3000
REQUEST_TIMEOUT = 15

AI_APP_KEYWORDS = [
    "AI应用", "落地", "应用场景", "数字员工", "AI+",
    "智能客服", "AI医疗", "AI教育", "AI金融", "AI制造",
    "降本增效", "提升效率", "转型", "赋能", "深水区",
    "商业化", "规模化", "案例", "实测", "实践",
]
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
