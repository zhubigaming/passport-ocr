#!/usr/bin/env python3
"""
使用PaddleX官方服务化部署的OCR服务器
基于PaddleOCR官方推荐的服务化部署方案
"""

import os
import sys
import json
import base64
import argparse
import logging
import subprocess
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import requests

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('paddlex_ocr_server')

# PaddleX OCR服务配置
PADDLEX_OCR_URL = "http://localhost:8080"
PADDLEX_OCR_PIPELINE = "OCR"

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
    logger.info("启动PaddleX OCR服务代理...")
    try:
        # 检查PaddleX OCR服务是否可用
        await check_paddlex_service()
        logger.info("PaddleX OCR服务代理启动成功")
    except Exception as e:
        logger.error(f"PaddleX OCR服务代理启动失败: {str(e)}")
        raise
    
    yield  # 服务运行中
    
    # 关闭事件
    logger.info("PaddleX OCR服务代理正在关闭...")

async def check_paddlex_service():
    """检查PaddleX OCR服务是否可用"""
    try:
        response = requests.get(f"{PADDLEX_OCR_URL}/health", timeout=5)
        if response.status_code == 200:
            logger.info("PaddleX OCR服务连接正常")
            return True
        else:
            raise Exception(f"PaddleX OCR服务响应异常: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"PaddleX OCR服务连接失败: {e}")
        logger.info("请确保已启动PaddleX OCR服务:")
        logger.info("paddlex --serve --pipeline OCR")
        raise Exception("PaddleX OCR服务不可用")

# 创建FastAPI应用
app = FastAPI(
    title="PaddleX OCR服务代理",
    description="基于PaddleX官方服务化部署的OCR识别服务",
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
        "service": "PaddleX OCR服务代理",
        "version": "1.0.0",
        "status": "running",
        "paddlex_url": PADDLEX_OCR_URL
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        response = requests.get(f"{PADDLEX_OCR_URL}/health", timeout=5)
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "paddlex_available": response.status_code == 200
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "paddlex_available": False,
            "error": str(e)
        }

@app.post("/ocr", response_model=OCRResponse)
async def ocr_recognize(request: OCRRequest):
    """OCR识别接口 - 代理到PaddleX OCR服务"""
    try:
        # 检查PaddleX OCR服务
        try:
            response = requests.get(f"{PADDLEX_OCR_URL}/health", timeout=5)
            if response.status_code != 200:
                raise HTTPException(status_code=503, detail="PaddleX OCR服务不可用")
        except requests.exceptions.RequestException:
            raise HTTPException(status_code=503, detail="PaddleX OCR服务连接失败")
        
        # 解码base64图片
        try:
            image_data = base64.b64decode(request.file)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"图片数据解码失败: {str(e)}")
        
        # 调用PaddleX OCR服务
        logger.info("调用PaddleX OCR服务进行识别...")
        
        # 准备请求数据（根据PaddleX OCR API格式）
        paddlex_request = {
            "images": [request.file],  # base64编码的图片
            "file_type": request.fileType
        }
        
        # 发送请求到PaddleX OCR服务
        try:
            response = requests.post(
                f"{PADDLEX_OCR_URL}/predict",
                json=paddlex_request,
                timeout=30
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"PaddleX OCR服务错误: {response.text}"
                )
            
            # 解析PaddleX OCR响应
            paddlex_result = response.json()
            
            # 转换为标准格式
            formatted_result = {
                "ocrResults": [{
                    "rec_texts": [],
                    "prunedResult": {
                        "rec_texts": []
                    }
                }]
            }
            
            # 提取识别的文本（根据PaddleX OCR响应格式调整）
            if "results" in paddlex_result:
                for result in paddlex_result["results"]:
                    if "text" in result:
                        formatted_result["ocrResults"][0]["rec_texts"].append(result["text"])
                        formatted_result["ocrResults"][0]["prunedResult"]["rec_texts"].append(result["text"])
            
            logger.info(f"识别到 {len(formatted_result['ocrResults'][0]['rec_texts'])} 行文字")
            
            return OCRResponse(
                result=formatted_result,
                status="success"
            )
            
        except requests.exceptions.Timeout:
            raise HTTPException(status_code=504, detail="PaddleX OCR服务响应超时")
        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=502, detail=f"PaddleX OCR服务请求失败: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"OCR识别错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR识别失败: {str(e)}")

def main():
    parser = argparse.ArgumentParser(description='PaddleX OCR服务代理')
    parser.add_argument('--host', default='0.0.0.0', help='绑定主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='绑定端口 (默认: 8080)')
    parser.add_argument('--paddlex-url', default='http://localhost:8080', help='PaddleX OCR服务地址')
    
    args = parser.parse_args()
    
    # 更新PaddleX OCR服务地址
    global PADDLEX_OCR_URL
    PADDLEX_OCR_URL = args.paddlex_url
    
    print(f"🚀 启动PaddleX OCR服务代理...")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   PaddleX OCR服务: {PADDLEX_OCR_URL}")
    print(f"   API文档: http://{args.host}:{args.port}/docs")
    
    try:
        uvicorn.run(
            "ocr_server_paddlex:app",
            host=args.host,
            port=args.port,
            reload=False
        )
    except KeyboardInterrupt:
        print("\n👋 PaddleX OCR服务代理已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 