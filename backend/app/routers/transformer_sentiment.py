from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import pandas as pd
import os
import json
import io
from datetime import datetime
import uuid
import shutil
import re
from typing import List, Dict, Any, Optional
from transformers import pipeline
import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from collections import Counter
import numpy as np

# 确保nltk资源已下载
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Create router
router = APIRouter(
    prefix="/api/transformer-sentiment",
    tags=["transformer-sentiment"],
    responses={404: {"description": "Not found"}},
)

# Create sentiment analysis model
print("正在初始化Transformer情感分析器...")

class TransformerSentimentAnalyzer:
    def __init__(self):
        # 加载情感分析模型
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment",
            return_all_scores=True
        )
        
    def __call__(self, texts):
        if not isinstance(texts, list):
            texts = [texts]
        
        results = []
        for text in texts:
            try:
                # 直接使用transformers的pipeline进行分析
                result = self.sentiment_analyzer(text)
                results.append(result)
                
                # 打印调试信息
                scores = {item['label']: item['score'] for item in result[0]}
                max_sentiment = max(result[0], key=lambda x: x['score'])
                print(f"Analysis for: '{text[:50]}...'")
                print(f"Scores: {scores}")
                print(f"Final sentiment: {max_sentiment['label']} with score {max_sentiment['score']:.2f}")
            except Exception as e:
                print(f"Error analyzing text: {str(e)}")
                # 返回一个默认的中性结果
                results.append([
                    {"label": "LABEL_0", "score": 0.2},  # negative
                    {"label": "LABEL_1", "score": 0.6},  # neutral
                    {"label": "LABEL_2", "score": 0.2}   # positive
                ])
        
        return results

sentiment_analyzer = TransformerSentimentAnalyzer()
print("成功初始化Transformer情感分析器")

# Define models
class TextRequest(BaseModel):
    text: str

class AnalysisResult(BaseModel):
    sentiment: str
    score: float
    polarity: float

class SummaryResult(BaseModel):
    positive: int
    negative: int
    neutral: int
    total: int

class AspectSentiment(BaseModel):
    aspect: str
    positive: int
    negative: int
    neutral: int
    total: int

class AspectAnalysisResult(BaseModel):
    aspect: str
    sentiment: str
    confidence: float
    reason: str

class TableAnalysisResult(BaseModel):
    total_rows: int
    analyzed_column: str
    results: List[AnalysisResult]
    summary: SummaryResult
    aspect_analysis: List[AspectSentiment]
    aspect_details: List[AspectAnalysisResult]
    output_file: str
    original_texts: List[str] = []

# Output directory
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Sentiment labels mapping
SENTIMENT_LABELS = {
    'LABEL_0': 'negative',
    'LABEL_1': 'neutral',
    'LABEL_2': 'positive'
}

# Define aspects and related keywords
ASPECTS = {
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

# Aspect reason templates
ASPECT_REASONS = {
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

class AspectBasedSentimentAnalyzer:
    """
    基于方面的情感分析器
    """
    def __init__(self):
        # 加载情感分析模型
        print("初始化情感分析模型...")
        self.sentiment_analyzer = sentiment_analyzer
        
        # 定义情感标签映射
        self.sentiment_labels = SENTIMENT_LABELS
        
        # 加载NLTK资源
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        
        # 添加自定义停用词
        self.stop_words.update(['also', 'would', 'could', 'should', 'may', 'might', 'many', 'much'])
        
        # TF-IDF向量化器
        self.vectorizer = TfidfVectorizer(
            max_df=0.9,
            min_df=2,
            max_features=1000,
            stop_words='english'
        )

    def extract_aspects(self, text):
        """
        自动提取文本中的各个方面
        """
        # 清理并分割文本为句子
        cleaned_text = clean_text(text)
        sentences = sent_tokenize(cleaned_text)
        
        if len(sentences) <= 3:  # 如果句子太少，整体当作一个方面
            return {"Content Overview": cleaned_text}
        
        # 预处理每个句子，删除停用词和标点
        processed_sentences = []
        for sentence in sentences:
            # 保留原始句子用于后续分析
            processed_sentences.append(sentence)
        
        # 如果句子数量太少，无法进行聚类
        if len(processed_sentences) < 3:
            return {"Content Overview": " ".join(processed_sentences)}
            
        try:
            # 使用TF-IDF向量化句子
            tfidf_matrix = self.vectorizer.fit_transform(processed_sentences)
            
            # 确定聚类数量
            num_clusters = min(max(3, len(processed_sentences) // 3), 8)
            
            # 使用KMeans进行聚类
            km = KMeans(n_clusters=num_clusters, random_state=42)
            km.fit(tfidf_matrix)
            clusters = km.labels_.tolist()
            
            # 获取每个聚类的关键词作为方面名称
            order_centroids = km.cluster_centers_.argsort()[:, ::-1]
            terms = self.vectorizer.get_feature_names_out()
            
            # 构建方面字典
            aspects = {}
            for i in range(num_clusters):
                # 获取当前聚类的前3个关键词作为方面名称
                aspect_keywords = [terms[ind] for ind in order_centroids[i, :3]]
                aspect_name = self.generate_aspect_name(aspect_keywords)
                
                # 收集属于该聚类的所有句子
                cluster_sentences = [processed_sentences[j] for j in range(len(processed_sentences)) if clusters[j] == i]
                
                if cluster_sentences:  # 确保有句子分配给这个方面
                    aspects[aspect_name] = " ".join(cluster_sentences)
            
            # 如果没有成功提取方面，使用整个文本
            if not aspects:
                aspects["Content Overview"] = cleaned_text
                
            return aspects
            
        except Exception as e:
            print(f"提取方面时出错: {str(e)}")
            # 出错时返回整个文本作为一个方面
            return {"Content Overview": cleaned_text}
    
    def generate_aspect_name(self, keywords):
        """根据关键词生成方面名称"""
        # 常见的方面名称模板
        aspect_templates = {
            "product": ["product", "quality", "design", "build", "construct", "material"],
            "performance": ["performance", "speed", "fast", "slow", "quick", "responsive"],
            "usability": ["use", "user", "usability", "easy", "difficult", "intuitive", "interface"],
            "service": ["service", "customer", "support", "staff", "help", "assist"],
            "price": ["price", "cost", "value", "expensive", "cheap", "worth"],
            "feature": ["feature", "function", "option", "capability"],
            "reliability": ["reliable", "stability", "stable", "consistent", "dependable"],
            "experience": ["experience", "impression", "overall", "general"],
            "content": ["content", "information", "data", "knowledge", "overview"],
            "technical": ["technical", "technology", "software", "hardware", "system"],
            "gameplay": ["gameplay", "play", "game", "mechanic"],
            "visual": ["visual", "graphic", "display", "screen", "look"],
            "audio": ["audio", "sound", "noise", "voice", "speaker"],
            "issue": ["issue", "problem", "bug", "error", "defect"],
            "improve": ["improve", "enhancement", "upgrade", "update"]
        }
        
        # 检查关键词是否匹配任何模板
        for aspect, related_words in aspect_templates.items():
            for keyword in keywords:
                if keyword.lower() in related_words:
                    # 使用第一个匹配的关键词构建方面名称
                    matched_word = next((word for word in keywords if word.lower() != keyword.lower()), keywords[0])
                    return f"{aspect.capitalize()} & {matched_word.capitalize()}"
        
        # 如果没有匹配，使用前两个关键词
        if len(keywords) >= 2:
            return f"{keywords[0].capitalize()} & {keywords[1].capitalize()}"
        elif len(keywords) == 1:
            return f"{keywords[0].capitalize()} Analysis"
        else:
            return "General Analysis"

    def analyze_sentiment(self, text):
        """
        分析文本的情感
        """
        results = self.sentiment_analyzer(text)
        return results[0]

    def analyze_aspects(self, text):
        """
        分析文本中各个方面的情感
        """
        # 清理文本
        cleaned_text = clean_text(text)
        
        # 自动提取各个方面
        aspects = self.extract_aspects(cleaned_text)
        
        # 分析每个方面的情感
        results = {}
        for aspect, aspect_text in aspects.items():
            try:
                # 使用与该方面相关的文本内容进行情感分析
                sentiment_result = self.analyze_sentiment(aspect_text)
                
                # 获取最高分的情感
                sentiment = max(sentiment_result[0], key=lambda x: x['score'])
                sentiment_label = self.sentiment_labels[sentiment['label']]
                confidence = sentiment['score'] * 100
                
                # 生成简短的原因描述
                reason = self.generate_reason(aspect, sentiment_label, aspect_text)
                
                results[aspect] = {
                    'sentiment': sentiment_label,
                    'confidence': confidence,
                    'reason': reason
                }
            except Exception as e:
                print(f"分析方面 '{aspect}' 时出错: {str(e)}")
                continue
        
        return results
        
    def generate_reason(self, aspect, sentiment_label, text):
        """
        根据方面、情感和文本生成简短的总结描述，控制在50字以内
        """
        # 根据情感和方面生成总结性描述
        general_reasons = {
            'positive': {
                "Gameplay & Strategy": "Smooth and engaging gameplay with strong strategic elements",
                "Game Progression": "Well-designed progression with rewarding advancement system",
                "Social & Community": "Excellent social features with a positive community atmosphere",
                "Combat & Troops": "Balanced combat system with diverse troop design",
                "Resources & Economy": "Fair resource acquisition and balanced economy system",
                "Builder Base": "Well-designed builder base with enjoyable features",
                "Game Balance": "Good game balance with fair matchmaking system",
                "Technical": "Stable technical implementation with smooth performance",
                "Monetization": "Reasonable pricing model without forced spending",
                "User Experience": "Fluid user experience with intuitive interface design",
                "Content & Features": "Rich and diverse content with practical feature design",
                "Time & Progression": "Balanced time investment with appropriate rewards",
                "Visual & Audio": "Impressive visual and audio design elements",
                "Support": "Responsive customer support that effectively resolves issues",
                "Technical Issues": "Few technical problems with good overall stability"
            },
            'negative': {
                "Gameplay & Strategy": "Problematic gameplay with insufficient strategic depth",
                "Game Progression": "Slow progression with excessive upgrade waiting times",
                "Social & Community": "Incomplete social features with poor community management",
                "Combat & Troops": "Unbalanced combat system with flawed troop design",
                "Resources & Economy": "Difficult resource acquisition with unfair economy",
                "Builder Base": "Poorly designed builder base with negative experience",
                "Game Balance": "Poor game balance with unfair matchmaking system",
                "Technical": "Unstable implementation with frequent lag or crashes",
                "Monetization": "Unreasonable pricing model with obvious pay-to-win elements",
                "User Experience": "Clunky user experience with complex interface design",
                "Content & Features": "Repetitive content with impractical feature design",
                "Time & Progression": "Excessive time investment with disproportionate rewards",
                "Visual & Audio": "Mediocre visual and audio design with notable flaws",
                "Support": "Unresponsive customer support that doesn't solve problems",
                "Technical Issues": "Frequent technical problems with poor stability"
            },
            'neutral': {
                "Gameplay & Strategy": "Average gameplay and strategic elements",
                "Game Progression": "Standard progression design and rewards",
                "Social & Community": "Basic social features and community experience",
                "Combat & Troops": "Standard combat system and troop design",
                "Resources & Economy": "Average resource acquisition and economy experience",
                "Builder Base": "Functional builder base with basic features",
                "Game Balance": "Average game balance and matchmaking system",
                "Technical": "Standard technical stability",
                "Monetization": "Average pricing model with room for improvement",
                "User Experience": "Standard user experience and interface design",
                "Content & Features": "Average content and feature design",
                "Time & Progression": "Standard time investment and progression rewards",
                "Visual & Audio": "Average visual and audio design",
                "Support": "Basic customer support that meets minimal needs",
                "Technical Issues": "Occasional technical issues that don't impact main experience"
            }
        }
        
        # 获取与方面匹配的原因描述
        for aspect_category, reasons in general_reasons[sentiment_label.lower()].items():
            if aspect_category.lower() in aspect.lower() or aspect.lower() in aspect_category.lower():
                return reasons
                
        # 提取关键词，创建通用描述
        # 如果没有匹配到预定义的方面，使用通用描述
        general_templates = {
            'positive': f"Excellent {aspect} experience with positive user feedback",
            'negative': f"Poor {aspect} experience with significant issues",
            'neutral': f"Average {aspect} experience with both pros and cons"
        }
        
        return general_templates[sentiment_label.lower()]

def clean_text(text):
    """Clean text data by removing special markers and whitespace"""
    # Remove special markers
    text = re.sub(r'###\s*(USER|ASSISTANT):\s*', '', text)
    # Remove excess whitespace
    text = ' '.join(text.split())
    return text

# Analyze single text
def analyze_text(text: str) -> AnalysisResult:
    """Use Transformer model to analyze text sentiment"""
    try:
        # Clean the text
        text = clean_text(text)
        
        # Use transformers for sentiment analysis
        results = sentiment_analyzer(text)
        
        # Get the highest scoring sentiment
        max_sentiment = max(results[0][0], key=lambda x: x['score'])
        sentiment = SENTIMENT_LABELS[max_sentiment['label']]
        score = max_sentiment['score'] * 100  # Convert to percentage
        
        # Calculate polarity (-1 to 1 range)
        polarity = 0
        if sentiment == "positive":
            polarity = max_sentiment['score']
        elif sentiment == "negative":
            polarity = -max_sentiment['score']
        
        return AnalysisResult(
            sentiment=sentiment,
            score=round(score, 2),
            polarity=round(polarity, 2)
        )
    except Exception as e:
        print(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

def analyze_aspects_sentiment(text: str) -> List[AspectAnalysisResult]:
    """Analyze aspects and their sentiments in text"""
    analyzer = AspectBasedSentimentAnalyzer()
    aspect_results = []
    
    # 分析文本中各个方面的情感
    aspects_analysis = analyzer.analyze_aspects(text)
    
    # 处理分析结果
    for aspect, result in aspects_analysis.items():
        aspect_results.append(AspectAnalysisResult(
            aspect=aspect,
            sentiment=result['sentiment'],
            confidence=round(result['confidence'], 2),
            reason=result['reason']
        ))
    
    return aspect_results

# Analyze table file
def analyze_file(file_path: str, column_name: str = None, aspect_column: str = None) -> TableAnalysisResult:
    """Analyze text in CSV, Excel or TSV files"""
    try:
        # Read file based on extension
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # 尝试自动检测分隔符
        if file_ext == '.csv':
            # 首先尝试读取文件的前几行来检测分隔符
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                
            # 检查是否使用分号作为分隔符
            if ';' in first_line:
                print("检测到分号(;)分隔符")
                df = pd.read_csv(file_path, sep=';')
            else:
                print("使用默认逗号(,)分隔符")
                df = pd.read_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            df = pd.read_excel(file_path)
        elif file_ext == '.tsv':
            df = pd.read_csv(file_path, sep='\t')
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # Check if data is empty
        if df.empty:
            raise ValueError("File contains no data")
        
        # 数据清理：删除内容为空的行
        original_row_count = len(df)
        print(f"原始数据行数: {original_row_count}")
        
        # 清理数据前先打印前几行
        print("清理前的数据:")
        print(df.head())
        
        # 查找文本列
        if not column_name or column_name not in df.columns:
            # 优先检查常见的文本列名
            common_text_columns = ['Text', 'text', 'comment', 'Comment', 'content', 'Content']
            
            # 首先尝试精确匹配列名
            for col in common_text_columns:
                if col in df.columns:
                    column_name = col
                    print(f"使用文本列: {column_name}")
                    break
            
            # 如果没有找到精确匹配，尝试部分匹配
            if not column_name:
                for col in df.columns:
                    col_lower = col.lower()
                    if any(text_col.lower() in col_lower for text_col in common_text_columns):
                        column_name = col
                        print(f"使用部分匹配的文本列: {column_name}")
                        break
            
            # 如果仍未找到，使用第一个字符串类型的列
            if not column_name:
                text_columns = [col for col in df.columns if df[col].dtype == 'object']
                if not text_columns:
                    raise ValueError("No text column found")
                column_name = text_columns[0]
                print(f"使用第一个字符串类型列: {column_name}")
        
        print(f"最终使用的文本列: {column_name}")
        
        # 删除文本列内容为空的行
        df = df.dropna(subset=[column_name])
        df = df[df[column_name].astype(str).str.strip() != '']
        
        cleaned_row_count = len(df)
        print(f"清理后的数据行数: {cleaned_row_count}")
        print(f"删除了 {original_row_count - cleaned_row_count} 行空数据")
        
        # 清理后再打印前几行
        print("清理后的数据:")
        print(df.head())
        
        # 如果清理后没有数据了，抛出错误
        if df.empty:
            raise ValueError("After cleaning empty rows, no data remains for analysis")
        
        # Find aspect column (if any)
        aspect_column_exists = False
        if aspect_column and aspect_column in df.columns:
            aspect_column_exists = True
        elif 'aspect' in [col.lower() for col in df.columns]:
            aspect_column = df.columns[[col.lower() == 'aspect' for col in df.columns]].tolist()[0]
            aspect_column_exists = True
        
        if aspect_column_exists:
            print(f"Using aspect column: {aspect_column}")
        
        # 创建情感分析器
        analyzer = AspectBasedSentimentAnalyzer()
        
        # 创建两个列表分别存储评论信息和分析结果
        reviews_data = []  # 存储评论基本信息
        analysis_results = []  # 存储分析结果
        
        # 分析结果变量
        results = []  # 存储基本情感分析结果
        all_aspect_details = []  # 存储方面详细分析结果
        
        # Debug: Print total number of rows to analyze
        print(f"Total rows to analyze: {len(df)}")
        
        # Make sure we're iterating through all rows
        total_rows = len(df)  # 原始行数
        original_contents = []  # 存储所有非空原始内容
        processed_rows = 0
        
        # 标题列
        title_col = None
        if 'title' in [col.lower() for col in df.columns]:
            title_cols = [col for col in df.columns if col.lower() == 'title']
            if title_cols:
                title_col = title_cols[0]
        
        # 遍历每一行进行分析
        for idx, row in df.iterrows():
            try:
                # 获取评论内容
                content = str(row[column_name])
                
                # 处理可能的分号问题
                if ';' in content and content.count(';') > 3:  # 如果包含多个分号，可能是分隔符问题
                    parts = content.split(';')
                    # 尝试提取最长的部分作为内容
                    longest_part = max(parts, key=len)
                    if len(longest_part) > 10:  # 确保有足够的内容
                        print(f"修复行 {idx} 的分号问题: 原长度 {len(content)}，修复后长度 {len(longest_part)}")
                        content = longest_part
                
                # 获取标题
                title = str(row[title_col]) if title_col else f"Review {idx+1}"
                
                # Debug 输出
                print(f"分析行 {idx}: '{content[:50]}...' (长度: {len(content)})")
                print(f"标题: {title}")

                # 如果内容不为空，添加到原始内容列表
                if content and content.lower() != 'nan' and content.strip() != '':
                    # 存储评论基本信息
                    review_data = {
                        'Review_ID': idx + 1,
                        'Title': title,
                        'Content': content
                    }
                    reviews_data.append(review_data)
                    # 记录原始内容
                    original_contents.append(content)
                else:
                    print(f"跳过行 {idx}: 空或NaN文本")
                    continue
                
                # Basic sentiment analysis
                result = analyze_text(content)
                print(f"  - Sentiment: {result.sentiment}, Score: {result.score}%")
                results.append(result)
                processed_rows += 1
                
                # Aspect-based analysis
                aspects_analysis = analyzer.analyze_aspects(content)
                
                if not aspects_analysis:
                    print(f"  - 未找到任何可分析的方面，添加一个通用方面")
                    # 为没有方面的内容添加一个"General Content"方面
                    general_sentiment = result.sentiment
                    general_confidence = result.score
                    
                    # 创建一个通用方面结果
                    generic_aspect = "Content Overview"
                    generic_reason = f"General {general_sentiment} sentiment detected in the content."
                    
                    # 添加到方面分析结果
                    aspect_result = AspectAnalysisResult(
                        aspect=generic_aspect,
                        sentiment=general_sentiment,
                        confidence=general_confidence,
                        reason=generic_reason
                    )
                    all_aspect_details.append(aspect_result)
                    
                    # 添加到分析结果列表
                    analysis_results.append({
                        'Review_ID': idx + 1,
                        'Aspect': generic_aspect,
                        'Sentiment': general_sentiment,
                        'Confidence': general_confidence,
                        'Reason': generic_reason
                    })
                else:
                    # 处理每个方面的结果
                    for aspect, data in aspects_analysis.items():
                        aspect_result = AspectAnalysisResult(
                            aspect=aspect,
                            sentiment=data['sentiment'],
                            confidence=round(data['confidence'], 2),
                            reason=data['reason']
                        )
                        all_aspect_details.append(aspect_result)
                        
                        # 添加到分析结果列表
                        analysis_results.append({
                            'Review_ID': idx + 1,
                            'Aspect': aspect,
                            'Sentiment': data['sentiment'],
                            'Confidence': round(data['confidence'], 2),
                            'Reason': data['reason']
                        })
            except Exception as e:
                print(f"Error analyzing row {idx}: {str(e)}")
                continue
        
        # Debug: Print analysis summary
        print(f"Processed {processed_rows} out of {total_rows} rows")
        print(f"原始内容数量: {len(original_contents)}")
        print(f"分析结果数量: {len(results)}")
        print(f"方面分析结果数量: {len(all_aspect_details)}")
        
        if processed_rows == 0:
            raise ValueError("No rows were processed. Please check your file format and content.")
        
        # Generate summary
        positive = sum(1 for r in results if r.sentiment == "positive")
        negative = sum(1 for r in results if r.sentiment == "negative")
        neutral = sum(1 for r in results if r.sentiment == "neutral")
        total = len(results)
        
        # Debug: Print sentiment summary
        print(f"Sentiment summary - Positive: {positive}, Negative: {negative}, Neutral: {neutral}, Total: {total}")
        
        # Aspect-based analysis
        aspect_analysis = []
        
        # If we have aspect details, summarize them
        if all_aspect_details:
            aspect_counts = {}
            for aspect_result in all_aspect_details:
                aspect = aspect_result.aspect
                sentiment = aspect_result.sentiment
                
                if aspect not in aspect_counts:
                    aspect_counts[aspect] = {'positive': 0, 'negative': 0, 'neutral': 0, 'total': 0}
                
                aspect_counts[aspect][sentiment] += 1
                aspect_counts[aspect]['total'] += 1
            
            # Convert to list of AspectSentiment objects
            for aspect, counts in aspect_counts.items():
                aspect_analysis.append(AspectSentiment(
                    aspect=aspect,
                    positive=counts['positive'],
                    negative=counts['negative'],
                    neutral=counts['neutral'],
                    total=counts['total']
                ))
        
        # Generate output file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"transformer_analysis_{timestamp}.csv"
        output_path = os.path.join(OUTPUT_DIR, output_file)
        
        # 将评论内容和分析结果合并成DataFrame
        original_texts = []
        if reviews_data:
            reviews_df = pd.DataFrame(reviews_data)
            analysis_df = pd.DataFrame(analysis_results)
            
            # 保存原始文本
            for review in reviews_data:
                original_texts.append(review['Content'])
            
            # 如果有分析结果
            if not analysis_results:
                # 如果没有方面分析结果，直接保存评论数据
                reviews_df.to_csv(output_path, index=False, encoding='utf-8')
                aspect_details = []
            else:
                # 合并两个DataFrame
                result_df = pd.merge(reviews_df, analysis_df, on='Review_ID', how='inner')
                
                # 确保Confidence列是字符串格式的百分比
                result_df['Confidence'] = result_df['Confidence'].apply(lambda x: f"{x}%" if isinstance(x, (int, float)) else x)
                
                # 重新排列列的顺序
                result_df = result_df[['Review_ID', 'Title', 'Content', 'Aspect', 'Sentiment', 'Confidence', 'Reason']]
                
                # 保存合并后的结果
                result_df.to_csv(output_path, index=False, encoding='utf-8')
                
                # 直接将DataFrame转为dict列表返回，保证与导出文件一致
                aspect_details = result_df.to_dict(orient='records')
            # 更新all_aspect_details
            all_aspect_details = aspect_details
        else:
            # 如果没有评论数据，创建一个简单的结果DataFrame
            result_records = []
            for idx, result in enumerate(results):
                record = {
                    "Review_ID": idx + 1,
                    "Sentiment": result.sentiment,
                    "Confidence": f"{result.score}%",
                    "Polarity": result.polarity
                }
                result_records.append(record)
            
            result_df = pd.DataFrame(result_records)
            result_df.to_csv(output_path, index=False, encoding='utf-8')
        
        print(f"Analysis results saved to: {output_path}")
        
        # 统计信息
        print("\n基本统计信息：")
        print(f"总评论数: {len(reviews_data)}")
        print(f"总aspect数: {len(analysis_results)}")
        
        if analysis_results:
            # 创建临时DataFrame以便使用value_counts()
            temp_df = pd.DataFrame(analysis_results)
            print("\n分析得到的Aspect分布：")
            print(temp_df['Aspect'].value_counts())
            print("\n分析得到的情感分布：")
            print(temp_df['Sentiment'].value_counts())
        
        return TableAnalysisResult(
            total_rows=len(original_contents),  # 使用原始内容的数量而不是处理的行数
            analyzed_column=column_name,
            results=results,
            summary=SummaryResult(
                positive=positive,
                negative=negative,
                neutral=neutral,
                total=total
            ),
            aspect_analysis=aspect_analysis,
            aspect_details=all_aspect_details,  # 直接返回dict列表
            output_file=output_file,
            original_texts=original_contents  # 使用记录的原始内容
        )
    except Exception as e:
        print(f"File analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"File analysis failed: {str(e)}")

@router.post("/", response_model=AnalysisResult)
async def analyze_sentiment(request: TextRequest):
    """Analyze sentiment of a single text"""
    try:
        print(f"分析文本: {request.text}")
        result = analyze_text(request.text)
        print(f"分析结果: {result}")
        return result
    except Exception as e:
        print(f"分析出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@router.post("/upload", response_model=TableAnalysisResult)
async def upload_and_analyze(
    file: UploadFile = File(...),
    text_column: str = None,
    aspect_column: str = None,
    background_tasks: BackgroundTasks = None
):
    """Upload and analyze a file"""
    try:
        # 创建临时文件来保存上传的内容
        temp_file = f"temp_{uuid.uuid4().hex}.csv"
        temp_path = os.path.join(OUTPUT_DIR, temp_file)
        
        # 保存上传的文件
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        print(f"文件已保存到临时路径: {temp_path}")
        
        # 分析文件
        try:
            result = analyze_file(temp_path, text_column, aspect_column)
            # 分析完成后删除临时文件
            os.remove(temp_path)
            return result
        except Exception as e:
            # 发生错误时也清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
            print(f"分析过程中出错: {str(e)}")
            raise HTTPException(status_code=500, detail=f"文件分析失败: {str(e)}")
    except Exception as e:
        print(f"上传处理错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传处理失败: {str(e)}")

@router.get("/download/{filename}")
async def download_result(filename: str):
    """Download analysis result file"""
    try:
        print(f"尝试下载文件: {filename}")
        
        # 检查文件是否存在
        file_path = os.path.join(OUTPUT_DIR, filename)
        excel_path = os.path.join(OUTPUT_DIR, filename.replace('.csv', '.xlsx'))
        
        print(f"检查CSV路径: {file_path}")
        print(f"检查Excel路径: {excel_path}")
        
        # 列出output目录中的所有文件以进行调试
        files_in_output = os.listdir(OUTPUT_DIR)
        print(f"Output目录中的文件: {files_in_output}")
        
        # 先检查Excel版本
        if os.path.exists(excel_path):
            print(f"找到Excel文件，返回: {excel_path}")
            return FileResponse(
                path=excel_path,
                filename=filename.replace('.csv', '.xlsx'),
                media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        
        # 然后检查CSV版本
        if os.path.exists(file_path):
            print(f"找到CSV文件，返回: {file_path}")
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type="text/csv"
            )
        
        # 如果都找不到，尝试部分匹配
        for file in files_in_output:
            if filename in file:
                matched_path = os.path.join(OUTPUT_DIR, file)
                print(f"找到部分匹配的文件: {matched_path}")
                
                if file.endswith('.xlsx'):
                    return FileResponse(
                        path=matched_path,
                        filename=file,
                        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    return FileResponse(
                        path=matched_path,
                        filename=file,
                        media_type="text/csv"
                    )
        
        # 如果仍然找不到文件
        print(f"文件未找到: {filename}")
        raise HTTPException(status_code=404, detail=f"找不到文件: {filename}")
    except Exception as e:
        print(f"下载文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")

@router.get("/visualization/{filename}")
async def get_visualization_data(filename: str):
    """Get visualization data"""
    # Check if we have an Excel version first
    excel_path = os.path.join(OUTPUT_DIR, filename.replace('.csv', '.xlsx'))
    if os.path.exists(excel_path):
        try:
            # Read all sheets
            sentiment_df = pd.read_excel(excel_path, sheet_name='Sentiment Analysis')
            aspect_df = pd.read_excel(excel_path, sheet_name='Aspect Analysis')
            
            # Process visualization data
            return process_visualization_data(sentiment_df, aspect_df)
        except Exception as e:
            print(f"Error reading Excel file: {str(e)}")
            # Fall back to CSV if Excel reading fails
            pass
    
    # Fall back to CSV
    file_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    try:
        df = pd.read_csv(file_path)
        return process_visualization_data(df)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get visualization data: {str(e)}")

def process_visualization_data(df, aspect_df=None):
    """Process dataframes into visualization data"""
    # Sentiment distribution
    sentiment_counts = df["Sentiment"].value_counts().to_dict()
    
    # Confidence distribution (remove percentage and convert to float)
    df["Confidence_Value"] = df["Confidence"].str.replace("%", "").astype(float)
    confidence_stats = {
        "Average": round(df["Confidence_Value"].mean(), 2),
        "Min": round(df["Confidence_Value"].min(), 2),
        "Max": round(df["Confidence_Value"].max(), 2),
        "Median": round(df["Confidence_Value"].median(), 2)
    }
    
    # Polarity distribution
    polarity_bins = [-1.0, -0.6, -0.2, 0.2, 0.6, 1.0]
    polarity_labels = ["Strong Negative", "Moderate Negative", "Neutral", "Moderate Positive", "Strong Positive"]
    
    if "Polarity" in df.columns:
        df["Polarity_Group"] = pd.cut(df["Polarity"], bins=polarity_bins, labels=polarity_labels, include_lowest=True)
        polarity_dist = df["Polarity_Group"].value_counts().sort_index().to_dict()
    else:
        polarity_dist = {}
    
    # Aspect distribution
    aspect_distribution = {}
    
    # If we have dedicated aspect analysis
    if aspect_df is not None and not aspect_df.empty:
        for aspect in aspect_df["Aspect"].unique():
            aspect_data = aspect_df[aspect_df["Aspect"] == aspect]
            aspect_distribution[aspect] = {
                "positive": int(aspect_data[aspect_data["Sentiment"] == "positive"].shape[0]),
                "negative": int(aspect_data[aspect_data["Sentiment"] == "negative"].shape[0]),
                "neutral": int(aspect_data[aspect_data["Sentiment"] == "neutral"].shape[0]),
                "total": int(aspect_data.shape[0])
            }
    # Otherwise check for Aspect column in main dataframe
    elif "Aspect" in df.columns:
        for aspect in df["Aspect"].dropna().unique():
            aspect_df = df[df["Aspect"] == aspect]
            aspect_distribution[aspect] = {
                "positive": int(aspect_df[aspect_df["Sentiment"] == "positive"].shape[0]),
                "negative": int(aspect_df[aspect_df["Sentiment"] == "negative"].shape[0]),
                "neutral": int(aspect_df[aspect_df["Sentiment"] == "neutral"].shape[0]),
                "total": int(aspect_df.shape[0])
            }
    
    return {
        "sentiment_distribution": sentiment_counts,
        "confidence_stats": confidence_stats,
        "polarity_distribution": polarity_dist,
        "aspect_distribution": aspect_distribution,
        "total_samples": len(df)
    } 