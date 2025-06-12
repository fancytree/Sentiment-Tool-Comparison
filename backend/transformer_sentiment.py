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

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
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

class AnalysisResult(BaseModel):
    sentiment: str
    score: float
    polarity: float

class TableAnalysisResult(BaseModel):
    total_rows: int
    analyzed_column: str
    results: List[AnalysisResult]
    summary: Dict[str, int]
    output_file: str
    original_texts: Optional[List[str]] = None

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

def analyze_sentiment(text: str) -> Dict:
    """
    分析单个文本的情感
    
    Args:
        text (str): 要分析的文本
    
    Returns:
        Dict: 包含分析结果的字典
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
            "polarity": polarity
        }
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        # 如果模型分析失败，使用简单的基于规则的分析
        return simple_sentiment_analysis(text)

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
    分析单个文本的情感
    """
    try:
        # 预热模型（如果还没有加载）
        analyzer = get_sentiment_analyzer()
        if analyzer != "fallback":
            logger.info("使用 Transformer 模型进行分析")
        else:
            logger.info("使用基于规则的分析")
            
        result = analyze_sentiment(request.text)
        return AnalysisResult(**result)
    except Exception as e:
        logger.error(f"分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
    if not isinstance(text, str):
        return ""
    # 移除特殊标记
    text = re.sub(r'###\s*(USER|ASSISTANT):\s*', '', text)
    # 移除多余的空白字符
    text = ' '.join(text.split())
    return text

def extract_title(text):
    """
    从文本中提取标题
    """
    if not isinstance(text, str):
        return ""
    
    # 清理文本
    text = clean_text(text)
    
    # 如果文本很短，直接返回
    if len(text) <= 50:
        return text
    
    # 尝试提取第一句话作为标题
    sentences = re.split(r'[.!?。！？]', text)
    if sentences:
        title = sentences[0].strip()
        if len(title) > 10:  # 确保标题有意义
            return title[:50] + "..." if len(title) > 50 else title
    
    # 如果没有找到合适的标题，返回前50个字符
    return text[:50] + "..." if len(text) > 50 else text

def read_csv_file(file_path: str) -> pd.DataFrame:
    """
    读取CSV文件，支持多种分隔符
    """
    try:
        # 首先尝试使用分号作为分隔符
        df = pd.read_csv(
            file_path,
            sep=';',
            encoding='utf-8',
            quoting=1,  # QUOTE_ALL
            engine='python',
            on_bad_lines='skip'
        )
        logging.info(f"Successfully read CSV file with {len(df)} rows and columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        logging.error(f"Error reading CSV with semicolon separator: {str(e)}")
        try:
            # 如果失败，尝试使用逗号作为分隔符
            df = pd.read_csv(
                file_path,
                sep=',',
                encoding='utf-8',
                quoting=1,
                engine='python',
                on_bad_lines='skip'
            )
            logging.info(f"Successfully read CSV file with comma separator: {len(df)} rows")
            return df
        except Exception as e:
            logging.error(f"Error reading CSV with comma separator: {str(e)}")
            # 最后尝试自动检测分隔符
            try:
                df = pd.read_csv(
                    file_path,
                    encoding='utf-8',
                    engine='python',
                    on_bad_lines='skip'
                )
                logging.info(f"Successfully read CSV file with auto-detected separator: {len(df)} rows")
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
                
            # 分析情感
            sentiment_result = analyze_sentiment(cleaned_text)
            
            # 更新统计
            sentiment_stats[sentiment_result['sentiment']] += 1
            
            # 创建新的行
            new_row = {
                'Review_ID': row.get('Review_ID', index + 1),
                'Title': extract_title(cleaned_text),
                'Content': cleaned_text,
                'Sentiment': sentiment_result['sentiment'],
                'Score': f"{sentiment_result['score']:.2f}",
                'Polarity': f"{sentiment_result['polarity']:.2f}"
            }
            result_rows.append(new_row)
            
            # 添加到结果列表
            results.append({
                'sentiment': sentiment_result['sentiment'],
                'score': sentiment_result['score'],
                'polarity': sentiment_result['polarity']
            })
            
            # 保存原始文本
            original_texts.append(cleaned_text)
        
        # 创建结果DataFrame
        result_df = pd.DataFrame(result_rows)
        
        # 生成输出文件名
        output_file = f"transformer_analysis_{int(time.time())}.csv"
        output_path = os.path.join("output", output_file)
        
        # 保存结果到CSV
        result_df.to_csv(output_path, index=False, encoding='utf-8')
        
        # 构建响应数据
        response_data = {
            'total_rows': len(results),
            'analyzed_column': text_column,
            'results': results,
            'summary': sentiment_stats,
            'output_file': output_file,
            'original_texts': original_texts
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File analysis failed: {str(e)}")

def detect_text_column(df: pd.DataFrame) -> Optional[str]:
    """检测文本列"""
    for col in df.columns:
        if 'text' in col.lower() or 'content' in col.lower() or 'comment' in col.lower():
            return col
    return df.columns[0] if not df.empty else None

# 确保输出目录存在
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True) 