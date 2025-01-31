import base64
import os
from agent.llm_model import LlmModel

from executor_agent import ExecutorAgent
from tools import GetFileContentTool, GetUserFeedbackTool, RenderWebsiteTool
from tools_core import ParamSpec, ToolSpec
from utils import  markdown_to_html, scan_directory
from ws import WsSocket
from PIL import Image


class OrchestratorAgent:
    def __init__(self, working_dir, preview_url):
        self.working_dir = working_dir
        self.preview_url = preview_url

        self.current_dir_structure = scan_directory(self.working_dir)
        
        WsSocket.send_messages('chat_message', {'type': 'system', 'txt': 'Agent ready.'})
        WsSocket.send_messages('project_message', {'project': self.current_dir_structure})


        #self.page_image = render_website_to_image(preview_url)
        #WsSocket.send_messages('render_message', {'img': b64_encode_image(self.page_image)})
        ...


    def call(self, user_message):
        WsSocket.send_messages('chat_message', {'type': 'user', 'html': markdown_to_html(user_message)})

        llm = LlmModel("You are an AI full-stack Web Developer. Your role is to understand the task and plan it.")

        tools = [
            GetUserFeedbackTool(),
            GetFileContentTool(self.working_dir),
            RenderWebsiteTool(),
            ExecutorAgent(self.working_dir)
            ]


        msg = f"""
This is current directory structure of the project:\n
--------------------------------\n
{self.current_dir_structure}\n
--------------------------------\n\n
A user has asked for help with the project. Undertstand the request, PARAPHRASE IT and provive a minimal PLAN to achive user's request.\n
If something is unclear, ask user for clarification. Try making as much decisions, as possible. Make your own decision how to proceed!\n\n
Limit number of steps to a reasonable minimum, the lest the better.\n\n

Plan must be built in a way that it can be executed by the 'agent_task_executor'.\n
Pay attential that all agents and tools are STATELESS and have no memory, so don't expect to keep state between calls. Always provide full information to complete the task fully in one step.\n\n
User request is always in reference to the existing code. Inspect existing content first, to build reasonable plan.

User message:\n
{user_message}
"""

        # will call tools automatically
        response = llm.call(msg, tools=tools)
        WsSocket.send_messages('chat_message', {'type': 'agent', 'txt': "Plan ready. Executing...", 'secondary': markdown_to_html(response)})

        msg = f"""
Now, you need to execute the plan. Use the 'agent_task_executor' to execute the plan. Provide it all required details to complete the task succesfully\n
Execute each step one by one, until your plan is ready. \n
When every step was executed and the whole plan was executed, and only then, return text "COMPLETED:<your execution status>" \n

"""
        response = llm.call(msg, tools=tools)
        for x in range(30):
            response = llm.call('is task ready? Say "COMPLETED:<your execution status>" or execute the next step. Dont exit prematurly.', tools=tools)
            WsSocket.send_messages('chat_message', {'type': 'agent', 'html': markdown_to_html(response)})
            if response.startswith("COMPLETED"):
                return response
        else:
            raise RuntimeError("Too many iterations!")

        return response
        


