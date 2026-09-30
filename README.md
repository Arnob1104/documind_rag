<img width="1321" height="600" alt="image" src="https://github.com/user-attachments/assets/62d5fa95-6263-4be7-871c-cf5d745fee56" />

# 🧠 DocuMind — AI Knowledge Base

> **An intelligent, searchable knowledge base that lets you upload, organize, search, and chat with your documents using AI.**

DocuMind combines **RAG, semantic search, PDF processing, and multi-agent AI** to turn your documents into an interactive knowledge base.

---

## ✨ Features

### 💬 Chat with Your Documents

Ask questions in natural language and get **AI-generated answers grounded in your own documents**, with relevant source citations.

### 🤖 Multi-Agent AI Assistant

Powered by **LangGraph**, DocuMind uses a supervisor-based architecture that intelligently routes requests between specialized agents:

* 🔎 **Retriever Agent** — Searches and retrieves relevant document content.
* 🏷️ **Tagger Agent** — Analyzes documents and generates relevant tags.
* 🧠 **Supervisor** — Determines which agent should handle each request.
* ✍️ **Responder** — Combines the retrieved information into a clear response.

### 🔍 Semantic Search

Search your knowledge base by **meaning, not just keywords**.

* Vector-based semantic search
* Similarity-based ranking
* Exact title matching
* PostgreSQL + pgvector
* PDF content extraction and indexing

### 📄 PDF Import

Upload PDF documents and automatically:

1. Extract their text
2. Process and chunk the content
3. Generate embeddings
4. Store searchable vectors
5. Make the documents available to the AI assistant

### 📝 Markdown Editor

Create and manage documents using a clean Markdown editing experience.

* Live preview
* Auto-save
* Markdown support
* Document organization
* Public/private visibility

### 🏷️ AI-Powered Tagging

Automatically generate meaningful tags for your documents using AI, making your knowledge base easier to organize and navigate.

### 🕒 Version History

Keep track of document changes with **version history snapshots**, allowing you to review previous versions of your documents.

---

## 🏗️ Architecture

```text
                         ┌──────────────────┐
                         │     User Query   │
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │ LangGraph        │
                         │   Supervisor     │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
          ┌──────────────────┐        ┌──────────────────┐
          │ Retriever Agent  │        │   Tagger Agent   │
          │                  │        │                  │
          │ Semantic Search  │        │ AI Tagging       │
          └────────┬─────────┘        └────────┬─────────┘
                   │                           │
                   └─────────────┬─────────────┘
                                 ▼
                       ┌──────────────────┐
                       │    Responder     │
                       │                  │
                       │ Grounded Answer  │
                       └──────────────────┘
```

---

## 🔄 Document Processing

```text
       PDF Upload
            │
            ▼
     Text Extraction
            │
            ▼
       Text Chunking
            │
            ▼
      Embeddings
            │
            ▼
     ┌──────────────┐
     │  PostgreSQL  │
     │   pgvector   │
     └──────┬───────┘
            │
            ▼
      Semantic Search
            │
            ▼
        AI Assistant
```

---

## 🛠️ Tech Stack

| Technology       | Purpose                          |
| ---------------- | -------------------------------- |
| **Next.js**      | Frontend & application framework |
| **React.js**     | UI components                    |
| **Tailwind CSS** | Styling & responsive UI          |
| **FastAPI**      | Backend API                      |
| **LangGraph**    | Multi-agent orchestration        |
| **RAG**          | Retrieval-augmented generation   |
| **pgvector**     | Vector similarity search         |
| **PostgreSQL**   | Database                         |
| **Groq**         | LLM inference                    |

---

## 🚀 Core Capabilities

* 📚 Personal AI knowledge base
* 📄 PDF document ingestion
* 🔎 Semantic document search
* 💬 Retrieval-augmented Q&A
* 🤖 Multi-agent AI workflow
* 🏷️ AI-generated document tags
* 📝 Markdown editing
* ⚡ Auto-save
* 🔐 Public/private documents
* 🕒 Document version history
* 📌 Source-grounded AI responses

---

## 🎯 Why DocuMind?

Traditional document storage makes you **search for information manually**.

DocuMind turns your documents into a **conversational knowledge base** where you can simply ask:

> *"What are the main conclusions from this document?"*

> *"Find everything related to authentication."*

> *"Which documents discuss database optimization?"*

> *"Tag this document based on its content."*

The AI retrieves relevant information from your documents and uses it to generate grounded responses.

---

## 📌 Project Overview

**DocuMind** is designed as an AI-powered knowledge management system that combines modern web development with **RAG and multi-agent architectures**.

The project demonstrates how documents can be transformed into a searchable, structured, and conversational knowledge base using **semantic retrieval and agent-based AI workflows**.

---

## 👨‍💻 Built With

**Next.js • React • Tailwind CSS • FastAPI • LangGraph • RAG • pgvector • PostgreSQL • Groq**

---

