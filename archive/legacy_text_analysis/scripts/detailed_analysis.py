import re

def analyze_text_structure(text):
    """分析文本结构和内容"""
    
    # 分割主要部分
    parts = text.split('[H2]')
    if len(parts) > 1:
        main_part = parts[1]
        # 进一步分割H3部分
        h3_parts = main_part.split('[H3]')
        
        print("=== 文本结构分析 ===")
        print(f"1. 主要部分数量: {len(parts)}")
        print(f"2. H3子部分数量: {len(h3_parts)}")
        print()
        
        # 分析第一部分（国内外研究综述）
        if len(h3_parts) >= 1:
            research_review = h3_parts[0]
            print("=== 第一部分：国内外研究综述 ===")
            
            # 检查关键内容点
            key_points = [
                ("乡村振兴战略", "核心纲领提及"),
                ("西北地区", "地域聚焦"),
                ("国内研究三个层面", "国内研究分析"),
                ("地域不平衡性", "区域差异分析"),
                ("国际研究视角", "国际比较"),
                ("研究方法多元化", "方法论分析"),
                ("2025年国家社科基金", "研究前沿性"),
                ("研究不足四个方面", "问题分析"),
                ("研究意义", "研究价值阐述")
            ]
            
            for keyword, description in key_points:
                if keyword in research_review:
                    print(f"✓ 包含: {description}")
                else:
                    print(f"✗ 缺失: {description}")
            
            print()
        
        # 分析第二部分（学术价值与应用价值）
        if len(h3_parts) >= 2:
            value_part = h3_parts[1]
            print("=== 第二部分：学术价值与应用价值 ===")
            
            # 检查学术价值
            academic_keywords = [
                ("理论内涵", "理论深化"),
                ("范式创新", "研究视角转变"),
                ("实践模式理论", "模式构建"),
                ("学科体系", "学科建设")
            ]
            
            print("学术价值分析:")
            for keyword, description in academic_keywords:
                if keyword in value_part:
                    print(f"✓ 包含: {description}")
                else:
                    print(f"✗ 缺失: {description}")
            
            print()
            
            # 检查应用价值
            application_keywords = [
                ("实践指导", "政策建议"),
                ("社会治理创新", "治理效能"),
                ("民族团结进步", "民族关系"),
                ("高校服务", "校地合作"),
                ("经验参考", "可推广性")
            ]
            
            print("应用价值分析:")
            for keyword, description in application_keywords:
                if keyword in value_part:
                    print(f"✓ 包含: {description}")
                else:
                    print(f"✗ 缺失: {description}")
    
    return True

def count_words_detailed(text):
    """详细统计字数"""
    
    # 移除标题标记
    clean_text = re.sub(r'\[H[23]\]\s*', '', text)
    
    # 统计中文字符
    chinese_chars = re.findall(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', clean_text)
    chinese_count = len(chinese_chars)
    
    # 统计段落
    paragraphs = [p for p in clean_text.split('\n\n') if p.strip()]
    paragraph_count = len(paragraphs)
    
    # 统计句子
    sentences = re.split(r'[。！？；]', clean_text)
    sentences = [s.strip() for s in sentences if s.strip()]
    sentence_count = len(sentences)
    
    # 统计平均段落长度
    avg_paragraph_length = chinese_count / paragraph_count if paragraph_count > 0 else 0
    
    # 统计平均句子长度
    avg_sentence_length = chinese_count / sentence_count if sentence_count > 0 else 0
    
    print("=== 字数统计 ===")
    print(f"中文字符数: {chinese_count}")
    print(f"段落数: {paragraph_count}")
    print(f"句子数: {sentence_count}")
    print(f"平均段落长度: {avg_paragraph_length:.1f} 字/段")
    print(f"平均句子长度: {avg_sentence_length:.1f} 字/句")
    print()
    
    return chinese_count

def check_academic_rigor(text):
    """检查学术严谨性"""
    
    print("=== 学术严谨性检查 ===")
    
    # 检查学术术语使用
    academic_terms = [
        "研究综述", "理论建构", "范式创新", "学科体系",
        "实证研究", "理论思辨", "案例分析", "系统性",
        "多维度的分析框架", "运行机制", "实践模式"
    ]
    
    term_count = 0
    for term in academic_terms:
        if term in text:
            term_count += 1
    
    print(f"学术术语使用: {term_count}/{len(academic_terms)} 个术语被使用")
    
    # 检查引用和参考文献提及
    if "文献" in text or "研究" in text or "学者" in text:
        print("✓ 包含对现有研究的引用")
    else:
        print("✗ 缺乏对现有研究的引用")
    
    # 检查逻辑连接词
    logical_connectors = ["首先", "其次", "第三", "第四", "第五", "基于以上分析", "综上所述", "值得注意的是", "特别需要指出的是"]
    connector_count = 0
    for connector in logical_connectors:
        if connector in text:
            connector_count += 1
    
    print(f"逻辑连接词使用: {connector_count}/{len(logical_connectors)} 个连接词被使用")
    
    # 检查问题-分析-解决方案结构
    has_problem = any(word in text for word in ["不足", "问题", "挑战", "缺乏"])
    has_analysis = any(word in text for word in ["分析", "探讨", "研究", "考察"])
    has_solution = any(word in text for word in ["对策", "建议", "路径", "优化", "方案"])
    
    print(f"问题-分析-解决方案结构: {'✓' if has_problem and has_analysis and has_solution else '✗'}")
    if has_problem:
        print("  - 包含问题描述")
    if has_analysis:
        print("  - 包含分析探讨")
    if has_solution:
        print("  - 包含解决方案")
    
    return True

def main():
    # 读取文件
    with open('/text_analysis.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("=" * 60)
    print("文本分析报告")
    print("=" * 60)
    print()
    
    # 字数统计
    word_count = count_words_detailed(content)
    
    # 目标检查
    target_count = 2297
    print("=== 字数目标检查 ===")
    print(f"当前字数: {word_count}")
    print(f"目标字数: {target_count}")
    print(f"差异: {word_count - target_count} 字 ({((word_count - target_count)/target_count)*100:.1f}%)")
    
    if word_count >= target_count * 0.95 and word_count <= target_count * 1.05:
        print("✓ 字数接近目标范围（±5%）")
    elif word_count < target_count:
        print(f"⚠ 字数不足，需要增加约 {target_count - word_count} 字")
    else:
        print(f"⚠ 字数超出，需要减少约 {word_count - target_count} 字")
    
    print()
    
    # 结构分析
    analyze_text_structure(content)
    
    # 学术严谨性检查
    check_academic_rigor(content)
    
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()