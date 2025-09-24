#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import os

def install_package(package_name, install_name=None):
    """安装Python包"""
    if install_name is None:
        install_name = package_name
    
    print(f"🔍 正在安装 {package_name}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", install_name])
        print(f"✅ {package_name} 安装成功")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {package_name} 安装失败: {e}")
        return False

def install_dependencies():
    """安装所有必要的依赖"""
    
    print("=== 依赖安装脚本 ===")
    print("正在安装PP-OCRv5系统所需的依赖包...")
    print()
    
    # 基础依赖
    basic_packages = [
        ("fastapi", "fastapi"),
        ("uvicorn", "uvicorn"),
        ("pillow", "pillow"),
        ("numpy", "numpy"),
        ("psutil", "psutil"),
        ("pydantic", "pydantic"),
        ("python-multipart", "python-multipart"),
        ("aiofiles", "aiofiles")
    ]
    
    # PaddlePaddle相关
    paddle_packages = [
        ("paddlepaddle", "paddlepaddle"),
        ("paddleocr", "paddleocr")
    ]
    
    print("📦 步骤1: 安装基础依赖...")
    success_count = 0
    for package, install_name in basic_packages:
        if install_package(package, install_name):
            success_count += 1
    
    print(f"\n📊 基础依赖安装结果: {success_count}/{len(basic_packages)} 成功")
    
    print("\n📦 步骤2: 安装PaddlePaddle相关依赖...")
    print("⚠️  注意: PaddlePaddle安装可能需要较长时间...")
    
    paddle_success = 0
    for package, install_name in paddle_packages:
        if install_package(package, install_name):
            paddle_success += 1
    
    print(f"\n📊 PaddlePaddle依赖安装结果: {paddle_success}/{len(paddle_packages)} 成功")
    
    # 总结
    total_success = success_count + paddle_success
    total_packages = len(basic_packages) + len(paddle_packages)
    
    print(f"\n📋 安装总结:")
    print(f"   总包数: {total_packages}")
    print(f"   成功安装: {total_success}")
    print(f"   失败: {total_packages - total_success}")
    
    if total_success == total_packages:
        print("\n🎉 所有依赖安装成功！")
        print("📝 现在可以启动PP-OCRv5服务器了")
        print("\n启动命令:")
        print("python ppocrv5_server_final.py --host 0.0.0.0 --port 8080")
    else:
        print("\n⚠️  部分依赖安装失败，请检查网络连接或手动安装")
        print("📝 建议:")
        print("   1. 检查网络连接")
        print("   2. 尝试使用国内镜像源")
        print("   3. 手动安装失败的包")

if __name__ == "__main__":
    install_dependencies() 