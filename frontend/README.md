# 📚 Arxiv Accelerator - Modern Frontend

Modern React + shadcn/ui frontend for the Arxiv paper analysis assistant.

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ 
- npm or yarn
- Backend server running on `http://localhost:8080`

### Installation & Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`

### Production Build

```bash
# Build for production
npm run build

# Start production server  
npm start
```

## 🏗️ Architecture

### Technology Stack
- **React 18** with TypeScript
- **Next.js 14** (App Router)
- **shadcn/ui** for modern, accessible components
- **Tailwind CSS** for styling
- **Tanstack Query** for server state management
- **Zustand** for client state management

### Project Structure
```
src/
├── app/                    # Next.js app router
├── components/             # React components
│   ├── ui/                # shadcn/ui components
│   ├── layout/            # Layout components
│   ├── search/            # Search functionality
│   ├── analysis/          # Analysis features
│   ├── table/             # Table components
│   └── common/            # Shared components
├── hooks/                 # Custom React hooks
├── stores/                # Zustand stores
└── lib/                   # Utilities and API client
```

## 🔧 Features

### ✅ Implemented
- **Modern UI**: Clean, responsive design with shadcn/ui components
- **Paper Search**: Date and category selection with enhanced UX
- **Real-time Analysis**: Progress tracking with Server-Sent Events
- **Interactive Tables**: Sortable analysis results
- **State Management**: Efficient global state with Zustand
- **API Integration**: Complete Flask backend integration
- **Responsive Design**: Mobile-friendly interface

### 🎯 Key Components

| Component | Purpose |
|-----------|---------|
| `SearchControls` | Date picker and category selection |
| `ArticlesTable` | Display and sort paper results |
| `AnalysisModal` | Real-time analysis progress |
| `StatusMessages` | Error and success notifications |
| `Container` | Dynamic layout switching |

## 🔄 Backend Integration

### API Endpoints
- `POST /api/search_articles` - Search papers
- `POST /api/analyze_papers` - Start analysis
- `GET /api/analysis_progress` - SSE progress stream
- `POST /api/get_analysis_results` - Fetch results

### State Synchronization
- Real-time progress via Server-Sent Events
- Automatic result caching and loading
- URL state management for bookmarkable links

## 🎨 UI Features

### Enhanced Components
- **Calendar Picker**: Better date selection UX
- **Progress Tracking**: Visual analysis progress
- **Sortable Tables**: Click headers to sort results
- **Modal Workflows**: Streamlined analysis process
- **Responsive Layout**: Adaptive width for analysis mode

### Design Consistency
- Maintains original layout structure
- Preserves all existing functionality
- Enhanced visual hierarchy
- Improved accessibility

## 🧪 Development

### Running with Backend
1. Start the Flask backend: `python server.py` (port 8080)
2. Start the frontend: `npm run dev` (port 3000)
3. Navigate to `http://localhost:3000`

### Environment Variables
```bash
# .env.local (optional)
NODE_ENV=development
```

## 📦 Deployment

### With Backend
1. Build the frontend: `npm run build`
2. Serve static files through Flask or separate server
3. Update API_BASE_URL for production

### Standalone
1. Configure proxy in `next.config.ts` for API calls
2. Deploy to Vercel, Netlify, or any static host

## 🎯 Next Steps

1. **Performance**: Add React.lazy() for code splitting
2. **Testing**: Add Jest + React Testing Library
3. **Accessibility**: Enhanced keyboard navigation
4. **PWA**: Add service worker for offline support
5. **Themes**: Dark mode support

---

*Modern React frontend with shadcn/ui components while preserving original functionality* ✨