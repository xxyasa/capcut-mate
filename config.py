# 项目常量定义
import os
import sys


# 应用资源目录：开发时是项目根目录，PyInstaller 打包后是 _internal 资源目录。
APP_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

# 项目数据目录：打包后必须指向用户可写目录，避免 Program Files 权限问题。
PROJECT_ROOT = os.getenv("CAPCUT_MATE_DATA_DIR", APP_ROOT)

# 保存剪映草稿的目录
DRAFT_DIR = os.path.join(PROJECT_ROOT, "output", "draft")

# 日志目录
LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

# 临时文件目录
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")

# 视频生成任务完成结果（SQLite 持久化）
VIDEO_GEN_TASK_DB_PATH = os.path.join(PROJECT_ROOT, "db", "video_gen_tasks.sqlite3")

# 视频生成任务：生成视频在 COS 上的可访问保留天数（预签名下载 URL 有效期，环境变量覆盖）
VIDEO_GEN_RETENTION_DAYS = max(1, int(os.getenv("VIDEO_GEN_RETENTION_DAYS", "7")))

# 剪映草稿的下载路径
DRAFT_URL = os.getenv("DRAFT_URL", "https://capcut-mate.jcaigc.cn/openapi/capcut-mate/v1/get_draft")

# 将容器内的文件路径转成一个下载路径，执行替换操作，即将/app/ -> https://capcut-mate.jcaigc.cn/
DOWNLOAD_URL = os.getenv("DOWNLOAD_URL", "https://capcut-mate.jcaigc.cn/")

# 草稿提示URL
TIP_URL = os.getenv("TIP_URL", "https://docs.jcaigc.cn/")

# 贴纸配置文件路径
STICKER_CONFIG_PATH = os.path.join(APP_ROOT, "config", "sticker.json")

# 花字配置文件路径
HUAZI_CONFIG_PATH = os.path.join(APP_ROOT, "config", "huazi.json")

# 模板目录路径
TEMPLATE_DIR = os.path.join(APP_ROOT, "template")

# 剪映草稿保存路径（下载剪映草稿保存位置）-- 云渲染必需配置
#DRAFT_SAVE_PATH = "C:/Users/Administrator/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"
DRAFT_SAVE_PATH = "C:/Users/1/AppData/Local/JianyingPro/User Data/Projects/com.lveditor.draft"

# 腾讯云对象存储配置（优先）
COS_SECRET_ID = os.getenv("COS_SECRET_ID", "")
COS_SECRET_KEY = os.getenv("COS_SECRET_KEY", "")
COS_BUCKET_NAME = os.getenv("COS_BUCKET_NAME", "")
COS_REGION = os.getenv("COS_REGION", "")

# 阿里云对象存储配置（COS 未配置时作为兜底）
OSS_ACCESS_KEY_ID = os.getenv("OSS_ACCESS_KEY_ID", "")
OSS_ACCESS_KEY_SECRET = os.getenv("OSS_ACCESS_KEY_SECRET", "")
OSS_BUCKET_NAME = os.getenv("OSS_BUCKET_NAME", "")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "")

# APIKEY启用配置-默认启用 -- 云渲染必需配置（环境变量 true / false，大小写不敏感）
ENABLE_APIKEY = os.getenv("ENABLE_APIKEY", "true").strip().lower() == "true"

# 文件下载大小限制（字节），默认200MB
DOWNLOAD_FILE_SIZE_LIMIT = int(os.getenv("DOWNLOAD_FILE_SIZE_LIMIT", str(200 * 1024 * 1024)))

# 智能包装远程视频下载快失败配置；桌面端推荐选择本地视频，远程 OSS 网络异常时不要让用户长时间空等。
SMART_PACKAGING_VIDEO_DOWNLOAD_TIMEOUT = int(os.getenv("SMART_PACKAGING_VIDEO_DOWNLOAD_TIMEOUT", "20"))
SMART_PACKAGING_VIDEO_DOWNLOAD_RETRY = int(os.getenv("SMART_PACKAGING_VIDEO_DOWNLOAD_RETRY", "0"))
