import { useMutation, useQuery } from '@tanstack/react-query'
import { apiClient } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'

// Define Article type to match the one in stores/appStore.ts
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

export const useSearchArticles = () => {
  const { setCurrentArticles, setHasSearched, setLoading, setError, setSuccess, clearMessages } = useAppStore()
  
  return useMutation({
    mutationFn: ({ date, category }: { date: string; category: string }) =>
      apiClient.searchArticles(date, category) as Promise<{ articles: Article[]; total: number }>,
    onMutate: () => {
      setLoading(true)
      clearMessages()
    },
    onSuccess: (data: { articles: Article[]; total: number }) => {
      setCurrentArticles(data.articles)
      setHasSearched(true)
      setSuccess(`Successfully loaded ${data.total} articles for ${data.articles[0]?.published_date || ''}`)
      setLoading(false)
    },
    onError: (error: Error) => {
      setError(error.message || 'Search failed')
      setHasSearched(false)
      setLoading(false)
    },
  })
}

export const useCheckAnalysisExists = () => {
  return useMutation({
    mutationFn: ({ date, category }: { date: string; category: string }) =>
      apiClient.checkAnalysisExists(date, category) as Promise<{ exists: boolean }>,
  })
}

export const useAnalyzeArticles = () => {
  const { setIsAnalyzing, setError } = useAppStore()
  
  return useMutation({
    mutationFn: ({ date, category, testCount }: { 
      date: string; 
      category: string; 
      testCount?: string 
    }) => apiClient.analyzeArticles(date, category, testCount) as Promise<{ success?: boolean }>,
    onMutate: () => {
      setIsAnalyzing(true)
    },
    onError: (error: Error) => {
      setError(error.message || 'Analysis start failed')
      setIsAnalyzing(false)
    },
  })
}

export const useGetAnalysisResults = () => {
  const { setCurrentAnalysisArticles, setLoading, setError } = useAppStore()
  
  return useMutation({
    mutationFn: ({ date, category, testCount }: { 
      date: string; 
      category: string; 
      testCount?: string 
    }) => apiClient.getAnalysisResults(date, category, testCount) as Promise<{ articles?: Article[] }>,
    onMutate: () => {
      setLoading(true)
    },
    onSuccess: (data: { articles?: Article[] }) => {
      setCurrentAnalysisArticles(data.articles || [])
      setLoading(false)
    },
    onError: (error: Error) => {
      setError(error.message || 'Failed to get analysis results')
      setLoading(false)
    },
  })
}

export const useAvailableDates = () => {
  return useQuery({
    queryKey: ['availableDates'],
    queryFn: () => apiClient.getAvailableDates() as Promise<{ dates: string[] }>,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}