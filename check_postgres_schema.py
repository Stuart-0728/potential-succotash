import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 数据库连接信息
conn_params = {
    'dbname': 'cqnu_association_uxft',
    'user': 'cqnu_association_uxft_user',
    'password': 'BamPWSRTgj0sPGKM4sGsLDv8sGCPCPzB',
    'host': 'dpg-d0sjag49c44c73f7jt4g-a.oregon-postgres.render.com',
    'port': '5432'
}

try:
    # 连接到PostgreSQL数据库
    print(f"正在连接到数据库...")
    conn = psycopg2.connect(**conn_params)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 获取所有表名
    print("\n获取所有表名:")
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cursor.fetchall()
    
    if not tables:
        print("数据库中没有表")
        sys.exit(0)
    
    print(f"找到 {len(tables)} 个表:")
    for table in tables:
        print(f"- {table['table_name']}")
    
    # 对每个表获取详细信息
    for table in tables:
        table_name = table['table_name']
        print(f"\n表 '{table_name}' 的结构:")
        
        # 获取列信息
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length, 
                   is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """, (table_name,))
        columns = cursor.fetchall()
        
        for column in columns:
            nullable = "NULL" if column['is_nullable'] == 'YES' else "NOT NULL"
            length = f"({column['character_maximum_length']})" if column['character_maximum_length'] else ""
            default = f" DEFAULT {column['column_default']}" if column['column_default'] else ""
            print(f"  {column['column_name']}: {column['data_type']}{length} {nullable}{default}")
        
        # 获取主键信息
        cursor.execute("""
            SELECT c.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
            JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema
                AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
            WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s;
        """, (table_name,))
        pks = cursor.fetchall()
        
        if pks:
            print("  主键:", ", ".join([pk['column_name'] for pk in pks]))
        
        # 获取外键信息
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                  ON ccu.constraint_name = tc.constraint_name
                  AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_name=%s;
        """, (table_name,))
        fks = cursor.fetchall()
        
        if fks:
            print("  外键:")
            for fk in fks:
                print(f"    {fk['column_name']} -> {fk['foreign_table_name']}.{fk['foreign_column_name']}")
        
        # 获取唯一约束
        cursor.execute("""
            SELECT
                tc.constraint_name,
                kcu.column_name
            FROM
                information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'UNIQUE' AND tc.table_name=%s;
        """, (table_name,))
        uqs = cursor.fetchall()
        
        if uqs:
            constraints = {}
            for uq in uqs:
                if uq['constraint_name'] not in constraints:
                    constraints[uq['constraint_name']] = []
                constraints[uq['constraint_name']].append(uq['column_name'])
            
            print("  唯一约束:")
            for constraint, columns in constraints.items():
                print(f"    {constraint}: ({', '.join(columns)})")
    
    # 关闭连接
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"错误: {str(e)}")
    sys.exit(1) 