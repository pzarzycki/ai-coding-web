

import os
from time import sleep
from agent.render_website import render_website_to_image
from agent.tools_core import BaseTool, ToolSpec, ParamSpec, llm_tool
from agent.utils import b64_encode_image, markdown_to_html, scan_directory, truncate_content
from ws import WsSocket
from PIL import Image
import requests
from markdownify import markdownify
from requests.exceptions import RequestException
import re


@llm_tool(ToolSpec(name="render_website_image", description="This tool renders a website, at any URL, to an image. Great for visual inspection of a website and final test.", parameters=[
    ParamSpec(name="url", description="URL of the website or page to render", required=True, type="string")
    ]))
class RenderWebsiteTool(BaseTool):
    def __init__(self, agent_worker, max_res=600):
        super().__init__()
        self.max_res = max_res
        self.agent_worker = agent_worker

    def __call__(self, url : str):
        if url.startswith(f'http://localhost:{self.agent_worker.self_port}') or url.startswith(f'http://127.0.0.1:{self.agent_worker.self_port}'):
            raise RuntimeError("URL unavailable")

        # if url.startswith('http://localhost') or url.startswith('http://127.0.0.1'):
        #     self.agent_worker.restart_server(silent=True)  

        page_image = render_website_to_image(url)
        max_dim = max(page_image.size)
        if max_dim > self.max_res:
            scale = self.max_res / max_dim
            new_size = (int(page_image.size[0] * scale), int(page_image.size[1] * scale))
            page_image = page_image.resize(new_size, resample=Image.Resampling.LANCZOS)
        
        # debug
        WsSocket.send_messages('render_message', {'img': b64_encode_image(page_image)})

        return page_image





@llm_tool(ToolSpec(name="visit_website", description="This tool visits a given page and returns textual (markdown) representation of the its content. Great for obtaining web page content.", parameters=[
    ParamSpec(name="url", description="URL of the website or page to visit", required=True, type="string")
    ]))
class VisitWebsiteTool(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker

    def __call__(self, url : str):
        if url.startswith(f'http://localhost:{self.agent_worker.self_port}') or url.startswith(f'http://127.0.0.1:{self.agent_worker.self_port}'):
            raise RuntimeError("URL unavailable")
        
        # if url.startswith('http://localhost') or url.startswith('http://127.0.0.1'):
        #     self.agent_worker.restart_server(silent=True)  

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()  

            markdown_content = markdownify(response.text).strip()

            markdown_content = re.sub(r"\n{3,}", "\n\n", markdown_content)

            return truncate_content(markdown_content, 10_000)

        except requests.exceptions.Timeout:
            return "The request timed out. Please try again later or check the URL."
        except RequestException as e:
            return f"Error fetching the webpage: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

        


@llm_tool(ToolSpec(name="http_request", description="This tool can call a HTTP request (GET, POST, etc) to any given URL and will return raw content response. It uses `requests.request()` method. Great for detailed and low level testing", parameters=[
    ParamSpec(name="url", description="full URL of the request", required=True, type="string"),
    ParamSpec(name="method", description="HTTP request method (GET, OPTIONS, HEAD, POST, PUT, PATCH, or DELETE)", required=True, type="string"),
    ParamSpec(name="data", description="Any body for the request. Optional, can be null.", required=False, type="string")
    ]))
class HttpRequestTool(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker

    def __call__(self, url : str, method : str, data : str = None):
        if url.startswith(f'http://localhost:{self.agent_worker.self_port}') or url.startswith(f'http://127.0.0.1:{self.agent_worker.self_port}'):
            raise RuntimeError("URL unavailable")
        
        # if url.startswith('http://localhost') or url.startswith('http://127.0.0.1'):
        #     self.agent_worker.restart_server(silent=True)  

        try:
            requests.request(method=method, url=url, data=data)
            response = requests.get(url, timeout=20)
            response.raise_for_status()  

            content = response.text.strip()

            return truncate_content(content, 10_000)

        except requests.exceptions.Timeout:
            return "The request timed out. Please try again later or check the URL."
        except RequestException as e:
            return f"Request Error: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"

        




@llm_tool(ToolSpec(name="get_file_content", description="Read file content", parameters=[
    ParamSpec(name="file_path", description="relative path to the file", required=True, type="string")
    ])) 
class GetFileContentTool(BaseTool):
    def __init__(self, working_dir):
        super().__init__()
        self.working_dir = working_dir

    def __call__(self, file_path):
        assert file_path is not None, "File path is required"
        assert not file_path[0] in ['/', '\\'], "File path must be relative"

        try:
            with open(os.path.join(self.working_dir, file_path), 'r') as f:
                return f.read()
        except FileNotFoundError:
            return f"File '{file_path}' not found."
        

@llm_tool(ToolSpec(name="save_file_content", description="Save file content on disk", parameters=[
    ParamSpec(name="file_path", description="relative path to the file", required=True, type="string"),
    ParamSpec(name="content", description="Full content of the file to save", required=True, type="string")
    ])) 
class SaveFileContentTool(BaseTool):
    def __init__(self, working_dir):
        super().__init__()
        self.working_dir = working_dir

    def __call__(self, file_path, content):
        assert content is not None, "Content is required"
        assert file_path is not None, "File path is required"
        assert not file_path[0] in ['/', '\\'], "File path must be relative"

        try:
            path = os.path.join(self.working_dir, file_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            new_file = not os.path.exists(path)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)

            if new_file:
                WsSocket.send_messages('project_message', {'project': scan_directory(self.working_dir)})
                WsSocket.send_messages('chat_message', {'type': 'system', 'html': f"<div><i class='fa-regular fa-file-lines'></i> Creating file: '{file_path}'</div>"})
            else:
                WsSocket.send_messages('chat_message', {'type': 'system', 'html': f"<div><i class='fa-solid fa-file-pen'></i> Updating file: '{file_path}'</div>"})

            return 'success'
        except FileNotFoundError:
            return f"File '{file_path}' not found."



@llm_tool(ToolSpec(name="download_file", description="This tool can download file from the Internet via HTTP GET request", parameters=[
    ParamSpec(name="file_path", description="Relative path to the target file (destination)", required=True, type="string"),
    ParamSpec(name="url", description="full URL of the request", required=True, type="string"),
    ])) 
class DownloadFileTool(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker

    def __call__(self, file_path, url):
        assert file_path is not None, "File path is required"
        assert not file_path[0] in ['/', '\\'], "File path must be relative"

        if url.startswith(f'http://localhost:{self.agent_worker.self_port}') or url.startswith(f'http://127.0.0.1:{self.agent_worker.self_port}'):
            raise RuntimeError("URL unavailable")

        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()  


            path = os.path.join(self.agent_worker.working_dir, file_path)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            new_file = not os.path.exists(path)
            with open(path, 'wb') as f:
                f.write(response.content)

            if new_file:
                WsSocket.send_messages('project_message', {'project': scan_directory(self.agent_worker.working_dir)})
                WsSocket.send_messages('chat_message', {'type': 'system', 'html': f"<div><i class='fa-solid fa-file-arrow-down'></i> Downloading file: '{file_path}'</div>"})
            else:
                WsSocket.send_messages('chat_message', {'type': 'system', 'html': f"<div><i class='fa-solid fa-file-arrow-down'></i> Downloading (overwrite) file: '{file_path}'</div>"})

            return 'success'
        
        except requests.exceptions.Timeout:
            return "The request timed out. Please try again later or check the URL."
        except RequestException as e:
            return f"Error fetching the webpage: {str(e)}"
        except Exception as e:
            return f"An unexpected error occurred: {str(e)}"


@llm_tool(ToolSpec(name="install_update_requirements", description="This tool will pip install -U requirements.txt in current environment", parameters=[
    ])) 
class InstallRequirementsTool(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker

    def __call__(self):
        result = self.agent_worker._install_working_requirements()
        #self.agent_worker.restart_server()        
        return result

@llm_tool(ToolSpec(name="restart_application", description="This tool restart Flask application. Call it before you want to test live any changes to source code.", parameters=[
    ])) 
class RestartApplicationTool(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker

    def __call__(self):
        self.agent_worker.restart_server(silent=True)        
        sleep(1)
        result = self.agent_worker.get_current_output()
        return f"Application restarted:\n{result}"


@llm_tool(ToolSpec(name="get_current_server_logs", description="This tool will provide current server execution logs. Might be helpfull to trace some execution errors.", parameters=[
    ])) 
class GetCurrentServerLogsTool(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker

    def __call__(self):
        result = self.agent_worker.get_current_output()
        #self.agent_worker.restart_server()        
        return result


@llm_tool(ToolSpec(name="get_user_feedback", description="Get feedback from user or ask user clarification questions", parameters=[
    ParamSpec(name="ask", description="Question to the user", required=True, type="string")
    ]))
class GetUserFeedbackTool(BaseTool):
    def __init__(self):
        super().__init__()

    def __call__(self, ask):
        WsSocket.send_messages('chat_message', {'type': 'agent', 'html': markdown_to_html("(proceed) " + ask)})

        return "User asks to proceed"

