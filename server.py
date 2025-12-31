from flask import Flask, jsonify, Response
import subprocess
import os
import sys
from threading import Lock

app = Flask(__name__)
proc = None
proc_lock = Lock()
logfile = os.path.join(os.path.dirname(__file__), 'app.log')

def is_running():
    global proc
    return proc is not None and proc.poll() is None

@app.route('/start', methods=['POST'])
def start():
    global proc
    with proc_lock:
        if is_running():
            return jsonify({"status": "running"})
        f = open(logfile, 'a', encoding='utf-8', buffering=1)
        # Use same Python executable
        proc = subprocess.Popen([sys.executable, os.path.join(os.path.dirname(__file__), 'app.py')], stdout=f, stderr=subprocess.STDOUT)
        return jsonify({"status": "started"})

@app.route('/stop', methods=['POST'])
def stop():
    global proc
    with proc_lock:
        if not is_running():
            return jsonify({"status": "not running"})
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        proc = None
        return jsonify({"status": "stopped"})

@app.route('/logs', methods=['GET'])
def logs():
    if not os.path.exists(logfile):
        return Response('', mimetype='text/plain')
    # return full log content (simple)
    with open(logfile, 'r', encoding='utf-8', errors='ignore') as f:
        return Response(f.read(), mimetype='text/plain')

if __name__ == '__main__':
    # listen on localhost:5000
    app.run(host='127.0.0.1', port=5000)
