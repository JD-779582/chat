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
    if (data.type === 'file') {
        appendFileMessage(data);
    } else {
        appendMessage(data);
    }
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

// 文件上传相关
const fileInput = document.getElementById('file-input');
const uploadPreview = document.getElementById('upload-preview');
const previewContainer = document.getElementById('preview-container');
const previewFilename = document.getElementById('preview-filename');
const previewFilesize = document.getElementById('preview-filesize');
let currentFile = null;

fileInput.addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    currentFile = file;
    previewFilename.textContent = file.name;
    previewFilesize.textContent = formatFileSize(file.size);
    
    // 显示预览
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = function(e) {
            previewContainer.innerHTML = `<img src="${e.target.result}" alt="预览">`;
        };
        reader.readAsDataURL(file);
    } else {
        previewContainer.innerHTML = `
            <div class="file-message">
                <i class="fas fa-file file-icon"></i>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
            </div>
        `;
    }
    
    uploadPreview.style.display = 'block';
});

// 发送文件
async function sendFile() {
    if (!currentFile) return;
    
    const formData = new FormData();
    formData.append('file', currentFile);
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        if (result.success) {
            uploadPreview.style.display = 'none';
            currentFile = null;
            fileInput.value = '';
        } else {
            showNotification(result.error, 'error');
        }
    } catch (error) {
        showNotification('文件上传失败', 'error');
    }
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function appendFileMessage(data) {
    const div = document.createElement('div');
    div.className = `message ${data.username === currentUser ? 'self' : ''}`;
    
    const content = document.createElement('div');
    content.className = 'message-content file-message';
    
    const isImage = ['jpg', 'jpeg', 'png', 'gif'].includes(data.filetype.toLowerCase());
    
    content.innerHTML = `
        <div class="message-header">
            <span class="message-username">${data.username}</span>
            <span class="message-time">${data.timestamp}</span>
        </div>
        ${isImage ? `
            <img src="${data.url}" alt="${data.filename}" style="max-width: 200px; max-height: 200px;">
        ` : `
            <div class="file-message">
                <i class="fas fa-file file-icon"></i>
                <div class="file-info">
                    <div class="file-name">${data.filename}</div>
                    <div class="file-size">${formatFileSize(data.filesize)}</div>
                </div>
                <a href="${data.url}" class="file-download" download>
                    <i class="fas fa-download"></i>
                </a>
            </div>
        `}
    `;
    
    div.appendChild(content);
    messagesDiv.appendChild(div);
    scrollToBottom();
}

// 添加粘贴处理函数
function handlePaste(event) {
    const items = (event.clipboardData || event.originalEvent.clipboardData).items;
    
    for (let item of items) {
        if (item.type.indexOf('image') === 0) {
            event.preventDefault();
            const blob = item.getAsFile();
            
            // 创建预览
            const reader = new FileReader();
            reader.onload = function(e) {
                previewContainer.innerHTML = `<img src="${e.target.result}" alt="预览">`;
                previewFilename.textContent = "粘贴的图片.png";
                previewFilesize.textContent = formatFileSize(blob.size);
            };
            reader.readAsDataURL(blob);
            
            // 将 blob 转换为 File 对象
            currentFile = new File([blob], "pasted_image_" + new Date().getTime() + ".png", {
                type: blob.type
            });
            
            // 显示预览模态框
            uploadPreview.style.display = 'block';
            return;
        }
    }
}

// 修改文件上传预览模态框的按钮事件
document.querySelector('.modal .btn-send').addEventListener('click', function() {
    sendFile();
});

document.querySelector('.modal .btn-cancel').addEventListener('click', function() {
    uploadPreview.style.display = 'none';
    currentFile = null;
});

document.querySelector('.modal .close').addEventListener('click', function() {
    uploadPreview.style.display = 'none';
    currentFile = null;
}); 