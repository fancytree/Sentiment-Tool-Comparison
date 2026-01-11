import json
import os
import time
import pandas as pd
import csv
from openai import OpenAI
import httpx
from datetime import datetime
import logging
import sys
from typing import Dict, List, Optional, Union
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

# 加载环境变量
load_dotenv()

# OpenAI API 配置
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# 创建自定义的 HTTP 客户端，避免代理问题
http_client = httpx.Client(
    timeout=30.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
)

# 初始化 OpenAI 客户端
client = OpenAI(
    api_key=api_key,
    base_url="https://api.openai.com/v1",
    http_client=http_client
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# 创建路由器
app = APIRouter()

# 数据模型
class TextAnalysisRequest(BaseModel):
    text: str

class AspectAnalysis(BaseModel):
    aspect: str
    sentiment: str
    confidence: float
    reason: str

class AnalysisResult(BaseModel):
    aspect: str
    sentiment: str
    intensity: float
    score: float
    polarity: float
    brief_analysis: str
    aspects: Optional[List] = []

class TableAnalysisResult(BaseModel):
    total_rows: int
    analyzed_column: str
    results: List[AnalysisResult]
    summary: Dict[str, int]
    output_file: str
    original_texts: Optional[List[str]] = None
    aspect_details: Optional[List[Dict]] = None

class ChatRequest(BaseModel):
    message: str
    analysis_data: Optional[Dict] = None
    context: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    is_sentiment_related: bool

def clean_aspect_name(name: str) -> str:
    """
    清理和标准化方面名称
    """
    name = name.strip('- *')
    name = name.replace('Aspect Name:', '').strip()
    return name

def parse_aspects(aspect_section: str) -> List[AspectAnalysis]:
    """
    解析方面分析部分
    
    Args:
        aspect_section (str): 包含方面分析的文本
        
    Returns:
        List[AspectAnalysis]: 解析后的方面分析结果列表
    """
    aspects = []
    current_aspect = None
    current_sentiment = None
    current_intensity = None
    current_analysis = []
    
    if not aspect_section:
        return aspects
        
    lines = aspect_section.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith('- **') and line.endswith('**'):
            if current_aspect and current_sentiment and current_intensity is not None:
                aspects.append(AspectAnalysis(
                    aspect=current_aspect,
                    sentiment=current_sentiment,
                    confidence=abs(current_intensity) * 20,  # 将强度转换为百分比
                    reason=' '.join(current_analysis)
                ))
            
            current_aspect = line.strip('- **').rstrip('**').strip()
            current_sentiment = None
            current_intensity = None
            current_analysis = []
            
        elif current_aspect:
            if line.startswith('  - Sentiment:'):
                current_sentiment = line.split(':', 1)[1].strip()
            elif line.startswith('  - Intensity:'):
                try:
                    current_intensity = float(line.split(':', 1)[1].strip())
                except (ValueError, IndexError):
                    current_intensity = 0
            elif line.startswith('  - Analysis:'):
                analysis_text = line.split(':', 1)[1].strip()
                if analysis_text:
                    current_analysis.append(analysis_text)
            elif line and not line.startswith('  -'):
                current_analysis.append(line)
    
    if current_aspect and current_sentiment and current_intensity is not None:
        aspects.append(AspectAnalysis(
            aspect=current_aspect,
            sentiment=current_sentiment,
            confidence=abs(current_intensity) * 20,
            reason=' '.join(current_analysis)
        ))
                
    return aspects

def build_prompt(text: str) -> str:
    """
    构建情感分析提示模板
    """
    return f"""Please analyze the following game review and identify ALL aspects mentioned. Respond in the following format:

ASPECTS_ANALYSIS:
[For each aspect found, use this format:]

Aspect: [Choose from: Gameplay, Graphics, Sound, Story, Performance, UI/UX, Game Balance, Monetization, Community, Overall Experience]
Sentiment: [Positive/Neutral/Negative]
Intensity: [Number]
- Positive sentiment: 1.0 to 5.0 (1.0=slightly positive, 5.0=extremely positive)
- Negative sentiment: -1.0 to -5.0 (-1.0=slightly negative, -5.0=extremely negative)  
- Neutral sentiment: 0.0
Analysis: [Brief analysis for this specific aspect, 20 words or less]

[Repeat above format for each aspect found]

OVERALL_SUMMARY:
Brief Analysis: [Overall summary of the review in 30 words or less]

Important Guidelines:
1. Identify ALL aspects mentioned in the review (typically 1-5 aspects)
2. If no specific aspects are clearly mentioned, use "Overall Experience"
3. Each aspect should have its own sentiment and intensity
4. Intensity values must match sentiment (positive numbers for positive, negative for negative)
5. Use decimal format (e.g., 2.5, -3.0)
6. Keep individual aspect analysis under 20 words each

Review Content: "{text}"

Please respond in the above format."""

def analyze_sentiment(text: str, max_retries: int = 3) -> Dict:
    """
    分析单个文本的情感、方面和强度
    
    Args:
        text (str): 要分析的文本
        max_retries (int): 最大重试次数
    
    Returns:
        Dict: 包含分析结果的字典
    """
    try:
        for attempt in range(max_retries):
            try:
                prompt = build_prompt(text)
                
                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # 使用 gpt-4o-mini 模型
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional game review sentiment analysis assistant. Please strictly follow the specified format for output."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=2000,
                    stream=False
                )
                
                response_text = response.choices[0].message.content.strip()
                logging.info(f"\nAPI Response:\n{response_text}\n")
                
                # 解析多个aspects的分析结果
                aspects_list = []
                brief_analysis = ""
                
                lines = response_text.split('\n')
                current_aspect = None
                current_sentiment = None
                current_intensity = 0.0
                current_analysis = ""
                
                in_aspects_section = False
                in_summary_section = False
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                        
                    if "ASPECTS_ANALYSIS:" in line:
                        in_aspects_section = True
                        in_summary_section = False
                        continue
                    elif "OVERALL_SUMMARY:" in line:
                        # 保存当前aspect（如果有的话）
                        if current_aspect and current_sentiment:
                            aspects_list.append({
                                "aspect": current_aspect,
                                "sentiment": current_sentiment.lower(),
                                "intensity": current_intensity,
                                "analysis": current_analysis
                            })
                        in_aspects_section = False
                        in_summary_section = True
                        current_aspect = None
                        current_sentiment = None
                        current_intensity = 0.0
                        current_analysis = ""
                        continue
                    
                    if in_aspects_section:
                        if line.startswith("Aspect:"):
                            # 保存上一个aspect（如果有的话）
                            if current_aspect and current_sentiment:
                                aspects_list.append({
                                    "aspect": current_aspect,
                                    "sentiment": current_sentiment.lower(),
                                    "intensity": current_intensity,
                                    "analysis": current_analysis
                                })
                            # 开始新的aspect
                            current_aspect = line.split(':', 1)[1].strip()
                            current_sentiment = None
                            current_intensity = 0.0
                            current_analysis = ""
                        elif line.startswith("Sentiment:"):
                            current_sentiment = line.split(':', 1)[1].strip()
                        elif line.startswith("Intensity:"):
                            try:
                                current_intensity = float(line.split(':', 1)[1].strip())
                            except (ValueError, IndexError):
                                current_intensity = 0.0
                        elif line.startswith("Analysis:"):
                            current_analysis = line.split(':', 1)[1].strip()
                    
                    elif in_summary_section:
                        if line.startswith("Brief Analysis:"):
                            brief_analysis = line.split(':', 1)[1].strip()
                
                # 保存最后一个aspect（如果有的话）
                if current_aspect and current_sentiment:
                    aspects_list.append({
                        "aspect": current_aspect,
                        "sentiment": current_sentiment.lower(),
                        "intensity": current_intensity,
                        "analysis": current_analysis
                    })
                
                # 如果没有找到任何aspects，创建一个默认的
                if not aspects_list:
                    aspects_list.append({
                        "aspect": "Overall Experience",
                        "sentiment": "neutral",
                        "intensity": 0.0,
                        "analysis": brief_analysis or "No specific aspects detected."
                    })
                
                # 返回第一个aspect作为主要aspect（保持向后兼容）
                main_aspect_data = aspects_list[0]
                
                # 计算情感得分和极性
                sentiment_score = 0
                if main_aspect_data["sentiment"] == "positive":
                    sentiment_score = 100
                elif main_aspect_data["sentiment"] == "negative":
                    sentiment_score = -100
                
                return {
                    "aspect": main_aspect_data["aspect"],
                    "sentiment": main_aspect_data["sentiment"],
                    "intensity": main_aspect_data["intensity"],
                    "score": abs(sentiment_score),
                    "polarity": main_aspect_data["intensity"],
                    "brief_analysis": brief_analysis or main_aspect_data["analysis"],
                    "aspects": aspects_list  # 包含所有aspects的列表
                }
                
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                raise
                
    except Exception as e:
        logging.error(f"Analysis failed: {str(e)}")
        return {
            "aspect": "Overall Experience",
            "sentiment": "unknown",
            "intensity": 0.0,
            "score": 0,
            "polarity": 0,
            "brief_analysis": f"Analysis failed: {str(e)}",
            "aspects": [{
                "aspect": "Overall Experience",
                "sentiment": "unknown",
                "intensity": 0.0,
                "analysis": f"Analysis failed: {str(e)}"
            }]
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
async def analyze_file(file: UploadFile = File(...)) -> TableAnalysisResult:
    """
    分析上传的文件
    """
    try:
        logging.info(f"Received file upload request: {file.filename}")
        logging.info(f"Content type: {file.content_type}")
        
        # 检查文件类型
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file uploaded")
            
        if not file.filename.endswith(('.csv', '.xls', '.xlsx')):
            raise HTTPException(status_code=400, detail="Unsupported file format. Please upload .csv, .xls, or .xlsx files")
        
        ensure_output_dir()
        
        # 保存上传的文件
        file_path = f"output/{file.filename}"
        logging.info(f"Saving file to: {file_path}")
        
        try:
            content = await file.read()
            if not content:
                raise HTTPException(status_code=400, detail="Empty file uploaded")
                
            logging.info(f"File content size: {len(content)} bytes")
            
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            logging.info(f"File saved successfully")
        except Exception as e:
            logging.error(f"Failed to save file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        
        # 读取文件
        try:
            if file.filename.endswith('.csv'):
                logging.info("Reading CSV file")
                # 先尝试分号分隔
                df = pd.read_csv(file_path, sep=';', encoding='utf-8')
                # 如果只有一列，再尝试逗号分隔
                if len(df.columns) == 1:
                    df = pd.read_csv(file_path, sep=',', encoding='utf-8')
            elif file.filename.endswith(('.xls', '.xlsx')):
                logging.info("Reading Excel file")
                df = pd.read_excel(file_path)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format")
            
            logging.info(f"File read successfully, columns: {df.columns.tolist()}")
            logging.info(f"DataFrame shape: {df.shape}")
        except Exception as e:
            logging.error(f"Failed to read file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
        
        # 自动检测可分析的文本列
        text_column = None
        for col in df.columns:
            if col.lower() in ['text', 'content', 'comment']:
                text_column = col
                break
        
        if not text_column:
            logging.error("No text column found in file")
            raise HTTPException(status_code=400, detail="No text column found in file. Please ensure your file has a column named 'text', 'content', or 'comment'")
        
        logging.info(f"Using text column: {text_column}")
        
        # 移除空值
        df = df.dropna(subset=[text_column])
        logging.info(f"Removed empty values, remaining rows: {len(df)}")
        
        if len(df) == 0:
            raise HTTPException(status_code=400, detail="No valid text content found in the file")
        
        # 分析所有文本
        results = []
        original_texts = []
        
        for i, text in enumerate(df[text_column]):
            try:
                logging.info(f"Analyzing text {i+1}/{len(df)}")
                result = analyze_sentiment(text)
                results.append(result)
                original_texts.append(text)
            except Exception as e:
                logging.error(f"Failed to analyze text {i+1}: {str(e)}")
                # 即使分析失败，也要添加默认结果以保持长度一致
                results.append({
                    "aspect": "Overall Experience",
                    "sentiment": "unknown",
                    "intensity": 0.0,
                    "score": 0,
                    "polarity": 0,
                    "brief_analysis": f"Analysis failed: {str(e)}",
                    "aspects": [{
                        "aspect": "Overall Experience",
                        "sentiment": "unknown",
                        "intensity": 0.0,
                        "analysis": f"Analysis failed: {str(e)}"
                    }]
                })
                original_texts.append(text)
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to analyze any text in the file")
        
        # 计算统计信息 - 基于所有aspects
        sentiment_counts = {
            'positive': 0,
            'negative': 0,
            'neutral': 0
        }
        
        for result in results:
            # 统计所有aspects的情感分布
            aspects_list = result.get('aspects', [])
            if not aspects_list:
                # 后备：使用主要sentiment
                sentiment = result.get('sentiment', 'unknown')
                if sentiment in sentiment_counts:
                    sentiment_counts[sentiment] += 1
            else:
                # 统计每个aspect的sentiment
                for aspect_data in aspects_list:
                    sentiment = aspect_data.get('sentiment', 'unknown')
                    if sentiment in sentiment_counts:
                        sentiment_counts[sentiment] += 1
        
        logging.info(f"Sentiment counts: {sentiment_counts}")
        
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"llm_analysis_{timestamp}.csv"
        
        # 保存结果到 CSV - 新逻辑：为每个aspect生成一行
        try:
            output_path = os.path.join('output', output_file)
            
            logging.info(f"=== 保存CSV调试信息 ===")
            logging.info(f"分析结果数量: {len(results)}")
            logging.info(f"原始文本数量: {len(original_texts)}")
            
            # 创建新的DataFrame，为每个aspect生成一行
            csv_rows = []
            
            for i, (result, original_text) in enumerate(zip(results, original_texts)):
                review_id = i + 1
                
                # 获取所有aspects（如果有的话）
                aspects_list = result.get('aspects', [])
                if not aspects_list:
                    # 后备：使用主要aspect信息
                    aspects_list = [{
                        'aspect': result.get('aspect', 'Overall Experience'),
                        'sentiment': result.get('sentiment', 'unknown'),
                        'intensity': result.get('intensity', 0.0),
                        'analysis': result.get('brief_analysis', 'No analysis available')
                    }]
                
                # 为每个aspect创建一行
                for aspect_data in aspects_list:
                    row = {
                        'Review_ID': review_id,
                        'Content': original_text,
                        'aspect': aspect_data['aspect'],
                        'sentiment': aspect_data['sentiment'],
                        'intensity': aspect_data['intensity'],
                        'reason': aspect_data.get('analysis', result.get('brief_analysis', 'No analysis available'))
                    }
                    csv_rows.append(row)
            
            # 创建DataFrame
            results_df = pd.DataFrame(csv_rows)
            
            logging.info(f"生成的CSV行数: {len(csv_rows)}")
            logging.info(f"最终DataFrame列: {results_df.columns.tolist()}")
            logging.info(f"最终DataFrame形状: {results_df.shape}")
            if not results_df.empty:
                logging.info(f"第一行数据: {results_df.iloc[0].to_dict()}")
            
            # 定义要保留的列
            columns_to_keep = ['Review_ID', 'Content', 'aspect', 'sentiment', 'intensity', 'reason']
            existing_columns = [col for col in columns_to_keep if col in results_df.columns]
            
            logging.info(f"最终DataFrame列: {results_df.columns.tolist()}")
            logging.info(f"最终DataFrame形状: {results_df.shape}")
            logging.info(f"第一行数据: {results_df.iloc[0].to_dict()}")
            
            # 确保输出目录存在
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 手动构建CSV内容，确保所有字段都被引号包装
            csv_lines = []
            
            # 添加表头
            headers = [col for col in existing_columns]
            header_line = ';'.join(f'"{header}"' for header in headers)
            csv_lines.append(header_line)
            logging.info(f"CSV表头: {header_line}")
            
            # 添加数据行
            for i, (_, row) in enumerate(results_df.iterrows()):
                values = []
                for col in headers:
                    value = str(row[col]) if pd.notna(row[col]) else ''
                    # 转义引号并包装在引号中
                    escaped_value = value.replace('"', '""')
                    values.append(f'"{escaped_value}"')
                data_line = ';'.join(values)
                csv_lines.append(data_line)
                if i == 0:  # 只记录第一行作为示例
                    logging.info(f"CSV第一行数据: {data_line}")
            
            # 写入文件
            csv_content = '\n'.join(csv_lines)
            logging.info(f"CSV内容前100字符: {csv_content[:100]}")
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(csv_content)
            
            # 验证保存的文件
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                logging.info(f"文件已保存: {output_path}, 大小: {file_size} bytes")
                
                # 读取并验证保存的文件
                saved_df = pd.read_csv(output_path, sep=';', encoding='utf-8')
                logging.info(f"验证保存的文件 - 列: {saved_df.columns.tolist()}, 形状: {saved_df.shape}")
            else:
                raise Exception(f"文件保存失败: {output_path}")
                
        except Exception as e:
            logging.error(f"保存结果失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"保存结果失败: {str(e)}")
        
        # 计算总的aspect数量（CSV中的行数）
        total_aspects = sum(len(result.get('aspects', [result])) for result in results)
        
        # 构建aspect_details列表，用于前端显示
        aspect_details = []
        for result in results:
            aspects_list = result.get('aspects', [])
            if not aspects_list:
                # 后备：使用主要aspect信息
                aspects_list = [{
                    'aspect': result.get('aspect', 'Overall Experience'),
                    'sentiment': result.get('sentiment', 'unknown'),
                    'intensity': result.get('intensity', 0.0),
                    'analysis': result.get('brief_analysis', 'No analysis available')
                }]
            
            # 为每个aspect创建详情记录
            for aspect_data in aspects_list:
                aspect_detail = {
                    'aspect': aspect_data['aspect'],
                    'sentiment': aspect_data['sentiment'],
                    'intensity': aspect_data['intensity'],
                    'reason': aspect_data.get('analysis', result.get('brief_analysis', 'No analysis available'))
                }
                aspect_details.append(aspect_detail)
        
        logging.info(f"构建的aspect_details数量: {len(aspect_details)}")
        
        return TableAnalysisResult(
            total_rows=total_aspects,  # 现在表示aspects的总数，不是原始评论数
            analyzed_column=text_column,
            results=results,
            summary=sentiment_counts,
            output_file=output_file,
            original_texts=original_texts,
            aspect_details=aspect_details
        )
        
    except Exception as e:
        logging.error(f"File analysis failed: {str(e)}")
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

def detect_language(text: str) -> str:
    """
    检测文本语言（简单版本）
    """
    # 统计中文字符数量
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    # 统计英文单词数量（简单估算）
    english_words = len([word for word in text.split() if word.isalpha() and all(ord(char) < 128 for char in word)])
    
    # 如果中文字符占比较高，判断为中文
    if chinese_chars > len(text) * 0.1:
        return 'zh'
    # 如果有英文单词且中文字符很少，判断为英文
    elif english_words > 0 and chinese_chars < len(text) * 0.05:
        return 'en'
    # 默认根据中文字符数量决定
    else:
        return 'zh' if chinese_chars > 0 else 'en'

def is_sentiment_related_question(message: str) -> bool:
    """
    检查用户问题是否与情感分析相关
    """
    sentiment_keywords = [
        # 英文关键词 - 基础情感分析
        'sentiment', 'emotion', 'feeling', 'opinion', 'positive', 'negative', 'neutral',
        'review', 'feedback', 'analysis', 'score', 'rating', 'polarity', 'mood',
        'happy', 'sad', 'angry', 'satisfied', 'disappointed', 'recommend', 'like', 'dislike',
        'comment', 'comments', 'content', 'text', 'balance', 'game', 'aspect', 'aspects',
        'slice', 'slices', 'extract', 'list', 'show', 'display', 'find', 'identify',
        'good', 'bad', 'great', 'terrible', 'awesome', 'horrible', 'love', 'hate',
        'praise', 'criticism', 'complain', 'complaint', 'appreciate', 'frustration',
        
        # 英文关键词 - 扩展分析功能
        'summary', 'summarize', 'overview', 'breakdown', 'trend', 'pattern', 'distribution',
        'classify', 'categorize', 'segment', 'filter', 'sort', 'group', 'aggregate',
        'statistics', 'count', 'percentage', 'ratio', 'compare', 'comparison', 'contrast',
        'performance', 'quality', 'experience', 'satisfaction', 'dissatisfaction',
        'improvement', 'issue', 'problem', 'concern', 'strength', 'weakness',
        'feature', 'functionality', 'usability', 'design', 'interface', 'gameplay',
        'bug', 'glitch', 'error', 'lag', 'crash', 'stability', 'performance',
        'character', 'weapon', 'skill', 'ability', 'mechanic', 'system',
        'update', 'patch', 'version', 'change', 'modification', 'adjustment',
        'player', 'user', 'community', 'developer', 'team', 'support',
        
        # 中文关键词 - 基础情感分析
        '情感', '分析', '评价', '意见', '反馈', '积极', '消极', '中性', '评分',
        '负面', '正面', '评论', '内容', '文本', '切片', '提取', '列举', '显示',
        '查找', '识别', '方面', '平衡', '游戏', '好评', '差评', '抱怨', '赞美',
        '批评', '喜欢', '讨厌', '满意', '不满', '推荐', '建议', '体验', '感受',
        '态度', '观点', '看法', '倾向', '偏好', '情绪', '心情', '感情',
        
        # 中文关键词 - 扩展分析功能
        '总结', '概括', '汇总', '统计', '分布', '趋势', '模式', '分类', '归类',
        '筛选', '过滤', '排序', '分组', '聚合', '对比', '比较', '对照',
        '百分比', '比例', '数量', '计数', '性能', '质量', '体验', '满意度',
        '改进', '问题', '缺点', '优点', '强项', '弱点', '特性', '功能',
        '可用性', '设计', '界面', '玩法', '机制', '系统', '角色', '武器',
        '技能', '能力', '更新', '补丁', '版本', '修改', '调整', '玩家',
        '用户', '社区', '开发者', '团队', '支持', '稳定性', '流畅度',
        '卡顿', '崩溃', '错误', '故障', '漏洞', '帮助', '帮我', '给我',
        '告诉', '说明', '解释', '描述', '展示', '呈现', '提供', '获取',
        '收集', '整理', '梳理', '分析一下', '看看', '检查', '调研', '研究'
    ]
    
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in sentiment_keywords)

def generate_chat_response(message: str, analysis_data: Optional[Dict] = None, context: Optional[str] = None) -> Dict:
    """
    生成基于情感分析的对话回复，支持aspect总结和片段列举
    """
    try:
        # 检测用户输入的语言
        user_language = detect_language(message)
        
        # 检查是否为情感分析相关问题
        if not is_sentiment_related_question(message):
            # 根据用户语言返回对应的回复
            if user_language == 'zh':
                not_related_message = "抱歉，我只能提供与情感分析相关的见解和分析。请询问关于情感、观点、评论或情感分析相关的问题！"
            else:
                not_related_message = "Sorry, I can only provide insights and analysis related to sentiment analysis. Please ask questions about sentiments, opinions, reviews, or sentiment analysis!"
            
            return {
                "message": not_related_message,
                "is_sentiment_related": False
            }
        
        # 根据用户语言构建系统提示
        if user_language == 'zh':
            system_prompt = """你是一个专业的情感分析助手，具备以下能力：

1. **情感分析**: 分析文本的情感倾向、强度和极性
2. **方面分析**: 针对特定方面(aspect)进行深入分析
3. **内容总结**: 提供情感分析结果的总结和统计
4. **片段列举**: 根据要求列举相关的文本片段
5. **趋势分析**: 分析情感分布和变化趋势

**重要规则**:
- 只回答与情感分析、情绪、观点、评论相关的问题
- 如果用户询问无关话题，请礼貌地引导回到情感分析相关内容
- 基于提供的分析数据回答问题，如果没有数据则提供一般性指导
- 用中文回答用户的问题
- 回答要准确、有用，重点关注情感相关洞察

**特殊功能**:
- 当用户要求某个方面的总结时，提供该方面的情感分布、关键问题和改进建议
- 当用户要求列举片段时，从分析数据中提取相关的文本内容
- 支持按情感极性(正面/负面/中性)筛选内容
- 支持按特定关键词或主题筛选相关评论"""
        else:
            system_prompt = """You are a professional sentiment analysis assistant with the following capabilities:

1. **Sentiment Analysis**: Analyze text sentiment tendencies, intensity, and polarity
2. **Aspect Analysis**: Conduct in-depth analysis on specific aspects
3. **Content Summarization**: Provide summaries and statistics of sentiment analysis results
4. **Segment Listing**: List relevant text segments as requested
5. **Trend Analysis**: Analyze sentiment distribution and change trends

**Important Rules**:
- Only answer questions related to sentiment analysis, emotions, opinions, and reviews
- If users ask unrelated questions, politely guide them back to sentiment analysis content
- Base answers on provided analysis data, or provide general guidance if no data is available
- Answer user questions in English
- Answers should be accurate, useful, and focus on sentiment-related insights

**Special Features**:
- When users request summaries of specific aspects, provide sentiment distribution, key issues, and improvement suggestions for those aspects
- When users request segment listings, extract relevant text content from analysis data
- Support filtering content by sentiment polarity (positive/negative/neutral)
- Support filtering relevant comments by specific keywords or themes"""
        
        # 构建用户提示，包含分析数据
        user_prompt = message
        if analysis_data:
            # 根据用户语言构建数据描述
            if user_language == 'zh':
                data_description = f"""
基于以下情感分析结果回答用户问题：

**数据概览**:
- 总分析条目数: {analysis_data.get('total_rows', 'N/A')}
- 分析的列: {analysis_data.get('analyzed_column', 'N/A')}
- 情感分布: 
  * 正面: {analysis_data.get('summary', {}).get('positive', 0)}条
  * 负面: {analysis_data.get('summary', {}).get('negative', 0)}条  
  * 中性: {analysis_data.get('summary', {}).get('neutral', 0)}条

**数据详情**: 
如果用户询问具体内容、片段或案例，请基于这些统计数据提供分析和建议。
如果用户要求列举具体的负面/正面评论片段，请说明基于当前数据的情况，并提供该类别下可能包含的典型问题类型。

**用户问题**: {message}

请根据用户的具体需求，提供相应的分析、总结或建议。如果用户询问特定方面(如"Game Balance")，请重点分析该方面的情感分布和主要问题。"""
            else:
                data_description = f"""
Answer the user's question based on the following sentiment analysis results:

**Data Overview**:
- Total analyzed entries: {analysis_data.get('total_rows', 'N/A')}
- Analyzed column: {analysis_data.get('analyzed_column', 'N/A')}
- Sentiment distribution: 
  * Positive: {analysis_data.get('summary', {}).get('positive', 0)} entries
  * Negative: {analysis_data.get('summary', {}).get('negative', 0)} entries  
  * Neutral: {analysis_data.get('summary', {}).get('neutral', 0)} entries

**Data Details**: 
If the user asks about specific content, segments, or cases, please provide analysis and suggestions based on these statistics.
If the user requests specific negative/positive comment segments, please explain the situation based on current data and provide typical issue types that might be included in that category.

**User Question**: {message}

Please provide appropriate analysis, summaries, or suggestions based on the user's specific needs. If the user asks about specific aspects (like "Game Balance"), please focus on analyzing the sentiment distribution and main issues for that aspect."""
            user_prompt = data_description
        
        if context:
            user_prompt = f"**上下文**: {context}\n\n{user_prompt}"
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            max_tokens=800,  # 增加最大token数以支持更详细的回复
            stream=False
        )
        
        response_text = response.choices[0].message.content.strip()
        
        return {
            "message": response_text,
            "is_sentiment_related": True
        }
        
    except Exception as e:
        logging.error(f"Chat response generation failed: {str(e)}")
        # 检测用户语言以返回对应的错误信息
        user_language = detect_language(message)
        if user_language == 'zh':
            error_message = "抱歉，在处理您的问题时遇到了错误，请重试。如果您有情感分析相关的问题，我很乐意为您提供帮助。"
        else:
            error_message = "Sorry, an error occurred while processing your question. Please try again. If you have sentiment analysis related questions, I'd be happy to help."
        
        return {
            "message": error_message,
            "is_sentiment_related": True
        }

@app.post("/chat")
async def chat_with_sentiment_assistant(request: ChatRequest) -> ChatResponse:
    """
    与情感分析助手对话
    """
    try:
        result = generate_chat_response(
            message=request.message,
            analysis_data=request.analysis_data,
            context=request.context
        )
        
        return ChatResponse(
            message=result["message"],
            is_sentiment_related=result["is_sentiment_related"]
        )
    except Exception as e:
        logging.error(f"Chat API failed: {str(e)}")
        # 检测用户语言以返回对应的错误信息
        user_language = detect_language(request.message)
        if user_language == 'zh':
            error_detail = f"聊天API出错: {str(e)}"
        else:
            error_detail = f"Chat API error: {str(e)}"
        raise HTTPException(status_code=500, detail=error_detail)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 
