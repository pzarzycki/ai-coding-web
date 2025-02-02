from dataclasses import dataclass
import json
import os
import sys
from time import sleep
from typing import List, Optional, Callable, Union
import openai
import base64
from io import BytesIO
from PIL import Image

from agent.tools_core import BaseTool, ToolSpec
from agent.utils import b64_encode_image
from ws import WsSocket


class LlmModel:
    def __init__(self, system_prompt = "", model="gpt-4o"):
        """
        Initializes the LLM model with a system prompt.

        :param system_prompt: A string defining the system's behavior and rules.

        Models: ['gpt-4o-mini', 'gpt-4o', 'o1-preview', 'o1-mini']
        """
        self.api_key = os.getenv('OPENAI_API_KEY')
        openai.api_key = self.api_key
        self.system_prompt = system_prompt
        self.model = model
        self.messages = [{"role": "system", "content": system_prompt}]  # Initialize conversation with system prompt



    def call(self, user_input, tool_results=None, tools: Optional[List[Union[ToolSpec, BaseTool]]] = None):

        # intial call
        response = self._call(user_input=user_input, tools=tools)
        while True:
            if isinstance(response, list):
                tool_results = dict()
                tool_map = {tool.tool_spec.name: tool.tool_spec for tool in tools}

                # call each tool
                for tool_call in response:
                    id, tool_name, args = tool_call['id'], tool_call['name'], tool_call['args']
                    try:
                        if tool_name not in tool_map:
                            raise ValueError(f"Tool '{tool_name}' not found in the tool list.")
                        print("Calling tool:", tool_name, args)
                        WsSocket.send_messages('tool_message', {'tool_name': tool_name, 'args': str(args)[:100]})
                        tool_result = tool_map[tool_name].function (**args)
                        #WsSocket.send_messages('tool_message', {'tool_name': '', 'args': ''})
                    except Exception as e:
                        exc_type, exc_value, exc_traceback = sys.exc_info()
                        print("Error calling tool:", tool_name, exc_type, exc_value)
                        tool_result = f"{exc_type}: {exc_value}"
                    tool_results[id] = tool_result

                # update LLM response
                response = self._call(None, tool_results=tool_results,) #  tools=tools
            else:
                return response
 

    def _call(self, user_input, tool_results=None, tools : ToolSpec =None):
        """
        Calls the OpenAI API with user input, handling text, images, and tools.

        tool_results: {tool_call_id: result, ...}

        :param user_input: Can be text, image URL, or both.
        :param tools: List of function specs for function calling.
        :return: Assistant response or tool execution request.
        """

        def format_msg_item(item):
            if isinstance(item, Image.Image):
                return {"type": "image_url", "image_url": {"url": b64_encode_image(item), 'detail': 'low'}}
            elif isinstance(item, str):
                return {"type": "text", "text": item}
            else:
                raise ValueError("Invalid message item type.")

        assert user_input is not None or tool_results is not None, "Either user_input or tool_results must be provided."
        assert user_input is None or tool_results is None, "Only one of user_input or tool_results can be provided."

        # format content
        if user_input is not None:
            user_input = user_input if isinstance(user_input, list) else [user_input]
            content = [format_msg_item(item) for item in user_input]

            # Append user input to messages
            self.messages.append({"role": "user", "content": content})



        tool_extra_messages = []
        if tool_results is not None:
            for t,c in tool_results.items():
                if isinstance(c, str):
                    tool_result_message = {'role':'tool', 'tool_call_id':t, 'content': c } 
                    self.messages.append(tool_result_message)
                elif isinstance(c, Image.Image):
                    # special processing for images
                    tool_result_message = {'role':'tool', 'tool_call_id':t, 'content': "success" } 
                    self.messages.append(tool_result_message)

                    content = [format_msg_item(str(f"This is result from the tool call: {t}")), format_msg_item(c)]
                    tool_extra_messages.append({"role": "user", "content": content})
                else:
                    raise ValueError(f"Invalid tool result type: {type(c)}")
                
        self.messages.extend(tool_extra_messages)
            
        if tools is not None:
            tools = [tool.tool_spec.to_dict() for tool in tools]


        # Prepare the API call
        api_request = {
            "model": self.model,
            "messages": self.messages,
        }

        if tools:
            api_request["tools"] = tools
            api_request["tool_choice"] = "auto"  # Allows the model to decide if a tool is needed

        # Call OpenAI API
        client = openai.OpenAI(api_key=self.api_key)

        for _ in range(5):
            try:            
                response = client.chat.completions.create(**api_request)
                break
            except openai.RateLimitError:
                sleep(1)
        else:
            raise RuntimeError("Too many openai API call retries! Hitting RateLimit.")

        assistant_message = response.choices[0].message.to_dict()
        self.messages.append(assistant_message)

        # Process function calls
        if "tool_calls" in assistant_message:
            calls = []
            for tc in assistant_message["tool_calls"]:
                call_id = tc['id']
                tool_name = tc['function']['name']
                tool_args = json.loads(tc['function']['arguments'])

                calls.append({"id": call_id, "name": tool_name, "args": tool_args})

            return calls

        # Append assistant response to messages
        return assistant_message['content']

