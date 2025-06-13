// Initialize Socket.io connection
const socket = io();

// Notification handling
function showNotification(message, level = 'info') {
    const container = document.getElementById('notificationContainer');
    if (!container) return;
    
    const notification = document.createElement('div');
    notification.className = `notification animate__animated animate__fadeInRight ${level}`;
    notification.innerHTML = `
        <div class="notification-icon">
            ${level === 'warning' ? '<i class="fas fa-exclamation-triangle"></i>' : '<i class="fas fa-info-circle"></i>'}
        </div>
        <div class="notification-content">
            <p>${message}</p>
            <small>Just now</small>
        </div>
        <button class="notification-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    container.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('animate__fadeOutRight');
        setTimeout(() => notification.remove(), 500);
    }, 5000);
}

// Request notification permission
document.addEventListener('DOMContentLoaded', () => {
    if ('Notification' in window) {
        Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
                console.log('Notification permission granted');
            }
        });
    }
});

// Handle battery updates from server
// Handle battery updates from server
socket.on('battery_update', function(data) {
    // Update all displayed values
    document.getElementById('voltageValue').textContent = data.battery_voltage.toFixed(2) + ' V';
    document.getElementById('currentValue').textContent = data.current.toFixed(3) + ' A';
    document.getElementById('powerValue').textContent = data.power.toFixed(2) + ' W';
    
    if (data.temperature !== null) {
        document.getElementById('temperatureValue').textContent = data.temperature.toFixed(1) + ' °C';
    }
    
    //document.getElementById('lastUpdateTime').textContent = data.timestamp;
    
    // Update status indicators
    updateStatusIndicator('voltage', data.battery_voltage >= 3.6 && data.battery_voltage <= 4.1);
    
    if (data.temperature !== null) {
        updateStatusIndicator('temperature', data.temperature <= 38);
    }
    
    updateSystemStatus(data.status === 'normal');
    
    // Update last anomaly if needed
    if (data.status !== 'normal') {
        document.getElementById('lastAnomaly').textContent = 
            `${data.timestamp} (${data.status.replace('_', ' ')})`;
    }
    
    // Add data to charts
    if (window.combinedChart && window.tempChart) {
        addChartData(window.combinedChart, [data.battery_voltage, data.current]);
        
        if (data.temperature !== null) {
            addChartData(window.tempChart, [data.temperature]);
        }
    }
});

// Handle notifications from server
socket.on('notification', function(notification) {
    showNotification(notification.message, notification.level);
    
    // Show browser notification if permission is granted
    if (Notification.permission === 'granted') {
        new Notification('BMS Alert', {
            body: notification.message,
            icon: '/static/images/battery-icon.png'
        });
    }
});

function updateDashboard(data) {
    // Update voltage display
    const voltageElement = document.getElementById('voltageValue');
    if (voltageElement) voltageElement.textContent = `${data.voltage} V`;
    
    // Update current display
    const currentElement = document.getElementById('currentValue');
    if (currentElement) currentElement.textContent = `${data.current} A`;
    
    // Update power display
    const powerElement = document.getElementById('powerValue');
    if (powerElement) powerElement.textContent = `${data.power} W`;
    
    // Update temperature display
    const tempElement = document.getElementById('temperatureValue');
    if (tempElement) tempElement.textContent = `${data.temperature} °C`;
    
    // Update timestamp
    const timeElement = document.getElementById('lastUpdateTime');
    if (timeElement) timeElement.textContent = data.timestamp;
    
    // Update status indicators
    updateStatusIndicator('voltage', data.voltage >= 3.6 && data.voltage <= 4.1);
    updateStatusIndicator('temperature', data.temperature <= 38);
    updateSystemStatus(data.status === 'normal');
    
    // Update last anomaly
    if (data.status !== 'normal') {
        const anomalyElement = document.getElementById('lastAnomaly');
        if (anomalyElement) {
            anomalyElement.textContent = `${data.timestamp} (${data.status.replace('_', ' ')})`;
        }
    }
}

function updateStatusIndicator(metric, isNormal) {
    const elements = document.querySelectorAll(`.metric-card .status`);
    if (!elements.length) return;
    
    elements.forEach(el => {
        if (el.textContent.toLowerCase().includes(metric)) {
            el.className = isNormal ? 'status good' : 'status bad';
            el.textContent = isNormal ? 'Normal' : 'Warning';
        }
    });
}

function updateSystemStatus(isNormal) {
    const indicator = document.querySelector('.status-indicator');
    const statusText = document.querySelector('.system-status span');
    
    if (indicator) {
        indicator.className = isNormal ? 'status-indicator status-good' : 'status-indicator status-warning';
    }
    
    if (statusText) {
        statusText.textContent = `System Status: ${isNormal ? 'Normal' : 'Warning'}`;
    }
}

function addChartData(chart, newData) {
    if (chart.data.datasets.length > 1) {
        // For combined chart
        chart.data.datasets[0].data.push(newData[0]);
        chart.data.datasets[1].data.push(newData[1]);
    } else {
        // For single dataset charts
        chart.data.datasets[0].data.push(newData[0]);
    }
    
    chart.data.labels.push('');
    
    // Limit data points to 20
    if (chart.data.datasets[0].data.length > 20) {
        chart.data.datasets.forEach(dataset => {
            dataset.data.shift();
        });
        chart.data.labels.shift();
    }
    
    chart.update();
}

// Initialize time selector buttons
document.addEventListener('DOMContentLoaded', () => {
    const timeButtons = document.querySelectorAll('.time-selector button');
    timeButtons.forEach(button => {
        button.addEventListener('click', function() {
            timeButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            // Here you would typically fetch new data for the selected time range
        });
    });
});