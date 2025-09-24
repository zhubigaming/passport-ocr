#!/usr/bin/env python3
"""
快速诊断OCR问题
检查OCR模型和图片处理是否正常
"""

import requests
import base64
import json
from PIL import Image, ImageDraw, ImageFont
import io

def create_simple_test_image():
    """创建一个非常简单的测试图片"""
    img = Image.new('RGB', (300, 150), color='white')
    draw = ImageDraw.Draw(img)
    
    # 添加一些简单的文本
    draw.text((50, 50), "HELLO", fill='black')
    draw.text((50, 80), "WORLD", fill='black')
    draw.text((50, 110), "12345", fill='black')
    
    return img

def test_ocr_server_directly():
    """直接测试OCR服务器"""
    print("🧪 直接测试OCR服务器...")
    
    # 创建测试图片
    test_image = create_simple_test_image()
    
    # 转换为base64
    img_byte_arr = io.BytesIO()
    test_image.save(img_byte_arr, format='PNG')
    img_byte_arr = img_byte_arr.getvalue()
    image_base64 = base64.b64encode(img_byte_arr).decode('utf-8')
    
    # 发送OCR请求
    ocr_data = {
        "file": image_base64,
        "fileType": 1
    }
    
    try:
        response = requests.post("http://localhost:8080/ocr", json=ocr_data, timeout=30)
        
        print(f"📡 服务器响应状态: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ OCR请求成功")
            print(f"📋 响应内容: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            # 检查结果
            if 'result' in result:
                ocr_result = result['result']
                if 'ocrResults' in ocr_result:
                    ocr_results = ocr_result['ocrResults']
                    if ocr_results and len(ocr_results) > 0:
                        rec_texts = ocr_results[0].get('rec_texts', [])
                        print(f"🔍 识别到 {len(rec_texts)} 个文本片段")
                        
                        if rec_texts:
                            print("📝 识别的文本:")
                            for i, text_item in enumerate(rec_texts):
                                if isinstance(text_item, dict):
                                    text = text_item.get('text', '')
                                    confidence = text_item.get('confidence', 0)
                                    print(f"   {i+1}. '{text}' (置信度: {confidence:.2f})")
                                else:
                                    print(f"   {i+1}. '{text_item}'")
                        else:
                            print("⚠️  未识别到任何文本")
                    else:
                        print("⚠️  ocrResults为空")
                else:
                    print(f"⚠️  未找到ocrResults字段")
            else:
                print(f"⚠️  未找到result字段")
        else:
            print(f"❌ OCR请求失败: {response.status_code}")
            print(f"错误信息: {response.text}")
            
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_health_check():
    """测试健康检查"""
    print("\n🏥 测试健康检查...")
    
    try:
        response = requests.get("http://localhost:8080/health")
        print(f"📡 健康检查状态: {response.status_code}")
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"📋 健康检查响应: {json.dumps(health_data, indent=2)}")
            
            if health_data.get('status') == 'healthy':
                print("✅ 服务器健康状态正常")
            else:
                print("⚠️  服务器健康状态异常")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")

def test_server_info():
    """测试服务器信息"""
    print("\nℹ️  测试服务器信息...")
    
    try:
        response = requests.get("http://localhost:8080/")
        print(f"📡 服务器信息状态: {response.status_code}")
        
        if response.status_code == 200:
            info_data = response.json()
            print(f"📋 服务器信息: {json.dumps(info_data, indent=2)}")
        else:
            print(f"❌ 获取服务器信息失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 获取服务器信息异常: {e}")

if __name__ == "__main__":
    print("🔍 开始OCR问题诊断...")
    
    # 1. 测试健康检查
    test_health_check()
    
    # 2. 测试服务器信息
    test_server_info()
    
    # 3. 测试OCR识别
    test_ocr_server_directly()
    
    print("\n🎯 诊断完成！") 