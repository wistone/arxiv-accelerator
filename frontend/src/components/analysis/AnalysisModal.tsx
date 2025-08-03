import React, { useState } from 'react'

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
import { Button } from '@/components/ui/button'
import { 
  Dialog, 
  DialogContent, 
  DialogDescription,
  DialogHeader, 
  DialogTitle 
} from '@/components/ui/dialog'
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select'
import { Progress } from '@/components/ui/progress'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAppStore } from '@/stores/appStore'
import { useAnalyzeArticles, useCheckAnalysisExists, useGetAnalysisResults } from '@/hooks/useApi'
import { useSSE } from '@/hooks/useSSE'

export const AnalysisModal = () => {
  const { 
    isAnalysisModalOpen, 
    setAnalysisModalOpen, 
    selectedDate, 
    selectedCategory,
    analysisProgress,
    isAnalyzing,
    clearMessages 
  } = useAppStore()
  
  const [testCount, setTestCount] = useState<string>('all')
  const [analysisStatus, setAnalysisStatus] = useState<string>('')
  const [availableOptions, setAvailableOptions] = useState<string[]>(['all', '5', '10', '20'])
  const [existingFiles, setExistingFiles] = useState<{ range_desc: string, filename: string }[]>([])
  
  const analyzeMutation = useAnalyzeArticles()
  const checkExistsMutation = useCheckAnalysisExists()
  const getResultsMutation = useGetAnalysisResults()
  const { startProgress, stopProgress } = useSSE()

  // Check for existing analysis when modal opens
  React.useEffect(() => {
    if (isAnalysisModalOpen && selectedDate && selectedCategory) {
      checkExistingAnalysis()
    }
  }, [isAnalysisModalOpen, selectedDate, selectedCategory]) // eslint-disable-line react-hooks/exhaustive-deps

  const checkExistingAnalysis = async () => {
    try {
      console.log('Checking for existing analysis...')
      const result = await checkExistsMutation.mutateAsync({
        date: selectedDate,
        category: selectedCategory
      })
      
      const data = result as { exists?: boolean, available_options?: string[], existing_files?: { range_desc: string, filename: string }[] }
      
      if (data.exists && data.available_options) {
        // Update available options based on existing analysis
        setAvailableOptions(data.available_options)
        setExistingFiles(data.existing_files || [])
        
        // Update analysis status
        let statusText = '📋 发现已有分析结果：\n'
        data.existing_files?.forEach(file => {
          statusText += `• ${file.range_desc} (${file.filename})\n`
        })
        statusText += '\n💡 提示：您可以选择加载现有结果或重新生成更大范围的分析。'
        setAnalysisStatus(statusText)
      } else {
        // No existing analysis, show default options
        setAvailableOptions(['all', '5', '10', '20'])
        setExistingFiles([])
        setAnalysisStatus('')
      }
    } catch (error) {
      console.log('检查分析文件时出错，继续进行新分析:', error)
      setAvailableOptions(['all', '5', '10', '20'])
      setExistingFiles([])
      setAnalysisStatus('')
    }
  }

  const handleClose = () => {
    stopProgress()
    setAnalysisModalOpen(false)
    clearMessages()
    // Reset state
    setAvailableOptions(['all', '5', '10', '20'])
    setExistingFiles([])
    setAnalysisStatus('')
    setTestCount('all')
  }

  const handleStartAnalysis = async () => {
    // Safety checks
    if (!selectedDate || !selectedCategory) {
      setAnalysisStatus('请先选择日期和分类')
      return
    }
    
    try {
      console.log('Starting analysis with:', { selectedDate, selectedCategory, testCount })
      setAnalysisStatus('正在启动分析...')
      
      const actualTestCount = testCount === 'all' ? '' : testCount
      const rangeType = testCount === 'all' ? 'full' :
                      testCount === '5' ? 'top5' :
                      testCount === '10' ? 'top10' :
                      testCount === '20' ? 'top20' : 'full'
      
      // First try to load existing results
      try {
        console.log('尝试加载现有结果...', rangeType)
        const existingResult = await getResultsMutation.mutateAsync({
          date: selectedDate,
          category: selectedCategory,
          testCount: actualTestCount
        })
        
        const existingData = existingResult as { articles?: Article[], total?: number, is_analysis_failed?: boolean }
        
        if (existingData.articles && existingData.articles.length > 0) {
          // Existing results found, close modal and show results
          console.log('找到现有结果，加载中...')
          setAnalysisStatus('加载现有分析结果...')
          setTimeout(() => {
            handleClose()
          }, 1000)
          return
        }
      } catch (error) {
        console.log('没有找到现有结果，开始新分析:', error)
      }
      
      // No existing results, start new analysis
      const result = await analyzeMutation.mutateAsync({
        date: selectedDate,
        category: selectedCategory,
        testCount: actualTestCount
      }) as { success?: boolean }
      
      console.log('Analysis result:', result)
      
      if (result.success) {
        // Start SSE progress tracking with the required parameters
        startProgress(selectedDate, selectedCategory, actualTestCount)
        setAnalysisStatus('分析已启动，正在跟踪进度...')
      } else {
        setAnalysisStatus('分析启动失败')
      }
    } catch (error) {
      console.error('Analysis error:', error)
      setAnalysisStatus('启动分析失败，请重试')
    }
  }

  const getProgressPercentage = () => {
    if (!analysisProgress || analysisProgress.total === 0) return 0
    return Math.round((analysisProgress.current / analysisProgress.total) * 100)
  }

  // Don't render if modal is not open to avoid potential issues
  if (!isAnalysisModalOpen) {
    return null
  }

  return (
    <Dialog open={isAnalysisModalOpen} onOpenChange={setAnalysisModalOpen}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold">
            论文分析进度
          </DialogTitle>
          <DialogDescription>
            配置和跟踪论文分析的进度。
          </DialogDescription>
        </DialogHeader>

        {!isAnalyzing && !analysisProgress && (
          <div className="space-y-6">
            {/* Analysis Options */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">分析范围选择</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {availableOptions.length > 1 ? (
                  <Select value={testCount} onValueChange={setTestCount}>
                    <SelectTrigger>
                      <SelectValue placeholder="选择分析范围" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableOptions.map(option => (
                        <SelectItem key={option} value={option}>
                          {option === 'all' ? '全部分析' :
                           option === '5' ? '仅前5篇' :
                           option === '10' ? '仅前10篇' :
                           option === '20' ? '仅前20篇' : option}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="text-sm text-muted-foreground">
                    可用分析范围: {availableOptions[0] === 'all' ? '全部分析' :
                    availableOptions[0] === '5' ? '仅前5篇' :
                    availableOptions[0] === '10' ? '仅前10篇' :
                    availableOptions[0] === '20' ? '仅前20篇' : availableOptions[0]}
                  </div>
                )}
                
                <div className="flex gap-3">
                  <Button 
                    onClick={handleStartAnalysis}
                    disabled={analyzeMutation.isPending}
                  >
                    开始分析
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    onClick={handleClose}
                  >
                    取消
                  </Button>
                </div>
                {analysisStatus && (
                  <div className="text-sm text-muted-foreground mt-2 whitespace-pre-line">
                    {analysisStatus}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* Progress Display */}
        {(isAnalyzing || analysisProgress) && (
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>分析进度</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>进度: {analysisProgress?.current || 0} / {analysisProgress?.total || 0}</span>
                    <span>{getProgressPercentage()}%</span>
                  </div>
                  <Progress value={getProgressPercentage()} className="w-full" />
                </div>
                
                <div className="text-sm text-muted-foreground">
                  {analysisProgress?.status || '准备开始分析...'}
                </div>
              </CardContent>
            </Card>

            {/* Current Paper */}
            {analysisProgress?.currentPaper && (
                          <Card>
              <CardHeader>
                <CardTitle className="text-lg">当前正在分析的论文</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <h4 className="font-semibold text-foreground">
                    {analysisProgress.currentPaper.title}
                  </h4>
                </div>
                
                <div>
                  <span className="font-medium">作者: </span>
                  <span className="text-muted-foreground">
                    {analysisProgress.currentPaper.authors}
                  </span>
                </div>
                
                <div>
                  <span className="font-medium">摘要: </span>
                  <div className="text-muted-foreground text-sm mt-1 max-h-20 overflow-y-auto">
                    {analysisProgress.currentPaper.abstract}
                  </div>
                </div>
                
                <div>
                  <span className="font-medium">分析结果: </span>
                  <div className="text-muted-foreground text-sm mt-1">
                    {analysisProgress.currentPaper.analysis}
                  </div>
                </div>
              </CardContent>
            </Card>
            )}

            <div className="flex justify-end">
              <Button 
                variant="outline" 
                onClick={handleClose}
              >
                关闭进度跟踪
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}