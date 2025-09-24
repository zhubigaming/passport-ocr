#!/usr/bin/env python3
"""
SSL证书生成脚本
用于生成自签名证书供开发环境使用
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

def check_openssl():
    """检查OpenSSL是否可用"""
    try:
        result = subprocess.run(['openssl', 'version'], 
                              capture_output=True, text=True, check=True)
        print(f"✅ OpenSSL可用: {result.stdout.strip()}")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ OpenSSL不可用")
        print("请安装OpenSSL:")
        print("  Windows: 下载并安装 https://slproweb.com/products/Win32OpenSSL.html")
        print("  macOS: brew install openssl")
        print("  Ubuntu: sudo apt-get install openssl")
        return False

def generate_self_signed_cert(
    cert_file="fullchain.pem",
    key_file="privkey.pem",
    days=365,
    country="CN",
    state="Beijing",
    city="Beijing",
    org="OCR System",
    common_name="localhost"
):
    """生成自签名SSL证书"""
    
    project_root = Path(__file__).parent
    cert_path = project_root / cert_file
    key_path = project_root / key_file
    
    print(f"🔧 生成SSL证书...")
    print(f"   证书文件: {cert_path}")
    print(f"   私钥文件: {key_path}")
    print(f"   有效期: {days}天")
    print(f"   域名: {common_name}")
    
    # 创建证书主题
    subject = f"/C={country}/ST={state}/L={city}/O={org}/CN={common_name}"
    
    try:
        # 生成私钥和证书
        cmd = [
            'openssl', 'req', '-new', '-x509',
            '-days', str(days),
            '-nodes',
            '-out', str(cert_path),
            '-keyout', str(key_path),
            '-subj', subject
        ]
        
        print("⏳ 正在生成证书...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        print("✅ SSL证书生成成功！")
        print(f"   证书: {cert_path}")
        print(f"   私钥: {key_path}")
        
        # 显示证书信息
        print("\n📋 证书信息:")
        info_cmd = ['openssl', 'x509', '-in', str(cert_path), '-text', '-noout']
        info_result = subprocess.run(info_cmd, capture_output=True, text=True)
        
        if info_result.returncode == 0:
            lines = info_result.stdout.split('\n')
            for line in lines:
                if 'Subject:' in line or 'Not Before:' in line or 'Not After:' in line:
                    print(f"   {line.strip()}")
        
        print("\n⚠️  重要提示:")
        print("   这是自签名证书，浏览器会显示安全警告")
        print("   在生产环境中请使用正式的SSL证书")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 证书生成失败: {e}")
        if e.stderr:
            print(f"错误详情: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ 生成过程中出现错误: {e}")
        return False

def generate_cert_for_multiple_domains():
    """生成支持多个域名的证书"""
    
    project_root = Path(__file__).parent
    cert_path = project_root / "fullchain.pem"
    key_path = project_root / "privkey.pem"
    config_path = project_root / "ssl.conf"
    
    # 创建OpenSSL配置文件
    ssl_config = """[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = CN
ST = Beijing
L = Beijing
O = OCR System
CN = localhost

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = 127.0.0.1
DNS.3 = 0.0.0.0
IP.1 = 127.0.0.1
IP.2 = 0.0.0.0
"""
    
    try:
        # 写入配置文件
        with open(config_path, 'w') as f:
            f.write(ssl_config)
        
        print("🔧 生成支持多域名的SSL证书...")
        
        # 生成私钥
        key_cmd = ['openssl', 'genpkey', '-algorithm', 'RSA', '-out', str(key_path), '-pkcs8']
        subprocess.run(key_cmd, check=True)
        
        # 生成证书
        cert_cmd = [
            'openssl', 'req', '-new', '-x509',
            '-key', str(key_path),
            '-out', str(cert_path),
            '-days', '365',
            '-config', str(config_path),
            '-extensions', 'v3_req'
        ]
        
        subprocess.run(cert_cmd, check=True)
        
        # 删除临时配置文件
        config_path.unlink()
        
        print("✅ 多域名SSL证书生成成功！")
        print("   支持的域名/IP:")
        print("   - localhost")
        print("   - 127.0.0.1") 
        print("   - 0.0.0.0")
        
        return True
        
    except Exception as e:
        print(f"❌ 多域名证书生成失败: {e}")
        if config_path.exists():
            config_path.unlink()
        return False

def main():
    print("=" * 50)
    print("🔐 SSL证书生成工具")
    print("=" * 50)
    
    if not check_openssl():
        return 1
    
    project_root = Path(__file__).parent
    cert_path = project_root / "fullchain.pem"
    key_path = project_root / "privkey.pem"
    
    # 检查是否已存在证书
    if cert_path.exists() and key_path.exists():
        print("⚠️  发现现有SSL证书:")
        print(f"   证书: {cert_path}")
        print(f"   私钥: {key_path}")
        
        choice = input("\n是否重新生成? (y/N): ").lower()
        if choice not in ['y', 'yes']:
            print("👋 保持现有证书")
            return 0
        
        # 备份现有证书
        import shutil
        backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(cert_path, f"{cert_path}.backup_{backup_time}")
        shutil.copy2(key_path, f"{key_path}.backup_{backup_time}")
        print(f"📁 已备份现有证书 (后缀: .backup_{backup_time})")
    
    print("\n请选择证书类型:")
    print("1. 简单自签名证书 (推荐)")
    print("2. 支持多域名的证书")
    
    choice = input("请选择 (1-2): ").strip()
    
    if choice == "2":
        success = generate_cert_for_multiple_domains()
    else:
        # 获取域名
        default_cn = "localhost"
        cn = input(f"请输入域名 (默认: {default_cn}): ").strip()
        if not cn:
            cn = default_cn
        
        success = generate_self_signed_cert(common_name=cn)
    
    if success:
        print(f"\n🚀 现在可以使用HTTPS启动服务:")
        print(f"   python start_server.py --ssl")
        print(f"   或")
        print(f"   python start_all_services.py --ssl")
        return 0
    else:
        return 1

if __name__ == '__main__':
    sys.exit(main()) 