from pathlib import Path
import threading
import queue
import os
import shutil
import subprocess
import io
import sys

import psutil

from agent.orchestrator_agent import  OrchestratorAgent
from ws import WsSocket

class AgentWorker:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AgentWorker, cls).__new__(cls, *args, **kwargs)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self.working_dir = '_working_dir'
        self.port = 8090

        self.message_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_messages)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        self.process = None
        self._initialize_app()
        self._run_working_app()

        self.agent = None


    def _initialize_app(self):
        working_dir = self.working_dir
        app_template_dir = '_app_template'

        if os.path.exists(working_dir):
            shutil.rmtree(working_dir)
        os.makedirs(working_dir)

        if os.path.exists(app_template_dir):
            for item in os.listdir(app_template_dir):
                s = os.path.join(app_template_dir, item)
                d = os.path.join(working_dir, item)
                if os.path.isdir(s):
                    shutil.copytree(s, d, False, None)
                else:
                    shutil.copy2(s, d)

    def _install_working_requirements(self):
        process = subprocess.Popen(
            [self._get_env_exe(), '-m', 'pip', 'install', '-r', 'requirements.txt'],
            cwd=os.path.abspath(self.working_dir),
        )
        process.wait()
        return process.stdout

    def _get_env_exe(self):
        env_exe = ('Scripts/python.exe' if os.name == 'nt' else 'bin/python') 
        exe = os.path.abspath(f'{self.working_dir}/.venv/{env_exe}')
        return exe

    def _run_working_app(self):
        self.stdout_stream = io.StringIO()
        self.stderr_stream = io.StringIO()


        def target():
            # create virtual environment
            self.process = subprocess.Popen(
                [sys.executable, '-m', 'venv', f'{self.working_dir}/.venv'],
            )
            self.process.wait()

            # install requirements
            self._install_working_requirements()

            # run the app
            self.process = subprocess.Popen(
                [self._get_env_exe(), '-m', 'flask', '--app', 'app.py', 'run', '--port', str(self.port),] ,# '--no-reload'
                cwd=os.path.abspath(self.working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                env=os.environ
            )

            WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'Server ready.'})

            self.send_message({'msg':'worker_ready'})

            def read_output(pipe, pipe_name, target_stream):
                """Reads output line-by-line and passes it to a callback function."""
                with pipe:
                    for line in iter(pipe.readline, ''):
                        WsSocket.send_messages('log_message', {'txt': line, 'type': pipe_name})
                        target_stream.write(line)
                        
            # Start a thread to read output asynchronously
            stdout_thread = threading.Thread(target=read_output, args=(self.process.stdout, 'stdout', self.stdout_stream))
            stderr_thread = threading.Thread(target=read_output, args=(self.process.stderr, 'stderr', self.stderr_stream))

            stdout_thread.start()
            stderr_thread.start()

            # Wait for process to complete
            self.process.wait()
            stdout_thread.join()
            stderr_thread.join()

            self.process = None
            print("!!! Worker Exited !!!")
            ...

        self.app_thread = threading.Thread(target=target)
        self.app_thread.daemon = True
        self.app_thread.start()



    def _process_messages(self):
        while True:
            message = self.message_queue.get()
            if message is None:
                break
            self._handle_message(message)

    def _handle_message(self, message):
        # Process the message (message is a dict)
        print(f"Processing message: {message}")

        if message['msg']  == 'user_message':
            self.agent.call(message['data'])
        elif message['msg'] == 'worker_ready':
            self._init_agent()
        else:
            raise ValueError(f"Unknown message: {message}")

    def send_message(self, message):
        self.message_queue.put(message)

    def _init_agent(self):
        self.agent = OrchestratorAgent(self.working_dir, f"http://localhost:{self.port}")

    def kill_process(self, process):
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()
        parent.wait()

    def command(self, command, **kwargs):
        if command == 'restart':
            #TODO
            if self.process:
                self.kill_process(self.process)
            self._initialize_app()
            self._run_working_app()

            WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'App restarted.'})
        elif command == 'start':
            #TODO
            WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'App started.'})
        else:
            raise ValueError(f"Unknown command: {command}")
        