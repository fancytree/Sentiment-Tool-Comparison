from pydantic import BaseModel

class TextInput(BaseModel):
    """文本输入模型"""
    text: str
 
class LLMResponse(BaseModel):
    """大语言模型响应"""
    response: str 