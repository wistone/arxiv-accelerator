import { useEffect } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAppStore } from '@/stores/appStore'

export const useUrlState = () => {
  const searchParams = useSearchParams()
  const { setSelectedDate, setSelectedCategory } = useAppStore()

  // Parse URL parameters on mount
  useEffect(() => {
    const date = searchParams.get('date')
    const category = searchParams.get('category')

    if (date) {
      setSelectedDate(date)
    }
    if (category) {
      setSelectedCategory(category)
    }
  }, [searchParams, setSelectedDate, setSelectedCategory])

  const updateUrlState = (action: string, date: string, category: string, testCount?: string) => {
    const params = new URLSearchParams()
    params.set('action', action)
    params.set('date', date)
    params.set('category', category)
    
    if (testCount) {
      params.set('test_count', testCount)
    }

    const newUrl = `${window.location.pathname}?${params.toString()}`
    
    // Update URL without triggering navigation
    window.history.pushState(null, '', newUrl)
  }

  const parseUrlParams = () => {
    return {
      action: searchParams.get('action'),
      date: searchParams.get('date'),
      category: searchParams.get('category'),
      testCount: searchParams.get('test_count'),
    }
  }

  return {
    updateUrlState,
    parseUrlParams,
  }
}