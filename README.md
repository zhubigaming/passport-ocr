# PP-OCRv5 护照识别系统

基于PP-OCRv5的护照识别系统，支持队列式图片上传和处理。

## 🚀 核心功能

### 1. PP-OCRv5 引擎
- 使用最新的PP-OCRv5识别引擎
- 更高的识别准确率和速度
- 支持多语言识别

### 2. 队列式处理
- 用户可以随时上传单张图片
- 系统自动将图片加入处理队列
- 后台依次处理队列中的图片
- 支持在处理过程中继续上传

### 3. 实时状态监控
- 显示当前处理队列大小
- 显示上传队列状态
- 显示活跃线程数
- 实时更新处理状态

## 📋 系统要求

- Python 3.8+
- PaddlePaddle 2.5.2
- PaddleOCR 2.7.0+

## 🛠️ 安装

### 方法1：使用官方安装脚本（推荐）
```bash
# 运行官方安装脚本（自动安装所有依赖）
python install_paddleocr.py
```

### 方法2：手动安装
1. **安装基础依赖**
```bash
pip install -r requirements.txt
```

2. **安装PaddleOCR（官方推荐）**
```bash
# 安装PaddlePaddle 3.0.0（CPU版本）
python -m pip install paddlepaddle==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
## 📖 使用说明

> **注意**: 本项目使用PaddleOCR官方推荐的安装方式。详细文档请参考：[PaddleOCR官方文档](http://www.paddleocr.ai/main/quick_start.html)

# 安装PaddleOCR
pip install paddleocr
```


> **注意**: `requirements.txt`中不包含OCR相关依赖，请使用专门的安装脚本或手动安装。

## 🚀 启动服务

### 1. 生成SSL证书（首次使用）
```bash
python generate_ssl_cert.py
```

### 2. 启动OCR服务（仅需一个命令，SSL模式）
```bash
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080
```

> **注意**：
> - 必须先生成SSL证书，否则无法以HTTPS方式访问
> - 访问地址：https://localhost:8000
> - 首次访问HTTPS可能需要浏览器接受自签名证书
> - 仅需这一个命令即可完成OCR服务启动

## 🌐 访问地址

### HTTPS模式（推荐，支持摄像头）
- **网页界面**: https://localhost:8000
- **API文档**: https://localhost:8000/docs
- **PP-OCRv5服务**: http://localhost:8080
- **PP-OCRv5文档**: http://localhost:8080/docs

### HTTP模式（仅用于测试）
- **网页界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **PP-OCRv5服务**: http://localhost:8080
- **PP-OCRv5文档**: http://localhost:8080/docs

> **重要提示**: 
> - 摄像头功能需要HTTPS环境，请使用 `--ssl` 参数启动服务
> - 推荐使用HTTPS模式以获得完整功能
> - 首次访问HTTPS可能需要接受自签名证书

## ⚡ 快速启动指南

### 首次使用（推荐SSL模式）
```bash
# 1. 生成SSL证书
python generate_ssl_cert.py

# 2. 启动PP-OCRv5服务器
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080

# 3. 启动API服务器（SSL模式）
python start_server.py --host 0.0.0.0 --port 8000 --ssl

# 4. 访问网页界面
# 打开浏览器访问: https://localhost:8000
```

### 后续使用
```bash
# 直接启动两个服务
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080
python start_server.py --host 0.0.0.0 --port 8000 --ssl
```


### 1. 上传图片
1. 点击"上传图片"按钮
2. 选择单张图片文件
3. 系统自动将图片加入处理队列
4. 可以立即继续上传其他图片

### 2. 查看队列状态
- 页面顶部显示当前队列状态
- 包括处理队列、上传队列、活跃线程数
- 实时更新状态信息

### 3. 查看处理结果
- 在主页查看所有识别记录
- 使用日期筛选功能
- 支持编辑和删除记录

## 📁 服务器文件说明


## 🔧 API接口

### 1. 上传图片
```
POST /api/ocr/upload-photo
Content-Type: multipart/form-data

file: 图片文件
```

响应示例：
```json
{
    "status": "success",
    "message": "图片上传成功！已加入处理队列...",
    "record_id": 123,
    "task_id": "abc123",
    "image_url": "/uploads/photo_20240101_120000_123456.jpg",
    "queue_position": 5
}
```

### 2. 检查服务状态
```
GET /api/ocr/status/check
```

响应示例：
```json
{
    "ocr_service": "available",
    "upload_queue_size": 2,
    "ocr_queue_size": 5,
    "active_threads": 3,
    "max_upload_queue": 100,
    "max_thread_pool": 10
}
```

### 3. 单张图片OCR识别
```
POST /ocr
Content-Type: application/json

{
    "file": "base64编码的图片数据",
    "fileType": 1
}
```

### 4. 批量图片OCR识别
```
POST /batch_ocr
Content-Type: application/json

{
    "files": ["base64编码的图片数据1", "base64编码的图片数据2", ...]
}
```

## 📊 队列管理

### 队列限制
- **上传队列**: 最大100个任务
- **OCR队列**: 最大50个任务


## 📊 功能特性

### 1. 队列式处理
- 支持随时上传单张图片
- 自动排队处理
- 实时状态更新

### 2. 数据管理
- 自动保存识别结果到数据库
- 支持记录查询和筛选
- 支持记录编辑和删除

### 3. 图片管理
- 自动生成缩略图
- 支持图片预览
- 支持图片下载

### 4. 统计功能
- 今日识别统计
- 按证件类型统计
- 总识别数量统计

## 🔍 监控功能

### 1. 队列监控
- 实时显示队列大小
- 监控队列处理速度
- 预警队列满载

### 2. 性能监控
- 处理时间统计
- 成功率统计
- 错误率统计

### 3. 资源监控
- CPU使用率
- 内存使用率
- 磁盘使用率

## 🐛 故障排除

### 1. PP-OCRv5启动失败
```bash
# 检查PaddleOCR安装
python -c "import paddleocr; print('PaddleOCR安装成功')"

# 重新安装PaddleOCR
pip uninstall paddleocr
pip install paddleocr>=2.7.0
```

### 2. 队列满载
```bash
# 检查队列状态
curl http://localhost:8000/api/ocr/status/check

# 重启服务
python start_ppocrv5_services.py
```

### 3. 数据库连接失败
- 检查数据库服务是否启动
- 验证数据库配置信息
- 确保数据库用户有足够权限

### 4. 图片上传失败
- 检查图片格式是否支持
- 验证图片大小是否超限
- 确认网络连接正常

### 5. 摄像头无法使用
```bash
# 检查是否使用HTTPS
# 确保使用 --ssl 参数启动服务
python start_ppocrv5_services.py --ssl

# 如果证书有问题，重新生成
python generate_ssl_cert.py
```

### 6. SSL证书问题
```bash
# 生成SSL证书
python generate_ssl_cert.py

# 检查证书文件
ls -la *.pem

# 如果证书过期，重新生成
rm *.pem
python generate_ssl_cert.py

# 测试SSL功能
python test_ssl.py
```

### 7. PaddleOCR初始化失败
```bash
# 检查PaddleOCR安装
python test_paddleocr.py

# 测试PaddleOCR参数
python test_paddleocr_params.py

# 重新安装PaddleOCR（官方推荐）
pip uninstall paddleocr paddlepaddle
python -m pip install paddlepaddle==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
pip install paddleocr

# 测试安装
python test_paddleocr.py
```

## 📝 配置说明

### 环境变量
```bash
# OCR服务地址
OCR_SERVICE_URL=http://localhost:8080/ocr

# 队列配置
MAX_UPLOAD_QUEUE=100
MAX_OCR_QUEUE=50
UPLOAD_THREAD_POOL_SIZE=10
```

## 🚀 性能优化

### 1. 队列优化
- 动态调整队列大小
- 智能任务调度
- 优先级队列

### 2. 处理优化
- 并行处理多个任务
- 缓存识别结果
- 压缩图片传输

### 3. 存储优化
- 自动清理临时文件
- 定期清理旧记录
- 数据库索引优化

## 📈 扩展功能

### 1. 批量上传
- 支持多文件选择
- 批量加入队列
- 批量状态查询

### 2. 优先级处理
- VIP用户优先处理
- 紧急任务插队
- 智能任务调度

### 3. 分布式处理
- 多服务器部署
- 负载均衡
- 故障转移

## 📝 更新日志

### v2.0.0 (2024-01-XX)
- ✨ 升级到PP-OCRv5引擎
- ✨ 支持队列式图片处理
- ✨ 实时状态监控
- ✨ 优化识别性能
- 🐛 修复已知问题

## 🤝 贡献

欢迎提交Issue和Pull Request！

## �� 许可证

MIT License 

---

您的服务报了**Segmentation fault (core dumped)**，并且是PaddlePaddle底层C++报错。这种情况常见于：

- **内存不足**（最常见，尤其是CPU推理大模型时）
- **PaddlePaddle与系统/依赖不兼容**
- **模型文件损坏或下载不完整**
- **CPU环境下模型/算子不支持或bug**

---

## 解决步骤

### 1. **极限内存优化（推荐）**
- **只用英文模型**，不要多语言。
- **限制线程池为1**（你现在是4，建议降到1）。
- **减少uvicorn进程数**（`--workers 1`）。
- **重启机器，释放内存**。

#### 修改`ppocrv5_server_final.py`线程池为1
```python
_executor = ThreadPoolExecutor(max_workers=1)
```
并确保启动命令只用1个worker：
```bash
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080
```

---

### 2. **彻底清理模型缓存，重新下载模型**
有时模型文件损坏也会导致Segmentation fault。请删除`/root/.paddlex/official_models`目录下的所有内容，然后重启服务让其自动重新下载。

```bash
rm -rf /root/.paddlex/official_models/*
```

---

### 3. **检查PaddlePaddle版本**
- 建议使用 PaddlePaddle 2.5.x 或 2.6.x 的CPU版本。
- 不要用GPU版（你现在是CPU环境）。

---

### 4. **降级PaddleOCR模型复杂度**
- 可以尝试用`det_model_dir`和`rec_model_dir`指定更小的模型（如`en_PP-OCRv3`），但一般只用英文模型已是最小化。

---

### 5. **系统资源监控**
- 启动服务时用`htop`或`top`监控内存，看看是不是内存瞬间被吃光。

---

## 总结

1. **先把线程池和进程数都降到1**，重启服务。
2. **清空模型缓存，重新下载模型**。
3. **如果还是Segmentation fault，贴出`htop`/`top`截图和`pip show paddlepaddle paddleocr`信息**，我帮你进一步分析。

---


# PP-OCRv5 离线部署指南

##  概述

本指南详细说明如何将 PP-OCRv5 系统部署到不联网的机器上，包括环境打包、模型压缩和离线部署步骤。

## 🗂️ 离线部署包内容

```
paddleocr_offline_deploy.tar.gz
├── ocr_env.tar.gz              # Anaconda 环境包
├── paddleocr_models.tar.gz     # PaddleOCR 模型文件
├── ppocrv5_server_final.py     # OCR 服务代码
├── ocr_environment.yml         # 环境配置文件
├── ocr_packages.txt           # 包列表
└── README_OFFLINE_DEPLOY.md   # 部署说明
```

##  离线部署步骤

### 步骤1：解压部署包

```bash
# 解压部署包
tar -xzf paddleocr_offline_deploy.tar.gz
cd offline_deploy

# 查看文件
ls -la
```

### 步骤2：部署 Anaconda 环境

#### 方法1：使用 conda-pack 打包的环境（推荐）

```bash
# 创建环境目录
mkdir -p /home/hujinchaopk/anaconda3/envs/ocr

# 解压环境
cd /home/hujinchaopk/anaconda3/envs/ocr
tar -xzf /path/to/ocr_env.tar.gz

# 激活环境
conda activate ocr

# 验证环境
python -c "import paddleocr; print('PaddleOCR 环境部署成功！')"
```

#### 方法2：使用环境配置文件

```bash
# 创建环境
conda env create -f ocr_environment.yml

# 激活环境
conda activate ocr
```

### 步骤3：部署模型文件

```bash
# 创建模型目录
sudo mkdir -p /root/.paddlex/

# 解压模型文件
sudo tar -xzf paddleocr_models.tar.gz -C /root/.paddlex/

# 设置权限
sudo chmod -R 644 /root/.paddlex/official_models/
sudo chmod -R +X /root/.paddlex/official_models/
sudo chmod 755 /root/.paddlex/
sudo chmod 755 /root/.paddlex/official_models/

# 验证模型文件
ls -la /root/.paddlex/official_models/
```

### 步骤4：部署代码文件

```bash
# 复制代码文件到项目目录
cp ppocrv5_server_final.py /path/to/your/project/

# 设置执行权限
chmod +x /path/to/your/project/ppocrv5_server_final.py
```

### 步骤5：启动服务

```bash
# 激活环境
conda activate ocr

# 启动 OCR 服务
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080
```

### 步骤6：验证部署

```bash
# 测试服务健康状态
curl http://localhost:8080/health

# 测试根路径
curl http://localhost:8080/

# 查看服务日志
# 应该看到类似以下输出：
# 🚀 开始处理OCR请求: image.jpg
# ⏱️  文件读取耗时: 0.001秒
# ⏱️  OCR识别耗时: 2.345秒
# ⏱️  总处理耗时: 2.469秒
```

## 🔧 自动化部署脚本

### 创建部署脚本

```bash
cat > deploy_offline.sh << 'EOF'
#!/bin/bash

echo "🚀 开始离线部署 PP-OCRv5..."

# 配置变量
DEPLOY_DIR="/tmp/offline_deploy"
ENV_NAME="ocr"
ANACONDA_PATH="/home/hujinchaopk/anaconda3"

# 检查部署包
if [ ! -f "paddleocr_offline_deploy.tar.gz" ]; then
    echo "❌ 部署包不存在: paddleocr_offline_deploy.tar.gz"
    exit 1
fi

# 解压部署包
echo " 解压部署包..."
tar -xzf paddleocr_offline_deploy.tar.gz
cd offline_deploy

# 部署环境
echo "🔧 部署 Anaconda 环境..."
mkdir -p $ANACONDA_PATH/envs/$ENV_NAME
cd $ANACONDA_PATH/envs/$ENV_NAME
tar -xzf /tmp/offline_deploy/ocr_env.tar.gz
echo "✅ 环境部署完成"

# 部署模型
echo " 部署模型文件..."
sudo mkdir -p /root/.paddlex/
sudo tar -xzf /tmp/offline_deploy/paddleocr_models.tar.gz -C /root/.paddlex/
sudo chmod -R 644 /root/.paddlex/official_models/
sudo chmod -R +X /root/.paddlex/official_models/
sudo chmod 755 /root/.paddlex/
sudo chmod 755 /root/.paddlex/official_models/
echo "✅ 模型部署完成"

# 部署代码
echo " 部署代码文件..."
cp /tmp/offline_deploy/ppocrv5_server_final.py /opt/ppocr/
chmod +x /opt/ppocr/ppocrv5_server_final.py
echo "✅ 代码部署完成"

# 验证部署
echo "🧪 验证部署..."
source $ANACONDA_PATH/bin/activate $ENV_NAME
python -c "
from paddleocr import PaddleOCR
try:
    ocr = PaddleOCR(device='cpu')
    print('✅ 模型加载成功！')
except Exception as e:
    print(f'❌ 模型加载失败: {e}')
"

echo " 离线部署完成！"
echo "💡 启动命令: conda activate ocr && python /opt/ppocr/ppocrv5_server_final.py --host 0.0.0.0 --port 8080"
EOF

chmod +x deploy_offline.sh
./deploy_offline.sh
```

## 🔍 故障排除

### 1. 环境激活失败

```bash
# 检查环境路径
conda info --envs

# 重新初始化 conda
source /home/hujinchaopk/anaconda3/bin/activate
conda init bash
```

### 2. 模型加载失败

```bash
# 检查模型文件
ls -la /root/.paddlex/official_models/

# 检查权限
sudo chown -R $USER:$USER /root/.paddlex/official_models/

# 设置环境变量
export PADDLE_HOME=/root/.paddlex
```

### 3. 服务启动失败

```bash
# 检查端口占用
netstat -tlnp | grep 8080

# 检查 Python 依赖
python -c "import paddleocr, fastapi, uvicorn; print('依赖正常')"

# 查看详细错误日志
python ppocrv5_server_final.py --host 0.0.0.0 --port 8080 2>&1 | tee ocr.log
```

### 4. 内存不足

```bash
# 检查内存使用
free -h

# 优化内存使用
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

## 📊 性能优化

### 1. 内存优化

```bash
# 设置环境变量
export FLAGS_use_gpu=False
export FLAGS_use_mkldnn=False
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
```

### 2. CPU 优化

```bash
# 限制 CPU 使用
export FLAGS_cpu_math_library_num_threads=1
```

### 3. 模型优化

```python
# 在代码中设置
ocr = PaddleOCR(
    device='cpu',
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    show_log=False
)
```

##  部署检查清单

- [ ] Anaconda 环境解压成功
- [ ] 环境激活正常
- [ ] 模型文件解压到正确位置
- [ ] 模型文件权限设置正确
- [ ] 代码文件部署完成
- [ ] 服务启动成功
- [ ] 健康检查通过
- [ ] OCR 识别测试通过

## 🆘 获取帮助

如果遇到问题，请检查：

1. **日志文件**：查看服务启动和运行日志
2. **系统资源**：检查内存、CPU 使用情况
3. **文件权限**：确保模型文件可读
4. **网络配置**：确保端口未被占用

---

**注意**：离线部署需要确保目标机器的系统架构和 Python 版本与源机器兼容。

## 🔌 API 接口使用指南

### 护照数据管理接口

#### 1. 获取今日护照数据

**接口地址**: `POST /api/passport/today`

**功能**: 读取今日数据库中类型为护照的所有数据

**请求方式**: POST

**请求示例**:

```bash
# 使用 curl（跳过SSL验证）
curl -X POST https://localhost:8000/api/passport/today -k

# 使用 curl（HTTP方式）
curl -X POST http://localhost:8000/api/passport/today

# 使用 wget
wget --no-check-certificate -O - --post-data='' https://localhost:8000/api/passport/today
```

**返回格式**:
```json
{
  "success": true,
  "count": 5,
  "date": "2024-08-08",
  "records": [
    {
      "id": 123,
      "passport_no": "E12345678",
      "name1": "张三",
      "name2": "ZHANG SAN",
      "gender": "男",
      "birth_date": "1990-01-01",
      "expiry_date": "2030-01-01",
      "country_name_cn": "中国",
      "doc_type_cn": "护照",
      "visa_no": "V123456",
      "visa_date": "2024-08-01",
      "passport_type": "普通护照",
      "image_path": "/uploads/123.jpg",
      "created_at": "2024-08-08T10:30:00",
      "updated_at": "2024-08-08T10:30:00"
    }
  ]
}
```

#### 2. 更新签证信息

**接口地址**: `POST /api/passport/{record_id}/visa`

**功能**: 通过数据ID写入签证号码和签证日期

**请求方式**: POST

**路径参数**:
- `record_id`: 记录ID（整数）

**请求体格式**:
```json
{
  "visa_no": "V123456789",
  "visa_date": "2024-08-01"
}
```

**请求示例**:

```bash
# 使用 curl（跳过SSL验证）
curl -X POST https://localhost:8000/api/passport/123/visa \
  -H "Content-Type: application/json" \
  -d '{
    "visa_no": "V987654321",
    "visa_date": "2024-08-15"
  }' \
  -k

# 使用 curl（HTTP方式）
curl -X POST http://localhost:8000/api/passport/123/visa \
  -H "Content-Type: application/json" \
  -d '{
    "visa_no": "V987654321",
    "visa_date": "2024-08-15"
  }'

# 使用 wget
wget --no-check-certificate -O - \
  --post-data='{"visa_no": "V987654321", "visa_date": "2024-08-15"}' \
  --header='Content-Type: application/json' \
  https://localhost:8000/api/passport/123/visa
```

**返回格式**:
```json
{
  "success": true,
  "message": "签证信息更新成功",
  "record_id": 123,
  "updated_fields": ["visa_no", "visa_date"]
}
```

### 接口特点

#### 数据过滤
- 只返回今日创建的记录
- 只返回文档类型包含"护照"的记录
- 按创建时间倒序排列

#### 日期处理
- 自动处理日期格式转换
- 支持空值处理
- 返回 ISO 格式的日期字符串

#### 错误处理
- 完整的异常捕获和日志记录
- 详细的错误信息返回
- 数据库事务回滚

#### 数据验证
- 检查记录是否存在
- 验证必填字段
- 处理空字符串和 NULL 值

### 常见问题解决

#### SSL证书问题
如果遇到SSL证书验证错误，可以使用以下方法：

```bash
# 方法1：跳过SSL验证（推荐用于测试）
curl -k https://localhost:8000/api/passport/today

# 方法2：使用HTTP（如果服务器支持）
curl http://localhost:8000/api/passport/today

# 方法3：使用wget
wget --no-check-certificate -O - https://localhost:8000/api/passport/today
```

#### 网络连接问题
```bash
# 检查服务是否运行
netstat -tlnp | grep 8000

# 检查防火墙
sudo ufw status

# 测试本地连接
curl -v http://localhost:8000/health
```

#### 数据库连接问题
```bash
# 检查数据库服务
sudo systemctl status mysql

# 检查数据库连接
mysql -u username -p -h localhost
``` 