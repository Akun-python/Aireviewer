#!/usr/bin/env python3
import subprocess
import sys

# 运行计数脚本
result = subprocess.run([sys.executable, "/count_text.py"], 
                       capture_output=True, text=True, encoding='utf-8')
print(result.stdout)
if result.stderr:
    print("错误信息：", result.stderr)