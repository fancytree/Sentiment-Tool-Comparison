from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from app.models.sentiment import TextInput, SentimentResponse, TableAnalysisResult, UploadResponse
from app.services.sentiment_service import sentiment_service
from app.services.table_service import table_service
import logging
import os
from tempfile import NamedTemporaryFile
from typing import Optional
import pandas as pd
import numpy as np

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/sentiment",
    tags=["sentiment"],
    responses={404: {"description": "Not found"}},
)

def process_dataframe_for_json(df: pd.DataFrame) -> list:
    """处理数据框，确保 JSON 兼容"""
    raw_data = []
    for record in df.to_dict('records'):
        processed_record = {}
        for key, value in record.items():
            if pd.isna(value) or value is None:
                processed_record[key] = None
            elif isinstance(value, float):
                if np.isinf(value) or np.isnan(value):
                    processed_record[key] = None
                else:
                    processed_record[key] = float(value)
            else:
                processed_record[key] = value
        raw_data.append(processed_record)
    return raw_data

@router.post("/", response_model=SentimentResponse)
async def analyze_sentiment(text_input: TextInput):
    """分析单条文本的情感"""
    try:
        logger.info(f"收到情感分析请求: {text_input.text}")
        result = sentiment_service.analyze(text_input.text)
        logger.info(f"情感分析结果: {result}")
        return result
    except Exception as e:
        logger.error(f"情感分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload")
async def upload_file(file: UploadFile = File(...), text_column: str = None):
    """上传并分析表格文件"""
    try:
        logger.info(f"收到文件上传请求: {file.filename}")
        
        # 检查文件类型
        if not table_service.is_allowed_file(file.filename):
            allowed_exts = ', '.join(table_service.ALLOWED_EXTENSIONS)
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型。支持的类型：{allowed_exts}"
            )
        
        # 保存上传的文件
        with NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
            
        try:
            # 读取表格
            logger.info(f"开始读取文件: {file.filename}")
            df = table_service.read_table(temp_file_path)
            
            # 分析表格
            logger.info(f"开始分析表格，总行数: {len(df)}")
            result = table_service.analyze_table(df, text_column)
            logger.info(f"表格分析完成: {result['summary']}")
            
            return result
        except ValueError as ve:
            logger.error(f"表格处理失败: {str(ve)}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            logger.error(f"表格处理发生错误: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"清理临时文件失败: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传处理失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/download/{filename}")
async def download_file(filename: str):
    """下载分析结果文件"""
    try:
        file_path = os.path.join(table_service.OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")
            
        return FileResponse(
            file_path,
            media_type='text/csv',
            filename=filename
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件下载失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest")
async def get_latest_analysis():
    """获取最新的分析结果"""
    try:
        # 获取最新的CSV文件
        latest_file = table_service.get_latest_file()
        
        # 读取CSV文件
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        
        # 处理特殊值
        for col in df.columns:
            # 将无穷大值替换为 None
            df[col] = df[col].replace([np.inf, -np.inf], None)
            # 将 NaN 值替换为 None
            df[col] = df[col].where(pd.notnull(df[col]), None)
        
        # 统计情感分析结果
        sentiment_stats = {
            'positive': len(df[df['sentiment'] == 'positive']),
            'negative': len(df[df['sentiment'] == 'negative']),
            'neutral': len(df[df['sentiment'] == 'neutral'])
        }
        
        # 准备返回数据
        return {
            'stats': sentiment_stats,
            'raw_data': process_dataframe_for_json(df),
            'total_rows': len(df),
            'columns': list(df.columns)
        }
    except Exception as e:
        logger.error(f"获取最新分析结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 