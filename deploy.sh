#!/bin/bash

# 安装系统依赖
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx

# 创建项目目录
PROJECT_DIR=/var/www/chat
sudo mkdir -p $PROJECT_DIR
sudo chown -R $USER:$USER $PROJECT_DIR

# 创建并激活虚拟环境
python3 -m venv $PROJECT_DIR/venv
source $PROJECT_DIR/venv/bin/activate

# 安装项目依赖
pip install -r requirements.txt

# 创建 systemd 服务文件
sudo tee /etc/systemd/system/chat.service << EOF
[Unit]
Description=Chat Application
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python -m server.app
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# 配置 Nginx
sudo tee /etc/nginx/sites-available/chat << EOF
server {
    listen 80;
    server_name your_domain.com;  # 替换为您的域名

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

# 启用 Nginx 配置
sudo ln -s /etc/nginx/sites-available/chat /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable chat
sudo systemctl start chat

# 显示状态
sudo systemctl status chat