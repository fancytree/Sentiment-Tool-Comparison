import sys
import os
import pandas as pd

# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from llm_sentiment import analyze_sentiment

def debug_upload():
    print("=== 调试文件上传逻辑 ===")
    
    # 读取测试文件
    file_path = 'test_Sentiment Analysis.csv'
    print(f"读取文件: {file_path}")
    
    # 先尝试分号分隔
    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
    # 如果只有一列，再尝试逗号分隔
    if len(df.columns) == 1:
        df = pd.read_csv(file_path, sep=',', encoding='utf-8')
    
    print(f"原始DataFrame列: {df.columns.tolist()}")
    print(f"原始DataFrame形状: {df.shape}")
    print(f"原始DataFrame前2行:\n{df.head(2)}")
    
    # 自动检测可分析的文本列
    text_column = None
    for col in df.columns:
        if col.lower() in ['text', 'content', 'comment']:
            text_column = col
            break
    
    print(f"检测到的文本列: {text_column}")
    
    # 移除空值
    df = df.dropna(subset=[text_column])
    print(f"移除空值后的形状: {df.shape}")
    
    # 只分析第一条数据进行测试
    first_text = df[text_column].iloc[0]
    print(f"第一条文本内容: {first_text[:100]}...")
    
    # 分析第一条
    result = analyze_sentiment(first_text)
    print(f"分析结果: {result}")
    
    # 模拟保存逻辑
    results_df = df.reset_index(drop=True).copy()
    print(f"保存前DataFrame列: {results_df.columns.tolist()}")
    print(f"保存前DataFrame形状: {results_df.shape}")
    
    # 添加分析结果列（只为第一行）
    results_df['sentiment'] = ['unknown'] * len(results_df)
    results_df['强度'] = [0] * len(results_df)
    results_df['reason'] = ['test'] * len(results_df)
    
    # 更新第一行的真实结果
    results_df.loc[0, 'sentiment'] = result['sentiment']
    results_df.loc[0, '强度'] = result['polarity']
    results_df.loc[0, 'reason'] = result['brief_analysis']
    
    print(f"保存后DataFrame列: {results_df.columns.tolist()}")
    print(f"保存后DataFrame前2行:\n{results_df.head(2)}")
    
    # 保存测试文件
    output_path = 'debug_result.csv'
    results_df.to_csv(output_path, index=False, sep=';', encoding='utf-8')
    print(f"测试文件已保存: {output_path}")

if __name__ == "__main__":
    debug_upload() 