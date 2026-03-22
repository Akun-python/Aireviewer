Quickstart  快速入门

Copy page  复制页面

Build your first deep agent in minutes
在几分钟内构建你的第一个深度代理

This guide walks you through creating your first deep agent with planning, file system tools, and subagent capabilities. You’ll build a research agent that can conduct research and write reports.
本指南将带你通过规划、文件系统工具和子代理功能来创建你的第一个深度代理。你将构建一个研究代理，它可以进行研究和撰写报告。
​
Prerequisites  前提条件
Before you begin, make sure you have an API key from a model provider (e.g., Anthropic, OpenAI).
开始之前，请确保你有一个来自模型提供者（例如，Anthropic、OpenAI）的 API 密钥。
Deep agents require a model that supports tool calling. See customization for how to configure your model.
深度代理需要一个支持工具调用的模型。有关如何配置模型的详细信息，请参阅自定义部分。
​
Step 1: Install dependencies
步骤 1：安装依赖项

pip

uv

poetry
  复制
pip install deepagents tavily-python
This guide uses Tavily as an example search provider, but you can substitute any search API (e.g., DuckDuckGo, SerpAPI, Brave Search).
本指南以 Tavily 作为示例搜索提供者，但您可以用任何搜索 API（例如，DuckDuckGo、SerpAPI、Brave Search）进行替换。
​
Step 2: Set up your API keys
步骤 2：设置你的 API 密钥
  复制
export ANTHROPIC_API_KEY="your-api-key"
export TAVILY_API_KEY="your-tavily-api-key"
​
Step 3: Create a search tool
第三步：创建一个搜索工具
  复制
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )
​
Step 4: Create a deep agent
第 4 步：创建深度代理
  复制
# System prompt to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""

agent = create_deep_agent(
    tools=[internet_search],
    system_prompt=research_instructions
)
​
Step 5: Run the agent
第五步：运行代理
  复制
result = agent.invoke({"messages": [{"role": "user", "content": "What is langgraph?"}]})

# Print the agent's response
print(result["messages"][-1].content)
​
What happened?  发生了什么？
Your deep agent automatically:
您的深度代理自动执行：
Planned its approach: Used the built-in write_todos tool to break down the research task
规划了方法：使用内置的 write_todos 工具分解研究任务
Conducted research: Called the internet_search tool to gather information
进行研究：调用 internet_search 工具收集信息
Managed context: Used file system tools (write_file, read_file) to offload large search results
管理上下文：使用文件系统工具（ write_file ， read_file ）将大型搜索结果卸载
Spawned subagents (if needed): Delegated complex subtasks to specialized subagents
生成子代理（如有需要）：将复杂的子任务委派给专业的子代理
Synthesized a report: Compiled findings into a coherent response
综合报告：将发现结果汇编成一个连贯的回应
​
Next steps  下一步
Now that you’ve built your first deep agent:
现在你已经构建了你的第一个深度代理：
Customize your agent: Learn about customization options, including custom system prompts, tools, and subagents.
自定义你的代理：了解自定义选项，包括自定义系统提示、工具和子代理。
Understand middleware: Dive into the middleware architecture that powers deep agents.
理解中间件：深入了解驱动深度代理的中间件架构。
Add long-term memory: Enable persistent memory across conversations.
添加长期记忆：启用跨对话的持久记忆。
Deploy to production: Learn about deployment options for LangGraph applications.
部署到生产环境：了解 LangGraph 应用的部署选项。


Customize Deep Agents  定制 Deep Agents

Copy page  复制页面

Learn how to customize deep agents with system prompts, tools, subagents, and more
学习如何使用系统提示、工具、子代理等自定义深度代理








create_deep_agent

Core Config

Features

Model

System Prompt

Tools

Backend

Subagents

Interrupts

Customized Agent

​
Model  模型
By default, deepagents uses claude-sonnet-4-5-20250929. You can customize the model used by passing any supported
默认情况下， deepagents 使用 claude-sonnet-4-5-20250929 。您可以通过传递任何支持的model identifier string or LangChain model object.
或 LangChain 模型对象来自定义所使用的模型。
Use the provider:model format (e.g., openai:gpt-5) to quickly switch between models.
使用 provider:model 格式（例如 openai:gpt-5 ）可以快速切换模型。

Model string
  模型字符串

LangChain model object
  LangChain 模型对象
  复制
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

model = init_chat_model(model="openai:gpt-5")
agent = create_deep_agent(model=model)
​
System prompt  系统提示
Deep agents come with a built-in system prompt inspired by Claude Code’s system prompt. The default system prompt contains detailed instructions for using the built-in planning tool, file system tools, and subagents.
深度代理内置了一个受 Claude Code 系统提示启发的系统提示。默认系统提示包含使用内置规划工具、文件系统工具和子代理的详细说明。
Each deep agent tailored to a use case should include a custom system prompt specific to that use case.
针对特定用例定制的每个深度代理都应包含一个针对该用例的定制系统提示。
  复制
from deepagents import create_deep_agent

research_instructions = """\
You are an expert researcher. Your job is to conduct \
thorough research, and then write a polished report. \
"""

agent = create_deep_agent(
    system_prompt=research_instructions,
)
​
Tools  工具
In addition to custom tools you provide, deep agents include built-in tools for planning, file management, and subagent spawning.
除了您提供的自定义工具外，深度代理还包括用于规划、文件管理和子代理生成的内置工具。
  复制
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

agent = create_deep_agent(
    tools=[internet_search]
)
​
Skills  技能
You can use skills to provide your deep agent with new capabilities and expertise. While tools tend to cover lower level functionality like native file system actions or planning, skills can contain detailed instructions on how to complete tasks, reference info, and other assets, such as templates. These files are only loaded by the agent when the agent has determined that the skill is useful for the current prompt. This progressive disclosure reduces the amount of tokens and context the agent has to consider upon startup.
您可以使用技能为您的深度代理提供新的功能和专业知识。虽然工具通常涵盖较低级别的功能（如原生文件系统操作或规划），但技能可以包含完成任务的详细说明、参考资料和其他资源，例如模板。这些文件仅在代理确定该技能对当前提示有用时才会加载。这种渐进式披露减少了代理在启动时需要考虑的令牌和上下文量。
For example skills, see Deep Agent example skills.
有关示例技能，请参阅深度代理示例技能。
To add skills to your deep agent, pass them as an argument to create_deep_agent:
为您的深度代理添加技能，将它们作为参数传递给 create_deep_agent :

StateBackend

StoreBackend

FilesystemBackend
  复制
from urllib.request import urlopen
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagentsjs/refs/heads/main/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

skills_files = {
    "/skills/langgraph-docs/SKILL.md": skill_content
}

agent = create_deep_agent(
    skills=["./skills/"],
    checkpointer=checkpointer,
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is langgraph?",
            }
        ],
        # Seed the default StateBackend's in-state filesystem (virtual paths must start with "/").
        "files": skills_files
    },
    config={"configurable": {"thread_id": "12345"}},
)
​
Memory  记忆
Use AGENTS.md files to provide extra context to your deep agent.
使用 AGENTS.md 文件为您的深度代理提供额外上下文。
You can pass one or more file paths to the memory parameter when creating your deep agent:
在创建深度代理时，您可以将一个或多个文件路径传递给 memory 参数：

StateBackend

StoreBackend

FilesystemBackend
  复制
from urllib.request import urlopen

from deepagents import create_deep_agent
from deepagents.backends.utils import create_file_data
from langgraph.checkpoint.memory import MemorySaver

with urlopen("https://raw.githubusercontent.com/langchain-ai/deepagents/refs/heads/master/examples/text-to-sql-agent/AGENTS.md") as response:
    agents_md = response.read().decode("utf-8")
checkpointer = MemorySaver()

agent = create_deep_agent(
    memory=[
        "/AGENTS.md"
    ],
    checkpointer=checkpointer,
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Please tell me what's in your memory files.",
            }
        ],
        # Seed the default StateBackend's in-state filesystem (virtual paths must start with "/").
        "files": {"/AGENTS.md": create_file_data(agents_md)},
    },
    config={"configurable": {"thread_id": "123456"}},
)

Core capabilities  核心功能
Agent harness capabilities
代理框架功能

Copy page  复制页面

We think of deepagents as an “agent harness”. It is the same core tool calling loop as other agent frameworks, but with built-in tools and capabilities.
我们将 deepagents 视为一个“代理框架”。它与其他代理框架相同，都是核心工具调用循环，但内置了工具和功能。







isolated work

Deep Agent

File System Tools

To-Do List

Subagents

Storage Backend

State

Filesystem

Store

Final Result

This page lists out the components that make up the agent harness.
本页面列出了构成代理框架的组件。
​
File system access  文件系统访问
The harness provides six tools for file system operations, making files first-class citizens in the agent’s environment:
该驱动程序提供六种用于文件系统操作的工具，使文件成为代理环境中的一流公民：
Tool  工具	Description  描述
ls	List files in a directory with metadata (size, modified time)
列出目录中的文件及其元数据（大小、修改时间）
read_file	Read file contents with line numbers, supports offset/limit for large files
读取文件内容并显示行号，支持对大文件进行偏移/限制
write_file	Create new files  创建新文件
edit_file	Perform exact string replacements in files (with global replace mode)
在文件中执行精确字符串替换（带全局替换模式）
glob	Find files matching patterns (e.g., **/*.py)
查找匹配模式的文件（例如， **/*.py ）
grep	Search file contents with multiple output modes (files only, content with context, or counts)
使用多种输出模式搜索文件内容（仅文件、带上下文的文件内容或计数）
​
Large tool result eviction
大型工具结果淘汰
The FilesystemMiddleware automatically evicts large tool results to the file system when they exceed a token threshold, preventing context window saturation.
FilesystemMiddleware 在结果超过标记阈值时自动将其从文件系统移除，防止上下文窗口饱和。
How it works:  工作原理：
Monitors tool call results for size (default threshold: 20,000 tokens, configurable via tool_token_limit_before_evict)
监控工具调用结果的大小（默认阈值：20,000 个标记，可通过 tool_token_limit_before_evict 配置）
When exceeded, writes the result using the configured backend
超过阈值时，使用配置的后端写入结果
Replaces the tool result with a truncated preview and file reference
用截断的预览和文件引用替换工具结果
Agent can read the full result from the file system as needed
Agent 可以根据需要从文件系统中读取完整结果
​
Pluggable storage backends
可插拔的存储后端
The harness abstracts file system operations behind a protocol, allowing different storage strategies for different use cases.
该框架将文件系统操作抽象为协议，允许针对不同用例采用不同的存储策略。
Available backends:  可用的后端：
StateBackend - Ephemeral in-memory storage
StateBackend - 临时内存存储
Files live in the agent’s state (checkpointed with conversation)
文件存储在代理的状态中（与对话一起检查点）
Persists within a thread but not across threads
在单个线程中持久化，但不同线程间不持久化
Useful for temporary working files
适用于临时工作文件
FilesystemBackend - Real filesystem access
FilesystemBackend - 真实文件系统访问
Read/write from actual disk
从实际磁盘读写
Supports virtual mode (sandboxed to a root directory)
支持虚拟模式（沙盒到根目录）
Integrates with system tools (ripgrep for grep)
与系统工具集成（使用 ripgrep 代替 grep）
Security features: path validation, size limits, symlink prevention
安全特性：路径验证、大小限制、防止符号链接
StoreBackend - Persistent cross-conversation storage
StoreBackend - 持久化跨对话存储
Uses LangGraph’s BaseStore for durability
使用 LangGraph 的 BaseStore 确保持久性
Namespaced per assistant_id  按 assistant_id 命名空间划分
Files persist across conversations
文件跨对话持久化
Useful for long-term memory or knowledge bases
适用于长期记忆或知识库
CompositeBackend - Route different paths to different backends
CompositeBackend - 将不同路径路由到不同的后端
Example: / → StateBackend, /memories/ → StoreBackend
示例： / → StateBackend, /memories/ → StoreBackend
Longest-prefix matching for routing
最长前缀匹配用于路由
Enables hybrid storage strategies
支持混合存储策略
See backends for configuration details and examples.
有关配置详情和示例，请参考后端部分。
​
Task delegation (subagents)
任务委派（子代理）
The harness allows the main agent to create ephemeral “subagents” for isolated multi-step tasks.
这个框架允许主代理为隔离的多步骤任务创建临时的“子代理”。
Why it’s useful:  它的用途：
Context isolation - Subagent’s work doesn’t clutter main agent’s context
上下文隔离 - 子代理的工作不会使主代理的上下文变得杂乱
Parallel execution - Multiple subagents can run concurrently
并行执行 - 多个子代理可以同时运行
Specialization - Subagents can have different tools/configurations
专业化 - 子代理可以有不同的工具/配置
Token efficiency - Large subtask context is compressed into a single result
标记效率 - 大型子任务上下文被压缩成一个结果
How it works:  工作原理：
Main agent has a task tool
主代理有一个 task 工具
When invoked, creates a fresh agent instance with its own context
调用时，创建一个具有独立上下文的新代理实例
Subagent executes autonomously until completion
子代理自主执行直至完成
Returns a single final report to the main agent
向主代理返回一份最终报告
Subagents are stateless (can’t send multiple messages back)
子代理是无状态的（不能发送多条消息）
Default subagent:  默认子代理：
“general-purpose” subagent automatically available
“通用”子代理自动可用
Has filesystem tools by default
默认具有文件系统工具
Can be customized with additional tools/middleware
可通过附加工具/中间件进行定制
Custom subagents:  自定义子代理：
Define specialized subagents with specific tools
定义具有特定工具的专用子代理
Example: code-reviewer, web-researcher, test-runner
示例：code-reviewer, web-researcher, test-runner
Configure via subagents parameter
通过 subagents 参数进行配置
​
Conversation history summarization
对话历史摘要
The harness automatically compresses old conversation history when token usage becomes excessive.
当 token 使用量过大时，harness 会自动压缩旧的对话历史。
Configuration:  配置：
Triggers at 85% of the model’s max_input_tokens from its model profile
在模型 max_input_tokens 的 85% 处触发，基于其模型配置
Keeps 10% of tokens as recent context
保留 10%的 token 作为最近的上下文
Falls back to 170,000 tokens trigger / 6 messages kept if model profile is unavailable
如果模型配置不可用，则回退到 170,000 个 token 触发/保留 6 条消息
Older messages are summarized by the model
旧消息由模型进行总结
Why it’s useful:  它的用途：
Enables very long conversations without hitting context limits
支持超长对话而不触及上下文限制
Preserves recent context while compressing ancient history
在压缩历史信息的同时保留近期上下文
Transparent to the agent (appears as a special system message)
对代理透明（表现为特殊的系统消息）
​
Dangling tool call repair
悬空工具调用修复
The harness fixes message history when tool calls are interrupted or cancelled before receiving results.
当工具调用在接收到结果之前被中断或取消时，该框架会修复消息历史。
The problem:  问题：
Agent requests tool call: “Please run X”
代理请求工具调用："请运行 X"
Tool call is interrupted (user cancels, error, etc.)
工具调用被中断（用户取消、错误等）
Agent sees tool_call in AIMessage but no corresponding ToolMessage
代理在 AIMessage 中看到 tool_call 但没有相应的 ToolMessage
This creates an invalid message sequence
这会创建一个无效的消息序列
The solution:  解决方案：
Detects AIMessage objects with tool_calls that have no results
检测到具有 tool_calls 但无结果的 AIMessage 对象
Creates synthetic ToolMessage responses indicating the call was cancelled
创建合成 ToolMessage 响应，表明调用已被取消
Repairs the message history before agent execution
在代理执行前修复消息历史
Why it’s useful:  它的用途：
Prevents agent confusion from incomplete message chains
防止因消息链不完整导致的代理混淆
Gracefully handles interruptions and errors
优雅地处理中断和错误
Maintains conversation coherence
保持对话连贯性
​
To-do list tracking  待办事项跟踪
The harness provides a write_todos tool that agents can use to maintain a structured task list.
该工具包提供了一个 write_todos 工具，供代理使用以维护结构化的任务列表。
Features:  功能：
Track multiple tasks with statuses ('pending', 'in_progress', 'completed')
跟踪多个任务及其状态（ 'pending' ， 'in_progress' ， 'completed' ）
Persisted in agent state
持久化代理状态
Helps agent organize complex multi-step work
帮助代理组织复杂的多步骤工作
Useful for long-running tasks and planning
适用于长时间运行的任务和规划
​
Human-in-the-loop  人机交互
The harness can pause agent execution at specified tool calls to allow human approval or modification. This feature is opt-in via the interrupt_on parameter.
该框架可以在指定的工具调用处暂停代理执行，以允许人工批准或修改。此功能通过 interrupt_on 参数选择启用。
Configuration:  配置：
Pass interrupt_on to create_deep_agent with a mapping of tool names to interrupt configurations
将 interrupt_on 传递给 create_deep_agent ，并附带工具名称到中断配置的映射
Example: interrupt_on={"edit_file": True} pauses before every edit
示例： interrupt_on={"edit_file": True} 在每次编辑前暂停
Can provide approval messages or modify tool inputs
可以提供审批消息或修改工具输入
Why it’s useful:  它的用途：
Safety gates for destructive operations
破坏性操作的防护措施
User verification before expensive API calls
在昂贵的 API 调用前进行用户验证
Interactive debugging and guidance
交互式调试和指导
​
Prompt caching (Anthropic)
提示缓存（Anthropic）
The harness enables Anthropic’s prompt caching feature to reduce redundant token processing.
这个工具使 Anthropic 的提示缓存功能得以实现，从而减少冗余的 token 处理。
How it works:  工作原理：
Caches portions of the prompt that repeat across turns
缓存跨回合重复的提示部分
Significantly reduces latency and cost for long system prompts
显著降低长系统提示的延迟和成本
Automatically skipped for non-Anthropic models
对于非 Anthropic 模型自动跳过
Why it’s useful:  它为什么有用：
System prompts (especially with filesystem docs) can be 5k+ tokens
系统提示（尤其是带有文件系统文档时）可能超过 5k 个 token
These repeat every turn without caching
这些在每个回合中重复，且不缓存
Caching provides ~10x speedup and cost reduction
缓存可提供约 10 倍的加速和成本降低


Backends  后端

Copy page  复制页面

Choose and configure filesystem backends for deep agents. You can specify routes to different backends, implement virtual filesystems, and enforce policies.
选择并配置深度代理的文件系统后端。您可以指定不同后端的路径，实现虚拟文件系统，并执行策略。

Deep agents expose a filesystem surface to the agent via tools like ls, read_file, write_file, edit_file, glob, and grep. These tools operate through a pluggable backend.
深度代理通过 ls 、 read_file 、 write_file 、 edit_file 、 glob 和 grep 等工具向代理暴露文件系统接口。这些工具通过可插拔的后端运行。







Filesystem Tools

Backend

State

Filesystem

Store

Composite

Custom

Routes

This page explains how to choose a backend, route different paths to different backends, implement your own virtual filesystem (e.g., S3 or Postgres), add policy hooks, and comply with the backend protocol.
本页面解释如何选择后端，将不同路径路由到不同后端，实现自己的虚拟文件系统（例如 S3 或 Postgres），添加策略钩子，并遵守后端协议。
​
Quickstart  快速入门
Here are a few pre-built filesystem backends that you can quickly use with your deep agent:
这里有一些预构建的文件系统后端，你可以快速与你的深度代理一起使用：
Built-in backend  内置后端	Description  描述
Default  默认	agent = create_deep_agent()
Ephemeral in state. The default filesystem backend for an agent is stored in langgraph state. Note that this filesystem only persists for a single thread.
状态短暂。代理的默认文件系统后端存储在 langgraph 状态中。请注意，这个文件系统仅对单个线程持久化。
Local filesystem persistence
本地文件系统持久化	agent = create_deep_agent(backend=FilesystemBackend(root_dir="/Users/nh/Desktop/"))
This gives the deep agent access to your local machine’s filesystem. You can specify the root directory that the agent has access to. Note that any provided root_dir must be an absolute path.
这使深度代理能够访问您的本地计算机的文件系统。您可以指定代理可以访问的根目录。请注意，提供的任何 root_dir 必须是绝对路径。
Durable store (LangGraph store)
持久存储（LangGraph 存储）	agent = create_deep_agent(backend=lambda rt: StoreBackend(rt))
This gives the agent access to long-term storage that is persisted across threads. This is great for storing longer term memories or instructions that are applicable to the agent over multiple executions.
这为代理提供了跨线程持久化的长期存储。这对于存储适用于多次执行代理的长期记忆或指令非常有利。
Composite  组合	Ephemeral by default, /memories/ persisted. The Composite backend is maximally flexible. You can specify different routes in the filesystem to point towards different backends. See Composite routing below for a ready-to-paste example.
默认情况下是暂时的， /memories/ 持久化。组合式后端具有最大的灵活性。您可以在文件系统中指定不同的路由指向不同的后端。有关组合式路由的示例，请参见下文。
​
Built-in backends  内置后端
​
StateBackend (ephemeral)  StateBackend（易失性）
  复制
# By default we provide a StateBackend
agent = create_deep_agent()

# Under the hood, it looks like
from deepagents.backends import StateBackend

agent = create_deep_agent(
    backend=(lambda rt: StateBackend(rt))   # Note that the tools access State through the runtime.state
)
How it works:  工作原理：
Stores files in LangGraph agent state for the current thread.
将文件存储在当前线程的 LangGraph 代理状态中。
Persists across multiple agent turns on the same thread via checkpoints.
通过检查点在同一个线程上的多个代理回合中持久化。
Best for:  最适合：
A scratch pad for the agent to write intermediate results.
一个供代理写入中间结果的草稿板。
Automatic eviction of large tool outputs which the agent can then read back in piece by piece.
自动清除大型工具输出，代理可以逐段重新读取。
Note that this backend is shared between the supervisor agent and subagents, and any files a subagent writes will remain in the LangGraph agent state even after that subagent’s execution is complete. Those files will continue to be available to the supervisor agent and other subagents.
注意，这个后端在主管代理和子代理之间共享，任何子代理写入的文件在子代理执行完成后仍会保留在 LangGraph 代理状态中。这些文件将继续对主管代理和其他子代理可用。
​
FilesystemBackend (local disk)
FilesystemBackend (本地磁盘)
This backend grants agents direct filesystem read/write access. Use with caution and only in appropriate environments.
这个后端授予代理直接文件系统读写访问权限。谨慎使用，仅在适当的环境中使用。
Appropriate use cases:  适当的用例：
Local development CLIs (coding assistants, development tools)
本地开发 CLI（编程助手、开发工具）
CI/CD pipelines (see security considerations below)
CI/CD 流水线（见下文安全注意事项）
Inappropriate use cases:  不恰当的使用场景：
Web servers or HTTP APIs - use StateBackend, StoreBackend, or SandboxBackend instead
Web 服务器或 HTTP API - 使用 StateBackend ， StoreBackend ，或 SandboxBackend 代替
Security risks:  安全风险：
Agents can read any accessible file, including secrets (API keys, credentials, .env files)
代理可以读取任何可访问的文件，包括机密文件（API 密钥、凭证、 .env 文件）
Combined with network tools, secrets may be exfiltrated via SSRF attacks
结合网络工具，机密文件可能通过 SSRF 攻击被窃取
File modifications are permanent and irreversible
文件修改是永久且不可逆的
Recommended safeguards:  建议的安全措施：
Enable Human-in-the-Loop (HITL) middleware to review sensitive operations.
启用人工审核中间件（HITL）以审查敏感操作。
Exclude secrets from accessible filesystem paths (especially in CI/CD).
将密钥排除在可访问的文件系统路径之外（尤其是在 CI/CD 中）。
Use SandboxBackend for production environments requiring filesystem interaction.
在生产环境中需要文件系统交互时，使用 SandboxBackend 。
Always use virtual_mode=True with root_dir to enable path-based access restrictions (blocks .., ~, and absolute paths outside root). Note that the default (virtual_mode=False) provides no security even with root_dir set.
始终使用 virtual_mode=True 与 root_dir 配合使用，以启用基于路径的访问限制（阻止 .. 、 ~ 以及根目录外的绝对路径）。请注意，默认的 virtual_mode=False 即使设置了 root_dir 也无法提供安全性。
  复制
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    backend=FilesystemBackend(root_dir=".", virtual_mode=True)
)
How it works:  工作原理：
Reads/writes real files under a configurable root_dir.
在可配置的 root_dir 下读取/写入真实文件。
You can optionally set virtual_mode=True to sandbox and normalize paths under root_dir.
你可以选择性地设置 virtual_mode=True 来沙盒化并在 root_dir 下规范化路径。
Uses secure path resolution, prevents unsafe symlink traversal when possible, can use ripgrep for fast grep.
使用安全路径解析，在可能的情况下防止不安全的符号链接遍历，可以使用 ripgrep 进行快速 grep 搜索。
Best for:  最适合：
Local projects on your machine
您本机上的本地项目
CI sandboxes  CI 沙盒
Mounted persistent volumes
挂载的持久卷
​
StoreBackend (LangGraph store)
  复制
from langgraph.store.memory import InMemoryStore
from deepagents.backends import StoreBackend

agent = create_deep_agent(
    backend=(lambda rt: StoreBackend(rt)),   # Note that the tools access Store through the runtime.store
    store=InMemoryStore()
)
How it works:  工作原理：
Stores files in a LangGraph BaseStore provided by the runtime, enabling cross‑thread durable storage.
将文件存储在运行时提供的 LangGraph BaseStore 中，实现跨线程持久化存储。
Best for:  最适合：
When you already run with a configured LangGraph store (for example, Redis, Postgres, or cloud implementations behind BaseStore).
当你已经使用配置好的 LangGraph 存储（例如 Redis、Postgres 或 BaseStore 背后的云实现）时。
When you’re deploying your agent through LangSmith Deployment (a store is automatically provisioned for your agent).
当你通过 LangSmith 部署你的代理时（系统会自动为你的代理配置存储）。
​
CompositeBackend (router)
CompositeBackend (路由器)
  复制
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/memories/": StoreBackend(rt),
    }
)

agent = create_deep_agent(
    backend=composite_backend,
    store=InMemoryStore()  # Store passed to create_deep_agent, not backend
)
How it works:  工作原理：
Routes file operations to different backends based on path prefix.
根据路径前缀将文件操作路由到不同的后端。
Preserves the original path prefixes in listings and search results.
在列表和搜索结果中保留原始路径前缀。
Best for:  最适合：
When you want to give your agent both ephemeral and cross-thread storage, a CompositeBackend allows you provide both a StateBackend and StoreBackend
当你希望为你的代理同时提供短暂和跨线程存储时，一个 CompositeBackend 允许你提供 StateBackend 和 StoreBackend
When you have multiple sources of information that you want to provide to your agent as part of a single filesystem.
当你有多个信息源，希望将它们作为单个文件系统的一部分提供给你的代理时。
e.g. You have long-term memories stored under /memories/ in one Store and you also have a custom backend that has documentation accessible at /docs/.
例如，你在某个 Store 下以 /memories/ 存储长期记忆，同时你还有一个自定义后端，其文档可通过 /docs/ 访问。
​
Specify a backend  指定一个后端
Pass a backend to create_deep_agent(backend=...). The filesystem middleware uses it for all tooling.
将后端传递给 create_deep_agent(backend=...) 。文件系统中间件使用它来处理所有工具。
You can pass either:  你可以传递：
An instance implementing BackendProtocol (for example, FilesystemBackend(root_dir=".")), or
一个实现 BackendProtocol 的实例（例如 FilesystemBackend(root_dir=".") ），或者
A factory BackendFactory = Callable[[ToolRuntime], BackendProtocol] (for backends that need runtime like StateBackend or StoreBackend).
一个工厂 BackendFactory = Callable[[ToolRuntime], BackendProtocol] （用于需要运行时支持的后端，如 StateBackend 或 StoreBackend ）。
If omitted, the default is lambda rt: StateBackend(rt).
如果省略，默认值为 lambda rt: StateBackend(rt) 。
​
Route to different backends
路由到不同的后端
Route parts of the namespace to different backends. Commonly used to persist /memories/* and keep everything else ephemeral.
将命名空间的不同部分路由到不同的后端。通常用于持久化 /memories/* ，而将其他所有内容设置为临时。
  复制
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, FilesystemBackend

composite_backend = lambda rt: CompositeBackend(
    default=StateBackend(rt),
    routes={
        "/memories/": FilesystemBackend(root_dir="/deepagents/myagent", virtual_mode=True),
    },
)

agent = create_deep_agent(backend=composite_backend)
Behavior:  行为：
/workspace/plan.md → StateBackend (ephemeral)   /workspace/plan.md → StateBackend (短暂的)
/memories/agent.md → FilesystemBackend under /deepagents/myagent
/memories/agent.md → FilesystemBackend 在 /deepagents/myagent 下
ls, glob, grep aggregate results and show original path prefixes.
ls 、 glob 、 grep 汇总结果并显示原始路径前缀。
Notes:  注意：
Longer prefixes win (for example, route "/memories/projects/" can override "/memories/").
较长的前缀优先（例如，route "/memories/projects/" 可以覆盖 "/memories/" ）。
For StoreBackend routing, ensure the agent runtime provides a store (runtime.store).
对于 StoreBackend 路由，确保代理运行时提供一个存储（ runtime.store ）。
​
Use a virtual filesystem  使用虚拟文件系统
Build a custom backend to project a remote or database filesystem (e.g., S3 or Postgres) into the tools namespace.
构建自定义后端以将远程或数据库文件系统（例如 S3 或 Postgres）映射到工具命名空间。
Design guidelines:  设计指南：
Paths are absolute (/x/y.txt). Decide how to map them to your storage keys/rows.
路径是绝对的 ( /x/y.txt )。决定如何将它们映射到你的存储键/行。
Implement ls_info and glob_info efficiently (server-side listing where available, otherwise local filter).
高效实现 ls_info 和 glob_info (在可用的情况下进行服务器端列出，否则进行本地过滤)。
Return user-readable error strings for missing files or invalid regex patterns.
对于缺失文件或无效正则表达式模式，返回用户可读的错误字符串。
For external persistence, set files_update=None in results; only in-state backends should return a files_update dict.
对于外部持久化，在结果中设置 files_update=None ；只有状态内后端应返回一个 files_update 字典。
S3-style outline:  S3 风格的提纲：
  复制
from deepagents.backends.protocol import BackendProtocol, WriteResult, EditResult
from deepagents.backends.utils import FileInfo, GrepMatch

class S3Backend(BackendProtocol):
    def __init__(self, bucket: str, prefix: str = ""):
        self.bucket = bucket
        self.prefix = prefix.rstrip("/")

    def _key(self, path: str) -> str:
        return f"{self.prefix}{path}"

    def ls_info(self, path: str) -> list[FileInfo]:
        # List objects under _key(path); build FileInfo entries (path, size, modified_at)
        ...

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        # Fetch object; return numbered content or an error string
        ...

    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str:
        # Optionally filter server‑side; else list and scan content
        ...

    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        # Apply glob relative to path across keys
        ...

    def write(self, file_path: str, content: str) -> WriteResult:
        # Enforce create‑only semantics; return WriteResult(path=file_path, files_update=None)
        ...

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        # Read → replace (respect uniqueness vs replace_all) → write → return occurrences
        ...
Postgres-style outline:  Postgres 风格大纲：
Table files(path text primary key, content text, created_at timestamptz, modified_at timestamptz)  表 files(path text primary key, content text, created_at timestamptz, modified_at timestamptz)
Map tool operations onto SQL:
将地图工具操作映射到 SQL：
ls_info uses WHERE path LIKE $1 || '%'   ls_info 使用 WHERE path LIKE $1 || '%'
glob_info filter in SQL or fetch then apply glob in Python
glob_info 在 SQL 中过滤或获取后应用 Python 中的 glob
grep_raw can fetch candidate rows by extension or last modified time, then scan lines
grep_raw 可以通过扩展或最后修改时间获取候选行，然后扫描行
​
Add policy hooks  添加策略钩子
Enforce enterprise rules by subclassing or wrapping a backend.
通过子类化或包装后端来强制执行企业规则。
Block writes/edits under selected prefixes (subclass):
在选定前缀（子类）下进行区块写入/编辑：
  复制
from deepagents.backends.filesystem import FilesystemBackend
from deepagents.backends.protocol import WriteResult, EditResult

class GuardedBackend(FilesystemBackend):
    def __init__(self, *, deny_prefixes: list[str], **kwargs):
        super().__init__(**kwargs)
        self.deny_prefixes = [p if p.endswith("/") else p + "/" for p in deny_prefixes]

    def write(self, file_path: str, content: str) -> WriteResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return WriteResult(error=f"Writes are not allowed under {file_path}")
        return super().write(file_path, content)

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        if any(file_path.startswith(p) for p in self.deny_prefixes):
            return EditResult(error=f"Edits are not allowed under {file_path}")
        return super().edit(file_path, old_string, new_string, replace_all)
Generic wrapper (works with any backend):
通用封装器（适用于任何后端）：
  复制
from deepagents.backends.protocol import BackendProtocol, WriteResult, EditResult
from deepagents.backends.utils import FileInfo, GrepMatch

class PolicyWrapper(BackendProtocol):
    def __init__(self, inner: BackendProtocol, deny_prefixes: list[str] | None = None):
        self.inner = inner
        self.deny_prefixes = [p if p.endswith("/") else p + "/" for p in (deny_prefixes or [])]

    def _deny(self, path: str) -> bool:
        return any(path.startswith(p) for p in self.deny_prefixes)

    def ls_info(self, path: str) -> list[FileInfo]:
        return self.inner.ls_info(path)
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str:
        return self.inner.read(file_path, offset=offset, limit=limit)
    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str:
        return self.inner.grep_raw(pattern, path, glob)
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]:
        return self.inner.glob_info(pattern, path)
    def write(self, file_path: str, content: str) -> WriteResult:
        if self._deny(file_path):
            return WriteResult(error=f"Writes are not allowed under {file_path}")
        return self.inner.write(file_path, content)
    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        if self._deny(file_path):
            return EditResult(error=f"Edits are not allowed under {file_path}")
        return self.inner.edit(file_path, old_string, new_string, replace_all)
​
Protocol reference  协议参考
Backends must implement the BackendProtocol.
后端必须实现 BackendProtocol 。
Required endpoints:  必需的端点：
ls_info(path: str) -> list[FileInfo]
Return entries with at least path. Include is_dir, size, modified_at when available. Sort by path for deterministic output.
返回至少 path 条记录。当可用时，包含 is_dir 、 size 、 modified_at 。按 path 排序以获得确定性输出。
read(file_path: str, offset: int = 0, limit: int = 2000) -> str
Return numbered content. On missing file, return "Error: File '/x' not found".
返回编号内容。当文件缺失时，返回 "Error: File '/x' not found" 。
grep_raw(pattern: str, path: Optional[str] = None, glob: Optional[str] = None) -> list[GrepMatch] | str
Return structured matches. For an invalid regex, return a string like "Invalid regex pattern: ..." (do not raise).  
glob_info(pattern: str, path: str = "/") -> list[FileInfo]
Return matched files as FileInfo entries (empty list if none).  
write(file_path: str, content: str) -> WriteResult
Create-only. On conflict, return WriteResult(error=...). On success, set path and for state backends set files_update={...}; external backends should use files_update=None.  
edit(file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult
Enforce uniqueness of old_string unless replace_all=True. If not found, return error. Include occurrences on success.  
Supporting types:  支持类型：
WriteResult(error, path, files_update)
EditResult(error, path, files_update, occurrences)
FileInfo with fields: path (required), optionally is_dir, size, modified_at.
FileInfo 具有字段： path （必填），可选地 is_dir 、 size 、 modified_at 。
GrepMatch with fields: path, line, text.

Subagents  子代理

Copy page  复制页面

Learn how to use subagents to delegate work and keep context clean
学习如何使用子代理来分配任务并保持上下文清晰

Deep agents can create subagents to delegate work. You can specify custom subagents in the subagents parameter. Subagents are useful for context quarantine (keeping the main agent’s context clean) and for providing specialized instructions.
深度代理可以创建子代理来分配任务。您可以在 subagents 参数中指定自定义子代理。子代理适用于上下文隔离（保持主代理的上下文清洁）以及提供专业指令。







task tool

isolated work

isolated work

isolated work

Main Agent

Subagent

Research

Code

General

Final Result

​
Why use subagents?  为什么要使用子代理？
Subagents solve the context bloat problem. When agents use tools with large outputs (web search, file reads, database queries), the context window fills up quickly with intermediate results. Subagents isolate this detailed work—the main agent receives only the final result, not the dozens of tool calls that produced it.
子代理解决了上下文膨胀问题。当代理使用具有大量输出的工具（网络搜索、文件读取、数据库查询）时，上下文窗口会迅速被中间结果填满。子代理隔离了这项详细工作——主代理只接收最终结果，而不是产生它的几十个工具调用。
When to use subagents:  何时使用子代理：
✅ Multi-step tasks that would clutter the main agent’s context
✅ 需要多个步骤且会使主代理上下文杂乱的任务
✅ Specialized domains that need custom instructions or tools
✅ 需要自定义指令或工具的专业领域
✅ Tasks requiring different model capabilities
✅ 需要不同模型能力的任务
✅ When you want to keep the main agent focused on high-level coordination
✅ 当你想让主代理专注于高层级协调时
When NOT to use subagents:
不使用子代理的情况：
❌ Simple, single-step tasks
❌ 简单、单步任务
❌ When you need to maintain intermediate context
❌ 当你需要保持中间状态上下文时
❌ When the overhead outweighs benefits
❌ 当开销超过收益时
​
Configuration  配置
subagents should be a list of dictionaries or CompiledSubAgent objects. There are two types:
subagents 应该是一个字典列表或 CompiledSubAgent 对象。有两种类型：
​
SubAgent (Dictionary-based)
子代理（基于字典）
For most use cases, define subagents as dictionaries:
对于大多数使用场景，将子代理定义为字典：
Required fields:  必需字段：
​
name
strrequired
Unique identifier for the subagent. The main agent uses this name when calling the task() tool. The subagent name becomes metadata for AIMessages and for streaming, which helps to differentiate between agents.
子代理的唯一标识符。主代理在调用 task() 工具时使用此名称。子代理名称成为 AIMessage 的元数据，并用于流式传输，这有助于区分不同的代理。
​
description
strrequired
What this subagent does. Be specific and action-oriented. The main agent uses this to decide when to delegate.
这个子代理的作用是什么。要具体且以行动为导向。主代理将使用这个来决定何时进行委托。
​
system_prompt
strrequired
Instructions for the subagent. Include tool usage guidance and output format requirements.
子代理的说明。包含工具使用指南和输出格式要求。
​
tools  工具
list[Callable]required  list[Callable]必需
Tools the subagent can use. Keep this minimal and include only what’s needed.
子代理可使用的工具。保持简洁，仅包含所需内容。
Optional fields:  可选字段：
​
model  模型
str | BaseChatModel
Override the main agent’s model. Use the format 'provider:model-name' (for example, 'openai:gpt-4o').
覆盖主要代理的模型。使用格式 'provider:model-name' （例如， 'openai:gpt-4o' ）。
​
middleware  中间件
list[Middleware]  list[中间件]
Additional middleware for custom behavior, logging, or rate limiting.
用于自定义行为、日志记录或速率限制的额外中间件。
​
interrupt_on
dict[str, bool]
Configure human-in-the-loop for specific tools. Requires a checkpointer.
为特定工具配置人工参与流程。需要检查点器。
​
CompiledSubAgent
For complex workflows, use a pre-built LangGraph graph:
对于复杂的流程，使用预构建的 LangGraph 图：
​
name  名称
strrequired
Unique identifier for the subagent. The subagent name becomes metadata for AIMessages and for streaming, which helps to differentiate between agents.
子代理的唯一标识符。子代理名称成为 AIMessage s 的元数据，并且在流式传输中，这有助于区分不同的代理。
​
description  描述
strrequired
What this subagent does.  这个子代理的作用。
​
runnable  可运行
Runnablerequired  可运行 required
A compiled LangGraph graph (must call .compile() first).
一个编译好的 LangGraph 图（必须先调用 .compile() ）。
​
Using SubAgent  使用 SubAgent
  复制
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "openai:gpt-4o",  # Optional override, defaults to main agent model
}
subagents = [research_subagent]

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    subagents=subagents
)
​
Using CompiledSubAgent  使用 CompiledSubAgent
For more complex use cases, you can provide your custom subagents. You can create a custom subagent using LangChain’s create_agent or by making a custom LangGraph graph using the graph API.
对于更复杂的用例，您可以提供自定义子代理。您可以使用 LangChain 的 create_agent 创建自定义子代理，或通过使用图 API 创建自定义 LangGraph 图。
If you’re creating a custom LangGraph graph, make sure that the graph has a state key called "messages":
如果您正在创建自定义 LangGraph 图，请确保该图有一个名为 "messages" 的状态键：
  复制
from deepagents import create_deep_agent, CompiledSubAgent
from langchain.agents import create_agent

# Create a custom agent graph
custom_graph = create_agent(
    model=your_model,
    tools=specialized_tools,
    prompt="You are a specialized agent for data analysis..."
)

# Use it as a custom subagent
custom_subagent = CompiledSubAgent(
    name="data-analyzer",
    description="Specialized agent for complex data analysis tasks",
    runnable=custom_graph
)

subagents = [custom_subagent]

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[internet_search],
    system_prompt=research_instructions,
    subagents=subagents
)
​
Streaming  流式传输
When streaming tracing information agents’ names are available as lc_agent_name in metadata. When reviewing tracing information, you can use this metadata to differentiate which agent the data came from.
当流式传输跟踪信息时，代理的名称在元数据中以 lc_agent_name 的形式提供。在查看跟踪信息时，您可以使用此元数据来区分数据来自哪个代理。
The following example creates a deep agent with the name main-agent and a subagent with the name research-agent:
以下示例创建了一个名为 main-agent 的深度代理和一个名为 research-agent 的子代理：
  复制
import os
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent

tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

def internet_search(
    query: str,
    max_results: int = 5,
    topic: Literal["general", "news", "finance"] = "general",
    include_raw_content: bool = False,
):
    """Run a web search"""
    return tavily_client.search(
        query,
        max_results=max_results,
        include_raw_content=include_raw_content,
        topic=topic,
    )

research_subagent = {
    "name": "research-agent",
    "description": "Used to research more in depth questions",
    "system_prompt": "You are a great researcher",
    "tools": [internet_search],
    "model": "claude-sonnet-4-5-20250929",  # Optional override, defaults to main agent model
}
subagents = [research_subagent]

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    subagents=subagents,
    name="main-agent"
)
As you prompt your deepagents, all agent runs executed by a subagent or deep agent will have the agent name in their metadata. In this case the subagent with the name "research-agent", will have {'lc_agent_name': 'research-agent'} in any associated agent run metadata:
当你提示你的深度代理时，由子代理或深度代理执行的任何代理运行都会在其元数据中包含代理名称。在这种情况下，名为 "research-agent" 的子代理在任何相关代理运行元数据中都会包含 {'lc_agent_name': 'research-agent'} ：
LangSmith Example trace showing the metadata
​
The general-purpose subagent
通用子代理
In addition to any user-defined subagents, deep agents have access to a general-purpose subagent at all times. This subagent:
除了任何用户定义的子代理外，深度代理始终可以访问一个 general-purpose 子代理。该子代理：
Has the same system prompt as the main agent
与主代理使用相同的系统提示
Has access to all the same tools
拥有对所有相同工具的访问权限
Uses the same model (unless overridden)
使用相同的模型（除非被覆盖）
​
When to use it  何时使用它
The general-purpose subagent is ideal for context isolation without specialized behavior. The main agent can delegate a complex multi-step task to this subagent and get a concise result back without bloat from intermediate tool calls.
通用子代理非常适合进行上下文隔离而不需要特殊行为。主代理可以将复杂的多步骤任务委托给这个子代理，并返回简洁的结果，而不会因为中间工具调用而产生冗余。
Example  示例
Instead of the main agent making 10 web searches and filling its context with results, it delegates to the general-purpose subagent: task(name="general-purpose", task="Research quantum computing trends"). The subagent performs all the searches internally and returns only a summary.
主代理不再进行 10 次网络搜索并将结果填入其上下文中，而是将任务委托给通用子代理： task(name="general-purpose", task="Research quantum computing trends") 。子代理在内部完成所有搜索，并仅返回摘要。
​
Best practices  最佳实践
​
Write clear descriptions  写清晰的描述
The main agent uses descriptions to decide which subagent to call. Be specific:
主代理使用描述来决定调用哪个子代理。要具体：
✅ Good: "Analyzes financial data and generates investment insights with confidence scores"  ✅ 好: "Analyzes financial data and generates investment insights with confidence scores"
❌ Bad: "Does finance stuff"  ❌ 不好: "Does finance stuff"
​
Keep system prompts detailed
保持系统提示详细
Include specific guidance on how to use tools and format outputs:
包含使用工具和格式输出的具体指导：
  复制
research_subagent = {
    "name": "research-agent",
    "description": "Conducts in-depth research using web search and synthesizes findings",
    "system_prompt": """You are a thorough researcher. Your job is to:

    1. Break down the research question into searchable queries
    2. Use internet_search to find relevant information
    3. Synthesize findings into a comprehensive but concise summary
    4. Cite sources when making claims

    Output format:
    - Summary (2-3 paragraphs)
    - Key findings (bullet points)
    - Sources (with URLs)

    Keep your response under 500 words to maintain clean context.""",
    "tools": [internet_search],
}
​
Minimize tool sets  最小化工具集
Only give subagents the tools they need. This improves focus and security:
仅向子代理提供它们所需的工具。这提高了专注度和安全性：
  复制
# ✅ Good: Focused tool set
email_agent = {
    "name": "email-sender",
    "tools": [send_email, validate_email],  # Only email-related
}

# ❌ Bad: Too many tools
email_agent = {
    "name": "email-sender",
    "tools": [send_email, web_search, database_query, file_upload],  # Unfocused
}
​
Choose models by task  按任务选择模型
Different models excel at different tasks:
不同的模型擅长不同的任务：
  复制
subagents = [
    {
        "name": "contract-reviewer",
        "description": "Reviews legal documents and contracts",
        "system_prompt": "You are an expert legal reviewer...",
        "tools": [read_document, analyze_contract],
        "model": "claude-sonnet-4-5-20250929",  # Large context for long documents
    },
    {
        "name": "financial-analyst",
        "description": "Analyzes financial data and market trends",
        "system_prompt": "You are an expert financial analyst...",
        "tools": [get_stock_price, analyze_fundamentals],
        "model": "openai:gpt-5",  # Better for numerical analysis
    },
]
​
Return concise results  返回简洁结果
Instruct subagents to return summaries, not raw data:
指示子代理返回摘要，而不是原始数据：
  复制
data_analyst = {
    "system_prompt": """Analyze the data and return:
    1. Key insights (3-5 bullet points)
    2. Overall confidence score
    3. Recommended next actions

    Do NOT include:
    - Raw data
    - Intermediate calculations
    - Detailed tool outputs

    Keep response under 300 words."""
}
​
Common patterns  常见模式
​
Multiple specialized subagents
多个专业子代理
Create specialized subagents for different domains:
为不同领域创建专门的子代理：
  复制
from deepagents import create_deep_agent

subagents = [
    {
        "name": "data-collector",
        "description": "Gathers raw data from various sources",
        "system_prompt": "Collect comprehensive data on the topic",
        "tools": [web_search, api_call, database_query],
    },
    {
        "name": "data-analyzer",
        "description": "Analyzes collected data for insights",
        "system_prompt": "Analyze data and extract key insights",
        "tools": [statistical_analysis],
    },
    {
        "name": "report-writer",
        "description": "Writes polished reports from analysis",
        "system_prompt": "Create professional reports from insights",
        "tools": [format_document],
    },
]

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    system_prompt="You coordinate data analysis and reporting. Use subagents for specialized tasks.",
    subagents=subagents
)
Workflow:  工作流：
Main agent creates high-level plan
主代理创建高级计划
Delegates data collection to data-collector
将数据收集委托给数据收集器
Passes results to data-analyzer
将结果传递给数据分析器
Sends insights to report-writer
将洞察发送给报告撰写者
Compiles final output  编译最终输出
Each subagent works with clean context focused only on its task.
每个子代理都使用只关注其任务的干净上下文进行工作。
​
Troubleshooting  故障排除
​
Subagent not being called
子代理未被调用
Problem: Main agent tries to do work itself instead of delegating.
问题：主代理试图自己做工作而不是委托。
Solutions:  解决方案：
Make descriptions more specific:
使描述更具体：
  复制
# ✅ Good
{"name": "research-specialist", "description": "Conducts in-depth research on specific topics using web search. Use when you need detailed information that requires multiple searches."}

# ❌ Bad
{"name": "helper", "description": "helps with stuff"}
Instruct main agent to delegate:
指示主代理进行委托：
  复制
agent = create_deep_agent(
    system_prompt="""...your instructions...

    IMPORTANT: For complex tasks, delegate to your subagents using the task() tool.
    This keeps your context clean and improves results.""",
    subagents=[...]
)
​
Context still getting bloated
上下文仍然膨胀
Problem: Context fills up despite using subagents.
问题：尽管使用了子代理，上下文仍然填满。
Solutions:  解决方案：
Instruct subagent to return concise results:
指示子代理返回简洁的结果：
  复制
system_prompt="""...

IMPORTANT: Return only the essential summary.
Do NOT include raw data, intermediate search results, or detailed tool outputs.
Your response should be under 500 words."""
Use filesystem for large data:
使用文件系统处理大数据：
  复制
system_prompt="""When you gather large amounts of data:
1. Save raw data to /data/raw_results.txt
2. Process and analyze the data
3. Return only the analysis summary

This keeps context clean."""
​
Wrong subagent being selected
选择了错误的子代理
Problem: Main agent calls inappropriate subagent for the task.
问题：主代理为任务调用了不合适的子代理。
Solution: Differentiate subagents clearly in descriptions:
解决方案：在描述中明确区分子代理：
  复制
subagents = [
    {
        "name": "quick-researcher",
        "description": "For simple, quick research questions that need 1-2 searches. Use when you need basic facts or definitions.",
    },
    {
        "name": "deep-researcher",
        "description": "For complex, in-depth research requiring multiple searches, synthesis, and analysis. Use for comprehensive reports.",
    }
]


Human-in-the-loop  人机交互

Copy page  复制页面

Learn how to configure human approval for sensitive tool operations
学习如何为敏感工具操作配置人工审批

Some tool operations may be sensitive and require human approval before execution. Deep agents support human-in-the-loop workflows through LangGraph’s interrupt capabilities. You can configure which tools require approval using the interrupt_on parameter.
某些工具操作可能具有敏感性，需要在执行前获得人工审批。Deep agents 通过 LangGraph 的中断功能支持人工介入的工作流程。您可以使用 interrupt_on 参数配置哪些工具需要审批。







no

yes

approve

edit

reject

Agent

Interrupt?

Execute

Human

Cancel

​
Basic configuration  基本配置
The interrupt_on parameter accepts a dictionary mapping tool names to interrupt configurations. Each tool can be configured with:
interrupt_on 参数接受一个将工具名称映射到中断配置的字典。每个工具可以配置以下内容：
True: Enable interrupts with default behavior (approve, edit, reject allowed)
True : 使用默认行为启用中断（允许批准、编辑、拒绝）
False: Disable interrupts for this tool
False : 禁用此工具的中断
{"allowed_decisions": [...]}: Custom configuration with specific allowed decisions
{"allowed_decisions": [...]} : 自定义配置，包含特定的允许决策
  复制
from langchain.tools import tool
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

@tool
def delete_file(path: str) -> str:
    """Delete a file from the filesystem."""
    return f"Deleted {path}"

@tool
def read_file(path: str) -> str:
    """Read a file from the filesystem."""
    return f"Contents of {path}"

@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Sent email to {to}"

# Checkpointer is REQUIRED for human-in-the-loop
checkpointer = MemorySaver()

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[delete_file, read_file, send_email],
    interrupt_on={
        "delete_file": True,  # Default: approve, edit, reject
        "read_file": False,   # No interrupts needed
        "send_email": {"allowed_decisions": ["approve", "reject"]},  # No editing
    },
    checkpointer=checkpointer  # Required!
)
​
Decision types  决策类型
The allowed_decisions list controls what actions a human can take when reviewing a tool call:
allowed_decisions 列表控制人类在审查工具调用时可以采取的操作：
"approve": Execute the tool with the original arguments as proposed by the agent
"approve" : 按照代理提议的原参数执行该工具
"edit": Modify the tool arguments before execution
"edit" : 在执行前修改工具参数
"reject": Skip executing this tool call entirely
"reject" : 完全跳过执行此工具调用
You can customize which decisions are available for each tool:
你可以自定义每个工具可用的决策：
  复制
interrupt_on = {
    # Sensitive operations: allow all options
    "delete_file": {"allowed_decisions": ["approve", "edit", "reject"]},

    # Moderate risk: approval or rejection only
    "write_file": {"allowed_decisions": ["approve", "reject"]},

    # Must approve (no rejection allowed)
    "critical_operation": {"allowed_decisions": ["approve"]},
}
​
Handle interrupts  处理中断
When an interrupt is triggered, the agent pauses execution and returns control. Check for interrupts in the result and handle them accordingly.
当中断被触发时，代理会暂停执行并返回控制权。在结果中检查中断，并相应地处理它们。
  复制
import uuid
from langgraph.types import Command

# Create config with thread_id for state persistence
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

# Invoke the agent
result = agent.invoke({
    "messages": [{"role": "user", "content": "Delete the file temp.txt"}]
}, config=config)

# Check if execution was interrupted
if result.get("__interrupt__"):
    # Extract interrupt information
    interrupts = result["__interrupt__"][0].value
    action_requests = interrupts["action_requests"]
    review_configs = interrupts["review_configs"]

    # Create a lookup map from tool name to review config
    config_map = {cfg["action_name"]: cfg for cfg in review_configs}

    # Display the pending actions to the user
    for action in action_requests:
        review_config = config_map[action["name"]]
        print(f"Tool: {action['name']}")
        print(f"Arguments: {action['args']}")
        print(f"Allowed decisions: {review_config['allowed_decisions']}")

    # Get user decisions (one per action_request, in order)
    decisions = [
        {"type": "approve"}  # User approved the deletion
    ]

    # Resume execution with decisions
    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config  # Must use the same config!
    )

# Process final result
print(result["messages"][-1].content)
​
Multiple tool calls  多个工具调用
When the agent calls multiple tools that require approval, all interrupts are batched together in a single interrupt. You must provide decisions for each one in order.
当代理调用多个需要批准的工具时，所有中断都会被批量组合在一个中断中。你必须按顺序为每一个提供决策。
  复制
config = {"configurable": {"thread_id": str(uuid.uuid4())}}

result = agent.invoke({
    "messages": [{
        "role": "user",
        "content": "Delete temp.txt and send an email to admin@example.com"
    }]
}, config=config)

if result.get("__interrupt__"):
    interrupts = result["__interrupt__"][0].value
    action_requests = interrupts["action_requests"]

    # Two tools need approval
    assert len(action_requests) == 2

    # Provide decisions in the same order as action_requests
    decisions = [
        {"type": "approve"},  # First tool: delete_file
        {"type": "reject"}    # Second tool: send_email
    ]

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config
    )
​
Edit tool arguments  编辑工具参数
When "edit" is in the allowed decisions, you can modify the tool arguments before execution:
当 "edit" 在允许的决策中时，您可以在执行前修改工具参数：
  复制
if result.get("__interrupt__"):
    interrupts = result["__interrupt__"][0].value
    action_request = interrupts["action_requests"][0]

    # Original args from the agent
    print(action_request["args"])  # {"to": "everyone@company.com", ...}

    # User decides to edit the recipient
    decisions = [{
        "type": "edit",
        "edited_action": {
            "name": action_request["name"],  # Must include the tool name
            "args": {"to": "team@company.com", "subject": "...", "body": "..."}
        }
    }]

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config
    )
​
Subagent interrupts  子代理中断
Each subagent can have its own interrupt_on configuration that overrides the main agent’s settings:
每个子代理可以拥有自己的 interrupt_on 配置，该配置会覆盖主代理的设置：
  复制
agent = create_deep_agent(
    tools=[delete_file, read_file],
    interrupt_on={
        "delete_file": True,
        "read_file": False,
    },
    subagents=[{
        "name": "file-manager",
        "description": "Manages file operations",
        "system_prompt": "You are a file management assistant.",
        "tools": [delete_file, read_file],
        "interrupt_on": {
            # Override: require approval for reads in this subagent
            "delete_file": True,
            "read_file": True,  # Different from main agent!
        }
    }],
    checkpointer=checkpointer
)
When a subagent triggers an interrupt, the handling is the same – check for __interrupt__ and resume with Command.  
​
Best practices  
​
Always use a checkpointer  
Human-in-the-loop requires a checkpointer to persist agent state between the interrupt and resume:  
  
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
agent = create_deep_agent(
    tools=[...],
    interrupt_on={...},
    checkpointer=checkpointer  # Required for HITL
)
​
Use the same thread ID  
When resuming, you must use the same config with the same thread_id:  
  
# First call
config = {"configurable": {"thread_id": "my-thread"}}
result = agent.invoke(input, config=config)

# Resume (use same config)
result = agent.invoke(Command(resume={...}), config=config)
​
Match decision order to actions  
The decisions list must match the order of action_requests:  
  
if result.get("__interrupt__"):
    interrupts = result["__interrupt__"][0].value
    action_requests = interrupts["action_requests"]

    # Create one decision per action, in order
    decisions = []
    for action in action_requests:
        decision = get_user_decision(action)  # Your logic
        decisions.append(decision)

    result = agent.invoke(
        Command(resume={"decisions": decisions}),
        config=config
    )
​
Tailor configurations by risk  
Configure different tools based on their risk level:  
  
interrupt_on = {
    # High risk: full control (approve, edit, reject)
    "delete_file": {"allowed_decisions": ["approve", "edit", "reject"]},
    "send_email": {"allowed_decisions": ["approve", "edit", "reject"]},

    # Medium risk: no editing allowed
    "write_file": {"allowed_decisions": ["approve", "reject"]},

    # Low risk: no interrupts
    "read_file": False,
    "list_files": False,
}


Long-term memory  长期记忆

Copy page  复制页面

Learn how to extend deep agents with persistent memory across threads
学习如何扩展具有跨线程持久内存的深度代理

Deep agents come with a local filesystem to offload memory. By default, this filesystem is stored in agent state and is transient to a single thread—files are lost when the conversation ends.
深度代理自带本地文件系统以卸载内存。默认情况下，该文件系统存储在代理状态中，并且仅对单个线程是临时的——当对话结束时，文件会丢失。
You can extend deep agents with long-term memory by using a CompositeBackend that routes specific paths to persistent storage. This enables hybrid storage where some files persist across threads while others remain ephemeral.
您可以通过使用一个 CompositeBackend 将特定路径路由到持久化存储来扩展具有长期记忆的深度代理。这实现了混合存储，其中一些文件跨线程持久存在，而另一些则保持短暂。







/memories/*

other

Deep Agent

Path Router

Store Backend

State Backend

Persistent
across threads

Ephemeral
single thread

​
Setup  设置
Configure long-term memory by using a CompositeBackend that routes the /memories/ path to a StoreBackend:
通过使用 CompositeBackend 配置长期记忆，将 /memories/ 路由到 StoreBackend ：
  复制
from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

def make_backend(runtime):
    return CompositeBackend(
        default=StateBackend(runtime),  # Ephemeral storage
        routes={
            "/memories/": StoreBackend(runtime)  # Persistent storage
        }
    )

agent = create_deep_agent(
    store=InMemoryStore(),  # Required for StoreBackend
    backend=make_backend,
    checkpointer=checkpointer
)
​
How it works  工作原理
When using CompositeBackend, deep agents maintain two separate filesystems:
在使用 CompositeBackend 时，深度代理维护两个独立的文件系统：
​
1. Short-term (transient) filesystem
1. 短期（临时）文件系统
Stored in the agent’s state (via StateBackend)
存储在代理的状态中（通过 StateBackend ）
Persists only within a single thread
仅持久化于单个线程内
Files are lost when the thread ends
线程结束时文件会丢失
Accessed through standard paths: /notes.txt, /workspace/draft.md
通过标准路径访问： /notes.txt ， /workspace/draft.md
​
2. Long-term (persistent) filesystem
2. 长期（持久）文件系统
Stored in a LangGraph Store (via StoreBackend)
存储在 LangGraph Store 中（通过 StoreBackend ）
Persists across all threads and conversations
跨所有线程和对话持久保存
Survives agent restarts  在代理重启时仍然存在
Accessed through paths prefixed with /memories/: /memories/preferences.txt
通过以 /memories/ 开头的路径访问： /memories/preferences.txt
​
Path routing  路径路由
The CompositeBackend routes file operations based on path prefixes:
CompositeBackend 路由根据路径前缀处理文件操作：
Files with paths starting with /memories/ are stored in the Store (persistent)
路径以 /memories/ 开头的文件存储在 Store（持久化）中
Files without this prefix remain in transient state
没有这个前缀的文件保持瞬时状态
All filesystem tools (ls, read_file, write_file, edit_file) work with both
所有文件系统工具（ ls ， read_file ， write_file ， edit_file ）都与两者协同工作
  复制
# Transient file (lost after thread ends)
agent.invoke({
    "messages": [{"role": "user", "content": "Write draft to /draft.txt"}]
})

# Persistent file (survives across threads)
agent.invoke({
    "messages": [{"role": "user", "content": "Save final report to /memories/report.txt"}]
})
​
Cross-thread persistence  跨线程持久化
Files in /memories/ can be accessed from any thread:
/memories/ 中的文件可以从任何线程访问：
  复制
import uuid

# Thread 1: Write to long-term memory
config1 = {"configurable": {"thread_id": str(uuid.uuid4())}}
agent.invoke({
    "messages": [{"role": "user", "content": "Save my preferences to /memories/preferences.txt"}]
}, config=config1)

# Thread 2: Read from long-term memory (different conversation!)
config2 = {"configurable": {"thread_id": str(uuid.uuid4())}}
agent.invoke({
    "messages": [{"role": "user", "content": "What are my preferences?"}]
}, config=config2)
# Agent can read /memories/preferences.txt from the first thread
​
Use cases  应用场景
​
User preferences  用户偏好
Store user preferences that persist across sessions:
存储跨会话持久化的用户偏好：
  复制
agent = create_deep_agent(
    store=InMemoryStore(),
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt)}
    ),
    system_prompt="""When users tell you their preferences, save them to
    /memories/user_preferences.txt so you remember them in future conversations."""
)
​
Self-improving instructions
自我改进指令
An agent can update its own instructions based on feedback:
一个智能体可以根据反馈更新自己的指令：
  复制
agent = create_deep_agent(
    store=InMemoryStore(),
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt)}
    ),
    system_prompt="""You have a file at /memories/instructions.txt with additional
    instructions and preferences.

    Read this file at the start of conversations to understand user preferences.

    When users provide feedback like "please always do X" or "I prefer Y",
    update /memories/instructions.txt using the edit_file tool."""
)
Over time, the instructions file accumulates user preferences, helping the agent improve.
随着时间的推移，指令文件会积累用户偏好，帮助代理改进。
​
Knowledge base  知识库
Build up knowledge over multiple conversations:
在多次对话中积累知识：
  复制
# Conversation 1: Learn about a project
agent.invoke({
    "messages": [{"role": "user", "content": "We're building a web app with React. Save project notes."}]
})

# Conversation 2: Use that knowledge
agent.invoke({
    "messages": [{"role": "user", "content": "What framework are we using?"}]
})
# Agent reads /memories/project_notes.txt from previous conversation
​
Research projects  研究项目
Maintain research state across sessions:
保持跨会话的研究状态：
  复制
research_agent = create_deep_agent(
    store=InMemoryStore(),
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt)}
    ),
    system_prompt="""You are a research assistant.

    Save your research progress to /memories/research/:
    - /memories/research/sources.txt - List of sources found
    - /memories/research/notes.txt - Key findings and notes
    - /memories/research/report.md - Final report draft

    This allows research to continue across multiple sessions."""
)
​
Store implementations  存储实现
Any LangGraph BaseStore implementation works:
任何 LangGraph BaseStore 实现都可以使用：
​
InMemoryStore (development)
InMemoryStore (开发中)
Good for testing and development, but data is lost on restart:
适合测试和开发，但重启时会丢失数据：
  复制
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()
agent = create_deep_agent(
    store=store,
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt)}
    )
)
​
PostgresStore (production)
PostgresStore (生产环境)
For production, use a persistent store:
在生产环境中，使用持久化存储：
  复制
from langgraph.store.postgres import PostgresStore
import os

# Use PostgresStore.from_conn_string as a context manager
store_ctx = PostgresStore.from_conn_string(os.environ["DATABASE_URL"])
store = store_ctx.__enter__()
store.setup()

agent = create_deep_agent(
    store=store,
    backend=lambda rt: CompositeBackend(
        default=StateBackend(rt),
        routes={"/memories/": StoreBackend(rt)}
    )
)
​
Best practices  最佳实践
​
Use descriptive paths  使用描述性路径
Organize persistent files with clear paths:
使用清晰的路径组织持久文件：
  复制
/memories/user_preferences.txt
/memories/research/topic_a/sources.txt
/memories/research/topic_a/notes.txt
/memories/project/requirements.md
​
Document the memory structure
记录内存结构
Tell the agent what’s stored where in your system prompt:
在系统提示中告诉代理你的系统中存储了什么：
  复制
Your persistent memory structure:
- /memories/preferences.txt: User preferences and settings
- /memories/context/: Long-term context about the user
- /memories/knowledge/: Facts and information learned over time
​
Prune old data  修剪旧数据
Implement periodic cleanup of outdated persistent files to keep storage manageable.
实现定期清理过时的持久文件，以保持存储的可管理性。
​
Choose the right storage  选择合适的存储
Development: Use InMemoryStore for quick iteration
开发：使用 InMemoryStore 进行快速迭代
Production: Use PostgresStore or other persistent stores
生产：使用 PostgresStore 或其他持久化存储
Multi-tenant: Consider using assistant_id-based namespacing in your store
多租户：考虑在您的存储中使用基于 assistant_id 的命名空间


Deep Agents Middleware  深度代理中间件

Copy page  复制页面

Understand the middleware that powers deep agents
了解驱动深度代理的中间件

Deep agents are built with a modular middleware architecture. Deep agents have access to:
深度代理采用模块化中间件架构构建。深度代理可以访问：
A planning tool  一个规划工具
A filesystem for storing context and long-term memories
用于存储上下文和长期记忆的文件系统
The ability to spawn subagents
生成子代理的能力
Each feature is implemented as separate middleware. When you create a deep agent with create_deep_agent, we automatically attach TodoListMiddleware, FilesystemMiddleware, and SubAgentMiddleware to your agent.
每个功能都作为独立的中间件实现。当你使用 create_deep_agent 创建深度代理时，我们会自动将 TodoListMiddleware 、 FilesystemMiddleware 和 SubAgentMiddleware 附加到你的代理上。







create_deep_agent

TodoList

Filesystem

SubAgent

Agent Tools

Middleware is composable—you can add as many or as few middleware to an agent as needed. You can use any middleware independently.
中间件是可组合的——你可以根据需要向代理添加任意数量或任意数量的中间件。你可以独立使用任何中间件。
The following sections explain what each middleware provides.
以下各节将解释每个中间件提供的内容。
​
To-do list middleware  待办事项中间件
Planning is integral to solving complex problems. If you’ve used Claude Code recently, you’ll notice how it writes out a to-do list before tackling complex, multi-part tasks. You’ll also notice how it can adapt and update this to-do list on the fly as more information comes in.
规划对于解决复杂问题至关重要。如果你最近使用过 Claude Code，你会注意到它在处理复杂的多部分任务之前会先列出一个待办事项清单。你还会注意到它可以根据新信息的获取动态调整和更新这个待办事项清单。
TodoListMiddleware provides your agent with a tool specifically for updating this to-do list. Before and while it executes a multi-part task, the agent is prompted to use the write_todos tool to keep track of what it’s doing and what still needs to be done.
TodoListMiddleware 为你的智能体提供了一个专门用于更新这个待办事项清单的工具。在执行多部分任务之前和执行过程中，智能体会被提示使用 write_todos 工具来跟踪其当前进度以及仍需完成的事项。
  复制
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

# TodoListMiddleware is included by default in create_deep_agent
# You can customize it if building a custom agent
agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    # Custom planning instructions can be added via middleware
    middleware=[
        TodoListMiddleware(
            system_prompt="Use the write_todos tool to..."  # Optional: Custom addition to the system prompt
        ),
    ],
)
​
Filesystem middleware  文件系统中间件
Context engineering is a main challenge in building effective agents. This is particularly difficult when using tools that return variable-length results (for example, web_search and RAG), as long tool results can quickly fill your context window.
上下文工程是构建有效智能体的主要挑战。当使用返回可变长度结果的工具（例如 web_search 和 RAG）时，这一点尤其困难，因为长工具结果可能会迅速填满您的上下文窗口。
FilesystemMiddleware provides four tools for interacting with both short-term and long-term memory:
FilesystemMiddleware 提供了四个用于与短期和长期记忆交互的工具：
ls: List the files in the filesystem
ls : 列出文件系统中的文件
read_file: Read an entire file or a certain number of lines from a file
read_file : 读取整个文件或文件中的某几行
write_file: Write a new file to the filesystem
write_file : 将新文件写入文件系统
edit_file: Edit an existing file in the filesystem
edit_file : 编辑文件系统中的现有文件
  复制
from langchain.agents import create_agent
from deepagents.middleware.filesystem import FilesystemMiddleware

# FilesystemMiddleware is included by default in create_deep_agent
# You can customize it if building a custom agent
agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    middleware=[
        FilesystemMiddleware(
            backend=None,  # Optional: custom backend (defaults to StateBackend)
            system_prompt="Write to the filesystem when...",  # Optional custom addition to the system prompt
            custom_tool_descriptions={
                "ls": "Use the ls tool when...",
                "read_file": "Use the read_file tool to..."
            }  # Optional: Custom descriptions for filesystem tools
        ),
    ],
)
​
Short-term vs. long-term filesystem
短期与长期文件系统
By default, these tools write to a local “filesystem” in your graph state. To enable persistent storage across threads, configure a CompositeBackend that routes specific paths (like /memories/) to a StoreBackend.
默认情况下，这些工具会写入图状态中的本地“文件系统”。要实现跨线程的持久化存储，请配置一个 CompositeBackend 将特定路径（如 /memories/ ）路由到 StoreBackend 。
  复制
from langchain.agents import create_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

store = InMemoryStore()

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    store=store,
    middleware=[
        FilesystemMiddleware(
            backend=lambda rt: CompositeBackend(
                default=StateBackend(rt),
                routes={"/memories/": StoreBackend(rt)}
            ),
            custom_tool_descriptions={
                "ls": "Use the ls tool when...",
                "read_file": "Use the read_file tool to..."
            }  # Optional: Custom descriptions for filesystem tools
        ),
    ],
)
When you configure a CompositeBackend with a StoreBackend for /memories/, any files prefixed with /memories/ are saved to persistent storage and survive across different threads. Files without this prefix remain in ephemeral state storage.
当你为 CompositeBackend 配置 StoreBackend 用于 /memories/ 时，以 /memories/ 开头的任何文件都会保存到持久化存储中，并在不同线程间持续存在。没有这个前缀的文件则保留在临时状态存储中。
​
Subagent middleware  子代理中间件
Handing off tasks to subagents isolates context, keeping the main (supervisor) agent’s context window clean while still going deep on a task.
将任务委托给子代理可以隔离上下文，在深入处理任务的同时保持主代理（监督者）的上下文窗口干净。
The subagents middleware allows you to supply subagents through a task tool.
子代理中间件允许你通过 task 工具提供子代理。
  复制
from langchain.tools import tool
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware


@tool
def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is sunny."

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-5-20250929",
            default_tools=[],
            subagents=[
                {
                    "name": "weather",
                    "description": "This subagent can get weather in cities.",
                    "system_prompt": "Use the get_weather tool to get the weather in a city.",
                    "tools": [get_weather],
                    "model": "gpt-4o",
                    "middleware": [],
                }
            ],
        )
    ],
)
A subagent is defined with a name, description, system prompt, and tools. You can also provide a subagent with a custom model, or with additional middleware. This can be particularly useful when you want to give the subagent an additional state key to share with the main agent.
子代理通过名称、描述、系统提示和工具来定义。您还可以为子代理提供自定义模型或额外的中间件。当您希望为子代理提供一个额外的状态键以与主代理共享时，这特别有用。
For more complex use cases, you can also provide your own pre-built LangGraph graph as a subagent.
对于更复杂的用例，您也可以将您自己的预构建 LangGraph 图作为子代理提供。
  复制
from langchain.agents import create_agent
from deepagents.middleware.subagents import SubAgentMiddleware
from deepagents import CompiledSubAgent
from langgraph.graph import StateGraph

# Create a custom LangGraph graph
def create_weather_graph():
    workflow = StateGraph(...)
    # Build your custom graph
    return workflow.compile()

weather_graph = create_weather_graph()

# Wrap it in a CompiledSubAgent
weather_subagent = CompiledSubAgent(
    name="weather",
    description="This subagent can get weather in cities.",
    runnable=weather_graph
)

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    middleware=[
        SubAgentMiddleware(
            default_model="claude-sonnet-4-5-20250929",
            default_tools=[],
            subagents=[weather_subagent],
        )
    ],
)
In addition to any user-defined subagents, the main agent has access to a general-purpose subagent at all times. This subagent has the same instructions as the main agent and all the tools it has access to. The primary purpose of the general-purpose subagent is context isolation—the main agent can delegate a complex task to this subagent and get a concise answer back without bloat from intermediate tool calls.
除了任何用户定义的子代理外，主代理始终可以访问一个 general-purpose 子代理。这个子代理与主代理具有相同的指令以及它所能访问的所有工具。 general-purpose 子代理的主要目的是上下文隔离——主代理可以将复杂任务委托给这个子代理，并得到简洁的答案，而不会因中间工具调用而产生冗余信息。


Skills  技能

Copy page  复制页面

Learn how to extend your deep agent’s capabilities with skills
学习如何通过技能扩展深度代理的功能

You can use Agent Skills to provide your deep agent with new capabilities and expertise.
您可以使用代理技能为您的深度代理提供新的功能和专业知识。
​
What are skills  什么是技能
Skills are a directory of folders, where each folder has one or more files that contain context the agent can use:
技能是一个文件夹目录，每个文件夹包含一个或多个文件，这些文件包含代理可以使用的内容：
a SKILL.md file containing instructions and metadata about the skill
一个 SKILL.md 文件，包含技能的说明和元数据
additional scripts (optional)
额外的脚本（可选）
additional reference info, such as docs (optional)
额外的参考信息，例如文档（可选）
additional assets, such as templates and other resources (optional)
额外的资源，例如模板和其他资源（可选）
​
How do skills work  技能如何工作
When you create a deep agent, you can pass in a list of directories containing skills. As the agent starts, it reads through the frontmatter of each SKILL.md file.
当你创建一个深度代理时，你可以传入一个包含技能的目录列表。代理启动时，会逐个读取每个 SKILL.md 文件的 frontmatter 部分。
When the agent receives a prompt, the agent checks if it can use any skills while fulfilling the prompt. If it finds a matching prompt, it then reviews the rest of the skill files. This pattern of only reviewing the skill information when needed is called progressive disclosure.
当代理接收到一个提示时，它会检查在完成提示的过程中是否可以使用任何技能。如果找到匹配的提示，它接着会审查其余的技能文件。这种仅在需要时才审查技能信息的模式称为渐进式披露。
​
Examples  示例
You might have a skills folder that contains a skill to use a docs site in a certain way, as well as another skill to search the arXiv preprint repository of research papers:
你可能有一个技能文件夹，其中包含一个用于以特定方式使用文档站点的技能，以及另一个用于搜索 arXiv 预印本研究论文库的技能：
  复制
    skills/
    ├── langgraph-docs
    │   └── SKILL.md
    └── arxiv_search
        ├── SKILL.md
        └── arxiv_search.ts # code for searchign arXiv
The SKILL.md file always follows the same pattern, starting with metadata in the frontmatter and followed by the instructions for the skill. The following example shows a skill that gives instructions on how to provide relevant langgraph docs when prompted:
SKILL.md 文件始终遵循相同的模式，以元数据开头，随后是技能的说明。以下示例展示了一个技能，它提供了在提示时如何提供相关 langgraph 文档的说明：
  复制
---
name: langgraph-docs
description: Use this skill for requests related to LangGraph in order to fetch relevant documentation to provide accurate, up-to-date guidance.
---

# langgraph-docs

## Overview

This skill explains how to access LangGraph Python documentation to help answer questions and guide implementation.

## Instructions

### 1. Fetch the Documentation Index

Use the fetch_url tool to read the following URL:
https://docs.langchain.com/llms.txt

This provides a structured list of all available documentation with descriptions.

### 2. Select Relevant Documentation

Based on the question, identify 2-4 most relevant documentation URLs from the index. Prioritize:

- Specific how-to guides for implementation questions
- Core concept pages for understanding questions
- Tutorials for end-to-end examples
- Reference docs for API details

### 3. Fetch Selected Documentation

Use the fetch_url tool to read the selected documentation URLs.

### 4. Provide Accurate Guidance

After reading the documentation, complete the user's request.
For more example skills, see Deep Agent example skills.
更多示例技能，请参阅 Deep Agent 示例技能。
​
Usage  使用
Pass the skills directory when creating your deep agent:
创建你的深度代理时，请传递技能目录：

StateBackend

StoreBackend

FilesystemBackend
  复制
from urllib.request import urlopen
from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

skill_url = "https://raw.githubusercontent.com/langchain-ai/deepagentsjs/refs/heads/main/examples/skills/langgraph-docs/SKILL.md"
with urlopen(skill_url) as response:
    skill_content = response.read().decode('utf-8')

skills_files = {
    "/skills/langgraph-docs/SKILL.md": skill_content
}

agent = create_deep_agent(
    skills=["./skills/"],
    checkpointer=checkpointer,
)

result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "What is langgraph?",
            }
        ],
        # Seed the default StateBackend's in-state filesystem (virtual paths must start with "/").
        "files": skills_files
    },
    config={"configurable": {"thread_id": "12345"}},
)
​
skills  技能
list[str]
List of skill source paths. Paths must be specified using forward slashes and are relative to the backend’s root.
技能源路径列表。路径必须使用正斜杠指定，且相对于后端的根目录。
When using StateBackend (default), provide skill files with invoke(files={...}).
在使用 StateBackend（默认情况下），请提供带有 invoke(files={...}) 的技能文件。
With FilesystemBackend, skills are loaded from disk relative to the backend’s root_dir.
使用 FilesystemBackend 时，技能会相对于后端的 root_dir 从磁盘加载。
Later sources override earlier ones for skills with the same name (last one wins).
对于同名的技能，后者的源会覆盖前者（后载入者生效）。
​
When to use skills and tools
何时使用技能和工具
These are a few general guidelines for using tools and skills:
以下是使用工具和技能的一些一般性指导原则：
Use skills when there is a lot of context to reduce the number of tokens in the system prompt.
在存在大量上下文时使用技能，以减少系统提示中的 token 数量。
Use skills to bundle capabilities together into larger actions and provide additional context beyond single tool descriptions.
使用技能将功能捆绑成更大的动作，并在单个工具描述之外提供额外的上下文。
Use tools if the agent does not have access to the file system.
如果代理无法访问文件系统，则使用工具。