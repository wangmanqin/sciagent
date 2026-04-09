"""
SciAgent Streamlit 前端。
用法：streamlit run app.py
"""

import streamlit as st
import os
import json
import glob
from datetime import datetime
from sciagent.agent import Agent
from sciagent.tools import OUTPUTS_DIR

# 历史记录保存路径
HISTORY_DIR = os.path.join(os.path.dirname(__file__), "history")
HISTORY_FILE = os.path.join(HISTORY_DIR, "chat_history.json")

st.set_page_config(page_title="SciAgent", page_icon="\U0001f52c", layout="wide")


# ---- 历史记录读写 ----

def load_history():
    """从文件加载历史记录"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_history(history):
    """保存历史记录到文件"""
    os.makedirs(HISTORY_DIR, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


# ---- 初始化 ----

if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_history()

st.title("\U0001f52c SciAgent")
st.caption("Natural Language-Driven Scientific Computing Agent")

# ---- 侧边栏 ----
with st.sidebar:
    st.header("Settings")
    llm_mode = st.selectbox("LLM Mode", ["auto", "deepseek", "mock", "claude"], index=0)

    st.markdown("---")

    # 历史问题列表
    st.header("History")
    history = st.session_state.chat_history
    user_questions = [
        (i, msg) for i, msg in enumerate(history) if msg["role"] == "user"
    ]

    if user_questions:
        for idx, msg in reversed(user_questions):
            # 找到这个问题对应的时间
            time_str = msg.get("time", "")
            label = msg["content"][:40]
            if len(msg["content"]) > 40:
                label += "..."
            if time_str:
                label = f"{time_str}  {label}"
            st.text(label)
    else:
        st.caption("No history yet")

    st.markdown("---")

    if st.button("Clear History"):
        st.session_state.chat_history = []
        save_history([])
        st.rerun()

    st.markdown("---")
    st.markdown(
        "**Example queries:**\n"
        "- *优化矩形微通道散热器，通道宽度0.1-1mm，深度0.2-2mm，最小化热阻和压降*\n"
        "- *用 NSGA-II 求解 ZDT1 测试函数*\n"
        "- *计算并可视化 Rosenbrock 函数的等高线图*"
    )

# ---- 显示对话历史 ----
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        for img in msg.get("images", []):
            if os.path.exists(img):
                st.image(img)

# ---- 用户输入 ----
user_input = st.chat_input("描述你的计算/优化问题...")

if user_input:
    # 保存用户消息（带时间戳）
    time_str = datetime.now().strftime("%m/%d %H:%M")
    user_msg = {"role": "user", "content": user_input, "time": time_str}
    st.session_state.chat_history.append(user_msg)
    with st.chat_message("user"):
        st.markdown(user_input)

    # 运行 Agent
    with st.chat_message("assistant"):
        status = st.status("Agent 正在工作...", expanded=True)

        agent = Agent(llm_mode=llm_mode if llm_mode != "auto" else None)

        tool_call_count = [0]  # 用列表包装，这样内部函数可以修改

        def on_event(event):
            icons = {
                "thinking": "\u2728",
                "tool_call": "\U0001f4bb",
                "tool_result": "\u2705",
                "error": "\u274c",
                "answer": "\U0001f4dd",
            }
            icon = icons.get(event.event_type, " ")

            if event.event_type == "tool_call":
                tool_call_count[0] += 1
                code = event.metadata.get("code", "")
                status.write(f"{icon} **[Round {tool_call_count[0]}] {event.content}**")
                if code:
                    status.code(code, language="python")
            elif event.event_type == "tool_result":
                status.write(f"{icon} 执行成功")
                with status.expander("查看输出"):
                    st.text(event.content[:1000])
            elif event.event_type == "error":
                status.write(f"{icon} {event.content[:200]}")
            elif event.event_type == "thinking":
                status.write(f"{icon} {event.content}")

        # 记录运行前已有的图片
        old_pngs = set(glob.glob(os.path.join(OUTPUTS_DIR, "*.png")))

        result = agent.run(user_input, on_event=on_event)

        status.update(label=f"Agent 完成 (executed {tool_call_count[0]} round(s) of code)", state="complete")

        # 显示最终回答
        st.markdown(result)

        # 只展示本次新生成的图片
        current_pngs = set(glob.glob(os.path.join(OUTPUTS_DIR, "*.png")))
        new_pngs = sorted(current_pngs - old_pngs)
        for img_path in new_pngs:
            st.image(img_path, caption=os.path.basename(img_path))

        # 保存到历史并持久化
        assistant_msg = {
            "role": "assistant",
            "content": result,
            "images": new_pngs,
            "time": datetime.now().strftime("%m/%d %H:%M"),
        }
        st.session_state.chat_history.append(assistant_msg)
        save_history(st.session_state.chat_history)
