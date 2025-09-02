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
- **Modular JavaScript architecture**: 
  - `search.js`: Standard date/category search functionality
  - `smart-search.js`: Smart search using arXiv IDs from text
  - `analysis.js`: Analysis result display and management  
  - `progress.js`: Real-time SSE progress tracking
  - `url.js`: URL state management for shareable analysis links
  - `table.js`: Dynamic table rendering and sorting
  - `ui.js`: UI components and modal management
- **Real-time updates**: Server-Sent Events (SSE) with fallback mechanisms
- **State management**: URL-based state for shareable analysis sessions
- **Responsive design**: Desktop and mobile optimized interface

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

### Standard Search & Analysis
- `POST /api/search_articles`: Import papers from arXiv by date/category
- `POST /api/analyze_papers`: Start AI analysis tasks (supports top5/10/20/full ranges)
- `POST /api/get_analysis_results`: Retrieve analysis results
- `POST /api/check_analysis_exists`: Check analysis status for date/category

### Smart Search & Analysis
- `POST /api/smart_search`: Import papers from arXiv using text with arXiv IDs
- `POST /api/analyze_papers_by_ids`: Start analysis for specific paper IDs
- `POST /api/get_analysis_results_by_ids`: Retrieve results for specific paper IDs
- `POST /api/check_analysis_exists_by_ids`: Check analysis status for paper IDs

### Real-time Progress & Utilities
- `GET /api/analysis_progress`: Real-time SSE progress updates (supports task_id parameter)
- `POST /api/fetch_affiliations`: Extract author institutions from PDFs
- `GET /api/available_dates`: Get available paper dates for date picker

## Configuration
Environment variables (copy from `env.example`):
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`: Database connection
- `DOUBAO_API_KEY`, `DOUBAO_MODEL`: AI model configuration
- `PORT`: Server port (default 8080, auto-detected on Render)

## Core Features

### Search Modes
1. **Standard Search**: Query by date and category (cs.CV, cs.LG, cs.AI)
2. **Smart Search**: Extract arXiv IDs from text content (supports copy-paste from papers/websites)

### Analysis Features
- **Incremental Analysis**: Only analyzes unprocessed papers
- **Flexible Scope**: Support for top5/top10/top20/full analysis ranges
- **Real-time Progress**: Live updates with concurrent processing status
- **Author Affiliations**: Automatic PDF extraction for approved papers
- **Result Caching**: Multi-level caching prevents duplicate work

### User Experience
- **URL State Management**: Shareable analysis sessions via URLs
- **Responsive Tables**: Sortable columns with expand/collapse details
- **Excel-style Filtering**: Column-based date filtering for smart search results
- **Progress Tracking**: Real-time SSE updates with fallback mechanisms

## Development Workflow
1. Papers are imported from arXiv API and stored with duplicate detection
2. AI analysis runs incrementally (only processes unanalyzed papers)
3. Successful analyses trigger automatic affiliation extraction
4. Results cached at multiple levels for performance
5. Frontend displays real-time progress via SSE streams
6. URL state enables shareable analysis sessions

## Performance Features
- Batch database operations (50-100 records per batch)
- Intelligent caching preventing duplicate API calls
- Composite database indexes optimized for date/category queries
- Connection pooling and async processing support
- Query optimization with 3-5x speed improvements over file-based storage

## Development Notes

### Code Quality
- Minimal debug logging in production (cleaned up SSE and smart search logs)
- Modular JavaScript architecture with clear separation of concerns
- Error handling with user-friendly messages and fallback mechanisms

### Testing & Debugging
- Use browser developer tools to monitor network requests
- Server logs provide detailed analysis progress and error information
- SSE connection status visible in Network tab during analysis

### Common Issues & Solutions
- **Button appears disabled**: Check analysis status - may already be completed
- **SSE connection drops**: Fallback polling mechanism auto-activates after 60s
- **Analysis hangs**: Check server logs for API rate limits or network issues
- **Missing affiliations**: PDF extraction requires successful analysis first

### Best Practices
- Always use incremental analysis to avoid duplicate work
- Monitor server resources during large batch analyses
- Use appropriate analysis scope (top5/10/20) for testing
- Keep environment variables secure and up-to-date