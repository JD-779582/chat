#!/bin/bash

# 检查项目结构
echo "检查项目结构..."
PROJECT_DIR=/var/www/chat

# 检查必要的目录
directories=(
    "$PROJECT_DIR"
    "$PROJECT_DIR/server"
    "$PROJECT_DIR/static"
    "$PROJECT_DIR/static/css"
    "$PROJECT_DIR/static/js"
    "$PROJECT_DIR/server/templates"
)

for dir in "${directories[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "创建目录: $dir"
        mkdir -p "$dir"
    fi
done

# 检查必要的文件
files=(
    "$PROJECT_DIR/requirements.txt"
    "$PROJECT_DIR/server/__init__.py"
    "$PROJECT_DIR/server/app.py"
    "$PROJECT_DIR/server/chat.py"
    "$PROJECT_DIR/server/database.py"
    "$PROJECT_DIR/static/css/style.css"
    "$PROJECT_DIR/static/js/chat.js"
    "$PROJECT_DIR/server/templates/chat.html"
    "$PROJECT_DIR/server/templates/login.html"
    "$PROJECT_DIR/server/templates/register.html"
)

for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "警告: 缺少文件 $file"
    fi
done

# 检查权限
echo "检查权限..."
sudo chown -R www-data:www-data "$PROJECT_DIR"
sudo chmod -R 755 "$PROJECT_DIR"

# 检查日志目录
echo "创建日志目录..."
sudo mkdir -p /var/log/chat
sudo chown -R www-data:www-data /var/log/chat