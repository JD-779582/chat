const socket = io();
const messagesDiv = document.getElementById('messages');
const messageInput = document.getElementById('message-input');
const onlineUsersDiv = document.getElementById('online-users');
const onlineCountSpan = document.getElementById('online-count');

// 连接状态处理
socket.on('connect', () => {
    console.log('Connected to server');
    showNotification('已连接到服务器');
});

socket.on('disconnect', () => {
    console.log('Disconnected from server');
    showNotification('与服务器断开连接', 'error');
});

// 消息处理
socket.on('message', (data) => {
    appendMessage(data);
});

socket.on('status', (data) => {
    appendStatus(data.message);
});

socket.on('error', (data) => {
    showNotification(data.message, 'error');
});

socket.on('system', (data) => {
    appendStatus(data.message);
});

// 在线用户列表处理
socket.on('user_list', (data) => {
    updateOnlineUsers(data.users);
});

// 发送消息
function sendMessage() {
    const text = messageInput.value.trim();
    if (text) {
        socket.emit('message', { text: text });
        messageInput.value = '';
        // 自动调整输入框高度
        adjustTextareaHeight();
    }
}

// 添加消息到聊天区域
function appendMessage(data) {
    const div = document.createElement('div');
    // 检查消息是否是自己发送的
    const isSelf = data.username === currentUser;
    div.className = `message ${isSelf ? 'self' : ''} ${data.is_admin ? 'admin' : ''}`;
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const header = document.createElement('div');
    header.className = 'message-header';
    
    const username = document.createElement('span');
    username.className = 'message-username';
    username.textContent = data.username;
    
    const time = document.createElement('span');
    time.className = 'message-time';
    time.textContent = data.timestamp;
    
    // 根据是否是自己的消息调整顺序
    if (isSelf) {
        header.appendChild(time);
        header.appendChild(username);
    } else {
        header.appendChild(username);
        header.appendChild(time);
    }
    
    const text = document.createElement('div');
    text.className = 'message-text';
    text.textContent = data.text;
    
    content.appendChild(header);
    content.appendChild(text);
    div.appendChild(content);
    
    messagesDiv.appendChild(div);
    scrollToBottom();
}

// 添加状态消息
function appendStatus(message) {
    const div = document.createElement('div');
    div.className = 'system-message';
    const span = document.createElement('span');
    span.textContent = message;
    div.appendChild(span);
    messagesDiv.appendChild(div);
    scrollToBottom();
}

// 更新在线用户列表
function updateOnlineUsers(users) {
    onlineUsersDiv.innerHTML = '';
    users.forEach(user => {
        const div = document.createElement('div');
        div.className = 'user-item';
        
        const avatar = document.createElement('div');
        avatar.className = 'user-avatar';
        avatar.textContent = user.username[0].toUpperCase();
        
        const name = document.createElement('span');
        name.textContent = user.username;
        if (user.is_admin) {
            name.innerHTML += ' <span class="admin-badge">管理员</span>';
        }
        
        div.appendChild(avatar);
        div.appendChild(name);
        onlineUsersDiv.appendChild(div);
    });
    
    // 更新在线人数
    if (onlineCountSpan) {
        onlineCountSpan.textContent = users.length;
    }
}

// 显示通知
function showNotification(message, type = 'info') {
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type} show`;
    
    setTimeout(() => {
        notification.className = 'notification';
    }, 3000);
}

// 自动调整输入框高度
function adjustTextareaHeight() {
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// 滚动到底部
function scrollToBottom() {
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// 事件监听器
messageInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

messageInput.addEventListener('input', adjustTextareaHeight);

// 初始化
adjustTextareaHeight(); 

// 在文件顶部添加当前用户变量
let currentUser = document.querySelector('.user-info').textContent.trim();
if (currentUser.includes('管理员')) {
    currentUser = currentUser.replace('管理员', '').trim();
} 