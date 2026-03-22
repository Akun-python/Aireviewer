import subprocess
import sys

print("运行文本分析...")
print("=" * 50)

try:
    # 运行分析脚本
    result = subprocess.run([sys.executable, '/final_analysis.py'], 
                          capture_output=True, text=True, encoding='utf-8')
    
    if result.stdout:
        print(result.stdout)
    
    if result.stderr:
        print("错误:", result.stderr)
        
except Exception as e:
    print(f"运行错误: {e}")
    
print("\n" + "=" * 50)
print("分析完成")