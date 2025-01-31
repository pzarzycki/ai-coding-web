

import os
from agent.render_website import render_website_to_image
from tools_core import BaseTool, ToolSpec, ParamSpec, llm_tool
from utils import b64_encode_image, markdown_to_html
from ws import WsSocket
from PIL import Image



@llm_tool(ToolSpec(name="render_website_image", description="Renders a website to an image", parameters=[
    ParamSpec(name="url", description="URL of the website or page to render", required=True, type="string")
    ]))
class RenderWebsiteTool(BaseTool):
    def __init__(self, max_res=600):
        super().__init__()
        self.max_res = max_res

    def __call__(self, url):
        page_image = render_website_to_image(url)
        max_dim = max(page_image.size)
        if max_dim > self.max_res:
            scale = self.max_res / max_dim
            new_size = (int(page_image.size[0] * scale), int(page_image.size[1] * scale))
            page_image = page_image.resize(new_size, resample=Image.Resampling.LANCZOS)
        
        # debug
        WsSocket.send_messages('render_message', {'img': b64_encode_image(page_image)})

        return page_image


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
            with open(os.path.join(self.working_dir, file_path), 'w') as f:
                f.write(content)
                return 'success'
        except FileNotFoundError:
            return f"File '{file_path}' not found."
        

@llm_tool(ToolSpec(name="get_user_feedback", description="Get feedback from user or ask user clarification questions", parameters=[
    ParamSpec(name="ask", description="Question to the user", required=True, type="string")
    ]))
class GetUserFeedbackTool(BaseTool):
    def __init__(self):
        super().__init__()

    def __call__(self, ask):
        WsSocket.send_messages('chat_message', {'type': 'agent', 'html': markdown_to_html("(proceed) " + ask)})

        return "User asks to proceed"

