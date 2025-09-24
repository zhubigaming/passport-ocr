#!/usr/bin/env python3
"""
最简版 OCR 服务（Python API 版本）
- 启动时仅加载一次 PaddleOCR 模型（按用户给定参数：关闭三个可选模块）
- 仅提供 /ocr 接口：接收图片，调用 ocr.predict 处理
- 将结果保存为 JSON 到临时目录，并读回内容作为返回值
"""

import os
import json
import tempfile
import time
from pathlib import Path
from typing import List, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 依据环境变量配置设备，默认为 cpu；可设置 PPOCR_DEVICE=gpu 或 gpu:0
PPOCR_DEVICE = os.environ.get("PPOCR_DEVICE", "cpu")

# 延迟导入以加快模块加载提示
from paddleocr import PaddleOCR

# 全局仅初始化一次模型
# 关闭文档方向分类 / 文本图像矫正 / 文本行方向分类，等同你提供的示例
if PPOCR_DEVICE.lower().startswith("gpu"):
    # 使用 GPU（若环境不具备，请改为 CPU 或设置 PPOCR_DEVICE=cpu）
    ocr = PaddleOCR(
        device="gpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )
else:
    # 使用 CPU
    ocr = PaddleOCR(
        device="cpu",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        # 指定本地模型路径（离线部署时使用）
        # det_model_dir="/path/to/offline/models/PP-OCRv5_server_det",
        # rec_model_dir="/path/to/offline/models/PP-OCRv5_server_rec",
    )

app = FastAPI(title="Minimal PP-OCRv5 Service (Python API)", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)) -> Any:
    start_time = time.time()
    print(f"🚀 开始处理OCR请求: {file.filename}")
    print(f"📥 收到文件上传请求:")
    print(f"   文件名: {file.filename}")
    print(f"   内容类型: {file.content_type}")
    print(f"   文件大小: {file.size if hasattr(file, 'size') else '未知'}")
    
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="只支持图片文件")
    
    # 检查文件大小限制（可选）
    max_file_size = 10 * 1024 * 1024  # 10MB
    if hasattr(file, 'size') and file.size and file.size > max_file_size:
        raise HTTPException(status_code=400, detail=f"文件大小超过限制: {file.size} > {max_file_size}")

    # 读取图片数据到内存
    read_start = time.time()
    data = await file.read()
    read_time = time.time() - read_start
    print(f"📏 文件大小: {len(data)} 字节")
    print(f"⏱️  文件读取耗时: {read_time:.3f}秒")
    
    # 使用 BytesIO 直接在内存中处理图片
    from io import BytesIO
    from PIL import Image
    import numpy as np
    
    try:
        # 检查数据是否为空
        if len(data) == 0:
            raise ValueError("上传的文件数据为空")
        
        print(f"🔍 数据前20字节: {data[:20].hex()}")
        
        # 从内存数据创建 PIL Image
        try:
            image = Image.open(BytesIO(data))
            print(f"🖼️  图片信息: {image.size} {image.mode}")
        except Exception as img_error:
            print(f"❌ PIL 无法识别图片: {str(img_error)}")
            # 尝试保存到临时文件进行调试
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()
                print(f"💾 调试：文件已保存到 {tmp_file.name}")
                try:
                    # 尝试从文件读取
                    image = Image.open(tmp_file.name)
                    print(f"✅ 从文件读取成功: {image.size} {image.mode}")
                except Exception as file_error:
                    print(f"❌ 从文件读取也失败: {str(file_error)}")
                    raise ValueError(f"无法识别图片格式: {str(img_error)}")
                finally:
                    # 清理临时文件
                    import os
                    os.unlink(tmp_file.name)
        
        # 转换为 RGB 模式（如果需要）
        if image.mode != 'RGB':
            image = image.convert('RGB')
            print(f"🔄 转换为 RGB 模式")
        
        # 转换为 numpy 数组
        image_array = np.array(image)
        print(f"🔍 开始OCR识别 (内存处理)")
        
        # 直接使用 numpy 数组进行预测
        ocr_start = time.time()
        try:
            results = ocr.predict(image_array)
            ocr_time = time.time() - ocr_start
            print(f"⏱️  OCR识别耗时: {ocr_time:.3f}秒")
        except Exception as ocr_error:
            print(f"❌ OCR 预测失败: {str(ocr_error)}")
            # 尝试使用文件路径方式
            print("🔄 尝试使用文件路径方式...")
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                tmp_file.write(data)
                tmp_file.flush()
                try:
                    results = ocr.predict(tmp_file.name)
                    print("✅ 文件路径方式成功")
                except Exception as file_ocr_error:
                    print(f"❌ 文件路径方式也失败: {str(file_ocr_error)}")
                    raise ValueError(f"OCR 处理失败: {str(ocr_error)}")
                finally:
                    import os
                    os.unlink(tmp_file.name)
        
        # 打印识别结果
        print(f"\n🔍 OCR 识别结果 (文件: {file.filename}):")
        print("=" * 50)
        
        for idx, res in enumerate(results):
            print(f"📄 第 {idx + 1} 个结果:")
            res.print()  # 打印详细结果
            print("-" * 30)

        # 使用临时目录保存输出结果
        save_start = time.time()
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "output"
            out_dir.mkdir(parents=True, exist_ok=True)
        
            # 将结果保存到临时目录，并读回 JSON 内容
            saved_json_files: List[str] = []
            saved_img_files: List[str] = []
            aggregated: List[Any] = []

            for idx, res in enumerate(results):
                # 保存可视化结果图片与 JSON
                res.save_to_img(str(out_dir))
                res.save_to_json(str(out_dir))

            # 读取保存的 JSON 文件
            for p in sorted(out_dir.glob("*.json")):
                try:
                    aggregated.append(json.loads(p.read_text(encoding="utf-8")))
                    saved_json_files.append(str(p))
                except Exception:
                    continue

            # 收集保存的图片文件（若有）
            for p in sorted(out_dir.glob("*.png")):
                if p.is_file():
                    saved_img_files.append(str(p))

        save_time = time.time() - save_start
        total_time = time.time() - start_time
        
        print(f"⏱️  结果保存耗时: {save_time:.3f}秒")
        print(f"⏱️  总处理耗时: {total_time:.3f}秒")
        print(f"✅ OCR处理完成")

        return {
            "status": "success",
            "results": aggregated,  # 直接返回 JSON 解析后的结构
            "saved_json_files": saved_json_files,
            "saved_image_files": saved_img_files,
            "timing": {
                "file_read_time": round(read_time, 3),
                "ocr_time": round(ocr_time, 3),
                "save_time": round(save_time, 3),
                "total_time": round(total_time, 3)
            }
        }
        
    except Exception as e:
        total_time = time.time() - start_time
        print(f"❌ 图片处理失败: {str(e)}")
        print(f"⏱️  失败前耗时: {total_time:.3f}秒")
        raise HTTPException(status_code=500, detail=f"图片处理失败: {str(e)}")

@app.get("/")
async def root():
    """根路径 - 服务状态检查"""
    return {
        "message": "PP-OCRv5 服务运行中",
        "version": "1.0.0",
        "endpoints": {
            "ocr": "POST /ocr - 上传图片进行OCR识别",
            "docs": "GET /docs - API文档"
        },
        "device": PPOCR_DEVICE
    }

@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "PP-OCRv5"}

if __name__ == "__main__":
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run("ppocrv5_server_final:app", host=host, port=port, workers=1, log_level="info") 