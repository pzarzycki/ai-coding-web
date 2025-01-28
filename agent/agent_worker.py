from pathlib import Path
import threading
import queue
import os
import shutil
import subprocess
import io
import sys

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
        self.message_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_messages)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        self._initialize_app()
        self._run_working_app()

    def _initialize_app(self):
        working_dir = '_working_dir'
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

    def _run_working_app(self):
        working_dir = '_working_dir'
        self.stdout_stream = io.StringIO()
        self.stderr_stream = io.StringIO()

        env_exe = ('Scripts/python.exe' if os.name == 'nt' else 'bin/python') 

        def target():
            process = subprocess.Popen(
                [sys.executable, '-m', 'venv', f'{working_dir}/.venv'],
            )
            process.wait()

            exe = os.path.abspath(f'{working_dir}/.venv/{env_exe}')

            process = subprocess.Popen(
                [exe, '-m', 'pip', 'install', '-r', 'requirements.txt'],
                cwd=os.path.abspath(working_dir),
            )
            process.wait()

            process = subprocess.Popen(
                [exe, '-m', 'flask', '--app', 'app.py', 'run', '--port', '8090',] ,# '--no-reload'
                cwd=os.path.abspath(working_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=True,
                env=os.environ
            )

            for line in process.stdout:
                self.stdout_stream.write(line)
            for line in process.stderr:
                self.stderr_stream.write(line)
            print("!!! Worker Exited !!!")
            stdout =self.stdout_stream.getvalue()
            stderr = self.stderr_stream.getvalue()
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

    def send_message(self, message):
        self.message_queue.put(message)
