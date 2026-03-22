#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

# 读取文本文件
with open('/text_to_count.txt', 'r', encoding='utf-8') as f:
    text = f.read()

print("正在分析文本...")
print(f"原始文本长度: {len(text)} 字符")

# 方法1：直接统计中文字符（包括在标点中的）
chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)
print(f"方法1 - 所有中文字符数: {len(chinese_chars)}")

# 方法2：先移除标点符号和空格，再统计
# 移除标点符号
no_punct = re.sub(r'[。，、；：！？""\'\'（）《》【】『』「」〔〕…—～.,;:!?"\'()\[\]{}<>\-~ ]', '', text)
# 移除数字
no_punct_num = re.sub(r'\d+', '', no_punct)
# 移除英文字母
no_punct_num_eng = re.sub(r'[a-zA-Z]', '', no_punct_num)
# 移除[H2]、[H3]等标记
clean_text = re.sub(r'\[H\d+\]', '', no_punct_num_eng)

# 统计中文字符
final_chinese_chars = re.findall(r'[\u4e00-\u9fff]', clean_text)
print(f"方法2 - 纯净中文字符数（排除标点、空格、数字、英文）: {len(final_chinese_chars)}")

# 显示一些样本
print("\n前100个统计到的中文字符:")
sample = ''.join(final_chinese_chars[:100])
for i in range(0, len(sample), 50):
    print(f"  {sample[i:i+50]}")

print(f"\n最后50个统计到的中文字符:")
sample_end = ''.join(final_chinese_chars[-50:])
print(f"  {sample_end}")

print("\n统计完成！")