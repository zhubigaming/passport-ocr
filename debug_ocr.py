#!/usr/bin/env python3
"""
调试OCR模型
测试OCR模型是否能正常识别文本
"""

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import io

def create_test_image_with_text():
    """创建一个包含清晰文本的测试图片"""
    # 创建一个白色背景的图片
    img = Image.new('RGB', (800, 400), color='white')
    draw = ImageDraw.Draw(img)
    
    # 尝试使用默认字体
    try:
        font = ImageFont.load_default()
    except:
        font = None
    
    # 添加一些测试文本
    texts = [
        "PASSPORT",
        "SURNAME / APELLIDOS",
        "GIVEN NAMES / NOMBRES",
        "NATIONALITY / NACIONALIDAD",
        "DATE OF BIRTH / FECHA DE NACIMIENTO",
        "PLACE OF BIRTH / LUGAR DE NACIMIENTO",
        "DATE OF ISSUE / FECHA DE EXPEDICION",
        "DATE OF EXPIRY / FECHA DE VENCIMIENTO",
        "AUTHORITY / AUTORIDAD",
        "MACHINE READABLE ZONE",
        "123456789"
    ]
    
    y_position = 30
    for text in texts:
        draw.text((50, y_position), text, fill='black', font=font)
        y_position += 30
    
    return img

def test_ocr_model():
    """测试OCR模型"""
    try:
        from paddleocr import PaddleOCR
        
        print("🚀 初始化PaddleOCR模型...")
        ocr = PaddleOCR(lang='en')
        print("✅ PaddleOCR模型初始化成功")
        
        # 创建测试图片
        print("🖼️  创建测试图片...")
        test_image = create_test_image_with_text()
        
        # 转换为numpy数组
        img_array = np.array(test_image)
        print(f"📏 图片尺寸: {img_array.shape}")
        
        # 执行OCR识别
        print("🔍 开始OCR识别...")
        result = ocr.ocr(img_array)
        
        # 输出原始结果
        print(f"🔍 原始OCR结果类型: {type(result)}")
        print(f"🔍 原始OCR结果长度: {len(result) if result else 0}")
        
        if result and len(result) > 0:
            print(f"🔍 第一个结果类型: {type(result[0])}")
            print(f"🔍 第一个结果长度: {len(result[0]) if result[0] else 0}")
            
            if result[0]:
                print(f"🔍 识别到 {len(result[0])} 行文本")
                
                for i, line in enumerate(result[0]):
                    if line and len(line) >= 2:
                        text_info = line[1]
                        if len(text_info) >= 2:
                            text = text_info[0]
                            confidence = text_info[1]
                            print(f"   行 {i+1}: '{text}' (置信度: {confidence:.2f})")
                        else:
                            print(f"   行 {i+1}: 格式异常 - {text_info}")
                    else:
                        print(f"   行 {i+1}: 格式异常 - {line}")
            else:
                print("⚠️  第一个结果为空")
        else:
            print("⚠️  OCR结果为空")
        
        return True
        
    except Exception as e:
        print(f"❌ OCR测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_with_simple_text():
    """测试简单的文本识别"""
    try:
        from paddleocr import PaddleOCR
        
        print("\n🧪 测试简单文本识别...")
        ocr = PaddleOCR(lang='en')
        
        # 创建一个非常简单的图片
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((20, 40), "TEST", fill='black')
        
        img_array = np.array(img)
        result = ocr.ocr(img_array)
        
        print(f"🔍 简单文本OCR结果: {result}")
        
        if result and result[0]:
            print("✅ 简单文本识别成功")
            for line in result[0]:
                if line and len(line) >= 2:
                    text_info = line[1]
                    if len(text_info) >= 2:
                        text = text_info[0]
                        confidence = text_info[1]
                        print(f"   文本: '{text}' (置信度: {confidence:.2f})")
        else:
            print("❌ 简单文本识别失败")
        
    except Exception as e:
        print(f"❌ 简单文本测试失败: {e}")

if __name__ == "__main__":
    print("🧪 开始OCR模型调试...")
    
    # 基本测试
    if test_ocr_model():
        print("\n✅ OCR模型测试成功！")
    else:
        print("\n❌ OCR模型测试失败！")
    
    # 简单文本测试
    test_with_simple_text() 