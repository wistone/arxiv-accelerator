import React, { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from '@/components/ui/table'
import { useAppStore } from '@/stores/appStore'
import { cn } from '@/lib/utils'

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

interface ArticlesTableProps {
  articles: Article[]
  isAnalysisMode?: boolean
  onSort?: (column: string) => void
}

// Expandable content component
const ExpandableContent = ({ 
  content, 
  maxHeight, 
  className,
  textAlign = 'left'
}: { 
  content: string; 
  maxHeight: string; 
  className?: string;
  textAlign?: 'left' | 'justify';
}) => {
  const [isExpanded, setIsExpanded] = useState(false)
  const [shouldShowToggle, setShouldShowToggle] = useState(false)
  
  React.useEffect(() => {
    // Check if content needs truncation
    const element = document.createElement('div')
    element.style.cssText = `
      position: absolute; 
      visibility: hidden; 
      height: auto; 
      width: 280px; 
      line-height: 1.5;
      font-size: 13px;
      word-wrap: break-word;
      word-break: break-word;
      overflow-wrap: break-word;
    `
    element.textContent = content
    document.body.appendChild(element)
    
    const fullHeight = element.offsetHeight
    document.body.removeChild(element)
    
    const maxHeightPx = parseInt(maxHeight.replace('px', ''))
    setShouldShowToggle(fullHeight > maxHeightPx)
  }, [content, maxHeight])

  return (
    <div className={`${className} break-words`}>
      <div 
        className="overflow-hidden relative transition-all duration-300 break-words"
        style={{ 
          maxHeight: isExpanded ? 'none' : maxHeight,
          lineHeight: '1.5',
          wordWrap: 'break-word',
          wordBreak: 'break-word',
          overflowWrap: 'break-word',
          whiteSpace: 'normal',
          textAlign: textAlign
        }}
      >
        {content}
      </div>
      {shouldShowToggle && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-primary hover:underline text-xs font-semibold mt-1 block cursor-pointer"
        >
          {isExpanded ? '收起' : '展开'}
        </button>
      )}
    </div>
  )
}

export const ArticlesTable = ({ 
  articles, 
  isAnalysisMode = false, 
  onSort 
}: ArticlesTableProps) => {
  const { sortColumn, sortDirection } = useAppStore()

  if (!articles || articles.length === 0) {
    return null
  }

  const getSortIndicator = (column: string) => {
    if (sortColumn !== column) return '↕'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  const truncateText = (text: string, maxLength: number) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  return (
    <div className="px-8 pb-8">
      {/* Stats */}
      <div className="mb-6">
        <div className="flex items-center gap-4">
          <Badge variant="secondary" className="text-lg px-4 py-2">
            文章总数: {articles.length}
          </Badge>
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table className="table-fixed">
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">序号</TableHead>
                  
                  {isAnalysisMode && (
                    <>
                      <TableHead className="w-24">筛选结果</TableHead>
                      <TableHead 
                        className={cn(
                          "w-20 cursor-pointer hover:bg-muted/50",
                          onSort && "cursor-pointer"
                        )}
                        onClick={() => onSort?.('raw_score')}
                      >
                        总分 {onSort && (
                          <span className="ml-1">{getSortIndicator('raw_score')}</span>
                        )}
                      </TableHead>
                      <TableHead className="w-32">详细分析</TableHead>
                    </>
                  )}
                  
                  <TableHead className={cn(
                    isAnalysisMode ? "max-w-[280px] min-w-[220px]" : "max-w-[320px] min-w-[260px]"
                  )}>
                    标题
                  </TableHead>
                  <TableHead className={cn(
                    isAnalysisMode ? "max-w-[180px] min-w-[140px]" : "max-w-[200px] min-w-[150px]"
                  )}>
                    作者
                  </TableHead>
                  <TableHead className={cn(
                    isAnalysisMode ? "max-w-[350px] min-w-[280px]" : "max-w-[420px] min-w-[320px]"
                  )}>
                    摘要
                  </TableHead>
                  
                  {!isAnalysisMode && (
                    <TableHead className="w-20">链接</TableHead>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {articles.map((article, index) => (
                  <TableRow key={`${article.id}-${index}`} className="hover:bg-muted/50">
                    <TableCell className="font-medium text-center">
                      {article.number || index + 1}
                    </TableCell>
                    
                    {isAnalysisMode && (
                      <>
                        <TableCell>
                          <Badge 
                            variant={article.filter_result === '推荐' ? 'default' : 'destructive'}
                            className={cn(
                              article.filter_result === '推荐' 
                                ? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200' 
                                : 'bg-red-100 text-red-800 hover:bg-red-200'
                            )}
                          >
                            {article.filter_result || '未知'}
                          </Badge>
                        </TableCell>
                        <TableCell className="font-bold text-center">
                          {article.raw_score !== undefined ? article.raw_score : 'N/A'}
                        </TableCell>
                        <TableCell className="text-sm">
                          <div className="max-h-20 overflow-y-auto">
                            {article.detailed_analysis ? 
                              truncateText(article.detailed_analysis, 150) : 
                              '无详细分析'
                            }
                          </div>
                        </TableCell>
                      </>
                    )}
                    
                    <TableCell className={cn(
                      isAnalysisMode ? "max-w-[280px] min-w-[220px]" : "max-w-[320px] min-w-[260px]",
                      "break-words"
                    )}>
                      <div 
                        className="font-medium text-foreground break-words" 
                        style={{ 
                          lineHeight: '1.4',
                          wordWrap: 'break-word',
                          wordBreak: 'break-word',
                          overflowWrap: 'break-word',
                          whiteSpace: 'normal'
                        }}
                      >
                        {article.title}
                      </div>
                    </TableCell>
                    <TableCell className={cn(
                      isAnalysisMode ? "max-w-[180px] min-w-[140px]" : "max-w-[200px] min-w-[150px]",
                      "break-words"
                    )}>
                      <ExpandableContent
                        content={article.authors}
                        maxHeight="75px"
                        className="text-sm text-muted-foreground break-words"
                      />
                    </TableCell>
                    <TableCell className={cn(
                      isAnalysisMode ? "max-w-[350px] min-w-[280px]" : "max-w-[420px] min-w-[320px]",
                      "break-words"
                    )}>
                      <ExpandableContent
                        content={article.abstract}
                        maxHeight="120px"
                        className="text-sm text-foreground break-words"
                        textAlign="justify"
                      />
                    </TableCell>
                    
                    {!isAnalysisMode && (
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <a 
                            href={article.arxiv_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-primary hover:text-primary/80 text-xs"
                          >
                            arXiv
                          </a>
                          <a 
                            href={article.pdf_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-destructive hover:text-destructive/80 text-xs"
                          >
                            PDF
                          </a>
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}