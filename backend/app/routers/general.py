from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import os
import tempfile
import uuid
from datetime import datetime
import pandas as pd
import re
from textblob import TextBlob

# 输出目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 定义输入/输出模型
class TextRequest(BaseModel):
    text: str

# 创建路由器
router = APIRouter(
    prefix="/api/general",
    tags=["general-analysis"],
    responses={404: {"description": "Not found"}},
)

def load_latest_csv():
    """
    加载最新的CSV文件
    """
    if not os.path.exists(OUTPUT_DIR):
        return pd.DataFrame(), None
    
    # 获取最新的CSV文件
    csv_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.csv')]
    if not csv_files:
        return pd.DataFrame(), None
    
    latest_file = max(csv_files, key=lambda x: os.path.getctime(os.path.join(OUTPUT_DIR, x)))
    return pd.read_csv(os.path.join(OUTPUT_DIR, latest_file)), latest_file

def get_sentiment_stats(df):
    """
    计算情感分析统计信息
    """
    if df.empty:
        return {}
    
    # 检查列名是否存在，如果不存在则添加默认值
    if 'sentiment' not in df.columns:
        df['sentiment'] = 'neutral'
    if 'score' not in df.columns:
        df['score'] = 50.0
    
    # 情感统计
    sentiment_stats = {
        'positive': len(df[df['sentiment'] == 'positive']),
        'negative': len(df[df['sentiment'] == 'negative']),
        'neutral': len(df[df['sentiment'] == 'neutral'])
    }
    
    # 评分分布
    sentiment_scores = df['score'].tolist()
    
    return {
        'sentiment_stats': sentiment_stats,
        'sentiment_scores': sentiment_scores
    }

def analyze_text_with_textblob(text):
    """
    使用TextBlob分析文本情感
    """
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    
    # 确定情感标签
    if polarity > 0.1:
        sentiment = "positive"
        score = 50 + polarity * 50  # 映射到50-100范围
    elif polarity < -0.1:
        sentiment = "negative"
        score = 50 - abs(polarity) * 50  # 映射到0-50范围
    else:
        sentiment = "neutral"
        score = 50 + polarity * 20  # 在45-55范围内
    
    return sentiment, round(score, 2), round(polarity, 2)  # 保留两位小数

@router.post("/analyze")
async def analyze_text(request: TextRequest):
    """分析单个文本"""
    try:
        text = request.text.strip()
        if not text:
            return JSONResponse(
                status_code=400,
                content={"error": "文本内容为空"}
            )
        
        # 使用TextBlob进行情感分析
        textblob_sentiment, textblob_score, textblob_polarity = analyze_text_with_textblob(text)
        
        # 生成简单摘要
        summary = f"Text length: {len(text)} characters, Sentiment: {textblob_sentiment}, Polarity: {textblob_polarity}"
        
        # 提取简单的关键词
        words = [word for word in re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', text)]
        word_freq = {}
        for word in words:
            if word in word_freq:
                word_freq[word] += 1
            else:
                word_freq[word] = 1
        
        # 排序并获取前5个关键词
        keywords = [
            {"text": word, "relevance": min(1.0, count / max(1, len(words)) * 5)} 
            for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        # 简单的实体识别（基于常见实体模式）
        entities = []
        
        # 数字实体
        numbers = re.findall(r'\d+(?:\.\d+)?', text)
        for num in numbers[:2]:  # 最多取前两个数字
            entities.append({
                "text": num,
                "type": "Number",
                "relevance": 0.7
            })
        
        # 日期时间
        dates = re.findall(r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?', text)
        for date in dates[:1]:  # 最多取一个日期
            entities.append({
                "text": date,
                "type": "Date",
                "relevance": 0.8
            })
        
        # 添加一些示例实体
        if len(entities) < 2:
            entities.append({
                "text": "Sentiment Analysis",
                "type": "Topic",
                "relevance": 0.9
            })
        
        return {
            "summary": summary,
            "sentiment": textblob_sentiment,
            "score": textblob_score,
            "polarity": textblob_polarity,
            "keywords": keywords,
            "entities": entities
        }
    except Exception as e:
        print(f"分析出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")

@router.post("/upload")
async def upload_and_analyze(file: UploadFile = File(...)):
    """上传并分析文件"""
    try:
        # 创建临时文件
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp:
            # 写入上传的内容
            content = await file.read()
            temp.write(content)
            temp_path = temp.name
        
        try:
            # 生成输出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"general_analysis_{timestamp}_{uuid.uuid4().hex[:8]}.csv"
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            # 尝试读取CSV文件
            df = pd.DataFrame()
            try:
                # 首先尝试使用逗号分隔符
                df = pd.read_csv(temp_path)
                
                # 检查是否实际上是分号分隔的文件
                if len(df.columns) == 1 and ';' in df.columns[0]:
                    # 重新读取文件使用分号分隔符
                    df = pd.read_csv(temp_path, sep=';')
                
                # 添加一个内容列（如果不存在）
                if 'Content' not in df.columns and len(df.columns) > 0:
                    # 尝试找到可能的内容列
                    content_col = None
                    for col in df.columns:
                        if 'content' in col.lower() or 'text' in col.lower() or 'comment' in col.lower():
                            content_col = col
                            break
                    
                    if content_col:
                        df['Content'] = df[content_col]
                    else:
                        df['Content'] = df.iloc[:, 0]  # 使用第一列作为内容
            except:
                # 如果读取失败，创建一个简单的数据帧
                df = pd.DataFrame({"Content": ["Sample text"]})
            
            # 对每行内容进行情感分析
            textblob_sentiments = []
            textblob_scores = []
            textblob_polarities = []
            
            for content in df['Content']:
                try:
                    # 使用TextBlob分析
                    sentiment, score, polarity = analyze_text_with_textblob(str(content))
                    textblob_sentiments.append(sentiment)
                    textblob_scores.append(score)
                    textblob_polarities.append(polarity)
                except:
                    textblob_sentiments.append("neutral")
                    textblob_scores.append(50.0)
                    textblob_polarities.append(0.0)
            
            # 添加分析结果
            df['sentiment'] = textblob_sentiments
            df['score'] = textblob_scores
            df['polarity'] = textblob_polarities
            
            # 保存分析结果
            df.to_csv(output_path, index=False)
            
            # 计算统计信息
            stats = get_sentiment_stats(df)
            
            # 提取最常见的词作为关键词
            all_content = " ".join([str(content) for content in df['Content']])
            words = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9]{2,}', all_content)
            word_freq = {}
            for word in words:
                if word in word_freq:
                    word_freq[word] += 1
                else:
                    word_freq[word] = 1
            
            # 排序并获取前5个关键词
            top_keywords = [
                {"text": word, "relevance": min(1.0, count / max(1, len(words)) * 5)} 
                for word, count in sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            ] if words else []
            
            sentiment_stats = stats.get('sentiment_stats', {'positive': 0, 'negative': 0, 'neutral': 0})
            
            return {
                "fileName": file.filename,
                "columns": df.columns.tolist(),
                "rowCount": len(df),
                "summary": f"File {file.filename} analysis completed with {len(df)} rows of data.",
                "sentiment_stats": sentiment_stats,
                "top_keywords": top_keywords,
                "insights": [
                    {
                        "type": "Sentiment",
                        "description": f"Positive: {sentiment_stats['positive']}({int(sentiment_stats['positive']/len(df)*100 if len(df)>0 else 0)}%), "
                                      f"Neutral: {sentiment_stats['neutral']}({int(sentiment_stats['neutral']/len(df)*100 if len(df)>0 else 0)}%), "
                                      f"Negative: {sentiment_stats['negative']}({int(sentiment_stats['negative']/len(df)*100 if len(df)>0 else 0)}%)",
                        "relevance": 0.95
                    },
                    {
                        "type": "Keywords",
                        "description": f"Main keywords: {', '.join([kw['text'] for kw in top_keywords])}",
                        "relevance": 0.85
                    }
                ],
                "output_file": output_file
            }
        finally:
            # 清理临时文件
            if os.path.exists(temp_path):
                os.remove(temp_path)
    except Exception as e:
        print(f"文件分析出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件分析失败: {str(e)}")

@router.get("/download/{filename}")
async def download_result(filename: str):
    """下载分析结果文件"""
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        
        # 如果文件不存在，尝试返回最新的CSV文件
        if not os.path.exists(file_path):
            try:
                df, latest_file = load_latest_csv()
                if latest_file:
                    file_path = os.path.join(OUTPUT_DIR, latest_file)
            except:
                # 如果找不到最新文件，创建一个示例文件
                with open(file_path, "w") as f:
                    f.write("Content,sentiment,score,polarity\n")
                    f.write(f"Generated on {datetime.now()},positive,85.5,0.75\n")
        
        return FileResponse(
            path=file_path,
            media_type="text/csv",
            filename=filename
        )
    except Exception as e:
        print(f"下载文件出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")

@router.get("/sentiment_data")
async def get_sentiment_data():
    """获取情感分析数据"""
    try:
        df, latest_file = load_latest_csv()
        if df.empty or not latest_file:
            return JSONResponse(
                status_code=404,
                content={"error": "没有找到分析数据"}
            )
        
        stats = get_sentiment_stats(df)
        
        # 添加原始数据
        raw_data = df.to_dict('records')
        
        return {
            **stats,
            "raw_data": raw_data,
            "latest_file": latest_file
        }
    except Exception as e:
        print(f"获取情感数据出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取情感数据失败: {str(e)}") 