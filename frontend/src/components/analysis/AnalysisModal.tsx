import React, { useState } from 'react'
import { Button } from '@/components/ui/button'
import { 
  Dialog, 
  DialogContent, 
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
import { useAnalyzeArticles } from '@/hooks/useApi'
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
  
  const [testCount, setTestCount] = useState<string>('')
  const [analysisStatus, setAnalysisStatus] = useState<string>('')
  
  const analyzeMutation = useAnalyzeArticles()
  const { startProgress, stopProgress } = useSSE()

  const handleClose = () => {
    stopProgress()
    setAnalysisModalOpen(false)
    clearMessages()
  }

  const handleStartAnalysis = async () => {
    try {
      const result = await analyzeMutation.mutateAsync({
        date: selectedDate,
        category: selectedCategory,
        testCount
      }) as { success?: boolean }
      
      if (result.success) {
        startProgress()
        setAnalysisStatus('Analysis started, tracking progress...')
      }
    } catch {
      setAnalysisStatus('Failed to start analysis, please try again')
    }
  }

  const getProgressPercentage = () => {
    if (!analysisProgress || analysisProgress.total === 0) return 0
    return Math.round((analysisProgress.current / analysisProgress.total) * 100)
  }

  return (
    <Dialog open={isAnalysisModalOpen} onOpenChange={setAnalysisModalOpen}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-xl font-semibold flex items-center gap-2">
            📊 Paper Analysis Progress
          </DialogTitle>
        </DialogHeader>

        {!isAnalyzing && !analysisProgress && (
          <div className="space-y-6">
            {/* Analysis Options */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">🧪 Analysis Range Selection</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <Select value={testCount} onValueChange={setTestCount}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select analysis range" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Analyze All</SelectItem>
                    <SelectItem value="5">First 5 Only</SelectItem>
                    <SelectItem value="10">First 10 Only</SelectItem>
                    <SelectItem value="20">First 20 Only</SelectItem>
                  </SelectContent>
                </Select>
                
                <div className="flex gap-3">
                  <Button 
                    onClick={handleStartAnalysis}
                    disabled={analyzeMutation.isPending}
                    className="bg-gradient-to-r from-indigo-500 to-purple-600"
                  >
                    Start Analysis
                  </Button>
                  
                  <Button 
                    variant="outline" 
                    onClick={handleClose}
                  >
                    Cancel
                  </Button>
                </div>
                
                {analysisStatus && (
                  <div className="text-sm text-gray-600 mt-2">
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
                <CardTitle>Analysis Progress</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span>Progress: {analysisProgress?.current || 0} / {analysisProgress?.total || 0}</span>
                    <span>{getProgressPercentage()}%</span>
                  </div>
                  <Progress value={getProgressPercentage()} className="w-full" />
                </div>
                
                <div className="text-sm text-gray-600">
                  {analysisProgress?.status || 'Preparing to start analysis...'}
                </div>
              </CardContent>
            </Card>

            {/* Current Paper */}
            {analysisProgress?.currentPaper && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Current Paper Being Processed</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div>
                    <h4 className="font-semibold text-gray-900">
                      {analysisProgress.currentPaper.title}
                    </h4>
                  </div>
                  
                  <div>
                    <span className="font-medium">Authors: </span>
                    <span className="text-gray-700">
                      {analysisProgress.currentPaper.authors}
                    </span>
                  </div>
                  
                  <div>
                    <span className="font-medium">Abstract: </span>
                    <div className="text-gray-700 text-sm mt-1 max-h-20 overflow-y-auto">
                      {analysisProgress.currentPaper.abstract}
                    </div>
                  </div>
                  
                  <div>
                    <span className="font-medium">Analysis Result: </span>
                    <div className="text-gray-700 text-sm mt-1">
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
                Close Progress Tracking
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}