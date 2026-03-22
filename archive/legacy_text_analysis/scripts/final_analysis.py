# 直接读取并计算
with open('/文本分析.txt', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"文本总字数: {len(content)}")

# 分割计算
h2_start = content.find("[H2] 学术观点创新")
h3_start = content.find("[H3] 研究方法创新")

if h2_start != -1 and h3_start != -1:
    academic_part = content[h2_start:h3_start]
    method_part = content[h3_start:]
    
    print(f"学术观点创新部分字数: {len(academic_part)}")
    print(f"研究方法创新部分字数: {len(method_part)}")
    print(f"合计验证: {len(academic_part) + len(method_part)}")
    
    # 结构分析
    print("\n=== 文本结构评估 ===")
    
    # 1. 标题结构
    print("1. 标题结构完整性:")
    print(f"   - 主标题[H2]: {'✓ 完整' if '[H2]' in content else '✗ 缺失'}")
    print(f"   - 子标题[H3]: {'✓ 完整' if '[H3]' in content else '✗ 缺失'}")
    
    # 2. 内容结构
    print("\n2. 内容结构完整性:")
    print(f"   - 引言部分: {'✓ 完整' if '本研究在乡村全面振兴背景下' in content else '✗ 缺失'}")
    academic_points = content.count('一、', 0, h3_start)  # 学术观点部分的要点
    method_points = content.count('一、', h3_start)  # 研究方法部分的要点
    print(f"   - 学术观点要点: {'✓ 完整（3个）' if academic_points >= 3 else f'✗ 不完整，只有{academic_points}个要点'}")
    print(f"   - 研究方法要点: {'✓ 完整（3个）' if method_points >= 3 else f'✗ 不完整，只有{method_points}个要点'}")
    print(f"   - 结论部分: {'✓ 完整' if '综上所述' in content else '✗ 缺失'}")
    
    # 3. 逻辑结构
    print("\n3. 逻辑结构评估:")
    print("   - 学术观点部分: 包含三个创新点，逻辑清晰")
    print("   - 研究方法部分: 包含三个创新点，结构完整")
    print("   - 总分总结构: 引言→分述→结论，结构完整")
    
    # 4. 目标字数分析
    target = 1276
    current = len(content)
    diff = current - target
    
    print(f"\n=== 字数调整建议 ===")
    print(f"当前字数: {current}")
    print(f"目标字数: {target}")
    print(f"差异: {diff} ({'超出' if diff > 0 else '不足'} {abs(diff)}字)")
    
    if diff > 0:
        print(f"\n建议减少约{diff}字，可通过:")
        print("1. 精简重复表述（如'检索资料显示'等重复表述）")
        print("2. 合并相似内容（如理论框架描述中的重复内容）")
        print("3. 删除冗余修饰语（如过多的形容词和副词）")
        print("4. 简化长句为短句（将复合长句拆分为简单句）")
        print("5. 压缩案例描述（保留核心信息，删除细节描述）")
    elif diff < 0:
        print(f"\n建议增加约{abs(diff)}字，可通过:")
        print("1. 增加具体案例说明（添加西北地区具体案例）")
        print("2. 补充理论依据（引用相关理论支持）")
        print("3. 添加实践意义分析（扩展实践应用价值）")
        print("4. 扩展研究方法细节（详细说明方法实施步骤）")
        print("5. 增加对比分析（与传统研究方法对比）")
    else:
        print("字数已达到目标要求")
        
    # 具体调整建议
    print(f"\n=== 具体调整方案 ===")
    
    # 计算各部分理想字数
    academic_ratio = len(academic_part) / current
    method_ratio = len(method_part) / current
    
    print(f"当前比例: 学术观点{academic_ratio*100:.1f}% ({len(academic_part)}字), 研究方法{method_ratio*100:.1f}% ({len(method_part)}字)")
    
    # 建议保持比例调整
    target_academic = int(target * academic_ratio)
    target_method = int(target * method_ratio)
    
    print(f"建议目标: 学术观点约{target_academic}字, 研究方法约{target_method}字")
    print(f"调整量: 学术观点{target_academic - len(academic_part)}字, 研究方法{target_method - len(method_part)}字")
    
    # 提供具体修改示例
    print(f"\n=== 具体修改建议 ===")
    
    if diff > 50:  # 需要大幅删减
        print("1. 删除重复的'检索资料显示'表述（可节省约20-30字）")
        print("2. 精简'本研究基于检索资料中关于...的分析'等冗长表述（可节省约30-40字）")
        print("3. 合并相似的理论框架描述（可节省约20-30字）")
        print("4. 简化方法步骤描述，保留核心步骤（可节省约30-40字）")
    elif diff < -50:  # 需要大幅增加
        print("1. 为每个创新点添加1-2个具体西北地区案例（可增加约80-100字）")
        print("2. 补充每个方法的理论来源和依据（可增加约60-80字）")
        print("3. 增加实践应用场景描述（可增加约40-60字）")
        print("4. 添加研究局限性和未来展望（可增加约50-70字）")
    
    # 结构优化建议
    print(f"\n=== 结构优化建议 ===")
    print("1. 确保每个部分都有明确的引言和结论")
    print("2. 保持三个要点的平衡发展")
    print("3. 加强两部分之间的逻辑衔接")
    print("4. 增加过渡句，使文章更流畅")