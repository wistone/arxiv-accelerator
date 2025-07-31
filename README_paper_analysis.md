# 论文分析处理脚本使用说明

## 概述

这组脚本可以处理arxiv论文的markdown文件，调用doubao1.6模型对每篇论文进行多模态大模型相关度评估，并生成分析结果文件。

## 文件说明

### 1. `test_paper_analysis.py`
- **功能**: 测试脚本，用于快速验证论文分析功能
- **特点**: 只处理前10篇论文，显示详细的分析日志

### 2. `paper_analysis_processor.py`
- **功能**: 完整的论文处理脚本
- **特点**: 可以处理整个文件或指定数量的论文

### 3. `demo_paper_analysis.py`
- **功能**: 演示脚本，生成示例分析结果
- **特点**: 不调用实际API，展示最终输出格式

## 输入输出格式

### 输入文件格式
原始markdown文件表头：
```
|   No. |   number_id | title | authors | abstract | link |
```

### 输出文件格式
分析结果文件表头：
```
|   No. |   analysis_result | title | authors | abstract | link |
```

关键变化：
- 移除了 `number_id` 字段
- 新增了 `analysis_result` 字段，包含JSON格式的分析结果

## analysis_result字段说明

JSON格式，包含以下字段：

### 通过过滤的论文
```json
{
  "pass_filter": true,
  "exclude_reason": "",
  "core_features": {
    "multi_modal": 1,
    "large_scale": 1,
    "unified_framework": 0,
    "novel_paradigm": 0
  },
  "plus_features": {
    "new_benchmark": 0,
    "sota": 1,
    "fusion_arch": 1,
    "real_world_app": 1,
    "reasoning_planning": 1,
    "scaling_modalities": 0,
    "open_source": 0
  },
  "raw_score": 9,
  "norm_score": 9.0,
  "reason": "满足多模态与大规模两大核心特征，通过SkipCA模块实现融合架构创新，强调文本-图像相关性推理，并达到SOTA性能。"
}
```

### 未通过过滤的论文
```json
{
  "pass_filter": false,
  "exclude_reason": "single-modality (only visual, top-down view to panorama)",
  "raw_score": 0,
  "norm_score": 0,
  "reason": "Excluded: single-modality (only visual, top-down view to panorama)"
}
```

## 使用方法

### 1. 快速测试（前10篇）
```bash
python3 test_paper_analysis.py
```

### 2. 处理指定数量的论文
```bash
python3 paper_analysis_processor.py log/2025-07-28-cs.CV-result.md --test 10
```

### 3. 处理整个文件
```bash
python3 paper_analysis_processor.py log/2025-07-28-cs.CV-result.md
```

### 4. 查看演示结果
```bash
python3 demo_paper_analysis.py
```

## 输出文件

- 输入: `log/2025-07-28-cs.CV-result.md`
- 输出: `log/2025-07-28-cs.CV-analysis.md`

## 依赖要求

1. **doubao_client.py**: doubao1.6模型调用客户端
2. **prompt/system_prompt.md**: 系统提示词文件
3. 必要的Python包：
   - pandas
   - json
   - os
   - argparse

## 评估标准

基于system_prompt.md中定义的多模态大模型论文甄别标准：

### 核心特征（每项2分）
- multi_modal: 涉及视觉且语言
- large_scale: 使用大规模模型
- unified_framework: 统一框架解决多任务
- novel_paradigm: 新颖训练范式

### 加分特征（每项1分）
- new_benchmark: 提出新基准
- sota: 刷新SOTA
- fusion_arch: 融合架构创新
- real_world_app: 真实应用
- reasoning_planning: 推理/规划
- scaling_modalities: 扩展多模态
- open_source: 开源

### 评分公式
- raw_score = 核心特征分 + 加分特征分
- norm_score = min(10, raw_score)

## 注意事项

1. **API调用频率**: 每篇论文需要调用一次API，处理大量论文时需要考虑时间成本
2. **错误处理**: 脚本包含完善的错误处理机制，API调用失败时会记录错误信息
3. **文件编码**: 使用UTF-8编码处理中文内容
4. **特殊字符转义**: 自动处理markdown表格中的特殊字符

## 示例结果

详见生成的演示文件：`log/2025-07-28-cs.CV-analysis-demo.md`

该文件展示了三种典型的分析结果：
1. 高分多模态论文（9分）
2. 单模态被过滤论文（0分）
3. 中分多模态论文（7分）