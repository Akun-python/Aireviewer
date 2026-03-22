import subprocess
import sys

# 运行最终统计脚本
try:
    result = subprocess.run(
        [sys.executable, "/final_count.py"],
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    print(result.stdout)
    if result.stderr:
        print("错误信息:", result.stderr)
except Exception as e:
    print(f"运行出错: {e}")
    # 如果子进程运行失败，直接执行代码
    print("尝试直接执行统计...")
    exec(open("/final_count.py", "r", encoding='utf-8').read())