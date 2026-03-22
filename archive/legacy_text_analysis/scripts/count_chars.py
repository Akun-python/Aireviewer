import re

def count_chinese_chars(text):
    """统计中文字符数（包括中文标点）"""
    # 匹配中文字符和中文标点
    chinese_pattern = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]')
    matches = chinese_pattern.findall(text)
    return len(matches)

def count_total_chars(text):
    """统计总字符数（包括空格）"""
    return len(text)

def main():
    # 读取文件
    with open('/text_analysis.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除标题标记（[H2]、[H3]）进行纯文本统计
    clean_content = re.sub(r'\[H[23]\]\s*', '', content)
    
    # 统计
    chinese_count = count_chinese_chars(clean_content)
    total_count = count_total_chars(clean_content)
    
    print(f"中文字符数（包括中文标点）: {chinese_count}")
    print(f"总字符数（包括所有字符和空格）: {total_count}")
    
    # 计算段落数
    paragraphs = [p for p in content.split('\n\n') if p.strip()]
    print(f"段落数: {len(paragraphs)}")
    
    # 计算句子数（粗略估计）
    sentences = re.split(r'[。！？；]', clean_content)
    sentences = [s for s in sentences if s.strip()]
    print(f"句子数（粗略）: {len(sentences)}")

if __name__ == "__main__":
    main()