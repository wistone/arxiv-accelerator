'use client'

import React, { Suspense } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Container } from '@/components/layout/Container'
import { Header } from '@/components/layout/Header'
import { SearchControls } from '@/components/search/SearchControls'
import { SearchButton } from '@/components/search/SearchButton'
import { StatusMessages } from '@/components/common/StatusMessages'
import { LoadingSpinner } from '@/components/common/LoadingSpinner'
import { ArticlesTable } from '@/components/table/ArticlesTable'
import { AnalysisModal } from '@/components/analysis/AnalysisModal'
import { useAppStore } from '@/stores/appStore'
import { useUrlState } from '@/hooks/useUrlState'

const queryClient = new QueryClient()

function ArxivAssistantContent() {
  const { 
    currentArticles, 
    currentAnalysisArticles, 
    setAnalysisModalOpen,
    setSortColumn,
    setSortDirection,
    sortColumn,
    sortDirection
  } = useAppStore()
  
  const { updateUrlState } = useUrlState()
  
  const isAnalysisMode = currentAnalysisArticles.length > 0
  const displayArticles = isAnalysisMode ? currentAnalysisArticles : currentArticles

  const handleAnalyzeClick = () => {
    setAnalysisModalOpen(true)
  }

  const handleSort = (column: string) => {
    const newDirection = sortColumn === column && sortDirection === 'asc' ? 'desc' : 'asc'
    setSortColumn(column)
    setSortDirection(newDirection)
    
    // Update URL state
    updateUrlState('analysis', '', '', '')
  }

  const sortedArticles = React.useMemo(() => {
    if (!displayArticles || displayArticles.length === 0 || !sortColumn) {
      return displayArticles
    }

    return [...displayArticles].sort((a, b) => {
      let aValue: string | number = a[sortColumn as keyof typeof a] as string | number
      let bValue: string | number = b[sortColumn as keyof typeof b] as string | number

      // Handle numeric sorting for raw_score
      if (sortColumn === 'raw_score') {
        aValue = typeof aValue === 'number' ? aValue : 0
        bValue = typeof bValue === 'number' ? bValue : 0
      }

      // Ensure values are not undefined
      if (aValue === undefined || aValue === null) aValue = ''
      if (bValue === undefined || bValue === null) bValue = ''

      if (sortDirection === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0
      }
    })
  }, [displayArticles, sortColumn, sortDirection])

  return (
    <Container isAnalysisMode={isAnalysisMode}>
      <Header />
      <SearchControls />
      <SearchButton onAnalyzeClick={handleAnalyzeClick} />
      <StatusMessages />
      <LoadingSpinner />
      
      {sortedArticles && sortedArticles.length > 0 && (
        <ArticlesTable 
          articles={sortedArticles}
          isAnalysisMode={isAnalysisMode}
          onSort={isAnalysisMode ? handleSort : undefined}
        />
      )}
      
      <AnalysisModal />
    </Container>
  )
}

export default function ArxivAssistant() {
  return (
    <QueryClientProvider client={queryClient}>
      <Suspense fallback={<div>Loading...</div>}>
        <ArxivAssistantContent />
      </Suspense>
    </QueryClientProvider>
  )
}