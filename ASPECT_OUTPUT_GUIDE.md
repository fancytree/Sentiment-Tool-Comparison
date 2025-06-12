# 🎯 方面分析输出格式指南

## 📋 概述

根据您的需求，我们已经优化了Transformer情感分析的输出格式，现在可以清晰地展示每个Aspect的Sentiment、Confidence和Reason。

## 🔧 新增功能

### 1. 专门的方面分析API端点

**新端点**: `/api/transformer-sentiment/aspects`

这个端点专门用于方面分析，返回格式化的结果，突出显示每个方面的详细信息。

### 2. 优化的CSV输出格式

文件分析现在为每个方面创建独立的列：
- `Aspect_1`, `Aspect_1_Sentiment`, `Aspect_1_Confidence`, `Aspect_1_Reason`
- `Aspect_2`, `Aspect_2_Sentiment`, `Aspect_2_Confidence`, `Aspect_2_Reason`
- 等等...

## 📊 API 使用示例

### 方面分析端点

**请求**:
```bash
curl -X POST https://your-backend-url/api/transformer-sentiment/aspects \
  -H "Content-Type: application/json" \
  -d '{"text":"The product quality is excellent but the price is too expensive. Customer service was very helpful."}'
```

**响应格式**:
```json
{
  "text": "The product quality is excellent but the price is too expensive. Customer service was very helpful.",
  "overall_analysis": {
    "sentiment": "positive",
    "confidence": 0.750,
    "reason": "Positive sentiment detected across quality, price, service. Analysis based on 16 words with positive emotional indicators."
  },
  "aspect_analysis": [
    {
      "aspect": "quality",
      "sentiment": "positive",
      "confidence": 0.850,
      "reason": "Positive sentiment detected for quality based on keywords: excellent"
    },
    {
      "aspect": "price",
      "sentiment": "negative",
      "confidence": 0.800,
      "reason": "Negative sentiment detected for price based on keywords: expensive"
    },
    {
      "aspect": "service",
      "sentiment": "positive",
      "confidence": 0.750,
      "reason": "Positive sentiment detected for service based on keywords: helpful"
    }
  ]
}
```

### 标准分析端点

**请求**:
```bash
curl -X POST https://your-backend-url/api/transformer-sentiment/ \
  -H "Content-Type: application/json" \
  -d '{"text":"Amazing features and great performance!"}'
```

**响应格式**:
```json
{
  "sentiment": "positive",
  "score": 0.900,
  "polarity": 0.900,
  "confidence": 0.900,
  "reason": "Positive sentiment detected across features, performance. Analysis based on 5 words with positive emotional indicators.",
  "aspects": [
    {
      "aspect": "features",
      "sentiment": "positive",
      "confidence": 0.900,
      "reason": "Positive sentiment detected for features based on keywords: amazing"
    },
    {
      "aspect": "performance",
      "sentiment": "positive",
      "confidence": 0.850,
      "reason": "Positive sentiment detected for performance based on keywords: great"
    }
  ]
}
```

## 📈 CSV文件分析输出

### 输入CSV格式
```csv
Review_ID,Title,Content
1,Product Review,The quality is excellent but price is high
2,Service Review,Customer service was very helpful and fast
```

### 输出CSV格式
```csv
Review_ID,Title,Content,Overall_Sentiment,Overall_Score,Overall_Confidence,Overall_Reason,Aspect_1,Aspect_1_Sentiment,Aspect_1_Confidence,Aspect_1_Reason,Aspect_2,Aspect_2_Sentiment,Aspect_2_Confidence,Aspect_2_Reason
1,Product Review,The quality is excellent but price is high,positive,0.75,0.75,"Positive sentiment detected across quality, price...",quality,positive,0.85,"Positive sentiment detected for quality based on keywords: excellent",price,negative,0.80,"Negative sentiment detected for price based on keywords: high"
2,Service Review,Customer service was very helpful and fast,positive,0.85,0.85,"Positive sentiment detected across service, delivery...",service,positive,0.90,"Positive sentiment detected for service based on keywords: helpful",delivery,positive,0.80,"Positive sentiment detected for delivery based on keywords: fast"
```

## 🎯 输出字段说明

### 整体分析字段
| 字段 | 说明 | 示例 |
|------|------|------|
| **Overall_Sentiment** | 整体情感倾向 | positive/negative/neutral |
| **Overall_Score** | 整体情感分数 | 0.85 |
| **Overall_Confidence** | 整体分析置信度 | 0.85 |
| **Overall_Reason** | 整体分析原因 | "Positive sentiment detected across quality, price..." |

### 方面分析字段
| 字段模式 | 说明 | 示例 |
|----------|------|------|
| **Aspect_N** | 第N个检测到的方面 | quality, price, service |
| **Aspect_N_Sentiment** | 该方面的情感倾向 | positive/negative/neutral |
| **Aspect_N_Confidence** | 该方面的分析置信度 | 0.85 |
| **Aspect_N_Reason** | 该方面的分析原因 | "Positive sentiment detected for quality..." |

## 🔍 支持的方面类型

系统自动识别以下方面：

| 方面 | 关键词示例 | 情感词汇示例 |
|------|-----------|-------------|
| **quality** | quality, build, material | excellent, poor, durable |
| **price** | price, cost, expensive | affordable, overpriced, value |
| **service** | service, support, customer | helpful, rude, responsive |
| **delivery** | delivery, shipping, fast | quick, slow, timely |
| **design** | design, appearance, style | beautiful, ugly, elegant |
| **usability** | easy, difficult, interface | simple, complex, convenient |
| **performance** | performance, speed, efficient | fast, slow, smooth |
| **features** | feature, function, capability | amazing, limited, useful |
| **packaging** | package, box, wrap | nice, poor, damaged |
| **size** | size, big, small | perfect, tiny, huge |

## 🚀 技术特点

### 1. 增强的方面情感分析
- **方面特定词汇**: 每个方面都有专门的正面/负面词汇库
- **权重优化**: 方面特定词汇权重更高（2.0），通用词汇权重较低（1.0）
- **否定词处理**: 智能处理"not good"等否定表达

### 2. 智能置信度计算
- 基于情感词汇数量和强度
- 方面特定分析提供更准确的置信度
- 范围：0.5-0.95

### 3. 详细原因说明
- 整体原因包含检测到的方面和词数统计
- 方面原因包含具体的关键词
- 支持中性情感的平衡性解释

## 📝 使用建议

### 1. 选择合适的端点
- **标准端点** (`/`): 适合需要完整API响应的应用
- **方面端点** (`/aspects`): 适合专注于方面分析的场景

### 2. 文件分析最佳实践
- 确保CSV文件包含文本内容列
- 支持的分隔符：分号(;)、逗号(,)
- 建议文本长度：10-500字符

### 3. 结果解读
- **置信度 > 0.8**: 高可信度结果
- **置信度 0.6-0.8**: 中等可信度结果
- **置信度 < 0.6**: 建议人工复核

## 🎉 总结

新的输出格式提供了：

- 🎯 **清晰的方面展示** - 每个Aspect独立显示Sentiment、Confidence、Reason
- 📊 **结构化输出** - JSON和CSV格式都经过优化
- 🔍 **详细的分析原因** - 可解释的AI分析结果
- ⚡ **高效的API设计** - 专门的方面分析端点
- 📈 **实用的CSV格式** - 便于数据分析和可视化

这使得方面分析结果更加直观、详细和实用！ 