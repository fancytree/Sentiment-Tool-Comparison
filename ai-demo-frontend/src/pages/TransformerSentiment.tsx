import React, { useState, useRef, useEffect } from 'react';
import { Box, Text, Button } from '@radix-ui/themes';
import { useToast } from '../components/Toast';
import { Link } from 'react-router-dom';
import backIcon from '../assets/icons/back.svg';
import avatarIcon from '../assets/icons/Avatar.png';
import sendIcon from '../assets/icons/Send.svg';
import paperclipIcon from '../assets/icons/Paperclip.svg';
import Papa from 'papaparse';

// Add custom styles
const styles = `
  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }
`;

interface AnalysisResult {
  sentiment: string;
  score: number;
  polarity: number;
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
  confidence: number;
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
}

export default function TransformerSentiment() {
  const [text, setText] = useState('');
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [tableResult, setTableResult] = useState<TableAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();
  const [csvTableData, setCsvTableData] = useState<any[]>([]);

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
      const response = await fetch('http://localhost:8001/api/transformer-sentiment/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Origin': 'http://localhost:5173'
        },
        body: JSON.stringify({ text: text.trim() }),
      });

      if (!response.ok) {
        throw new Error('Sentiment analysis failed');
      }

      const data = await response.json();
      setResult(data);
      setTableResult(null);
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
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      console.log('Uploading file...');
      const response = await fetch('http://localhost:8001/api/transformer-sentiment/upload', {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Origin': 'http://localhost:5173'
        },
        body: formData,
      });

      console.log('Response status:', response.status);
      const responseText = await response.text();
      console.log('Response text length:', responseText.length);
      
      if (!response.ok) {
        throw new Error(`File analysis failed: ${responseText}`);
      }

      try {
        const data = JSON.parse(responseText);
        console.log('Parsed data summary:', {
          total_rows: data.total_rows,
          analyzed_column: data.analyzed_column,
          results_count: data.results ? data.results.length : 0,
          original_texts_count: data.original_texts ? data.original_texts.length : 0,
          aspect_analysis_count: data.aspect_analysis ? data.aspect_analysis.length : 0,
          aspect_details_count: data.aspect_details ? data.aspect_details.length : 0
        });
        
        // 验证原始内容数量
        console.log(`原始内容数量: ${data.total_rows}`);
        
        setTableResult(data);
        setResult(null);
        
        // 新增：分析成功后自动下载并解析CSV
        if (data.output_file) {
          const csvRes = await fetch(`http://localhost:8001/api/transformer-sentiment/download/${data.output_file}`);
          const csvText = await csvRes.text();
          const parsed = Papa.parse(csvText, { header: true });
          setCsvTableData(parsed.data);
        }
      } catch (parseError) {
        console.error('JSON parse error:', parseError);
        throw new Error('Error parsing response data');
      }
    } catch (error: any) {
      console.error('Upload error:', error);
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
          Confidence: {result.score}%<br/>
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
          Confidence: string;
          Reason: string;
        }>;
      }
      
      // 优先用csvTableData渲染表格
      let displayItems: DirectDisplayItem[] = [];
      if (csvTableData && csvTableData.length > 0) {
        // 按Review_ID和Content分组，合并AspectAnalyses
        const groupedItems: Record<string, DirectDisplayItem> = {};
        csvTableData.filter(row => row.Review_ID).forEach((row) => {
          const key = `${row['Review_ID']}-${row['Content']}`;
          if (!groupedItems[key]) {
            groupedItems[key] = {
              Review_ID: row['Review_ID'],
              Content: row['Content'],
              AspectAnalyses: []
            };
          }
          groupedItems[key].AspectAnalyses.push({
            Aspect: row['Aspect'],
            Sentiment: row['Sentiment'],
            Confidence: row['Confidence'],
            Reason: row['Reason']
          });
        });
        displayItems = Object.values(groupedItems);
      } else {
        // 兼容老逻辑
        const directDisplayItems: DirectDisplayItem[] = [];
        if (tableResult.aspect_details && tableResult.aspect_details.length > 0 && tableResult.original_texts) {
          console.log('Aspect details:', tableResult.aspect_details);
          console.log('Original texts:', tableResult.original_texts);

          // 创建一个映射表，按Review_ID组织内容和方面分析
          const contentMap: Record<number, {
            content: string,
            aspects: Array<{
              Aspect: string;
              Sentiment: string;
              Confidence: string;
              Reason: string;
            }>
          }> = {};
          
          // 从原始文本中建立 Review_ID 到内容的映射
          tableResult.original_texts.forEach((text, index) => {
            contentMap[index + 1] = {
              content: text,
              aspects: []
            };
          });
          
          // 打印调试信息
          console.log('Content map:', contentMap);
          
          // 为每个方面分析找到对应的内容
          // 假设方面分析的顺序与原始内容的顺序相关
          // 这里我们希望根据实际分析时的对应关系来分配方面
          let aspectIndex = 0;
          const contentCount = tableResult.original_texts.length;
          const aspectCount = tableResult.aspect_details.length;
          
          console.log(`内容数量: ${contentCount}, 方面数量: ${aspectCount}`);
          
          // 改进的分配算法
          if (contentCount === 1) {
            // 如果只有一个内容，将所有方面分配给它
            const reviewId = 1;
            tableResult.aspect_details.forEach(detail => {
              if (contentMap[reviewId]) {
                contentMap[reviewId].aspects.push({
                  Aspect: detail.aspect,
                  Sentiment: detail.sentiment,
                  Confidence: detail.confidence ? `${detail.confidence}%` : "0%",
                  Reason: detail.reason
                });
              }
            });
          } else {
            // 多个内容时，尽量平均分配方面
            const aspectsPerContent = Math.max(1, Math.floor(aspectCount / contentCount));
            console.log(`每个内容的方面数量: ${aspectsPerContent}`);
            
            // 第一次分配：确保每个内容至少有一个方面
            for (let reviewId = 1; reviewId <= contentCount && aspectIndex < aspectCount; reviewId++) {
              // 给每个内容分配指定数量的方面
              for (let i = 0; i < aspectsPerContent && aspectIndex < aspectCount; i++) {
                const detail = tableResult.aspect_details[aspectIndex++];
                if (contentMap[reviewId]) {
                  contentMap[reviewId].aspects.push({
                    Aspect: detail.aspect,
                    Sentiment: detail.sentiment,
                    Confidence: detail.confidence ? `${detail.confidence}%` : "0%",
                    Reason: detail.reason
                  });
                }
              }
            }
            
            // 分配剩余的方面（如果有）
            while (aspectIndex < aspectCount) {
              const detail = tableResult.aspect_details[aspectIndex++];
              // 分配给最后一个内容
              const lastReviewId = contentCount;
              if (contentMap[lastReviewId]) {
                contentMap[lastReviewId].aspects.push({
                  Aspect: detail.aspect,
                  Sentiment: detail.sentiment,
                  Confidence: detail.confidence ? `${detail.confidence}%` : "0%",
                  Reason: detail.reason
                });
              }
            }
          }
          
          // 将contentMap转换为directDisplayItems，确保包含所有内容
          Object.entries(contentMap).forEach(([reviewId, data]) => {
            // 即使没有方面分析，也添加内容
            directDisplayItems.push({
              Review_ID: parseInt(reviewId),
              Content: data.content,
              AspectAnalyses: data.aspects.length > 0 ? data.aspects : [{
                Aspect: "General Content",
                Sentiment: "neutral",
                Confidence: "100%",
                Reason: "No specific aspects detected in this content."
              }]
            });
          });
          
          // 打印最终的展示项目
          console.log('Final direct display items:', directDisplayItems);
          
          // 按Review_ID排序
          directDisplayItems.sort((a, b) => a.Review_ID - b.Review_ID);
        }
        
        // 统计分析了多少个独立的内容
        const uniqueContentCount = tableResult.original_texts ? tableResult.original_texts.length : 0;
        
        // 在控制台打印数据，方便调试
        console.log('Direct Display Items:', directDisplayItems);
        console.log('Unique Content Count:', uniqueContentCount);
        
        displayItems = directDisplayItems;
      }
      
      // 统计分析了多少个独立的内容
      const uniqueContentCount = tableResult.original_texts ? tableResult.original_texts.length : 0;
      
      // 在控制台打印数据，方便调试
      console.log('Direct Display Items:', displayItems);
      console.log('Unique Content Count:', uniqueContentCount);
      
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
          
          {/* Analysis Results Table - Direct CSV Format Display */}
          <div style={{ marginTop: '20px', marginBottom: '20px' }}>
            <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '10px' }}>
              Analysis Results: <span style={{ fontWeight: 'normal', color: '#666' }}>
                ({uniqueContentCount} original contents, 
                {tableResult.aspect_details ? tableResult.aspect_details.length : 0} aspect analyses)
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
                    <th style={{ padding: '12px', textAlign: 'center', borderBottom: '1px solid #E5E7EB', width: '90px' }}>Confidence</th>
                    <th style={{ padding: '12px', textAlign: 'left', borderBottom: '1px solid #E5E7EB' }}>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {displayItems.map((item, index) => {
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
                              {aspect.Confidence}
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
              window.open(`http://localhost:8001/api/transformer-sentiment/download/${tableResult.output_file}`, '_blank');
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
            <div style={{ color: 'rgba(0, 5, 9, 0.89)', fontSize: '24px', fontFamily: 'SF Pro', fontWeight: 590, wordWrap: 'break-word' }}>Transformer-based Sentiment Analysis</div>
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
                    👋 Welcome to the Transformer-based Sentiment Analysis Assistant!<br/>
                    I use advanced Transformer models to analyze the sentiment behind text — whether it's product reviews, customer feedback, tweets, or other messages.<br/><br/>
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