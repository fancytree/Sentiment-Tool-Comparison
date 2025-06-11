import pandas as pd
import sys
import os

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from llm_sentiment import analyze_sentiment

def test_and_save_first_row():
    # 读取测试文件
    df = pd.read_csv('test_Sentiment Analysis.csv', sep=';', encoding='utf-8')
    # 获取第一条数据
    first_row = df.iloc[[0]].reset_index(drop=True)
    content_col = None
    for col in first_row.columns:
        if col.lower() in ['text', 'content', 'comment']:
            content_col = col
            break
    if not content_col:
        raise ValueError('No analyzable text column found!')
    # 分析
    result = analyze_sentiment(first_row.loc[0, content_col])
    # 添加分析结果列
    first_row['sentiment'] = result['sentiment']
    first_row['强度'] = result['polarity']
    first_row['reason'] = result['brief_analysis']
    # 保存
    output_path = 'test_sentiment_result.csv'
    first_row.to_csv(output_path, index=False, sep=';', encoding='utf-8')
    print(f'Result saved to {output_path}')
    print(first_row.head())

if __name__ == "__main__":
    test_and_save_first_row() 