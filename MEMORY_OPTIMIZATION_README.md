# OCR服务内存优化解决方案

## 问题描述

您的OCR服务遇到了两个主要问题：

1. **内存不足错误**：`ResourceExhaustedError: Fail to alloc memory of 16307453952 size`
2. **OCR结果对象属性问题**：`OCRResult对象中没有rec_texts或rec_scores属性`

## 解决方案

### 1. 内存优化

#### 环境变量设置
```python
# 设置PaddlePaddle环境变量
os.environ['FLAGS_use_gpu'] = '0'  # 强制使用CPU
os.environ['FLAGS_use_mkldnn'] = '1'  # 启用MKL-DNN优化
os.environ['FLAGS_allocator_strategy'] = 'auto_growth'  # 内存自动增长
os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0.1'  # 限制GPU内存使用
os.environ['FLAGS_eager_delete_tensor_gb'] = '0.0'  # 立即删除张量
os.environ['FLAGS_fast_eager_deletion_mode'] = 'True'  # 快速删除模式
```

#### PaddleOCR参数优化
```python
_ocr_instance = PaddleOCR(
    lang='en',
    # use_angle_cls=False,  # 禁用角度分类以节省内存
    # use_gpu=False,  # 强制使用CPU
    # show_log=False,  # 减少日志输出
    # det_db_thresh=0.3,  # 降低检测阈值
    # det_db_box_thresh=0.6,  # 降低检测框阈值
    # det_db_unclip_ratio=1.5,  # 调整检测框比例
    # rec_char_dict_path=None,  # 使用默认字典
    # rec_batch_num=1,  # 批处理大小为1
    # det_limit_side_len=960,  # 限制图像边长
    # det_limit_type='max'  # 限制类型为最大值
)
```

#### 图像处理优化
- 限制图像最大尺寸为1024像素
- 自动缩放大图像
- 转换为RGB模式
- 启用垃圾回收

### 2. OCR结果处理优化

#### 支持多种结果格式
```python
# 处理字典格式
if isinstance(ocr_result, dict):
    if 'rec_texts' in ocr_result and 'rec_scores' in ocr_result:
        texts = ocr_result['rec_texts']
        scores = ocr_result['rec_scores']
        # 处理文本和置信度

# 处理列表格式
elif isinstance(ocr_result, list) and len(ocr_result) > 0:
    first_result = ocr_result[0]
    if isinstance(first_result, dict):
        # 处理列表中的字典
    elif isinstance(first_result, list):
        # 处理旧格式的列表
```

## 使用方法

### 1. 启动优化后的服务
```bash
# 启动内存优化的OCR服务
python ppocrv5_server.py --host 0.0.0.0 --port 8080 --workers 1
```

### 2. 测试服务
```bash
# 运行内存优化测试
python test_memory_optimized_server.py
```

### 3. 监控内存使用
```bash
# 查看内存使用情况
python -c "import psutil; print(f'内存使用: {psutil.virtual_memory().percent}%')"
```

## 配置说明

### 内存优化配置 (`memory_optimized_config.py`)
- `setup_memory_optimization()`: 设置内存优化环境变量
- `cleanup_memory()`: 清理内存
- `get_optimized_paddleocr_params()`: 获取优化的PaddleOCR参数

### 服务器配置
- 最大工作线程数：2
- 最大图像尺寸：1024像素
- 最大文件大小：10MB
- 启用垃圾回收

## 故障排除

### 1. 内存不足
- 检查系统可用内存
- 减少并发请求数
- 使用更小的图像
- 重启服务释放内存

### 2. OCR结果格式问题
- 检查PaddleOCR版本
- 查看日志中的结果格式
- 更新到最新版本的PaddleOCR

### 3. 服务启动失败
- 检查依赖安装
- 确认端口未被占用
- 查看错误日志

## 性能优化建议

1. **硬件优化**
   - 增加系统内存
   - 使用SSD存储
   - 优化CPU性能

2. **软件优化**
   - 定期重启服务
   - 监控内存使用
   - 使用负载均衡

3. **配置优化**
   - 调整图像处理参数
   - 优化线程池大小
   - 设置合理的超时时间

## 监控和维护

### 内存监控
```python
import psutil
import os

def monitor_memory():
    process = psutil.Process(os.getpid())
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"当前内存使用: {memory_mb:.2f} MB")
    
    if memory_mb > 1024:  # 超过1GB
        print("⚠️  内存使用过高，建议重启服务")
```

### 日志监控
```bash
# 查看服务日志
tail -f logs/ppocrv5_server.log

# 监控错误
grep "ERROR" logs/ppocrv5_server.log
```

## 更新日志

### v2.0.0 (2025-08-05)
- ✅ 修复内存不足问题
- ✅ 优化OCR结果处理
- ✅ 添加内存监控
- ✅ 支持多种结果格式
- ✅ 改进错误处理

## 技术支持

如果问题仍然存在，请：

1. 检查系统资源使用情况
2. 查看详细的错误日志
3. 尝试使用更小的测试图像
4. 重启服务并重新测试

---

**注意**：这些优化主要针对内存使用和结果处理问题。如果您的系统内存仍然不足，建议增加系统内存或使用更轻量级的OCR解决方案。 