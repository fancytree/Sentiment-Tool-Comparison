from textblob import TextBlob
import pandas as pd
import os
import json
from datetime import datetime
import uuid

# 定义输出目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class SentimentService:
    def __init__(self):
        # 初始化情感分析服务
        pass
        
    def analyze_text(self, text):
        # 使用TextBlob进行情感分析
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        
        # 确定情感标签
        if polarity > 0.2:
            sentiment = "positive"
        elif polarity < -0.2:
            sentiment = "negative"
        else:
            sentiment = "neutral"
            
        # 计算置信度分数 (0-100)
        score = abs(polarity) * 100
        if sentiment == "neutral":
            score = 50 + score / 2
        
        return {
            "sentiment": sentiment,
            "score": round(score),
            "polarity": round(polarity, 2)
        }
    
    def analyze_file(self, file_path, text_column=None):
        try:
            # 确定文件类型并读取
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                df = pd.read_csv(file_path)
            elif file_ext in ['.xls', '.xlsx']:
                df = pd.read_excel(file_path)
            else:
                raise ValueError("Unsupported file format")
                
            # 如果未指定文本列，尝试自动检测
            if text_column is None:
                potential_text_cols = ["text", "content", "comment", "review", "message"]
                for col in potential_text_cols:
                    if col in df.columns:
                        text_column = col
                        break
                        
                # 如果还是找不到，使用第一列
                if text_column is None and len(df.columns) > 0:
                    text_column = df.columns[0]
            
            if text_column not in df.columns:
                raise ValueError(f"Column '{text_column}' not found in the file")
                
            # 分析每一行
            results = []
            for _, row in df.iterrows():
                text = str(row[text_column])
                if text and text.strip():
                    result = self.analyze_text(text)
                    results.append(result)
                    
            # 计算摘要
            summary = {
                "positive": sum(1 for r in results if r["sentiment"] == "positive"),
                "negative": sum(1 for r in results if r["sentiment"] == "negative"),
                "neutral": sum(1 for r in results if r["sentiment"] == "neutral"),
                "total": len(results)
            }
            
            # 创建输出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"sentiment_analysis_{timestamp}_{uuid.uuid4().hex[:8]}.csv"
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            # 将分析结果合并到原始数据中
            df_results = pd.DataFrame(results)
            df_with_results = pd.concat([df, df_results], axis=1)
            df_with_results.to_csv(output_path, index=False)
            
            return {
                "total_rows": len(df),
                "analyzed_column": text_column,
                "results": results,
                "summary": summary,
                "output_file": output_file
            }
            
        except Exception as e:
            print(f"Error in analyze_file: {str(e)}")
            raise

# 创建服务实例
sentiment_service = SentimentService() 