import React, { useState, useRef, useEffect } from 'react';
import { Box, Text, Button } from '@radix-ui/themes';
import { useToast } from '../components/Toast';
import { Link } from 'react-router-dom';
import backIcon from '../assets/icons/back.svg';
import avatarIcon from '../assets/icons/Avatar.png';
import sendIcon from '../assets/icons/Send.svg';
import paperclipIcon from '../assets/icons/Paperclip.svg';
import { API_ENDPOINTS, DEFAULT_FETCH_OPTIONS } from '../config/api';

// CSV解析函数 - 正确处理带引号的字段
function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let current = '';
  let inQuotes = false;
  let i = 0;
  
  while (i < line.length) {
    const char = line[i];
    
    if (char === '"') {
      if (inQuotes && line[i + 1] === '"') {
        // 双引号转义
        current += '"';
        i += 2;
      } else {
        // 开始或结束引号
        inQuotes = !inQuotes;
        i++;
      }
    } else if (char === ';' && !inQuotes) {
      // 分隔符（不在引号内）
      result.push(current);
      current = '';
      i++;
    } else {
      current += char;
      i++;
    }
  }
  
  result.push(current);
  return result;
}

// Add custom styles
const styles = `
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
`;

interface AnalysisResult {
  aspect: string;
  sentiment: string;
  intensity: number;
  score: number;
  polarity: number;
  brief_analysis: string;
}

interface AspectSentiment {
  aspect: string;
  positive: number;
  negative: number;
  neutral: number;
  total: number;
}

interface AspectAnalysisResult {
  aspect: string;
  sentiment: string;
  intensity: number;
  reason: string;
}

interface TableAnalysisResult {
  total_rows: number;
  analyzed_column: string;
  results: AnalysisResult[];
  summary: {
    positive: number;
    negative: number;
    neutral: number;
    total: number;
  };
  aspect_analysis: AspectSentiment[];
  aspect_details: AspectAnalysisResult[];
  output_file: string;
  original_texts?: string[];
  csvData?: any[];
  csvHeaders?: string[];
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant';
  content: string;
  timestamp: number;
  isError?: boolean;
}

interface ChatRequest {
  message: string;
  analysis_data?: any;
  context?: string;
}

interface ChatResponse {
  message: string;
  is_sentiment_related: boolean;
}

export default function LLMSentiment() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tableResult, setTableResult] = useState<TableAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatLoading, setChatLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  // 渲染完成后显示分析结果的Toast
  useEffect(() => {
    if (tableResult && !result && !analyzing) {
      // 获取唯一内容数量 - 使用 original_texts 的长度作为基准
      const uniqueContentCount = tableResult.original_texts ? tableResult.original_texts.length : 0;
      
      showToast(`Analysis completed. Successfully analyzed ${uniqueContentCount} contents with ${tableResult.aspect_details ? tableResult.aspect_details.length : 0} aspect analyses.`, 'success');
    }
  }, [tableResult, result, analyzing, showToast]);

  const handleAnalyze = async () => {
    if (!text.trim()) {
      showToast('Please enter text to analyze', 'error');
      return;
    }

    setLoading(true);
    setAnalyzing(true);
    setResult(null);
    setTableResult(null);
    
    try {
      const response = await fetch(API_ENDPOINTS.LLM_SENTIMENT, {
        method: 'POST',
        ...DEFAULT_FETCH_OPTIONS,
        body: JSON.stringify({ text: text.trim() }),
      });

      if (!response.ok) {
        throw new Error('Sentiment analysis failed');
      }

      const data = await response.json();
      setResult(data);
      setTableResult(null);
      setText(''); // 清空输入框
      showToast('Analysis completed', 'success');
    } catch (error) {
      showToast('Analysis failed, please try again', 'error');
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    const allowedTypes = [
      'text/csv',
      'application/vnd.ms-excel',
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'text/tab-separated-values'
    ];
    
    console.log('File type:', file.type);
    console.log('File name:', file.name);
    console.log('File size:', file.size, 'bytes');
    
    if (!allowedTypes.includes(file.type) && !file.name.endsWith('.csv')) {
      showToast('Unsupported file type. Please upload .csv, .xls, .xlsx, or .tsv files', 'error');
      return;
    }

    setLoading(true);
    setAnalyzing(true);
    setResult(null);
    setTableResult(null);
    
    try {
      console.log('Uploading file...');
      console.log('File details:', {
        name: file.name,
        type: file.type,
        size: file.size
      });

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(API_ENDPOINTS.LLM_SENTIMENT_UPLOAD, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
        body: formData,
      });

      console.log('Response status:', response.status);
      console.log('Response headers:', Object.fromEntries(response.headers.entries()));
      
      const responseText = await response.text();
      console.log('Response text:', responseText);
      
      if (!response.ok) {
        console.error('Upload failed:', responseText);
        throw new Error(`File analysis failed: ${responseText}`);
      }

      let data;
      try {
        data = JSON.parse(responseText);
        console.log('Parsed response data:', data);
      } catch (parseError) {
        console.error('Failed to parse response:', parseError);
        throw new Error('Failed to parse server response');
      }

      setTableResult(data);
      
      // 下载并解析生成的CSV文件数据用于显示
      try {
        console.log('Downloading CSV file for display:', data.output_file);
        const csvResponse = await fetch(API_ENDPOINTS.LLM_SENTIMENT_DOWNLOAD(data.output_file));
        if (csvResponse.ok) {
          const csvText = await csvResponse.text();
          console.log('CSV file downloaded successfully');
          
          // 解析CSV数据 - 改进版本，正确处理带引号的字段
          const lines = csvText.trim().split('\n');
          const headers = parseCSVLine(lines[0]);
          const csvData = [];
          
          for (let i = 1; i < lines.length; i++) {
            const values = parseCSVLine(lines[i]);
            const row: { [key: string]: string } = {};
            headers.forEach((header: string, index: number) => {
              row[header.trim()] = values[index] ? values[index].trim() : '';
            });
            csvData.push(row);
          }
          
          console.log('Parsed CSV data:', csvData);
          console.log('CSV headers:', headers);
          
          // 更新表格数据，使用CSV文件的数据
          setTableResult({
            ...data,
            csvData: csvData,
            csvHeaders: headers.map((h: string) => h.trim())
          });
        } else {
          console.error('Failed to download CSV file');
        }
      } catch (csvError) {
        console.error('Error downloading CSV file:', csvError);
      }
      
      setResult(null);
      showToast('File analysis completed', 'success');
    } catch (error: any) {
      console.error('File upload error:', error);
      showToast(`File analysis failed: ${error.message}`, 'error');
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleSendChatMessage = async (message: string) => {
    if (!message.trim()) return;

    // 添加用户消息
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: 'user',
      content: message.trim(),
      timestamp: Date.now()
    };

    setChatMessages(prev => [...prev, userMessage]);
    setChatLoading(true);

    try {
      // 准备分析数据（如果有）
      let analysisData = null;
      if (tableResult) {
        analysisData = {
          total_rows: tableResult.total_rows,
          summary: tableResult.summary,
          analyzed_column: tableResult.analyzed_column
        };
      }

      const chatRequest: ChatRequest = {
        message: message.trim(),
        analysis_data: analysisData
      };

      const response = await fetch(API_ENDPOINTS.LLM_SENTIMENT_CHAT, {
        method: 'POST',
        ...DEFAULT_FETCH_OPTIONS,
        body: JSON.stringify(chatRequest),
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const chatResponse: ChatResponse = await response.json();
      
      console.log('Chat response received:', chatResponse);
      console.log('Is sentiment related:', chatResponse.is_sentiment_related);
      console.log('Response message:', chatResponse.message);
      
      // 添加助手回复
      const assistantMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: chatResponse.message,
        timestamp: Date.now(),
        isError: !chatResponse.is_sentiment_related
      };

      setChatMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      
      // 添加错误消息
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: 'assistant',
        content: 'I apologize, but I encountered an error while processing your message. Please try again.',
        timestamp: Date.now(),
        isError: true
      };

      setChatMessages(prev => [...prev, errorMessage]);
      showToast('Chat request failed', 'error');
    } finally {
      setChatLoading(false);
    }
  };

  const handleSendMessage = () => {
    if (!text.trim()) {
      showToast('Please enter some text', 'error');
      return;
    }

    // 检测是否是问句（简单的启发式检测）
    const isQuestion = text.trim().includes('?') || 
                      text.toLowerCase().startsWith('what') ||
                      text.toLowerCase().startsWith('how') ||
                      text.toLowerCase().startsWith('why') ||
                      text.toLowerCase().startsWith('when') ||
                      text.toLowerCase().startsWith('where') ||
                      text.toLowerCase().startsWith('which') ||
                      text.toLowerCase().startsWith('can you') ||
                      text.toLowerCase().startsWith('could you') ||
                      text.toLowerCase().startsWith('tell me') ||
                      text.toLowerCase().startsWith('explain');

    if (isQuestion || tableResult) {
      // 如果是问句或者已经有分析结果，则发送聊天消息
      handleSendChatMessage(text);
      setText('');
    } else {
      // 否则进行情感分析
      handleAnalyze();
    }
  };

  const renderAnalysisResult = () => {
    if (!result && !tableResult) return null;

    // 添加自定义滚动条样式
    const scrollbarStyles = `
      .custom-scrollbar::-webkit-scrollbar {
        width: 6px;
        height: 6px;
      }
      .custom-scrollbar::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 4px;
      }
      .custom-scrollbar::-webkit-scrollbar-thumb {
        background: #ccc;
        border-radius: 4px;
      }
      .custom-scrollbar::-webkit-scrollbar-thumb:hover {
        background: #aaa;
      }
      .table-row-hover:hover {
        background-color: rgba(245, 247, 250, 0.8) !important;
      }
    `;

    if (result) {
      return (
        <div style={{ color: 'black', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>
          Analysis Result: {result.sentiment === 'positive' ? 'Positive' : result.sentiment === 'negative' ? 'Negative' : 'Neutral'}<br/>
                      Aspect: {result.aspect}<br/>
            Intensity: {result.intensity}<br/>
          Polarity: {result.polarity}
        </div>
      );
    }

    if (tableResult) {
      // 定义直接展示格式的数据结构
      interface DirectDisplayItem {
        Review_ID: number;
        Content: string;
        AspectAnalyses: Array<{
          Aspect: string;
          Sentiment: string;
          Intensity: number;
          Reason: string;
        }>;
      }

      const directDisplayItems: DirectDisplayItem[] = [];
      
      // 优先使用CSV数据进行合并显示
      if (tableResult.csvData && tableResult.csvHeaders) {
        // 将CSV数据按Review_ID分组进行合并显示
        const groupedData: { [key: number]: DirectDisplayItem } = {};
        
        tableResult.csvData.forEach(row => {
          const reviewId = parseInt(row.Review_ID || '0');
          
          if (!groupedData[reviewId]) {
            groupedData[reviewId] = {
              Review_ID: reviewId,
              Content: row.Content || '',
              AspectAnalyses: []
            };
          }
          
          // 添加aspect分析
          groupedData[reviewId].AspectAnalyses.push({
            Aspect: row.aspect || 'Overall Experience',
            Sentiment: row.sentiment || 'neutral',
            Intensity: parseFloat(row.intensity || '0'),
            Reason: row.reason || ''
          });
        });
        
        // 转换为数组并排序
        directDisplayItems.push(...Object.values(groupedData).sort((a, b) => a.Review_ID - b.Review_ID));
      }
      // 后备：处理原始数据格式
      else if (tableResult.original_texts && tableResult.aspect_details) {
        const contentCount = tableResult.original_texts.length;
        const aspectCount = tableResult.aspect_details.length;
        
        // 创建内容映射
        const contentMap: { [key: number]: { content: string; aspects: any[] } } = {};
        
        // 初始化内容映射
        for (let i = 0; i < contentCount; i++) {
          contentMap[i + 1] = {
            content: tableResult.original_texts[i],
            aspects: []
          };
        }
        
        // 分配方面分析
        let aspectIndex = 0;
        for (let i = 0; i < contentCount && aspectIndex < aspectCount; i++) {
          const aspectsPerContent = Math.ceil((aspectCount - aspectIndex) / (contentCount - i));
          
          for (let j = 0; j < aspectsPerContent && aspectIndex < aspectCount; j++) {
            const detail = tableResult.aspect_details[aspectIndex++];
            contentMap[i + 1].aspects.push({
              Aspect: detail.aspect,
              Sentiment: detail.sentiment,
              Intensity: detail.intensity,
              Reason: detail.reason
            });
          }
        }
        
        // 将contentMap转换为directDisplayItems
        Object.entries(contentMap).forEach(([reviewId, data]) => {
          directDisplayItems.push({
            Review_ID: parseInt(reviewId),
            Content: data.content,
            AspectAnalyses: data.aspects.length > 0 ? data.aspects : [{
              Aspect: "General Content",
              Sentiment: "neutral",
              Intensity: 0.0,
              Reason: "No specific aspects detected in this content."
            }]
          });
        });
        
        // 按Review_ID排序
        directDisplayItems.sort((a, b) => a.Review_ID - b.Review_ID);
      }
      
      // 统计分析了多少个独立的内容
      const uniqueContentCount = tableResult.original_texts ? tableResult.original_texts.length : 0;
      
      return (
        <div style={{ color: 'black', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>
          <style>{scrollbarStyles}</style>

          <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '15px' }}>File Analysis Completed</div>
          
          <div style={{ marginBottom: '15px' }}>
            <div style={{ display: 'flex' }}>
              <div style={{ width: '150px', fontWeight: 500 }}>Original Content Count:</div>
              <div>{uniqueContentCount}</div>
            </div>
            <div style={{ display: 'flex' }}>
              <div style={{ width: '150px', fontWeight: 500 }}>Aspect Analysis Count:</div>
              <div>{tableResult.aspect_details ? tableResult.aspect_details.length : 0}</div>
            </div>
            <div style={{ display: 'flex' }}>
              <div style={{ width: '150px', fontWeight: 500 }}>Analyzed Column:</div>
              <div>{tableResult.analyzed_column}</div>
            </div>
            
            {/* Sentiment Distribution Summary */}
            <div style={{ display: 'flex', marginTop: '10px', gap: '20px' }}>
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: '#f5f5f5',
                padding: '10px',
                borderRadius: '8px',
                minWidth: '80px'
              }}>
                <div style={{ fontWeight: 600, color: '#4CAF50', fontSize: '16px' }}>{tableResult.summary.positive}</div>
                <div>Positive</div>
              </div>
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: '#f5f5f5',
                padding: '10px',
                borderRadius: '8px',
                minWidth: '80px'
              }}>
                <div style={{ fontWeight: 600, color: '#F44336', fontSize: '16px' }}>{tableResult.summary.negative}</div>
                <div>Negative</div>
              </div>
              <div style={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center',
                background: '#f5f5f5',
                padding: '10px',
                borderRadius: '8px',
                minWidth: '80px'
              }}>
                <div style={{ fontWeight: 600, color: '#9E9E9E', fontSize: '16px' }}>{tableResult.summary.neutral}</div>
                <div>Neutral</div>
              </div>
            </div>
          </div>
          
          {/* Analysis Results Table */}
          <div style={{ marginTop: '20px', marginBottom: '20px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '10px' }}>
              Analysis Results: <span style={{ fontWeight: 'normal', color: '#666' }}>
                ({tableResult.csvData ? tableResult.csvData.length : tableResult.total_rows} rows, 
                CSV file format)
              </span>
            </div>
            <div 
              className="custom-scrollbar"
              style={{ 
                maxHeight: '500px', 
                overflowY: 'auto',
                border: '1px solid #E5E7EB',
                borderRadius: '8px'
              }}
            >
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead style={{ 
                  position: 'sticky', 
                  top: 0, 
                  background: '#F9FAFB',
                  borderBottom: '2px solid #E5E7EB',
                  zIndex: 1
                }}>
                  <tr>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', width: '40px' }}>ID</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', width: '400px' }}>Content</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', width: '100px' }}>Aspect</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', width: '90px' }}>Sentiment</th>
                    <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #E5E7EB', width: '90px' }}>Intensity</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB' }}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {directDisplayItems.map((item, index) => {
                    // 为每行设置背景色
                    const rowBackground = index % 2 === 0 ? '#f9f9f9' : 'white';
                    
                    // 计算内容单元格的rowSpan
                    const rowSpan = item.AspectAnalyses.length;
                    
                    return (
                      <>
                        {item.AspectAnalyses.map((aspect, aspectIndex) => (
                          <tr 
                            className="table-row-hover" 
                            key={`item-${index}-aspect-${aspectIndex}`} 
                            style={{ 
                              borderBottom: aspectIndex === item.AspectAnalyses.length - 1 ? '1px solid #E5E7EB' : 'none',
                              backgroundColor: rowBackground
                            }}
                          >
                            {aspectIndex === 0 && (
                              <>
                                <td 
                                  rowSpan={rowSpan}
                                  style={{ 
                                    padding: '12px', 
                                    verticalAlign: 'top',
                                    textAlign: 'center',
                                    fontWeight: 500,
                                    color: '#555',
                                    borderRight: '1px solid #E5E7EB',
                                  }}
                                >
                                  {item.Review_ID}
                                </td>
                                <td 
                                  rowSpan={rowSpan}
                                  style={{ 
                                    padding: '12px', 
                                    maxWidth: '400px',
                                    width: '400px',
                                    verticalAlign: 'top',
                                    position: 'relative',
                                    borderRight: '1px solid #E5E7EB',
                                  }}
                                >
                                  <div className="custom-scrollbar" style={{
                                    overflowY: 'auto',
                                    overflowX: 'auto',
                                    maxHeight: '250px',
                                    padding: '12px 15px',
                                    fontSize: '13px',
                                    lineHeight: '1.6',
                                    wordBreak: 'break-word',
                                    whiteSpace: 'pre-wrap',
                                    border: '1px solid #eaeaea',
                                    borderRadius: '4px',
                                    background: '#fafafa',
                                    boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.05)',
                                    fontStyle: item.Content && item.Content.startsWith('Row ') ? 'italic' : 'normal',
                                    color: item.Content && item.Content.startsWith('Row ') ? '#888' : 'inherit'
                                  }}>
                                    {item.Content && item.Content.startsWith('Row ') ? 
                                      `[Default Row ID: ${item.Content.substring(4)}]` : 
                                      item.Content}
                                  </div>
                                </td>
                              </>
                            )}
                            <td style={{ padding: '12px', fontWeight: 500, maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {aspect.Aspect}
                            </td>
                            <td style={{ 
                              padding: '12px', 
                              color: aspect.Sentiment === 'positive' ? '#4CAF50' : 
                                    aspect.Sentiment === 'negative' ? '#F44336' : '#9E9E9E',
                              fontWeight: 500
                            }}>
                              {aspect.Sentiment.charAt(0).toUpperCase() + aspect.Sentiment.slice(1)}
                            </td>
                            <td style={{ padding: '12px', textAlign: 'center' }}>
                              {aspect.Intensity}
                            </td>
                            <td style={{ padding: '12px' }}>
                              {aspect.Reason}
                            </td>
                          </tr>
                        ))}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <button
            onClick={() => {
              window.open(API_ENDPOINTS.LLM_SENTIMENT_DOWNLOAD(tableResult.output_file), '_blank');
            }}
            style={{
              padding: '8px 16px',
              background: '#5D5FEF',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px',
              fontFamily: 'SF Pro',
              fontWeight: 500,
              transition: 'opacity 0.2s ease'
            }}
            onMouseDown={(e) => e.currentTarget.style.opacity = '0.7'}
            onMouseUp={(e) => e.currentTarget.style.opacity = '1'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          >
            Download Analysis Results
          </button>
        </div>
      );
    }
  };

  return (
    <div style={{ width: '100%', height: '100%', background: '#FDF5EB', overflow: 'hidden', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      <style>{styles}</style>
      {/* Top Navigation Bar */}
      <div style={{ alignSelf: 'stretch', padding: '12px 36px', background: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ color: 'black', fontSize: '36px', fontFamily: 'League Spartan', fontWeight: 700, wordWrap: 'break-word' }}>ai.meichai</div>
        <Button style={{ height: '40px', padding: '0 16px', background: '#F76B15', borderRadius: '6px', color: 'white', fontSize: '16px', fontFamily: 'SF Pro', fontWeight: 510, lineHeight: '24px' }}>
          Contact
        </Button>
      </div>

      {/* Back Button */}
      <div style={{ alignSelf: 'stretch', padding: '12px 48px', display: 'flex', alignItems: 'center', gap: '10px' }}>
        <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '10px', textDecoration: 'none' }}>
          <img 
            src={backIcon} 
            alt="Back" 
            style={{ 
              width: '32px', 
              height: '32px', 
              cursor: 'pointer',
              transition: 'opacity 0.2s ease',
            }}
            onMouseDown={(e) => e.currentTarget.style.opacity = '0.7'}
            onMouseUp={(e) => e.currentTarget.style.opacity = '1'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          />
          <div style={{ color: '#202020', fontSize: '20px', fontFamily: 'SF Pro', fontWeight: 510, wordWrap: 'break-word' }}>Back</div>
        </Link>
      </div>

      {/* Main Content Area */}
      <div style={{ alignSelf: 'stretch', padding: '0 48px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px' }}>
        <div style={{ width: '100%', height: '669px', maxWidth: '1200px', background: 'white', boxShadow: '0px 8px 24px rgba(0, 0, 0, 0.08)', borderRadius: '12px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
          {/* Title Bar */}
          <div style={{ alignSelf: 'stretch', padding: '16px 24px', background: 'white', borderTopLeftRadius: '12px', borderTopRightRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ color: 'rgba(0, 5, 9, 0.89)', fontSize: '24px', fontFamily: 'SF Pro', fontWeight: 590, wordWrap: 'break-word' }}>Large Language Models Sentiment Analysis</div>
          </div>

          {/* Chat Area */}
          <div style={{ flex: 1, padding: '24px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Welcome Message */}
            <div style={{ display: 'flex', gap: '14px' }}>
              <div style={{ width: '32px', height: '32px', background: '#5D5FEF', borderRadius: '20px', display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', flexShrink: 0 }}>
                <img 
                  src={avatarIcon} 
                  alt="Assistant" 
                  style={{ 
                    width: '100%', 
                    height: '100%', 
                    objectFit: 'cover',
                    borderRadius: '20px'
                  }} 
                />
              </div>

              <div style={{ flex: '1 1 0', display: 'flex', flexDirection: 'column', gap: '13px' }}>
                <div style={{ alignSelf: 'stretch', color: '#363636', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400, wordWrap: 'break-word' }}>Analysis Assistant</div>
                <div style={{ maxWidth: '835px', padding: '14px 21px 10px', background: '#F2F3F7', borderRadius: '8px', display: 'inline-flex' }}>
                  <div style={{ flex: '1 1 0', color: 'black', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400, wordWrap: 'break-word' }}>
                    👋 Welcome to the Large Language Models Sentiment Analysis Assistant!<br/>
                    I use advanced LLM models to analyze the sentiment behind text — whether it's product reviews, customer feedback, tweets, or other messages.<br/><br/>
                    You can:<br/>
                    1. <strong>Enter text directly</strong> for quick sentiment analysis<br/>
                    2. <strong>Upload a table file</strong> (supports .csv, .xls, .xlsx, .tsv formats) for batch analysis<br/>
                    3. <strong>Ask me questions</strong> about sentiment analysis, emotions, or any uploaded data<br/><br/>
                    <em>Note: I can only answer questions related to sentiment analysis and emotions. For other topics, I'll politely redirect you back to sentiment-related discussions.</em>
                  </div>
                </div>
              </div>
            </div>

            {/* Analyzing Message - Loading indicator bubble */}
            {analyzing && (
              <div style={{ display: 'flex', gap: '14px', marginTop: '20px' }}>
                <div style={{ width: '32px', height: '32px', background: '#5D5FEF', borderRadius: '20px', display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', flexShrink: 0 }}>
                  <img 
                    src={avatarIcon} 
                    alt="Assistant" 
                    style={{ 
                      width: '100%', 
                      height: '100%', 
                      objectFit: 'cover',
                      borderRadius: '20px'
                    }} 
                  />
                </div>
                <div style={{ flex: '1 1 0', display: 'flex', flexDirection: 'column', gap: '13px' }}>
                  <div style={{ color: '#363636', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>Analysis Assistant</div>
                  <div style={{ maxWidth: '835px', padding: '14px 21px 10px', background: '#F2F3F7', borderRadius: '8px' }}>
                    <div style={{ color: 'black', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>
                      Analysing... Please wait while we process your content.
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Results Display Area */}
            {(result || tableResult) && (
              <div style={{ display: 'flex', gap: '14px', marginTop: '20px' }}>
                <div style={{ width: '32px', height: '32px', background: '#5D5FEF', borderRadius: '20px', display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', flexShrink: 0 }}>
                  <img 
                    src={avatarIcon} 
                    alt="Assistant" 
                    style={{ 
                      width: '100%', 
                      height: '100%', 
                      objectFit: 'cover',
                      borderRadius: '20px'
                    }} 
                  />
                </div>
                <div style={{ flex: '1 1 0', display: 'flex', flexDirection: 'column', gap: '13px' }}>
                  <div style={{ color: '#363636', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>Analysis Result</div>
                  <div style={{ maxWidth: '835px', padding: '14px 21px 10px', background: '#F2F3F7', borderRadius: '8px' }}>
                    {renderAnalysisResult()}
                  </div>
                </div>
              </div>
            )}

            {/* Chat Messages Display */}
            {chatMessages.map((message) => (
              <div key={message.id} style={{ display: 'flex', gap: '14px', marginTop: '20px' }}>
                {message.type === 'assistant' && (
                  <div style={{ width: '32px', height: '32px', background: '#5D5FEF', borderRadius: '20px', display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', flexShrink: 0 }}>
                    <img 
                      src={avatarIcon} 
                      alt="Assistant" 
                      style={{ 
                        width: '100%', 
                        height: '100%', 
                        objectFit: 'cover',
                        borderRadius: '20px'
                      }} 
                    />
                  </div>
                )}
                
                <div style={{ 
                  flex: '1 1 0', 
                  display: 'flex', 
                  flexDirection: 'column', 
                  gap: '13px',
                  ...(message.type === 'user' ? { alignItems: 'flex-end' } : {})
                }}>
                  <div style={{ 
                    color: '#363636', 
                    fontSize: '12px', 
                    fontFamily: 'Inter', 
                    fontWeight: 400,
                    ...(message.type === 'user' ? { textAlign: 'right' } : {})
                  }}>
                    {message.type === 'user' ? 'You' : 'Analysis Assistant'}
                  </div>
                  <div style={{ 
                    maxWidth: '835px', 
                    padding: '14px 21px 10px', 
                    background: message.type === 'user' ? '#E3F2FD' : (message.isError ? '#FFE6E6' : '#F2F3F7'), 
                    borderRadius: '8px', 
                    display: 'inline-flex',
                    ...(message.type === 'user' ? { marginLeft: 'auto' } : {})
                  }}>
                    <div style={{ 
                      flex: '1 1 0', 
                      color: message.isError ? '#D32F2F' : 'black', 
                      fontSize: '12px', 
                      fontFamily: 'Inter', 
                      fontWeight: 400, 
                      wordWrap: 'break-word',
                      whiteSpace: 'pre-wrap'
                    }}>
                      {message.content}
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {/* Chat Loading Indicator */}
            {chatLoading && (
              <div style={{ display: 'flex', gap: '14px', marginTop: '20px' }}>
                <div style={{ width: '32px', height: '32px', background: '#5D5FEF', borderRadius: '20px', display: 'flex', justifyContent: 'center', alignItems: 'center', overflow: 'hidden', flexShrink: 0 }}>
                  <img 
                    src={avatarIcon} 
                    alt="Assistant" 
                    style={{ 
                      width: '100%', 
                      height: '100%', 
                      objectFit: 'cover',
                      borderRadius: '20px'
                    }} 
                  />
                </div>
                <div style={{ flex: '1 1 0', display: 'flex', flexDirection: 'column', gap: '13px' }}>
                  <div style={{ color: '#363636', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>Analysis Assistant</div>
                  <div style={{ maxWidth: '835px', padding: '14px 21px 10px', background: '#F2F3F7', borderRadius: '8px' }}>
                    <div style={{ color: 'black', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>
                      Thinking... Please wait while I process your question.
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Input Area */}
          <div style={{ alignSelf: 'stretch', padding: '12px 32px', borderTop: '1px solid #D3D3D3', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ alignSelf: 'stretch', display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{ flex: '1 1 0', height: '48px', padding: '0 24px', borderRadius: '24px', outline: '1px solid #C1C1C1', outlineOffset: '-1px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                  <img 
                    src={paperclipIcon} 
                    alt="Attach" 
                    style={{ 
                      width: '24px', 
                      height: '24px',
                      cursor: 'pointer',
                      transition: 'opacity 0.2s ease',
                    }}
                    onMouseDown={(e) => e.currentTarget.style.opacity = '0.7'}
                    onMouseUp={(e) => e.currentTarget.style.opacity = '1'}
                    onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
                    onClick={handleFileClick}
                  />
                  <input
                    type="text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Enter text to analyze or ask a question about sentiment analysis..."
                    style={{ 
                      flex: 1,
                      border: 'none',
                      outline: 'none',
                      fontSize: '16px',
                      fontFamily: 'SF Pro',
                      fontWeight: 400,
                      lineHeight: '24px',
                      color: '#000000'
                    }}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleSendMessage();
                      }
                    }}
                  />
                  <input
                    type="file"
                    ref={fileInputRef}
                    style={{ display: 'none' }}
                    accept=".csv,.xls,.xlsx,.tsv"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) {
                        handleFileUpload(file);
                      }
                    }}
                  />
                </div>
                <button 
                  onClick={() => handleSendMessage()}
                  disabled={loading || chatLoading}
                  style={{ 
                    width: '24px',
                    height: '24px',
                    background: 'none',
                    border: 'none',
                    padding: 0,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                >
                  <img 
                    src={sendIcon} 
                    alt="Send"
                    style={{ 
                      width: '24px', 
                      height: '24px',
                      transition: 'opacity 0.2s ease',
                      opacity: (loading || chatLoading) ? '0.5' : '1'
                    }}
                    onMouseDown={(e) => !(loading || chatLoading) && (e.currentTarget.style.opacity = '0.7')}
                    onMouseUp={(e) => !(loading || chatLoading) && (e.currentTarget.style.opacity = '1')}
                    onMouseLeave={(e) => !(loading || chatLoading) && (e.currentTarget.style.opacity = '1')}
                  />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 