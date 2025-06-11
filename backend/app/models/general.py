from pydantic import BaseModel
from typing import List, Dict, Optional

class TextInput(BaseModel):
    """文本输入模型"""
    text: str

class SentimentInfo(BaseModel):
    """情感分析信息"""
    label: str
    score: float
    polarity: float
    subjectivity: float = 0.0

class KeywordInfo(BaseModel):
    """关键词信息"""
    text: str
    relevance: float

class EntityInfo(BaseModel):
    """实体信息"""
    text: str
    type: str
    relevance: float

class TextAnalysisResponse(BaseModel):
    """文本分析响应"""
    summary: str
    sentiment: SentimentInfo
    keywords: List[KeywordInfo] = []
    entities: List[EntityInfo] = []

class InsightInfo(BaseModel):
    """见解信息"""
    type: str
    description: str
    relevance: float

class FileAnalysisResponse(BaseModel):
    """文件分析响应"""
    fileName: str
    columns: List[str]
    rowCount: int
    summary: str
    sentiment_stats: Dict[str, int]
    top_keywords: List[KeywordInfo] = []
    insights: List[InsightInfo] = []
    output_file: str 