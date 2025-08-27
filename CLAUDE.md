# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Starting the Application
```bash
# Production/local startup
./start.sh

# Manual startup  
python3 server.py
```

### Dependencies
```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Database Operations
- Database initialization SQL scripts are in `sql/` directory (001-007 series)
- Execute in Supabase console in order: schema → basics → permissions → performance indexes
- Database client: `backend/db/client.py`, repository layer: `backend/db/repo.py`

## Architecture Overview

### System Architecture
```
Frontend (HTML/CSS/JS) → Flask Backend → Supabase/PostgreSQL → External APIs (arXiv, Doubao AI)
```

### Core Components

**Backend Services** (`backend/services/`):
- `analysis_service.py`: AI-powered paper analysis using Doubao models
- `arxiv_service.py`: arXiv paper import and data processing
- `affiliation_service.py`: Author affiliation extraction from PDFs
- `concurrent_analysis_service.py`: Concurrent processing management

**External Clients** (`backend/clients/`):
- `ai_client.py`: Doubao AI model integration (DoubaoClient)
- `arxiv_client.py`: arXiv API client for paper fetching

**Database Layer** (`backend/db/`):
- `client.py`: Supabase connection management
- `repo.py`: Data access layer with optimized queries and batch operations

**Frontend** (`frontend/`):
- Modular JavaScript architecture with separate files for search, analysis, progress tracking
- Real-time updates via Server-Sent Events (SSE)
- Responsive design supporting desktop and mobile

### Database Design
Core tables: `papers`, `categories`, `paper_categories`, `prompts`, `analysis_results`
- Optimized with composite indexes for high-performance queries
- Supports incremental analysis (avoids re-analyzing existing papers)
- Built-in caching layers (search: 5min TTL, import: 30min TTL, affiliations: permanent)

### AI Analysis System
- Uses Doubao-1.6-flash model for multi-modal LLM paper evaluation
- Scoring system: core features (2pts each) + bonus features (1pt each)
- Features evaluated: multi_modal, large_scale, unified_framework, novel_paradigm, new_benchmark, sota, etc.
- Pass threshold: standardized score ≥ 4

## Key APIs
- `POST /api/search_articles`: Import papers from arXiv
- `POST /api/analyze_papers`: Start AI analysis tasks (supports top5/10/20/full ranges)
- `GET /api/analysis_progress`: Real-time SSE progress updates
- `POST /api/get_analysis_results`: Retrieve analysis results
- `POST /api/fetch_affiliations`: Extract author institutions from PDFs

## Configuration
Environment variables (copy from `env.example`):
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: Database connection
- `DOUBAO_API_KEY`, `DOUBAO_MODEL`: AI model configuration
- `PORT`: Server port (default 8080, auto-detected on Render)

## Development Workflow
1. Papers are imported from arXiv API and stored with duplicate detection
2. AI analysis runs incrementally (only processes unanalyzed papers)
3. Successful analyses trigger automatic affiliation extraction
4. Results cached at multiple levels for performance
5. Frontend displays real-time progress via SSE streams

## Performance Features
- Batch database operations (50-100 records per batch)
- Intelligent caching preventing duplicate API calls
- Composite database indexes optimized for date/category queries
- Connection pooling and async processing support
- Query optimization with 3-5x speed improvements over file-based storage