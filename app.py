import streamlit as st
import subprocess
import time
import os
from collections import deque
import signal

BOT_CMD = ["python", "main.py"]
LOG_FILE = "runtime.log"
MAX_LINES = 20
REFRESH_SECONDS = 2
PID_FILE = "bot.pid"

st.set_page_config(
    page_title="TubeRocket Monitor",
    layout="wide"
)

st.title("📡 TubeRocket Live Logs")

# ---------------- BOT SUPERVISOR ---------------- #

def is_bot_running():
    if not os.path.exists(PID_FILE):
        return False
    try:
        pid = int(open(PID_FILE).read())
        os.kill(pid, 0)
        return True
    except:
        return False

def start_bot():
    st.write("🚀 Starting TubeRocket bot...")
    p = subprocess.Popen(
        BOT_CMD,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    with open(PID_FILE, "w") as f:
        f.write(str(p.pid))

# Auto-start bot once
if not is_bot_running():
    start_bot()
else:
    st.write("✅ Bot already running")

# ---------------- LOG VIEWER ---------------- #

log_box = st.empty()

def read_last_lines(file, n):
    try:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            return list(deque(f, n))
    except FileNotFoundError:
        return ["Waiting for logs...\n"]

while True:
    lines = read_last_lines(LOG_FILE, MAX_LINES)
    log_box.code("".join(lines), language="text")
    time.sleep(REFRESH_SECONDS)
