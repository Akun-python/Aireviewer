#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def count_chinese_characters(text):
    """
    统计文本中的中文字符数（不包括标点符号和空格）
    
    参数:
        text: 输入的文本字符串
        
    返回:
        中文字符数（整数）
    """
    # 读取文本文件
    with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除所有标点符号（包括中文标点和英文标点）
    # 中文标点：。，、；：！？""''（）《》【】『』「」〔〕…—～
    # 英文标点：.,;:!?"'()[]{}<>-~ 
    punctuation_pattern = r'[。，、；：！？""\'\'（）《》【】『』「」〔〕…—～.,;:!?"\'()\[\]{}<>\-~ ]'
    cleaned_text = re.sub(punctuation_pattern, '', content)
    
    # 移除所有数字
    cleaned_text = re.sub(r'\d+', '', cleaned_text)
    
    # 移除所有英文字母
    cleaned_text = re.sub(r'[a-zA-Z]', '', cleaned_text)
    
    # 移除所有特殊字符如[H2]、[H3]等
    cleaned_text = re.sub(r'\[H\d+\]', '', cleaned_text)
    
    # 统计中文字符（Unicode范围：\u4e00-\u9fff）
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', cleaned_text)
    
    return len(chinese_chars), chinese_chars[:50]  # 返回前50个字符用于验证

def main():
    # 读取文本
    with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    # 统计总字符数（包括所有字符）
    total_chars = len(text)
    
    # 统计中文字符数（不包括标点符号和空格）
    chinese_count, sample_chars = count_chinese_characters(text)
    
    # 输出结果
    print("=" * 60)
    print("文本字数统计结果")
    print("=" * 60)
    print(f"文本总字符数（包括所有字符）: {total_chars}")
    print(f"中文字符数（不包括标点符号和空格）: {chinese_count}")
    print("-" * 60)
    print("统计规则说明：")
    print("1. 只统计中文字符（Unicode范围：\\u4e00-\\u9fff）")
    print("2. 排除所有标点符号（中文和英文标点）")
    print("3. 排除所有空格")
    print("4. 排除所有数字")
    print("5. 排除所有英文字母")
    print("6. 排除[H2]、[H3]等标记")
    print("-" * 60)
    print(f"前50个统计到的中文字符示例: {''.join(sample_chars)}...")
    print("=" * 60)
    
    # 为了验证，让我们也进行一些额外的检查
    print("\n验证检查：")
    print("-" * 60)
    
    # 检查文本中是否包含非中文字符
    all_chars = re.findall(r'.', text)
    chinese_only = re.findall(r'[\u4e00-\u9fff]', text)
    punctuation = re.findall(r'[。，、；：！？""\'\'（）《》【】『』「」〔〕…—～.,;:!?"\'()\[\]{}<>\-~ ]', text)
    numbers = re.findall(r'\d', text)
    english = re.findall(r'[a-zA-Z]', text)
    
    print(f"文本总字符数: {len(all_chars)}")
    print(f"所有中文字符数（包括在标点中的）: {len(chinese_only)}")
    print(f"标点符号数: {len(punctuation)}")
    print(f"数字字符数: {len(numbers)}")
    print(f"英文字母数: {len(english)}")
    
    # 验证计算
    calculated_total = len(chinese_only) + len(punctuation) + len(numbers) + len(english)
    print(f"各部分字符数之和: {calculated_total}")
    print(f"与总字符数差异: {len(all_chars) - calculated_total} (可能是换行符等其他字符)")

if __name__ == "__main__":
    main()