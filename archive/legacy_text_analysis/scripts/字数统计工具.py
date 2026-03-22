def count_chars(text):
    """统计中文字符数"""
    return len(text)

# 读取整个文件
with open('/文本分析.txt', 'r', encoding='utf-8') as f:
    full_text = f.read()

# 分割文本
h2_marker = "[H2] 学术观点创新"
h3_marker = "[H3] 研究方法创新"

h2_pos = full_text.find(h2_marker)
h3_pos = full_text.find(h3_marker)

if h2_pos != -1 and h3_pos != -1:
    # 学术观点创新部分
    academic_text = full_text[h2_pos:h3_pos]
    # 研究方法创新部分
    method_text = full_text[h3_pos:]
    
    total_chars = count_chars(full_text)
    academic_chars = count_chars(academic_text)
    method_chars = count_chars(method_text)
    
    print("=== 字数统计结果 ===")
    print(f"1. 文本总字数: {total_chars} 字符")
    print(f"2. 学术观点创新部分字数: {academic_chars} 字符")
    print(f"3. 研究方法创新部分字数: {method_chars} 字符")
    print(f"4. 字数验证: {academic_chars + method_chars} 字符 (应与总字数一致)")
    print(f"5. 学术观点部分占比: {academic_chars/total_chars*100:.1f}%")
    print(f"6. 研究方法部分占比: {method_chars/total_chars*100:.1f}%")
    
    # 分析文本结构
    print("\n=== 文本结构分析 ===")
    
    # 检查结构完整性
    has_h2 = h2_marker in full_text
    has_h3 = h3_marker in full_text
    has_intro = "本研究在乡村全面振兴背景下" in full_text
    has_conclusion = "综上所述" in full_text
    
    print(f"1. 包含[H2]标题: {'是' if has_h2 else '否'}")
    print(f"2. 包含[H3]标题: {'是' if has_h3 else '否'}")
    print(f"3. 包含引言部分: {'是' if has_intro else '否'}")
    print(f"4. 包含结论部分: {'是' if has_conclusion else '否'}")
    
    # 检查三个要点
    academic_points = full_text.count("一、")
    method_points = full_text.count("一、", h3_pos)  # 从H3位置开始计数
    
    print(f"5. 学术观点部分要点数: {academic_points}")
    print(f"6. 研究方法部分要点数: {method_points}")
    
    # 目标字数分析
    target_words = 1276
    difference = total_chars - target_words
    print(f"\n=== 目标字数分析 ===")
    print(f"当前字数: {total_chars} 字符")
    print(f"目标字数: {target_words} 字符")
    print(f"字数差异: {difference} 字符 ({'+' if difference > 0 else ''}{difference})")
    print(f"需要调整: {'增加' if difference < 0 else '减少'} {abs(difference)} 字符")
    
else:
    print("无法找到H2或H3标记")