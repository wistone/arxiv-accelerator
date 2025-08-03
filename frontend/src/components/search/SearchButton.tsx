import React from 'react'
import { Search, BarChart3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAppStore } from '@/stores/appStore'
import { useSearchArticles } from '@/hooks/useApi'

interface SearchButtonProps {
  onAnalyzeClick: () => void
}

export const SearchButton = ({ onAnalyzeClick }: SearchButtonProps) => {
  const { 
    selectedDate, 
    selectedCategory, 
    hasSearched, 
    isLoading 
  } = useAppStore()
  
  const searchMutation = useSearchArticles()

  const handleSearch = () => {
    if (!selectedDate) {
      return
    }
    
    searchMutation.mutate({ 
      date: selectedDate, 
      category: selectedCategory 
    })
  }

  return (
    <div className="px-8 pb-5">
      <div className="flex flex-wrap gap-4">
        <Button 
          onClick={handleSearch}
          disabled={!selectedDate || isLoading}
        >
          <Search className="mr-2 h-4 w-4" />
          搜索文章列表
        </Button>
        
        <Button 
          variant="secondary"
          onClick={onAnalyzeClick}
          disabled={!hasSearched || isLoading}
        >
          <BarChart3 className="mr-2 h-4 w-4" />
          分析
        </Button>
      </div>
    </div>
  )
}