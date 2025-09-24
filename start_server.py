#!/usr/bin/env python3
"""
OCR护照识别系统启动脚本
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 确保项目根目录在Python路径中
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_directories():
    """创建必要的目录"""
    directories = [
        'logs',
        'uploads',
        'uploads/thumbnails',
        'ocr_info',
        'static'
    ]
    
    for directory in directories:
        dir_path = project_root / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ 目录已准备: {directory}")

def check_dependencies():
    """检查必要的依赖"""
    print("检查依赖...")
    
    try:
        import fastapi
        print(f"✓ FastAPI: {fastapi.__version__}")
    except ImportError:
        print("✗ FastAPI 未安装")
        return False
    
    try:
        import uvicorn
        print(f"✓ Uvicorn: {uvicorn.__version__}")
    except ImportError:
        print("✗ Uvicorn 未安装")
        return False
    
    try:
        import mysql.connector
        print("✓ MySQL Connector 已安装")
    except ImportError:
        print("✗ MySQL Connector 未安装")
        return False
    
    try:
        from PIL import Image
        print("✓ Pillow 已安装")
    except ImportError:
        print("✗ Pillow 未安装")
        return False
    
    return True

def check_config():
    """检查配置文件"""
    try:
        from config import DB_CONFIG, APP_CONFIG
        print("✓ 配置文件加载成功")
        
        # 检查数据目录
        data_dir = project_root / 'data'
        country_codes_file = data_dir / 'country-codes.csv'
        if country_codes_file.exists():
            print("✓ 国家代码数据文件存在")
        else:
            print("⚠ 国家代码数据文件不存在")
        
        return True
    except Exception as e:
        print(f"✗ 配置文件错误: {e}")
        return False

def start_server(host='0.0.0.0', port=8000, ssl_mode=False, ssl_keyfile=None, ssl_certfile=None):
    """启动FastAPI服务器"""
    print(f"\n{'='*50}")
    print("OCR护照识别系统")
    print(f"{'='*50}")
    
    # 检查环境
    if not check_dependencies():
        print("\n❌ 依赖检查失败，请安装必要的依赖包")
        print("运行: pip install -r requirements.txt")
        return 1
    
    if not check_config():
        print("\n❌ 配置检查失败，请检查 config.py 文件")
        return 1
    
    # 创建目录
    setup_directories()
    
    # SSL配置处理
    if ssl_mode:
        if not ssl_keyfile or not ssl_certfile:
            # 使用默认证书路径
            ssl_keyfile = str(project_root / 'privkey.pem')
            ssl_certfile = str(project_root / 'fullchain.pem')
        
        # 检查证书文件
        if not os.path.exists(ssl_keyfile) or not os.path.exists(ssl_certfile):
            print(f"\n❌ SSL证书文件不存在:")
            print(f"   私钥: {ssl_keyfile}")
            print(f"   证书: {ssl_certfile}")
            print(f"\n💡 请先生成SSL证书:")
            print(f"   python generate_ssl_cert.py")
            return 1
    
    # 启动服务器
    print(f"\n🚀 启动服务器...")
    if ssl_mode:
        print(f"   HTTPS模式: https://{host}:{port}")
        print(f"   SSL私钥: {ssl_keyfile}")
        print(f"   SSL证书: {ssl_certfile}")
    else:
        print(f"   HTTP模式: http://{host}:{port}")
    
    protocol = "https" if ssl_mode else "http"
    print(f"   管理界面: {protocol}://{host}:{port}")
    print(f"   API文档: {protocol}://{host}:{port}/docs")
    
    try:
        import uvicorn
        from api_server import app
        
        # 准备uvicorn参数
        uvicorn_kwargs = {
            'host': host,
            'port': port,
            'reload': False
        }
        
        # 添加SSL配置
        if ssl_mode:
            uvicorn_kwargs.update({
                'ssl_keyfile': ssl_keyfile,
                'ssl_certfile': ssl_certfile
            })
        
        print(f"\n✅ 服务器配置完成，正在启动...")
        if ssl_mode:
            print(f"⚠️  使用自签名证书时，浏览器会显示安全警告，这是正常的")
        
        uvicorn.run(app, **uvicorn_kwargs)
        
    except KeyboardInterrupt:
        print("\n\n👋 服务器已停止")
        return 0
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return 1

def main():
    parser = argparse.ArgumentParser(description='OCR护照识别系统启动脚本')
    parser.add_argument('--host', default='0.0.0.0', help='绑定主机地址 (默认: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8000, help='绑定端口 (默认: 8000)')
    parser.add_argument('--ssl', action='store_true', help='启用HTTPS')
    parser.add_argument('--ssl-keyfile', help='SSL私钥文件路径')
    parser.add_argument('--ssl-certfile', help='SSL证书文件路径')
    
    args = parser.parse_args()
    
    return start_server(
        host=args.host,
        port=args.port,
        ssl_mode=args.ssl,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile
    )

if __name__ == '__main__':
    sys.exit(main()) 