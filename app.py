from flask import Flask, make_response, render_template, request, jsonify, redirect
from agent.agent_worker import AgentWorker
import os
from flask_socketio import SocketIO
import threading
import time

from ws import WsSocket

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True  # Forces Flask to reload templates on every request
app.config['SECRET_KEY'] = os.environ.get('FLASK_APP_SECRET', '210de364-02eb-4765-aac4-2ec5f4aea939')
socketio = SocketIO(app)
# never create AgentWorker instance in the module initialization

@app.route('/')
def home():
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

@app.route('/api/command', methods=['POST'])
def post_command():
    agent_worker = AgentWorker()
    message = request.json
    agent_worker.command(**message)
    return jsonify({"status": "Command sent"}), 200

@app.route('/api/user-message', methods=['POST'])
def user_message():
    message = request.json.get('message')
    # Process the message as needed

    agent_worker = AgentWorker()
    agent_worker.send_message({'msg':"user_message", 'data':message})

    return jsonify({"status": "User message received", "message": message}), 200

@app.route('/target_preview')
def target_preview():
    return redirect('http://localhost:8090/')

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    ...

if __name__ == '__main__':
    #app.run(debug=True)
    WsSocket.connectSocket(socketio)
    socketio.run(app, debug=True, reloader_options=dict(extra_files="templates/*"), use_reloader=False, host='127.0.0.1', port=5000)