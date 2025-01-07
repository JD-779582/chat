from datetime import datetime
from flask_socketio import emit, join_room, leave_room
from flask_login import current_user
import json

class ChatManager:
    def __init__(self, socketio, db):
        self.socketio = socketio
        self.db = db
        self.active_users = {}  # 存储活跃用户
        self.chat_rooms = {}    # 存储聊天室信息

    def handle_connect(self, sid):
        """处理用户连接"""
        if current_user.is_authenticated:
            self.active_users[sid] = {
                'user_id': current_user.id,
                'username': current_user.username,
                'is_admin': current_user.is_admin
            }
            join_room('chat_room', sid)
            self.broadcast_status(f'{current_user.username} 加入了聊天室')
            # 发送在线用户列表
            self.broadcast_user_list()

    def handle_disconnect(self, sid):
        """处理用户断开连接"""
        if sid in self.active_users:
            username = self.active_users[sid]['username']
            del self.active_users[sid]
            leave_room('chat_room', sid)
            self.broadcast_status(f'{username} 离开了聊天室')
            # 更新在线用户列表
            self.broadcast_user_list()

    def handle_message(self, sid, data):
        """处理聊天消息"""
        if sid not in self.active_users:
            return
        
        user = self.active_users[sid]
        text = data.get('text', '').strip()
        
        if not text:
            return

        # 处理管理员命令
        if text.startswith('/') and user['is_admin']:
            self.handle_admin_command(sid, text)
            return

        # 检查用户是否被禁言
        if self.db.is_user_muted(user['user_id']):
            mute_info = self.db.get_mute_info(user['user_id'])
            if mute_info:
                until_time = datetime.strptime(mute_info['muted_until'], '%Y-%m-%d %H:%M:%S')
                remaining = until_time - datetime.now()
                minutes = int(remaining.total_seconds() / 60)
                error_msg = f"你已被禁言，剩余 {minutes} 分钟"
                if mute_info['reason']:
                    error_msg += f"，原因：{mute_info['reason']}"
                emit('error', {'message': error_msg}, room=sid)
            else:
                emit('error', {'message': '你已被禁言'}, room=sid)
            return

        # 创建消息数据
        message = {
            'username': user['username'],
            'text': text,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_admin': user['is_admin']
        }

        # 保存消息到数据库
        if self.db.save_message(message):
            # 广播消息给所有用户
            emit('message', message, room='chat_room')
        else:
            emit('error', {'message': '消息发送失败'}, room=sid)

    def handle_admin_command(self, sid, command):
        """处理管理员命令"""
        parts = command.split()
        cmd = parts[0].lower()
        user = self.active_users[sid]

        try:
            if cmd == '/mute':
                if len(parts) < 3:
                    raise ValueError("使用方法: /mute username duration [reason]")
                username = parts[1]
                duration = int(parts[2])
                reason = ' '.join(parts[3:]) if len(parts) > 3 else None
                
                target = self.db.get_user_by_username(username)
                if not target:
                    emit('error', {'message': '找不到指定用户'}, room=sid)
                    return

                success, msg = self.db.mute_user(target['id'], user['user_id'], duration, reason)
                if success:
                    self.broadcast_status(f'系统: {username} 已被禁言 {duration} 分钟')
                else:
                    emit('error', {'message': msg}, room=sid)

            elif cmd == '/unmute':
                if len(parts) < 2:
                    raise ValueError("使用方法: /unmute username")
                username = parts[1]
                target = self.db.get_user_by_username(username)
                if not target:
                    emit('error', {'message': '找不到指定用户'}, room=sid)
                    return

                success, msg = self.db.unmute_user(target['id'])
                if success:
                    self.broadcast_status(f'系统: {username} 的禁言已被解除')
                else:
                    emit('error', {'message': msg}, room=sid)

            elif cmd == '/ban':
                if len(parts) < 2:
                    raise ValueError("使用方法: /ban username")
                username = parts[1]
                target = self.db.get_user_by_username(username)
                if not target:
                    emit('error', {'message': '找不到指定用户'}, room=sid)
                    return

                success, msg = self.db.ban_user(target['id'])
                if success:
                    self.broadcast_status(f'系统: {username} 已被封禁')
                    # 断开被封禁用户的连接
                    self.disconnect_user(username)
                else:
                    emit('error', {'message': msg}, room=sid)

            elif cmd == '/help':
                help_text = """可用的管理员命令:
/mute username duration [reason] - 禁言用户
/unmute username - 解除用户禁言
/ban username - 封禁用户
/unban username - 解除用户封禁
/users - 显示在线用户列表
/help - 显示此帮助信息"""
                emit('system', {'message': help_text}, room=sid)

            elif cmd == '/users':
                users_list = [f"{user['username']}{'(管理员)' if user['is_admin'] else ''}" 
                            for user in self.active_users.values()]
                emit('system', {'message': f"在线用户:\n{chr(10).join(users_list)}"}, room=sid)

        except Exception as e:
            emit('error', {'message': f'命令执行失败: {str(e)}'}, room=sid)

    def broadcast_status(self, message):
        """广播状态消息"""
        emit('status', {'message': message}, room='chat_room')

    def broadcast_user_list(self):
        """广播在线用户列表"""
        users = [{
            'username': user['username'],
            'is_admin': user['is_admin']
        } for user in self.active_users.values()]
        emit('user_list', {'users': users}, room='chat_room')

    def disconnect_user(self, username):
        """断开指定用户的连接"""
        for sid, user in list(self.active_users.items()):
            if user['username'] == username:
                self.socketio.disconnect(sid) 