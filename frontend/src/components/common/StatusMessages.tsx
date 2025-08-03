import React from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { AlertCircle, CheckCircle } from 'lucide-react'
import { useAppStore } from '@/stores/appStore'

export const StatusMessages = () => {
  const { error, success } = useAppStore()

  if (!error && !success) {
    return null
  }

  return (
    <div className="px-8 py-4">
      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      
      {success && (
        <Alert className="mb-4 border-green-200 bg-green-50">
          <CheckCircle className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-800">
            {success}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}