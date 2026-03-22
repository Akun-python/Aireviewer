#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def count_chinese_chars(text):
    """统计文本中的中文字符数，排除所有非中文字符"""
    # 使用正则表达式匹配所有中文字符（Unicode范围：4E00-9FFF）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
    return len(chinese_chars), chinese_chars

def main():
    # 读取文本
    with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 统计字数
    count, chars = count_chinese_chars(text)
    
    # 输出结果
    print("=" * 70)
    print("文本字数统计报告")
    print("=" * 70)
    print(f"统计对象：学术观点创新与研究方法创新文本")
    print(f"统计规则：只统计中文字符，排除标点符号、空格、数字、英文字母等所有非中文字符")
    print("-" * 70)
    print(f"统计结果：{count} 个中文字符")
    print("-" * 70)
    
    # 详细分析
    print("\n详细分析：")
    print("-" * 70)
    
    # 分析文本结构
    sections = text.split('[H')
    print(f"文本包含 {len(sections)} 个主要部分")
    
    # 统计每个部分
    total_count = 0
    for i, section in enumerate(sections):
        if section.strip():
            section_count, _ = count_chinese_chars(section)
            total_count += section_count
            
            # 获取部分标题
            lines = section.strip().split('\n')
            title = lines[0][:50] + "..." if len(lines[0]) > 50 else lines[0]
            
            print(f"部分 {i+1}: {section_count} 字 | {title}")
    
    print(f"\n各部分字数总和: {total_count} 字")
    
    # 验证统计准确性
    print("\n验证检查：")
    print("-" * 70)
    
    # 检查前100个字符
    print(f"前100个中文字符样本：")
    sample = ''.join(chars[:100])
    for i in range(0, len(sample), 50):
        print(f"  {sample[i:i+50]}")
    
    # 检查最后50个字符
    print(f"\n最后50个中文字符样本：")
    sample_end = ''.join(chars[-50:])
    print(f"  {sample_end}")
    
    # 字符频率分析（前20个最常用字）
    print("\n字符频率分析（前20个最常用字）：")
    char_freq = {}
    for char in chars:
        char_freq[char] = char_freq.get(char, 0) + 1
    
    sorted_chars = sorted(char_freq.items(), key=lambda x: x[1], reverse=True)
    for i, (char, freq) in enumerate(sorted_chars[:20]):
        print(f"  {i+1:2d}. '{char}'：{freq:3d}次", end=" | ")
        if (i + 1) % 4 == 0:
            print()
    
    print("\n" + "=" * 70)
    print("最终确认：")
    print(f"该文本的中文字符数（不包括标点符号和空格）为：{count} 字")
    print("=" * 70)

if __name__ == "__main__":
    main()