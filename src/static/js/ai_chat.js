/**
 * 师能素质协会 - AI聊天助手
 * 
 * 实现功能：
 * 1. 聊天历史记录的数据库存储和加载
 * 2. 页面间保持聊天记录
 * 3. 会话管理
 * 4. Markdown 格式支持
 */

// 配置参数
const AI_CHAT_CONFIG = {
    cookiePrefix: 'cqnu_ai_chat_',
    maxStoredMessages: 50,  // 最大存储消息数
    cookieExpireDays: 7,    // Cookie保存天数
    initialBotMessage: '您好，欢迎来到重庆师范大学师能素质协会平台，我是基于DeepSeek大语言模型的智能助手，有什么可以帮助您的吗？',
    notLoggedInMessage: '您好！AI助手功能需要登录后使用。请先<a href="/login" class="ai-chat-link">登录</a>或<a href="/register" class="ai-chat-link">注册</a>。'
};

// 智能助手信息
const ASSOCIATION_INFO = {
    name: 'DeepSeek AI智能助手',
    description: '基于DeepSeek大语言模型的智能聊天助手，为师能素质协会平台提供智能服务',
    model: 'deepseek-r1-distill-qwen-7b-250120',
    capabilities: [
        '回答关于活动的问题',
        '推荐适合您兴趣的活动',
        '提供活动参与和报名流程指导',
        '分析参与历史和积分情况',
        '提供平台使用帮助'
    ],
    contactInfo: {
        address: '重庆市沙坪坝区大学城中路37号',
        qqGroup: '995213034',
        adminEmail: '2023051101095@stu.cqnu.edu.cn',
        website: 'http://shineng.cqnu.edu.cn'
    },
    features: [
        '实时对话', '历史记录保存', '个性化推荐', '多轮交互', '上下文理解'
    ],
    disclaimer: '本助手基于人工智能技术，回答可能并非完全准确，如有疑问请联系管理员'
};

// 在文件开头添加marked库的动态加载
function loadMarkedLibrary() {
    return new Promise((resolve, reject) => {
        // 检查是否已加载
        if (window.marked) {
            resolve(window.marked);
            return;
        }
        
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
        script.onload = () => resolve(window.marked);
        script.onerror = () => reject(new Error('Failed to load Marked library'));
        document.head.appendChild(script);
    });
}

// 会话管理
class AIChatSession {
    constructor() {
        this.sessionId = this.getOrCreateSessionId();
        this.messages = [];
        this.isOpen = false;
        // 初始化时从后端加载历史记录
        this.loadMessagesFromServer();
    }

    // 获取或创建会话ID
    getOrCreateSessionId() {
        let sessionId = this.getCookie('session_id');
        if (!sessionId) {
            sessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 15);
            this.setCookie('session_id', sessionId, AI_CHAT_CONFIG.cookieExpireDays);
        }
        return sessionId;
    }

    // 添加消息
    addMessage(content, role) {
        const message = {
            role: role,
            content: content,
            timestamp: new Date().toISOString()
        };
        
        this.messages.push(message);
        
        // 如果消息超过最大存储数，删除最早的消息
        if (this.messages.length > AI_CHAT_CONFIG.maxStoredMessages) {
            this.messages = this.messages.slice(this.messages.length - AI_CHAT_CONFIG.maxStoredMessages);
        }
        
        return message;
    }

    // 清除所有消息
    clearMessages() {
        this.messages = [];
        // 调用后端API清除历史记录
        fetch(`/api/ai_chat/clear?session_id=${this.sessionId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .catch(error => console.error('清除历史记录失败:', error));
    }
    
    // 清除用户所有会话历史记录
    clearAllHistory() {
        this.messages = [];
        // 调用后端API清除所有历史记录
        fetch('/api/ai_chat/clear_history', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                console.log(`清除历史记录成功: ${data.message}`);
                // 删除cookie中的消息记录
                this.deleteCookie('messages');
            } else {
                console.error(`清除历史记录失败: ${data.message}`);
            }
        })
        .catch(error => console.error('清除所有历史记录失败:', error));
    }
    
    // 获取所有消息
    getMessages() {
        return this.messages;
    }
    
    // 从后端加载消息历史
    loadMessagesFromServer() {
        // 先尝试从Cookie加载，作为备用方案
        const cookieMessages = this.loadMessagesFromCookie();
        if (cookieMessages) {
            this.messages = cookieMessages;
        }
        
        // 从后端API加载历史记录
        fetch(`/api/ai_chat/history?session_id=${this.sessionId}`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('加载历史记录失败');
                }
                return response.json();
            })
            .then(data => {
                if (data.success && data.data && data.data.length > 0) {
                    this.messages = data.data;
                    // 如果有UI实例，刷新UI
                    if (window.aiChat && window.aiChat.ui) {
                        window.aiChat.ui.refreshMessages();
                    }
                }
            })
            .catch(error => {
                console.error('从服务器加载历史记录失败:', error);
                // 如果从服务器加载失败，就使用Cookie中的数据（如果有）
            });
    }
    
    // 从Cookie加载消息（作为备用方案）
    loadMessagesFromCookie() {
        const messagesJson = this.getCookie('messages');
        return messagesJson ? JSON.parse(messagesJson) : null;
    }
    
    // 保存消息到Cookie（作为备用方案）
    saveMessagesToCookie() {
        const messagesJson = JSON.stringify(this.messages);
        this.setCookie('messages', messagesJson, AI_CHAT_CONFIG.cookieExpireDays);
    }
    
    // 设置Cookie
    setCookie(name, value, days) {
        let expires = '';
        if (days) {
            const date = new Date();
            date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
            expires = '; expires=' + date.toUTCString();
        }
        document.cookie = AI_CHAT_CONFIG.cookiePrefix + name + '=' + encodeURIComponent(value) + expires + '; path=/';
    }
    
    // 获取Cookie
    getCookie(name) {
        const nameEQ = AI_CHAT_CONFIG.cookiePrefix + name + '=';
        const ca = document.cookie.split(';');
        for (let i = 0; i < ca.length; i++) {
            let c = ca[i];
            while (c.charAt(0) === ' ') c = c.substring(1, c.length);
            if (c.indexOf(nameEQ) === 0) 
                return decodeURIComponent(c.substring(nameEQ.length, c.length));
        }
        return null;
    }
    
    // 删除Cookie
    deleteCookie(name) {
        this.setCookie(name, '', -1);
    }
}

// AI聊天UI管理
class AIChatUI {
    constructor(session) {
        this.session = session;
        this.container = document.getElementById('aiChatContainer');
        this.messagesContainer = document.getElementById('aiChatMessages');
        this.input = document.getElementById('aiChatInput');
        this.sendButton = document.getElementById('aiSendButton');
        this.toggleButton = document.querySelector('.ai-chat-button');
        
        this.setupEventListeners();
        this.initialize();
    }
    
    // 初始化
    initialize() {
        // 清空现有消息区域
        this.clearMessagesUI();
        
        // 如果有保存的消息，则加载消息
        const messages = this.session.getMessages();
        
        // 如果没有历史消息，添加初始欢迎消息
        if (messages.length === 0) {
            this.addMessageToUI(AI_CHAT_CONFIG.initialBotMessage, 'bot');
        } else {
            // 加载保存的消息
            this.refreshMessages();
        }
        
        // 恢复聊天窗口状态
        const isOpen = this.session.getCookie('chat_open') === 'true';
        if (isOpen) {
            // 初始化时如果应该打开，直接设置样式而不使用动画
            this.container.style.display = 'flex';
            this.container.classList.add('visible');
            this.session.isOpen = true;
            this.scrollToBottom();
        } else {
            // 确保窗口是关闭的
            this.container.style.display = 'none';
            this.container.classList.remove('visible');
            this.session.isOpen = false;
        }
    }
    
    // 刷新消息显示
    refreshMessages() {
        // 清空消息区域
        this.clearMessagesUI();
        
        // 加载消息
        const messages = this.session.getMessages();
        messages.forEach(msg => {
            this.addMessageToUI(msg.content, msg.role === 'user' ? 'user' : 'bot');
        });
        
        // 滚动到最新消息
        this.scrollToBottom();
    }
    
    // 设置事件监听器
    setupEventListeners() {
        // 发送按钮点击事件
        if (this.sendButton) {
            this.sendButton.addEventListener('click', (e) => {
                e.preventDefault(); // 防止表单提交
                e.stopPropagation(); // 阻止事件冒泡
                this.sendMessage();
            });
        }
        
        // 输入框回车事件
        if (this.input) {
            this.input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault(); // 防止默认的换行行为
                    this.sendMessage();
                }
            });
        }
        
        // 切换聊天窗口按钮事件
        if (this.toggleButton) {
            this.toggleButton.addEventListener('click', () => {
                // 防止快速多次点击
                if (this.isToggling) return;
                this.toggleChat();
            });
        }
        
        // 添加关闭按钮事件监听
        const closeButton = document.getElementById('aiChatCloseBtn');
        if (closeButton) {
            closeButton.addEventListener('click', (e) => {
                e.preventDefault(); // 防止表单提交
                e.stopPropagation(); // 阻止事件冒泡
                this.closeChat();
            });
        }
    }
    
    // 切换聊天窗口显示/隐藏
    toggleChat() {
        // 防抖处理
        if (this.isToggling) return;
        this.isToggling = true;
        
        if (this.container.style.display === 'none' || this.container.style.display === '') {
            this.openChat();
        } else {
            this.closeChat();
        }
        
        // 300ms后重置标志位，防止频繁切换
        setTimeout(() => {
            this.isToggling = false;
        }, 300);
    }
    
    // 打开聊天窗口
    openChat() {
        // 先设置display为flex，然后添加visible类触发过渡动画
        this.container.style.display = 'flex';
        // 等待浏览器渲染一帧后添加visible类，触发过渡效果
        setTimeout(() => {
            this.container.classList.add('visible');
        }, 10);
        
        this.session.isOpen = true;
        this.session.setCookie('chat_open', 'true', AI_CHAT_CONFIG.cookieExpireDays);
        
        // 滚动到最新消息
        setTimeout(() => {
            this.scrollToBottom();
        }, 100);
    }
    
    // 关闭聊天窗口
    closeChat() {
        // 先移除visible类触发过渡动画
        this.container.classList.remove('visible');
        // 等待过渡动画完成后隐藏元素
        setTimeout(() => {
            this.container.style.display = 'none';
        }, 300); // 与CSS过渡时间一致
        
        this.session.isOpen = false;
        this.session.setCookie('chat_open', 'false', AI_CHAT_CONFIG.cookieExpireDays);
    }
    
    // 发送消息
    sendMessage() {
        if (!this.input) return;
        
        const message = this.input.value.trim();
        if (!message) return;
        
        // 清空输入框
        this.input.value = '';
        
        // 添加用户消息到UI
        this.addMessageToUI(message, 'user');
        
        // 添加消息到会话
        this.session.addMessage(message, 'user');
        
        // 禁用输入和按钮
        this.disableInput(true);
        
        // 准备接收AI响应
        this.receiveAIResponse(message);
    }
    
    // 接收AI响应
    receiveAIResponse(userMessage) {
        // 创建AI消息容器
        const aiMessageDiv = document.createElement('div');
        aiMessageDiv.className = 'ai-message bot';
        this.messagesContainer.appendChild(aiMessageDiv);
        
        // 滚动到底部
        this.scrollToBottom();
        
        // 显示加载指示器
        aiMessageDiv.innerHTML = '<span class="loading-indicator">AI思考中<span class="dot-animation">...</span></span>';
        
        // 检查用户是否已登录
        const isLoggedIn = document.body.getAttribute('data-user-logged-in') === 'true';
        
        if (!isLoggedIn) {
            // 如果未登录，显示登录提示信息
            aiMessageDiv.innerHTML = AI_CHAT_CONFIG.notLoggedInMessage;
            this.disableInput(false);
            return;
        }
        
        // 创建 EventSource 连接
        const role = 'student'; // 默认角色，可扩展
        const eventSource = new EventSource(`/api/ai_chat?message=${encodeURIComponent(userMessage)}&role=${role}&session_id=${this.session.sessionId}`);
        
        // 完整的AI响应文本
        let fullResponse = '';
        let hasError = false;
        let retryCount = 0;
        const MAX_RETRIES = 2;
        
        // 处理消息
        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.error) {
                    hasError = true;
                    aiMessageDiv.textContent = `错误: ${data.error}`;
                    eventSource.close();
                    this.disableInput(false);
                    this.input.focus();
                } else if (data.content) {
                    // 移除加载指示器
                    if (fullResponse === '') {
                        aiMessageDiv.innerHTML = '';
                    }
                    
                    fullResponse += data.content;
                    
                    // 使用Markdown渲染响应
                    if (window.marked) {
                        aiMessageDiv.innerHTML = window.marked.parse(fullResponse);
                    } else {
                        // 如果marked未加载，尝试加载
                        loadMarkedLibrary()
                            .then(marked => {
                                aiMessageDiv.innerHTML = marked.parse(fullResponse);
                            })
                            .catch(err => {
                                console.error('Markdown渲染失败:', err);
                                aiMessageDiv.textContent = fullResponse;
                            });
                    }
                    
                    // 为新添加的链接添加样式和目标
                    const links = aiMessageDiv.querySelectorAll('a');
                    links.forEach(link => {
                        if (!link.classList.contains('ai-chat-link')) {
                            link.classList.add('ai-chat-link');
                        }
                        link.setAttribute('target', '_blank');
                    });
                    
                    this.scrollToBottom();
                }
            } catch (e) {
                console.error('解析AI响应失败:', e);
            }
        };
        
        // 处理结束
        eventSource.addEventListener('done', () => {
            eventSource.close();
            
            // 存储AI响应到会话
            if (fullResponse) {
                this.session.addMessage(fullResponse, 'assistant');
                // 备份到Cookie
                this.session.saveMessagesToCookie();
            } else if (!hasError) {
                // 如果没有响应但也没有错误，显示一个提示
                aiMessageDiv.textContent = '抱歉，AI没有返回响应。请重试。';
            }
            
            this.disableInput(false);
            this.input.focus();
        });
        
        // 处理错误
        eventSource.onerror = () => {
            eventSource.close();
            
            if (retryCount < MAX_RETRIES && !hasError && !fullResponse) {
                // 尝试重新连接
                retryCount++;
                aiMessageDiv.innerHTML = `<span class="loading-indicator">连接中断，正在重试 (${retryCount}/${MAX_RETRIES})<span class="dot-animation">...</span></span>`;
                
                setTimeout(() => {
                    // 重新创建连接
                    this.receiveAIResponse(userMessage);
                }, 1000 * retryCount); // 逐步增加重试间隔
                
                return;
            }
            
            if (!aiMessageDiv.textContent || aiMessageDiv.textContent.includes('AI思考中') || aiMessageDiv.textContent.includes('连接中断')) {
                aiMessageDiv.textContent = '抱歉，服务出现错误，请稍后再试。';
            }
            this.disableInput(false);
            this.input.focus();
        };
    }
    
    // 添加消息到UI
    addMessageToUI(text, type) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `ai-message ${type}`;
        
        // 根据不同类型处理内容
        if (type === 'bot') {
            // 使用marked库渲染Markdown（如果已加载）
            if (window.marked) {
                messageDiv.innerHTML = window.marked.parse(text);
            } else {
                // 尝试加载marked库
                loadMarkedLibrary()
                    .then(marked => {
                        messageDiv.innerHTML = marked.parse(text);
                    })
                    .catch(err => {
                        console.error('Markdown渲染失败:', err);
                        messageDiv.textContent = text;
                    });
            }
        } else {
            // 用户消息不渲染Markdown
            messageDiv.textContent = text;
        }
        
        this.messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
        
        // 为消息中的链接添加点击事件
        if (type === 'bot') {
            const links = messageDiv.querySelectorAll('a');
            links.forEach(link => {
                if (!link.classList.contains('ai-chat-link')) {
                    link.classList.add('ai-chat-link');
                }
                link.setAttribute('target', '_blank');
            });
        }
    }
    
    // 清空消息UI
    clearMessagesUI() {
        while (this.messagesContainer.firstChild) {
            this.messagesContainer.removeChild(this.messagesContainer.firstChild);
        }
    }
    
    // 滚动到底部
    scrollToBottom() {
        this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
    }
    
    // 禁用/启用输入
    disableInput(disabled) {
        if (this.input) this.input.disabled = disabled;
        if (this.sendButton) this.sendButton.disabled = disabled;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    // 加载Markdown库
    loadMarkedLibrary().catch(err => console.warn('Markdown库加载失败:', err));
    
    // 初始化会话
    const chatSession = new AIChatSession();
    
    // 初始化UI
    const chatUI = new AIChatUI(chatSession);
    
    // 将对象挂到全局以便调试和外部访问
    window.aiChat = {
        session: chatSession,
        ui: chatUI,
        config: AI_CHAT_CONFIG,
        associationInfo: ASSOCIATION_INFO,
        
        // 公共API
        clearHistory: () => {
            chatSession.clearMessages();
            chatUI.clearMessagesUI();
            chatUI.addMessageToUI(AI_CHAT_CONFIG.initialBotMessage, 'bot');
        },
        
        // 清除所有会话历史
        clearAllHistory: () => {
            chatSession.clearAllHistory();
            chatUI.clearMessagesUI();
            chatUI.addMessageToUI(AI_CHAT_CONFIG.initialBotMessage, 'bot');
        },
        
        // 获取协会信息
        getAssociationInfo: () => ASSOCIATION_INFO,
        
        // 设置初始消息
        setInitialMessage: (message) => {
            AI_CHAT_CONFIG.initialBotMessage = message;
        }
    };
});

// 添加样式
document.addEventListener('DOMContentLoaded', () => {
    // 创建样式元素
    const style = document.createElement('style');
    style.textContent = `
        .ai-chat-link {
            color: #1a73e8;
            text-decoration: underline;
            cursor: pointer;
        }
        
        .ai-message.bot a {
            color: #1a73e8;
            text-decoration: underline;
        }
        
        .ai-message.bot strong, 
        .ai-message.bot b {
            font-weight: bold;
        }
        
        .ai-message.bot em,
        .ai-message.bot i {
            font-style: italic;
        }
        
        .ai-message.bot code {
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: monospace;
        }
        
        .ai-message.bot pre {
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        
        .ai-message.bot pre code {
            background-color: transparent;
            padding: 0;
        }
        
        .ai-message.bot ul, 
        .ai-message.bot ol {
            margin-left: 20px;
            padding-left: 0;
        }
        
        .ai-message.bot blockquote {
            border-left: 3px solid #ddd;
            margin-left: 0;
            padding-left: 10px;
            color: #555;
        }
    `;
    document.head.appendChild(style);
}); 