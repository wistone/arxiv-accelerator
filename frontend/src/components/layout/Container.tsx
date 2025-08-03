import React from 'react'
import { cn } from '@/lib/utils'

interface ContainerProps {
  children: React.ReactNode
  className?: string
  isAnalysisMode?: boolean
}

export const Container = ({ children, className, isAnalysisMode = false }: ContainerProps) => {
  return (
    <div className="min-h-screen bg-background p-6">
      <div 
        className={cn(
          "mx-auto bg-card rounded-lg border shadow-sm overflow-hidden transition-all duration-300",
          isAnalysisMode ? "max-w-7xl" : "max-w-5xl",
          "max-md:max-w-[95%] max-md:mx-[2.5%]",
          "max-sm:max-w-full max-sm:mx-0 max-sm:rounded-none",
          className
        )}
      >
        {children}
      </div>
    </div>
  )
}