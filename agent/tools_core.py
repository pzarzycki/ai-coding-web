
from dataclasses import dataclass
from typing import Callable, List, Optional, ParamSpec

@dataclass
class ParamSpec:
    name: str
    description: str
    type: str
    required: bool = False
    enum : Optional[List[str]] = None

    def to_dict(self, nullable=False):
        d = {
            "description": self.description,
            "type": self.type if not nullable or not self.required else [self.type, "null"],
        }
        if self.enum is not None:
            d["enum"] = self.enum
        return d

@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: List[ParamSpec] = None
    strict: bool = True
    function: Callable = None

    @property
    def tool_spec(self):
        return self

    def to_dict(self):
        d = {
                'type':'function',
                'function': {
                    'name': self.name,
                    'description': self.description,
                    'parameters': {
                        'type': 'object',
                        'properties':{param.name : param.to_dict(self.strict) for param in self.parameters},
                        'required': [x.name for x in self.parameters if x.required] if not self.strict else [x.name for x in self.parameters],
                        "additionalProperties": False
                    },
                    'strict': self.strict,
                },                
                }
        return d
    
class BaseTool():
    def __init__(self):
        self.tool_spec = getattr(type(self), '_tool_spec', None)
        self.tool_spec.function = self


def llm_tool(tool_spec: ToolSpec):
    def decorator(cls):
        cls._tool_spec = tool_spec
        return cls  # Return the modified class
    return decorator

