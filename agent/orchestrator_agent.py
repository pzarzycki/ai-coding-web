import base64
import os
from time import sleep
from agent.llm_model import LlmModel

from agent.executor_agent import ExecutorAgent
from agent.tools import DownloadFileTool, GetCurrentServerLogsTool, GetFileContentTool, GetUserFeedbackTool, HttpRequestTool, InstallRequirementsTool, RenderWebsiteTool, RestartApplicationTool, SaveFileContentTool, VisitWebsiteTool
from agent.tools_core import ParamSpec, ToolSpec
from agent.utils import  markdown_to_html, scan_directory
from ws import WsSocket
from PIL import Image


class OrchestratorAgent:
    def __init__(self, agent_worker):
        self.agent_worker = agent_worker
        self.working_dir = self.agent_worker.working_dir
        self.preview_url =  f"http://localhost:{self.agent_worker.port}"

        self.current_dir_structure = scan_directory(self.working_dir)
        
        WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'Agent ready.'})
        WsSocket.send_messages('project_message', {'project': self.current_dir_structure})


        #self.page_image = render_website_to_image(preview_url)
        #WsSocket.send_messages('render_message', {'img': b64_encode_image(self.page_image)})
        ...


    def call(self, user_message):
        WsSocket.send_messages('chat_message', {'type': 'user', 'html': markdown_to_html(user_message)})

        llm = LlmModel("You are an AI full-stack Web Developer. Your role is to understand the task and plan it.\nWhen you've completed the final goal say 'COMPLETED: <explanation>' and dont anything else before or after. But never start answer like this if the final goal is ready.")

        tools = [
            GetUserFeedbackTool(),
            GetFileContentTool(self.working_dir),
            # SaveFileContentTool(self.working_dir),
            RestartApplicationTool(self.agent_worker),
            RenderWebsiteTool(agent_worker=self.agent_worker),
            ExecutorAgent(self.agent_worker),
            InstallRequirementsTool(self.agent_worker),
            GetCurrentServerLogsTool(self.agent_worker),
            VisitWebsiteTool(self.agent_worker),
            HttpRequestTool(self.agent_worker),
            DownloadFileTool(self.agent_worker),
            ]


        msg = f"""
This is current directory structure of the project:\n
--------------------------------\n
{self.current_dir_structure}\n
--------------------------------\n\n
A user has asked for help with the project. Undertstand the request, PARAPHRASE IT and provive a minimal PLAN to achive user's request.\n
If something is unclear, ask user for clarification. Try making as much decisions, as possible. Make your own decision how to proceed!\n\n
Limit number of steps to a reasonable minimum, the lest the better.\n
\n
Current application is already running and available at {self.preview_url}, you can render it to see how it looks, if you need.\n
Available rendering tool can be used to get screenshot of any website in the Internet.\n 
You can also use **rendering tool** to test created links and URLs in the local server.\n
It's a good practice to **test any newly created link**, to make sure routing is correct and content is actually available.\n
If you are creating subpages, make sure to use **common layout template** with a common navigation elements - it's a good development practice. Remember, you are a professional!\n
\n
\n
Make sure User can access newly created content easily - make it available from root main page and/or provide details how to access new content\n 
\n
ReadMe.txt contains a history of user requests. Keep the history of the project and write down current requirements.\n
\n
**Plan** must be built in a way that it can be executed by the 'agent_task_executor'.\n
Each task must have a clear goal and clear specification. Give enough context about the general objective and the task, so it's clear how to execute it. Do not theorize - always say exactly what has to be done. Agent can use any available tools and can save files on disk.\n
Pay attential that all **agents** and tools are **STATELESS** and have no memory, so don't expect to keep state between calls. Always provide full information to complete the task fully in one step.\n\n
User request is always in reference to the existing code. Inspect existing content first, to build reasonable plan.\n
Never ask to create an account for an API.\n

User message:\n
{user_message}
"""

        WsSocket.send_messages('chat_message', {'type': 'agent', 'txt': "Building an execution plan..."})

        # will call tools automatically
        response = llm.call(msg, tools=tools)
        WsSocket.send_messages('chat_message', {'type': 'agent', 'txt': "Plan is ready. Executing...", 'secondary': markdown_to_html(response)})

        msg = f"""
Now, you need to execute the plan. **Use the 'agent_task_executor'** to execute the plan.\n 
Provide the agent all required details to complete each task succesfully. Be very specific, give an overall objective and context. Clearly explain the task step by step.\n
Execute each step one by one, until your plan is ready. \n
When the final goal is achieved (or was proved that is impossible to be achieved now), and only then, return text 'COMPLETED:<your execution status>' \n

"""
        def notify_thought(response : str):
                idx = response.index('\n') if '\n' in response else len(response)
                if idx > 200:
                    idx = 200
                    posfix = '...'
                else:
                    posfix = ''
                header = response[:idx]
                thought = response[idx:]
                WsSocket.send_messages('chat_message', {'type': 'agent', 'html': header + posfix, 'secondary': markdown_to_html(thought)})

        response = llm.call(msg, tools=tools)
        for x in range(30):
            response = llm.call("Is the FINAL GOAL achived? If so, and ONLY THEN, say 'COMPLETED: <your execution status>' or execute next required step and don't confuse the output. Never finish prematurly! Make sure the whole plan is executed! You have either call agents, tools or finish.", 
                        tools=tools)
            print(response)
            if response.startswith("COMPLETED"):
                # restart Flask server
                self.agent_worker.restart_server(silent=True)
                sleep(1)
                output = self.agent_worker.get_current_output()
        
                response = llm.call(f'This is current server output:\n{output}\n\n Is application behaves as expected? If so, and ONLY then, return text "COMPLETED: <your execution status>" (dont add anything before it) or call agent again to fix the issue.', 
                                    tools=tools)
                print (response)
                if response.startswith("COMPLETED"):    
                    WsSocket.send_messages('chat_message', {'type': 'agent', 'final':'final', 'html': markdown_to_html(response)})
                    return response
                else:
                    notify_thought(response)
            else:
                notify_thought(response)
                
        else:
            raise RuntimeError("Too many iterations!")

        return response
        


