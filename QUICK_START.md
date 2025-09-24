# PP-OCRv5 快速启动指南

## 🚨 段错误问题解决方案

如果遇到 `Segmentation fault` 错误，请按以下步骤解决：

### 1. 安装依赖包

```bash
# 安装基础依赖
pip install fastapi uvicorn pillow numpy psutil pydantic python-multipart aiofiles

# 安装PaddlePaddle（CPU版本）
pip install paddlepaddle

# 安装PaddleOCR
pip install paddleocr
```

### 2. 环境变量设置

在启动服务器前，设置以下环境变量：

```bash
# Windows
set FLAGS_use_gpu=False
set FLAGS_use_mkldnn=False
set OMP_NUM_THREADS=1
set MKL_NUM_THREADS=1

# Linux/Mac
export FLAGS_use_gpu=False
export FLAGS_use_mkldnn=False
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

### 3. 启动服务器

```bash
# 生成SSL证书（首次使用）
python generate_ssl_cert.py

# 启动PP-OCRv5服务器
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080
```

### 4. 测试服务器

访问以下地址测试：
- 健康检查: http://localhost:8080/health
- API文档: http://localhost:8080/docs

## 🔧 故障排除

### 内存不足问题
- 关闭其他程序释放内存
- 增加系统内存
- 使用更小的图片进行测试

### 模型加载失败
- 检查网络连接
- 重新安装PaddleOCR: `pip install --upgrade paddleocr`
- 清除缓存: `pip cache purge`

### 段错误持续出现
- 重启系统
- 检查Python版本兼容性
- 使用虚拟环境隔离依赖

## 📞 技术支持

如果问题仍然存在，请提供以下信息：
1. 操作系统版本
2. Python版本
3. 内存大小
4. 完整的错误日志 