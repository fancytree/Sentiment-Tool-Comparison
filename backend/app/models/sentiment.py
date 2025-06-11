from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TextInput(BaseModel):
    """文本输入模型"""
    text: str

class SentimentResponse(BaseModel):
    """情感分析响应模型"""
    sentiment: str
    score: int
    polarity: float

class SentimentStats(BaseModel):
    """情感统计模型"""
    positive: int
    negative: int
    neutral: int

class TableAnalysisResult(BaseModel):
    """表格分析结果模型"""
    total_rows: int
    analyzed_column: str
    results: List[Dict[str, Any]]
    summary: SentimentStats
    output_file: str

class UploadResponse(BaseModel):
    """文件上传响应模型"""
    filename: str
    status: str
    message: str 