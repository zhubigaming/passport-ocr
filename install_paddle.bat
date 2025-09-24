@echo off
chcp 65001 >nul

echo ==========================================
echo PaddlePaddle 3.0.0 快速安装脚本 (Windows)
echo ==========================================

REM 检查Python环境
echo 🔍 检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python未安装
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo ✅ Python版本: %PYTHON_VERSION%

REM 检查pip
pip --version >nul 2>&1
if errorlevel 1 (
    echo ❌ pip未安装
    pause
    exit /b 1
)

echo ✅ pip已安装

REM 升级pip
echo ⬆️ 升级pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ❌ pip升级失败
    pause
    exit /b 1
)
echo ✅ pip升级完成

REM 安装PaddlePaddle
echo 📦 安装PaddlePaddle 3.0.0...
echo ⏳ 正在安装PaddlePaddle，这可能需要几分钟...

python -m pip install paddlepaddle==3.0.0 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
if errorlevel 1 (
    echo ❌ PaddlePaddle安装失败
    pause
    exit /b 1
)
echo ✅ PaddlePaddle安装成功

REM 安装PaddleOCR
echo 📦 安装PaddleOCR...
echo ⏳ 正在安装PaddleOCR...

pip install paddleocr
if errorlevel 1 (
    echo ❌ PaddleOCR安装失败
    pause
    exit /b 1
)
echo ✅ PaddleOCR安装成功

REM 验证安装
echo 🔍 验证安装...

echo 验证PaddlePaddle...
python -c "import paddle; print(f'✅ PaddlePaddle版本: {paddle.__version__}')"
if errorlevel 1 (
    echo ❌ PaddlePaddle验证失败
    pause
    exit /b 1
)

echo 验证PaddleOCR...
python -c "from paddleocr import PaddleOCR; print('✅ PaddleOCR导入成功')"
if errorlevel 1 (
    echo ❌ PaddleOCR验证失败
    pause
    exit /b 1
)

echo ✅ 所有组件验证成功

REM 显示安装信息
echo 📊 安装信息:
echo    - Python版本: %PYTHON_VERSION%
for /f "tokens=2" %%i in ('pip --version 2^>^&1') do echo    - pip版本: %%i

echo.
echo 🎉 安装完成！
echo.
echo 📋 下一步:
echo    1. 运行测试: python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR()"
echo    2. 查看文档: https://www.paddlepaddle.org.cn/
echo    3. 开始使用OCR功能

pause 