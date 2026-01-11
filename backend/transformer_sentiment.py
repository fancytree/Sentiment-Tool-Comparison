#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transformer情感分析服务
支持方面分析、置信度评估和详细原因说明
"""

import os
import pandas as pd
from datetime import datetime
import logging
import sys
from typing import Dict, List, Optional, Union, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import re
import json
import time
from fastapi.middleware.cors import CORSMiddleware

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建路由器
app = APIRouter(
    prefix="",  # 移除前缀，因为已经在 main.py 中设置了
    tags=["transformer-sentiment"],
    responses={404: {"description": "Not found"}},
)

# 数据模型
class TextAnalysisRequest(BaseModel):
    text: str

class AspectAnalysis(BaseModel):
    aspect: str
    sentiment: str
    confidence: float
    reason: str

class AnalysisResult(BaseModel):
    sentiment: str
    score: float
    polarity: float
    confidence: float
    reason: str
    aspects: List[AspectAnalysis]

class TableAnalysisResult(BaseModel):
    total_rows: int
    analyzed_column: str
    results: List[AnalysisResult]
    summary: Dict[str, int]
    output_file: str
    original_texts: Optional[List[str]] = None

def safe_string(value, default="") -> str:
    """
    确保返回值是有效的字符串，防止前端charAt错误
    """
    if value is None:
        return str(default) if default else ""
    if not isinstance(value, str):
        try:
            value = str(value)
        except:
            return str(default) if default else ""
    
    # 确保是字符串并去除空白
    try:
        result = value.strip() if hasattr(value, 'strip') else str(value)
        return result if result else (str(default) if default else "")
    except:
        return str(default) if default else ""

def validate_text_input(text) -> str:
    """
    验证和清理输入文本
    """
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    text = text.strip()
    return text if text else ""

# 延迟加载情感分析模型
_sentiment_analyzer = None

def get_sentiment_analyzer():
    """延迟加载情感分析模型以节省内存"""
    global _sentiment_analyzer
    if _sentiment_analyzer is None:
        try:
            logger.info("开始加载情感分析模型...")
            # 检查是否在render.com环境中，如果是则直接使用后备方案
            import os
            is_render_env = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_ID')
            
            if is_render_env:
                logger.info("检测到 render.com 环境，使用基于规则的情感分析以节省内存")
                _sentiment_analyzer = "fallback"
                return _sentiment_analyzer
            
            # 本地环境检查内存
            import psutil
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            logger.info(f"可用内存: {available_mb:.1f} MB")
            
            if available_mb < 1000:  # 如果可用内存少于1GB，使用后备方案
                logger.warning("内存不足，使用基于规则的情感分析")
                _sentiment_analyzer = "fallback"
                return _sentiment_analyzer
            
            # 使用更轻量级的模型和配置
            from transformers import pipeline
            import torch
            
            # 设置为CPU模式以节省内存
            device = -1  # CPU
            
            _sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="distilbert-base-uncased-finetuned-sst-2-english",  # 轻量级模型
                return_all_scores=True,
                device=device,
                model_kwargs={"torch_dtype": torch.float32}  # 使用float32而不是float64
            )
            logger.info("✅ 情感分析模型加载成功")
        except Exception as e:
            logger.error(f"❌ 模型加载失败: {str(e)}")
            logger.info("🔄 切换到基于规则的情感分析")
            # 如果模型加载失败，使用简单的基于规则的分析
            _sentiment_analyzer = "fallback"
    return _sentiment_analyzer

def extract_aspects(text: str) -> List[str]:
    """
    从文本中提取可能的方面（aspects）
    """
    # 常见的产品/服务方面关键词
    aspect_keywords = {
        'quality': ['quality', 'build', 'material', 'construction', 'durability', 'craftsmanship'],
        'price': ['price', 'cost', 'expensive', 'cheap', 'affordable', 'value', 'money', 'budget'],
        'service': ['service', 'support', 'staff', 'customer', 'help', 'assistance', 'response'],
        'delivery': ['delivery', 'shipping', 'arrival', 'fast', 'slow', 'quick', 'time', 'speed'],
        'design': ['design', 'look', 'appearance', 'style', 'color', 'beautiful', 'ugly', 'aesthetic'],
        'usability': ['easy', 'difficult', 'user', 'interface', 'simple', 'complex', 'convenient'],
        'performance': ['performance', 'speed', 'fast', 'slow', 'efficient', 'work', 'function'],
        'features': ['feature', 'function', 'capability', 'option', 'tool', 'functionality'],
        'packaging': ['package', 'packaging', 'box', 'wrap', 'container', 'presentation'],
        'size': ['size', 'big', 'small', 'large', 'tiny', 'compact', 'huge', 'dimension']
    }
    
    text_lower = text.lower()
    found_aspects = []
    
    for aspect, keywords in aspect_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                if aspect not in found_aspects:
                    found_aspects.append(aspect)
                break
    
    # 如果没有找到特定方面，返回通用方面
    if not found_aspects:
        found_aspects = ['overall']
    
    return found_aspects

def analyze_aspect_sentiment(text: str, aspect: str) -> Dict:
    """
    分析特定方面的情感
    
    Args:
        text (str): 要分析的文本
        aspect (str): 要分析的方面
    
    Returns:
        Dict: 包含方面分析结果的字典
    """
    try:
        # 获取相关句子
        relevant_sentences = get_relevant_sentences(text, aspect)
        if not relevant_sentences:
            return {
                "sentiment": "neutral",
                "confidence": 0.5,
                "reason": f"No specific content found about {aspect}"
            }
        
        # 分析情感
        analyzer = get_sentiment_analyzer()
        if analyzer == "fallback":
            # 使用简单的基于规则的分析
            result = simple_sentiment_analysis(" ".join(relevant_sentences))
        else:
            # 使用 Transformer 模型
            results = analyzer(" ".join(relevant_sentences))
            sentiment = max(results[0], key=lambda x: x['score'])
            result = {
                "sentiment": sentiment['label'].lower(),
                "score": sentiment['score'],
                "confidence": sentiment['score']
            }
        
        # 生成原因
        reason = generate_aspect_reason(aspect, result['sentiment'], relevant_sentences)
        
        return {
            "sentiment": result.get('sentiment', 'neutral'),
            "confidence": float(result.get('confidence', 0.5)),
            "reason": safe_string(reason, f"No specific reason available for {aspect}")
        }
    except Exception as e:
        logger.error(f"Aspect sentiment analysis failed: {str(e)}")
        return {
            "sentiment": "neutral",
            "confidence": 0.5,
            "reason": f"Analysis failed for {aspect}: {str(e)}"
        }

def enhanced_aspect_sentiment_analysis(text: str, aspect: str) -> Dict:
    """
    增强的方面情感分析，针对特定方面优化
    """
    text_lower = text.lower()
    
    # 方面特定的正面和负面词汇
    aspect_sentiment_words = {
        'quality': {
            'positive': ['excellent', 'outstanding', 'superior', 'high-quality', 'durable', 'solid', 'well-built'],
            'negative': ['poor', 'cheap', 'flimsy', 'low-quality', 'defective', 'broken']
        },
        'price': {
            'positive': ['affordable', 'reasonable', 'value', 'worth', 'cheap', 'budget-friendly'],
            'negative': ['expensive', 'overpriced', 'costly', 'pricey', 'too much']
        },
        'service': {
            'positive': ['helpful', 'responsive', 'friendly', 'professional', 'excellent'],
            'negative': ['rude', 'unhelpful', 'slow', 'poor', 'terrible']
        },
        'delivery': {
            'positive': ['fast', 'quick', 'prompt', 'timely', 'speedy'],
            'negative': ['slow', 'delayed', 'late', 'long']
        }
    }
    
    # 通用情感词汇
    general_positive = ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'best', 'awesome']
    general_negative = ['bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disappointing', 'poor', 'useless']
    
    # 获取方面特定词汇
    aspect_words = aspect_sentiment_words.get(aspect, {'positive': [], 'negative': []})
    
    # 计算情感分数
    positive_score = 0
    negative_score = 0
    
    words = text_lower.split()
    for word in words:
        # 方面特定词汇权重更高
        if word in aspect_words['positive']:
            positive_score += 2.0
        elif word in aspect_words['negative']:
            negative_score += 2.0
        # 通用词汇权重较低
        elif word in general_positive:
            positive_score += 1.0
        elif word in general_negative:
            negative_score += 1.0
    
    # 检查否定词
    negation_words = ['not', "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "couldn't", "isn't", "aren't"]
    has_negation = any(neg in text_lower for neg in negation_words)
    
    if has_negation:
        # 如果有否定词，交换正负分数
        positive_score, negative_score = negative_score, positive_score
    
    # 计算最终结果
    total_score = positive_score + negative_score
    if total_score == 0:
        return {"sentiment": "neutral", "score": 0.5}
    
    if positive_score > negative_score:
        confidence = min(0.95, 0.6 + (positive_score - negative_score) * 0.1)
        return {"sentiment": "positive", "score": confidence}
    elif negative_score > positive_score:
        confidence = min(0.95, 0.6 + (negative_score - positive_score) * 0.1)
        return {"sentiment": "negative", "score": confidence}
    else:
        return {"sentiment": "neutral", "score": 0.5}

def generate_aspect_reason(aspect: str, sentiment: str, relevant_sentences: List[str]) -> str:
    """
    生成方面分析的原因
    
    Args:
        aspect (str): 分析的方面
        sentiment (str): 情感分析结果
        relevant_sentences (List[str]): 相关句子列表
    
    Returns:
        str: 分析原因
    """
    try:
        # 情感关键词
        sentiment_keywords = {
            'positive': ['good', 'great', 'excellent', 'amazing', 'wonderful', 'perfect', 'best', 'love', 'like'],
            'negative': ['bad', 'poor', 'terrible', 'awful', 'worst', 'hate', 'dislike', 'problem', 'issue'],
            'neutral': ['okay', 'fine', 'average', 'normal', 'standard', 'usual']
        }
        
        # 获取情感关键词
        keywords = sentiment_keywords.get(sentiment.lower(), [])
        
        # 在相关句子中查找情感关键词
        found_keywords = []
        for sentence in relevant_sentences:
            sentence_lower = sentence.lower()
            for keyword in keywords:
                if keyword in sentence_lower:
                    found_keywords.append(keyword)
        
        # 生成原因
        if found_keywords:
            return f"Found {sentiment} sentiment keywords: {', '.join(found_keywords)} in the text about {aspect}"
        else:
            return f"Overall {sentiment} sentiment detected for {aspect} based on context"
    except Exception as e:
        logger.error(f"Failed to generate aspect reason: {str(e)}")
        return f"Unable to generate detailed reason for {aspect} analysis"

def simple_sentiment_analysis(text: str) -> Dict:
    """增强的基于规则的情感分析作为后备方案"""
    # 扩展的情感词汇表
    positive_words = [
        'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like', 'best', 'awesome',
        'perfect', 'brilliant', 'outstanding', 'superb', 'magnificent', 'incredible', 'marvelous', 'terrific',
        'fabulous', 'exceptional', 'impressive', 'remarkable', 'delightful', 'enjoyable', 'pleasant', 'satisfied',
        'happy', 'pleased', 'thrilled', 'excited', 'recommend', 'beautiful', 'nice', 'fine', 'cool', 'fun'
    ]
    
    negative_words = [
        'bad', 'terrible', 'awful', 'hate', 'worst', 'horrible', 'disgusting', 'annoying', 'frustrating', 'disappointing',
        'poor', 'pathetic', 'useless', 'worthless', 'dreadful', 'appalling', 'atrocious', 'abysmal', 'disastrous',
        'unacceptable', 'inadequate', 'inferior', 'defective', 'faulty', 'broken', 'failed', 'wrong', 'problem',
        'issue', 'trouble', 'difficulty', 'complaint', 'regret', 'waste', 'boring', 'slow', 'expensive', 'overpriced'
    ]
    
    # 强化词汇（增加权重）
    intensifiers = ['very', 'extremely', 'incredibly', 'absolutely', 'totally', 'completely', 'really', 'quite']
    
    text_lower = text.lower()
    
    # 计算基础分数
    positive_score = 0
    negative_score = 0
    
    # 检查每个词汇
    words = text_lower.split()
    for i, word in enumerate(words):
        # 检查强化词
        multiplier = 1.5 if i > 0 and words[i-1] in intensifiers else 1.0
        
        if word in positive_words:
            positive_score += multiplier
        elif word in negative_words:
            negative_score += multiplier
    
    # 检查完整短语（处理标点符号）
    import re
    clean_text = re.sub(r'[^\w\s]', ' ', text_lower)
    for word in positive_words:
        if word in clean_text:
            positive_score += 0.5  # 额外加分
    for word in negative_words:
        if word in clean_text:
            negative_score += 0.5  # 额外加分
    
    # 检查否定词（not, don't, isn't等）
    negation_words = ['not', "don't", "doesn't", "didn't", "won't", "wouldn't", "can't", "couldn't", "isn't", "aren't", "wasn't", "weren't"]
    has_negation = any(neg in text_lower for neg in negation_words)
    
    if has_negation:
        # 如果有否定词，交换正负分数
        positive_score, negative_score = negative_score, positive_score
    
    # 计算最终结果
    total_score = positive_score + negative_score
    if total_score == 0:
        return {"sentiment": "neutral", "score": 0.5, "polarity": 0.0}
    
    if positive_score > negative_score:
        confidence = min(0.95, 0.6 + (positive_score - negative_score) * 0.1)
        return {"sentiment": "positive", "score": confidence, "polarity": confidence}
    elif negative_score > positive_score:
        confidence = min(0.95, 0.6 + (negative_score - positive_score) * 0.1)
        return {"sentiment": "negative", "score": confidence, "polarity": -confidence}
    else:
        return {"sentiment": "neutral", "score": 0.5, "polarity": 0.0}

def analyze_sentiment_with_aspects(text: str) -> Dict:
    """
    分析文本的情感，包括整体情感和各个方面的情感
    
    Args:
        text (str): 要分析的文本
    
    Returns:
        Dict: 包含完整分析结果的字典
    """
    try:
        # 输入验证
        text = validate_text_input(text)
        if not text:
            return {
                "sentiment": "neutral",
                "score": 0.5,
                "polarity": 0.0,
                "confidence": 0.5,
                "reason": "No text provided for analysis",
                "aspects": []
            }
        
        # 1. 整体情感分析
        overall_sentiment = analyze_basic_sentiment(text)
        
        # 2. 提取方面
        aspects = extract_aspects(text)
        
        # 3. 分析每个方面的情感
        aspect_analyses = []
        for aspect in aspects:
            aspect_result = analyze_aspect_sentiment(text, aspect)
            # 确保 sentiment 字段有默认值
            sentiment = aspect_result.get('sentiment', 'neutral')
            if not sentiment or sentiment.strip() == '':
                sentiment = 'neutral'
            
            aspect_analyses.append({
                "aspect": safe_string(aspect, "general"),
                "sentiment": safe_string(sentiment, "neutral"),
                "confidence": float(aspect_result.get('confidence', 0.5)),
                "reason": safe_string(aspect_result.get('reason'), "No reason available")
            })
        
        # 4. 生成整体分析的原因
        overall_reason = generate_overall_reason(text, overall_sentiment)
        
        return {
            "sentiment": overall_sentiment.get('sentiment', 'neutral'),
            "score": float(overall_sentiment.get('score', 0.5)),
            "polarity": float(overall_sentiment.get('polarity', 0.0)),
            "confidence": float(overall_sentiment.get('confidence', 0.5)),
            "reason": safe_string(overall_reason, "No reason available"),
            "aspects": aspect_analyses
        }
    except Exception as e:
        logger.error(f"Aspect analysis failed: {str(e)}")
        # 如果分析失败，返回安全的默认值
        return {
            "sentiment": "neutral",
            "score": 0.5,
            "polarity": 0.0,
            "confidence": 0.5,
            "reason": safe_string(f"Analysis failed: {str(e)}", "Analysis error"),
            "aspects": []
        }

def analyze_basic_sentiment(text: str) -> Dict:
    """
    基础情感分析（不包含方面分析）
    
    Args:
        text (str): 要分析的文本
    
    Returns:
        Dict: 包含基础分析结果的字典
    """
    try:
        analyzer = get_sentiment_analyzer()
        
        if analyzer == "fallback":
            # 使用简单的基于规则的分析
            return simple_sentiment_analysis(text)
        
        # 使用 Transformer 模型
        results = analyzer(text)
        # 获取得分最高的情感
        sentiment = max(results[0], key=lambda x: x['score'])
        
        # 转换情感标签
        sentiment_label = sentiment['label'].lower()
        if 'negative' in sentiment_label or sentiment_label == 'label_0':
            sentiment_label = 'negative'
        elif 'positive' in sentiment_label or sentiment_label == 'label_1':
            sentiment_label = 'positive'
        else:
            sentiment_label = 'neutral'
        
        # 计算极性
        polarity = sentiment['score'] if sentiment_label == 'positive' else -sentiment['score'] if sentiment_label == 'negative' else 0
        
        return {
            "sentiment": sentiment_label,
            "score": sentiment['score'],
            "polarity": polarity,
            "confidence": sentiment['score']  # 添加缺失的confidence字段
        }
    except Exception as e:
        logger.error(f"Basic analysis failed: {str(e)}")
        # 如果模型分析失败，使用简单的基于规则的分析
        return simple_sentiment_analysis(text)

def generate_overall_reason(text: str, overall_sentiment: Dict) -> str:
    """
    生成整体分析的原因
    
    Args:
        text (str): 要分析的文本
        overall_sentiment (Dict): 整体情感分析结果
    
    Returns:
        str: 分析原因
    """
    try:
        sentiment = overall_sentiment.get('sentiment', 'neutral')
        confidence = overall_sentiment.get('confidence', 0.5)
        
        # 情感关键词
        sentiment_keywords = {
            'positive': ['good', 'great', 'excellent', 'amazing', 'wonderful', 'perfect', 'best', 'love', 'like'],
            'negative': ['bad', 'poor', 'terrible', 'awful', 'worst', 'hate', 'dislike', 'problem', 'issue'],
            'neutral': ['okay', 'fine', 'average', 'normal', 'standard', 'usual']
        }
        
        # 获取情感关键词
        keywords = sentiment_keywords.get(sentiment.lower(), [])
        
        # 在文本中查找情感关键词
        found_keywords = []
        text_lower = text.lower()
        for keyword in keywords:
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        # 生成原因
        if found_keywords:
            return f"Found {sentiment} sentiment keywords: {', '.join(found_keywords)} with {confidence:.2f} confidence"
        else:
            return f"Overall {sentiment} sentiment detected with {confidence:.2f} confidence based on context"
    except Exception as e:
        logger.error(f"Failed to generate overall reason: {str(e)}")
        return "Unable to generate detailed reason for overall analysis"

def ensure_output_dir():
    """
    确保输出目录存在
    """
    if not os.path.exists('output'):
        os.makedirs('output')
        logging.info("Created output directory: output")

@app.post("/")
async def analyze_text(request: TextAnalysisRequest) -> AnalysisResult:
    """
    分析单个文本的情感，包括方面分析
    """
    try:
        # 预热模型（如果还没有加载）
        analyzer = get_sentiment_analyzer()
        if analyzer != "fallback":
            logger.info("使用 Transformer 模型进行分析")
        else:
            logger.info("使用基于规则的分析")
            
        result = analyze_sentiment_with_aspects(request.text)
        return AnalysisResult(**result)
    except Exception as e:
        logger.error(f"分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/aspects")
async def analyze_aspects(request: TextAnalysisRequest):
    """
    专门的方面分析端点，返回格式化的方面分析结果
    """
    try:
        result = analyze_sentiment_with_aspects(request.text)
        
        # 格式化输出，突出显示每个方面的信息
        formatted_result = {
            "text": safe_string(request.text, ""),
            "overall_analysis": {
                "sentiment": safe_string(result.get('sentiment'), "neutral"),
                "confidence": float(result.get('confidence', 0.5)),
                "reason": safe_string(result.get('reason'), "No reason available")
            },
            "aspect_analysis": []
        }
        
        # 添加每个方面的详细分析
        if result.get('aspects') and isinstance(result['aspects'], list):
            for aspect in result['aspects']:
                if isinstance(aspect, dict):
                    formatted_result["aspect_analysis"].append({
                        "aspect": safe_string(aspect.get('aspect'), "general"),
                        "sentiment": safe_string(aspect.get('sentiment'), "neutral"),
                        "confidence": float(aspect.get('confidence', 0.5)),
                        "reason": safe_string(aspect.get('reason'), "No reason available")
                    })
        
        return formatted_result
    except Exception as e:
        logger.error(f"方面分析失败: {str(e)}")
        # 返回安全的错误响应
        return {
            "text": safe_string(getattr(request, 'text', ''), ""),
            "overall_analysis": {
                "sentiment": "neutral",
                "confidence": 0.5,
                "reason": safe_string(f"Analysis failed: {str(e)}", "Analysis error")
            },
            "aspect_analysis": []
        }

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存上传的文件（添加时间戳）
        original_filename = os.path.splitext(file.filename)[0]
        file_extension = os.path.splitext(file.filename)[1]
        file_path = os.path.join("output", f"{original_filename}_{timestamp}{file_extension}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 分析文件
        analysis_results = analyze_file(file_path)
        # 直接返回分析结果
        return analysis_results
        
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载分析结果文件
    """
    file_path = os.path.join('output', filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename) 

@app.get("/health")
async def health_check():
    """
    健康检查端点，显示模型状态
    """
    try:
        import os
        import psutil
        memory = psutil.virtual_memory()
        
        # 检查环境和模型状态
        is_render_env = os.getenv('RENDER') or os.getenv('RENDER_SERVICE_ID')
        analyzer = get_sentiment_analyzer()
        model_status = "transformer" if analyzer != "fallback" else "rule-based"
        
        return {
            "status": "healthy",
            "environment": "render.com" if is_render_env else "local",
            "model_type": model_status,
            "model_info": {
                "description": "Enhanced rule-based analysis with 70+ sentiment words" if model_status == "rule-based" else "DistilBERT transformer model",
                "memory_optimized": True if model_status == "rule-based" else False
            },
            "memory_usage": {
                "total_mb": round(memory.total / (1024 * 1024), 1),
                "available_mb": round(memory.available / (1024 * 1024), 1),
                "used_percent": memory.percent
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

def clean_text(text):
    """
    清理文本数据
    """
    try:
        if not isinstance(text, str) or not text:
            return ""
        # 移除特殊标记
        text = re.sub(r'###\s*(USER|ASSISTANT):\s*', '', text)
        # 移除多余的空白字符
        text = ' '.join(text.split())
        return text if text else ""
    except Exception as e:
        logger.error(f"Error cleaning text: {str(e)}")
        return ""

def extract_title(text):
    """
    从文本中提取标题
    """
    try:
        if not isinstance(text, str) or not text:
            return "No Title"
        
        # 清理文本
        text = clean_text(text)
        if not text:
            return "No Title"
        
        # 如果文本很短，直接返回
        if len(text) <= 50:
            return text
        
        # 尝试提取第一句话作为标题
        sentences = re.split(r'[.!?。！？]', text)
        if sentences and sentences[0]:
            title = sentences[0].strip()
            if len(title) > 10:  # 确保标题有意义
                return title[:50] + "..." if len(title) > 50 else title
        
        # 如果没有找到合适的标题，返回前50个字符
        return text[:50] + "..." if len(text) > 50 else text
    except Exception as e:
        logger.error(f"Error extracting title: {str(e)}")
        return "No Title"

def read_csv_file(file_path: str) -> pd.DataFrame:
    """
    读取CSV文件，支持多种分隔符
    """
    try:
        # 首先尝试标准的CSV读取（逗号分隔，支持引号）
        df = pd.read_csv(
            file_path,
            sep=',',
            encoding='utf-8',
            quotechar='"',
            quoting=1,  # QUOTE_ALL
            engine='python',
            on_bad_lines='skip'
        )
        
        # 检查是否只有一列且列名包含分号，说明应该用分号分隔
        if len(df.columns) == 1 and ';' in df.columns[0]:
            logging.info("Detected semicolon-separated data, retrying with semicolon separator")
            raise ValueError("Need to use semicolon separator")
        
        logging.info(f"Successfully read CSV file with comma separator: {len(df)} rows and columns: {df.columns.tolist()}")
        
        # 打印前几行数据用于调试
        if not df.empty:
            logging.info(f"First row data: {df.iloc[0].to_dict()}")
        
        return df
    except Exception as e:
        logging.error(f"Error reading CSV with comma separator: {str(e)}")
        try:
            # 如果失败，尝试使用分号作为分隔符
            df = pd.read_csv(
                file_path,
                sep=';',
                encoding='utf-8',
                quotechar='"',
                quoting=1,
                engine='python',
                on_bad_lines='skip'
            )
            logging.info(f"Successfully read CSV file with semicolon separator: {len(df)} rows and columns: {df.columns.tolist()}")
            
            # 打印前几行数据用于调试
            if not df.empty:
                logging.info(f"First row data: {df.iloc[0].to_dict()}")
            
            return df
        except Exception as e:
            logging.error(f"Error reading CSV with semicolon separator: {str(e)}")
            # 最后尝试自动检测分隔符
            try:
                df = pd.read_csv(
                    file_path,
                    encoding='utf-8',
                    engine='python',
                    on_bad_lines='skip'
                )
                logging.info(f"Successfully read CSV file with auto-detected separator: {len(df)} rows and columns: {df.columns.tolist()}")
                return df
            except Exception as e:
                logging.error(f"Error reading CSV with auto-detected separator: {str(e)}")
                raise

def analyze_file(file_path: str) -> Dict:
    """分析文件内容并返回结果"""
    try:
        # 读取CSV文件
        df = read_csv_file(file_path)
        if df is None or df.empty:
            raise ValueError("No data found in file")
            
        # 获取文本列
        text_column = detect_text_column(df)
        if not text_column:
            raise ValueError("No text column found in the file")
            
        # 分析文本
        results = []
        original_texts = []
        
        # 统计情感分布
        sentiment_stats = {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }
        
        # 创建新的DataFrame来存储结果
        result_rows = []
        
        for index, row in df.iterrows():
            text = row[text_column]
            if pd.isna(text) or not text.strip():
                continue
                
            # 清理文本
            cleaned_text = clean_text(text)
            if not cleaned_text:
                continue
                
            # 分析情感（包含方面分析）
            sentiment_result = analyze_sentiment_with_aspects(cleaned_text)
            
            # 更新统计
            sentiment_stats[sentiment_result['sentiment']] += 1
            
            # 创建基础行信息
            base_row = {
                'Review_ID': row.get('Review_ID', index + 1),
                'Title': safe_string(extract_title(cleaned_text), "No Title"),
                'Content': safe_string(cleaned_text, "No Content"),
                'Overall_Sentiment': safe_string(sentiment_result.get('sentiment'), 'neutral'),
                'Overall_Score': f"{float(sentiment_result.get('score', 0.5)):.2f}",
                'Overall_Polarity': f"{float(sentiment_result.get('polarity', 0.0)):.2f}",
                'Overall_Confidence': f"{float(sentiment_result.get('confidence', 0.5)):.2f}",
                'Overall_Reason': safe_string(sentiment_result.get('reason'), 'No reason available')
                    }
                
            # 添加每个方面的详细信息
            if sentiment_result.get('aspects'):
                for i, aspect in enumerate(sentiment_result['aspects'], 1):
                    base_row[f'Aspect_{i}'] = safe_string(aspect.get('aspect'), 'general')
                    base_row[f'Aspect_{i}_Sentiment'] = safe_string(aspect.get('sentiment'), 'neutral')
                    base_row[f'Aspect_{i}_Confidence'] = f"{float(aspect.get('confidence', 0.5)):.2f}"
                    base_row[f'Aspect_{i}_Reason'] = safe_string(aspect.get('reason'), 'No reason available')
            
            result_rows.append(base_row)
            
            # 添加到结果列表（确保所有数据都是安全的）
            result_sentiment = safe_string(sentiment_result.get('sentiment'), 'neutral')
            result_reason = safe_string(sentiment_result.get('reason'), 'No reason available')
                
            # 确保字符串字段有有效内容
            if not result_sentiment or result_sentiment.strip() == '':
                result_sentiment = 'neutral'
            if not result_reason or result_reason.strip() == '':
                result_reason = 'No reason available'
            
            # 处理aspects数组，确保每个aspect都有有效的字符串字段
            safe_aspects = []
            for aspect in sentiment_result.get('aspects', []):
                if isinstance(aspect, dict):
                    aspect_name = safe_string(aspect.get('aspect'), 'general')
                    aspect_sentiment = safe_string(aspect.get('sentiment'), 'neutral')
                    aspect_reason = safe_string(aspect.get('reason'), 'No reason available')
                    
                    if not aspect_name or aspect_name.strip() == '':
                        aspect_name = 'general'
                    if not aspect_sentiment or aspect_sentiment.strip() == '':
                        aspect_sentiment = 'neutral'
                    if not aspect_reason or aspect_reason.strip() == '':
                        aspect_reason = 'No reason available'
                    
                    safe_aspects.append({
                        'aspect': aspect_name,
                        'sentiment': aspect_sentiment,
                        'confidence': float(aspect.get('confidence', 0.5)),
                        'reason': aspect_reason
                    })
            
            results.append({
                'sentiment': result_sentiment,
                'score': float(sentiment_result.get('score', 0.5)),
                'polarity': float(sentiment_result.get('polarity', 0.0)),
                'confidence': float(sentiment_result.get('confidence', 0.5)),
                'reason': result_reason,
                'aspects': safe_aspects
            })
            
            # 保存原始文本（只保存实际的文本内容，并限制长度以避免前端渲染问题）
            original_text = safe_string(text, "No content available").strip()
            # 确保文本不为空
            if not original_text:
                original_text = "No content available"
            # 如果文本太长，截取前500个字符并添加省略号
            if len(original_text) > 500:
                original_text = original_text[:500] + "..."
            original_texts.append(original_text)
        
        # 创建结果DataFrame（宽格式，用于详细分析）
        result_df = pd.DataFrame(result_rows)
        
        # 生成输出文件名
        output_file = f"transformer_analysis_{int(time.time())}.csv"
        output_path = os.path.join("output", output_file)
        
        # 保存宽格式结果到CSV
        result_df.to_csv(output_path, index=False, encoding='utf-8')
        
        # 创建前端期望的长格式CSV（每一行代表一个方面分析）
        long_format_rows = []
        for result_row in result_rows:
            review_id = result_row['Review_ID']
            content = result_row['Content']
            
            # 查找该行的所有方面分析
            aspect_index = 1
            while f'Aspect_{aspect_index}' in result_row:
                aspect_name = result_row.get(f'Aspect_{aspect_index}', '')
                aspect_sentiment = result_row.get(f'Aspect_{aspect_index}_Sentiment', '')
                aspect_confidence = result_row.get(f'Aspect_{aspect_index}_Confidence', '')
                aspect_reason = result_row.get(f'Aspect_{aspect_index}_Reason', '')
                
                # 只添加有效的方面分析
                if aspect_name and aspect_sentiment:
                    long_format_rows.append({
                        'Review_ID': review_id,
                        'Content': content,
                        'Aspect': aspect_name,
                        'Sentiment': aspect_sentiment,
                        'Confidence': aspect_confidence,
                        'Reason': aspect_reason
                    })
                
                aspect_index += 1
        
        # 如果有长格式数据，保存为额外的CSV文件
        if long_format_rows:
            long_format_df = pd.DataFrame(long_format_rows)
            long_format_file = f"transformer_analysis_long_{int(time.time())}.csv"
            long_format_path = os.path.join("output", long_format_file)
            long_format_df.to_csv(long_format_path, index=False, encoding='utf-8')
            
            # 将长格式文件名作为主要输出文件（前端会下载这个）
            output_file = long_format_file
        
        # 构建aspect_details列表（前端需要这个字段）
        aspect_details = []
        for result in results:
            if result.get('aspects'):
                for aspect in result['aspects']:
                    # 确保所有数值都是有效的浮点数
                    confidence = aspect.get('confidence', 0.5)
                    if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                        confidence = 0.5
                    
                    # 确保所有字段都是有效的字符串和数值
                    aspect_name = safe_string(aspect.get('aspect'), 'general')
                    aspect_sentiment = safe_string(aspect.get('sentiment'), 'neutral')
                    aspect_reason = safe_string(aspect.get('reason'), 'No reason available')
                    
                    # 确保字符串不为空且有有效内容
                    if not aspect_name or aspect_name.strip() == '':
                        aspect_name = 'general'
                    if not aspect_sentiment or aspect_sentiment.strip() == '':
                        aspect_sentiment = 'neutral'
                    if not aspect_reason or aspect_reason.strip() == '':
                        aspect_reason = 'No reason available'
                    
                    aspect_details.append({
                        'aspect': aspect_name,
                        'sentiment': aspect_sentiment,
                        'confidence': float(confidence),
                        'reason': aspect_reason
                    })
        
        # 构建响应数据
        response_data = {
            'total_rows': len(results),
            'analyzed_column': safe_string(text_column, 'Content'),
            'results': results,
            'summary': sentiment_stats,
            'aspect_details': aspect_details,  # 添加aspect_details字段
            'output_file': safe_string(output_file, ''),
            'original_texts': original_texts
        }
        
        # 验证响应数据的完整性
        response_data = validate_response_data(response_data)
        
        # 添加调试日志
        logger.info(f"Analysis completed: {len(results)} results, {len(aspect_details)} aspect details, {len(original_texts)} original texts")
        logger.info(f"Response data keys: {list(response_data.keys())}")
        
        return response_data
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File analysis failed: {str(e)}")

def validate_response_data(data: Dict) -> Dict:
    """
    验证和清理响应数据，确保所有字符串字段都是有效的
    """
    try:
        # 验证顶级字段
        data['total_rows'] = int(data.get('total_rows', 0))
        data['analyzed_column'] = safe_string(data.get('analyzed_column'), 'Content')
        data['output_file'] = safe_string(data.get('output_file'), '')
        
        # 验证summary
        if not isinstance(data.get('summary'), dict):
            data['summary'] = {'positive': 0, 'negative': 0, 'neutral': 0}
        
        # 验证results数组
        if not isinstance(data.get('results'), list):
            data['results'] = []
        else:
            validated_results = []
            for result in data['results']:
                if isinstance(result, dict):
                    validated_result = {
                        'sentiment': safe_string(result.get('sentiment'), 'neutral'),
                        'score': float(result.get('score', 0.5)),
                        'polarity': float(result.get('polarity', 0.0)),
                        'confidence': float(result.get('confidence', 0.5)),
                        'reason': safe_string(result.get('reason'), 'No reason available'),
                        'aspects': []
                    }
                    
                    # 验证aspects
                    if isinstance(result.get('aspects'), list):
                        for aspect in result['aspects']:
                            if isinstance(aspect, dict):
                                validated_result['aspects'].append({
                                    'aspect': safe_string(aspect.get('aspect'), 'general'),
                                    'sentiment': safe_string(aspect.get('sentiment'), 'neutral'),
                                    'confidence': float(aspect.get('confidence', 0.5)),
                                    'reason': safe_string(aspect.get('reason'), 'No reason available')
                                })
                    
                    validated_results.append(validated_result)
            data['results'] = validated_results
        
        # 验证aspect_details数组
        if not isinstance(data.get('aspect_details'), list):
            data['aspect_details'] = []
        else:
            validated_aspect_details = []
            for detail in data['aspect_details']:
                if isinstance(detail, dict):
                    validated_aspect_details.append({
                        'aspect': safe_string(detail.get('aspect'), 'general'),
                        'sentiment': safe_string(detail.get('sentiment'), 'neutral'),
                        'confidence': float(detail.get('confidence', 0.5)),
                        'reason': safe_string(detail.get('reason'), 'No reason available')
                    })
            data['aspect_details'] = validated_aspect_details
        
        # 验证original_texts数组
        if not isinstance(data.get('original_texts'), list):
            data['original_texts'] = []
        else:
            validated_texts = []
            for text in data['original_texts']:
                validated_texts.append(safe_string(text, 'No content available'))
            data['original_texts'] = validated_texts
        
        return data
    except Exception as e:
        logger.error(f"Error validating response data: {str(e)}")
        # 返回最小安全的响应结构
        return {
            'total_rows': 0,
            'analyzed_column': 'Content',
            'results': [],
            'summary': {'positive': 0, 'negative': 0, 'neutral': 0},
            'aspect_details': [],
            'output_file': '',
            'original_texts': []
        }

def detect_text_column(df: pd.DataFrame) -> Optional[str]:
    """检测文本列"""
    if df.empty:
        return None
    
    # 优先查找常见的文本列名
    priority_keywords = ['content', 'text', 'comment', 'review', 'message', 'description']
    for keyword in priority_keywords:
        for col in df.columns:
            if keyword in col.lower():
                logging.info(f"Detected text column: {col}")
                return col
    
    # 如果没有找到，返回最后一列（通常是内容列）
    text_col = df.columns[-1]
    logging.info(f"No specific text column found, using last column: {text_col}")
    return text_col

# 确保输出目录存在
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def get_relevant_sentences(text: str, aspect: str) -> List[str]:
    """
    获取与特定方面相关的句子
    
    Args:
        text (str): 要分析的文本
        aspect (str): 要分析的方面
    
    Returns:
        List[str]: 相关句子列表
    """
    # 方面相关的上下文窗口
    aspect_keywords = {
        'quality': ['quality', 'build', 'material', 'construction', 'durability', 'craftsmanship'],
        'price': ['price', 'cost', 'expensive', 'cheap', 'affordable', 'value', 'money', 'budget'],
        'service': ['service', 'support', 'staff', 'customer', 'help', 'assistance', 'response'],
        'delivery': ['delivery', 'shipping', 'arrival', 'fast', 'slow', 'quick', 'time', 'speed'],
        'design': ['design', 'look', 'appearance', 'style', 'color', 'beautiful', 'ugly', 'aesthetic'],
        'usability': ['easy', 'difficult', 'user', 'interface', 'simple', 'complex', 'convenient'],
        'performance': ['performance', 'speed', 'fast', 'slow', 'efficient', 'work', 'function'],
        'features': ['feature', 'function', 'capability', 'option', 'tool', 'functionality'],
        'packaging': ['package', 'packaging', 'box', 'wrap', 'container', 'presentation'],
        'size': ['size', 'big', 'small', 'large', 'tiny', 'compact', 'huge', 'dimension'],
        'overall': []  # 整体评价
    }
    
    # 获取方面相关的句子和上下文
    sentences = text.split('.')
    relevant_sentences = []
    
    if aspect == 'overall':
        return [text]
    
    keywords = aspect_keywords.get(aspect, [])
    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(keyword in sentence_lower for keyword in keywords):
            relevant_sentences.append(sentence.strip())
    
    # 如果找到相关句子，返回相关句子；否则返回整个文本
    return relevant_sentences if relevant_sentences else [text] 