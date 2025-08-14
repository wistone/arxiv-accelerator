# 如何构建一个属于自己的Paper Judger

## Step 1 让牛逼的Claude4 Opus读一下最近我关注的paper，根据title和abstract总结规律，写一段挑paper的System Prompt

https://claude.ai/share/95226e7c-3f9d-4019-a185-a32dd9d3fbdd

## Step 2 让GPT O3把这个筛选规则改写成一个Judge Prompt，输出json格式

https://chatgpt.com/share/689d8d73-4300-8011-b70e-a3f6b9173060

## 最终的prompt 

**[Prompt 文档](prompt/multi-modal-llm-judger-example.md)** - 完整的multi model LLM论文打分器

## 备注
1. 为什么是这个步骤获取的prompt，我并没有仔细对比过，也许换用其他智商类似的agentic SOTA模型都可以，仅供参考
2. 这个步骤的核心是显示的给出筛选规则，并最终形成一套打分成json的prompt，强烈建议仔细研读思考这个prompt本身的合理性，和自己挑paper的insight是否一致
3. 最终的字段必须包含以下这两个字段
```jsonc
"pass_filter": true/false,
"raw_score": 8