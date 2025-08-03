import React from 'react'
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
    if (sortColumn !== column) return '↕️'
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
            📄 文章总数: {articles.length}
          </Badge>
        </div>
      </div>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">序号</TableHead>
                  
                  {isAnalysisMode ? (
                    <>
                      <TableHead className="w-24">筛选结果</TableHead>
                      <TableHead 
                        className={cn(
                          "w-20 cursor-pointer hover:bg-gray-50",
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
                  ) : (
                    <TableHead className="w-24">ID</TableHead>
                  )}
                  
                  <TableHead className={cn(
                    isAnalysisMode ? "max-w-[280px]" : "max-w-[400px]"
                  )}>
                    标题
                  </TableHead>
                  <TableHead className={cn(
                    isAnalysisMode ? "max-w-[180px]" : "max-w-[200px]"
                  )}>
                    作者
                  </TableHead>
                  <TableHead className={cn(
                    isAnalysisMode ? "max-w-[350px]" : "max-w-[400px]"
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
                  <TableRow key={article.id} className="hover:bg-gray-50">
                    <TableCell className="font-medium text-center">
                      {article.number || index + 1}
                    </TableCell>
                    
                    {isAnalysisMode ? (
                      <>
                        <TableCell>
                          <Badge 
                            variant={article.filter_result === '推荐' ? 'default' : 'secondary'}
                            className={cn(
                              article.filter_result === '推荐' 
                                ? 'bg-green-100 text-green-800 hover:bg-green-200' 
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
                    ) : (
                      <TableCell className="font-mono text-sm">
                        {article.id}
                      </TableCell>
                    )}
                    
                    <TableCell>
                      <div className="font-medium">
                        {truncateText(article.title, isAnalysisMode ? 100 : 150)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm text-gray-600">
                        {truncateText(article.authors, isAnalysisMode ? 80 : 120)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <details className="cursor-pointer">
                          <summary className="font-medium text-blue-600 hover:text-blue-800">
                            查看摘要 {article.abstract && `(${article.abstract.length} 字符)`}
                          </summary>
                          <div className="mt-2 text-gray-700 whitespace-pre-wrap">
                            {article.abstract}
                          </div>
                        </details>
                      </div>
                    </TableCell>
                    
                    {!isAnalysisMode && (
                      <TableCell>
                        <div className="flex flex-col gap-1">
                          <a 
                            href={article.arxiv_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 text-xs"
                          >
                            arXiv
                          </a>
                          <a 
                            href={article.pdf_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-red-600 hover:text-red-800 text-xs"
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