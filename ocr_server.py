#!/usr/bin/env python3
"""
PaddleOCR识别服务器
提供HTTP API接口进行OCR识别
"""

import os
import sys
import json
import base64
import argparse
import logging
from io import BytesIO
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ocr_server')

# 全局OCR实例
_ocr_instance = None

def init_ocr():
    """初始化PaddleOCR"""
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("正在初始化PaddleOCR...")
            _ocr_instance = PaddleOCR(
                use_angle_cls=True,
                lang='en',
                # 移除 use_gpu 参数，新版本PaddleOCR不再支持
            )
            logger.info("PaddleOCR初始化完成")
        except Exception as e:
            logger.error(f"PaddleOCR初始化失败: {str(e)}")
            raise
    return _ocr_instance

# 数据模型
class OCRRequest(BaseModel):
    file: str  # base64编码的图片数据
    fileType: int = 1  # 文件类型，1表示图片

class OCRResponse(BaseModel):
    result: dict
    status: str = "success"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动事件
    logger.info("启动OCR服务...")
    try:
        init_ocr()
        logger.info("OCR服务启动成功")
    except Exception as e:
        logger.error(f"OCR服务启动失败: {str(e)}")
        raise
    
    yield  # 服务运行中
    
    # 关闭事件
    logger.info("OCR服务正在关闭...")

# 创建FastAPI应用
app = FastAPI(
    title="PaddleOCR识别服务",
    description="基于PaddleOCR的图片文字识别服务",
    version="1.0.0",
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

@app.get("/")
async def root():
    """根路径，返回服务信息"""
    return {
        "service": "PaddleOCR识别服务",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "ocr_ready": _ocr_instance is not None
    }

@app.post("/ocr", response_model=OCRResponse)
async def ocr_recognize(request: OCRRequest):
    """OCR识别接口"""
    try:
        # 检查OCR实例
        if _ocr_instance is None:
            raise HTTPException(status_code=503, detail="OCR服务未初始化")
        
        # 解码base64图片
        try:
            image_data = base64.b64decode(request.file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"图片数据解码失败: {str(e)}")
        
        # 将图片数据转换为字节流
        image_stream = BytesIO(image_data)
        
        # 进行OCR识别
        logger.info("开始OCR识别...")
        ocr_result = _ocr_instance.ocr(image_stream.getvalue())
        logger.info("OCR识别完成")
        
        # 处理识别结果
        if not ocr_result or not ocr_result[0]:
            return OCRResponse(
                result={
                    "ocrResults": [],
                    "message": "未识别到文字内容"
                }
            )
        
        # 格式化结果
        formatted_result = {
            "ocrResults": [{
                "rec_texts": [],
                "prunedResult": {
                    "rec_texts": []
                }
            }]
        }
        
        # 提取识别的文本
        rec_texts = []
        for line in ocr_result[0]:
            if line and len(line) >= 2:
                text = line[1][0] if isinstance(line[1], tuple) else str(line[1])
                rec_texts.append(text)
        
        formatted_result["ocrResults"][0]["rec_texts"] = rec_texts
        formatted_result["ocrResults"][0]["prunedResult"]["rec_texts"] = rec_texts
        
        logger.info(f"识别到 {len(rec_texts)} 行文字")
        
        return OCRResponse(
            result=formatted_result,
            status="success"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR识别错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='PaddleOCR识别服务器')
    parser.add_argument('--host', default='0.0.0.0', help='绑定主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='绑定端口 (默认: 8080)')
    parser.add_argument('--workers', type=int, default=1, help='工作进程数 (默认: 1)')
    
    args = parser.parse_args()
    
    print(f"🚀 启动PaddleOCR服务器...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   API文档: http://{args.host}:{args.port}/docs")
    print(f"   工作进程数: {args.workers}")
    
    try:
        uvicorn.run(
            "ocr_server:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=False
        )
    except KeyboardInterrupt:
        print("\n👋 OCR服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 