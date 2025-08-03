import React from 'react'

export const Header = () => {
  return (
    <div className="bg-gradient-to-br from-indigo-500 to-purple-600 text-white px-8 py-8 text-center">
      <h1 className="text-4xl font-light mb-3">
        📚 Arxiv文章初筛小助手
      </h1>
      <p className="text-lg opacity-90">
        智能筛选和分析Arxiv论文，助您快速找到感兴趣的研究
      </p>
    </div>
  )
}