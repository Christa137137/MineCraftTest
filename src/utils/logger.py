import os
from datetime import datetime


CURRENT_LOG_FILE = None
file_time = datetime.now().strftime("%m%d_%H%M")

def set_log_file(filepath):
    global CURRENT_LOG_FILE
    CURRENT_LOG_FILE = filepath
def log_message(message, level=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    print(log_entry.strip())

    os.makedirs(os.path.dirname(CURRENT_LOG_FILE), exist_ok=True)

    try:
        with open(CURRENT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"log fails: {e}")