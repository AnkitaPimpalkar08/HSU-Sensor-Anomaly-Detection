#!/usr/bin/env python3
# level3_auto_pump.py
# full automation with relay control, pump, and web dashboard
import time
import csv
import os
import sys
import smtplib
import getpass
from datetime import datetime
from email.mime.text import MIMEText
import RPi.GPIO as GPIO
from flask import Flask, render_template_string, jsonify
import threading

# pins
SENSOR = 17
RELAY = 23

# settings - adjust for your plant
PUMP_TIME = 30        # seconds to run pump
COOLDOWN = 600        # seconds between waterings (10 min)
DRY_COUNT = 3         # dry readings needed

# email
EMAIL_FROM = ""
EMAIL_PASS = ""
EMAIL_TO = ""

LOG_FILE = "watering_log.csv"

# tracking
email_sent = False
last_water = None
dry_counter = 0
current_state = "UNKNOWN"
pump_running = False

# flask app for dashboard
app = Flask(__name__)

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
    GPIO.setup(RELAY, GPIO.OUT)
    GPIO.output(RELAY, GPIO.LOW)

def read():
    val = GPIO.input(SENSOR)
    if val == 1:
        return "DRY", val
    else:
        return "WET", val

def ready_to_water():
    if last_water is None:
        return True
    elapsed = (datetime.now() - last_water).total_seconds()
    return elapsed >= COOLDOWN

def time_remaining():
    if last_water is None:
        return 0, 0
    elapsed = (datetime.now() - last_water).total_seconds()
    remaining = max(0, COOLDOWN - elapsed)
    mins = int(remaining // 60)
    secs = int(remaining % 60)
    return mins, secs

def run_pump():
    global last_water, pump_running
    
    pump_running = True
    mins = PUMP_TIME // 60
    secs = PUMP_TIME % 60
 
    if mins > 0:
        print(f"\n  💧 PUMPING for {mins}m {secs}s")
    else:
        print(f"\n  💧 PUMPING for {secs} seconds")
    
    GPIO.output(RELAY, GPIO.HIGH)
    time.sleep(PUMP_TIME)
    GPIO.output(RELAY, GPIO.LOW)
    
    last_water = datetime.now()
    pump_running = False
    cooldown_min = COOLDOWN // 60
    print(f"  ✓ Done! Next watering in {cooldown_min} minutes\n")

def send_email():
    try:
        mins = PUMP_TIME // 60
        secs = PUMP_TIME % 60
        cooldown_min = COOLDOWN // 60
        
        if mins > 0:
            duration = f"{mins}m {secs}s"
        else:
            duration = f"{secs} seconds"
        
        body = f"Plant watered for {duration}.\n\nNext watering cycle in {cooldown_min} minutes."
        msg = MIMEText(body)
        msg["Subject"] = "🌱 Plant Watered"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)
        s.quit()
        
        print("  📧 Email sent")
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def log_data(timestamp, state, val, action=""):
    if not os.path.exists(LOG_FILE):
        f = open(LOG_FILE, "w", newline="")
        w = csv.writer(f)
        w.writerow(["timestamp", "state", "raw_value", "action"])
        f.close()
    
    f = open(LOG_FILE, "a", newline="")
    w = csv.writer(f)
    w.writerow([timestamp.isoformat(), state, val, action])
    f.close()

def get_email_credentials():
    """Prompt user for email credentials interactively"""
    global EMAIL_FROM, EMAIL_PASS, EMAIL_TO
    
    print("\n" + "=" * 60)
    print("  📧 EMAIL SETUP")
    print("=" * 60)
    print("\n  To receive alerts, please provide your Gmail credentials:")
    print("  (App Password required - visit: myaccount.google.com/apppasswords)\n")
    
    # Get email from
    EMAIL_FROM = input("  Enter your Gmail address: ").strip()
    
    # Get password (hidden)
    EMAIL_PASS = getpass.getpass("  Enter your App Password (hidden): ").strip()
    
    # Get email to
    email_to_input = input("  Send alerts to (press Enter for same): ").strip()
    EMAIL_TO = email_to_input if email_to_input else EMAIL_FROM
    
    print("\n  ✓ Credentials saved for this session")
    print("=" * 60)
    
    # Validate entries
    if not EMAIL_FROM or not EMAIL_PASS:
        print("\n Error: Email and password are required!")
        sys.exit(1)

# web dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Plant Watering System</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .card {
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            text-align: center;
            color: #2c3e50;
        }
        .status {
            text-align: center;
            font-size: 48px;
            font-weight: bold;
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }
        .dry { background: #ffebee; color: #c62828; }
        .wet { background: #e3f2fd; color: #1565c0; }
        .pumping { background: #fff3e0; color: #ef6c00; }
        .info {
            display: flex;
            justify-content: space-around;
            margin: 20px 0;
        }
        .info-box {
            text-align: center;
            flex: 1;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            margin: 0 10px;
        }
        .info-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
        }
        .info-value {
            font-size: 20px;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }
        button {
            width: 100%;
            padding: 15px;
            font-size: 18px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            margin-top: 20px;
        }
        button:hover {
            background: #45a049;
        }
        button:active {
            transform: scale(0.98);
        }
    </style>
</head>
<body>
    <div class="card">
        <h1>🌱 Plant Watering System</h1>
        
        <div id="status" class="status">Loading...</div>
        
        <div class="info">
            <div class="info-box">
                <div class="info-label">LAST WATERED</div>
                <div id="last-water" class="info-value">Never</div>
            </div>
            <div class="info-box">
                <div class="info-label">COOLDOWN</div>
                <div id="cooldown" class="info-value">Ready</div>
            </div>
        </div>
        
        <button onclick="waterNow()">💧 Manual Water</button>
    </div>
    
    <script>
        function updateStatus() {
            fetch('/status')
                .then(r => r.json())
                .then(data => {
                    let statusDiv = document.getElementById('status');
                    
                    if (data.pumping) {
                        statusDiv.textContent = '💧 PUMPING';
                        statusDiv.className = 'status pumping';
                    } else if (data.state === 'DRY') {
                        statusDiv.textContent = '🔴 DRY';
                        statusDiv.className = 'status dry';
                    } else {
                        statusDiv.textContent = '🔵 WET';
                        statusDiv.className = 'status wet';
                    }
                    
                    document.getElementById('last-water').textContent = data.last_water;
                    document.getElementById('cooldown').textContent = data.cooldown;
                });
        }
        
        function waterNow() {
            fetch('/water', { method: 'POST' })
                .then(r => r.json())
                .then(data => alert(data.message));
        }
        
        updateStatus();
        setInterval(updateStatus, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/status')
def status():
    mins, secs = time_remaining()
    
    if mins > 0 or secs > 0:
        cooldown_str = f"{mins}m {secs}s"
    else:
        cooldown_str = "Ready"
    
    if last_water:
        last_str = last_water.strftime('%I:%M %p')
    else:
        last_str = "Never"
    
    return jsonify({
        'state': current_state,
        'pumping': pump_running,
        'last_water': last_str,
        'cooldown': cooldown_str
    })

@app.route('/water', methods=['POST'])
def manual_water():
    if not ready_to_water():
        mins, secs = time_remaining()
        return jsonify({'message': f'Still in cooldown ({mins}m {secs}s left)'})
    
    # run pump in separate thread
    threading.Thread(target=run_pump).start()
    return jsonify({'message': 'Watering started!'})

def run_dashboard():
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def main():
    global email_sent, dry_counter, current_state
    global EMAIL_FROM, EMAIL_PASS, EMAIL_TO
    
    # Check if email credentials are in environment variables
    EMAIL_FROM = os.environ.get('SOIL_EMAIL_FROM', '')
    EMAIL_PASS = os.environ.get('SOIL_EMAIL_PASSWORD', '')
    EMAIL_TO = os.environ.get('SOIL_EMAIL_TO', '')
    
    # If not in environment, ask user interactively
    if not EMAIL_FROM or not EMAIL_PASS:
        get_email_credentials()
    
    setup()
    
    print("\n" + "=" * 60)
    print("  LEVEL 3: AUTOMATIC WATERING + DASHBOARD")
    print("=" * 60)
    print(f"  ⏱️  Pump time: {PUMP_TIME} seconds")
    print(f"  ⏳ Cooldown: {COOLDOWN // 60} minutes")
    print(f"  📧 Email: {EMAIL_TO}")
    print(f"  🌐 Dashboard: http://raspberrypi.local:5000")
    print("=" * 60)
    print("\n  🚀 Starting system...\n")
    
    # start dashboard in background
    dashboard_thread = threading.Thread(target=run_dashboard)
    dashboard_thread.daemon = True
    dashboard_thread.start()
    
    last_print = 0
    
    try:
        while True:
            state, val = read()
            current_state = state
            t = datetime.now()
            action = ""
            
            # count dry readings
            if state == "DRY":
                dry_counter += 1
            else:
                dry_counter = 0
            
            # print status every 30 sec
            now = time.time()
            if now - last_print >= 30:
                mins, secs = time_remaining()
                
                if mins > 0 or secs > 0:
                    print(f"  [{t.strftime('%H:%M')}] {state} - Cooldown: {mins}m {secs}s")
                else:
                    print(f"  [{t.strftime('%H:%M')}] {state} - Ready")
                
                last_print = now
            
            # auto watering logic
            if dry_counter >= DRY_COUNT and ready_to_water():
                action = "WATERED"
                run_pump()
                
                if not email_sent:
                    send_email()
                    email_sent = True
                
                dry_counter = 0
                last_print = 0
            
            # reset email flag
            if state == "WET":
                email_sent = False
            
            log_data(t, state, val, action)
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n  ✓ System stopped\n")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
