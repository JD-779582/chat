#!/bin/bash

# 设置变量
BACKUP_DIR="/var/backups/chat"
PROJECT_DIR="/var/www/chat"
DATE=$(date +%Y%m%d_%H%M%S)

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 备份数据库
cp "$PROJECT_DIR/chat.db" "$BACKUP_DIR/chat_$DATE.db"

# 备份项目文件
tar -czf "$BACKUP_DIR/chat_$DATE.tar.gz" "$PROJECT_DIR"

# 删除7天前的备份
find "$BACKUP_DIR" -type f -mtime +7 -delete

# 输出结果
echo "备份完成: $BACKUP_DIR/chat_$DATE.tar.gz"