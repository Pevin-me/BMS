from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_socketio import SocketIO, emit
from sensor_reader import BMSSensorReader
import threading
import time
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import csv
from flask import Response

app = Flask(__name__)
app.secret_key = os.urandom(24)
socketio = SocketIO(app)

# Initialize sensor reader
sensor_reader = BMSSensorReader()

def sensor_reading_thread():
    while True:
        try:
            sensor_data = sensor_reader.read_all_sensors()
            voltage = sensor_data.get('battery_voltage', 0.0)
            current = sensor_data.get('current', 0.0)
            power = sensor_data.get('power', 0.0)
            temperature = sensor_data.get('temperature', None)
            # Ignore negative values
            if voltage < 0:
                voltage = 0.0
            if current < 0:
                current = 0.0
            if power < 0:
                power = 0.0
            data = {
                'voltage': voltage,
                'current': current,
                'power': power,
                'temperature': temperature,
                'status': 'normal',
                'timestamp': sensor_data.get('timestamp')
            }
            # ...rest of the thread logic...

            # Check for anomalies
            if data['temperature'] is not None and data['temperature'] > 40:
                data['status'] = "temperature_anomaly"
            if data['voltage'] < 3.6 or data['voltage'] > 4.1:
                data['status'] = "voltage_anomaly"

            # Save to database
            conn = sqlite3.connect('bms.db')
            c = conn.cursor()
            c.execute('''INSERT INTO battery_data 
                        (voltage, current, power, temperature, status)
                        VALUES (?, ?, ?, ?, ?)''',
                        (data['voltage'], 
                         data['current'], 
                         data['power'], 
                         data['temperature'], 
                         data['status']))
            conn.commit()
            conn.close()

            # Emit to all connected clients
            socketio.emit('battery_update', data)

            # Check for anomalies and send notifications
            if data['status'] != "normal":
                notification = {
                    'message': f"Anomaly detected: {data['status'].replace('_', ' ')}",
                    'level': 'warning',
                    'timestamp': time.strftime("%H:%M:%S")
                }
                socketio.emit('notification', notification)

        except Exception as e:
            print(f"Sensor reading failed: {e}")

        time.sleep(1)  # Adjust interval as needed

# Start the real sensor background thread when the app starts
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

@app.route('/contact-admin', methods=['GET', 'POST'])
def contact_admin():
    if request.method == 'POST':
        first_name = request.form.get('FirstName', '')
        last_name = request.form.get('LastName', '')
        email = request.form.get('Email', '')
        phone = request.form.get('PhoneNumber', '')
        message = request.form.get('Message', '')
        full_name = f"{first_name} {last_name}"
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

@app.route('/download_csv')
def download_csv():
    conn = sqlite3.connect('bms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM battery_data ORDER BY timestamp DESC')
    rows = c.fetchall()
    conn.close()

    header = ['id', 'timestamp', 'voltage', 'current', 'power', 'temperature', 'status']

    def generate():
        yield ','.join(header) + '\n'
        for row in rows:
            yield ','.join([str(x) if x is not None else '' for x in row]) + '\n'

    return Response(generate(), mimetype='text/csv',
                    headers={"Content-Disposition": "attachment;filename=battery_data.csv"})

@app.route('/history')
def history():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = sqlite3.connect('bms.db')
    c = conn.cursor()
    c.execute('SELECT * FROM battery_data ORDER BY timestamp DESC LIMIT 20')
    rows = c.fetchall()
    conn.close()

    data = [
        {
            'id': row[0],
            'timestamp': row[1],
            'voltage': row[2],
            'current': row[3],
            'power': row[4],
            'temperature': row[5],
            'status': row[6]
        }
        for row in rows
    ]
    return render_template('history.html', data=data)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

