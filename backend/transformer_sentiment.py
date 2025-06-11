import os
import pandas as pd
from datetime import datetime
import logging
import sys
from typing import Dict, List, Optional, Union, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from transformers import pipeline
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

# 初始化情感分析模型
try:
    sentiment_analyzer = pipeline(
        "sentiment-analysis",
        model="cardiffnlp/twitter-roberta-base-sentiment",
        return_all_scores=True
    )
except Exception as e:
    logging.error(f"Failed to load sentiment analysis model: {str(e)}")
    raise

def analyze_sentiment(text: str) -> Dict:
    """
    分析单个文本的情感
    
    Args:
        text (str): 要分析的文本
    
    Returns:
        Dict: 包含分析结果的字典
    """
    try:
        results = sentiment_analyzer(text)
        # 获取得分最高的情感
        sentiment = max(results[0], key=lambda x: x['score'])
        
        # 转换情感标签
        sentiment_label = sentiment['label']
        if sentiment_label == 'LABEL_0':
            sentiment_label = 'negative'
        elif sentiment_label == 'LABEL_1':
            sentiment_label = 'neutral'
        elif sentiment_label == 'LABEL_2':
            sentiment_label = 'positive'
        
        # 计算极性
        polarity = sentiment['score'] if sentiment_label == 'positive' else -sentiment['score']
        
        return {
            "sentiment": sentiment_label,
            "score": sentiment['score'],
            "polarity": polarity
        }
    except Exception as e:
        logging.error(f"Analysis failed: {str(e)}")
        return {
            "sentiment": "unknown",
            "score": 0,
            "polarity": 0
        }

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
        result = analyze_sentiment(request.text)
        return AnalysisResult(**result)
    except Exception as e:
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

class AspectBasedSentimentAnalyzer:
    """
    基于方面的情感分析器
    """
    def __init__(self):
        # 加载情感分析模型
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment",
            return_all_scores=True
        )
        
        # 定义情感标签映射
        self.sentiment_labels = {
            'LABEL_0': 'negative',
            'LABEL_1': 'neutral',
            'LABEL_2': 'positive'
        }
        
        # 定义情感维度和关键词
        self.aspects = {
            "Gameplay & Strategy": [
                "gameplay", "strategy", "difficulty", "attack", "base", "village", 
                "building", "defense", "planning", "mechanic", "玩法", "策略", 
                "难度", "攻击", "基地", "村庄", "建筑", "防御", "规划", "机制"
            ],
            "Game Progression": [
                "progression", "update", "upgrade", "level", "town hall", "development",
                "progress", "advancement", "进度", "更新", "升级", "等级", "大本营", 
                "发展", "进步", "提升"
            ],
            "Social & Community": [
                "social", "community", "clan", "chat", "team", "interaction", 
                "communication", "leader", "member", "社交", "社区", "部落", "聊天", 
                "团队", "互动", "交流", "领导", "成员"
            ],
            "Combat & Troops": [
                "combat", "troop", "army", "hero", "battle", "war", "attack", 
                "defense", "training", "战斗", "部队", "军队", "英雄", "战争", 
                "攻击", "防御", "训练"
            ],
            "Resources & Economy": [
                "resource", "gold", "elixir", "gem", "currency", "money", "cost", 
                "price", "economy", "资源", "金币", "圣水", "宝石", "货币", 
                "金钱", "成本", "价格", "经济"
            ],
            "Builder Base": [
                "builder base", "builder hall", "builder", "otto", "builder hut", 
                "建筑基地", "建筑大厅", "建筑工人", "奥托", "建筑小屋"
            ],
            "Game Balance": [
                "balance", "fairness", "matchmaking", "trophy", "league", "competition",
                "平衡", "公平", "匹配", "奖杯", "联赛", "竞争"
            ],
            "Technical": [
                "technical", "performance", "graphics", "bug", "crash", "lag", 
                "stability", "compatibility", "技术", "性能", "图形", "错误", 
                "崩溃", "延迟", "稳定性", "兼容性"
            ],
            "Monetization": [
                "monetization", "purchase", "in-app", "microtransaction", "battle pass", 
                "season pass", "value", "price", "货币化", "购买", "应用内", 
                "微交易", "战斗通行证", "赛季通行证", "价值", "价格"
            ],
            "User Experience": [
                "experience", "interface", "usability", "accessibility", "fun", 
                "enjoyment", "entertainment", "体验", "界面", "可用性", "可访问性", 
                "乐趣", "享受", "娱乐"
            ],
            "Content & Features": [
                "content", "feature", "new", "update", "system", "functionality", 
                "内容", "功能", "新", "更新", "系统", "功能性"
            ],
            "Time & Progression": [
                "time", "duration", "wait", "speed", "progress", "investment", 
                "时间", "持续时间", "等待", "速度", "进度", "投入"
            ],
            "Visual & Audio": [
                "visual", "audio", "graphics", "sound", "design", "animation", 
                "visual", "audio", "图形", "声音", "设计", "动画"
            ],
            "Support": [
                "support", "help", "service", "customer", "assistance", "response", 
                "支持", "帮助", "服务", "客户", "协助", "响应"
            ],
            "Technical Issues": [
                "issue", "problem", "error", "bug", "crash", "glitch", "security", 
                "问题", "错误", "崩溃", "故障", "安全"
            ]
        }

    def extract_aspects(self, text):
        """
        提取文本中的各个方面
        """
        text = text.lower()
        found_aspects = {}
        
        # 对每个预定义的方面进行检查
        for aspect, keywords in self.aspects.items():
            # 检查文本是否包含该方面的任何关键词
            if any(keyword in text for keyword in keywords):
                # 提取包含关键词的句子
                sentences = [s.strip() for s in re.split('[.!?。！？]', text) if any(keyword in s.lower() for keyword in keywords)]
                if sentences:
                    found_aspects[aspect] = ' '.join(sentences)
        
        return found_aspects

    def analyze_sentiment(self, text):
        """
        分析文本的情感
        """
        results = self.sentiment_analyzer(text)
        # 获取得分最高的情感
        sentiment = max(results[0], key=lambda x: x['score'])
        
        # 转换情感标签
        sentiment_label = sentiment['label']
        if sentiment_label == 'LABEL_0':
            sentiment_label = 'negative'
        elif sentiment_label == 'LABEL_1':
            sentiment_label = 'neutral'
        elif sentiment_label == 'LABEL_2':
            sentiment_label = 'positive'
        
        # 计算极性
        polarity = sentiment['score'] if sentiment_label == 'positive' else -sentiment['score']
        
        return {
            'sentiment': sentiment_label,
            'score': sentiment['score'],
            'polarity': polarity
        }

    def analyze_aspects(self, text):
        """
        分析文本中各个方面的情感
        """
        # 清理文本
        cleaned_text = clean_text(text)
        
        # 提取各个方面
        aspects = self.extract_aspects(cleaned_text)
        
        # 分析每个方面的情感
        results = {}
        for aspect, aspect_text in aspects.items():
            sentiment_result = self.analyze_sentiment(aspect_text)
            
            results[aspect] = {
                'sentiment': sentiment_result,
                'aspect_text': aspect_text
            }
        
        return results
        
    def generate_reason(self, aspect, text, sentiment_label):
        """
        根据方面和情感生成简短的原因描述
        """
        text = text.lower()
        
        # 通用关键词映射
        sentiment_words = {
            'negative': ['problem', 'bad', 'issue', 'poor', 'negative', 'slow', 'expensive'],
            'neutral': ['okay', 'average', 'normal', 'fair', 'moderate'],
            'positive': ['good', 'great', 'excellent', 'love', 'awesome', 'amazing']
        }
        
        # 方面特定的关键词和短语
        aspect_patterns = {
            "Gameplay & Strategy": {
                'negative': "Game mechanics issues or poor gameplay experience",
                'neutral': "Average gaming experience",
                'positive': "Enjoyable gameplay mechanics"
            },
            "Game Progression": {
                'negative': "Slow progression or update issues",
                'neutral': "Standard progression experience",
                'positive': "Smooth and consistent progression"
            },
            "Social & Community": {
                'negative': "Poor social features or community issues",
                'neutral': "Basic social functionality",
                'positive': "Great social features and community"
            },
            "Combat & Troops": {
                'negative': "Combat or troop issues",
                'neutral': "Standard combat mechanics",
                'positive': "Exciting and effective combat"
            },
            "Resources & Economy": {
                'negative': "Pricing or cost concerns",
                'neutral': "Fair pricing model",
                'positive': "Good value for money"
            },
            "Builder Base": {
                'negative': "Builder base issues",
                'neutral': "Standard builder base functionality",
                'positive': "Well-designed builder base"
            },
            "Game Balance": {
                'negative': "Game balance issues",
                'neutral': "Standard game balance",
                'positive': "Balanced and fair game"
            },
            "Technical": {
                'negative': "Technical issues or performance problems",
                'neutral': "Stable but unremarkable performance",
                'positive': "Smooth and reliable performance"
            },
            "Monetization": {
                'negative': "Monetization concerns",
                'neutral': "Standard monetization model",
                'positive': "Good monetization strategy"
            },
            "User Experience": {
                'negative': "Poor user experience",
                'neutral': "Standard user experience",
                'positive': "Excellent user experience"
            },
            "Content & Features": {
                'negative': "Missing or poor content",
                'neutral': "Standard content",
                'positive': "Excellent content"
            },
            "Time & Progression": {
                'negative': "Slow time progression",
                'neutral': "Standard time progression",
                'positive': "Smooth and consistent time progression"
            },
            "Visual & Audio": {
                'negative': "Poor visual or audio quality",
                'neutral': "Standard visual and audio quality",
                'positive': "Impressive visuals and sound"
            },
            "Support": {
                'negative': "Poor customer support experience",
                'neutral': "Average support response",
                'positive': "Excellent customer support"
            },
            "Technical Issues": {
                'negative': "Technical issues or problems",
                'neutral': "Standard functionality",
                'positive': "Well-designed system"
            }
        }
        
        # 返回对应的原因描述
        return aspect_patterns[aspect][sentiment_label]

def extract_title(text):
    """
    从评论文本中提取标题
    """
    # 清理文本
    text = clean_text(text)
    # 尝试通过冒号分割获取标题
    parts = text.split(':', 1)
    if len(parts) > 1:
        return parts[0].strip()
    return "无标题"  # 如果没有找到冒号，返回"无标题"

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
        analyzer = AspectBasedSentimentAnalyzer()
        results = []
        original_texts = []
        aspect_analysis = []
        aspect_details = []
        
        # 统计情感分布
        sentiment_stats = {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }
        
        # 统计方面分布
        aspect_stats = {}
        
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
            sentiment_result = analyzer.analyze_sentiment(cleaned_text)
            
            # 更新统计
            sentiment_stats[sentiment_result['sentiment']] += 1
            
            # 分析方面
            aspects = analyzer.extract_aspects(cleaned_text)
            
            # 如果没有检测到方面，使用默认值
            if not aspects:
                aspects = {'General': cleaned_text}
            
            # 为每个方面创建一行
            for aspect, aspect_text in aspects.items():
                # 更新方面统计
                if aspect not in aspect_stats:
                    aspect_stats[aspect] = {
                        'positive': 0,
                        'negative': 0,
                        'neutral': 0,
                        'total': 0
                    }
                
                # 分析方面的情感
                aspect_sentiment = analyzer.analyze_sentiment(aspect_text)
                aspect_stats[aspect][aspect_sentiment['sentiment']] += 1
                aspect_stats[aspect]['total'] += 1
                
                # 添加到方面分析结果
                aspect_analysis.append({
                    'aspect': aspect,
                    'sentiment': aspect_sentiment['sentiment'],
                    'score': aspect_sentiment['score']
                })
                
                # 生成原因
                reason = analyzer.generate_reason(aspect, aspect_text, aspect_sentiment['sentiment'])
                
                # 添加到方面详情
                aspect_details.append({
                    'aspect': aspect,
                    'text': aspect_text,
                    'sentiment': aspect_sentiment['sentiment'],
                    'score': aspect_sentiment['score'],
                    'reason': reason
                })
                
                # 创建新的行
                new_row = {
                    'Review_ID': row.get('Review_ID', index + 1),
                    'Title': row.get('Title', extract_title(cleaned_text)),
                    'Content': cleaned_text,
                    'Aspect': aspect,
                    'Sentiment': aspect_sentiment['sentiment'],
                    'Confidence': f"{aspect_sentiment['score'] * 100:.2f}%",
                    'Reason': reason
                }
                result_rows.append(new_row)
            
            # 添加到结果列表
            results.append({
                'text': cleaned_text,
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
        output_path = os.path.join(OUTPUT_DIR, output_file)
        
        # 保存结果到CSV
        result_df.to_csv(output_path, index=False, encoding='utf-8')
        
        # 构建响应数据
        response_data = {
            'total_rows': len(results),
            'analyzed_column': text_column,
            'results': results,
            'summary': {
                'positive': sentiment_stats['positive'],
                'negative': sentiment_stats['negative'],
                'neutral': sentiment_stats['neutral'],
                'total': len(results)
            },
            'aspect_analysis': aspect_analysis,
            'aspect_details': aspect_details,
            'output_file': output_file,
            'original_texts': original_texts
        }
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def detect_text_column(df: pd.DataFrame) -> Optional[str]:
    """检测文本列"""
    for col in df.columns:
        if 'text' in col.lower() or 'content' in col.lower() or 'comment' in col.lower():
            return col
    return df.columns[0] if not df.empty else None

# 确保输出目录存在
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True) 