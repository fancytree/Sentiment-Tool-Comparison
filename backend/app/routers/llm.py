from fastapi import APIRouter, HTTPException
from app.models.llm import TextInput, LLMResponse
from app.services.llm_service import llm_service

router = APIRouter(
    prefix="/api/llm",
    tags=["llm"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=LLMResponse)
async def process_text(text_input: TextInput):
    """
    处理文本
    
    参数:
    - text: 要处理的文本内容
    
    返回:
    - response: 模型响应
    """
    try:
        result = llm_service.process(text_input.text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 