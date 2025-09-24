#!/bin/bash
# create_complete_package.sh

echo "📦 创建包含 PP-OCR 模型的完整 Docker 离线部署包..."

# 创建临时目录
PACKAGE_DIR="paddleocr_complete_package_$(date +%Y%m%d_%H%M%S)"
mkdir -p $PACKAGE_DIR

# 复制必要文件
cp Dockerfile $PACKAGE_DIR/
cp requirements.txt $PACKAGE_DIR/
cp docker-compose.yml $PACKAGE_DIR/
cp ppocrv5_server_final.py $PACKAGE_DIR/
cp start_server.py $PACKAGE_DIR/
cp api_server.py $PACKAGE_DIR/
cp config.py $PACKAGE_DIR/
cp check_data.py $PACKAGE_DIR/
cp build_docker.sh $PACKAGE_DIR/
cp start_services.sh $PACKAGE_DIR/
cp stop_services.sh $PACKAGE_DIR/

# 复制 PP-OCR 模型文件
echo "📋 步骤1: 复制 PP-OCR 模型文件..."

# 检查模型目录
MODEL_SOURCE="/root/.paddlex/official_models"
if [ -d "$MODEL_SOURCE" ]; then
    echo "✅ 找到模型目录: $MODEL_SOURCE"
    
    # 创建模型目录
    mkdir -p $PACKAGE_DIR/models
    
    # 复制模型文件
    cp -r $MODEL_SOURCE/* $PACKAGE_DIR/models/
    
    # 显示模型文件信息
    echo "📊 模型文件信息:"
    find $PACKAGE_DIR/models -type f -name "*.pdmodel" -o -name "*.pdiparams" | head -10
    echo "   模型文件总数: $(find $PACKAGE_DIR/models -type f | wc -l)"
    echo "   模型目录大小: $(du -sh $PACKAGE_DIR/models | cut -f1)"
else
    echo "⚠️  模型目录不存在: $MODEL_SOURCE"
    echo "   请先运行一次 OCR 服务以下载模型"
    echo "   python ppocrv5_server_final.py --host 0.0.0.0 --port 8080"
    exit 1
fi

# 复制其他目录
echo "📋 步骤2: 复制其他必要文件..."

if [ -d "ssl" ]; then
    cp -r ssl $PACKAGE_DIR/
    echo "✅ SSL 证书已包含"
fi

if [ -d "data" ]; then
    cp -r data $PACKAGE_DIR/
    echo "✅ 数据文件已包含"
fi

if [ -d "templates" ]; then
    cp -r templates $PACKAGE_DIR/
    echo "✅ 模板文件已包含"
fi

if [ -d "static" ]; then
    cp -r static $PACKAGE_DIR/
    echo "✅ 静态文件已包含"
fi

# 创建模型验证脚本
echo "📋 步骤3: 创建模型验证脚本..."

cat > $PACKAGE_DIR/verify_models.sh << 'EOF'
#!/bin/bash
echo "🔍 验证 PP-OCR 模型文件..."

MODEL_DIR="/root/.paddlex/official_models"

# 检查模型目录是否存在
if [ ! -d "$MODEL_DIR" ]; then
    echo "❌ 模型目录不存在: $MODEL_DIR"
    exit 1
fi

# 检查关键模型文件
REQUIRED_MODELS=(
    "PP-OCRv5_server_det/inference.pdmodel"
    "PP-OCRv5_server_det/inference.pdiparams"
    "PP-OCRv5_server_rec/inference.pdmodel"
    "PP-OCRv5_server_rec/inference.pdiparams"
)

echo "📋 检查必需模型文件:"
for model in "${REQUIRED_MODELS[@]}"; do
    if [ -f "$MODEL_DIR/$model" ]; then
        echo "✅ $model"
    else
        echo "❌ $model (缺失)"
        MISSING=true
    fi
done

if [ "$MISSING" = true ]; then
    echo "❌ 缺少必需的模型文件"
    exit 1
fi

echo "✅ 所有必需模型文件存在"
echo "�� 模型文件统计:"
echo "   检测模型: $(ls -la $MODEL_DIR/PP-OCRv5_server_det/ | grep -E '\.(pdmodel|pdiparams)$' | wc -l) 个文件"
echo "   识别模型: $(ls -la $MODEL_DIR/PP-OCRv5_server_rec/ | grep -E '\.(pdmodel|pdiparams)$' | wc -l) 个文件"
echo "   总模型文件: $(find $MODEL_DIR -type f | wc -l) 个"

# 测试模型加载
echo "🧪 测试模型加载..."
python -c "
from paddleocr import PaddleOCR
import os

try:
    print('正在初始化 PaddleOCR...')
    ocr = PaddleOCR(
        device='cpu',
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False
    )
    print('✅ PaddleOCR 初始化成功')
    print('✅ 模型加载成功')
except Exception as e:
    print(f'❌ 模型加载失败: {e}')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo "🎉 模型验证完成，所有测试通过！"
else
    echo "❌ 模型验证失败"
    exit 1
fi
EOF

chmod +x $PACKAGE_DIR/verify_models.sh

# 创建部署说明
echo "📋 步骤4: 创建部署说明..."

cat > $PACKAGE_DIR/README.md << 'EOF'
# PaddleOCR 双服务 Docker 离线部署包（含模型）

## 服务说明
- **PP-OCRv5 服务** (端口 8080): OCR 识别服务
- **API 服务** (端口 8000): 主 API 服务器，SSL 模式

## 文件说明
- `Dockerfile`: Docker 镜像构建文件
- `docker-compose.yml`: 双服务编排配置
- `requirements.txt`: Python 依赖包列表
- `ppocrv5_server_final.py`: PP-OCRv5 服务代码
- `start_server.py`: API 服务器启动脚本
- `api_server.py`: API 服务器主代码
- `models/`: **PP-OCR 模型文件目录**
  - `PP-OCRv5_server_det/`: 文本检测模型
  - `PP-OCRv5_server_rec/`: 文本识别模型
- `build_docker.sh`: 构建脚本
- `start_services.sh`: 启动双服务脚本
- `stop_services.sh`: 停止服务脚本
- `verify_models.sh`: 模型验证脚本

## 模型文件说明
本包已包含完整的 PP-OCRv5 模型文件：
- **检测模型**: PP-OCRv5_server_det
  - inference.pdmodel: 模型结构文件
  - inference.pdiparams: 模型参数文件
  - inference.pdiparams.info: 模型信息文件
- **识别模型**: PP-OCRv5_server_rec
  - inference.pdmodel: 模型结构文件
  - inference.pdiparams: 模型参数文件
  - inference.pdiparams.info: 模型信息文件

## 部署步骤

### 1. 验证模型文件
```bash
chmod +x verify_models.sh
./verify_models.sh
```

### 2. 构建镜像
```bash
chmod +x build_docker.sh
./build_docker.sh
```

### 3. 启动双服务
```bash
chmod +x start_services.sh
./start_services.sh
```

### 4. 验证服务
```bash
# PP-OCRv5 服务健康检查
curl http://localhost:8080/health

# API 服务健康检查
curl -k https://localhost:8000/health
```

### 5. 测试 OCR
```bash
# 通过 API 服务上传图片
curl -X POST https://localhost:8000/api/upload \
  -F "file=@your_image.jpg" \
  -k
```

## 服务地址
- PP-OCRv5 服务: http://localhost:8080
- API 服务: https://localhost:8000
- API 文档: https://localhost:8000/docs

## 离线部署优势
✅ **完全离线**: 包含所有模型文件，无需网络下载  
✅ **快速启动**: 无需等待模型下载  
✅ **稳定可靠**: 避免网络问题导致的模型加载失败  
✅ **版本固定**: 使用特定版本的模型，确保一致性  

## 注意事项
- 模型文件已预置，首次启动无需下载
- API 服务使用 SSL 模式，需要证书文件
- 服务默认使用 CPU 模式
- 日志文件保存在 logs/ 目录

## 故障排除
- 验证模型: `./verify_models.sh`
- 查看服务状态: `docker-compose ps`
- 查看日志: `docker-compose logs -f`
- 重启服务: `docker-compose restart`
- 停止服务: `./stop_services.sh`

## 模型文件大小
- 检测模型: ~3MB
- 识别模型: ~8MB
- 总模型大小: ~11MB
EOF

# 创建压缩包
echo "�� 步骤5: 创建压缩包..."
tar -czf ${PACKAGE_DIR}.tar.gz $PACKAGE_DIR/

echo "✅ 完整离线部署包已创建: ${PACKAGE_DIR}.tar.gz"
echo "📊 包大小: $(du -sh ${PACKAGE_DIR}.tar.gz | cut -f1)"
echo "�� 模型文件大小: $(du -sh $PACKAGE_DIR/models | cut -f1)"
echo ""
echo "📋 包内容概览:"
echo "   �� 模型文件: $(find $PACKAGE_DIR/models -type f | wc -l) 个文件"
echo "   �� 代码文件: $(find $PACKAGE_DIR -name "*.py" | wc -l) 个文件"
echo "   �� 配置文件: $(find $PACKAGE_DIR -name "*.yml" -o -name "*.txt" -o -name "Dockerfile" | wc -l) 个文件"
echo ""
echo "🚀 部署到离线机器："
echo "   1. 复制 ${PACKAGE_DIR}.tar.gz 到离线机器"
echo "   2. 解压: tar -xzf ${PACKAGE_DIR}.tar.gz"
echo "   3. 进入目录: cd $PACKAGE_DIR"
echo "   4. 验证模型: ./verify_models.sh"
echo "   5. 构建镜像: ./build_docker.sh"
echo "   6. 启动服务: ./start_services.sh"