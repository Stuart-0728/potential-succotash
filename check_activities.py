import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# 数据库连接信息
DB_URL = "postgresql://cqnu_association_uxft_user:BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB@dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com/cqnu_association_uxft"

def connect_to_db():
    """连接到数据库"""
    try:
        conn = psycopg2.connect(DB_URL)
        print("数据库连接成功")
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        sys.exit(1)

def check_activities(conn):
    """检查所有活动"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询所有活动
        cur.execute("""
            SELECT id, title, status, is_featured, poster_image, created_at, start_time, end_time 
            FROM activities 
            ORDER BY created_at DESC
        """)
        activities = cur.fetchall()
        
        print(f"\n找到 {len(activities)} 个活动:")
        for activity in activities:
            print(f"ID: {activity['id']}, 标题: {activity['title']}, 状态: {activity['status']}, 特色: {'是' if activity['is_featured'] else '否'}")
            print(f"  海报: {activity['poster_image']}")
            print(f"  创建时间: {activity['created_at']}")
            print(f"  活动时间: {activity['start_time']} - {activity['end_time']}")
            print("-" * 50)

def check_featured_activities(conn):
    """检查特色活动"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询特色活动
        cur.execute("""
            SELECT id, title, status, poster_image, created_at 
            FROM activities 
            WHERE is_featured = TRUE AND status = 'active'
            ORDER BY created_at DESC
        """)
        featured = cur.fetchall()
        
        print(f"\n找到 {len(featured)} 个特色活动:")
        for activity in featured:
            print(f"ID: {activity['id']}, 标题: {activity['title']}, 状态: {activity['status']}")
            print(f"  海报: {activity['poster_image']}")
            print(f"  创建时间: {activity['created_at']}")
            print("-" * 50)

def check_latest_activity(conn):
    """检查最新创建的活动"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # 查询最新的5个活动
        cur.execute("""
            SELECT id, title, status, is_featured, poster_image, created_at 
            FROM activities 
            ORDER BY created_at DESC
            LIMIT 5
        """)
        latest = cur.fetchall()
        
        print("\n最新创建的5个活动:")
        for activity in latest:
            print(f"ID: {activity['id']}, 标题: {activity['title']}, 状态: {activity['status']}, 特色: {'是' if activity['is_featured'] else '否'}")
            print(f"  海报: {activity['poster_image']}")
            print(f"  创建时间: {activity['created_at']}")
            print("-" * 50)

def fix_issue(conn):
    """修复问题 - 将最新活动设置为特色活动"""
    try:
        with conn.cursor() as cur:
            # 获取最新活动ID
            cur.execute("SELECT id FROM activities ORDER BY created_at DESC LIMIT 1")
            latest_id = cur.fetchone()[0]
            
            # 将最新活动设置为特色活动
            cur.execute("UPDATE activities SET is_featured = TRUE WHERE id = %s", (latest_id,))
            conn.commit()
            print(f"\n已将活动 ID {latest_id} 设置为特色活动")
    except Exception as e:
        conn.rollback()
        print(f"修复失败: {e}")

def main():
    """主函数"""
    conn = connect_to_db()
    try:
        check_activities(conn)
        check_featured_activities(conn)
        check_latest_activity(conn)
        
        # 询问是否需要修复
        answer = input("\n是否要将最新活动设置为特色活动? (y/n): ")
        if answer.lower() == 'y':
            fix_issue(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main() 