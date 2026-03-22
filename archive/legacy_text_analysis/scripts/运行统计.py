import subprocess
import sys

# 运行字数统计工具
try:
    result = subprocess.run([sys.executable, '/字数统计工具.py'], 
                          capture_output=True, text=True, encoding='utf-8')
    print(result.stdout)
    if result.stderr:
        print("错误信息:", result.stderr)
except Exception as e:
    print(f"运行错误: {e}")
    
# 直接计算
print("\n=== 直接计算 ===")
with open('/文本分析.txt', 'r', encoding='utf-8') as f:
    text = f.read()
    
print(f"总字符数: {len(text)}")

# 分割计算
h2_pos = text.find("[H2] 学术观点创新")
h3_pos = text.find("[H3] 研究方法创新")

if h2_pos != -1 and h3_pos != -1:
    academic = text[h2_pos:h3_pos]
    method = text[h3_pos:]
    
    print(f"学术观点部分: {len(academic)} 字符")
    print(f"研究方法部分: {len(method)} 字符")
    print(f"合计: {len(academic) + len(method)} 字符")