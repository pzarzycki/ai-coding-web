
from agent.llm_model import LlmModel
from agent.tools import DownloadFileTool, GetCurrentServerLogsTool, GetFileContentTool, HttpRequestTool, InstallRequirementsTool, RenderWebsiteTool, RestartApplicationTool, SaveFileContentTool, VisitWebsiteTool
from agent.tools_core import BaseTool, ParamSpec, ToolSpec, llm_tool
from agent.utils import markdown_to_html, scan_directory
from ws import WsSocket



@llm_tool(ToolSpec(name="agent_task_executor", description="Coding Agent that can execute tasks provided task details. Agent is stateless!", parameters=[
    ParamSpec(name="task_short_description", description="Very brief description of the task, few words max.", required=True, type="string"),
    ParamSpec(name="task_full_description", description="Full description of the task for the agent and all its required details.", required=True, type="string")
    ]))
class ExecutorAgent(BaseTool):
    def __init__(self, agent_worker):
        super().__init__()
        self.agent_worker = agent_worker
        self.working_dir = agent_worker.working_dir
        self.preview_url =  f"http://localhost:{self.agent_worker.port}"


    def __call__(self, task_short_description, task_full_description):
        current_dir_structure = scan_directory(self.working_dir)
        WsSocket.send_messages('chat_message', {'type': 'agent', 'txt': task_short_description, 'secondary': markdown_to_html(task_full_description)})

        llm = LlmModel("You are an AI full-stack Web Developer. Your role is to execute the given task.\nWhen you've completed the final goal say 'COMPLETED: <task result>' and dont anything else before or after. But never start answer like this if the final goal is ready.")

        tools = [
            GetFileContentTool(self.working_dir),
            SaveFileContentTool(self.working_dir),
            RestartApplicationTool(self.agent_worker),
            RenderWebsiteTool(self.agent_worker),
            InstallRequirementsTool(self.agent_worker),
            GetCurrentServerLogsTool(self.agent_worker),
            VisitWebsiteTool(self.agent_worker),
            HttpRequestTool(self.agent_worker),
            DownloadFileTool(self.agent_worker),
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
Remember to call `pip install -r requirements.txt`, using one of the tools, to update current environment, if there are any new new or updated Python packages. Install packages always through 'requirements.txt'\n
Never change the Flask package version!!\n
\n
Current application is already running and available at {self.preview_url}, you can render it to see how it looks, if you need.\n
Available **rendering tool** can be used to get screenshot of any website in the Internet.\n 
It's a good practice to **test any newly created link**, to make sure routing is correct and content is actually available.\n
If you are creating subpages, make sure to use **common layout template** with a common navigation elements - it's a good development practice. Remember, you are a professional!\n\n

When every step was execute and the FINAL GOAL is achived is completed return text "COMPLETED: <task result>".\n
If it was proven that achieving the goal is impossible now, return "COMPLETED: failed - <explain reason>\n\n
"""

        # will call tools automatically
        response = llm.call(msg, tools=tools)
        for x in range(20):
            response = llm.call('is task ready? Say "COMPLETED: <task result>" or execute the next step. Never exit prematurly!', 
                                tools=tools)
            if response.startswith("COMPLETED"):
                print("Executor -", response)
                return response
        else:
            raise RuntimeError("Too many iterations!")

        return response
        

