import pandas as pd
import os
import uuid
from datetime import datetime

# 定义输出目录
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class TableService:
    def __init__(self):
        # 初始化表格服务
        pass
        
    def read_table(self, file_path):
        """
        读取表格文件 (CSV, Excel 等)
        """
        # 确定文件类型
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext == '.csv':
            return pd.read_csv(file_path)
        elif file_ext in ['.xls', '.xlsx']:
            return pd.read_excel(file_path)
        elif file_ext == '.tsv':
            return pd.read_csv(file_path, sep='\t')
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")
            
    def save_result(self, df, result_df=None, format='csv'):
        """
        保存处理结果到文件
        """
        # 生成输出文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"analysis_result_{timestamp}_{uuid.uuid4().hex[:8]}"
        
        if format == 'csv':
            output_file += '.csv'
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            # 如果有结果数据框，合并它们
            if result_df is not None:
                # 确保结果数据框与原始数据框长度相同
                if len(df) == len(result_df):
                    df_with_results = pd.concat([df, result_df], axis=1)
                else:
                    # 如果长度不同，保持原样
                    df_with_results = df
            else:
                df_with_results = df
                
            # 保存到CSV
            df_with_results.to_csv(output_path, index=False)
            
        elif format == 'excel':
            output_file += '.xlsx'
            output_path = os.path.join(OUTPUT_DIR, output_file)
            
            # 创建 Excel 写入器
            with pd.ExcelWriter(output_path) as writer:
                df.to_excel(writer, sheet_name='Original Data', index=False)
                if result_df is not None:
                    result_df.to_excel(writer, sheet_name='Analysis Results', index=False)
                    
                    # 如果长度相同，也创建合并表
                    if len(df) == len(result_df):
                        df_with_results = pd.concat([df, result_df], axis=1)
                        df_with_results.to_excel(writer, sheet_name='Combined', index=False)
        else:
            raise ValueError(f"Unsupported output format: {format}")
            
        return output_file
        
    def detect_text_column(self, df):
        """
        自动检测可能包含文本内容的列
        """
        # 可能的文本列名称
        potential_text_cols = ["text", "content", "comment", "review", "message", "description"]
        
        # 首先检查列名
        for col in potential_text_cols:
            if col in df.columns:
                return col
                
        # 其次，查找包含这些词的列
        for col in df.columns:
            for text_col in potential_text_cols:
                if text_col in col.lower():
                    return col
                    
        # 最后，查找包含较长文本的列
        for col in df.columns:
            # 检查数据类型是否为字符串
            if df[col].dtype == 'object':
                # 计算平均文本长度
                avg_len = df[col].astype(str).str.len().mean()
                if avg_len > 20:  # 假设平均长度大于20的是文本列
                    return col
                    
        # 如果找不到，返回第一列
        if len(df.columns) > 0:
            return df.columns[0]
            
        return None

# 创建服务实例
table_service = TableService() 