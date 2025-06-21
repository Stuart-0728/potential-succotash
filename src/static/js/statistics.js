document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});

function initializeCharts() {
    // 设置全局Chart.js配置
    Chart.defaults.font.family = "'Segoe UI', 'Microsoft YaHei', sans-serif";
    Chart.defaults.color = '#6c757d';
    Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    Chart.defaults.plugins.tooltip.padding = 10;
    Chart.defaults.plugins.tooltip.cornerRadius = 6;
    Chart.defaults.plugins.legend.labels.usePointStyle = true;
    
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // 活动报名统计图表
            const registrationCtx = document.getElementById('registrationChart').getContext('2d');
            new Chart(registrationCtx, {
                type: 'doughnut',
                data: {
                    labels: data.registration_stats.labels,
                    datasets: [{
                        data: data.registration_stats.data,
                        backgroundColor: [
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(255, 99, 132, 0.8)'
                        ],
                        borderColor: [
                            'rgba(54, 162, 235, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 2,
                        hoverOffset: 15
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    cutout: '65%',
                    layout: {
                        padding: 20
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                boxWidth: 12,
                                boxHeight: 12
                            }
                        },
                        title: {
                            display: true,
                            text: '活动状态分布',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    animation: {
                        animateScale: true,
                        animateRotate: true,
                        duration: 1000
                    }
                }
            });

            // 学生参与度图表
            const participationCtx = document.getElementById('participationChart').getContext('2d');
            new Chart(participationCtx, {
                type: 'pie',
                data: {
                    labels: data.participation_stats.labels,
                    datasets: [{
                        data: data.participation_stats.data,
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(255, 99, 132, 0.8)'
                        ],
                        borderColor: [
                            'rgba(75, 192, 192, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 2,
                        hoverOffset: 15
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    layout: {
                        padding: 20
                    },
                    plugins: {
                        legend: {
                            position: 'bottom',
                            labels: {
                                padding: 15,
                                boxWidth: 12,
                                boxHeight: 12
                            }
                        },
                        title: {
                            display: true,
                            text: '学生参与情况',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.raw || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                    return `${label}: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    animation: {
                        animateScale: true,
                        animateRotate: true,
                        duration: 1000
                    }
                }
            });

            // 月度统计图表 - 使用双Y轴解决数量级不同的问题
            const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
            new Chart(monthlyCtx, {
                type: 'bar',
                data: {
                    labels: data.monthly_stats.labels,
                    datasets: [
                        {
                            label: '活动数量',
                            data: data.monthly_stats.activities,
                            backgroundColor: 'rgba(54, 162, 235, 0.7)',
                            borderColor: 'rgba(54, 162, 235, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            yAxisID: 'y-activities'
                        },
                        {
                            label: '报名人数',
                            data: data.monthly_stats.registrations,
                            backgroundColor: 'rgba(255, 99, 132, 0.7)',
                            borderColor: 'rgba(255, 99, 132, 1)',
                            borderWidth: 1,
                            borderRadius: 4,
                            yAxisID: 'y-registrations'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    layout: {
                        padding: {
                            top: 10,
                            right: 25,
                            bottom: 10,
                            left: 10
                        }
                    },
                    interaction: {
                        mode: 'index',
                        intersect: false
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                            labels: {
                                padding: 15,
                                boxWidth: 12,
                                boxHeight: 12
                            }
                        },
                        title: {
                            display: true,
                            text: '活动和报名趋势',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        }
                    },
                    scales: {
                        'y-activities': {
                            type: 'linear',
                            position: 'left',
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '活动数量',
                                color: 'rgba(54, 162, 235, 1)'
                            },
                            grid: {
                                display: false
                            },
                            ticks: {
                                precision: 0,
                                color: 'rgba(54, 162, 235, 1)'
                            }
                        },
                        'y-registrations': {
                            type: 'linear',
                            position: 'right',
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: '报名人数',
                                color: 'rgba(255, 99, 132, 1)'
                            },
                            grid: {
                                display: false
                            },
                            ticks: {
                                precision: 0,
                                color: 'rgba(255, 99, 132, 1)'
                            }
                        },
                        x: {
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('加载统计数据失败:', error);
            document.querySelectorAll('canvas').forEach(canvas => {
                const ctx = canvas.getContext('2d');
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.font = '14px "Microsoft YaHei", sans-serif';
                ctx.fillStyle = '#dc3545';
                ctx.textAlign = 'center';
                ctx.fillText('加载数据失败，请刷新页面重试', canvas.width/2, canvas.height/2);
            });
        });
    // 扩展统计：标签热度和积分分布
    fetch('/api/statistics_ext')
        .then(response => response.json())
        .then(ext => {
            // 标签热度
            const tagHeatCtx = document.getElementById('tagHeatChart').getContext('2d');
            new Chart(tagHeatCtx, {
                type: 'bar',
                data: {
                    labels: ext.tag_heat.labels,
                    datasets: [{
                        label: '活动数',
                        data: ext.tag_heat.data,
                        backgroundColor: 'rgba(255, 206, 86, 0.7)',
                        borderColor: 'rgba(255, 206, 86, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                        hoverBackgroundColor: 'rgba(255, 206, 86, 0.9)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    indexAxis: 'y',
                    layout: {
                        padding: {
                            top: 10,
                            right: 10,
                            bottom: 10,
                            left: 10
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        title: { 
                            display: true, 
                            text: '标签热度（按活动数）',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        }
                    },
                    scales: { 
                        y: { 
                            grid: {
                                display: false
                            }
                        },
                        x: { 
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                precision: 0
                            }
                        } 
                    }
                }
            });
            
            // 积分分布 - 修复百分比计算
            const pointsDistCtx = document.getElementById('pointsDistChart').getContext('2d');
            
            // 计算学生总数
            const totalStudents = ext.points_dist.data.reduce((a, b) => a + b, 0);
            
            // 计算每个区间的百分比
            const percentages = ext.points_dist.data.map(count => 
                totalStudents > 0 ? ((count / totalStudents) * 100).toFixed(1) : 0
            );
            
            new Chart(pointsDistCtx, {
                type: 'bar',
                data: {
                    labels: ext.points_dist.labels,
                    datasets: [{
                        label: '学生数',
                        data: ext.points_dist.data,
                        backgroundColor: 'rgba(54, 162, 235, 0.7)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                        hoverBackgroundColor: 'rgba(54, 162, 235, 0.9)'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    layout: {
                        padding: {
                            top: 10,
                            right: 10,
                            bottom: 10,
                            left: 10
                        }
                    },
                    plugins: {
                        legend: { display: false },
                        title: { 
                            display: true, 
                            text: '积分分布',
                            font: {
                                size: 16,
                                weight: 'bold'
                            },
                            padding: {
                                top: 10,
                                bottom: 20
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const value = context.raw || 0;
                                    const percentage = percentages[context.dataIndex];
                                    return `学生数: ${value} (${percentage}%)`;
                                }
                            }
                        }
                    },
                    scales: { 
                        y: { 
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.05)'
                            },
                            ticks: {
                                precision: 0
                            },
                            title: {
                                display: true,
                                text: '学生数量'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            title: {
                                display: true,
                                text: '积分区间'
                            }
                        }
                    }
                }
            });
        })
        .catch(error => {
            console.error('加载扩展统计数据失败:', error);
            ['tagHeatChart', 'pointsDistChart'].forEach(id => {
                const canvas = document.getElementById(id);
                if (canvas) {
                    const ctx = canvas.getContext('2d');
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                    ctx.font = '14px "Microsoft YaHei", sans-serif';
                    ctx.fillStyle = '#dc3545';
                    ctx.textAlign = 'center';
                    ctx.fillText('加载数据失败，请刷新页面重试', canvas.width/2, canvas.height/2);
                }
            });
        });
}
