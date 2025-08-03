import { create } from 'zustand'

interface Article {
  number: number
  id: string
  title: string
  authors: string
  abstract: string
  arxiv_url: string
  pdf_url: string
  published_date: string
  filter_result?: string
  raw_score?: number
  detailed_analysis?: string
}

interface AnalysisProgress {
  current: number
  total: number
  status: string
  currentPaper?: {
    title: string
    authors: string
    abstract: string
    analysis: string
  }
}

interface AppState {
  // Search state
  selectedDate: string
  selectedCategory: string
  currentArticles: Article[]
  hasSearched: boolean
  
  // Analysis state
  currentAnalysisArticles: Article[]
  sortColumn: string
  sortDirection: 'asc' | 'desc'
  
  // UI state
  isAnalysisModalOpen: boolean
  isLoading: boolean
  error: string | null
  success: string | null
  
  // Progress tracking
  analysisProgress: AnalysisProgress | null
  isAnalyzing: boolean
  
  // Actions
  setSelectedDate: (date: string) => void
  setSelectedCategory: (category: string) => void
  setCurrentArticles: (articles: Article[]) => void
  setHasSearched: (searched: boolean) => void
  setCurrentAnalysisArticles: (articles: Article[]) => void
  setSortColumn: (column: string) => void
  setSortDirection: (direction: 'asc' | 'desc') => void
  setAnalysisModalOpen: (open: boolean) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  setSuccess: (success: string | null) => void
  setAnalysisProgress: (progress: AnalysisProgress | null) => void
  setIsAnalyzing: (analyzing: boolean) => void
  clearMessages: () => void
}

export const useAppStore = create<AppState>((set) => ({
  // Initial state
  selectedDate: new Date().toISOString().split('T')[0],
  selectedCategory: 'cs.CV',
  currentArticles: [],
  hasSearched: false,
  currentAnalysisArticles: [],
  sortColumn: '',
  sortDirection: 'asc',
  isAnalysisModalOpen: false,
  isLoading: false,
  error: null,
  success: null,
  analysisProgress: null,
  isAnalyzing: false,
  
  // Actions
  setSelectedDate: (date) => set({ selectedDate: date }),
  setSelectedCategory: (category) => set({ selectedCategory: category }),
  setCurrentArticles: (articles) => set({ currentArticles: articles }),
  setHasSearched: (searched) => set({ hasSearched: searched }),
  setCurrentAnalysisArticles: (articles) => set({ currentAnalysisArticles: articles }),
  setSortColumn: (column) => set({ sortColumn: column }),
  setSortDirection: (direction) => set({ sortDirection: direction }),
  setAnalysisModalOpen: (open) => set({ isAnalysisModalOpen: open }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error: error }),
  setSuccess: (success) => set({ success: success }),
  setAnalysisProgress: (progress) => set({ analysisProgress: progress }),
  setIsAnalyzing: (analyzing) => set({ isAnalyzing: analyzing }),
  clearMessages: () => set({ error: null, success: null }),
}))