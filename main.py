"""
SciAgent 命令行入口。
用法：python main.py
"""

from sciagent.agent import Agent


def print_event(event):
    """在终端打印 Agent 事件"""
    icons = {
        "thinking": "\u2728",
        "tool_call": "\U0001f4bb",
        "tool_result": "\u2705",
        "error": "\u274c",
        "answer": "\U0001f4dd",
    }
    icon = icons.get(event.event_type, " ")

    if event.event_type == "tool_call":
        code = event.metadata.get("code", "")
        print(f"\n{icon} {event.content}")
        if code:
            # 只显示代码前 10 行的预览
            lines = code.strip().split("\n")
            preview = "\n".join(lines[:10])
            if len(lines) > 10:
                preview += f"\n... ({len(lines) - 10} more lines)"
            print(f"{'─' * 40}")
            print(preview)
            print(f"{'─' * 40}")
    elif event.event_type == "tool_result":
        # 截断过长的输出
        text = event.content
        if len(text) > 500:
            text = text[:500] + "\n... (output truncated)"
        print(f"\n{icon} 执行结果:\n{text}")
    elif event.event_type == "answer":
        print(f"\n{'═' * 50}")
        print(f"{icon} Agent 回答:\n")
        print(event.content)
        print(f"{'═' * 50}")
    else:
        print(f"\n{icon} {event.content}")


def main():
    print("=" * 50)
    print("  SciAgent - 科学计算智能体")
    print("  输入自然语言描述你的计算/优化问题")
    print("  输入 'quit' 退出")
    print("=" * 50)

    agent = Agent()

    while True:
        print()
        user_input = input("你> ").strip()

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("再见！")
            break

        result = agent.run(user_input, on_event=print_event)


if __name__ == "__main__":
    main()
