from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import pandas as pd
import os
import logging
from typing import List, Dict, Any
import json
from datetime import datetime
from textblob import TextBlob
import re
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = APIRouter()

# 确保输出目录存在
os.makedirs("output", exist_ok=True)

def clean_text(text: str) -> str:
    """
    清理文本，移除特殊字符和多余空格
    """
    if not isinstance(text, str):
        return ""
    # 保留基本标点符号，移除其他特殊字符
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)
    # 移除多余空格
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def analyze_sentiment(text: str) -> tuple:
    """
    分析文本情感
    返回: (情感标签, 情感分数)
    """
    if not isinstance(text, str) or not text.strip():
        return "neutral", 0.0
    
    text = clean_text(text)
    if not text:
        return "neutral", 0.0
    
    try:
        analysis = TextBlob(text)
        score = analysis.sentiment.polarity
        
        # 将分数映射到0-1范围
        normalized_score = (score + 1) / 2
        
        if score > 0.1:
            return "positive", normalized_score
        elif score < -0.1:
            return "negative", normalized_score
        else:
            return "neutral", normalized_score
    except Exception as e:
        logger.error(f"情感分析错误: {str(e)}")
        return "neutral", 0.0

def get_text_column(df: pd.DataFrame) -> str:
    """
    获取文本列名
    """
    text_columns = ['text', 'Text', 'content', 'Content']
    for col in text_columns:
        if col in df.columns:
            return col
    return None

def convert_to_serializable(obj):
    """
    将NumPy类型转换为Python原生类型
    """
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj

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
        logger.info(f"Successfully read CSV file with {len(df)} rows and columns: {df.columns.tolist()}")
        return df
    except Exception as e:
        logger.error(f"Error reading CSV with semicolon separator: {str(e)}")
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
            logger.info(f"Successfully read CSV file with comma separator: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Error reading CSV with comma separator: {str(e)}")
            # 最后尝试自动检测分隔符
            try:
                df = pd.read_csv(
                    file_path,
                    encoding='utf-8',
                    engine='python',
                    on_bad_lines='skip'
                )
                logger.info(f"Successfully read CSV file with auto-detected separator: {len(df)} rows")
                return df
            except Exception as e:
                logger.error(f"Error reading CSV with auto-detected separator: {str(e)}")
                raise

def analyze_file(file_path: str) -> dict:
    """
    分析文件并返回结果
    """
    try:
        # 读取CSV文件
        df = read_csv_file(file_path)
        
        # 获取文本列
        text_column = get_text_column(df)
        if not text_column:
            raise ValueError("No text column found in the file")
        
        logger.info(f"Found text column: {text_column}")
        
        # 保存原始文本
        original_texts = df[text_column].tolist()
        
        # 清理文本
        df[text_column] = df[text_column].apply(clean_text)
        logger.info(f"Cleaned text in column {text_column}")
        
        # 情感分析
        sentiment_results = df[text_column].apply(analyze_sentiment)
        df['textblob_sentiment'] = sentiment_results.apply(lambda x: x[0])
        df['textblob_score'] = sentiment_results.apply(lambda x: float(x[1]))  # 确保是Python float类型
        logger.info("Completed sentiment analysis")
        
        # 统计情感分布
        sentiment_stats = {k: int(v) for k, v in df['textblob_sentiment'].value_counts().to_dict().items()}  # 转换为Python int类型
        logger.info(f"Sentiment stats: {sentiment_stats}")
        
        # 准备分析结果
        analysis_results = {
            "file_info": {
                "filename": os.path.basename(file_path),
                "rows": int(len(df)),  # 转换为Python int类型
                "columns": int(len(df.columns)),  # 转换为Python int类型
                "column_names": df.columns.tolist()
            },
            "basic_stats": {
                "numeric_columns": {},
                "categorical_columns": {}
            },
            "sentiment_analysis": {
                "stats": sentiment_stats,
                "scores": [float(score) for score in df['textblob_score'].tolist()],  # 确保所有分数都是Python float类型
                "text_column_info": {
                    "column_name": text_column,
                    "total_texts": int(len(df)),  # 转换为Python int类型
                    "non_empty_texts": int(df[text_column].str.strip().astype(bool).sum())  # 转换为Python int类型
                }
            },
            "textblob_sentiment": df['textblob_sentiment'].tolist(),
            "textblob_score": [float(score) for score in df['textblob_score'].tolist()],  # 确保所有分数都是Python float类型
            "original_texts": original_texts
        }
        
        # 添加数值列统计
        for col in df.select_dtypes(include=[np.number]).columns:
            analysis_results["basic_stats"]["numeric_columns"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            }
        
        # 添加分类列统计
        for col in df.select_dtypes(include=['object']).columns:
            value_counts = {k: int(v) for k, v in df[col].value_counts().to_dict().items()}  # 转换为Python int类型
            analysis_results["basic_stats"]["categorical_columns"][col] = {
                "unique_values": int(len(value_counts)),  # 转换为Python int类型
                "value_counts": value_counts
            }
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存分析结果
        results_file = os.path.join("output", f"analysis_results_{timestamp}.json")
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
        
        # 保存情感分析结果到CSV
        sentiment_file = os.path.join("output", f"sentiment_analysis_{timestamp}.csv")
        df.to_csv(sentiment_file, index=False, encoding='utf-8')
        
        logger.info(f"Analysis completed successfully. Results saved to {results_file} and {sentiment_file}")
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        raise

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
        
        # 读取原始文件
        df = read_csv_file(file_path)
        
        # 添加分析结果列
        df['Sentiment'] = analysis_results['textblob_sentiment']
        df['Confidence'] = [f"{score*100:.1f}%" for score in analysis_results['textblob_score']]
        
        # 保存分析结果到CSV（保留原始数据）
        sentiment_file = os.path.join("output", f"sentiment_analysis_{timestamp}.csv")
        df.to_csv(sentiment_file, index=False, encoding='utf-8')
        
        # 准备返回的数据
        response_data = {
            "fileName": file.filename,
            "columns": analysis_results["file_info"]["column_names"],
            "rowCount": analysis_results["file_info"]["rows"],
            "summary": f"File {file.filename} analysis completed with {analysis_results['file_info']['rows']} rows of data.",
            "sentiment_stats": analysis_results["sentiment_analysis"]["stats"],
            "insights": [
                {
                    "type": "Sentiment",
                    "description": f"Positive: {analysis_results['sentiment_analysis']['stats'].get('positive', 0)}({int(analysis_results['sentiment_analysis']['stats'].get('positive', 0)/analysis_results['file_info']['rows']*100 if analysis_results['file_info']['rows']>0 else 0)}%), "
                                f"Neutral: {analysis_results['sentiment_analysis']['stats'].get('neutral', 0)}({int(analysis_results['sentiment_analysis']['stats'].get('neutral', 0)/analysis_results['file_info']['rows']*100 if analysis_results['file_info']['rows']>0 else 0)}%), "
                                f"Negative: {analysis_results['sentiment_analysis']['stats'].get('negative', 0)}({int(analysis_results['sentiment_analysis']['stats'].get('negative', 0)/analysis_results['file_info']['rows']*100 if analysis_results['file_info']['rows']>0 else 0)}%)",
                    "relevance": 0.95
                }
            ],
            "output_file": os.path.basename(sentiment_file),  # 使用新生成的CSV文件名
            "csvData": []  # 初始化空数组
        }
        
        # 添加CSV数据
        if 'textblob_sentiment' in analysis_results and 'textblob_score' in analysis_results:
            for i in range(len(analysis_results['textblob_sentiment'])):
                response_data["csvData"].append({
                    "Content": analysis_results['original_texts'][i] if i < len(analysis_results['original_texts']) else "",
                    "sentiment": analysis_results['textblob_sentiment'][i],
                    "score": float(analysis_results['textblob_score'][i]),
                    "polarity": float(analysis_results['textblob_score'][i])  # 使用score作为polarity
                })
        
        logger.info(f"Prepared response data with {len(response_data['csvData'])} rows")
        return response_data
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download/{filename}")
async def download_file(filename: str):
    """
    下载分析结果文件
    """
    file_path = f"output/{filename}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path) 