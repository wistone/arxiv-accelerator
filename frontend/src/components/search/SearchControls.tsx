import React, { useState } from 'react'
import { CalendarIcon } from 'lucide-react'
import { format } from 'date-fns'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/stores/appStore'

export const SearchControls = () => {
  const { 
    selectedDate, 
    selectedCategory, 
    setSelectedDate, 
    setSelectedCategory 
  } = useAppStore()
  
  const [isCalendarOpen, setIsCalendarOpen] = useState(false)

  const handleDateSelect = (date: Date | undefined) => {
    if (date) {
      setSelectedDate(date.toISOString().split('T')[0])
      setIsCalendarOpen(false)
    }
  }

  return (
    <div className="p-8 bg-muted/30 border-b">
      <div className="flex flex-wrap gap-5 items-end mb-5">
        {/* Date Selection */}
        <div className="flex flex-col min-w-[200px]">
          <Label htmlFor="date-picker" className="mb-2 font-medium text-foreground">
            选择日期
          </Label>
          <Popover open={isCalendarOpen} onOpenChange={setIsCalendarOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !selectedDate && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {selectedDate ? (
                  format(new Date(selectedDate), "yyyy-MM-dd")
                ) : (
                  <span>选择日期</span>
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={selectedDate ? new Date(selectedDate) : undefined}
                onSelect={handleDateSelect}
                disabled={(date) =>
                  date > new Date() || date < new Date("2020-01-01")
                }
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* Category Selection */}
        <div className="flex flex-col min-w-[200px]">
          <Label htmlFor="category-select" className="mb-2 font-medium text-foreground">
            板块筛选
          </Label>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger>
              <SelectValue placeholder="选择分类" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="cs.CV">cs.CV - 计算机视觉</SelectItem>
              <SelectItem value="cs.LG">cs.LG - 机器学习</SelectItem>
              <SelectItem value="cs.AI">cs.AI - 人工智能</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )
}