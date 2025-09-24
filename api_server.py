from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel
from typing import Optional, List
import mysql.connector
from datetime import datetime, date, timedelta
import os
import logging
from logging.handlers import RotatingFileHandler
from config import DB_CONFIG, APP_CONFIG
import base64
import shutil
from pathlib import Path
import json
from functools import wraps
from werkzeug.utils import secure_filename
import requests
import uuid
import argparse
import ssl
from PIL import Image
import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import io
import threading
import queue
import time
import traceback  # 添加在文件顶部的其他导入语句旁边
import re  # 添加正则表达式模块
from mysql.connector import pooling
from contextlib import asynccontextmanager

# 配置日志
logger = logging.getLogger('ocr_server.fastapi')
logger.setLevel(logging.INFO)

# 全局变量和配置
MAX_UPLOAD_QUEUE = 30  # 最大上传队列数量
IO_THREAD_POOL_SIZE = 10  # IO线程池大小
UPLOAD_THREAD_POOL_SIZE = 5  # 专门用于文件上传的线程池

# 创建全局线程池
thread_pool = ThreadPoolExecutor(max_workers=IO_THREAD_POOL_SIZE)
upload_thread_pool = ThreadPoolExecutor(max_workers=UPLOAD_THREAD_POOL_SIZE)

# 全局队列
ocr_queue = queue.Queue(maxsize=MAX_UPLOAD_QUEUE)  # OCR处理队列
upload_queue = queue.Queue(maxsize=MAX_UPLOAD_QUEUE)  # 文件上传队列
db_write_queue = queue.Queue()  # OCR结果写入队列

# 全局状态管理
processing_status = {}  # 处理状态字典
processing_lock = threading.Lock()  # 状态字典的线程锁

# 获取项目根目录
base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(base_dir, 'logs')

# 确保日志目录存在
if not os.path.exists(log_dir):
    os.makedirs(log_dir, exist_ok=True)

# 配置文件处理器
file_handler = RotatingFileHandler(
    os.path.join(log_dir, 'fastapi.log'),
    maxBytes=10*1024*1024,
    backupCount=5
)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# 配置控制台输出
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    生命周期事件管理器
    """
    # 启动事件
    try:
        # 打印软件设置
        logger.info("\n" + "="*50)
        logger.info("OCR服务器启动 - 系统配置")
        logger.info("="*50)
        
        # 数据库配置
        logger.info("\n[数据库配置]")
        logger.info(f"数据库地址: {DB_CONFIG['host']}")
        logger.info(f"数据库名称: {DB_CONFIG['database']}")
        logger.info(f"写连接池大小: {DB_WRITE_POOL_CONFIG['pool_size']}")
        logger.info(f"读连接池大小: {DB_READ_POOL_CONFIG['pool_size']}")
        logger.info(f"写连接超时: {DB_WRITE_POOL_CONFIG['connect_timeout']}秒")
        logger.info(f"读连接超时: {DB_READ_POOL_CONFIG['connect_timeout']}秒")
        
        # 线程池和队列配置
        logger.info("\n[线程池和队列配置]")
        logger.info(f"IO线程池大小: {IO_THREAD_POOL_SIZE}")
        logger.info(f"最大上传队列数量: {MAX_UPLOAD_QUEUE}")
        
        # OCR服务配置
        logger.info("\n[OCR服务配置]")
        logger.info(f"OCR服务地址: {OCR_SERVICE_URL}")
        
        # 目录配置
        logger.info("\n[目录配置]")
        logger.info(f"上传目录: {UPLOAD_DIR}")
        logger.info(f"OCR信息目录: {OCR_INFO_DIR}")
        logger.info(f"日志目录: {log_dir}")
        
        # 创建必要的目录
        logger.info("\n[创建目录]")
        UPLOAD_DIR.mkdir(exist_ok=True)
        logger.info(f"创建上传目录: {UPLOAD_DIR}")
        (UPLOAD_DIR / "thumbnails").mkdir(exist_ok=True)
        logger.info(f"创建缩略图目录: {UPLOAD_DIR / 'thumbnails'}")
        OCR_INFO_DIR.mkdir(exist_ok=True)
        logger.info(f"创建OCR信息目录: {OCR_INFO_DIR}")
        
        # 启动处理线程
        logger.info("\n[启动处理线程]")
        # 启动OCR处理线程
        ocr_thread = threading.Thread(target=process_ocr_queue, daemon=True)
        ocr_thread.start()
        logger.info("OCR处理线程已启动")
        
        # 启动OCR结果写入线程
        write_thread = threading.Thread(target=ocr_result_writer, daemon=True)
        write_thread.start()
        logger.info("OCR结果写入线程已启动")
        
        # 启动线程池监控
        monitor_thread = threading.Thread(target=monitor_thread_pools, daemon=True)
        monitor_thread.start()
        logger.info("线程池监控已启动")
        
        logger.info("\n" + "="*50)
        logger.info("系统初始化完成，服务已启动")
        logger.info("="*50 + "\n")
        
        yield  # 服务运行中
        
        # 关闭事件
        logger.info("正在关闭服务...")
        
        # 关闭线程池
        thread_pool.shutdown(wait=True)
        logger.info("线程池已关闭")
        
        logger.info("服务已停止")
        
    except Exception as e:
        logger.error(f"服务生命周期事件处理错误: {str(e)}")
        raise

# 使用生命周期管理器创建FastAPI应用
app = FastAPI(
    title="OCR数据管理系统",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置静态文件和模板
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/ocr_info", StaticFiles(directory="ocr_info"), name="ocr_info")
templates = Jinja2Templates(directory="templates")

# 确保上传目录存在
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
OCR_INFO_DIR = Path("ocr_info")
OCR_INFO_DIR.mkdir(exist_ok=True)

# OCR服务配置
OCR_SERVICE_URL = os.getenv('OCR_SERVICE_URL', 'http://localhost:8080/ocr')

# 配置OCR日志
OCR_LOG_DIR = Path("logs/ocr")
OCR_LOG_DIR.mkdir(parents=True, exist_ok=True)

# 创建读写分离的数据库连接池配置
DB_WRITE_POOL_CONFIG = {
    **DB_CONFIG,
    'pool_name': 'write_pool',
    'pool_size': 20,  # 写连接池大小
    'pool_reset_session': True,
    'autocommit': True,
    'connect_timeout': 20,
    'time_zone': '+00:00'
}

DB_READ_POOL_CONFIG = {
    **DB_CONFIG,
    'pool_name': 'read_pool',
    'pool_size': 12,  # 读连接池大小
    'pool_reset_session': True,
    'autocommit': True,
    'connect_timeout': 10,
    'time_zone': '+00:00'
}

# 配置数据库连接池（保持向后兼容）
DB_POOL_CONFIG = {
    **DB_CONFIG,
    'pool_name': 'mypool',
    'pool_size': 32,  # 最大允许值32
    'pool_reset_session': True,
    'autocommit': True,
    'connect_timeout': 20,
    'time_zone': '+00:00'
}

# 数据模型
class OCRRecord(BaseModel):
    id: int
    passport_no: Optional[str] = None
    name1: Optional[str] = None
    name2: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[date] = None
    expiry_date: Optional[date] = None
    country_name_cn: Optional[str] = None
    doc_type_cn: Optional[str] = None
    visa_no: Optional[str] = None
    visa_date: Optional[date] = None
    passport_type: Optional[str] = None
    image_path: Optional[str] = None
    updated_at: Optional[datetime] = None

class OCRRecordUpdate(BaseModel):
    passport_no: Optional[str] = None
    name1: Optional[str] = None
    gender: Optional[str] = None
    birth_date: Optional[str] = None
    expiry_date: Optional[str] = None
    country_name_cn: Optional[str] = None
    doc_type_cn: Optional[str] = None
    visa_no: Optional[str] = None
    visa_date: Optional[str] = None
    passport_type: Optional[str] = None

class VisaInfoUpdate(BaseModel):
    visa_no: Optional[str] = None
    visa_date: Optional[str] = None

# 创建全局连接池
try:
    connection_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_POOL_CONFIG)
    logger.info(f"数据库连接池初始化成功，连接池大小: {DB_POOL_CONFIG['pool_size']}")
except Exception as e:
    logger.error(f"数据库连接池初始化失败: {str(e)}")
    raise

def get_db_connection():
    """从连接池获取数据库连接"""
    max_retries = 5
    retry_delay = 1
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # 从连接池获取连接
            connection = connection_pool.get_connection()
            if connection.is_connected():
                # 设置时区为东八区
                cursor = connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
                return connection
            else:
                connection.ping(reconnect=True, attempts=3, delay=1)
                # 设置时区为东八区
                cursor = connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
                return connection
        except mysql.connector.Error as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)
                logger.warning(f"获取数据库连接失败，{sleep_time}秒后重试: {str(e)}")
                time.sleep(sleep_time)
            else:
                logger.error(f"获取数据库连接失败，已重试{max_retries}次: {str(e)}")
                raise last_error

def get_db():
    """FastAPI依赖项，用于获取数据库连接"""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    finally:
        if conn:
            try:
                conn.close()  # 这里实际上是将连接返回到连接池
            except Exception as e:
                logger.error(f"关闭数据库连接时出错: {str(e)}")

# 添加认证依赖
async def verify_auth(
    x_auth_key: str = Header(None, alias="X-Auth-Key"),
    x_auth_secret: str = Header(None, alias="X-Auth-Secret")
):
    if not x_auth_key or not x_auth_secret:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers"
        )
    
    if x_auth_key != APP_CONFIG['app_key'] or x_auth_secret != APP_CONFIG['app_secret']:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials"
        )
    
    return True

# 路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "config": {
            "app_key": APP_CONFIG['app_key'],
            "app_secret": APP_CONFIG['app_secret'],
            "ocr_service_url": OCR_SERVICE_URL,  # 添加OCR服务URL到前端配置
            "check_service_on_load": False  # 禁用前端在加载时自动检查服务状态
        }
    })

@app.get("/api/ocr/records")
async def get_records_route(
    page: int = 1,
    page_size: int = 20,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    try:
        # 验证参数
        if page < 1:
            page = 1
        if page_size not in [20, 50]:
            page_size = 20
            
        cursor = db.cursor(dictionary=True)
        
        # 构建基础查询 - 修复时区转换问题
        base_query = """
            SELECT 
                id, passport_no, name1, name2, gender, birth_date, 
                expiry_date, country_name_cn, doc_type_cn, 
                visa_no, visa_date, passport_type, image_path,
                DATE_FORMAT(created_at, '%Y-%m-%d %H:%i:%S') as created_at,
                DATE_FORMAT(updated_at, '%Y-%m-%d %H:%i:%S') as updated_at,
                status
            FROM passport_records
        """
        count_query = "SELECT COUNT(*) as total FROM passport_records"
        
        # 初始化参数列表
        params = []
        where_clauses = []
        
        # 处理日期过滤 - 修复时区转换问题
        if start_date and end_date:
            where_clauses.append("DATE(created_at) BETWEEN %s AND %s")
            params.extend([start_date, end_date])
        
        # 构建完整的查询语句
        if where_clauses:
            where_sql = " WHERE " + " AND ".join(where_clauses)
            base_query += where_sql
            count_query += where_sql
        
        # 获取总记录数
        cursor.execute(count_query, tuple(params))
        total_records = cursor.fetchone()['total']
        
        # 添加分页
        base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        offset = (page - 1) * page_size
        query_params = params.copy()  # 创建参数副本
        query_params.extend([page_size, offset])
        
        # 执行查询
        logger.info(f"执行查询: {base_query}")
        logger.info(f"查询参数: {query_params}")
        cursor.execute(base_query, tuple(query_params))
        records = cursor.fetchall()
        
        # 处理日期字段和图片路径
        for record in records:
            # 处理日期字段
            for field in ['birth_date', 'expiry_date', 'visa_date']:
                if record.get(field) in ('0000-00-00', None):
                    record[field] = None
            
            # 处理图片路径
            if record.get('image_path'):
                record['image_url'] = f"/uploads/{record['image_path']}"
                thumb_path = UPLOAD_DIR / "thumbnails" / record['image_path']
                if thumb_path.exists():
                    record['thumbnail_url'] = f"/uploads/thumbnails/{record['image_path']}"
                else:
                    try:
                        original_path = UPLOAD_DIR / record['image_path']
                        if original_path.exists():
                            create_thumbnail(str(original_path))
                            record['thumbnail_url'] = f"/uploads/thumbnails/{record['image_path']}"
                        else:
                            record['thumbnail_url'] = record['image_url']
                    except Exception as e:
                        logger.error(f"创建缩略图失败: {str(e)}")
                        record['thumbnail_url'] = record['image_url']
            else:
                record['image_url'] = None
                record['thumbnail_url'] = None
        
        # 计算总页数
        total_pages = (total_records + page_size - 1) // page_size
        
        return {
            'records': records,
            'total_pages': total_pages,
            'current_page': page,
            'total_records': total_records
        }
        
    except Exception as e:
        logger.error(f"获取记录失败: {str(e)}")
        import traceback as tb  # 确保traceback可用
        logger.error(tb.format_exc())  # 添加堆栈跟踪
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ocr/stats/simple")
async def get_stats_simple(
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    """简化的统计接口，用于测试"""
    try:
        logger.info("开始执行简化统计查询")
        
        # 检查数据库连接
        if not db or not db.is_connected():
            logger.error("数据库连接无效")
            raise HTTPException(status_code=500, detail="数据库连接无效")
        
        cursor = db.cursor(dictionary=True)
        
        # 基本连接测试
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        logger.info(f"数据库连接测试成功: {result}")
        
        # 获取总数据量
        cursor.execute("SELECT COUNT(*) as count FROM passport_records")
        total_count = cursor.fetchone()['count']
        logger.info(f"总数据量: {total_count}")
        
        # 获取今日数据量（简化版本）
        cursor.execute("SELECT COUNT(*) as count FROM passport_records WHERE DATE(created_at) = CURDATE()")
        today_count = cursor.fetchone()['count']
        logger.info(f"今日数据量: {today_count}")
        
        cursor.close()
        
        return {
            'total_count': total_count,
            'today_count': today_count,
            'message': '简化统计查询成功'
        }
        
    except Exception as e:
        logger.error(f"简化统计查询失败: {str(e)}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"简化统计查询失败: {str(e)}")

@app.get("/api/ocr/stats")
async def get_stats(
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    try:
        logger.info("开始执行统计查询")
        
        # 检查数据库连接
        if not db or not db.is_connected():
            logger.error("数据库连接无效")
            raise HTTPException(status_code=500, detail="数据库连接无效")
        
        cursor = db.cursor(dictionary=True)
        
        # 检查数据库连接
        try:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            logger.info(f"数据库连接测试成功: {result}")
        except Exception as e:
            logger.error(f"数据库连接测试失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"数据库连接测试失败: {str(e)}")
        
        # 获取数据库时区信息
        try:
            cursor.execute("SELECT @@global.time_zone, @@session.time_zone, NOW(), CURDATE()")
            timezone_info = cursor.fetchone()
            logger.info(f"数据库时区信息: {timezone_info}")
        except Exception as e:
            logger.error(f"获取时区信息失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"获取时区信息失败: {str(e)}")
        
        # 检查表是否存在
        try:
            cursor.execute("SHOW TABLES LIKE 'passport_records'")
            table_exists = cursor.fetchone()
            if not table_exists:
                logger.error("passport_records 表不存在")
                raise HTTPException(status_code=500, detail="passport_records 表不存在")
            logger.info("passport_records 表存在")
        except Exception as e:
            logger.error(f"检查表存在性失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"检查表存在性失败: {str(e)}")
        
        # 获取今日护照数量（使用本地时间）
        try:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM passport_records 
                WHERE DATE(created_at) = CURDATE()
                AND doc_type_cn = '护照'
            """)
            today_passport_count = cursor.fetchone()['count']
            logger.info(f"今日护照查询成功: {today_passport_count}")
        except Exception as e:
            logger.error(f"今日护照查询失败: {str(e)}")
            today_passport_count = 0
        
        # 获取今日港澳台相关证件数量（包含港、澳、台字的所有证件）
        try:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM passport_records 
                WHERE DATE(created_at) = CURDATE()
                AND (
                    doc_type_cn LIKE '%%港%%' 
                    OR doc_type_cn LIKE '%%澳%%' 
                    OR doc_type_cn LIKE '%%台%%'
                )
            """)
            today_hmt_count = cursor.fetchone()['count']
            logger.info(f"今日港澳台查询成功: {today_hmt_count}")
        except Exception as e:
            logger.error(f"今日港澳台查询失败: {str(e)}")
            today_hmt_count = 0
        
        # 获取今日身份证数量
        try:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM passport_records 
                WHERE DATE(created_at) = CURDATE()
                AND doc_type_cn = '身份证'
            """)
            today_id_card_count = cursor.fetchone()['count']
            logger.info(f"今日身份证查询成功: {today_id_card_count}")
        except Exception as e:
            logger.error(f"今日身份证查询失败: {str(e)}")
            today_id_card_count = 0
        
        # 获取总数据量
        try:
            cursor.execute("SELECT COUNT(*) as count FROM passport_records")
            total_count = cursor.fetchone()['count']
            logger.info(f"总数据量查询成功: {total_count}")
        except Exception as e:
            logger.error(f"总数据量查询失败: {str(e)}")
            total_count = 0
        
        # 获取今日总记录数
        try:
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM passport_records 
                WHERE DATE(created_at) = CURDATE()
            """)
            today_total_count = cursor.fetchone()['count']
            logger.info(f"今日总记录数查询成功: {today_total_count}")
        except Exception as e:
            logger.error(f"今日总记录数查询失败: {str(e)}")
            today_total_count = 0
        
        # 获取今日各类型文档详细统计
        try:
            cursor.execute("""
                SELECT doc_type_cn, COUNT(*) as count 
                FROM passport_records 
                WHERE DATE(created_at) = CURDATE()
                GROUP BY doc_type_cn
                ORDER BY count DESC
            """)
            today_doc_types = cursor.fetchall()
            logger.info(f"今日各类型文档查询成功: {len(today_doc_types)} 种类型")
        except Exception as e:
            logger.error(f"今日各类型文档查询失败: {str(e)}")
            today_doc_types = []
        
        # 获取最近几条记录的时区转换示例
        try:
            cursor.execute("""
                SELECT 
                    id,
                    doc_type_cn,
                    created_at,
                    CONVERT_TZ(created_at, '+00:00', '+08:00') as beijing_time,
                    DATE(CONVERT_TZ(created_at, '+00:00', '+08:00')) as beijing_date
                FROM passport_records 
                ORDER BY created_at DESC 
                LIMIT 3
            """)
            recent_examples = cursor.fetchall()
            logger.info(f"最近记录示例查询成功: {len(recent_examples)} 条记录")
        except Exception as e:
            logger.error(f"最近记录示例查询失败: {str(e)}")
            recent_examples = []
        
        # 记录详细的调试信息
        logger.info(f"=== 统计调试信息 ===")
        logger.info(f"数据库时区设置: 全局={timezone_info['@@global.time_zone']}, 会话={timezone_info['@@session.time_zone']}")
        logger.info(f"数据库当前时间: {timezone_info['NOW()']}")
        logger.info(f"数据库当前日期: {timezone_info['CURDATE()']}")
        logger.info(f"今日总记录数: {today_total_count}")
        logger.info(f"今日护照数量: {today_passport_count}")
        logger.info(f"今日港澳台数量: {today_hmt_count}")
        logger.info(f"今日身份证数量: {today_id_card_count}")
        logger.info(f"总数据量: {total_count}")
        
        logger.info(f"今日各类型文档:")
        for doc_type in today_doc_types:
            logger.info(f"  {doc_type['doc_type_cn']}: {doc_type['count']}")
        
        logger.info(f"最近记录时区转换示例:")
        for example in recent_examples:
            logger.info(f"  ID:{example['id']}, 类型:{example['doc_type_cn']}, 原始时间:{example['created_at']}, 北京时间:{example['beijing_time']}, 北京日期:{example['beijing_date']}")
        
        cursor.close()
        
        return {
            'today_passport_count': today_passport_count,
            'today_hmt_count': today_hmt_count,
            'today_id_card_count': today_id_card_count,
            'total_count': total_count,
            'debug_info': {
                'db_timezone_global': timezone_info['@@global.time_zone'],
                'db_timezone_session': timezone_info['@@session.time_zone'],
                'db_now': str(timezone_info['NOW()']),
                'db_today': str(timezone_info['CURDATE()']),
                'today_total': today_total_count,
                'today_doc_types': today_doc_types,
                'recent_examples': recent_examples
            }
        }
    except HTTPException:
        # 重新抛出HTTP异常
        raise
    except Exception as e:
        logger.error(f"统计API异常: {str(e)}")
        import traceback
        logger.error(f"异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"统计查询失败: {str(e)}")

@app.get("/api/ocr/records/{record_id}")
async def get_record(
    record_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM passport_records WHERE id = %s", (record_id,))
    record = cursor.fetchone()
    cursor.close()
    
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    
    return record

@app.post("/api/ocr/records/{record_id}")
async def update_record(
    record_id: int,
    record: OCRRecordUpdate,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor()
    
    # 构建更新字段
    update_fields = []
    values = []
    
    for field, value in record.dict(exclude_unset=True).items():
        # 处理日期字段：空字符串转换为None
        if field in ['birth_date', 'expiry_date', 'visa_date']:
            if value == "" or value is None:
                update_fields.append(f"{field} = NULL")
            else:
                update_fields.append(f"{field} = %s")
                values.append(value)
        # 处理签证字段：空字符串转换为None
        elif field in ['visa_no']:
            if value == "" or value is None:
                update_fields.append(f"{field} = NULL")
            else:
                update_fields.append(f"{field} = %s")
                values.append(value)
        # 其他字段
        elif value is not None:
            update_fields.append(f"{field} = %s")
            values.append(value)
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # 添加更新时间
    update_fields.append("updated_at = %s")
    values.append(datetime.now())
    
    # 添加记录ID
    values.append(record_id)
    
    # 执行更新
    query = f"""
        UPDATE passport_records 
        SET {', '.join(update_fields)}
        WHERE id = %s
    """
    
    try:
        cursor.execute(query, values)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
    
    return {"message": "Record updated successfully"}

@app.delete("/api/ocr/records/{record_id}")
async def delete_record(
    record_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor()
    try:
        cursor.execute("DELETE FROM passport_records WHERE id = %s", (record_id,))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
    
    return {"message": "Record deleted successfully"}

@app.post("/api/ocr/records/{record_id}/recheck")
async def recheck_record(
    record_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor()
    try:
        cursor.execute("""
            UPDATE passport_records 
            SET visa_no = NULL, 
                visa_date = NULL,
                updated_at = %s
            WHERE id = %s
        """, (datetime.now(), record_id))
        db.commit()
        return {"message": "Visa information cleared successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()

@app.get("/api/ocr/records/{record_id}/image")
async def get_record_image(
    record_id: int,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT image_path FROM passport_records WHERE id = %s", (record_id,))
        record = cursor.fetchone()
        if not record or not record['image_path']:
            raise HTTPException(status_code=404, detail="Image not found")
        
        image_path = UPLOAD_DIR / record['image_path']
        if not image_path.exists():
            raise HTTPException(status_code=404, detail="Image file not found")
        
        return FileResponse(image_path)
    finally:
        cursor.close()

@app.post("/api/ocr/upload-photo")
async def upload_photo(
    file: UploadFile = File(...)
):
    """上传单张护照图片到处理队列"""
    try:
        # 检查文件类型
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="请选择有效的图片文件")
        
        # 检查队列是否已满
        if upload_queue.qsize() >= MAX_UPLOAD_QUEUE:
            raise HTTPException(
                status_code=429,
                detail=f"上传队列已满（最大{MAX_UPLOAD_QUEUE}张），请稍后再试"
            )

        # 检查OCR队列状态
        ocr_queue_size = ocr_queue.qsize()
        if ocr_queue_size > 50:  # 限制OCR队列大小
            raise HTTPException(
                status_code=429,
                detail=f"处理队列已满（当前{ocr_queue_size}个任务），请稍后再试"
            )

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"photo_{timestamp}.jpg"
        filepath = UPLOAD_DIR / filename
        task_id = uuid.uuid4().hex

        # 异步读取文件内容
        content = await file.read()
        
        # 直接保存文件
        try:
            logger.info(f"开始保存文件: {filename}")
            with open(filepath, "wb") as f:
                f.write(content)
            logger.info(f"文件保存完成: {filename}")
            
            # 检查文件是否成功保存
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"文件保存失败，文件不存在: {filepath}")
                
        except Exception as e:
            logger.error(f"保存文件失败: {filename}, 错误: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"保存文件失败: {str(e)}"
            )

        # 创建数据库记录
        record_id = None
        conn = None
        try:
            conn = get_write_connection()
            cursor = conn.cursor()
            sql = """
                INSERT INTO passport_records 
                (task_id, status, image_path, doc_type, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (
                task_id,
                'pending',
                filename,
                'PASSPORT',
                datetime.now(),
                datetime.now()
            )
            cursor.execute(sql, values)
            record_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            logger.info(f"数据库记录创建成功 (record_id: {record_id})")
            
        except mysql.connector.Error as e:
            logger.error(f"数据库操作失败: {str(e)}")
            if conn:
                conn.rollback()
            # 如果数据库操作失败，删除已保存的文件
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    logger.info(f"已删除文件: {filepath}")
                except Exception as del_e:
                    logger.error(f"删除文件失败: {str(del_e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if conn:
                try:
                    conn.close()
                    logger.info(f"数据库连接已关闭 (record_id: {record_id})")
                except Exception as e:
                    logger.error(f"关闭数据库连接失败: {str(e)}")

        # 将任务添加到OCR队列进行处理
        ocr_queue.put({
            'record_id': record_id,
            'image_path': filename  # 只传递文件名，不传递完整路径
        })
        logger.info(f"任务已添加到OCR队列 (record_id: {record_id}, 队列大小: {ocr_queue.qsize()})")

        return {
            "status": "success",
            "message": "图片上传成功！已加入处理队列...",
            "record_id": record_id,
            "task_id": task_id,
            "image_url": f"/uploads/{filename}",
            "queue_position": ocr_queue.qsize(),
            "auto_close_delay": 2000,
            "should_refresh": True  # 添加标志，告诉前端需要刷新列表
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ocr/status/check")
async def check_ocr_service():
    """检查OCR服务状态"""
    try:
        # 检查OCR服务是否可用
        import requests
        
        # 尝试访问OCR服务的健康检查端点
        health_url = f"{OCR_SERVICE_URL.replace('/ocr', '/health')}"
        logger.info(f"检查OCR服务健康状态: {health_url}")
        
        response = requests.get(health_url, timeout=5)
        ocr_available = response.status_code == 200
        
        if ocr_available:
            logger.info("OCR服务状态: 正常")
        else:
            logger.warning(f"OCR服务返回异常状态码: {response.status_code}")
            
    except Exception as e:
        logger.error(f"连接OCR服务失败: {str(e)}")
        ocr_available = False
    
    # 获取队列状态
    upload_queue_size = upload_queue.qsize()
    ocr_queue_size = ocr_queue.qsize()
    
    # 获取活跃线程数
    active_threads = len([f for f in upload_thread_pool._threads if f.is_alive()])
    
    return {
        "ocr_service": "available" if ocr_available else "unavailable",
        "upload_queue_size": upload_queue_size,
        "ocr_queue_size": ocr_queue_size,
        "active_threads": active_threads,
        "max_upload_queue": MAX_UPLOAD_QUEUE,
        "max_thread_pool": UPLOAD_THREAD_POOL_SIZE
    }

@app.get("/api/ocr/status/{record_id}")
async def get_processing_status(record_id: int):
    """获取OCR处理状态"""
    try:
        status = processing_status.get(record_id, {
            'status': 'pending',
            'message': '等待处理'
        })
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "ok",
        "service": "fastapi",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/passport/today")
async def get_today_passport_records(
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    """
    获取今日所有护照类型的数据
    Returns:
        dict: 包含今日护照记录的列表
    """
    cursor = db.cursor(dictionary=True)
    try:
        # 查询今日的护照记录
        query = """
            SELECT id, passport_no, name1, name2, gender, 
                   birth_date, expiry_date, country_name_cn, 
                   doc_type_cn, visa_no, visa_date, passport_type,
                   image_path, created_at, updated_at
            FROM passport_records 
            WHERE DATE(created_at) = CURDATE()
            AND doc_type_cn LIKE '%护照%'
            ORDER BY created_at DESC
        """
        
        cursor.execute(query)
        records = cursor.fetchall()
        
        # 处理日期格式
        for record in records:
            if record['birth_date']:
                record['birth_date'] = record['birth_date'].isoformat() if record['birth_date'] else None
            if record['expiry_date']:
                record['expiry_date'] = record['expiry_date'].isoformat() if record['expiry_date'] else None
            if record['visa_date']:
                record['visa_date'] = record['visa_date'].isoformat() if record['visa_date'] else None
            if record['created_at']:
                record['created_at'] = record['created_at'].isoformat() if record['created_at'] else None
            if record['updated_at']:
                record['updated_at'] = record['updated_at'].isoformat() if record['updated_at'] else None
        
        return {
            "success": True,
            "count": len(records),
            "date": datetime.now().date().isoformat(),
            "records": records
        }
        
    except Exception as e:
        logger.error(f"获取今日护照记录失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取今日护照记录失败: {str(e)}")
    finally:
        cursor.close()

@app.post("/api/passport/{record_id}/visa")
async def update_visa_info(
    record_id: int,
    visa_info: VisaInfoUpdate,
    db: mysql.connector.MySQLConnection = Depends(get_db)
):
    """
    更新指定记录的签证信息
    Args:
        record_id: 记录ID
        visa_info: 签证信息（visa_no, visa_date）
    Returns:
        dict: 更新结果
    """
    cursor = db.cursor()
    try:
        # 检查记录是否存在
        cursor.execute("SELECT id FROM passport_records WHERE id = %s", (record_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"记录ID {record_id} 不存在")
        
        # 构建更新字段
        update_fields = []
        values = []
        
        # 处理签证号码
        if visa_info.visa_no is not None:
            if visa_info.visa_no == "":
                update_fields.append("visa_no = NULL")
            else:
                update_fields.append("visa_no = %s")
                values.append(visa_info.visa_no)
        
        # 处理签证日期
        if visa_info.visa_date is not None:
            if visa_info.visa_date == "":
                update_fields.append("visa_date = NULL")
            else:
                update_fields.append("visa_date = %s")
                values.append(visa_info.visa_date)
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="没有提供要更新的字段")
        
        # 添加更新时间
        update_fields.append("updated_at = %s")
        values.append(datetime.now())
        
        # 添加记录ID
        values.append(record_id)
        
        # 执行更新
        query = f"""
            UPDATE passport_records 
            SET {', '.join(update_fields)}
            WHERE id = %s
        """
        
        cursor.execute(query, values)
        db.commit()
        
        return {
            "success": True,
            "message": "签证信息更新成功",
            "record_id": record_id,
            "updated_fields": [field.split(' = ')[0] for field in update_fields if 'updated_at' not in field]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"更新签证信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新签证信息失败: {str(e)}")
    finally:
        cursor.close()

@app.get("/api/country/code/{country_code}")
async def get_country_by_code(country_code: str):
    """
    根据国家代码查询国家信息
    Args:
        country_code: 3位ISO国家代码 (如: CHN, USA, GBR)
    Returns:
        dict: 国家信息
    """
    try:
        country_name = get_country_name_cn(country_code.upper())
        if country_name:
            return {
                "success": True,
                "country_code": country_code.upper(),
                "country_name_cn": country_name,
                "message": f"找到国家: {country_name}"
            }
        else:
            return {
                "success": False,
                "country_code": country_code.upper(),
                "country_name_cn": None,
                "message": f"未找到国家代码: {country_code}"
            }
    except Exception as e:
        logger.error(f"查询国家代码时出错: {str(e)}")
        return {
            "success": False,
            "country_code": country_code.upper(),
            "country_name_cn": None,
            "message": f"查询失败: {str(e)}"
        }

@app.get("/api/country/search")
async def search_countries(
    keyword: str = Query(..., description="搜索关键词，支持中文国家名或英文国家代码"),
    limit: int = Query(10, description="返回结果数量限制")
):
    """
    搜索国家信息
    Args:
        keyword: 搜索关键词
        limit: 返回结果数量限制
    Returns:
        dict: 匹配的国家列表
    """
    try:
        results = []
        with open('data/country-codes.csv', 'r', encoding='utf-8') as f:
            # 读取表头
            header = f.readline().strip().split(',')
            try:
                iso_index = header.index('ISO3166-1-Alpha-3')
                cn_index = header.index('official_name_cn')
                en_index = header.index('official_name_en')
            except ValueError as e:
                return {
                    "success": False,
                    "message": f"CSV文件格式错误: {str(e)}",
                    "results": []
                }
            
            # 读取数据行
            for line in f:
                if len(results) >= limit:
                    break
                    
                parts = line.strip().split(',')
                if len(parts) > max(iso_index, cn_index, en_index):
                    code = parts[iso_index].strip()
                    name_cn = parts[cn_index].strip()
                    name_en = parts[en_index].strip()
                    
                    # 检查是否匹配搜索关键词
                    keyword_upper = keyword.upper()
                    if (keyword_upper in code.upper() or 
                        keyword_upper in name_cn.upper() or 
                        keyword_upper in name_en.upper()):
                        results.append({
                            "country_code": code,
                            "country_name_cn": name_cn,
                            "country_name_en": name_en
                        })
        
        return {
            "success": True,
            "keyword": keyword,
            "total": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"搜索国家信息时出错: {str(e)}")
        return {
            "success": False,
            "message": f"搜索失败: {str(e)}",
            "results": []
        }

@app.get("/api/country/list")
async def list_countries(
    page: int = Query(1, description="页码"),
    page_size: int = Query(50, description="每页数量"),
    region: str = Query(None, description="地区筛选 (如: Asia, Europe, Africa)")
):
    """
    获取国家列表
    Args:
        page: 页码
        page_size: 每页数量
        region: 地区筛选
    Returns:
        dict: 国家列表
    """
    try:
        all_countries = []
        with open('data/country-codes.csv', 'r', encoding='utf-8') as f:
            # 读取表头
            header = f.readline().strip().split(',')
            try:
                iso_index = header.index('ISO3166-1-Alpha-3')
                cn_index = header.index('official_name_cn')
                en_index = header.index('official_name_en')
                region_index = header.index('Region Name')
            except ValueError as e:
                return {
                    "success": False,
                    "message": f"CSV文件格式错误: {str(e)}",
                    "results": []
                }
            
            # 读取数据行
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > max(iso_index, cn_index, en_index, region_index):
                    code = parts[iso_index].strip()
                    name_cn = parts[cn_index].strip()
                    name_en = parts[en_index].strip()
                    region_name = parts[region_index].strip()
                    
                    # 如果指定了地区筛选
                    if region and region.upper() not in region_name.upper():
                        continue
                    
                    all_countries.append({
                        "country_code": code,
                        "country_name_cn": name_cn,
                        "country_name_en": name_en,
                        "region": region_name
                    })
        
        # 分页处理
        total = len(all_countries)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_countries = all_countries[start_idx:end_idx]
        
        return {
            "success": True,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
            "results": paginated_countries
        }
        
    except Exception as e:
        logger.error(f"获取国家列表时出错: {str(e)}")
        return {
            "success": False,
            "message": f"获取失败: {str(e)}",
            "results": []
        }

@app.get("/api/country/columns")
async def get_country_columns():
    """
    获取国家代码CSV文件的列信息
    Returns:
        dict: 列信息
    """
    try:
        with open('data/country-codes.csv', 'r', encoding='utf-8') as f:
            # 读取表头
            header = f.readline().strip().split(',')
            
            # 定义列说明
            column_descriptions = {
                'FIFA': 'FIFA国家代码',
                'Dial': '电话区号',
                'ISO3166-1-Alpha-3': 'ISO 3166-1 3位字母国家代码',
                'MARC': 'MARC国家代码',
                'is_independent': '是否独立国家',
                'ISO3166-1-numeric': 'ISO 3166-1 数字国家代码',
                'GAUL': 'GAUL代码',
                'FIPS': 'FIPS国家代码',
                'WMO': 'WMO国家代码',
                'ISO3166-1-Alpha-2': 'ISO 3166-1 2位字母国家代码',
                'ITU': 'ITU国家代码',
                'IOC': 'IOC国家代码',
                'DS': 'DS国家代码',
                'UNTERM Spanish Formal': '西班牙语正式名称',
                'Global Code': '全球代码',
                'Intermediate Region Code': '中间地区代码',
                'official_name_fr': '法语官方名称',
                'UNTERM French Short': '法语简称',
                'ISO4217-currency_name': 'ISO 4217货币名称',
                'UNTERM Russian Formal': '俄语正式名称',
                'UNTERM English Short': '英语简称',
                'ISO4217-currency_alphabetic_code': 'ISO 4217货币字母代码',
                'Small Island Developing States (SIDS)': '小岛屿发展中国家',
                'UNTERM Spanish Short': '西班牙语简称',
                'ISO4217-currency_numeric_code': 'ISO 4217货币数字代码',
                'UNTERM Chinese Formal': '中文正式名称',
                'UNTERM French Formal': '法语正式名称',
                'UNTERM Russian Short': '俄语简称',
                'M49': 'M49代码',
                'Sub-region Code': '子地区代码',
                'Region Code': '地区代码',
                'official_name_ar': '阿拉伯语官方名称',
                'ISO4217-currency_minor_unit': 'ISO 4217货币小数单位',
                'UNTERM Arabic Formal': '阿拉伯语正式名称',
                'UNTERM Chinese Short': '中文简称',
                'Land Locked Developing Countries (LLDC)': '内陆发展中国家',
                'Intermediate Region Name': '中间地区名称',
                'official_name_es': '西班牙语官方名称',
                'UNTERM English Formal': '英语正式名称',
                'official_name_cn': '中文官方名称',
                'official_name_en': '英语官方名称',
                'ISO4217-currency_country_name': 'ISO 4217货币国家名称',
                'Least Developed Countries (LDC)': '最不发达国家',
                'Region Name': '地区名称',
                'UNTERM Arabic Short': '阿拉伯语简称',
                'Sub-region Name': '子地区名称',
                'official_name_ru': '俄语官方名称',
                'Global Name': '全球名称',
                'Capital': '首都',
                'Continent': '大陆',
                'TLD': '顶级域名',
                'Languages': '语言',
                'Geoname ID': 'Geoname ID',
                'CLDR display name': 'CLDR显示名称',
                'EDGAR': 'EDGAR代码',
                'wikidata_id': '维基数据ID'
            }
            
            # 构建列信息
            columns_info = []
            for i, column in enumerate(header):
                description = column_descriptions.get(column, f'列 {i+1}')
                columns_info.append({
                    'index': i,
                    'name': column,
                    'description': description,
                    'is_key': column in ['ISO3166-1-Alpha-3', 'official_name_cn', 'official_name_en', 'Region Name']
                })
            
            return {
                "success": True,
                "total_columns": len(header),
                "columns": columns_info,
                "key_columns": {
                    "country_code": "ISO3166-1-Alpha-3",
                    "country_name_cn": "official_name_cn", 
                    "country_name_en": "official_name_en",
                    "region_name": "Region Name"
                }
            }
            
    except Exception as e:
        logger.error(f"获取列信息时出错: {str(e)}")
        return {
            "success": False,
            "message": f"获取列信息失败: {str(e)}",
            "columns": []
        }

@app.get("/api/country/code/{country_code}")
async def get_country_by_code(country_code: str):
    """
    根据国家代码查询国家信息
    Args:
        country_code: 3位ISO国家代码 (如: CHN, USA, GBR)
    Returns:
        dict: 国家信息
    """
    try:
        country_name = get_country_name_cn(country_code.upper())
        if country_name:
            return {
                "success": True,
                "country_code": country_code.upper(),
                "country_name_cn": country_name,
                "message": f"找到国家: {country_name}",
                "query_column": "ISO3166-1-Alpha-3",
                "result_column": "official_name_cn"
            }
        else:
            return {
                "success": False,
                "country_code": country_code.upper(),
                "country_name_cn": None,
                "message": f"未找到国家代码: {country_code}",
                "query_column": "ISO3166-1-Alpha-3",
                "result_column": "official_name_cn"
            }
    except Exception as e:
        logger.error(f"查询国家代码时出错: {str(e)}")
        return {
            "success": False,
            "country_code": country_code.upper(),
            "country_name_cn": None,
            "message": f"查询失败: {str(e)}",
            "query_column": "ISO3166-1-Alpha-3",
            "result_column": "official_name_cn"
        }

# OCR结果写入线程
def ocr_result_writer():
    """独立线程处理OCR结果写入"""
    while True:
        try:
            if not db_write_queue.empty():
                write_task = db_write_queue.get()
                db = None
                try:
                    db = get_write_connection()  # 使用写连接池
                    cursor = db.cursor()
                    
                    # 验证日期字段
                    values = list(write_task['values'])
                    date_fields = [5, 6, 10]  # birth_date, expiry_date, visa_date 在values中的索引
                    
                    for field_index in date_fields:
                        if field_index < len(values) and values[field_index]:
                            try:
                                # 验证日期格式
                                if isinstance(values[field_index], str):
                                    from datetime import datetime
                                    parsed_date = datetime.strptime(values[field_index], '%Y-%m-%d')
                                    values[field_index] = parsed_date.strftime('%Y-%m-%d')
                                    logger.info(f"验证日期字段: {values[field_index]}")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"无效的日期格式: {values[field_index]}, 设置为None")
                                values[field_index] = None
                    
                    # 更新OCR结果
                    cursor.execute("""
                    UPDATE passport_records 
                    SET status = %s,
                            doc_type_cn = %s,
                        name1 = %s,
                        name2 = %s,
                        gender = %s,
                        birth_date = %s,
                        expiry_date = %s,
                            passport_no = %s,
                        country_name_cn = %s,
                        visa_no = %s,
                        visa_date = %s,
                        passport_type = %s,
                        updated_at = %s,
                        remarks = %s
                    WHERE id = %s
                    """, values)
                    
                    db.commit()
                    logger.info(f"数据库更新成功，记录ID: {write_task['record_id']}")
                    
                except Exception as e:
                    logger.error(f"数据库写入失败: {str(e)}")
                finally:
                    if db:
                        try:
                            cursor.close()
                            db.close()
                            logger.info(f"数据库写入连接已关闭 (record_id: {write_task['record_id']})")
                        except Exception as e:
                            logger.error(f"关闭数据库写入连接失败: {str(e)}")
                    db_write_queue.task_done()
            
            time.sleep(0.1)  # 避免空队列时的CPU占用
            
        except Exception as e:
            logger.error(f"OCR结果写入线程错误: {str(e)}")
            time.sleep(1)

# 创建读写连接池
try:
    write_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_WRITE_POOL_CONFIG)
    read_pool = mysql.connector.pooling.MySQLConnectionPool(**DB_READ_POOL_CONFIG)
    logger.info(f"数据库写连接池初始化成功，连接池大小: {DB_WRITE_POOL_CONFIG['pool_size']}")
    logger.info(f"数据库读连接池初始化成功，连接池大小: {DB_READ_POOL_CONFIG['pool_size']}")
except Exception as e:
    logger.error(f"数据库连接池初始化失败: {str(e)}")
    raise

def get_write_connection():
    """获取写操作的数据库连接"""
    max_retries = 5
    retry_delay = 1
    last_error = None
    
    for attempt in range(max_retries):
        try:
            connection = write_pool.get_connection()
            if connection.is_connected():
                # 设置时区为东八区
                cursor = connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
                return connection
            else:
                connection.ping(reconnect=True, attempts=3, delay=1)
                # 设置时区为东八区
                cursor = connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
                return connection
        except mysql.connector.Error as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)
                logger.warning(f"获取写连接失败，{sleep_time}秒后重试: {str(e)}")
                time.sleep(sleep_time)
            else:
                logger.error(f"获取写连接失败，已重试{max_retries}次: {str(e)}")
                raise last_error

def get_read_connection():
    """获取读操作的数据库连接"""
    max_retries = 3
    retry_delay = 1
    last_error = None
    
    for attempt in range(max_retries):
        try:
            connection = read_pool.get_connection()
            if connection.is_connected():
                # 设置时区为东八区
                cursor = connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
                return connection
            else:
                connection.ping(reconnect=True, attempts=2, delay=1)
                # 设置时区为东八区
                cursor = connection.cursor()
                cursor.execute("SET time_zone = '+08:00'")
                cursor.close()
                return connection
        except mysql.connector.Error as e:
            last_error = e
            if attempt < max_retries - 1:
                sleep_time = retry_delay * (2 ** attempt)
                logger.warning(f"获取读连接失败，{sleep_time}秒后重试: {str(e)}")
                time.sleep(sleep_time)
            else:
                logger.error(f"获取读连接失败，已重试{max_retries}次: {str(e)}")
                raise last_error

# 在启动时添加线程池监控
def monitor_thread_pools():
    """监控线程池状态"""
    while True:
        try:
            upload_active = len([f for f in upload_thread_pool._threads if f.is_alive()])
            io_active = len([f for f in thread_pool._threads if f.is_alive()])
            
            logger.info(f"线程池状态 - 上传线程: {upload_active}/{UPLOAD_THREAD_POOL_SIZE}, IO线程: {io_active}/{IO_THREAD_POOL_SIZE}")
            
            time.sleep(60)  # 每分钟记录一次
            
        except Exception as e:
            logger.error(f"监控线程池状态时出错: {str(e)}")
            time.sleep(60)

async def process_ocr_task(task):
    """处理单个OCR任务"""
    record_id = task['record_id']
    db = None
    
    try:
        # 从数据库获取任务信息
        try:
            db = get_db_connection()
            cursor = db.cursor(dictionary=True)
            cursor.execute("""
                SELECT image_path, status 
                FROM passport_records 
                WHERE id = %s
            """, (record_id,))
            record = cursor.fetchone()
            cursor.close()
            db.close()
            
            if not record:
                logger.error(f"记录 {record_id} 不存在")
                return
                
            image_path = record['image_path']
            
        except Exception as e:
            logger.error(f"获取任务信息失败: {str(e)}")
            if db:
                db.close()
            return
            
        # 更新状态为处理中
        try:
            db = get_db_connection()
            cursor = db.cursor()
            cursor.execute("""
                    UPDATE passport_records 
                SET status = %s, updated_at = %s
                    WHERE id = %s
            """, ('processing', datetime.now(), record_id))
            db.commit()
            cursor.close()
            db.close()
        except Exception as e:
            logger.error(f"更新状态失败: {str(e)}")
            if db:
                db.close()
            return

        # 处理OCR
        try:
            # 构建图片的完整路径
            filepath = UPLOAD_DIR / image_path
            logger.info(f"开始处理图片，完整路径: {filepath}")
            
            # 检查文件是否存在
            if not os.path.exists(filepath):
                logger.error(f"图片文件不存在: {filepath}")
                raise FileNotFoundError(f"图片文件不存在: {filepath}")
            
            ocr_result = await process_image(str(filepath))
            extracted_data = extract_ocr_data(ocr_result)
            
            # 准备写入数据
            values = (
                'completed',  # status
                extracted_data.get('doc_type_cn', ''),
                extracted_data.get('name1', ''),
                extracted_data.get('name2', ''),
                extracted_data.get('gender', ''),
                extracted_data.get('birth_date'),
                extracted_data.get('expiry_date'),
                extracted_data.get('passport_no', ''),
                extracted_data.get('country_name_cn', ''),
                extracted_data.get('visa_no', ''),
                extracted_data.get('visa_date'),
                extracted_data.get('passport_type', ''),
                datetime.now(),
                '识别成功',
                record_id
            )
            
            # 将结果放入写入队列
            db_write_queue.put({
                'record_id': record_id,
                'values': values
            })

        except Exception as e:
            logger.error(f"OCR处理失败: {str(e)}")
            # 更新失败状态
            try:
                db = get_db_connection()
                cursor = db.cursor()
                cursor.execute("""
                    UPDATE passport_records 
                    SET status = %s,
                        remarks = %s,
                        updated_at = %s
                    WHERE id = %s
                """, ('failed', str(e)[:255], datetime.now(), record_id))
                db.commit()
                cursor.close()
                db.close()
            except Exception as update_err:
                logger.error(f"更新失败状态时出错: {str(update_err)}")
                if db:
                    db.close()
            
    except Exception as e:
        logger.error(f"处理任务失败: {str(e)}")
        if db:
            db.close()

async def process_image(image_path: str) -> dict:
    """处理单张图片的OCR识别
    Args:
        image_path: 图片路径
    Returns:
        dict: OCR识别结果
    """
    print(f"\n=== 开始处理图片: {image_path} ===")
    max_retries = 5  # 增加重试次数
    current_retry = 0
    
    # 获取事件循环
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 如果没有运行中的事件循环，创建一个新的
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    while current_retry < max_retries:
        try:
            # 读取图片并转换为base64
            print("读取图片文件...")
            
            try:
                # 检查文件是否存在
                if not os.path.exists(image_path):
                    raise FileNotFoundError(f"图片文件不存在: {image_path}")
                
                # 在线程池中异步读取文件
                def read_file():
                    with open(image_path, "rb") as file:
                        return file.read()
                        
                file_bytes = await loop.run_in_executor(thread_pool, read_file)
                print(f"图片大小: {len(file_bytes)/1024:.2f} KB")
                
            except Exception as e:
                logger.error(f"读取图片文件失败: {str(e)}")
                import traceback as tb  # 确保traceback可用
                logger.error(tb.format_exc())
                raise HTTPException(
                    status_code=500,
                    detail=f"读取图片文件失败: {str(e)}"
                )

            # 准备请求数据
            print("准备OCR请求数据...")

            # 在线程池中异步发送OCR请求
            async def send_ocr_request():
                print(f"发送OCR请求到: {OCR_SERVICE_URL}")
                print(f"当前重试次数: {current_retry + 1}/{max_retries}")
                print("正在等待响应...")
                
                session = requests.Session()
                adapter = requests.adapters.HTTPAdapter(
                    max_retries=3,
                    pool_connections=10,
                    pool_maxsize=10
                )
                session.mount('http://', adapter)
                session.mount('https://', adapter)
                
                try:
                    # 使用 multipart/form-data 格式发送文件
                    files = {'file': ('image.jpg', file_bytes, 'image/jpeg')}
                    response = await loop.run_in_executor(
                        thread_pool,
                        lambda: session.post(
                            OCR_SERVICE_URL,
                            files=files,
                            verify=False
                        )
                    )
                    return response
                except Exception as e:
                    logger.error(f"发送OCR请求失败: {str(e)}")
                    raise
                finally:
                    session.close()

            # 异步发送请求
            try:
                response = await send_ocr_request()
            except requests.exceptions.ConnectionError as e:
                logger.error(f"OCR服务连接错误: {str(e)}")
                if current_retry < max_retries - 1:
                    wait_time = min(30, 5 * (2 ** current_retry))  # 指数退避，最大等待30秒
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    current_retry += 1
                    continue
                raise HTTPException(
                    status_code=503,
                    detail="OCR服务连接失败，请检查服务是否正常运行"
                )
            
            # 检查响应状态
            print(f"收到响应: HTTP {response.status_code}")
            if response.status_code != 200:
                logger.error(f"OCR请求失败: HTTP {response.status_code}")
                logger.error(f"错误响应: {response.text}")
                if current_retry < max_retries - 1:
                    wait_time = min(30, 5 * (2 ** current_retry))  # 指数退避，最大等待30秒
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    current_retry += 1
                    continue
                raise HTTPException(
                    status_code=500,
                    detail=f"OCR服务请求失败: HTTP {response.status_code}"
                )

            # 解析响应结果
            try:
                response_data = response.json()
                return response_data
            except json.JSONDecodeError as e:
                logger.error(f"解析OCR响应JSON失败: {str(e)}")
                if current_retry < max_retries - 1:
                    wait_time = min(30, 5 * (2 ** current_retry))  # 指数退避，最大等待30秒
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    await asyncio.sleep(wait_time)
                    current_retry += 1
                    continue
                raise HTTPException(
                    status_code=500,
                    detail="OCR服务返回的数据格式无效"
                )

        except Exception as e:
            logger.error(f"处理图片时出错: {str(e)}")
            import traceback as tb  # 确保traceback可用
            logger.error(tb.format_exc())
            if current_retry < max_retries - 1:
                wait_time = min(30, 5 * (2 ** current_retry))  # 指数退避，最大等待30秒
                logger.info(f"等待 {wait_time} 秒后重试...")
                await asyncio.sleep(wait_time)
                current_retry += 1
                continue
            raise HTTPException(
                status_code=500,
                detail=f"处理图片失败: {str(e)}"
            )

    # 如果所有重试都失败
    error_msg = f"OCR服务请求失败 (已重试 {max_retries} 次)"
    logger.error(error_msg)
    raise HTTPException(status_code=503, detail=error_msg)

# OCR队列处理线程
def process_ocr_queue():
    """独立线程处理OCR队列"""
    async def run_queue():
        while True:
            try:
                if not ocr_queue.empty():
                    task = ocr_queue.get()
                    try:
                        await process_ocr_task(task)
                    except Exception as e:
                        logger.error(f"处理任务失败: {str(e)}")
                    finally:
                        ocr_queue.task_done()
                        logger.info(f"OCR任务处理完成 (record_id: {task.get('record_id')})")
                
                await asyncio.sleep(0.1)  # 避免空队列时的CPU占用
                
            except Exception as e:
                logger.error(f"OCR队列处理错误: {str(e)}")
                await asyncio.sleep(1)

    # 创建新的事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(run_queue())
    except Exception as e:
        logger.error(f"OCR队列处理线程异常: {str(e)}")
    finally:
        loop.close()

def create_thumbnail(image_path, max_size=(128, 128)):
    """创建图片缩略图"""
    try:
        # 确保输入路径是字符串
        image_path = str(image_path)

        # 确保目标目录存在
        thumbnail_dir = UPLOAD_DIR / "thumbnails"
        thumbnail_dir.mkdir(exist_ok=True)

        # 生成缩略图文件名（使用原始文件名）
        filename = os.path.basename(image_path)
        thumbnail_path = thumbnail_dir / filename

        # 打开原图并创建缩略图
        with Image.open(image_path) as img:
            # 保持宽高比
            img.thumbnail(max_size)
            # 保存缩略图
            img.save(str(thumbnail_path), "JPEG", quality=85)
            
        return str(thumbnail_path)
    except Exception as e:
        logger.error(f"创建缩略图失败: {str(e)}")
        return None

def save_ocr_images(record_id: int, ocr_result: dict) -> dict:
    """保存OCR结果图像
    Args:
        record_id: 记录ID
        ocr_result: OCR结果
    Returns:
        dict: 图像URL信息
    """
    image_urls = {}
    
    try:
        if "ocrResults" in ocr_result and len(ocr_result["ocrResults"]) > 0:
            result = ocr_result["ocrResults"][0]
            
            # 保存OCR结果图
            if result.get("ocrImage"):
                ocr_image_path = OCR_INFO_DIR / f"{record_id}-ocr_result.jpg"
                image_data = base64.b64decode(result["ocrImage"])
                with open(ocr_image_path, "wb") as f:
                    f.write(image_data)
                image_urls["ocr_image_url"] = f"/ocr_info/{record_id}-ocr_result.jpg"
            
            # 保存预处理图
            if result.get("docPreprocessingImage"):
                preprocess_path = OCR_INFO_DIR / f"{record_id}-preprocessing.jpg"
                image_data = base64.b64decode(result["docPreprocessingImage"])
                with open(preprocess_path, "wb") as f:
                    f.write(image_data)
                image_urls["preprocessing_url"] = f"/ocr_info/{record_id}-preprocessing.jpg"
            
            # 保存输入图像
            if result.get("inputImage"):
                input_path = OCR_INFO_DIR / f"{record_id}-input.jpg"
                image_data = base64.b64decode(result["inputImage"])
                with open(input_path, "wb") as f:
                    f.write(image_data)
                image_urls["input_url"] = f"/ocr_info/{record_id}-input.jpg"
    
    except Exception as e:
        logger.error(f"保存OCR图像失败: {str(e)}")
    
    return image_urls



def get_country_name_cn(country_code: str) -> str:
    """根据国家代码获取中文名称"""
    try:
        with open('data/country-codes.csv', 'r', encoding='utf-8') as f:
            # 读取表头
            header = f.readline().strip().split(',')
            # 找到需要的列的索引
            try:
                iso_index = header.index('ISO3166-1-Alpha-3')
                cn_index = header.index('official_name_cn')
            except ValueError as e:
                print(f"在CSV文件中未找到必要的列: {e}")
                return ""
                
            # 读取数据行
            for line in f:
                parts = line.strip().split(',')
                if len(parts) > max(iso_index, cn_index):
                    code = parts[iso_index].strip()  # ISO3166-1-Alpha-3代码
                    name = parts[cn_index].strip()  # 使用official_name_cn列的值
                    if code and name and code.upper() == country_code.upper():
                        return name
    except Exception as e:
        print(f"获取国家中文名称失败: {str(e)}")
    return ""

def extract_ocr_data(ocr_result: dict) -> dict:
    """
    从PP-OCRv5识别结果中提取护照信息
    优先使用MRZ信息，只有在MRZ中没有找到时才使用其他OCR文本
    Args:
        ocr_result: PP-OCRv5的识别结果 (OCRResponse格式)
    Returns:
        dict: 提取的护照信息
    """
    extracted_data = {
        'doc_type_cn': '',
        'name1': '',
        'name2': '',
        'gender': '',
        'birth_date': None,
        'expiry_date': None,
        'passport_no': '',
        'country_name_cn': '',
        'visa_no': '',
        'visa_date': None,
        'passport_type': ''
    }
    
    try:
        # 检查OCR结果结构 - 支持多种格式
        if not ocr_result:
            logger.warning("OCR结果为空")
            return extracted_data
        
        # 调试：输出完整的OCR结果结构
        logger.info(f"🔍 OCR结果类型: {type(ocr_result)}")
        logger.info(f"🔍 OCR结果键: {list(ocr_result.keys()) if isinstance(ocr_result, dict) else 'N/A'}")
        
        # 尝试多种格式解析
        rec_texts = []
        
        # 格式1: {"result": {"ocrResults": [{"rec_texts": [...]}]}}
        if isinstance(ocr_result, dict) and 'result' in ocr_result:
            result = ocr_result.get('result', {})
            ocr_results = result.get('ocrResults', [])
            if ocr_results and len(ocr_results) > 0:
                rec_texts = ocr_results[0].get('rec_texts', [])
                logger.info(f"✅ 使用格式1解析，找到 {len(rec_texts)} 个文本")
                
                # 调试：输出rec_texts的详细信息
                if rec_texts:
                    logger.info("🔍 rec_texts内容:")
                    for i, text_item in enumerate(rec_texts[:5]):  # 只显示前5个
                        if isinstance(text_item, dict):
                            text = text_item.get('text', '')
                            confidence = text_item.get('confidence', 0)
                            logger.info(f"   {i+1}. '{text}' (置信度: {confidence:.2f})")
                        else:
                            logger.info(f"   {i+1}. '{text_item}'")
                else:
                    logger.warning("⚠️  rec_texts为空，OCR服务器可能没有识别到文本")
        
        # 格式2: 直接包含rec_texts和rec_scores
        elif isinstance(ocr_result, dict) and 'rec_texts' in ocr_result and 'rec_scores' in ocr_result:
            texts = ocr_result['rec_texts']
            scores = ocr_result['rec_scores']
            rec_texts = [{"text": text, "confidence": score} for text, score in zip(texts, scores)]
            logger.info(f"✅ 使用格式2解析，找到 {len(rec_texts)} 个文本")
        
        # 格式3: 新的PP-OCRv5格式 {"status": "success", "results": [{"rec_texts": [...], "rec_scores": [...]}]}
        elif isinstance(ocr_result, dict) and 'status' in ocr_result and 'results' in ocr_result:
            if ocr_result.get('status') == 'success' and ocr_result.get('results'):
                first_result = ocr_result['results'][0]
                if 'rec_texts' in first_result and 'rec_scores' in first_result:
                    texts = first_result['rec_texts']
                    scores = first_result['rec_scores']
                    rec_texts = [{"text": text, "confidence": score} for text, score in zip(texts, scores)]
                    logger.info(f"✅ 使用新PP-OCRv5格式解析，找到 {len(rec_texts)} 个文本")
                    
                    # 调试：输出识别到的文本
                    if rec_texts:
                        logger.info("🔍 新格式识别结果:")
                        for i, text_item in enumerate(rec_texts[:10]):  # 显示前10个
                            text = text_item.get('text', '')
                            confidence = text_item.get('confidence', 0)
                            logger.info(f"   {i+1}. '{text}' (置信度: {confidence:.2f})")
                else:
                    logger.warning("⚠️  新格式中缺少rec_texts或rec_scores")
            else:
                logger.warning("⚠️  新格式状态不是success或results为空")
        
        # 格式4: 直接是列表格式
        elif isinstance(ocr_result, list) and len(ocr_result) > 0:
            if isinstance(ocr_result[0], list):
                rec_texts = []
                for line in ocr_result[0]:
                    if line and len(line) >= 2:
                        text = line[1][0] if isinstance(line[1], tuple) else str(line[1])
                        confidence = line[1][1] if isinstance(line[1], tuple) and len(line[1]) > 1 else 0.0
                        rec_texts.append({"text": text, "confidence": confidence})
                logger.info(f"✅ 使用格式4解析，找到 {len(rec_texts)} 个文本")
        
        if not rec_texts:
            logger.warning("⚠️  无法解析OCR结果格式")
            logger.warning(f"⚠️  OCR结果内容: {repr(ocr_result)}")
            return extracted_data
            
        logger.info(f"识别到 {len(rec_texts)} 个文本片段")
        
        # 输出原始OCR结果
        logger.info("🔍 原始OCR识别结果:")
        for i, text_item in enumerate(rec_texts):
            if isinstance(text_item, dict):
                text = text_item.get('text', '')
                confidence = text_item.get('confidence', 0)
                logger.info(f"   片段 {i+1}: '{text}' (置信度: {confidence:.2f})")
            else:
                text = str(text_item)
                logger.info(f"   片段 {i+1}: '{text}'")
        
        # 提取所有识别的文本
        all_texts = []
        for text_item in rec_texts:
            if isinstance(text_item, dict):
                text = text_item.get('text', '')
                confidence = text_item.get('confidence', 0)
                logger.info(f"📝 文本: '{text}' (置信度: {confidence:.2f})")
            else:
                text = str(text_item)
                logger.info(f"📝 文本: '{text}'")
            
            if text.strip():
                all_texts.append(text.strip())
        
        logger.info(f"📝 处理后的文本: {all_texts}")
        logger.info(f"📊 文本数量: {len(all_texts)}")
        
        # 输出前几个文本用于调试
        if all_texts:
            logger.info("🔍 前5个识别文本:")
            for i, text in enumerate(all_texts[:5]):
                logger.info(f"   {i+1}. '{text}'")
        
        # ========== 第一步：优先从MRZ信息中提取所有字段 ==========
        logger.info("🔍 第一步：优先从MRZ信息中提取所有字段")
        
        # 检测证件类型
        if any('<<' in t for t in all_texts):
            extracted_data['doc_type_cn'] = '护照'
            logger.info("🔍 检测到护照特征 (MRZ信息)")
        
        # 处理MRZ信息
        mrz_lines = [text for text in all_texts if '<<' in text and len(text) > 30]
        logger.info(f"🔍 找到 {len(mrz_lines)} 行MRZ信息")
        
        # 按顺序分配第一行和第二行MRZ
        first_line_mrz = None
        second_line_mrz = None
        
        # 直接按OCR获取的顺序，第一个MRZ行就是第一行，第二个MRZ行就是第二行
        for i, mrz_text in enumerate(mrz_lines):
            logger.info(f"🔍 分析MRZ行 {i+1}: {mrz_text}")
            
            if i == 0:
                first_line_mrz = mrz_text
                logger.info(f"🔍 按顺序识别为第一行MRZ: {mrz_text}")
            elif i == 1:
                second_line_mrz = mrz_text
                logger.info(f"🔍 按顺序识别为第二行MRZ: {mrz_text}")
            else:
                # 如果有多于2行，忽略后续行
                logger.warning(f"🔍 忽略额外的MRZ行: {mrz_text}")
        
        # 处理第一行MRZ
        if first_line_mrz:
            logger.info("🔍 处理第一行MRZ")
            
            # 提取护照类型代码 (前2位)
            if len(first_line_mrz) >= 2:
                passport_type_code = first_line_mrz[0:2]
                logger.info(f"🔍 提取的MRZ护照类型代码: {passport_type_code}")
                
                # 简化的护照类型判断：只支持三种类型
                if passport_type_code.startswith('P'):
                    extracted_data['passport_type'] = '普通护照'
                    logger.info("从MRZ设置护照类型: 普通护照")
                elif passport_type_code.startswith('D'):
                    extracted_data['passport_type'] = '外交护照'
                    logger.info("从MRZ设置护照类型: 外交护照")
                elif passport_type_code.startswith('O'):
                    extracted_data['passport_type'] = '外交官'
                    logger.info("从MRZ设置护照类型: 外交官")
                else:
                    logger.info(f"未知的护照类型代码: {passport_type_code}")
            
            # 提取国家代码 (位置2-5)
            if len(first_line_mrz) >= 5:
                country_code = first_line_mrz[2:5]
                logger.info(f"🔍 提取的MRZ国家代码: {country_code}")
                country_name = get_country_name_cn(country_code)
                if country_name:
                    extracted_data['country_name_cn'] = country_name
                    logger.info(f"从MRZ设置国家: {country_name} ({country_code})")
            
            # 提取姓名 (去掉护照类型和国家代码前缀)
            if len(first_line_mrz) >= 5:
                name_part = first_line_mrz[5:]  # 去掉前5位(护照类型+国家代码)
                name_parts = name_part.split('<<')
                if len(name_parts) >= 2:
                    # 提取姓氏
                    surname = name_parts[0].replace('<', ' ').strip()
                    # 提取名字
                    given_name = name_parts[1].replace('<', ' ').strip()
                    
                    if surname and len(surname) > 2 and not extracted_data['name1']:
                        extracted_data['name1'] = surname
                        logger.info(f"从MRZ第一行提取姓氏: {surname}")
                    
                    if given_name and len(given_name) > 2 and not extracted_data['name2']:
                        extracted_data['name2'] = given_name
                        logger.info(f"从MRZ第一行提取名字: {given_name}")
                elif len(name_parts) == 1:
                    # 如果只有一个部分，可能是完整的姓名
                    full_name = name_parts[0].replace('<', ' ').strip()
                    if full_name and len(full_name) > 2 and not extracted_data['name1']:
                        extracted_data['name1'] = full_name
                        logger.info(f"从MRZ第一行提取姓名: {full_name}")
        
        # 处理第二行MRZ
        if second_line_mrz:
            logger.info("🔍 处理第二行MRZ")
            
            # 从第二行MRZ提取护照号码 (位置0-9)
            if len(second_line_mrz) >= 9:
                # 尝试提取护照号码，可能是前9位或者包含字母和数字的组合
                passport_no = second_line_mrz[0:9]
                logger.info(f"🔍 从MRZ第二行提取护照号码: {passport_no}")
                
                # 清理护照号码，去除填充字符
                passport_no = passport_no.replace('<', '').strip()
                if passport_no:
                    extracted_data['passport_no'] = passport_no
                    logger.info(f"✅ 从MRZ第二行提取护照号码: {passport_no}")
                else:
                    logger.warning("从MRZ第二行提取的护照号码为空")
            
            # 从第二行MRZ提取出生日期 (位置13-19)
            if len(second_line_mrz) >= 19:
                birth_mrz = second_line_mrz[13:19]  # 620308 = 62年03月08日
                logger.info(f"🔍 提取的MRZ出生日期部分: {birth_mrz}")
                if birth_mrz.isdigit():  # 确保是数字
                    year = '19' + birth_mrz[0:2]  # 假设是19xx年
                    month = birth_mrz[2:4]
                    day = birth_mrz[4:6]
                    logger.info(f"🔍 解析出生日期: 年={year}, 月={month}, 日={day}")
                    # 验证日期有效性
                    if int(month) >= 1 and int(month) <= 12 and int(day) >= 1 and int(day) <= 31:
                        date_obj = f"{year}-{month}-{day}"
                        extracted_data['birth_date'] = date_obj
                        logger.info(f"从MRZ第二行提取出生日期: {date_obj}")
                    else:
                        logger.warning(f"无效的MRZ出生日期格式: {birth_mrz}")
                else:
                    logger.warning(f"MRZ出生日期部分不是数字: {birth_mrz}")
            elif len(second_line_mrz) >= 15:
                # 如果长度不够，尝试从其他位置提取
                birth_mrz = second_line_mrz[13:15] + second_line_mrz[15:17] + second_line_mrz[17:19]
                logger.info(f"🔍 尝试从其他位置提取出生日期: {birth_mrz}")
                if birth_mrz.isdigit() and len(birth_mrz) == 6:
                    year = '19' + birth_mrz[0:2]
                    month = birth_mrz[2:4]
                    day = birth_mrz[4:6]
                    logger.info(f"🔍 解析出生日期: 年={year}, 月={month}, 日={day}")
                    if int(month) >= 1 and int(month) <= 12 and int(day) >= 1 and int(day) <= 31:
                        date_obj = f"{year}-{month}-{day}"
                        extracted_data['birth_date'] = date_obj
                        logger.info(f"从MRZ第二行提取出生日期: {date_obj}")
            
            # 从第二行MRZ提取性别 (位置20)
            if len(second_line_mrz) >= 20:
                gender_code = second_line_mrz[20]
                logger.info(f"🔍 提取的MRZ性别代码: {gender_code}")
                if gender_code == 'M':
                    extracted_data['gender'] = '男'
                    logger.info("从MRZ第二行提取性别: 男")
                elif gender_code == 'F':
                    extracted_data['gender'] = '女'
                    logger.info("从MRZ第二行提取性别: 女")
            
            # 从第二行MRZ提取有效期 (位置21-27)
            if len(second_line_mrz) >= 27:
                expiry_mrz = second_line_mrz[21:27]  # 290314 = 29年03月14日
                logger.info(f"🔍 提取的MRZ有效期部分: {expiry_mrz}")
                if expiry_mrz.isdigit():  # 确保是数字
                    year = '20' + expiry_mrz[0:2]
                    month = expiry_mrz[2:4]
                    day = expiry_mrz[4:6]
                    logger.info(f"🔍 解析有效期: 年={year}, 月={month}, 日={day}")
                    # 验证日期有效性
                    if int(month) >= 1 and int(month) <= 12 and int(day) >= 1 and int(day) <= 31:
                        date_obj = f"{year}-{month}-{day}"
                        extracted_data['expiry_date'] = date_obj
                        logger.info(f"从MRZ第二行提取有效期: {date_obj}")
                    else:
                        logger.warning(f"无效的MRZ有效期格式: {expiry_mrz}")
                else:
                    logger.warning(f"MRZ有效期部分不是数字: {expiry_mrz}")
            elif len(second_line_mrz) >= 23:
                # 如果长度不够，尝试从其他位置提取
                expiry_mrz = second_line_mrz[21:23] + second_line_mrz[23:25] + second_line_mrz[25:27]
                logger.info(f"🔍 尝试从其他位置提取有效期: {expiry_mrz}")
                if expiry_mrz.isdigit() and len(expiry_mrz) == 6:
                    year = '20' + expiry_mrz[0:2]
                    month = expiry_mrz[2:4]
                    day = expiry_mrz[4:6]
                    logger.info(f"🔍 解析有效期: 年={year}, 月={month}, 日={day}")
                    if int(month) >= 1 and int(month) <= 12 and int(day) >= 1 and int(day) <= 31:
                        date_obj = f"{year}-{month}-{day}"
                        extracted_data['expiry_date'] = date_obj
                        logger.info(f"从MRZ第二行提取有效期: {date_obj}")
        
        # ========== 第二步：如果MRZ中没有找到，再从其他OCR文本中提取 ==========
        logger.info("🔍 第二步：如果MRZ中没有找到，再从其他OCR文本中提取")
        
        # 解析证件信息
        for text in all_texts:
            text = text.upper()
            
            # 检测证件类型 (如果MRZ中没有找到)
            if not extracted_data['doc_type_cn']:
                # 检查港澳通行证（优先级最高）
                if any('港澳居民来往内地通行证' in t or '港澳居民往来通行证' in t for t in all_texts):
                    extracted_data['doc_type_cn'] = '港澳居民来往内地通行证'
                    logger.info("🔍 检测到港澳居民来往内地通行证")
                # 检查身份证号码
                elif any('公民身份号码' in t or '身份证号码' in t for t in all_texts):
                    # 查找身份证号码
                    for t in all_texts:
                        if re.search(r'^\d{17}[\dXx]$', t):
                            id_number = t
                            logger.info(f"🔍 检测到身份证号码: {id_number}")
                            
                            # 根据身份证号码前缀判断证件类型
                            if id_number.startswith('81'):
                                extracted_data['doc_type_cn'] = '香港身份证'
                                logger.info("🔍 检测到香港身份证")
                            elif id_number.startswith('82'):
                                extracted_data['doc_type_cn'] = '澳门身份证'
                                logger.info("🔍 检测到澳门身份证")
                            elif id_number.startswith('83'):
                                extracted_data['doc_type_cn'] = '台湾身份证'
                                logger.info("🔍 检测到台湾身份证")
                            else:
                                extracted_data['doc_type_cn'] = '身份证'
                                logger.info("🔍 检测到身份证")
                            break
                # 检查身份证号码（直接匹配18位数字）
                elif any(re.search(r'^\d{17}[\dXx]$', t) for t in all_texts):
                    # 查找身份证号码
                    for t in all_texts:
                        if re.search(r'^\d{17}[\dXx]$', t):
                            id_number = t
                            logger.info(f"🔍 检测到身份证号码: {id_number}")
                            
                            # 根据身份证号码前缀判断证件类型
                            if id_number.startswith('81'):
                                extracted_data['doc_type_cn'] = '香港身份证'
                                logger.info("🔍 检测到香港身份证")
                            elif id_number.startswith('82'):
                                extracted_data['doc_type_cn'] = '澳门身份证'
                                logger.info("🔍 检测到澳门身份证")
                            elif id_number.startswith('83'):
                                extracted_data['doc_type_cn'] = '台湾身份证'
                                logger.info("🔍 检测到台湾身份证")
                            else:
                                extracted_data['doc_type_cn'] = '身份证'
                                logger.info("🔍 检测到身份证")
                            break
                # 检查其他通行证
                elif any('通行证' in t for t in all_texts):
                    extracted_data['doc_type_cn'] = '通行证'
                    logger.info("🔍 检测到通行证")
                else:
                    extracted_data['doc_type_cn'] = '护照'  # 默认
                    logger.info("🔍 默认证件类型: 护照")
            
            # 护照号码 (仅在MRZ中没有找到时)
            if not extracted_data['passport_no']:
                passport_pattern = r'[A-Z]{1,2}[0-9]{6,8}'
                matches = re.findall(passport_pattern, text)
                if matches:
                    extracted_data['passport_no'] = matches[0]
                    logger.info(f"通过正则匹配找到护照号码: {matches[0]}")
            
            # 身份证号码 (仅在MRZ中没有找到时)
            if not extracted_data['passport_no'] and extracted_data['doc_type_cn'] in ['身份证', '香港身份证', '澳门身份证', '台湾身份证']:
                id_pattern = r'^\d{17}[\dXx]$'
                if re.match(id_pattern, text):
                    extracted_data['passport_no'] = text  # 使用passport_no字段存储身份证号码
                    logger.info(f"找到身份证号码: {text}")
            
            # 姓名提取 (仅在MRZ中没有找到时)
            if not extracted_data['name1']:
                # 中文姓名 (2-4个中文字符)
                if extracted_data['doc_type_cn'] in ['身份证', '香港身份证', '澳门身份证', '台湾身份证', '港澳居民来往内地通行证']:
                    # 处理"姓名陈亚芬"格式
                    if text.startswith('姓名'):
                        name = text.replace('姓名', '').strip()
                        if re.match(r'^[\u4e00-\u9fa5]{2,4}$', name):
                            extracted_data['name1'] = name
                            logger.info(f"找到中文姓名: {name}")
                    # 直接匹配中文姓名
                    elif re.match(r'^[\u4e00-\u9fa5]{2,4}$', text):
                        extracted_data['name1'] = text
                        logger.info(f"找到中文姓名: {text}")
                # 英文姓名 (通常包含字母，长度在2-50个字符)
                else:
                    name_pattern = r'[A-Z\s]{2,50}'
                    # 排除已知的护照字段
                    if not any(keyword in text for keyword in ['PASSPORT', 'REPUBLIC', 'NATIONALITY', 'DATE', 'BIRTH', 'EXPIRY', 'AUTHORITY', 'SERVICE', 'CODE', 'TYPE']):
                        name_matches = re.findall(name_pattern, text)
                        if name_matches:
                            name = name_matches[0].strip()
                            if len(name) >= 2:
                                extracted_data['name1'] = name
                                logger.info(f"找到英文姓名: {name}")
            
            # 性别提取 (仅在MRZ中没有找到时)
            if not extracted_data['gender']:
                # 处理"性别女民族汉"格式
                if text.startswith('性别'):
                    gender_text = text.replace('性别', '').strip()
                    if '男' in gender_text:
                        extracted_data['gender'] = '男'
                        logger.info(f"找到中文性别: 男")
                    elif '女' in gender_text:
                        extracted_data['gender'] = '女'
                        logger.info(f"找到中文性别: 女")
                # 中文性别
                elif text in ['男', '女']:
                    extracted_data['gender'] = text
                    logger.info(f"找到中文性别: {text}")
                # 英文性别
                elif 'M' in text or 'MALE' in text:
                    extracted_data['gender'] = '男'
                    logger.info("找到英文性别: M -> 男")
                elif 'F' in text or 'FEMALE' in text:
                    extracted_data['gender'] = '女'
                    logger.info("找到英文性别: F -> 女")
            
            # 出生日期提取 (仅在MRZ中没有找到时)
            if not extracted_data['birth_date']:
                if text.startswith('出生'):
                    birth_text = text.replace('出生', '').strip()
                    chinese_date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
                    chinese_matches = re.findall(chinese_date_pattern, birth_text)
                    if chinese_matches:
                        try:
                            year, month, day = chinese_matches[0]
                            extracted_data['birth_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            logger.info(f"找到中文出生日期: {extracted_data['birth_date']}")
                        except:
                            pass
                elif re.match(r'^\d{4}\.\d{2}\.\d{2}$', text):
                    try:
                        year, month, day = text.split('.')
                        extracted_data['birth_date'] = f"{year}-{month}-{day}"
                        logger.info(f"找到港澳通行证出生日期: {extracted_data['birth_date']}")
                    except:
                        pass
                else:
                    chinese_date_pattern = r'(\d{4})年(\d{1,2})月(\d{1,2})日'
                    chinese_matches = re.findall(chinese_date_pattern, text)
                    if chinese_matches:
                        try:
                            year, month, day = chinese_matches[0]
                            extracted_data['birth_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            logger.info(f"找到中文出生日期: {extracted_data['birth_date']}")
                        except:
                            pass
                    # 港澳通行证日期格式已在上面处理，这里不用再处理
                    # 英文日期格式 (DD.MM.YYYY 或 DD/MM/YYYY)
                    else:
                        date_pattern = r'\d{2}[./]\d{2}[./]\d{4}'
                        date_matches = re.findall(date_pattern, text)
                        if date_matches:
                            try:
                                date_str = date_matches[0]
                                if '.' in date_str:
                                    day, month, year = date_str.split('.')
                                else:
                                    day, month, year = date_str.split('/')
                                extracted_data['birth_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                                logger.info(f"找到英文出生日期: {extracted_data['birth_date']}")
                            except:
                                pass
            
            # 有效期提取 (仅在MRZ中没有找到时)
            if not extracted_data['expiry_date']:
                # 港澳通行证有效期格式 (YYYY.MM.DD-YYYY.MM.DD)
                if '-' in text and re.match(r'^\d{4}\.\d{2}\.\d{2}-\d{4}\.\d{2}\.\d{2}$', text):
                    try:
                        start_date, end_date = text.split('-')
                        year, month, day = end_date.split('.')
                        extracted_data['expiry_date'] = f"{year}-{month}-{day}"
                        logger.info(f"找到港澳通行证有效期: {extracted_data['expiry_date']}")
                    except:
                        pass
                # 英文有效期格式 (DD.MM.YYYY 或 DD/MM/YYYY)
                elif 'EXPIRY' in text or 'VALID' in text:
                    date_pattern = r'\d{2}[./]\d{2}[./]\d{4}'
                    date_matches = re.findall(date_pattern, text)
                    if date_matches:
                        try:
                            date_str = date_matches[0]
                            if '.' in date_str:
                                day, month, year = date_str.split('.')
                            else:
                                day, month, year = date_str.split('/')
                            extracted_data['expiry_date'] = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                            logger.info(f"找到有效期: {extracted_data['expiry_date']}")
                        except:
                            pass
            
            # 国家/地区信息提取 (仅在MRZ中没有找到时)
            if not extracted_data['country_name_cn']:
                # 根据证件类型设置国家/地区
                if extracted_data['doc_type_cn'] == '身份证':
                    extracted_data['country_name_cn'] = '中国'
                    logger.info("设置国家: 中国")
                elif extracted_data['doc_type_cn'] == '香港身份证':
                    extracted_data['country_name_cn'] = '香港'
                    logger.info("设置地区: 香港")
                elif extracted_data['doc_type_cn'] == '澳门身份证':
                    extracted_data['country_name_cn'] = '澳门'
                    logger.info("设置地区: 澳门")
                elif extracted_data['doc_type_cn'] == '台湾身份证':
                    extracted_data['country_name_cn'] = '台湾'
                    logger.info("设置地区: 台湾")
                # 英文国家代码 (3位大写字母)
                else:
                    country_pattern = r'[A-Z]{3}'
                    country_matches = re.findall(country_pattern, text)
                    for country_code in country_matches:
                        # 排除常见的非国家代码
                        if country_code not in ['USA', 'GBR', 'CAN', 'AUS', 'DEU', 'FRA', 'ITA', 'ESP', 'NLD', 'BEL', 'CHE', 'AUT', 'SWE', 'NOR', 'DNK', 'FIN', 'POL', 'CZE', 'HUN', 'ROU', 'BGR', 'HRV', 'SVN', 'SVK', 'LTU', 'LVA', 'EST', 'LUX', 'MLT', 'CYP', 'GRC', 'PRT', 'IRL', 'ISL', 'LIE', 'MCO', 'AND', 'SMR', 'VAT', 'MDA', 'ALB', 'MKD', 'BIH', 'MNE', 'SRB', 'KOS']:
                            country_name = get_country_name_cn(country_code)
                            if country_name:
                                extracted_data['country_name_cn'] = country_name
                                logger.info(f"找到国家: {country_name} ({country_code})")
                                break
            
            # 签证号码
            if not extracted_data['visa_no']:
                visa_pattern = r'[A-Z]{1,2}[0-9]{6,10}'
                visa_matches = re.findall(visa_pattern, text)
                if visa_matches and 'VISA' in text:
                    extracted_data['visa_no'] = visa_matches[0]
                    logger.info(f"找到签证号码: {visa_matches[0]}")
        
        # 护照类型只通过MRZ判断，不再重复设置
        # 如果MRZ中没有设置护照类型，则保持为空
        if not extracted_data['passport_type']:
            logger.info("MRZ中未设置护照类型，保持为空")
        
        # 验证和清理日期字段
        for date_field in ['birth_date', 'expiry_date', 'visa_date']:
            if extracted_data[date_field]:
                try:
                    # 验证日期格式
                    if isinstance(extracted_data[date_field], str):
                        # 尝试解析日期字符串
                        parsed_date = datetime.strptime(extracted_data[date_field], '%Y-%m-%d')
                        extracted_data[date_field] = parsed_date.strftime('%Y-%m-%d')
                        logger.info(f"验证并格式化 {date_field}: {extracted_data[date_field]}")
                    else:
                        # 如果是datetime对象，转换为字符串
                        extracted_data[date_field] = extracted_data[date_field].strftime('%Y-%m-%d')
                except (ValueError, TypeError) as e:
                    logger.warning(f"无效的 {date_field} 格式: {extracted_data[date_field]}, 设置为None")
                    extracted_data[date_field] = None
        
        logger.info(f"提取完成，结果: {extracted_data}")
        
    except Exception as e:
        logger.error(f"提取OCR数据时出错: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    return extracted_data

if __name__ == "__main__":
    import uvicorn
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='OCR Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind')
    parser.add_argument('--no-ssl', action='store_true', help='Disable HTTPS (use HTTP instead)')
    parser.add_argument('--ssl-keyfile', help='SSL key file path')
    parser.add_argument('--ssl-certfile', help='SSL certificate file path')
    args = parser.parse_args()
    
    if not args.no_ssl:
        if not args.ssl_keyfile or not args.ssl_certfile:
            # 如果没有指定证书文件，使用默认路径
            base_dir = os.path.dirname(os.path.abspath(__file__))
            ssl_keyfile = os.path.join(base_dir, 'privkey.pem')
            ssl_certfile = os.path.join(base_dir, 'fullchain.pem')
        else:
            ssl_keyfile = args.ssl_keyfile
            ssl_certfile = args.ssl_certfile
        
        # 检查证书文件是否存在
        if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
            logger.error(f"SSL证书文件不存在: {ssl_keyfile} 或 {ssl_certfile}")
            raise FileNotFoundError("SSL证书文件不存在")
        
        # 创建SSL上下文
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(ssl_certfile, ssl_keyfile)
        
        # 启动HTTPS服务器
        logger.info(f"Starting HTTPS server on {args.host}:{args.port}...")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            ssl_keyfile=ssl_keyfile,
            ssl_certfile=ssl_certfile,
            ssl_version=ssl.PROTOCOL_TLS,
            reload=False
        )
    else:
        # 启动HTTP服务器
        logger.info(f"Starting HTTP server on {args.host}:{args.port}...")
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=False
        ) 