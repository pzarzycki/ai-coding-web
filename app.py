from flask import Flask, render_template, request, jsonify, redirect
from agent.agent_worker import AgentWorker
import os
import psutil

app = Flask(__name__)
# never create AgentWorker instance in the module initialization

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/send_message', methods=['POST'])
def send_message():
    agent_worker = AgentWorker()
    message = request.json
    agent_worker.send_message(message)
    return jsonify({"status": "Message sent"}), 200

@app.route('/target_preview')
def target_preview():
    return redirect('http://localhost:8090/')

if __name__ == '__main__':
    app.run(debug=False)