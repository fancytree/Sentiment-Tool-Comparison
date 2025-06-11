from textblob import TextBlob
import pandas as pd
import os
import json
from datetime import datetime
import uuid
import re
import string
from collections import Counter

# 定义输出目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 定义停用词列表（简化版，不再依赖nltk）
STOPWORDS = set([
    'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', "you're", "you've", "you'll", 
    "you'd", 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', "she's", 
    'her', 'hers', 'herself', 'it', "it's", 'its', 'itself', 'they', 'them', 'their', 'theirs', 
    'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', "that'll", 'these', 'those', 'am', 
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 
    'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 
    'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 
    'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 
    'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 
    'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 
    'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', "don't", 
    'should', "should've", 'now', 'd', 'll', 'm', 'o', 're', 've', 'y', 'ain', 'aren', "aren't", 
    'couldn', "couldn't", 'didn', "didn't", 'doesn', "doesn't", 'hadn', "hadn't", 'hasn', "hasn't", 
    'haven', "haven't", 'isn', "isn't", 'ma', 'mightn', "mightn't", 'mustn', "mustn't", 'needn', 
    "needn't", 'shan', "shan't", 'shouldn', "shouldn't", 'wasn', "wasn't", 'weren', "weren't", 'won', 
    "won't", 'wouldn', "wouldn't"
])

class GeneralService:
    """通用文本分析服务类"""
    
    def __init__(self):
        """初始化服务"""
        self.stop_words = STOPWORDS
        print("通用分析服务初始化完成")
    
    def analyze_text(self, text: str) -> dict:
        """
        对文本进行通用分析，包括情感分析、关键词提取、实体识别等
        
        参数:
            text (str): 要分析的文本
            
        返回:
            dict: 分析结果
        """
        if not text or not text.strip():
            return {
                "error": "文本内容为空"
            }
        
        try:
            # 清理文本
            cleaned_text = self._clean_text(text)
            
            # 使用TextBlob进行情感分析
            blob = TextBlob(cleaned_text)
            polarity = blob.sentiment.polarity
            subjectivity = blob.sentiment.subjectivity
            
            # 根据polarity确定情感标签
            if polarity > 0.2:
                sentiment = "positive"
                score = 50 + polarity * 50
            elif polarity < -0.2:
                sentiment = "negative"
                score = 50 + abs(polarity) * 50
            else:
                sentiment = "neutral"
                score = 50 + abs(polarity) * 20
            
            # 提取关键词
            keywords = self._extract_keywords(cleaned_text)
            
            # 提取实体
            entities = self._extract_entities(cleaned_text)
            
            # 生成摘要
            summary = self._generate_summary(cleaned_text, polarity, sentiment)
            
            return {
                "summary": summary,
                "sentiment": {
                    "label": sentiment,
                    "score": round(score, 2),
                    "polarity": round(polarity, 2),
                    "subjectivity": round(subjectivity, 2)
                },
                "keywords": keywords,
                "entities": entities
            }
        except Exception as e:
            print(f"文本分析错误: {str(e)}")
            return {
                "error": f"分析失败: {str(e)}"
            }
    
    def analyze_file(self, file_path: str, text_column: str = None) -> dict:
        """
        分析表格文件中的文本内容
        
        参数:
            file_path (str): 文件路径
            text_column (str): 包含文本内容的列名，如果为None则自动检测
            
        返回:
            dict: 分析结果
        """
        try:
            # 读取文件
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.csv':
                # 尝试自动检测分隔符
                with open(file_path, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    
                # 检查是否使用分号作为分隔符
                if ';' in first_line and first_line.count(';') > first_line.count(','):
                    df = pd.read_csv(file_path, sep=';')
                else:
                    df = pd.read_csv(file_path)
            elif file_ext in ['.xls', '.xlsx']:
                df = pd.read_excel(file_path)
            elif file_ext == '.tsv':
                df = pd.read_csv(file_path, sep='\t')
            else:
                return {"error": f"不支持的文件类型: {file_ext}"}
            
            # 检查数据是否为空
            if df.empty:
                return {"error": "文件不包含任何数据"}
            
            # 识别文本列
            if not text_column or text_column not in df.columns:
                text_column = self._detect_text_column(df)
                if not text_column:
                    return {"error": "无法识别包含文本内容的列"}
            
            # 清理数据，删除空行
            df = df.dropna(subset=[text_column])
            df = df[df[text_column].astype(str).str.strip() != '']
            
            if df.empty:
                return {"error": "清理数据后没有可用的文本内容"}
            
            # 收集文本数据
            texts = df[text_column].astype(str).tolist()
            
            # 批量分析
            results = []
            all_sentiments = {"positive": 0, "neutral": 0, "negative": 0}
            all_keywords = Counter()
            all_entities = {}
            
            for text in texts:
                result = self.analyze_text(text)
                if "error" not in result:
                    results.append(result)
                    
                    # 统计情感
                    all_sentiments[result["sentiment"]["label"]] += 1
                    
                    # 统计关键词
                    for keyword in result["keywords"]:
                        all_keywords[keyword["text"]] += 1
                    
                    # 统计实体
                    for entity in result["entities"]:
                        entity_type = entity["type"]
                        if entity_type not in all_entities:
                            all_entities[entity_type] = []
                        all_entities[entity_type].append(entity["text"])
            
            # 生成输出文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"general_analysis_{timestamp}_{uuid.uuid4().hex[:8]}.csv"
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            # 创建结果DataFrame
            result_df = df.copy()
            result_df["Sentiment"] = [r["sentiment"]["label"] for r in results]
            result_df["Score"] = [r["sentiment"]["score"] for r in results]
            result_df["Polarity"] = [r["sentiment"]["polarity"] for r in results]
            
            # 保存分析结果
            result_df.to_csv(output_path, index=False)
            
            # 提取最常见的关键词（前10个）
            top_keywords = [{"text": k, "relevance": v / len(results)} 
                           for k, v in all_keywords.most_common(10)]
            
            # 生成总体摘要
            total = len(results)
            summary = f"分析了{total}行数据，其中积极情感{all_sentiments['positive']}条，中性情感{all_sentiments['neutral']}条，消极情感{all_sentiments['negative']}条。"
            
            # 生成文件分析结果
            insights = [
                {
                    "type": "情感分布",
                    "description": f"积极: {all_sentiments['positive']}({round(all_sentiments['positive']/total*100)}%), "
                                  f"中性: {all_sentiments['neutral']}({round(all_sentiments['neutral']/total*100)}%), "
                                  f"消极: {all_sentiments['negative']}({round(all_sentiments['negative']/total*100)}%)",
                    "relevance": 0.95
                }
            ]
            
            # 添加关键词见解
            if top_keywords:
                keyword_desc = ", ".join([k["text"] for k in top_keywords[:5]])
                insights.append({
                    "type": "关键词分布",
                    "description": f"主要关键词: {keyword_desc}",
                    "relevance": 0.85
                })
            
            # 添加实体见解
            for entity_type, entities in all_entities.items():
                if entities:
                    # 计算每个实体的出现次数
                    entity_counter = Counter(entities)
                    # 获取出现频率最高的5个实体
                    top_entities = entity_counter.most_common(5)
                    
                    if top_entities:
                        entity_desc = ", ".join([e[0] for e in top_entities])
                        insights.append({
                            "type": f"{entity_type}实体分布",
                            "description": f"主要{entity_type}实体: {entity_desc}",
                            "relevance": 0.80
                        })
            
            return {
                "fileName": os.path.basename(file_path),
                "columns": list(df.columns),
                "rowCount": len(df),
                "summary": summary,
                "sentiment_stats": all_sentiments,
                "top_keywords": top_keywords,
                "insights": insights,
                "output_file": output_file
            }
        except Exception as e:
            print(f"文件分析错误: {str(e)}")
            return {
                "error": f"文件分析失败: {str(e)}"
            }
    
    def _clean_text(self, text: str) -> str:
        """
        清理文本，移除特殊字符、多余空格等
        """
        # 移除特殊标记
        text = re.sub(r'###\s*(USER|ASSISTANT):\s*', '', text)
        # 替换换行符为空格
        text = re.sub(r'\n+', ' ', text)
        # 移除多余空格
        text = ' '.join(text.split())
        return text
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> list:
        """
        从文本中提取关键词（简化版，不依赖nltk）
        """
        # 简单分词: 转为小写，用空格和标点分割
        text = text.lower()
        # 移除标点符号
        for char in string.punctuation:
            text = text.replace(char, ' ')
        
        # 分词
        words = text.split()
        
        # 过滤掉停用词和短词
        words = [word for word in words 
                if word not in self.stop_words 
                and len(word) > 2
                and not word.isdigit()]
        
        # 统计词频
        word_counts = Counter(words)
        
        # 提取最常见的词作为关键词
        keywords = []
        for word, count in word_counts.most_common(max_keywords * 2):
            # 跳过数字
            if not word.isdigit():
                relevance = min(1.0, count / len(words) * 10)  # 简单的相关性计算
                keywords.append({
                    "text": word,
                    "relevance": round(relevance, 2)
                })
                
                if len(keywords) >= max_keywords:
                    break
        
        return keywords
    
    def _extract_entities(self, text: str, max_entities: int = 5) -> list:
        """
        从文本中提取实体（简化版，基于规则）
        """
        entities = []
        
        # 使用TextBlob的名词短语提取功能
        blob = TextBlob(text)
        noun_phrases = blob.noun_phrases
        
        # 提取数字作为潜在的数量实体
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        
        # 提取日期模式
        dates = re.findall(r'\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b', text)
        dates.extend(re.findall(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b', text))
        
        # 添加名词短语作为概念实体
        for phrase in noun_phrases[:max_entities]:
            if len(phrase.split()) > 1:  # 只选择多词短语
                entities.append({
                    "text": phrase,
                    "type": "概念",
                    "relevance": 0.8
                })
        
        # 添加数字作为数量实体
        for number in numbers[:3]:
            entities.append({
                "text": number,
                "type": "数量",
                "relevance": 0.7
            })
        
        # 添加日期
        for date in dates[:2]:
            entities.append({
                "text": date,
                "type": "日期",
                "relevance": 0.9
            })
        
        return entities[:max_entities]
    
    def _generate_summary(self, text: str, polarity: float, sentiment: str) -> str:
        """
        生成文本摘要
        """
        # 获取文本长度
        text_length = len(text)
        
        # 简单的摘要生成逻辑
        if text_length < 100:
            summary = f"这是一段短文本，包含{text_length}个字符。"
        else:
            # 获取第一个句子作为摘要基础
            sentences = text.split('.')
            first_sentence = sentences[0] if sentences else text[:100]
            
            # 如果第一个句子太短，添加更多内容
            if len(first_sentence) < 50 and len(sentences) > 1:
                first_sentence += '. ' + sentences[1]
            
            summary = f"文本包含{text_length}个字符，约{len(text.split())}个单词。"
        
        # 添加情感分析结果
        sentiment_desc = "积极" if sentiment == "positive" else "消极" if sentiment == "negative" else "中性"
        polarity_strength = abs(polarity)
        
        if polarity_strength > 0.7:
            intensity = "非常"
        elif polarity_strength > 0.4:
            intensity = "相当"
        elif polarity_strength > 0.2:
            intensity = "轻微"
        else:
            intensity = ""
        
        if sentiment != "neutral":
            summary += f" 文本表达了{intensity}{sentiment_desc}的情感。"
        else:
            summary += f" 文本情感倾向中性。"
        
        return summary
    
    def _detect_text_column(self, df: pd.DataFrame) -> str:
        """
        自动检测表格中可能的文本列
        """
        # 可能的文本列名称
        potential_text_cols = ["text", "content", "comment", "review", "message", "description"]
        
        # 首先检查列名是否匹配
        for col in potential_text_cols:
            matching_cols = [c for c in df.columns if col.lower() in c.lower()]
            if matching_cols:
                return matching_cols[0]
        
        # 其次，查找包含较长文本的列
        for col in df.columns:
            if df[col].dtype == 'object':  # 字符串类型
                # 计算平均文本长度
                avg_len = df[col].astype(str).str.len().mean()
                if avg_len > 20:  # 假设文本列的平均长度大于20
                    return col
        
        # 如果找不到，返回第一个字符串列
        for col in df.columns:
            if df[col].dtype == 'object':
                return col
        
        # 如果还是找不到，返回第一列
        if len(df.columns) > 0:
            return df.columns[0]
        
        return None

# 创建单例实例
general_service = GeneralService() 