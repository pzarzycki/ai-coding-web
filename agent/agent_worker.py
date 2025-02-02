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


def run_process_monitor(args : list, cwd, shell=True, env=None, stdout_stream = None, stderr_stream = None, folder_base_remove=None):

    def read_output(pipe, pipe_name, target_stream):
        """Reads output line-by-line and passes it to a callback function."""
        with pipe:
            for line in iter(pipe.readline, ''):
                if folder_base_remove:
                    line = (line.replace(folder_base_remove + '\\', '').replace(folder_base_remove + '/', '').replace(folder_base_remove, '.').
                            replace(folder_base_remove.lower() + '\\', '').replace(folder_base_remove.lower() + '/', '').replace(folder_base_remove.lower(), '.'))
                WsSocket.send_messages('log_message', {'txt': line, 'type': pipe_name})
                target_stream.write(line)
    
    process = subprocess.Popen(
        args,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=shell,
        env=env
    )
    
    def target(process):
        # Start a thread to read output asynchronously
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, 'stdout', stdout_stream))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, 'stderr', stderr_stream))

        stdout_thread.start()
        stderr_thread.start()

        # Wait for process to complete
        process.wait()
        stdout_thread.join()
        stderr_thread.join()

    app_thread = threading.Thread(target=target, args=(process,))
    app_thread.daemon = True
    app_thread.start()
    
    return process

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
        self.self_port = 5000
        self.agent = None

        self.message_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._process_messages)
        self.worker_thread.daemon = True
        self.worker_thread.start()
        self.process = None
        WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'App started.'})
        self._initialize_app()
        self._run_working_app()



    def _initialize_app(self):
        working_dir = self.working_dir
        app_template_dir = '_app_template'

        WsSocket.send_messages('log_message', {'txt': "Initializing app...", 'type': 'stdout'})

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

    def _run_python_venv(self, args : list):
        stdout_stream = io.StringIO()
        stderr_stream = io.StringIO()

        process = run_process_monitor(
            [self._get_env_exe()] + args,
            cwd=os.path.abspath(self.working_dir),
            stdout_stream = stdout_stream,
            stderr_stream = stderr_stream,
            folder_base_remove = os.path.abspath(f'{self.working_dir}')
        )
        process.wait()

        return stdout_stream.getvalue() + "\n" + stderr_stream.getvalue()


    def _install_working_requirements(self):
        return self._run_python_venv(['-m', 'pip', 'install', '-r', 'requirements.txt'])


    def _get_env_exe(self):
        env_exe = ('Scripts/python.exe' if os.name == 'nt' else 'bin/python') 
        exe = os.path.abspath(f'{self.working_dir}/.venv/{env_exe}')
        return exe
    
    def get_current_output(self):
        out = self.stdout_stream.getvalue() + "\n" + \
            self.stderr_stream.getvalue()
        return out

    def _run_working_app(self, only_server=False, silent=False):
        self.stdout_stream = io.StringIO()
        self.stderr_stream = io.StringIO()

        #def target():
        if not only_server:
            # create virtual environment
            WsSocket.send_messages('log_message', {'txt': "Creating virtual environment...", 'type': 'stdout'})

            process = subprocess.Popen(
                [sys.executable, '-m', 'venv', f'{self.working_dir}/.venv'],
            )
            process.wait()

            # install requirements
            self._run_python_venv(['-m', 'pip', 'install', '-U', 'pip'])
            self._install_working_requirements()


        self.process = run_process_monitor(
            [self._get_env_exe(), '-m', 'flask', '--app', 'app.py', 'run', '--port', str(self.port), '--debug'] ,# '--no-reload'
            cwd=os.path.abspath(self.working_dir),
            shell=True,
            env=os.environ,
            stdout_stream = self.stdout_stream,
            stderr_stream = self.stderr_stream,
            folder_base_remove = os.path.abspath(f'{self.working_dir}')
        )

        if not silent:
            WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'Server ready.'})
        self.send_message({'msg':'worker_ready'})


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
        if self.agent is None:
            self.agent = OrchestratorAgent(self)

    def kill_process(self, process):
        try:
            parent = psutil.Process(process.pid)
            for child in parent.children(recursive=True):
                try:
                    child.kill()
                except Exception as e:
                    print("killing process failed: ", str(e))
                parent.kill()
                parent.wait()
        except Exception as e:
            print("killing process failed: ", str(e))

    def restart_server(self, silent=False):
        if self.process:
            self.kill_process(self.process)
            self.process = None

        self._run_working_app(only_server=True, silent=silent)

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
            # WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'App started.'})
            ...
        else:
            raise ValueError(f"Unknown command: {command}")
        