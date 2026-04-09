"""
工具定义与执行。
Agent 可以调用的工具在这里注册和实现。
"""

import subprocess
import sys
import os
import glob
import tempfile

# Agent 生成的文件都放在这个目录
OUTPUTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")


def run_python_code(code: str) -> str:
    """
    执行一段 Python 代码，返回 stdout/stderr。
    如果代码生成了图片文件，也会报告文件路径。
    """
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

    # 记录执行前已有的 png 文件
    existing_pngs = set(glob.glob(os.path.join(OUTPUTS_DIR, "*.png")))

    # 写入临时脚本
    script_path = os.path.join(OUTPUTS_DIR, "_temp_script.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(code)

    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=OUTPUTS_DIR,
        )
    except subprocess.TimeoutExpired:
        return "ERROR: 代码执行超时（60秒限制）。请检查是否有死循环或计算量过大。"

    output_parts = []

    if result.stdout.strip():
        output_parts.append(f"STDOUT:\n{result.stdout.strip()}")

    if result.returncode != 0 and result.stderr.strip():
        output_parts.append(f"ERROR:\n{result.stderr.strip()}")

    # 检测新生成的图片
    current_pngs = set(glob.glob(os.path.join(OUTPUTS_DIR, "*.png")))
    new_pngs = current_pngs - existing_pngs
    if new_pngs:
        png_list = "\n".join(f"  - {os.path.basename(p)}" for p in sorted(new_pngs))
        output_parts.append(f"GENERATED FILES:\n{png_list}")

    if not output_parts:
        return "代码执行成功，无输出。"

    return "\n\n".join(output_parts)


# ---- Claude API 的 tool 定义格式 ----

TOOL_DEFINITIONS = [
    {
        "name": "run_python_code",
        "description": (
            "在本地 Python 环境中执行一段代码。"
            "环境已安装 numpy, scipy, matplotlib, deap。"
            "代码中需要 print() 输出结果才能被捕获。"
            "如果要生成图表，请用 plt.savefig('filename.png') 保存到当前目录。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "要执行的完整 Python 代码",
                }
            },
            "required": ["code"],
        },
    }
]

# 工具名称 -> 执行函数的映射
TOOL_EXECUTORS = {
    "run_python_code": lambda args: run_python_code(args["code"]),
}
