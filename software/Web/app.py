from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit
from sensor_reader import BMSSensorReader
import threading
import time
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
socketio = SocketIO(app)

# Initialize sensor reader
sensor_reader = BMSSensorReader()

def sensor_reading_thread():
    """Background thread that reads sensors and emits updates"""
    while True:
        sensor_data = sensor_reader.read_all_sensors()
        
        # Check for anomalies
        status = "normal"
        if sensor_data['temperature'] and sensor_data['temperature'] > 40:
            status = "temperature_anomaly"
        if sensor_data['battery_voltage'] < 3.6 or sensor_data['battery_voltage'] > 4.1:
            status = "voltage_anomaly"
        
        # Add status to data
        sensor_data['status'] = status
        
        # Save to database
        conn = sqlite3.connect('bms.db')
        c = conn.cursor()
        c.execute('''INSERT INTO battery_data 
                    (voltage, current, power, temperature, status)
                    VALUES (?, ?, ?, ?, ?)''',
                    (sensor_data['battery_voltage'], 
                     sensor_data['current'], 
                     sensor_data['power'], 
                     sensor_data['temperature'], 
                     status))
        conn.commit()
        conn.close()
        
        # Emit to all connected clients
        socketio.emit('battery_update', sensor_data)
        
        # Check for anomalies and send notifications
        if status != "normal":
            notification = {
                'message': f"Anomaly detected: {status.replace('_', ' ')}",
                'level': 'warning',
                'timestamp': time.strftime("%H:%M:%S")
            }
            socketio.emit('notification', notification)
        
        time.sleep(2)  # Adjust interval as needed

# Start the background thread when the app starts
threading.Thread(target=sensor_reading_thread, daemon=True).start()

# Database setup
def init_db():
    conn = sqlite3.connect('bms.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 email TEXT)''')
    
    # Add default users if they don't exist
    try:
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                 ('admin', generate_password_hash('admin123')))
        c.execute("INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
                 ('user1', generate_password_hash('password1')))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Users already exist
    
    # Create battery data table
    c.execute('''CREATE TABLE IF NOT EXISTS battery_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                 voltage REAL,
                 current REAL,
                 power REAL,
                 temperature REAL,
                 status TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

# Mock user data (in production, use proper database)
users = {
    'admin': generate_password_hash('admin123'),
    'user1': generate_password_hash('password1')
}

# Simulated battery data (replace with actual sensor readings)
def generate_battery_data():
    while True:
        voltage = round(random.uniform(3.5, 4.2), 2)
        current = round(random.uniform(0.5, 2.5), 2)
        power = round(voltage * current, 2)
        temperature = round(random.uniform(25, 40), 1)
        
        # Check for anomalies
        status = "normal"
        if voltage < 3.6 or voltage > 4.1:
            status = "voltage_anomaly"
        elif temperature > 38:
            status = "temperature_anomaly"
        
        data = {
            'voltage': voltage,
            'current': current,
            'power': power,
            'temperature': temperature,
            'status': status,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save to database
        conn = sqlite3.connect('bms.db')
        c = conn.cursor()
        c.execute('''INSERT INTO battery_data 
                    (voltage, current, power, temperature, status)
                    VALUES (?, ?, ?, ?, ?)''',
                    (voltage, current, power, temperature, status))
        conn.commit()
        conn.close()
        
        # Emit to all connected clients
        socketio.emit('battery_update', data)
        
        # Check for anomalies and send notifications
        if status != "normal":
            notification = {
                'message': f"Anomaly detected: {status.replace('_', ' ')}",
                'level': 'warning',
                'timestamp': datetime.now().strftime("%H:%M:%S")
            }
            socketio.emit('notification', notification)
        
        time.sleep(2)

# Start background thread for simulated data
data_thread = Thread(target=generate_battery_data)
data_thread.daemon = True
data_thread.start()

@app.route('/contact-admin', methods=['GET', 'POST'])
def contact_admin():
    if request.method == 'POST':
        # Process form submission
        name = request.form.get('name')
        email = request.form.get('email')
        message = request.form.get('message')
        
        # Here you would typically send an email or save to database
        flash('Your message has been sent to the administrator')
        return redirect(url_for('login'))
    
    return render_template('contact_admin.html')

@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('bms.db')
        c = conn.cursor()
        c.execute('SELECT password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        conn.close()
        
        if user and check_password_hash(user[0], password):
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get latest battery data
    conn = sqlite3.connect('bms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM battery_data ORDER BY timestamp DESC LIMIT 1')
    latest_data = c.fetchone()
    conn.close()
    
    if latest_data:
        data = {
            'voltage': latest_data[2],
            'current': latest_data[3],
            'power': latest_data[4],
            'temperature': latest_data[5],
            'status': latest_data[6],
            'timestamp': latest_data[1]
        }
    else:
        data = None
    
    return render_template('dashboard.html', 
                         username=session['username'],
                         data=data)

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/api/battery_data')
def get_battery_data():
    conn = sqlite3.connect('bms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM battery_data ORDER BY timestamp DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()
    
    data = []
    for row in rows:
        data.append({
            'id': row[0],
            'timestamp': row[1],
            'voltage': row[2],
            'current': row[3],
            'power': row[4],
            'temperature': row[5],
            'status': row[6]
        })
    
    return jsonify(data)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)