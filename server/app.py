from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from server.database import Database
import json
from server.chat import ChatManager
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__, 
    static_folder='../static',  # 指定静态文件夹的路径
    template_folder='templates'  # 指定模板文件夹的路径
)

app.config['SECRET_KEY'] = 'your-secret-key'  # 请更改为随机字符串
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = Database()
chat_manager = ChatManager(socketio, db)

# 修改文件上传配置
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'zip', 'rar', '7z'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB 最大限制

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH  # 设置 Flask 的最大文件大小限制

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class User(UserMixin):
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.is_admin = user_data.get('is_admin', False)

@login_manager.user_loader
def load_user(user_id):
    user_data = db.get_user_by_id(int(user_id))
    if user_data:
        return User(user_data)
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        success, result = db.verify_user(username, password)
        if success and isinstance(result, dict):  # 确保 result 是字典类型
            user = User(result)
            login_user(user)
            return redirect(url_for('chat'))
        flash(result if isinstance(result, str) else '登录失败')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        success, message = db.register_user(username, password, email)
        if success:
            flash('注册成功，请登录')
            return redirect(url_for('login'))
        flash(message)
    return render_template('register.html')

@app.route('/chat')
@login_required
def chat():
    return render_template('chat.html', username=current_user.username, 
                         is_admin=current_user.is_admin)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# WebSocket事件处理
@socketio.on('connect')
def handle_connect():
    chat_manager.handle_connect(request.sid)

@socketio.on('disconnect')
def handle_disconnect():
    chat_manager.handle_disconnect(request.sid)

@socketio.on('message')
def handle_message(data):
    chat_manager.handle_message(request.sid, data)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': '没有文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400
    
    # 检查文件名是否合法
    if '.' not in file.filename:
        return jsonify({'error': '无效的文件名'}), 400
    
    try:
        if file and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)  # 保存原始文件名
            # 使用时间戳创建存储文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            name, ext = os.path.splitext(original_filename)
            storage_filename = f"{timestamp}_{name}{ext}"  # 用于存储的文件名
            
            # 确保上传目录存在
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], storage_filename)
            file.save(filepath)
            
            # 获取文件类型和大小
            filetype = ext[1:].lower()  # 移除点号
            filesize = os.path.getsize(filepath)
            
            # 保存文件记录
            file_id = db.save_file_record(
                filename=storage_filename,
                filepath=filepath,
                filetype=filetype,
                filesize=filesize,
                user_id=current_user.id
            )
            
            # 发送文件消息
            file_url = url_for('static', filename=f'uploads/{storage_filename}')
            message = {
                'type': 'file',
                'filename': original_filename,  # 使用原始文件名显示
                'storage_filename': storage_filename,  # 存储的文件名
                'url': file_url,
                'filetype': filetype,
                'filesize': filesize,
                'username': current_user.username,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            socketio.emit('message', message, room='chat_room')
            
            return jsonify({
                'success': True,
                'file_url': file_url,
                'filename': original_filename,  # 返回原始文件名
                'storage_filename': storage_filename
            })
        
        return jsonify({'error': '不支持的文件类型'}), 400
        
    except Exception as e:
        print(f"文件上传错误: {str(e)}")
        return jsonify({'error': '文件上传失败'}), 500

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True) 