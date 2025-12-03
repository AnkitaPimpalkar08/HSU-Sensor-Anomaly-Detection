#!/usr/bin/env python3
# level2_monitor_email.py
# logs data and sends email when soil gets dry
import time
import csv
import os
import sys
import smtplib
import getpass
from datetime import datetime
from email.mime.text import MIMEText
import RPi.GPIO as GPIO

SENSOR = 17
LOG_FILE = "soil_data.csv"

# global email variables
EMAIL_FROM = ""
EMAIL_PASS = ""
EMAIL_TO = ""

# track if we sent email for this dry cycle
email_sent = False

def setup():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def read():
    val = GPIO.input(SENSOR)
    if val == 1:
        return "DRY", val
    else:
        return "WET", val

def log_data(timestamp, state, val):
    # create file if first time
    if not os.path.exists(LOG_FILE):
        f = open(LOG_FILE, "w", newline="")
        w = csv.writer(f)
        w.writerow(["timestamp", "state", "raw_value"])
        f.close()
    
    # add reading
    f = open(LOG_FILE, "a", newline="")
    w = csv.writer(f)
    w.writerow([timestamp.isoformat(), state, val])
    f.close()

def send_alert():
    try:
        body = "Your plant's soil is DRY!\nConsider watering soon."   
        msg = MIMEText(body)
        msg["Subject"] = "🌱 Plant Needs Water"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(EMAIL_FROM, EMAIL_PASS)
        s.send_message(msg)
        s.quit()
        
        print("Email alert sent")
        return True
    except Exception as e:
        print(f"Email failed: {e}")
        return False

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
        print("\n  ❌ Error: Email and password are required!")
        sys.exit(1)

def main():
    global email_sent, EMAIL_FROM, EMAIL_PASS, EMAIL_TO
    
    # Check if email credentials are in environment variables
    EMAIL_FROM = os.environ.get('SOIL_EMAIL_FROM', '')
    EMAIL_PASS = os.environ.get('SOIL_EMAIL_PASSWORD', '')
    EMAIL_TO = os.environ.get('SOIL_EMAIL_TO', '')
    
    # If not in environment, ask user interactively
    if not EMAIL_FROM or not EMAIL_PASS:
        get_email_credentials()
    
    setup()
    
    print("\n" + "=" * 60)
    print("  LEVEL 2: MONITORING + EMAIL ALERTS")
    print("=" * 60)
    print(f"  📊 Data logging: {LOG_FILE}")
    print(f"  📧 Email alerts: {EMAIL_TO}")
    print("=" * 60)
    print("\n  🌱 Monitoring soil moisture...\n")
    
    last_print = 0
    
    try:
        while True:
            state, val = read()
            t = datetime.now()
            
            # save to csv
            log_data(t, state, val)
            
            # print status every 30 seconds
            now = time.time()
            if now - last_print >= 30:
                time_str = t.strftime('%H:%M:%S')
                if state == "DRY":
                    print(f"  [{time_str}] SOIL DRY")
                else:
                    print(f"  [{time_str}] Soil wet")
                
                last_print = now
            
            # send email when soil becomes dry
            if state == "DRY" and not email_sent:
                print(f"\n  Soil just became DRY!")
                send_alert()
                email_sent = True
                print()
            
            # reset flag when wet again
            if state == "WET":
                email_sent = False
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n  ✓ Monitoring stopped\n")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
