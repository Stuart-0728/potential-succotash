// 主要JavaScript功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化Bootstrap提示工具
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // 初始化图表（如果存在）
    initializeCharts();

    // 活动签到功能
    setupAttendanceCheckin();

    // 搜索功能优化
    setupSearchOptimization();

    // 通知系统
    // 检查是否已登录（通过查找用户菜单）
    const userMenu = document.querySelector('.user-menu');
    
    if (userMenu) {
        // 获取未读重要通知
        fetchUnreadNotifications();
        
        // 设置定时刷新（每5分钟）
        setInterval(fetchUnreadNotifications, 5 * 60 * 1000);
    }
    
    // 为所有通知关闭按钮添加事件监听
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('notification-close')) {
            const notificationId = e.target.getAttribute('data-notification-id');
            const banner = e.target.closest('.notification-banner');
            
            if (notificationId) {
                markNotificationAsRead(notificationId);
            }
            
            if (banner) {
                banner.style.height = banner.offsetHeight + 'px';
                setTimeout(() => {
                    banner.style.height = '0';
                    banner.style.padding = '0';
                    banner.style.margin = '0';
                    banner.style.overflow = 'hidden';
                    banner.style.borderWidth = '0';
                }, 10);
                
                setTimeout(() => {
                    banner.remove();
                }, 500);
            }
        }
    });

    // 检查是否有通知需要显示
    displayNotifications();
    
    // 处理删除确认
    setupDeleteConfirmation();
    
    // 处理签到表单
    setupCheckinForm();
    
    // 处理活动倒计时
    setupCountdowns();

    // 初始化Toast通知系统
    initToastSystem();
    
    // 初始化全局加载动画
    initGlobalLoading();
    
    // 为所有表单添加加载动画
    setupFormLoading();

    // 为所有按钮添加加载状态
    setupLoadingButtons();

    // 重置所有按钮状态（解决浏览器返回问题）
    resetAllButtonStates();
    
    // 监听浏览器前进/后退事件
    window.addEventListener('pageshow', function(event) {
        // 当页面从浏览器缓存中加载时（例如使用后退按钮）
        if (event.persisted) {
            console.log('页面从缓存加载，重置按钮状态');
            resetAllButtonStates();
        }
    });
    
    // 监听popstate事件（浏览器前进/后退按钮）
    window.addEventListener('popstate', function(event) {
        console.log('浏览器导航事件，重置按钮状态');
        resetAllButtonStates();
    });
    
    // 监听页面可见性变化
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            console.log('页面变为可见，重置按钮状态');
            resetAllButtonStates();
        }
    });

    // 特别处理登录按钮
    setupLoginButton();
});

// 初始化全局加载动画
function initGlobalLoading() {
    // 创建加载动画元素
    const loadingEl = document.createElement('div');
    loadingEl.className = 'global-loading';
    loadingEl.innerHTML = `
        <div class="spinner"></div>
        <div class="message">加载中...</div>
    `;
    document.body.appendChild(loadingEl);
    
    // 添加全局显示/隐藏加载的函数
    window.showLoading = function(message = '加载中...') {
        const loadingEl = document.querySelector('.global-loading');
        if (loadingEl) {
            const messageEl = loadingEl.querySelector('.message');
            if (messageEl) {
                messageEl.textContent = message;
            }
            loadingEl.classList.add('show');
            
            // 设置一个安全超时，确保加载动画不会永远显示
            if (window.loadingTimeout) {
                clearTimeout(window.loadingTimeout);
            }
            
            window.loadingTimeout = setTimeout(() => {
                window.hideLoading();
                console.log('安全超时：自动隐藏加载动画');
            }, 15000); // 15秒后自动隐藏
        }
    };
    
    window.hideLoading = function() {
        const loadingEl = document.querySelector('.global-loading');
        if (loadingEl) {
            loadingEl.classList.remove('show');
            
            // 清除超时
            if (window.loadingTimeout) {
                clearTimeout(window.loadingTimeout);
                window.loadingTimeout = null;
            }
        }
    };
    
    // 监听页面加载完成事件，确保隐藏加载动画
    window.addEventListener('load', function() {
        window.hideLoading();
    });
    
    // 监听页面卸载前事件，显示加载动画
    window.addEventListener('beforeunload', function(event) {
        // 检查是否是导航到管理页面
        const activeElement = document.activeElement;
        if (activeElement && activeElement.tagName === 'A' && 
            activeElement.getAttribute('href') && 
            (activeElement.getAttribute('href').includes('/admin/') || 
             !activeElement.hasAttribute('data-no-loading'))) {
            window.showLoading('页面加载中...');
        }
    });
    
    // 监听页面可见性变化
    document.addEventListener('visibilitychange', function() {
        if (document.visibilityState === 'visible') {
            // 如果页面变为可见，检查加载状态是否悬挂
            setTimeout(() => {
                // 如果加载动画显示超过5秒，自动隐藏
                const loadingEl = document.querySelector('.global-loading');
                if (loadingEl && loadingEl.classList.contains('show')) {
                    console.log('页面可见性变化：自动隐藏加载动画');
                    window.hideLoading();
                }
            }, 1000);
        }
    });
}

// 为所有表单添加加载动画
function setupFormLoading() {
    document.addEventListener('submit', function(e) {
        const form = e.target;
        
        // 排除特定表单（如搜索表单）
        if (form.classList.contains('no-loading') || 
            form.id === 'search-form' || 
            form.getAttribute('data-no-loading') === 'true' ||
            form.id === 'tagsForm' ||
            form.action?.includes('/tags/') ||  // 标签相关操作
            form.id === 'editTagForm') {
            return;
        }
        
        // 获取表单提交按钮
        const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
        if (submitBtn) {
            // 保存原始内容
            const originalContent = submitBtn.innerHTML || submitBtn.value;
            
            // 检查是否为登录表单
            const isLoginForm = form.action && (
                form.action.includes('/login') || 
                form.querySelector('input[name="username"]') && form.querySelector('input[name="password"]')
            );
            
            // 检查是否为注册表单
            const isRegisterForm = form.action && form.action.includes('/register');
            
            // 根据表单类型设置不同的加载文本
            let loadingText = '处理中...';
            if (isLoginForm) {
                loadingText = '登录中...';
            } else if (isRegisterForm) {
                loadingText = '注册中...';
            }
            
            // 替换为加载图标
            if (submitBtn.tagName === 'INPUT') {
                submitBtn.value = loadingText;
            } else {
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + loadingText;
            }
            submitBtn.disabled = true;
            
            // 保存原始内容到按钮属性中
            if (submitBtn.tagName === 'INPUT') {
                submitBtn.setAttribute('data-original-value', originalContent);
            } else {
                submitBtn.setAttribute('data-original-text', originalContent);
            }
            
            // 对于登录表单，不设置自动恢复，让服务器端处理结果
            if (!isLoginForm) {
                // 提交完成后恢复按钮状态
                setTimeout(function() {
                    // 如果10秒后表单还在页面上，恢复按钮状态
                    if (document.body.contains(submitBtn)) {
                        if (submitBtn.tagName === 'INPUT') {
                            submitBtn.value = originalContent;
                        } else {
                            submitBtn.innerHTML = originalContent;
                        }
                        submitBtn.disabled = false;
                    }
                }, 10000);
            }
        } else {
            // 如果没有找到提交按钮，显示全局加载动画
            showLoading('提交中...');
            
            // 10秒后自动隐藏
            setTimeout(hideLoading, 10000);
        }
    });
    
    // 为所有AJAX请求添加全局加载指示器
    setupAjaxLoading();
}

// 为AJAX请求添加全局加载指示器
function setupAjaxLoading() {
    // 保存原始的XMLHttpRequest
    const originalXHR = window.XMLHttpRequest;
    
    // 创建一个计数器来跟踪活动的AJAX请求
    let activeRequests = 0;
    
    // 替换XMLHttpRequest
    window.XMLHttpRequest = function() {
        const xhr = new originalXHR();
        
        // 覆盖open方法
        const originalOpen = xhr.open;
        xhr.open = function() {
            // 检查是否需要显示加载动画
            const url = arguments[1];
            
            // 默认不显示全局加载动画，除非特别指定
            xhr.showLoading = false;
            
            // 只有特定请求才显示全局加载动画
            const includeUrls = [
                '/admin/backup',
                '/admin/reset',
                '/admin/export',
                '/admin/import',
                '/admin/students',
                '/admin/student/'
            ];
            
            // 检查是否是需要显示全局加载的请求
            if (includeUrls.some(included => url.includes(included))) {
                xhr.showLoading = true;
            }
            
            // 检查是否有data-show-global-loading属性
            const activeElement = document.activeElement;
            if (activeElement && activeElement.hasAttribute('data-show-global-loading')) {
                xhr.showLoading = true;
            }
            
            // 标记特殊请求，避免处理302重定向错误
            xhr.isSpecialRequest = url.includes('/student/api/messages/unread_count') || 
                                  url.includes('/api/notifications/unread') ||
                                  url.includes('/admin/') || 
                                  url.includes('/student/') ||
                                  url.includes('/api/') ||
                                  url.includes('/auth/');
            
            return originalOpen.apply(this, arguments);
        };
        
        // 覆盖send方法
        const originalSend = xhr.send;
        xhr.send = function() {
            if (xhr.showLoading) {
                activeRequests++;
                if (activeRequests === 1) {
                    // 第一个请求开始时显示加载动画
                    window.showLoading();
                }
            }
            
            // 处理请求完成
            xhr.addEventListener('loadend', function() {
                if (xhr.showLoading) {
                    activeRequests--;
                    if (activeRequests === 0) {
                        // 所有请求完成时隐藏加载动画
                        window.hideLoading();
                    }
                }
                
                // 处理权限错误
                if (xhr.status === 401 || xhr.status === 403) {
                    // 如果是特殊请求，忽略处理
                    if (xhr.isSpecialRequest) {
                        console.log('特殊请求状态码:', xhr.status, '- 忽略处理');
                        return;
                    }
                    
                    // 如果不是特殊请求，显示权限提示
                    if (xhr.status === 401) {
                        window.showToast('请先登录后再执行此操作', 'warning');
                    } else if (xhr.status === 403) {
                        window.showToast('您没有权限执行此操作', 'warning');
                    }
                }
            });
            
            return originalSend.apply(this, arguments);
        };
        
        // 覆盖原始的onreadystatechange
        const originalOnReadyStateChange = xhr.onreadystatechange;
        xhr.onreadystatechange = function(e) {
            // 如果是特殊请求且返回302或401/403，不做任何处理
            if (xhr.readyState === 4 && xhr.isSpecialRequest && (xhr.status === 302 || xhr.status === 401 || xhr.status === 403)) {
                // 不处理重定向或权限错误
                console.log('特殊请求状态码:', xhr.status, '- 忽略处理');
                return;
            }
            
            // 调用原始的onreadystatechange
            if (originalOnReadyStateChange) {
                originalOnReadyStateChange.call(this, e);
            }
        };
        
        return xhr;
    };
}

// 初始化Toast通知系统
function initToastSystem() {
    // 创建Toast容器
    const toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 start-0 p-3';
    toastContainer.style.zIndex = '1090';
    document.body.appendChild(toastContainer);
    
    // 添加全局showToast函数
    window.showToast = function(message, type = 'info', duration = 3000) {
        const toastId = 'toast-' + Date.now();
        const toast = document.createElement('div');
        toast.className = `toast align-items-center border-0 show`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        toast.id = toastId;
        toast.style.maxWidth = '300px';
        toast.style.fontSize = '0.85rem';
        toast.style.padding = '0.25rem';
        
        // 设置不同类型的背景色
        let bgClass = 'bg-primary';
        switch(type) {
            case 'success': bgClass = 'bg-success'; break;
            case 'error': bgClass = 'bg-danger'; break;
            case 'warning': bgClass = 'bg-warning text-dark'; break;
            case 'info': bgClass = 'bg-info text-dark'; break;
        }
        
        toast.classList.add(bgClass);
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body py-1 px-2">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-1 m-auto" data-bs-dismiss="toast" aria-label="Close" style="font-size: 0.7rem;"></button>
            </div>
        `;
        
        // 添加到容器
        toastContainer.appendChild(toast);
        
        // 添加动画
        toast.style.transform = 'translateY(100%)';
        toast.style.opacity = '0';
        toast.style.transition = 'all 0.3s ease-out';
        
        // 触发重排，然后应用动画
        setTimeout(() => {
            toast.style.transform = 'translateY(0)';
            toast.style.opacity = '1';
        }, 10);
        
        // 添加关闭按钮事件
        const closeBtn = toast.querySelector('.btn-close');
        closeBtn.addEventListener('click', () => {
            closeToast(toastId);
        });
        
        // 自动关闭
        if (duration > 0) {
            setTimeout(() => {
                closeToast(toastId);
            }, duration);
        }
        
        return toastId;
    };
    
    // 关闭Toast的函数
    function closeToast(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.style.transform = 'translateY(100%)';
            toast.style.opacity = '0';
            
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }
    }
    
    // 添加全局closeToast函数
    window.closeToast = closeToast;
}

// 图表初始化函数
function initializeCharts() {
    // 活动统计图表
    const activityChartElement = document.getElementById('activityChart');
    if (activityChartElement) {
        fetch('/api/statistics/activities')
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应异常');
                }
                return response.json();
            })
            .then(data => {
                const ctx = activityChartElement.getContext('2d');
                new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: '活动数量',
                            data: data.values,
                            backgroundColor: 'rgba(54, 162, 235, 0.5)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('获取活动统计数据失败:', error);
                activityChartElement.parentElement.innerHTML = '<div class="alert alert-warning">加载图表数据失败，请刷新页面重试。</div>';
            });
    }

    // 报名统计图表
    const registrationChartElement = document.getElementById('registrationChart');
    if (registrationChartElement) {
        fetch('/api/statistics/registrations')
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应异常');
                }
                return response.json();
            })
            .then(data => {
                const ctx = registrationChartElement.getContext('2d');
                new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            label: '报名人次',
                            data: data.values,
                            backgroundColor: 'rgba(75, 192, 192, 0.5)',
                            borderColor: 'rgba(75, 192, 192, 1)',
                            borderWidth: 2,
                            tension: 0.1
                        }]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('获取报名统计数据失败:', error);
                registrationChartElement.parentElement.innerHTML = '<div class="alert alert-warning">加载图表数据失败，请刷新页面重试。</div>';
            });
    }

    // 学院分布图表
    const collegeChartElement = document.getElementById('collegeChart');
    if (collegeChartElement) {
        fetch('/api/statistics/colleges')
            .then(response => {
                if (!response.ok) {
                    throw new Error('网络响应异常');
                }
                return response.json();
            })
            .then(data => {
                const ctx = collegeChartElement.getContext('2d');
                new Chart(ctx, {
                    type: 'pie',
                    data: {
                        labels: data.labels,
                        datasets: [{
                            data: data.values,
                            backgroundColor: [
                                'rgba(255, 99, 132, 0.7)',
                                'rgba(54, 162, 235, 0.7)',
                                'rgba(255, 206, 86, 0.7)',
                                'rgba(75, 192, 192, 0.7)',
                                'rgba(153, 102, 255, 0.7)',
                                'rgba(255, 159, 64, 0.7)',
                                'rgba(199, 199, 199, 0.7)',
                                'rgba(83, 102, 255, 0.7)',
                                'rgba(40, 159, 64, 0.7)',
                                'rgba(210, 199, 199, 0.7)'
                            ],
                            borderColor: [
                                'rgba(255, 99, 132, 1)',
                                'rgba(54, 162, 235, 1)',
                                'rgba(255, 206, 86, 1)',
                                'rgba(75, 192, 192, 1)',
                                'rgba(153, 102, 255, 1)',
                                'rgba(255, 159, 64, 1)',
                                'rgba(199, 199, 199, 1)',
                                'rgba(83, 102, 255, 1)',
                                'rgba(40, 159, 64, 1)',
                                'rgba(210, 199, 199, 1)'
                            ],
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'right',
                            }
                        }
                    }
                });
            })
            .catch(error => {
                console.error('获取学院分布数据失败:', error);
                collegeChartElement.parentElement.innerHTML = '<div class="alert alert-warning">加载图表数据失败，请刷新页面重试。</div>';
            });
    }
}

// 活动签到功能
function setupAttendanceCheckin() {
    const checkinForm = document.getElementById('checkinForm');
    if (checkinForm) {
        checkinForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const studentId = document.getElementById('studentId').value;
            const activityId = document.getElementById('activityId').value;
            
            if (!studentId || !activityId) {
                alert('请输入学号和活动ID');
                return;
            }
            
            fetch('/api/attendance/checkin', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    student_id: studentId,
                    activity_id: activityId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('签到成功！');
                    document.getElementById('studentId').value = '';
                    // 刷新签到列表
                    if (typeof refreshAttendanceList === 'function') {
                        refreshAttendanceList();
                    }
                } else {
                    alert('签到失败: ' + data.message);
                }
            })
            .catch(error => {
                console.error('签到请求失败:', error);
                alert('签到请求失败，请重试');
            });
        });
    }
}

// 搜索功能优化
function setupSearchOptimization() {
    const searchForms = document.querySelectorAll('form[data-search-form]');
    searchForms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const searchInput = form.querySelector('input[name="search"]');
            if (searchInput && searchInput.value.trim().length < 2 && searchInput.value.trim().length > 0) {
                e.preventDefault();
                alert('搜索关键词至少需要2个字符');
            }
        });
    });
}

// 更新活动状态
function updateActivityStatus(activityId, newStatus) {
    // 找到触发按钮
    const button = event.target.closest('.activity-status-btn');
    if (!button) return;
    
    // 保存原始内容
    const originalContent = button.innerHTML;
    
    // 设置加载状态
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> 处理中...';
    button.disabled = true;
    
    // 获取CSRF令牌
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    
    // 发送请求
    fetch(`/admin/activity/${activityId}/change_status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': csrfToken
        },
        body: `status=${newStatus}&csrf_token=${csrfToken}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 显示成功消息
            showAlert('success', data.message || '活动状态已更新');
            
            // 延迟刷新页面，让用户看到成功消息
            setTimeout(() => {
                location.reload();
            }, 1000);
        } else {
            // 恢复按钮状态
            button.innerHTML = originalContent;
            button.disabled = false;
            
            // 显示错误消息
            showAlert('danger', data.message || '更新活动状态失败');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        
        // 恢复按钮状态
        button.innerHTML = originalContent;
        button.disabled = false;
        
        // 显示错误消息
        showAlert('danger', '更新活动状态时出错');
    });
}

// 报名状态更新
function updateRegistrationStatus(registrationId, newStatus) {
    if (!confirm('确定要更新报名状态吗？')) {
        return;
    }
    
    fetch(`/api/registration/${registrationId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            status: newStatus
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('状态更新成功！');
            window.location.reload();
        } else {
            alert('状态更新失败: ' + data.message);
        }
    })
    .catch(error => {
        console.error('状态更新请求失败:', error);
        alert('状态更新请求失败，请重试');
    });
}

// 通知系统
// 获取未读通知
function fetchUnreadNotifications() {
    fetch('/api/notifications/unread')
        .then(response => {
            if (!response.ok) {
                throw new Error('网络响应异常');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // 更新通知徽章
                updateNotificationBadge(data.notifications.length);
                
                // 显示通知横幅
                if (data.notifications.length > 0) {
                    // 移除旧的通知横幅
                    removeNotificationBanner();
                    
                    // 添加新的通知横幅
                    data.notifications.forEach((notification, index) => {
                        // 错开显示时间，避免所有通知同时出现
                        setTimeout(() => {
                            showNotificationBanner(notification);
                        }, index * 1000); // 每个通知间隔1秒显示
                    });
                }
            }
        })
        .catch(error => {
            console.error('获取未读通知失败:', error);
        });
}

// 更新通知徽章
function updateNotificationBadge(count) {
    const badge = document.querySelector('.notification-badge');
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'inline-block';
        } else {
            badge.style.display = 'none';
        }
    } else {
        // 如果不存在徽章，则创建一个
        const navLinks = document.querySelectorAll('.nav-link');
        navLinks.forEach(link => {
            if (link.href && link.href.includes('/notifications')) {
                const badge = document.createElement('span');
                badge.className = 'badge bg-danger notification-badge';
                badge.style.marginLeft = '5px';
                badge.textContent = count;
                if (count <= 0) {
                    badge.style.display = 'none';
                }
                link.appendChild(badge);
            }
        });
    }
}

// 显示通知横幅
function showNotificationBanner(notification) {
    // 检查是否已存在相同ID的通知横幅
    const existingBanner = document.querySelector(`.notification-banner[data-notification-id="${notification.id}"]`);
    if (existingBanner) {
        return; // 已存在，不再创建
    }
    
    // 检查通知容器是否存在，如果不存在则创建
    let notificationContainer = document.getElementById('notification-container');
    if (!notificationContainer) {
        notificationContainer = document.createElement('div');
        notificationContainer.id = 'notification-container';
        notificationContainer.style.position = 'fixed';
        notificationContainer.style.top = '10px';
        notificationContainer.style.right = '10px';
        notificationContainer.style.maxWidth = '400px';
        notificationContainer.style.zIndex = '9999';
        document.body.appendChild(notificationContainer);
    }
    
    const container = document.createElement('div');
    container.className = 'notification-banner alert alert-primary alert-dismissible fade show';
    container.setAttribute('data-notification-id', notification.id);
    container.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
    container.style.transition = 'all 0.5s ease';
    container.style.marginBottom = '10px';
    container.style.animation = 'slideIn 0.5s ease-out';
    
    container.innerHTML = `
        <strong>${notification.title}</strong>
        <p class="mb-0">${notification.content.length > 100 ? notification.content.substring(0, 100) + '...' : notification.content}</p>
        <button type="button" class="btn-close notification-close" data-notification-id="${notification.id}" aria-label="Close"></button>
        <div class="mt-2">
            <a href="/notification/${notification.id}" class="btn btn-sm btn-primary">查看详情</a>
        </div>
    `;
    
    // 添加动画样式
    const style = document.createElement('style');
    if (!document.getElementById('notification-animation-style')) {
        style.id = 'notification-animation-style';
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            @keyframes fadeOut {
                from {
                    opacity: 1;
                }
                to {
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    notificationContainer.appendChild(container);
    
    // 设置自动关闭（15秒后）
    setTimeout(() => {
        if (container && container.parentNode) {
            container.style.animation = 'fadeOut 0.5s ease-out';
            setTimeout(() => {
                if (container && container.parentNode) {
                    container.parentNode.removeChild(container);
                }
            }, 500);
        }
    }, 15000);
}

// 移除所有通知横幅
function removeNotificationBanner() {
    const banners = document.querySelectorAll('.notification-banner');
    banners.forEach(banner => {
        banner.classList.remove('show');
        setTimeout(() => {
            if (banner.parentNode) {
                banner.parentNode.removeChild(banner);
            }
        }, 500);
    });
}

// 标记通知为已读
function markNotificationAsRead(notificationId) {
    fetch(`/notification/${notificationId}/mark_read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken() // 获取CSRF令牌的函数
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('网络响应异常');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            // 更新通知徽章
            const badge = document.querySelector('.notification-badge');
            if (badge && badge.textContent) {
                const count = parseInt(badge.textContent) - 1;
                updateNotificationBadge(count);
            }
        }
    })
    .catch(error => {
        console.error('标记通知已读失败:', error);
    });
}

// 获取CSRF令牌
function getCsrfToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// 显示通知横幅
function displayNotifications() {
    // 查找页面中的所有通知
    const notifications = document.querySelectorAll('.notification-banner');
    
    if (notifications.length > 0) {
        // 如果有通知，创建通知容器
        let notificationContainer = document.querySelector('.notification-container');
        
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.className = 'notification-container';
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.top = '70px';
            notificationContainer.style.right = '20px';
            notificationContainer.style.zIndex = '1050';
            notificationContainer.style.maxWidth = '350px';
            notificationContainer.style.width = '100%';
            document.body.appendChild(notificationContainer);
        }
        
        // 显示每个通知
        notifications.forEach((notification, index) => {
            const clone = notification.cloneNode(true);
            clone.style.display = 'block';
            clone.style.opacity = '0';
            clone.style.transform = 'translateY(-20px)';
            clone.style.transition = 'all 0.3s ease-in-out';
            
            // 将通知添加到容器中
            notificationContainer.appendChild(clone);
            
            // 延迟显示，使其有动画效果
            setTimeout(() => {
                clone.style.opacity = '1';
                clone.style.transform = 'translateY(0)';
            }, index * 200);
            
            // 添加关闭按钮事件
            const closeBtn = clone.querySelector('.close-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', function() {
                    const notificationId = this.getAttribute('data-notification-id');
                    if (notificationId) {
                        markNotificationAsRead(notificationId);
                    }
                    
                    clone.style.opacity = '0';
                    clone.style.transform = 'translateY(-20px)';
                    
                    setTimeout(() => {
                        clone.remove();
                    }, 300);
                });
            }
            
            // 10秒后自动关闭
            setTimeout(() => {
                if (clone && clone.parentNode) {
                    clone.style.opacity = '0';
                    clone.style.transform = 'translateY(-20px)';
                    
                    setTimeout(() => {
                        if (clone && clone.parentNode) {
                            clone.remove();
                        }
                    }, 300);
                }
            }, 10000 + index * 1000);
        });
    }
}

// 设置删除确认
function setupDeleteConfirmation() {
    document.querySelectorAll('.delete-confirm').forEach(function(button) {
        button.addEventListener('click', function(e) {
            if (!confirm('确定要删除吗？此操作不可撤销。')) {
                e.preventDefault();
            }
        });
    });
}

// 设置签到表单
function setupCheckinForm() {
    const checkinForm = document.getElementById('checkin-form');
    if (checkinForm) {
        checkinForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const formData = new FormData(checkinForm);
            
            fetch('/api/attendance/checkin', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showAlert('success', '签到成功！');
                    // 如果需要，可以更新UI
                } else {
                    showAlert('danger', data.message || '签到失败，请重试');
                }
            })
            .catch(error => {
                console.error('签到请求失败:', error);
                showAlert('danger', '签到请求失败，请重试');
            });
        });
    }
}

// 显示警告信息
function showAlert(type, message) {
    const alertContainer = document.getElementById('alert-container');
    if (!alertContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.setAttribute('role', 'alert');
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.appendChild(alert);
    
    // 5秒后自动关闭
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

// 设置活动倒计时
function setupCountdowns() {
    document.querySelectorAll('[data-countdown]').forEach(function(element) {
        const targetDate = new Date(element.getAttribute('data-countdown')).getTime();
        
        // 更新倒计时
        function updateCountdown() {
            const now = new Date().getTime();
            const distance = targetDate - now;
            
            if (distance < 0) {
                element.textContent = '已截止';
                return;
            }
            
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            
            if (days > 0) {
                element.textContent = `${days}天${hours}小时`;
            } else if (hours > 0) {
                element.textContent = `${hours}小时${minutes}分钟`;
            } else {
                element.textContent = `${minutes}分钟`;
            }
        }
        
        // 立即更新一次
        updateCountdown();
        
        // 每分钟更新一次
        setInterval(updateCountdown, 60000);
    });
}

// 启动特定元素的倒计时
function startCountdown(elementId, targetDateStr) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const targetDate = new Date(targetDateStr).getTime();
    
    function update() {
        const now = new Date().getTime();
        const distance = targetDate - now;
        
        if (distance < 0) {
            element.textContent = '已截止';
            return;
        }
        
        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        
        if (days > 0) {
            element.textContent = `${days}天${hours}小时`;
        } else if (hours > 0) {
            element.textContent = `${hours}小时${minutes}分钟`;
        } else {
            element.textContent = `${minutes}分钟`;
        }
    }
    
    // 立即更新一次
    update();
    
    // 每分钟更新一次
    setInterval(update, 60000);
}

// 为所有按钮添加加载状态
function setupLoadingButtons() {
    // 选择所有可能需要加载状态的按钮
    const actionButtons = document.querySelectorAll('.btn-primary, .btn-outline-primary, .btn-success, .btn-outline-success, .btn-info, .btn-outline-info, .btn-secondary, .btn-outline-secondary');
    
    actionButtons.forEach(button => {
        // 跳过已经设置过的按钮
        if (button.hasAttribute('data-loading-setup')) {
            return;
        }
        
        button.setAttribute('data-loading-setup', 'true');
        
        // 跳过标签选择页面的按钮
        if (button.closest('#tagsForm') || button.closest('.tag-btn') || 
            button.closest('form[data-no-loading="true"]') || 
            button.hasAttribute('data-no-loading')) {
            return;
        }
        
        // 跳过标签管理页面的删除和编辑按钮
        if ((button.onclick && button.onclick.toString().includes('editTag')) || 
            (button.onclick && button.onclick.toString().includes('deleteTag'))) {
            return;
        }
        
        // 特殊处理链接按钮
        if (button.tagName === 'A' && button.getAttribute('href')) {
            button.addEventListener('click', function(e) {
                // 排除某些不需要加载状态的链接
                if (this.getAttribute('data-no-loading') || 
                    this.getAttribute('data-bs-toggle') === 'modal' ||
                    this.getAttribute('href').startsWith('#') ||
                    this.getAttribute('target') === '_blank' ||
                    this.closest('.pagination')) {
                    return;
                }
                
                // 检查是否是下载链接
                const isDownloadLink = this.getAttribute('href').includes('/download') || 
                                      this.getAttribute('href').includes('/export');
                
                // 如果是下载链接，不添加加载状态，因为浏览器会自动处理下载
                if (isDownloadLink) {
                    // 为下载链接添加特殊属性
                    this.setAttribute('data-no-loading', 'true');
                    
                    // 为下载链接添加特殊处理，确保3秒后自动隐藏全局加载状态
                    setTimeout(() => {
                        if (window.hideLoading) {
                            window.hideLoading();
                        }
                        
                        // 恢复按钮状态
                        if (this.classList.contains('disabled')) {
                            this.classList.remove('disabled');
                            if (this.hasAttribute('data-original-text')) {
                                this.innerHTML = this.getAttribute('data-original-text');
                                this.removeAttribute('data-original-text');
                            }
                        }
                    }, 3000);
                    return;
                }
                
                // 添加加载状态
                const originalText = this.innerHTML;
                
                // 检查是否为特定按钮
                const isViewAllBtn = this.textContent.includes('查看全部') || 
                                     this.textContent.includes('浏览活动') || 
                                     this.getAttribute('href').includes('/activities');
                const isLoginBtn = this.textContent.includes('登录') || 
                                   this.getAttribute('href').includes('/login');
                
                // 对特定按钮使用更明显的加载状态
                if (isViewAllBtn || isLoginBtn || this.classList.contains('btn-lg')) {
                    // 存储原始文本，以便在页面卸载时恢复
                    this.setAttribute('data-original-text', originalText);
                    
                    // 添加加载状态
                    this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + 
                                     (isViewAllBtn ? '加载活动...' : 
                                      isLoginBtn ? '正在登录...' : '加载中...');
                    this.classList.add('disabled');
                    
                    // 添加属性防止全局加载动画
                    this.setAttribute('data-no-global-loading', 'true');
                    
                    // 为大页面跳转显示全局加载动画
                    if (this.getAttribute('href').includes('/admin/')) {
                        window.showLoading('页面加载中...');
                    }
                    
                    // 添加页面卸载事件监听，确保在页面跳转前保持按钮状态
                    window.addEventListener('beforeunload', function() {
                        // 在页面卸载前保持按钮状态
                    }, { once: true });
                    
                    // 安全超时：如果10秒后仍未跳转，恢复按钮状态
                    setTimeout(() => {
                        if (document.body.contains(this) && this.classList.contains('disabled')) {
                            this.classList.remove('disabled');
                            if (this.hasAttribute('data-original-text')) {
                                this.innerHTML = this.getAttribute('data-original-text');
                            }
                        }
                    }, 10000);
                } else {
                    // 存储原始文本，以便在页面卸载时恢复
                    this.setAttribute('data-original-text', originalText);
                    
                    // 添加加载状态
                    this.classList.add('btn-loading');
                    
                    // 添加属性防止全局加载动画
                    this.setAttribute('data-no-global-loading', 'true');
                }
                
                // 如果8秒后页面还没有跳转，恢复按钮状态
                setTimeout(() => {
                    if (document.body.contains(this)) {
                        if (this.classList.contains('disabled')) {
                            this.classList.remove('disabled');
                            this.innerHTML = originalText;
                        }
                        if (this.classList.contains('btn-loading')) {
                            this.classList.remove('btn-loading');
                            this.innerHTML = originalText;
                        }
                    }
                }, 8000);
            });
            
            return;
        }
        
        button.addEventListener('click', function(e) {
            // 如果是分页按钮、模态框按钮或带有特定属性的按钮，不添加加载状态
            if (this.closest('.pagination') || 
                this.getAttribute('data-bs-toggle') === 'modal' || 
                this.hasAttribute('data-no-loading') ||
                (this.type === 'button' && !this.classList.contains('btn-export'))) {
                return;
            }
            
            // 特殊处理导出按钮
            const isExportButton = this.textContent.includes('导出') || 
                                  this.innerHTML.includes('fa-download') ||
                                  this.classList.contains('btn-export');
            
            if (isExportButton || this.getAttribute('href')?.includes('export')) {
                // 保存原始内容
                const originalText = this.innerHTML;
                
                // 存储原始文本，以便在页面卸载时恢复
                this.setAttribute('data-original-text', originalText);
                
                // 添加加载状态
                this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> 处理中...';
                this.classList.add('disabled');
                
                // 添加属性防止全局加载动画
                this.setAttribute('data-no-global-loading', 'true');
                
                // 恢复按钮状态（如果页面加载时间过长）
                setTimeout(() => {
                    if (document.body.contains(this)) {
                        if (this.classList.contains('disabled')) {
                            this.classList.remove('disabled');
                            this.innerHTML = originalText;
                        }
                    }
                    // 确保隐藏全局加载状态
                    if (window.hideLoading) {
                        window.hideLoading();
                    }
                }, 5000); // 导出操作可能需要更长时间
                
                return;
            }
            
            // 保存原始内容
            const originalText = this.innerHTML;
            
            // 存储原始文本，以便在页面卸载时恢复
            this.setAttribute('data-original-text', originalText);
            
            // 添加加载状态
            this.classList.add('btn-loading');
            
            // 添加属性防止全局加载动画
            this.setAttribute('data-no-global-loading', 'true');
            
            // 恢复按钮状态（如果页面加载时间过长）
            setTimeout(() => {
                if (document.body.contains(this)) {
                    if (this.classList.contains('btn-loading')) {
                        this.classList.remove('btn-loading');
                        this.innerHTML = originalText;
                    }
                }
            }, 5000);
        });
    });
}

// 重置所有按钮状态
function resetAllButtonStates() {
    console.log('重置所有按钮状态');
    
    // 重置所有带有加载状态的按钮
    document.querySelectorAll('.btn-loading').forEach(function(button) {
        button.classList.remove('btn-loading');
        if (button.hasAttribute('data-original-text')) {
            button.innerHTML = button.getAttribute('data-original-text');
            // 清除存储的原始文本，防止重复使用
            button.removeAttribute('data-original-text');
        }
    });
    
    // 重置所有禁用的按钮
    document.querySelectorAll('button.disabled, a.disabled').forEach(function(button) {
        // 排除应该保持禁用状态的按钮
        if (button.hasAttribute('disabled') && button.getAttribute('disabled') !== 'false') {
            return;
        }
        
        button.classList.remove('disabled');
        
        // 恢复原始内容
        if (button.hasAttribute('data-original-text')) {
            button.innerHTML = button.getAttribute('data-original-text');
            // 清除存储的原始文本，防止重复使用
            button.removeAttribute('data-original-text');
        }
    });
    
    // 重置所有包含spinner的按钮
    document.querySelectorAll('button .spinner-border, a .spinner-border').forEach(function(spinner) {
        const button = spinner.closest('button, a');
        if (button && button.hasAttribute('data-original-text')) {
            button.innerHTML = button.getAttribute('data-original-text');
            button.classList.remove('disabled');
            // 清除存储的原始文本，防止重复使用
            button.removeAttribute('data-original-text');
        }
    });
    
    // 重置所有下拉菜单按钮
    document.querySelectorAll('.dropdown-toggle').forEach(function(button) {
        if (button.hasAttribute('data-original-text')) {
            button.innerHTML = button.getAttribute('data-original-text');
            button.classList.remove('disabled');
            // 清除存储的原始文本，防止重复使用
            button.removeAttribute('data-original-text');
        }
    });
    
    // 重置所有表单提交按钮
    document.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function(button) {
        button.disabled = false;
        if (button.tagName === 'BUTTON' && button.hasAttribute('data-original-text')) {
            button.innerHTML = button.getAttribute('data-original-text');
            button.removeAttribute('data-original-text');
        } else if (button.tagName === 'INPUT' && button.hasAttribute('data-original-value')) {
            button.value = button.getAttribute('data-original-value');
            button.removeAttribute('data-original-value');
        }
    });
    
    // 隐藏全局加载状态
    if (window.hideLoading) {
        window.hideLoading();
    }
}

// 特别处理登录按钮
function setupLoginButton() {
    const loginBtn = document.querySelector('.login-btn');
    if (loginBtn) {
        loginBtn.addEventListener('click', function(e) {
            // 检查表单是否有效
            const form = this.closest('form');
            if (form && form.checkValidity()) {
                // 保存原始文本
                const originalText = this.value || this.innerHTML;
                this.setAttribute('data-original-text', originalText);
                
                // 添加加载动画
                const loadingText = this.getAttribute('data-loading-text') || '正在登录...';
                if (this.tagName === 'INPUT') {
                    this.value = loadingText;
                } else {
                    this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span> ' + loadingText;
                }
                
                // 禁用按钮
                this.disabled = true;
                this.classList.add('disabled');
                
                // 显示全局加载动画
                window.showLoading('登录中...');
                
                // 如果10秒后仍未跳转，恢复按钮状态
                setTimeout(() => {
                    if (document.body.contains(this)) {
                        this.disabled = false;
                        this.classList.remove('disabled');
                        if (this.tagName === 'INPUT') {
                            this.value = originalText;
                        } else {
                            this.innerHTML = originalText;
                        }
                        window.hideLoading();
                    }
                }, 10000);
            }
        });
    }
}

