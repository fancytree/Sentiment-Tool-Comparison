import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom'
import { Theme, Box, Button, Heading, Text, Flex, Card } from '@radix-ui/themes'
import { ChatBubbleIcon, ImageIcon, MagicWandIcon } from '@radix-ui/react-icons'
import '@radix-ui/themes/styles.css'
import './styles/toast.css'

import TransformerSentiment from './pages/TransformerSentiment'
import LLMSentiment from './pages/LLMSentiment'
import GeneralAnalysis from './pages/GeneralAnalysis'
import { ToastProvider } from './components/Toast'

// 顶部导航栏组件
function TopBar() {
  return (
    <Flex 
      style={{ 
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        padding: '12px 36px',
        background: 'white',
        justifyContent: 'space-between',
        alignItems: 'center',
        display: 'inline-flex'
      }}
    >
      <div style={{ 
        color: 'black', 
        fontSize: '36px', 
        fontFamily: 'League Spartan', 
        fontWeight: 700, 
        wordWrap: 'break-word'
      }}>
        ai.meichai
      </div>
      <div style={{ 
        height: '40px',
        paddingLeft: '16px',
        paddingRight: '16px',
        background: '#F76B15',
        borderRadius: '6px',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '12px',
        display: 'flex'
      }}>
        <div style={{ 
          justifyContent: 'center',
          display: 'flex',
          flexDirection: 'column',
          color: 'white',
          fontSize: '16px',
          fontFamily: 'SF Pro',
          fontWeight: 510,
          lineHeight: '24px',
          wordWrap: 'break-word'
        }}>
          Contact
        </div>
      </div>
    </Flex>
  )
}

// 主要内容区域组件
function HeroSection() {
  return (
    <div style={{ 
      alignSelf: 'stretch',
      paddingTop: '120px',
      paddingBottom: '60px',
      paddingLeft: '48px',
      paddingRight: '48px',
      justifyContent: 'center',
      alignItems: 'center',
      gap: '32px',
      display: 'inline-flex'
    }}>
      <div style={{ 
        flex: '1 1 0',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '24px',
        display: 'inline-flex'
      }}>
        <div style={{ 
          justifyContent: 'center',
          display: 'flex',
          flexDirection: 'column',
          color: 'rgba(0, 5, 9, 0.89)',
          fontSize: '64px',
          fontFamily: 'SF Pro',
          fontWeight: 400,
          lineHeight: '64px',
          wordWrap: 'break-word'
        }}>
          AI Demo Showcase Platform
        </div>
      </div>
    </div>
  )
}

function CardDemo({ icon, title, description, onClick }: { 
  icon: React.ReactNode, 
  title: string, 
  description: string,
  onClick: () => void 
}) {
  return (
    <div 
      onClick={onClick}
      style={{ 
        flex: '1 1 0',
        minWidth: '320px',
        padding: '24px',
        background: 'rgba(255, 255, 255, 0.80)',
        overflow: 'hidden',
        borderRadius: '12px',
        outline: '1px rgba(0, 0, 47, 0.15) solid',
        outlineOffset: '-1px',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        alignItems: 'flex-start',
        gap: '24px',
        display: 'inline-flex',
        cursor: 'pointer'
      }}
    >
      <div style={{ 
        alignSelf: 'stretch',
        overflow: 'hidden',
        justifyContent: 'flex-start',
        alignItems: 'center',
        gap: '12px',
        display: 'inline-flex'
      }}>
        <div style={{ 
          flex: '1 1 0',
          flexDirection: 'column',
          justifyContent: 'flex-start',
          alignItems: 'center',
          display: 'inline-flex'
        }}>
          <div style={{ 
            alignSelf: 'stretch',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '8px',
            display: 'inline-flex'
          }}>
            {icon}
            <div style={{ 
              flex: '1 1 0',
              color: '#1C2024',
              fontSize: '18px',
              fontFamily: 'SF Pro',
              fontWeight: 510,
              lineHeight: '26px',
              wordWrap: 'break-word'
            }}>
              {title}
            </div>
          </div>
          <div style={{ 
            alignSelf: 'stretch',
            color: 'rgba(0, 7, 20, 0.62)',
            fontSize: '16px',
            fontFamily: 'SF Pro',
            fontWeight: 400,
            lineHeight: '24px',
            wordWrap: 'break-word'
          }}>
            {description}
          </div>
        </div>
      </div>
      <div style={{ 
        alignSelf: 'stretch',
        height: '40px',
        paddingLeft: '16px',
        paddingRight: '16px',
        background: '#F76B15',
        borderRadius: '6px',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '12px',
        display: 'inline-flex',
        cursor: 'pointer'
      }}>
        <div style={{ 
          justifyContent: 'center',
          display: 'flex',
          flexDirection: 'column',
          color: 'white',
          fontSize: '16px',
          fontFamily: 'SF Pro',
          fontWeight: 510,
          lineHeight: '24px',
          wordWrap: 'break-word'
        }}>
          Open Demo
        </div>
      </div>
    </div>
  )
}

// Demo 展示区域组件
function DemoSection({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ 
      alignSelf: 'stretch',
      paddingLeft: '48px',
      paddingRight: '48px',
      flexDirection: 'column',
      justifyContent: 'flex-start',
      alignItems: 'center',
      gap: '10px',
      display: 'flex'
    }}>
      <div style={{ 
        width: '100%',
        maxWidth: '1200px',
        padding: '80px 48px',
        background: 'white',
        flexDirection: 'column',
        justifyContent: 'flex-start',
        alignItems: 'center',
        gap: '24px',
        display: 'flex'
      }}>
        <div style={{ 
          alignSelf: 'stretch',
          textAlign: 'center',
          color: 'rgba(0, 5, 9, 0.89)',
          fontSize: '24px',
          fontFamily: 'SF Pro',
          fontWeight: 274,
          wordWrap: 'break-word'
        }}>
          This is my personal AI demo hub — lightweight, interactive. Try out each demo below.
        </div>
        <div style={{ 
          alignSelf: 'stretch',
          justifyContent: 'flex-start',
          alignItems: 'flex-start',
          gap: '24px',
          display: 'inline-flex',
          flexWrap: 'wrap',
          alignContent: 'flex-start'
        }}>
          {children}
        </div>
      </div>
    </div>
  )
}

function HomePage() {
  const navigate = useNavigate()
  
  return (
    <div style={{ 
      width: '100%',
      height: '100%',
      overflow: 'hidden',
      flexDirection: 'column',
      justifyContent: 'flex-start',
      alignItems: 'center',
      gap: '10px',
      display: 'inline-flex',
      paddingTop: '64px'
    }}>
      <TopBar />
      <HeroSection />
      <DemoSection>
        <CardDemo
          icon={<MagicWandIcon width={16} height={16} />}
          title="General Sentiment Analysis"
          description="Sentiment analysis using traditional NLP techniques"
          onClick={() => navigate('/sentiment')}
        />
        <CardDemo
          icon={<ChatBubbleIcon width={16} height={16} />}
          title="Transformer-based Sentiment Analysis"
          description="Advanced sentiment analysis powered by transformer models"
          onClick={() => navigate('/transformer')}
        />
        <CardDemo
          icon={<ImageIcon width={16} height={16} />}
          title="Large Language Models Sentiment Analysis"
          description="State-of-the-art sentiment analysis using large language models"
          onClick={() => navigate('/llm')}
        />
      </DemoSection>
    </div>
  )
}

function App() {
  return (
    <Theme>
      <ToastProvider>
        <Router>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/transformer" element={<TransformerSentiment />} />
            <Route path="/llm" element={<LLMSentiment />} />
            <Route path="/sentiment" element={<GeneralAnalysis />} />
          </Routes>
        </Router>
      </ToastProvider>
    </Theme>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
) 