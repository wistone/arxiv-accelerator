import React from 'react'

export const Header = () => {
  return (
    <div className="border-b bg-background px-8 py-12 text-center">
      <h1 className="text-3xl font-semibold tracking-tight text-foreground mb-4">
        Arxiv文章初筛小助手
      </h1>
      <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
        智能筛选和分析Arxiv论文，助您快速找到感兴趣的研究
      </p>
    </div>
  )
}