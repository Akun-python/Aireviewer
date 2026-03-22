import re

def count_chinese_characters(text):
    """计算中文字符数（包括标点符号）"""
    # 读取文件内容
    with open('/文本分析.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 计算总字符数
    total_chars = len(content)
    
    # 分割学术观点创新部分和研究方法创新部分
    # 找到[H2]和[H3]的位置
    h2_index = content.find('[H2] 学术观点创新')
    h3_index = content.find('[H3] 研究方法创新')
    
    if h2_index != -1 and h3_index != -1:
        # 学术观点创新部分：从[H2]到[H3]之前
        academic_part = content[h2_index:h3_index]
        # 研究方法创新部分：从[H3]到结尾
        method_part = content[h3_index:]
        
        print(f"总字符数: {total_chars}")
        print(f"学术观点创新部分字符数: {len(academic_part)}")
        print(f"研究方法创新部分字符数: {len(method_part)}")
        
        return total_chars, len(academic_part), len(method_part)
    else:
        print("无法找到[H2]或[H3]标记")
        return total_chars, 0, 0

if __name__ == "__main__":
    total, academic, method = count_chinese_characters('/文本分析.txt')
    
    print("\n详细分析:")
    print(f"1. 文本总字数: {total} 字符")
    print(f"2. 学术观点创新部分字数: {academic} 字符")
    print(f"3. 研究方法创新部分字数: {method} 字符")
    print(f"4. 两部分字数比例: 学术观点:{academic/total*100:.1f}%, 研究方法:{method/total*100:.1f}%")