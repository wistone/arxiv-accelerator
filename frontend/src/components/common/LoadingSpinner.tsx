import React from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { useAppStore } from '@/stores/appStore'

export const LoadingSpinner = () => {
  const { isLoading } = useAppStore()

  if (!isLoading) {
    return null
  }

  return (
    <div className="px-8 py-6">
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
          <p className="text-muted-foreground">正在加载数据...</p>
        </CardContent>
      </Card>
    </div>
  )
}