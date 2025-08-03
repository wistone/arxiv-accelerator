import { useEffect, useRef } from 'react'
import { apiClient } from '@/lib/api'
import { useAppStore } from '@/stores/appStore'

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

// Helper function to format analysis result
const formatAnalysisResult = (analysisResult: string): string => {
  try {
    const result = JSON.parse(analysisResult)
    let formattedResult = ''
    
    if (result.pass_filter !== undefined) {
      formattedResult += `通过筛选: ${result.pass_filter ? '是' : '否'}\n`
    }
    if (result.raw_score !== undefined) {
      formattedResult += `原始分数: ${result.raw_score}\n`
    }
    if (result.norm_score !== undefined) {
      formattedResult += `标准化分数: ${result.norm_score}\n`
    }
    if (result.reason) {
      formattedResult += `原因: ${result.reason}\n`
    }
    if (result.exclude_reason) {
      formattedResult += `排除原因: ${result.exclude_reason}`
    }
    
    return formattedResult || JSON.stringify(result, null, 2)
  } catch {
    return analysisResult
  }
}

export const useSSE = () => {
  const eventSourceRef = useRef<EventSource | null>(null)
  const { 
    setAnalysisProgress, 
    setIsAnalyzing, 
    setAnalysisModalOpen,
    setCurrentAnalysisArticles,
    setSuccess,
    selectedDate,
    selectedCategory
  } = useAppStore()

  // Function to load analysis results after completion
  const loadAnalysisResults = async (rangeType: string) => {
    try {
      console.log('Loading analysis results for range:', rangeType)
      const response = await apiClient.getAnalysisResults(selectedDate, selectedCategory, rangeType)
      const data = response as { articles?: Article[], total?: number, is_analysis_failed?: boolean }
      
      console.log('Analysis results response:', data)
      
      if (data.is_analysis_failed) {
        console.error('Analysis failed:', data)
        setSuccess('分析失败，请重试')
      } else if (data.articles && data.articles.length > 0) {
        // Ensure articles have the correct structure for analysis mode
        const processedArticles = data.articles.map(article => ({
          ...article,
          filter_result: article.filter_result || '未知',
          raw_score: article.raw_score || 0,
          detailed_analysis: article.detailed_analysis || '无详细分析'
        }))
        
        setCurrentAnalysisArticles(processedArticles)
        setSuccess(`分析完成！共处理 ${data.total || processedArticles.length} 篇论文`)
        console.log('Analysis results loaded:', processedArticles.length, 'articles')
        console.log('Sample article:', processedArticles[0])
      } else {
        console.error('No articles found in analysis results')
        setSuccess('分析结果为空，请重试')
      }
    } catch (error) {
      console.error('Failed to load analysis results:', error)
      setSuccess('加载分析结果失败，请重试')
    }
  }

  const startProgress = (date: string, category: string, testCount?: string) => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close()
    }

    const url = `/api/analysis_progress?date=${date}&category=${category}&test_count=${testCount || ''}`
    console.log('Starting SSE with URL:', url)
    const eventSource = apiClient.createSSEConnection(url)
    eventSourceRef.current = eventSource

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('SSE received:', data)
        
        // Handle progress updates (similar to original implementation)
        if (data.current !== undefined && data.total !== undefined) {
          let statusText = `正在处理第 ${data.current} / ${data.total} 篇论文`
          if (data.success_count !== undefined || data.error_count !== undefined) {
            statusText += ` | 成功: ${data.success_count || 0}, 错误: ${data.error_count || 0}`
          }
          
          setAnalysisProgress({
            current: data.current,
            total: data.total,
            status: statusText,
            currentPaper: data.paper ? {
              title: `第${data.current}篇: ${data.paper.title}`,
              authors: data.paper.authors,
              abstract: data.paper.abstract,
              analysis: data.analysis_result ? formatAnalysisResult(data.analysis_result) : '正在分析...'
            } : undefined
          })
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error)
      }
    }

    // Handle completion event
    eventSource.addEventListener('complete', (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('Analysis complete:', data)
        setAnalysisProgress(null)
        setIsAnalyzing(false)
        
        // Load analysis results
        loadAnalysisResults(data.completed_range_type || 'full')
        
        // Close modal and navigate to results
        setTimeout(() => {
          setAnalysisModalOpen(false)
        }, 1000)
      } catch (error) {
        console.error('Error parsing complete event:', error)
      }
    })

    // Handle error event
    eventSource.addEventListener('error', (event) => {
      try {
        const messageEvent = event as MessageEvent
        if (messageEvent.data) {
          const data = JSON.parse(messageEvent.data)
          console.error('Analysis error event:', data)
        }
        setAnalysisProgress(null)
        setIsAnalyzing(false)
      } catch (error) {
        console.error('Error parsing error event:', error)
        setAnalysisProgress(null)
        setIsAnalyzing(false)
      }
    })

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