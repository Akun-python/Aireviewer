#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# 读取文本
with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
    content = f.read()

print("文本内容字数统计")
print("=" * 60)

# 统计方法：只匹配中文字符，排除其他所有字符
chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
matches = chinese_pattern.findall(content)

chinese_count = len(matches)

print(f"统计结果：{chinese_count} 个中文字符")
print("=" * 60)

# 显示统计详情
print("\n统计详情：")
print("-" * 60)

# 按段落统计
paragraphs = content.split('\n\n')
para_counts = []
for i, para in enumerate(paragraphs):
    if para.strip():  # 跳过空段落
        para_chars = chinese_pattern.findall(para)
        para_count = len(para_chars)
        para_counts.append(para_count)
        
        # 显示前几个段落的统计
        if i < 5:
            # 获取段落前50个字符作为标识
            preview = ''.join(para_chars[:30]) + "..." if len(para_chars) > 30 else ''.join(para_chars)
            print(f"段落 {i+1}: {para_count} 字 | {preview}")

print(f"\n段落总数: {len(para_counts)}")
print(f"总字数: {sum(para_counts)}")
print(f"平均每段字数: {sum(para_counts)/len(para_counts):.1f}")

# 验证：手动抽样检查
print("\n验证抽样检查：")
print("-" * 60)

# 抽样检查几个段落
test_paragraphs = [1, 5, 10]  # 检查第1、5、10段
for para_idx in test_paragraphs:
    if para_idx <= len(paragraphs):
        para = paragraphs[para_idx-1]
        if para.strip():
            para_chars = chinese_pattern.findall(para)
            print(f"段落 {para_idx} 抽样: {len(para_chars)} 字")

print("\n最终确认：")
print(f"文本中的中文字符数（不包括标点符号和空格）为：{chinese_count}")