import subprocess
import sys

# 运行统计脚本
result = subprocess.run([sys.executable, "/count_chinese_chars.py"], 
                       capture_output=True, text=True, encoding='utf-8')
print(result.stdout)
if result.stderr:
    print("错误信息:", result.stderr)