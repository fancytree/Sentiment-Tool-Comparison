import pandas as pd
import numpy as np
from textblob import TextBlob
import re
import json
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """
    清理文本，移除特殊字符和多余的空格
    """
    if not isinstance(text, str):
        return ""
    # 移除特殊字符，但保留基本的标点符号
    text = re.sub(r'[^\w\s.,!?;:\'"()-]', ' ', text)
    # 移除多余的空格和换行符
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def analyze_sentiment(text: str) -> tuple[str, float]:
    """
    使用 TextBlob 分析文本情感
    返回: (情感标签, 情感得分)
    """
    text = clean_text(text)
    if not text:
        return "neutral", 0.0
    
    analysis = TextBlob(text)
    score = analysis.sentiment.polarity
    
    if score > 0.1:
        return "positive", score
    elif score < -0.1:
        return "negative", score
    else:
        return "neutral", score

def get_text_column(df: pd.DataFrame) -> str:
    """
    获取文本列名
    支持的列名: 'text', 'Text', 'content', 'Content'
    """
    possible_columns = ['text', 'Text', 'content', 'Content']
    for col in possible_columns:
        if col in df.columns:
            return col
    return None

def convert_to_serializable(obj):
    """
    将NumPy数据类型转换为Python原生类型
    """
    if isinstance(obj, (np.int64, np.int32)):
        return int(obj)
    elif isinstance(obj, (np.float64, np.float32)):
        return float(obj)
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj

def analyze_file(file_path: str):
    """
    分析文件并返回结果
    """
    try:
        # 读取文件内容
        df = pd.read_csv(
            file_path,
            sep=';',
            encoding='utf-8',
            quoting=1,
            engine='python',
            on_bad_lines='skip'
        )
        logger.info(f"Successfully read CSV file with {len(df)} rows and columns: {df.columns.tolist()}")
        
        # 获取文本列名
        text_column = get_text_column(df)
        logger.info(f"Found text column: {text_column}")
        
        # 进行情感分析
        if text_column:
            # 清理文本
            df[text_column] = df[text_column].apply(clean_text)
            logger.info(f"Cleaned text in column {text_column}")
            
            # 对每个文本进行情感分析
            df['textblob_sentiment'], df['textblob_score'] = zip(*df[text_column].apply(analyze_sentiment))
            logger.info("Completed sentiment analysis")
            
            # 计算情感统计
            sentiment_stats = {
                'positive': int(len(df[df['textblob_sentiment'] == 'positive'])),
                'negative': int(len(df[df['textblob_sentiment'] == 'negative'])),
                'neutral': int(len(df[df['textblob_sentiment'] == 'neutral']))
            }
            logger.info(f"Sentiment stats: {sentiment_stats}")
            
            # 获取情感得分列表
            sentiment_scores = [float(score) for score in df['textblob_score'].tolist()]
            
            # 添加文本列信息
            text_column_info = {
                "column_name": text_column,
                "total_texts": int(len(df)),
                "non_empty_texts": int(df[text_column].notna().sum())
            }
        else:
            sentiment_stats = {}
            sentiment_scores = []
            text_column_info = None
            logger.warning("No text column found for sentiment analysis")
        
        # 进行基本分析
        analysis_results = {
            "file_info": {
                "filename": file_path,
                "rows": int(len(df)),
                "columns": int(len(df.columns)),
                "column_names": df.columns.tolist()
            },
            "basic_stats": {
                "numeric_columns": {},
                "categorical_columns": {}
            },
            "sentiment_analysis": {
                "stats": sentiment_stats,
                "scores": sentiment_scores,
                "text_column_info": text_column_info
            }
        }
        
        # 分析数值列
        for col in df.select_dtypes(include=['int64', 'float64']).columns:
            analysis_results["basic_stats"]["numeric_columns"][col] = {
                "mean": float(df[col].mean()),
                "median": float(df[col].median()),
                "std": float(df[col].std()),
                "min": float(df[col].min()),
                "max": float(df[col].max())
            }
        
        # 分析分类列
        for col in df.select_dtypes(include=['object']).columns:
            value_counts = df[col].value_counts().to_dict()
            # 确保所有值都是可序列化的
            value_counts = {str(k): int(v) for k, v in value_counts.items()}
            analysis_results["basic_stats"]["categorical_columns"][col] = {
                "unique_values": int(len(value_counts)),
                "value_counts": value_counts
            }
        
        # 确保所有数据都是可序列化的
        analysis_results = convert_to_serializable(analysis_results)
        
        # 保存分析结果
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_filename = f"test_analysis_{timestamp}.json"
        
        with open(result_filename, "w", encoding="utf-8") as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
        
        # 保存带有情感分析结果的CSV文件
        csv_filename = f"test_sentiment_{timestamp}.csv"
        df.to_csv(csv_filename, index=False)
        
        logger.info(f"Analysis completed successfully. Results saved to {result_filename} and {csv_filename}")
        return analysis_results
        
    except Exception as e:
        logger.error(f"Error analyzing file: {str(e)}")
        raise

if __name__ == "__main__":
    # 测试文件分析
    file_path = "../test_Sentiment Analysis.csv"
    results = analyze_file(file_path)
    print("\nAnalysis Results:")
    print(json.dumps(results, indent=2, ensure_ascii=False)) 