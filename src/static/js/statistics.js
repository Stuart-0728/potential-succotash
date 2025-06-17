document.addEventListener('DOMContentLoaded', function() {
    initializeCharts();
});

function initializeCharts() {
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // 活动报名统计图表
            const registrationCtx = document.getElementById('registrationChart').getContext('2d');
            new Chart(registrationCtx, {
                type: 'pie',
                data: {
                    labels: data.registration_stats.labels,
                    datasets: [{
                        data: data.registration_stats.data,
                        backgroundColor: [
                            'rgba(54, 162, 235, 0.7)',
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(255, 99, 132, 0.7)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        },
                        title: {
                            display: true,
                            text: '活动状态分布'
                        }
                    }
                }
            });

            // 学生参与度图表
            const participationCtx = document.getElementById('participationChart').getContext('2d');
            new Chart(participationCtx, {
                type: 'doughnut',
                data: {
                    labels: data.participation_stats.labels,
                    datasets: [{
                        data: data.participation_stats.data,
                        backgroundColor: [
                            'rgba(75, 192, 192, 0.7)',
                            'rgba(255, 99, 132, 0.7)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'bottom',
                        },
                        title: {
                            display: true,
                            text: '学生参与情况'
                        }
                    }
                }
            });

            // 月度统计图表
            const monthlyCtx = document.getElementById('monthlyChart').getContext('2d');
            new Chart(monthlyCtx, {
                type: 'line',
                data: {
                    labels: data.monthly_stats.labels,
                    datasets: [
                        {
                            label: '活动数量',
                            data: data.monthly_stats.activities,
                            borderColor: 'rgba(54, 162, 235, 1)',
                            backgroundColor: 'rgba(54, 162, 235, 0.2)',
                            fill: true
                        },
                        {
                            label: '报名人数',
                            data: data.monthly_stats.registrations,
                            borderColor: 'rgba(255, 99, 132, 1)',
                            backgroundColor: 'rgba(255, 99, 132, 0.2)',
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: true,
                            text: '活动和报名趋势'
                        }
                    },
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
            console.error('加载统计数据失败:', error);
            document.querySelectorAll('canvas').forEach(canvas => {
                canvas.getContext('2d').font = '14px Arial';
                canvas.getContext('2d').fillText('加载数据失败，请刷新页面重试', 10, 30);
            });
        });
}
