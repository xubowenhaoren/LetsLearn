# LetsLearn

[English](README.md) | 中文

企业级 AI 知识库管理系统 + Duolingo 风格 AI 学习 Agent，采用 RAG 技术。

## LetsLaern: AI 学习 Agent

- **智能 Quiz 生成**：上传教材 PDF → LangGraph Agent 识别知识点 → 15 路并行生成选择题卡片（~14s）
- **交互式学习**：AI 精讲 + 选择题 + 即时反馈，Duolingo 风格翻页
- **长期记忆**：MySQL 持久化答题记录和错题，跨 session 不遗忘。重新生成 quiz 自动注入历史错题
- **AI 助手侧边栏**：划词搜索，选中文字即可向 RAG Agent 提问
- **Quiz 历史**：双层列表浏览器 + 预览面板，完整回放
- **实时进度**：SSE 流式推送

> **Agent 技术栈**: Python FastAPI + LangGraph (Send fan-out) + DeepSeek + MySQL + Elasticsearch

## 功能介绍

- 根据PDF自动生成学习内容精讲和测验题目
![](images/quiz-generation.png)

- 遇到不会做的题，可以用AI侧边栏直接问RAG Agent
![](images/chat-sidebar.png)

- 做错了题不理解？没关系，AI提供讲解
![](images/quiz-feedback.png)

- 做完quiz想回看？没问题。OneNote风格quiz记录管理，操作直观
![](images/quiz-history.png)

- 想复习quiz？AI自动读取错题记录，加深印象
![](images/mistake-review.png)

## 技术栈

**后端**: Spring Boot 3.4 + Java 17 + MySQL + Redis + Elasticsearch + Kafka + MinIO + WebSocket + Spring Security + JWT

**前端**: Vue 3 + TypeScript + Vite + Naive UI + Pinia

**Python Agent**: FastAPI + LangGraph + elasticsearch-py + httpx

## 部署

```bash
# 1. 启动基础服务
cd docs && docker compose up -d

# 2. 配置
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY 和 EMBEDDING_API_KEY

# 3. 后端
mvn spring-boot:run

# 4. Python Agent (Quiz 生成)
cd learning-agent && python3 -m venv venv && source venv/bin/activate
pip install elasticsearch fastapi uvicorn langgraph langgraph-checkpoint httpx pydantic
uvicorn main:app --port 8000

# 5. 前端
cd frontend && pnpm install && pnpm dev
```

## 核心功能

- **文档管理**：分片上传 + 断点续传，Kafka 异步解析（LiteParse OCR + Tika），ES 混合搜索（KNN + BM25）
- **AI 聊天**：DeepSeek ReAct Agent，WebSocket 流式响应，来源引用 + 文档预览定位
- **Quiz 学习**：LangGraph Send fan-out 并行生成，SQL 长期记忆，跨 session 错题回顾
- **多租户**：组织标签 + 权限过滤，用户数据隔离
