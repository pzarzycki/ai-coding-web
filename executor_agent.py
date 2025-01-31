
from agent.llm_model import LlmModel
from tools import GetFileContentTool, RenderWebsiteTool, SaveFileContentTool
from tools_core import BaseTool, ParamSpec, ToolSpec, llm_tool
from utils import markdown_to_html, scan_directory
from ws import WsSocket



@llm_tool(ToolSpec(name="agent_task_executor", description="Agent that can execute tasks provided task details. Agent is stateless!", parameters=[
    ParamSpec(name="task_short_description", description="Very brief description of the task, few words max.", required=True, type="string"),
    ParamSpec(name="task_full_description", description="Full description of the task for the agent and all its required details.", required=True, type="string")
    ]))
class ExecutorAgent(BaseTool):
    def __init__(self, working_dir):
        super().__init__()
        self.working_dir = working_dir
        ...


    def __call__(self, task_short_description, task_full_description):
        current_dir_structure = scan_directory(self.working_dir)
        WsSocket.send_messages('chat_message', {'type': 'agent', 'txt': task_short_description, 'secondary': markdown_to_html(task_full_description)})

        llm = LlmModel("You are an AI full-stack Web Developer. Your role is to execute the given task.")

        tools = [
            GetFileContentTool(self.working_dir),
            SaveFileContentTool(self.working_dir),
            RenderWebsiteTool()
            ]


        msg = f"""
This is current directory structure of the project:\n
--------------------------------\n
{current_dir_structure}\n
--------------------------------\n\n


Your task is: {task_full_description}\n\n

Execute the task and provide the results. Use available tools to help you with the task. Be very succinct efficient.\n
Complete the tastk using tools, and only THEN return response indicating the task is completed.\n
Remember to SAVE and UPDATE files on the disk if requested before returning the response.\n
If you believe no action is required to complete the task, simply indicate the task is completed and return.\n
When every step was execute and the whole task is completed return text "COMPLETED:<your execution status>".\n
"""

        # will call tools automatically
        response = llm.call(msg, tools=tools)
        for x in range(20):
            response = llm.call('is every step executed? Say "COMPLETED:<your execution status>" or execute next step.', tools=tools)
            if response.startswith("COMPLETED"):
                return response
        else:
            raise RuntimeError("Too many iterations!")

        return response
        

