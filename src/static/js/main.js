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
});

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

// 活动状态更新
function updateActivityStatus(activityId, newStatus) {
    if (!confirm('确定要更新活动状态吗？')) {
        return;
    }
    
    fetch(`/api/activity/${activityId}/status`, {
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
    // 检查是否有通知元素
    var notificationContainer = document.querySelector('.notification-container');
    if (!notificationContainer) {
        // 创建通知容器
        notificationContainer = document.createElement('div');
        notificationContainer.className = 'notification-container position-fixed top-0 start-0 end-0 p-2 d-flex flex-column align-items-center';
        notificationContainer.style.zIndex = '1050';
        document.body.appendChild(notificationContainer);
    }
    
    // 如果页面上有公共通知，可以在这里添加额外的处理
    var publicNotifications = document.querySelectorAll('.public-notification');
    if (publicNotifications.length > 0) {
        // 公共通知已经在页面上显示，不需要额外处理
        console.log('公共通知已在页面上显示');
    }
    
    // 获取未读通知（如果用户已登录）
    if (typeof isAuthenticated !== 'undefined' && isAuthenticated) {
        fetch('/api/notifications/unread')
            .then(response => response.json())
            .then(data => {
                if (data.notifications && data.notifications.length > 0) {
                    // 显示通知数量徽章
                    updateNotificationBadge(data.notifications.length);
                    
                    // 显示最新的通知作为横幅
                    showNotificationBanner(data.notifications[0]);
                }
            })
            .catch(error => console.error('获取通知失败:', error));
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

