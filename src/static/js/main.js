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
    // 检查是否是学生用户页面
    const isStudentPage = document.body.classList.contains('student-page');
    
    if (isStudentPage) {
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
// 获取未读重要通知
function fetchUnreadNotifications() {
    fetch('/student/api/notifications/unread')
        .then(response => response.json())
        .then(data => {
            if (data.success && data.notifications && data.notifications.length > 0) {
                updateNotificationBadge(data.notifications.length);
                showNotificationBanner(data.notifications[0]);
            } else {
                updateNotificationBadge(0);
                removeNotificationBanner();
            }
        })
        .catch(error => {
            console.error('获取通知失败:', error);
        });
}

// 更新通知徽章
function updateNotificationBadge(count) {
    const badge = document.querySelector('.notification-badge');
    
    if (badge) {
        if (count > 0) {
            badge.textContent = count;
            badge.style.display = 'flex';
        } else {
            badge.style.display = 'none';
        }
    }
}

// 显示通知横幅
function showNotificationBanner(notification) {
    // 检查是否已经存在通知横幅
    let banner = document.querySelector('.notification-banner');
    
    if (!banner) {
        banner = document.createElement('div');
        banner.className = 'notification-banner important';
        banner.style.transition = 'all 0.5s ease';
        
        const content = document.createElement('div');
        content.className = 'notification-content text-center';
        content.innerHTML = `<strong>${notification.title}:</strong> ${notification.content}`;
        
        const closeBtn = document.createElement('button');
        closeBtn.className = 'close-btn notification-close';
        closeBtn.setAttribute('data-notification-id', notification.id);
        closeBtn.innerHTML = '&times;';
        
        banner.appendChild(content);
        banner.appendChild(closeBtn);
        
        // 添加到页面顶部
        document.body.insertBefore(banner, document.body.firstChild);
    } else {
        // 更新现有横幅内容
        const content = banner.querySelector('.notification-content');
        if (content) {
            content.innerHTML = `<strong>${notification.title}:</strong> ${notification.content}`;
        }
        
        const closeBtn = banner.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.setAttribute('data-notification-id', notification.id);
        }
    }
}

// 移除通知横幅
function removeNotificationBanner() {
    const banner = document.querySelector('.notification-banner');
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

// 标记通知为已读
function markNotificationAsRead(notificationId) {
    fetch(`/student/notification/${notificationId}/mark_read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('通知已标记为已读');
            // 重新获取未读通知
            fetchUnreadNotifications();
        }
    })
    .catch(error => {
        console.error('标记通知失败:', error);
    });
}
