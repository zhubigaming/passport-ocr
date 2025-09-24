import os

# 获取当前文件所在目录的绝对路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# API认证配置
APP_KEY = 'your_app_key'
APP_SECRET = 'your_app_secret'

# 数据库配置
DB_CONFIG = {
    'host': 'localhost',
    'user': 'ocr',
    'password': 'ocr',
    'database': 'ocr',
    'port': 3306,
    'charset': 'utf8mb4',
    'collation': 'utf8mb4_unicode_ci',
    'use_pure': True
}

# FastAPI应用配置
APP_CONFIG = {
    'host': '0.0.0.0',
    'port': 8000,
    'debug': True,
    'app_key': APP_KEY,
    'app_secret': APP_SECRET,
    'upload_folder': os.path.join(BASE_DIR, 'uploads'),
    'allowed_extensions': {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'},
    'max_content_length': 16 * 1024 * 1024  # 16MB
}

# OCR服务配置
OCR_CONFIG = {
    'service_url': 'http://localhost:8080/ocr',
    'max_retries': 5,
    'timeout': 30
}

# 日志配置
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        }
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'fastapi.log'),
            'maxBytes': 10*1024*1024,
            'backupCount': 5,
            'formatter': 'default'
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    'loggers': {
        'ocr_server': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False
        }
    }
} 