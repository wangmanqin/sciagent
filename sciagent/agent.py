"""
Agent 主循环 — 整个项目的核心。
实现 ReAct（Reasoning + Acting）模式：
  LLM 思考 → 调用工具 → 观察结果 → 继续思考 → ... → 输出最终回答
"""

from sciagent.llm import create_llm, LLMResponse
from sciagent.tools import TOOL_DEFINITIONS, TOOL_EXECUTORS
from sciagent.prompts import SYSTEM_PROMPT

MAX_ITERATIONS = 10  # 防止无限循环


class AgentEvent:
    """Agent 执行过程中的事件，用于前端展示"""

    def __init__(self, event_type: str, content: str, metadata: dict = None):
        self.event_type = event_type  # "thinking", "tool_call", "tool_result", "answer", "error"
        self.content = content
        self.metadata = metadata or {}


class Agent:
    def __init__(self, llm_mode: str = None):
        self.llm = create_llm(llm_mode)
        self.messages = []
        self.events = []  # 记录每一步，供前端展示

    def _add_event(self, event_type: str, content: str, **metadata):
        event = AgentEvent(event_type, content, metadata)
        self.events.append(event)
        return event

    def _execute_tool(self, name: str, arguments: dict) -> str:
        """执行一个工具调用"""
        executor = TOOL_EXECUTORS.get(name)
        if not executor:
            return f"ERROR: 未知工具 '{name}'"
        try:
            return executor(arguments)
        except Exception as e:
            return f"ERROR: 工具执行异常 — {type(e).__name__}: {e}"

    def run(self, user_query: str, on_event=None):
        """
        运行 Agent。

        Args:
            user_query: 用户的自然语言输入
            on_event: 回调函数，每产生一个事件就调用一次（用于实时展示）

        Returns:
            最终的文字回答
        """
        self.events = []

        def emit(event_type, content, **meta):
            ev = self._add_event(event_type, content, **meta)
            if on_event:
                on_event(ev)

        # 初始化消息列表
        self.messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_query},
        ]

        emit("thinking", "正在分析问题...")

        for iteration in range(MAX_ITERATIONS):
            # 调用 LLM
            response = self.llm.chat(self.messages, tools=TOOL_DEFINITIONS)

            # 如果有文字输出，记录
            if response.text:
                if response.has_tool_calls:
                    emit("thinking", response.text)
                else:
                    emit("answer", response.text)

            # 如果没有工具调用，Agent 完成了
            if not response.has_tool_calls:
                return response.text

            # 构建 assistant 消息（包含 text + tool_use）
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            for tc in response.tool_calls:
                assistant_content.append({
                    "type": "tool_use",
                    "id": tc.id,
                    "name": tc.name,
                    "input": tc.arguments,
                })
            self.messages.append({"role": "assistant", "content": assistant_content})

            # 执行每个工具调用
            tool_results = []
            for tc in response.tool_calls:
                emit("tool_call", f"调用工具: {tc.name}", code=tc.arguments.get("code", ""))

                result = self._execute_tool(tc.name, tc.arguments)

                is_error = result.startswith("ERROR")
                if is_error:
                    emit("error", f"执行出错，Agent 将尝试修正...\n{result}")
                else:
                    emit("tool_result", result)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc.id,
                    "content": result,
                    "is_error": is_error,
                })

            # 把工具执行结果追加到消息列表
            self.messages.append({"role": "user", "content": tool_results})

        # 超过最大迭代次数
        emit("error", f"Agent 已执行 {MAX_ITERATIONS} 轮仍未完成，强制停止。")
        return "抱歉，问题处理未能在限定步数内完成。请尝试简化问题描述。"
