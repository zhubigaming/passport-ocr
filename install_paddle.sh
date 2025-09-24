#!/bin/bash

# PaddlePaddle 快速安装脚本

echo "=========================================="
echo "PaddlePaddle 3.0.0 快速安装脚本"
echo "=========================================="

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 检查Python环境
check_python() {
    print_message $BLUE "🔍 检查Python环境..."
    
    if ! command -v python &> /dev/null; then
        print_message $RED "❌ Python未安装"
        exit 1
    fi
    
    local python_version=$(python --version 2>&1 | cut -d' ' -f2)
    print_message $GREEN "✅ Python版本: ${python_version}"
    
    # 检查pip
    if ! command -v pip &> /dev/null; then
        print_message $RED "❌ pip未安装"
        exit 1
    fi
    
    print_message $GREEN "✅ pip已安装"
}

# 升级pip
upgrade_pip() {
    print_message $BLUE "⬆️ 升级pip..."
    python -m pip install --upgrade pip
    print_message $GREEN "✅ pip升级完成"
}

# 安装PaddlePaddle
install_paddlepaddle() {
    print_message $BLUE "📦 安装PaddlePaddle 3.0.0..."
    
    print_message $YELLOW "⏳ 正在安装PaddlePaddle，这可能需要几分钟..."
    
    python -m pip install paddlepaddle==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
    
    if [ $? -eq 0 ]; then
        print_message $GREEN "✅ PaddlePaddle安装成功"
    else
        print_message $RED "❌ PaddlePaddle安装失败"
        exit 1
    fi
}

# 安装PaddleOCR
install_paddleocr() {
    print_message $BLUE "📦 安装PaddleOCR..."
    
    print_message $YELLOW "⏳ 正在安装PaddleOCR..."
    
    pip install paddleocr
    
    if [ $? -eq 0 ]; then
        print_message $GREEN "✅ PaddleOCR安装成功"
    else
        print_message $RED "❌ PaddleOCR安装失败"
        exit 1
    fi
}

# 验证安装
verify_installation() {
    print_message $BLUE "🔍 验证安装..."
    
    # 验证PaddlePaddle
    print_message $YELLOW "验证PaddlePaddle..."
    python -c "
import paddle
print(f'✅ PaddlePaddle版本: {paddle.__version__}')
"
    
    if [ $? -ne 0 ]; then
        print_message $RED "❌ PaddlePaddle验证失败"
        exit 1
    fi
    
    # 验证PaddleOCR
    print_message $YELLOW "验证PaddleOCR..."
    python -c "
from paddleocr import PaddleOCR
print('✅ PaddleOCR导入成功')
"
    
    if [ $? -ne 0 ]; then
        print_message $RED "❌ PaddleOCR验证失败"
        exit 1
    fi
    
    print_message $GREEN "✅ 所有组件验证成功"
}

# 显示安装信息
show_info() {
    print_message $BLUE "📊 安装信息:"
    echo "   - Python版本: $(python --version 2>&1)"
    echo "   - pip版本: $(pip --version 2>&1 | cut -d' ' -f2)"
    echo "   - PaddlePaddle版本: $(python -c 'import paddle; print(paddle.__version__)' 2>/dev/null || echo '未安装')"
    echo "   - PaddleOCR: $(python -c 'from paddleocr import PaddleOCR; print("已安装")' 2>/dev/null || echo '未安装')"
}

# 主函数
main() {
    print_message $BLUE "🚀 开始安装PaddlePaddle和PaddleOCR..."
    
    check_python
    upgrade_pip
    install_paddlepaddle
    install_paddleocr
    verify_installation
    show_info
    
    print_message $GREEN "🎉 安装完成！"
    print_message $BLUE "📋 下一步:"
    echo "   1. 运行测试: python -c 'from paddleocr import PaddleOCR; ocr = PaddleOCR()'"
    echo "   2. 查看文档: https://www.paddlepaddle.org.cn/"
    echo "   3. 开始使用OCR功能"
}

# 错误处理
trap 'print_message $RED "\n❌ 安装过程中发生错误"; exit 1' ERR

# 执行主函数
main "$@" 