import { useEffect, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'

export const useSSE = () => {
  const eventSourceRef = useRef<EventSource | null>(null)
  const { 
    setAnalysisProgress, 
    setIsAnalyzing, 
    setCurrentAnalysisArticles,
    setAnalysisModalOpen
  } = useAppStore()

  const startProgress = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const eventSource = apiClient.createSSEConnection('/api/analysis_progress')
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'progress') {
          setAnalysisProgress({
            current: data.current || 0,
            total: data.total || 0,
            status: data.status || 'Processing...',
            currentPaper: data.current_paper ? {
              title: data.current_paper.title,
              authors: data.current_paper.authors,
              abstract: data.current_paper.abstract,
              analysis: data.current_paper.analysis || 'Analyzing...'
            } : undefined
          })
        } else if (data.type === 'complete') {
          setAnalysisProgress(null)
          setIsAnalyzing(false)
          
          // Load the completed analysis results
          if (data.articles) {
            setCurrentAnalysisArticles(data.articles)
          }
          
          // Close the modal after a short delay
          setTimeout(() => {
            setAnalysisModalOpen(false)
          }, 2000)
        } else if (data.type === 'error') {
          setAnalysisProgress(null)
          setIsAnalyzing(false)
          console.error('Analysis error:', data.message)
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error)
      setAnalysisProgress(null)
      setIsAnalyzing(false)
      eventSource.close()
    }

    return eventSource
  }

  const stopProgress = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
      eventSourceRef.current = null
    }
    setAnalysisProgress(null)
    setIsAnalyzing(false)
  }

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close()
      }
    }
  }, [])

  return {
    startProgress,
    stopProgress,
  }
}