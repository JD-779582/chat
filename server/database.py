import sqlite3
import hashlib
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file="chat.db"):
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """初始化数据库，创建用户表和管理员表"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            # 修改用户表，添加 is_admin 字段
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    email TEXT UNIQUE,
                    is_admin BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            ''')
            
            # 创建禁言表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mutes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    muted_by INTEGER,
                    muted_until TIMESTAMP,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (muted_by) REFERENCES users(id)
                )
            ''')
            conn.commit()
            
            # 确保至少有一个管理员账户
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_admin = 1')
            if cursor.fetchone()[0] == 0:
                admin_password = self.hash_password("admin123")
                cursor.execute(
                    'INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                    ("admin", admin_password, True)
                )
                conn.commit()

    def hash_password(self, password):
        """对密码进行哈希处理"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register_user(self, username, password, email=None):
        """注册新用户"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                hashed_password = self.hash_password(password)
                cursor.execute(
                    'INSERT INTO users (username, password, email) VALUES (?, ?, ?)',
                    (username, hashed_password, email)
                )
                conn.commit()
                return True, "注册成功"
        except sqlite3.IntegrityError:
            return False, "用户名或邮箱已存在"
        except Exception as e:
            return False, f"注册失败: {str(e)}"

    def verify_user(self, username, password):
        """验证用户登录并返回用户信息"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, password, is_admin, status FROM users WHERE username = ?',
                    (username,)
                )
                result = cursor.fetchone()
                if not result:
                    return False, "用户名或密码错误"
                
                user_id, stored_password, is_admin, status = result
                
                if status == "banned":
                    return False, "账号已被封禁"
                
                if stored_password == self.hash_password(password):
                    # 检查是否被禁言
                    cursor.execute(
                        'SELECT muted_until, reason FROM mutes WHERE user_id = ? AND muted_until > ? ORDER BY id DESC LIMIT 1',
                        (user_id, datetime.now())
                    )
                    mute_info = cursor.fetchone()
                    
                    # 更新最后登录时间
                    cursor.execute(
                        'UPDATE users SET last_login = ? WHERE id = ?',
                        (datetime.now(), user_id)
                    )
                    conn.commit()
                    
                    return True, {
                        "id": user_id,
                        "username": username,
                        "is_admin": bool(is_admin),
                        "muted_until": mute_info[0] if mute_info else None,
                        "mute_reason": mute_info[1] if mute_info else None
                    }
                return False, "用户名或密码错误"
        except Exception as e:
            return False, f"验证失败: {str(e)}"

    def mute_user(self, user_id, admin_id, duration_minutes, reason=None):
        """禁言用户"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                muted_until = datetime.now() + timedelta(minutes=duration_minutes)
                cursor.execute(
                    'INSERT INTO mutes (user_id, muted_by, muted_until, reason) VALUES (?, ?, ?, ?)',
                    (user_id, admin_id, muted_until, reason)
                )
                conn.commit()
                return True, "禁言成功"
        except Exception as e:
            return False, f"禁言失败: {str(e)}"

    def unmute_user(self, user_id):
        """解除用户禁言"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE mutes SET muted_until = ? WHERE user_id = ? AND muted_until > ?',
                    (datetime.now(), user_id, datetime.now())
                )
                conn.commit()
                return True, "已解除禁言"
        except Exception as e:
            return False, f"解除禁言失败: {str(e)}"

    def ban_user(self, user_id):
        """封禁用户"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET status = "banned" WHERE id = ?',
                    (user_id,)
                )
                conn.commit()
                return True, "封禁成功"
        except Exception as e:
            return False, f"封禁失败: {str(e)}"

    def unban_user(self, user_id):
        """解除用户封禁"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'UPDATE users SET status = "active" WHERE id = ?',
                    (user_id,)
                )
                conn.commit()
                return True, "解除封禁成功"
        except Exception as e:
            return False, f"解除封禁失败: {str(e)}"

    def get_user_by_username(self, username):
        """根据用户名获取用户信息"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, username, is_admin, status FROM users WHERE username = ?',
                (username,)
            )
            result = cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "username": result[1],
                    "is_admin": bool(result[2]),
                    "status": result[3]
                }
            return None 

    def get_user_by_id(self, user_id):
        """根据ID获取用户信息"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, username, is_admin, status FROM users WHERE id = ?',
                    (user_id,)
                )
                result = cursor.fetchone()
                if result:
                    return {
                        "id": result[0],
                        "username": result[1],
                        "is_admin": bool(result[2]),
                        "status": result[3]
                    }
                return None
        except Exception as e:
            print(f"获取用户信息失败: {e}")
            return None 

    def is_user_muted(self, user_id):
        """检查用户是否被禁言"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT 1 FROM mutes WHERE user_id = ? AND muted_until > ?',
                    (user_id, datetime.now())
                )
                return cursor.fetchone() is not None
        except Exception as e:
            print(f"检查禁言状态失败: {e}")
            return False

    def get_mute_info(self, user_id):
        """获取用户的禁言信息"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT muted_until, reason 
                    FROM mutes 
                    WHERE user_id = ? AND muted_until > ? 
                    ORDER BY id DESC LIMIT 1
                    ''',
                    (user_id, datetime.now())
                )
                result = cursor.fetchone()
                if result:
                    return {
                        'muted_until': result[0],
                        'reason': result[1]
                    }
                return None
        except Exception as e:
            print(f"获取禁言信息失败: {e}")
            return None 

    def save_message(self, message_data):
        """保存聊天消息到数据库"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                # 首先创建消息表（如果不存在）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        text TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_admin BOOLEAN DEFAULT 0
                    )
                ''')
                
                # 插入消息
                cursor.execute('''
                    INSERT INTO messages (username, text, timestamp, is_admin)
                    VALUES (?, ?, ?, ?)
                ''', (
                    message_data['username'],
                    message_data['text'],
                    message_data['timestamp'],
                    message_data.get('is_admin', False)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"保存消息失败: {e}")
            return False

    def get_recent_messages(self, limit=50):
        """获取最近的消息"""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, text, timestamp, is_admin
                    FROM messages
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
                messages = cursor.fetchall()
                return [{
                    'username': msg[0],
                    'text': msg[1],
                    'timestamp': msg[2],
                    'is_admin': bool(msg[3])
                } for msg in messages][::-1]  # 反转列表以获得正确的时间顺序
        except Exception as e:
            print(f"获取消息历史失败: {e}")
            return [] 