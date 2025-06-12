import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Box, Text, Button } from '@radix-ui/themes';
import { useToast } from '../components/Toast';
import backIcon from '../assets/icons/back.svg';
import avatarIcon from '../assets/icons/Avatar.png';
import sendIcon from '../assets/icons/Send.svg';
import paperclipIcon from '../assets/icons/Paperclip.svg';
import { API_ENDPOINTS, DEFAULT_FETCH_OPTIONS } from '../config/api';

// Add custom styles
const styles = `
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
`;

// Define data structures for analysis results
interface TextAnalysisResult {
  summary: string;
  entities: Entity[];
  keywords: Keyword[];
  sentiment: string; // 更改为字符串类型
  score: number;
  polarity: number; // 添加polarity字段
}

interface Entity {
  text: string;
  type: string;
  relevance: number;
}

interface Keyword {
  text: string;
  relevance: number;
}

// 添加一个新的接口定义，用于CSV数据行
interface CsvRow {
  Content: string;
  sentiment: string;
  score: number;
  polarity: number;
  [key: string]: any; // 允许其他可能的字段
}

// 更新FileAnalysisResult接口，添加csvData字段
interface FileAnalysisResult {
  fileName: string;
  columns: string[];
  rowCount: number;
  summary: string;
  insights: Insight[];
  outputFile?: string;
  csvData?: CsvRow[]; // 添加CSV数据
  sentiment_stats?: {
    positive: number;
    negative: number;
    neutral: number;
  };
}

interface Insight {
  type: string;
  description: string;
  relevance: number;
}

export default function GeneralAnalysis() {
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [textResult, setTextResult] = useState<TextAnalysisResult | null>(null);
  const [fileResult, setFileResult] = useState<FileAnalysisResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  // 渲染完成后显示分析结果的Toast
  useEffect(() => {
    if (fileResult && !textResult && !analyzing) {
      // 获取唯一内容数量
      const uniqueContentCount = fileResult.rowCount || 0;
      
      showToast(`Analysis completed. Successfully analyzed ${uniqueContentCount} contents.`, 'success');
    }
  }, [fileResult, textResult, analyzing, showToast]);

  const handleAnalyze = async () => {
    if (!text.trim()) {
      showToast('Please enter text to analyze', 'error');
      return;
    }

    setLoading(true);
    setAnalyzing(true);
    setTextResult(null);
    setFileResult(null);
    
    try {
      // 使用general API端点
      const response = await fetch(API_ENDPOINTS.GENERAL_ANALYZE, {
        method: 'POST',
        ...DEFAULT_FETCH_OPTIONS,
        body: JSON.stringify({ text: text.trim() }),
      });

      if (!response.ok) {
        throw new Error(`API响应错误: ${response.status}`);
      }

      const data = await response.json();
      
      // 将API响应转换为前端数据结构，直接使用sentiment和score字段
      const result: TextAnalysisResult = {
        summary: data.summary,
        entities: data.entities || [],
        keywords: data.keywords || [],
        sentiment: data.sentiment, // 直接使用sentiment
        score: data.score, // 直接使用score
        polarity: data.polarity || 0 // 直接使用polarity
      };
      
      setTextResult(result);
      showToast('Analysis completed', 'success');
    } catch (error) {
      console.error('分析出错:', error);
      showToast(`Analysis failed: ${error instanceof Error ? error.message : 'Unknown error'}`, 'error');
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
    setTextResult(null);
    setFileResult(null);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log('Uploading file to general API...');
      const response = await fetch(API_ENDPOINTS.GENERAL_UPLOAD, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
        body: formData,
      });

      console.log('Response status:', response.status);
      const responseText = await response.text();
      console.log('Response text length:', responseText.length);
      
      if (!response.ok) {
        console.error('Upload error response:', responseText);
        throw new Error(`File analysis failed: ${responseText}`);
      }

      try {
        // 将响应文本解析为JSON
        const data = JSON.parse(responseText);
        console.log('Upload success, data:', data);
        
        // 创建文件分析结果
        const result: FileAnalysisResult = {
          fileName: data.fileName,
          columns: data.columns || [],
          rowCount: data.rowCount || 0,
          summary: data.summary,
          insights: data.insights || [],
          outputFile: data.output_file,
          sentiment_stats: data.sentiment_stats,
          csvData: data.csvData || []  // 直接使用后端返回的csvData
        };
        
        console.log('CSV data:', result.csvData);
        setFileResult(result);
        // 不在这里显示Toast消息，渲染完成后会显示正确的内容数量
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        throw new Error('Error parsing response data');
      }
    } catch (error: any) {
      console.error('文件分析出错:', error);
      showToast(`File analysis failed: ${error.message}`, 'error');
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const renderAnalysisResult = () => {
    if (!textResult && !fileResult) return null;

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

    if (textResult) {
      return (
        <div style={{ color: 'black', fontSize: '12px', fontFamily: 'Inter', fontWeight: 400 }}>
          <style>{scrollbarStyles}</style>
          
          <div style={{ fontSize: '16px', fontWeight: 600, marginBottom: '15px' }}>Text Analysis Result</div>
          
          <div style={{ marginBottom: '15px' }}>
            Analysis Result: {textResult.sentiment.charAt(0).toUpperCase() + textResult.sentiment.slice(1)}<br/>
            Confidence: {textResult.score.toFixed(1)}%<br/>
            Polarity: {textResult.polarity.toFixed(2)}
          </div>
        </div>
      );
    }

    if (fileResult) {
      // 创建类似TransformerSentiment的直接展示项结构
      interface DirectDisplayItem {
        Review_ID: number;
        Content: string;
        Sentiment: string;
        Confidence: number;
        Polarity: number;
      }
      
      // 构建直接展示的数据列表
      const directDisplayItems: DirectDisplayItem[] = [];
      
      // 从CSV数据生成展示项
      if (fileResult.csvData && fileResult.csvData.length > 0) {
        fileResult.csvData.forEach((row, index) => {
          directDisplayItems.push({
            Review_ID: index + 1,
            Content: row.Content || '',
            Sentiment: row.sentiment.charAt(0).toUpperCase() + row.sentiment.slice(1),
            Confidence: row.score,
            Polarity: row.polarity
          });
        });
      }
      
      // 获取唯一内容数
      const uniqueContentCount = fileResult.rowCount;
      
      // 统计情感分布
      const sentimentStats = fileResult.sentiment_stats || {
        positive: 0,
        negative: 0,
        neutral: 0
      };
      
      // 分组显示结果，使同一内容只显示一次
      let lastReviewId = 0;
      
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
              <div style={{ width: '150px', fontWeight: 500 }}>File Name:</div>
              <div>{fileResult.fileName}</div>
            </div>
            <div style={{ display: 'flex' }}>
              <div style={{ width: '150px', fontWeight: 500 }}>Analyzed Column:</div>
              <div>{fileResult.columns.join(', ')}</div>
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
                <div style={{ fontWeight: 600, color: '#4CAF50', fontSize: '16px' }}>
                  {sentimentStats.positive}
                </div>
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
                <div style={{ fontWeight: 600, color: '#9E9E9E', fontSize: '16px' }}>
                  {sentimentStats.neutral}
                </div>
                <div>Neutral</div>
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
                <div style={{ fontWeight: 600, color: '#F44336', fontSize: '16px' }}>
                  {sentimentStats.negative}
                </div>
                <div>Negative</div>
              </div>
            </div>
          </div>
          
          {/* Analysis Results Table */}
          <div style={{ marginTop: '20px', marginBottom: '20px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '10px' }}>
              Analysis Results: <span style={{ fontWeight: 'normal', color: '#666' }}>
                ({directDisplayItems.length} contents analyzed)
              </span>
            </div>
            <div 
              className="custom-scrollbar"
              style={{ 
                maxHeight: '400px', 
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
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', width: '300px' }}>Content</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB', width: '90px' }}>Sentiment</th>
                    <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #E5E7EB', width: '90px' }}>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {directDisplayItems.map((item, index) => {
                    // 确定是否显示Content
                    const showContent = item.Review_ID !== lastReviewId;
                    // 更新lastReviewId
                    if (showContent) {
                      lastReviewId = item.Review_ID;
                    }
                    
                    // 为同一内容的行设置相同的背景色
                    const rowBackground = index % 2 === 0 ? '#f9f9f9' : 'white';
                    
                    // 根据情感类型设置颜色和背景色
                    const sentimentStyle = 
                      item.Sentiment === 'Positive' ? {
                        color: '#4CAF50',
                        background: 'rgba(76, 175, 80, 0.1)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontWeight: 500
                      } : 
                      item.Sentiment === 'Negative' ? {
                        color: '#F44336',
                        background: 'rgba(244, 67, 54, 0.1)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontWeight: 500
                      } : {
                        color: '#9E9E9E',
                        background: 'rgba(158, 158, 158, 0.1)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontWeight: 500
                      };
                    
                    return (
                      <tr 
                        key={index} 
                        className="table-row-hover" 
                        style={{ 
                          backgroundColor: rowBackground,
                          transition: 'background-color 0.2s ease'
                        }}
                      >
                        <td style={{ padding: '12px', borderBottom: '1px solid #E5E7EB' }}>{item.Review_ID}</td>
                        <td style={{ 
                          padding: '12px', 
                          borderBottom: '1px solid #E5E7EB',
                          maxWidth: '300px',
                          width: '300px',
                          verticalAlign: 'top',
                          position: 'relative'
                        }}>
                          <div className="custom-scrollbar" style={{
                            overflowY: 'auto',
                            overflowX: 'auto',
                            maxHeight: '120px',
                            padding: '8px 10px',
                            fontSize: '12px',
                            lineHeight: '1.5',
                            wordBreak: 'break-word',
                            whiteSpace: 'pre-wrap',
                            border: '1px solid #eaeaea',
                            borderRadius: '4px',
                            background: '#fafafa',
                            boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.05)'
                          }}>
                            {item.Content}
                          </div>
                        </td>
                        <td style={{ padding: '12px', borderBottom: '1px solid #E5E7EB' }}>
                          <div style={sentimentStyle}>
                          {item.Sentiment}
                          </div>
                        </td>
                        <td style={{ padding: '12px', borderBottom: '1px solid #E5E7EB', textAlign: 'center' }}>
                          {Math.abs(item.Confidence * 100).toFixed(1)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* 下载按钮 - 与TransformerSentiment保持一致 */}
          {fileResult.outputFile && (
            <button
              onClick={() => {
                  if (fileResult.outputFile) {
                    window.open(API_ENDPOINTS.GENERAL_DOWNLOAD(fileResult.outputFile), '_blank');
                  }
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
          )}
        </div>
      );
    }

    return null;
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
            <div style={{ color: 'rgba(0, 5, 9, 0.89)', fontSize: '24px', fontFamily: 'SF Pro', fontWeight: 590, wordWrap: 'break-word' }}>General Analysis</div>
          </div>

          {/* Chat Area */}
          <div style={{ 
            alignSelf: 'stretch', 
            flex: '1 1 0', 
            padding: '32px', 
            display: 'flex', 
            flexDirection: 'column', 
            gap: '10px',
            overflowY: 'auto',
            maxHeight: 'calc(100vh - 300px)',
            msOverflowStyle: 'none',
            scrollbarWidth: 'none',
            WebkitOverflowScrolling: 'touch'
          }}
          className="hide-scrollbar"
          >
            {/* Welcome Message */}
            <div style={{ alignSelf: 'stretch', display: 'flex', gap: '14px', alignItems: 'flex-start' }}>
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
                    👋 Welcome to the General Analysis Assistant!<br/>
                    I can analyze sentiment and extract valuable insights from your text data.<br/><br/>
                    Let's get started — what would you like me to analyze today?<br/>
                    You can:<br/>
                    1. Enter text directly for analysis<br/>
                    2. Upload a table file (supports .csv, .xls, .xlsx, .tsv formats) for batch analysis
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
            {(textResult || fileResult) && (
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
                    placeholder="Enter text to analyze"
                    style={{ 
                      flex: 1,
                      border: 'none',
                      outline: 'none',
                      fontSize: '16px',
                      fontFamily: 'SF Pro',
                      fontWeight: 400,
                      lineHeight: '24px',
                      color: 'rgba(0, 5, 29, 0.45)'
                    }}
                    onKeyPress={(e) => {
                      if (e.key === 'Enter') {
                        handleAnalyze();
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
                  onClick={handleAnalyze}
                  disabled={loading}
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
                      opacity: loading ? '0.5' : '1'
                    }}
                    onMouseDown={(e) => !loading && (e.currentTarget.style.opacity = '0.7')}
                    onMouseUp={(e) => !loading && (e.currentTarget.style.opacity = '1')}
                    onMouseLeave={(e) => !loading && (e.currentTarget.style.opacity = '1')}
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