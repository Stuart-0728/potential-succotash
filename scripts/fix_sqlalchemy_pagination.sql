-- 检查SQLAlchemy版本
DO $$
DECLARE
  sqlalchemy_version TEXT;
BEGIN
  -- 获取当前SQLAlchemy版本
  SELECT version INTO sqlalchemy_version FROM alembic_version WHERE version_num = '1';
  
  RAISE NOTICE 'Current SQLAlchemy version: %', sqlalchemy_version;
  
  -- 输出提示信息
  RAISE NOTICE 'This script cannot directly modify the SQLAlchemy version as it is a Python library.';
  RAISE NOTICE 'You will need to fix pagination issues in the code by modifying the Python files.';
END $$; 