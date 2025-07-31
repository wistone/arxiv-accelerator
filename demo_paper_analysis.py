#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os

def create_demo_analysis():
    """创建演示分析结果"""
    
    # 模拟前3篇论文的分析结果
    demo_papers = [
        {
            'no': '1',
            'title': 'Multimodal LLMs as Customized Reward Models for Text-to-Image Generation',
            'authors': 'Shijie Zhou, Ruiyi Zhang, Huaisheng Zhu, Branislav Kveton, Yufan Zhou, Jiuxiang Gu, Jian Chen, Changyou Chen',
            'abstract': 'We introduce LLaVA-Reward, an efficient reward model designed to automatically evaluate text-to-image (T2I) generations across multiple perspectives, leveraging pretrained multimodal large language models (MLLMs)...',
            'link': 'http://arxiv.org/abs/2507.21391v2',
            'analysis_result': '{"pass_filter":true,"exclude_reason":"","core_features":{"multi_modal":1,"large_scale":1,"unified_framework":0,"novel_paradigm":0},"plus_features":{"new_benchmark":0,"sota":1,"fusion_arch":1,"real_world_app":1,"reasoning_planning":1,"scaling_modalities":0,"open_source":0},"raw_score":9,"norm_score":9.0,"reason":"满足多模态与大规模两大核心特征，通过SkipCA模块实现融合架构创新，强调文本-图像相关性推理，并达到SOTA性能。"}'
        },
        {
            'no': '2',
            'title': 'Top2Pano: Learning to Generate Indoor Panoramas from Top-Down View',
            'authors': 'Zitong Zhang, Suranjan Gautam, Rui Yu',
            'abstract': 'Generating immersive 360deg indoor panoramas from 2D top-down views has applications in virtual reality, interior design, real estate, and robotics...',
            'link': 'http://arxiv.org/abs/2507.21371v1',
            'analysis_result': '{"pass_filter":false,"exclude_reason":"single-modality (only visual, top-down view to panorama)","raw_score":0,"norm_score":0,"reason":"Excluded: single-modality (only visual, top-down view to panorama)"}'
        },
        {
            'no': '3',
            'title': 'Group Relative Augmentation for Data Efficient Action Detection',
            'authors': 'Deep Anil Patel, Iain Melvin, Zachary Izzo, Martin Renqiang Min',
            'abstract': 'Adapting large Video-Language Models (VLMs) for action detection using only a few examples poses challenges like overfitting and the granularity mismatch...',
            'link': 'http://arxiv.org/abs/2507.21353v1',
            'analysis_result': '{"pass_filter":true,"exclude_reason":"","core_features":{"multi_modal":1,"large_scale":1,"unified_framework":0,"novel_paradigm":1},"plus_features":{"new_benchmark":0,"sota":0,"fusion_arch":0,"real_world_app":1,"reasoning_planning":0,"scaling_modalities":0,"open_source":0},"raw_score":7,"norm_score":7.0,"reason":"满足多模态、大规模和新颖训练范式三大核心特征，在数据效率和真实应用方面表现突出。"}'
        }
    ]
    
    return demo_papers

def escape_markdown_content(content):
    """转义markdown表格中的特殊字符"""
    if not content:
        return ""
    
    # 转义管道符号
    content = content.replace('|', '\\|')
    # 转义换行符
    content = content.replace('\n', ' ')
    return content

def generate_demo_markdown():
    """生成演示markdown文件"""
    
    papers = create_demo_analysis()
    output_file = 'log/2025-07-28-cs.CV-analysis-demo.md'
    
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # 写入表头
            f.write("|   No. |   analysis_result | title | authors | abstract | link |\n")
            f.write("|------:|:------------------|:------|:--------|:---------|:-----|\n")
            
            # 写入数据行
            for paper in papers:
                no = escape_markdown_content(paper['no'])
                analysis_result = escape_markdown_content(paper['analysis_result'])
                title = escape_markdown_content(paper['title'])
                authors = escape_markdown_content(paper['authors'])
                abstract = escape_markdown_content(paper['abstract'])
                link = escape_markdown_content(paper['link'])
                
                f.write(f"|{no:>6} | {analysis_result} | {title} | {authors} | {abstract} | {link} |\n")
        
        print(f"✅ 演示分析结果已保存到: {output_file}")
        
        # 显示分析结果的详细信息
        print("\n" + "=" * 80)
        print("论文分析结果详情：")
        print("=" * 80)
        
        for i, paper in enumerate(papers):
            print(f"\n【第 {i+1} 篇论文】")
            print(f"标题: {paper['title']}")
            print(f"作者: {paper['authors']}")
            
            # 解析并显示分析结果
            try:
                analysis = json.loads(paper['analysis_result'])
                print(f"通过过滤: {'是' if analysis.get('pass_filter') else '否'}")
                
                if analysis.get('pass_filter'):
                    print(f"评分: {analysis.get('norm_score')}/10")
                    print(f"核心特征: {analysis.get('core_features')}")
                    print(f"加分特征: {analysis.get('plus_features')}")
                else:
                    print(f"排除原因: {analysis.get('exclude_reason')}")
                
                print(f"评价理由: {analysis.get('reason')}")
                
            except json.JSONDecodeError:
                print("分析结果JSON格式错误")
            
            print("-" * 50)
        
    except Exception as e:
        print(f"生成演示文件失败: {e}")

def main():
    """主函数"""
    print("生成论文分析演示文件...")
    generate_demo_markdown()

if __name__ == "__main__":
    main()