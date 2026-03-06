"""集中管理所有魔法数字和硬编码常量。

本模块提供项目中使用的所有常量定义，按功能模块分组。
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# AI 客户端常量
# ---------------------------------------------------------------------------

# HTTP 配置
AI_HTTP_TIMEOUT_TOTAL: float = 120.0  # 总超时时间（秒）
AI_HTTP_TIMEOUT_CONNECT: float = 30.0  # 连接超时时间（秒）

# 重试配置
AI_MAX_RETRIES: int = 3  # 最大重试次数
AI_BASE_DELAY: float = 5.0  # 基础延迟时间（秒）

# AI 模型参数
AI_TEMPERATURE_DEFAULT: float = 0.3  # 默认温度
AI_TEMPERATURE_SEGMENTATION: float = 0.1  # 分段温度
AI_TEMPERATURE_PROOFREADING: float = 0.2  # 校对温度
AI_TEMPERATURE_LANGUAGE_DETECT: float = 0.0  # 语言检测温度
AI_MAX_TOKENS_DEFAULT: int = 4096  # 默认最大 token 数
AI_MAX_TOKENS_LANGUAGE_DETECT: int = 10  # 语言检测最大 token 数

# 分段参数
AI_SEGMENTATION_MAX_WORDS: int = 18  # 最大单词数
AI_SEGMENTATION_MIN_WORDS: int = 5  # 最小单词数
AI_SEGMENTATION_MAX_ATTEMPTS: int = 3  # 最大尝试次数

# 翻译批次参数
AI_TRANSLATION_BATCH_SIZE: int = 45  # 翻译批次大小
AI_TRANSLATION_MAX_WORDS: int = 18  # 翻译最大单词数
AI_TRANSLATION_MIN_WORDS: int = 5  # 翻译最小单词数
AI_TRANSLATION_MAX_ATTEMPTS: int = 3  # 翻译最大尝试次数

# 校对批次参数
AI_PROOFREADING_BATCH_SIZE: int = 20  # 校对批次大小
AI_PROOFREADING_CONTEXT_SIZE: int = 3  # 校对上下文大小

# 语言检测
AI_LANGUAGE_DETECT_SAMPLE_LENGTH: int = 2000  # 语言检测样本长度

# ---------------------------------------------------------------------------
# 字幕常量
# ---------------------------------------------------------------------------

# ASS 样式 - 分辨率
SUBTITLE_ASS_RESOLUTION_X: int = 1920  # PlayResX
SUBTITLE_ASS_RESOLUTION_Y: int = 1080  # PlayResY

# ASS 样式 - 字体大小
SUBTITLE_ASS_FONT_SIZE_PRIMARY: int = 58  # 主字幕字体大小
SUBTITLE_ASS_FONT_SIZE_SECONDARY: int = 38  # 次字幕字体大小

# ASS 样式 - 边距
SUBTITLE_ASS_MARGIN_LEFT: int = 30  # 左边距
SUBTITLE_ASS_MARGIN_RIGHT: int = 30  # 右边距
SUBTITLE_ASS_MARGIN_VERTICAL: int = 35  # 垂直边距

# ASS 样式 - 颜色（BGR 格式）
SUBTITLE_ASS_COLOR_PRIMARY: str = "&H00FFFFFF"  # 主字幕颜色（白色）
SUBTITLE_ASS_COLOR_SECONDARY: str = "&H00FFFFFF"  # 次字幕颜色（白色）
SUBTITLE_ASS_COLOR_OUTLINE: str = "&H000000FF"  # 轮廓颜色（黑色）
SUBTITLE_ASS_COLOR_BACK: str = "&H00000000"  # 背景颜色（黑色）
SUBTITLE_ASS_COLOR_SHADOW: str = "&H80000000"  # 阴影颜色（半透明黑色）

# ASS 样式 - 其他
SUBTITLE_ASS_OUTLINE_WIDTH: int = 3  # 轮廓宽度
SUBTITLE_ASS_SHADOW_DEPTH: int = 0  # 阴影深度

# 时间调整
SUBTITLE_TIME_GAP_MS: int = 10  # 字幕间隙（毫秒）
SUBTITLE_END_EXTENSION_MS: int = 2000  # 结束时间延长（毫秒）
SUBTITLE_MIN_DURATION_MS: int = 1000  # 最小持续时间（毫秒）

# 语言检测阈值
SUBTITLE_LANG_DETECT_THRESHOLD_LATIN: float = 0.7  # 拉丁字符阈值
SUBTITLE_LANG_DETECT_THRESHOLD_CJK: float = 0.3  # CJK 字符阈值
SUBTITLE_LANG_DETECT_THRESHOLD_JAPANESE: float = 0.1  # 日文字符阈值
SUBTITLE_LANG_DETECT_THRESHOLD_MIXED: float = 0.05  # 混合语言阈值

# ---------------------------------------------------------------------------
# 下载器常量
# ---------------------------------------------------------------------------

# ANSI 转义码模式
DOWNLOADER_ANSI_ESCAPE_PATTERN: str = r"\033\[[0-9;]*m"

# YouTube 视频 ID 长度
DOWNLOADER_YOUTUBE_VIDEO_ID_LENGTH: int = 11

# URL 模式（正则表达式）
DOWNLOADER_YOUTUBE_URL_PATTERNS: list[str] = [
    r"youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
    r"youtu\.be/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/embed/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/v/([a-zA-Z0-9_-]{11})",
    r"youtube\.com/shorts/([a-zA-Z0-9_-]{11})",
]

# ---------------------------------------------------------------------------
# FFmpeg 常量
# ---------------------------------------------------------------------------

# FFmpeg 超时
FFMPEG_FFPROBE_TIMEOUT_S: int = 30  # ffprobe 超时（秒）
FFMPEG_FFMPEG_TIMEOUT_S: int = 600  # ffmpeg 超时（秒，10 分钟）

# 错误输出截断
FFMPEG_ERROR_TRUNCATE_LENGTH: int = 500  # 错误输出截断长度
