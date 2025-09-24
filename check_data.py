#!/usr/bin/env python3
"""
检查数据库中的实际数据
"""

import mysql.connector
from datetime import datetime

def check_database_data():
    """检查数据库中的实际数据"""
    try:
        # 连接数据库
        from config import DB_CONFIG
        db = mysql.connector.connect(**DB_CONFIG)
        cursor = db.cursor(dictionary=True)
        
        print("🔍 检查数据库中的实际数据...")
        print("=" * 50)
        
        # 1. 检查总记录数
        cursor.execute("SELECT COUNT(*) as total FROM passport_records")
        total = cursor.fetchone()['total']
        print(f"📊 总记录数: {total}")
        
        # 2. 检查各类型文档数量
        cursor.execute("""
            SELECT doc_type_cn, COUNT(*) as count 
            FROM passport_records 
            GROUP BY doc_type_cn 
            ORDER BY count DESC
        """)
        doc_types = cursor.fetchall()
        print("\n📋 各类型文档数量:")
        for doc_type in doc_types:
            print(f"   {doc_type['doc_type_cn']}: {doc_type['count']}")
        
        # 3. 检查最近10条记录
        cursor.execute("""
            SELECT id, doc_type_cn, created_at, updated_at 
            FROM passport_records 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        recent_records = cursor.fetchall()
        print("\n📅 最近10条记录:")
        for record in recent_records:
            print(f"   ID: {record['id']}, 类型: {record['doc_type_cn']}, 创建时间: {record['created_at']}, 更新时间: {record['updated_at']}")
        
        # 4. 检查今天的记录
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM passport_records 
            WHERE DATE(created_at) = CURDATE()
        """)
        today_raw = cursor.fetchone()['count']
        print(f"\n📅 今天记录数（原始时间）: {today_raw}")
        
        # 5. 检查时区转换后的今天记录
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM passport_records 
            WHERE DATE(CONVERT_TZ(created_at, '+00:00', '+08:00')) = CURDATE()
        """)
        today_converted = cursor.fetchone()['count']
        print(f"📅 今天记录数（时区转换后）: {today_converted}")
        
        # 6. 检查今天的护照记录
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM passport_records 
            WHERE DATE(CONVERT_TZ(created_at, '+00:00', '+08:00')) = CURDATE()
            AND doc_type_cn = '护照'
        """)
        today_passport = cursor.fetchone()['count']
        print(f"📅 今天护照记录数: {today_passport}")
        
        # 7. 检查数据库时区设置
        cursor.execute("SELECT @@global.time_zone, @@session.time_zone, NOW(), CURDATE()")
        timezone_info = cursor.fetchone()
        print(f"\n⏰ 数据库时区信息:")
        print(f"   全局时区: {timezone_info[0]}")
        print(f"   会话时区: {timezone_info[1]}")
        print(f"   当前时间: {timezone_info[2]}")
        print(f"   当前日期: {timezone_info[3]}")
        
        # 8. 检查时区转换示例
        cursor.execute("""
            SELECT 
                created_at,
                CONVERT_TZ(created_at, '+00:00', '+08:00') as beijing_time,
                DATE(created_at) as original_date,
                DATE(CONVERT_TZ(created_at, '+00:00', '+08:00')) as beijing_date
            FROM passport_records 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        timezone_examples = cursor.fetchall()
        print(f"\n🔄 时区转换示例:")
        for example in timezone_examples:
            print(f"   原始时间: {example['created_at']}")
            print(f"   北京时间: {example['beijing_time']}")
            print(f"   原始日期: {example['original_date']}")
            print(f"   北京日期: {example['beijing_date']}")
            print("   ---")
        
        cursor.close()
        db.close()
        
        print("\n" + "=" * 50)
        print("✅ 数据检查完成")
        
    except Exception as e:
        print(f"❌ 检查失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database_data() 