#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# 读取完整的文本
with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
    full_text = f.read()

print("开始统计中文字符数...")
print("=" * 60)

# 方法1：使用正则表达式匹配所有中文字符
chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
chinese_chars = chinese_pattern.findall(full_text)
count_method1 = len(chinese_chars)

print(f"方法1（正则匹配）：{count_method1} 个中文字符")

# 方法2：手动遍历统计
count_method2 = 0
manual_chars = []
for char in full_text:
    # 检查字符是否在中文Unicode范围内
    if '\u4e00' <= char <= '\u9fff':
        count_method2 += 1
        manual_chars.append(char)

print(f"方法2（手动遍历）：{count_method2} 个中文字符")

# 验证两种方法结果是否一致
if count_method1 == count_method2:
    print(f"✓ 两种方法结果一致：{count_method1} 字")
else:
    print(f"✗ 两种方法结果不一致：方法1={count_method1}, 方法2={count_method2}")

print("\n" + "=" * 60)
print("最终统计结果：")
print("=" * 60)
print(f"文本中的中文字符数（不包括标点符号和空格）：{count_method1} 字")

# 显示统计详情
print("\n统计详情：")
print("-" * 60)

# 按行统计，显示主要部分
lines = full_text.split('\n')
line_counts = []
for i, line in enumerate(lines):
    if line.strip():
        line_chars = chinese_pattern.findall(line)
        line_count = len(line_chars)
        line_counts.append(line_count)
        
        # 显示有内容的行
        if line_count > 0 and i < 10:  # 显示前10行
            preview = line[:50] + "..." if len(line) > 50 else line
            print(f"行 {i+1:3d}: {line_count:3d} 字 | {preview}")

print(f"\n总行数（有内容）：{len(line_counts)}")
print(f"总字数：{sum(line_counts)}")

# 验证抽样
print("\n验证抽样：")
print("-" * 60)

# 抽样检查几个关键段落
sample_indices = [3, 7, 15, 20]  # 抽样行号
for idx in sample_indices:
    if idx < len(lines):
        line = lines[idx]
        if line.strip():
            sample_chars = chinese_pattern.findall(line)
            print(f"行 {idx+1} 抽样：{len(sample_chars)} 字")

print("\n" + "=" * 60)
print("统计完成！")
print("=" * 60)