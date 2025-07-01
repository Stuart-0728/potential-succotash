-- 重置connor用户的密码
-- 使用已知的pbkdf2哈希，对应密码为 "password123"
UPDATE users 
SET password_hash = 'pbkdf2:sha256:260000$BIpVlvXBwAl0lYx0$e35e5a86e73f1e9c5a98198c5b9f417cfe823f8d853f8d8b097f905af9d3bae7' 
WHERE username = 'connor';

-- 确认更新
SELECT id, username, substr(password_hash, 1, 30) || '...' as password_preview 
FROM users 
WHERE username = 'connor';

-- 输出确认信息
SELECT 'connor用户密码已重置为 "password123"' AS result; 