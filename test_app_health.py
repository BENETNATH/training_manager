import subprocess
import time
import os
import requests

FLASK_APP_DIR = "/home/petitdadm/training_manager"
APP_OUT_PATH = os.path.join(FLASK_APP_DIR, "app.out")
LOG_PATH = os.path.join(FLASK_APP_DIR, "logs", "training_manager.log")
SERVER_URL = "http://localhost:5000"

def run_command(command, description):
    print(f"[INFO] {description}")
    process = subprocess.run(command, shell=True, capture_output=True, text=True)
    if process.returncode != 0:
        print(f"[ERROR] Command failed: {command}")
        print(f"Stdout: {process.stdout}")
        print(f"Stderr: {process.stderr}")
    return process

def start_server():
    print("[INFO] Starting Flask server in background...")
    # Clear previous logs
    if os.path.exists(APP_OUT_PATH):
        os.remove(APP_OUT_PATH)
    if os.path.exists(LOG_PATH):
        os.remove(LOG_PATH)

    # Start server
    process = subprocess.Popen(f"{FLASK_APP_DIR}/run_server.sh", shell=True, cwd=FLASK_APP_DIR)
    time.sleep(10) # Give server time to start
    return process

def stop_server():
    print("[INFO] Stopping Flask server...")
    run_command(f"{FLASK_APP_DIR}/stop_server.sh", "Stopping Flask server")

def check_url(url):
    print(f"[INFO] Accessing URL: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"[INFO] URL {url} returned status code: {response.status_code}")
        return response.status_code
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to access URL {url}: {e}")
        return None

def analyze_logs():
    errors_found = []
    print("[INFO] Analyzing server logs...")

    if os.path.exists(APP_OUT_PATH):
        with open(APP_OUT_PATH, "r") as f:
            content = f.read()
            if "Error" in content or "Traceback" in content:
                errors_found.append(f"Errors/Tracebacks found in {APP_OUT_PATH}:\n{content}")
    
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r") as f:
            content = f.read()
            if "ERROR" in content or "CRITICAL" in content:
                errors_found.append(f"Errors/Critical messages found in {LOG_PATH}:\n{content}")
    
    return errors_found

if __name__ == "__main__":
    server_process = None
    try:
        stop_server() # Ensure no old processes are running
        server_process = start_server()

        # URLs to check
        urls_to_check = [
            f"{SERVER_URL}/admin/index",
            f"{SERVER_URL}/auth/login"
        ]

        for url in urls_to_check:
            check_url(url)
        
        errors = analyze_logs()

        if errors:
            print("\n[ERROR] Application health check failed. Errors found:")
            for error in errors:
                print(error)
        else:
            print("\n[SUCCESS] Application health check passed. No errors found in logs after accessing key pages.")

    finally:
        if server_process:
            server_process.terminate()
            server_process.wait()
        stop_server()