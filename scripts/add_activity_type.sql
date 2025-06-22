-- SQLite版本
ALTER TABLE activities ADD COLUMN type VARCHAR(50) DEFAULT '其他';
 
-- PostgreSQL版本（注释掉，需要时取消注释）
-- ALTER TABLE activities ADD COLUMN IF NOT EXISTS type VARCHAR(50) DEFAULT '其他'; 