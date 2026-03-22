import subprocess
import sys

# 运行计算字数的脚本
result = subprocess.run([sys.executable, '/计算字数.py'], capture_output=True, text=True, encoding='utf-8')
print(result.stdout)
if result.stderr:
    print("错误:", result.stderr)