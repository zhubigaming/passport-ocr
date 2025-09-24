#!/usr/bin/env python3
"""
最简化OCR配置
只使用最基本的参数，确保与最新版本PaddleOCR兼容
"""

import os
import gc

def setup_memory_optimization():
    """设置内存优化配置"""
    
    # 设置PaddlePaddle环境变量
    os.environ['FLAGS_use_gpu'] = '0'  # 强制使用CPU
    os.environ['FLAGS_use_mkldnn'] = '1'  # 启用MKL-DNN优化
    os.environ['FLAGS_allocator_strategy'] = 'auto_growth'  # 内存自动增长
    os.environ['FLAGS_fraction_of_gpu_memory_to_use'] = '0.1'  # 限制GPU内存使用
    os.environ['FLAGS_eager_delete_tensor_gb'] = '0.0'  # 立即删除张量
    os.environ['FLAGS_fast_eager_deletion_mode'] = 'True'  # 快速删除模式
    os.environ['FLAGS_memory_fraction_of_eager_deletion'] = '1.0'  # 内存删除比例
    
    # 设置线程数限制
    os.environ['OMP_NUM_THREADS'] = '2'  # OpenMP线程数
    os.environ['MKL_NUM_THREADS'] = '2'  # MKL线程数
    
    # 设置内存限制
    os.environ['PADDLE_DISABLE_GPU_MEMORY_POOL'] = 'True'  # 禁用GPU内存池
    os.environ['FLAGS_use_parallel_executor'] = 'False'  # 禁用并行执行器
    
    print("✅ 内存优化配置已设置")

def cleanup_memory():
    """清理内存"""
    gc.collect()
    print("🧹 内存已清理")

def get_minimal_compatible_params():
    """获取最简化的PaddleOCR参数，确保兼容性"""
    return {
        'lang': 'en',
        # 只使用最基本的参数，确保与最新版本兼容
        # 移除所有可能不兼容的参数
    }

def get_image_processing_config():
    """获取图像处理配置"""
    return {
        'max_image_size': 1024,  # 最大图像尺寸
        'max_file_size': 10 * 1024 * 1024,  # 最大文件大小 (10MB)
        'supported_formats': ['.jpg', '.jpeg', '.png', '.bmp', '.tiff'],
        'compression_quality': 85,  # JPEG压缩质量
        'resize_method': 'LANCZOS',  # 缩放方法
    }

def get_server_config():
    """获取服务器配置"""
    return {
        'max_workers': 2,  # 最大工作线程数
        'max_concurrent_requests': 1,  # 最大并发请求数
        'request_timeout': 60,  # 请求超时时间(秒)
        'memory_limit_mb': 2048,  # 内存限制(MB)
        'enable_gc': True,  # 启用垃圾回收
        'gc_interval': 5,  # 垃圾回收间隔(请求数)
    }

if __name__ == '__main__':
    setup_memory_optimization()
    print("最简化兼容配置测试完成") 