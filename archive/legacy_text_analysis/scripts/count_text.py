#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

def count_chinese_chars(text):
    """
    计算文本中的中文字符数
    中文字符包括：汉字、中文标点符号等
    """
    # 匹配中文字符的正则表达式
    # 包括：汉字、中文标点符号（，。！？；："'（）【】《》）
    chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]')
    
    # 找到所有中文字符
    chinese_chars = chinese_pattern.findall(text)
    
    return len(chinese_chars)

def count_total_chars(text):
    """
    计算文本总字符数（包括所有字符）
    """
    return len(text)

def count_words(text):
    """
    计算文本中的单词数（按空格分割）
    """
    words = text.split()
    return len(words)

def main():
    # 读取文本文件
    with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    
    print("文本分析结果：")
    print("=" * 50)
    
    # 计算各种统计
    total_chars = count_total_chars(text)
    chinese_chars = count_chinese_chars(text)
    word_count = count_words(text)
    
    # 计算非中文字符数
    non_chinese_chars = total_chars - chinese_chars
    
    print(f"1. 文本总字符数（包括所有字符）：{total_chars}")
    print(f"2. 中文字符数（汉字和中文标点）：{chinese_chars}")
    print(f"3. 非中文字符数（英文、数字、符号等）：{non_chinese_chars}")
    print(f"4. 单词数（按空格分割）：{word_count}")
    print("=" * 50)
    
    # 与目标字数比较
    target_words = 1276
    difference = chinese_chars - target_words
    
    print(f"\n与目标字数比较：")
    print(f"目标字数：{target_words}字")
    print(f"实际中文字符数：{chinese_chars}字")
    
    if difference > 0:
        print(f"超出目标：{difference}字（需要精简）")
    elif difference < 0:
        print(f"不足目标：{abs(difference)}字（需要补充）")
    else:
        print(f"正好达到目标字数！")
    
    # 显示百分比
    percentage = (chinese_chars / target_words) * 100
    print(f"完成度：{percentage:.1f}%")

if __name__ == "__main__":
    main()