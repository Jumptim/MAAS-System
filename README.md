# Agent Template

This folder is a reusable template for one agent that performs one fixed subtask inside a larger top-level workflow.

The top-level workflow decides:

- when this agent runs
- what task input it receives
- which skills it should use
- the order of skill execution

This agent template defines:

- the agent role and task boundary
- allowed skills
- allowed MCP tools
- allowed RAG resources
- memory and logging policy
- input and output schemas

## Structure

```text
Agent Template/
  README.md
  agent.yaml
  skills/
  mcp/
  rag/
  memory/
  logs/
  prompts/
  schemas/
```

## How To Use

1. Copy this folder for a new agent.
2. Fill in `agent.yaml`.
3. Add or customize skill manifests in `skills/`.
4. Register MCP tools in `mcp/mcp.config.yaml`.
5. Register RAG resources in `rag/resources.yaml`.
6. Configure memory in `memory/memory.config.yaml`.
7. Replace schemas with stricter task-specific schemas.

## Running In Codex / 在 Codex 中运行

This template folder is the agent blueprint. Filling in this folder defines the agent, but it does not automatically make Codex recognize the agent's skills or MCP tools.

这个文件夹是 agent 的蓝图。你在这里填写配置，可以定义 agent 的结构；但这并不会自动让 Codex 识别里面的 skill 或 MCP 工具。

### 1. Agent Template Layer / Agent 模板层

Keep the agent-specific files here:

这些 agent 专属文件保留在本文件夹内：

```text
agent.yaml
skills/
mcp/
rag/
memory/
logs/
prompts/
schemas/
```

Use this folder to maintain:

这个文件夹负责维护：

- agent role, task boundary, and permissions
- allowed skills, MCP tools, and RAG resources
- memory and logging policy
- input/output schemas
- agent-specific RAG documents

中文说明：

- agent 的角色、任务边界和权限
- 允许使用的 skills、MCP tools 和 RAG resources
- memory 和 log 策略
- 输入/输出 schema
- 当前 agent 专属的 RAG 文档

### 2. Codex Skill Registration / Codex Skill 注册

If you want Codex to actively use a skill, convert the skill manifest into a Codex skill folder.

如果你希望 Codex 真正调用某个 skill，需要把这里的 skill manifest 转成 Codex skill 文件夹。

Typical Codex skill location:

常见 Codex skill 位置：

```text
C:\Users\zhong\.codex\skills\YOUR_SKILL_NAME\
  SKILL.md
```

The `SKILL.md` file should explain:

`SKILL.md` 应该说明：

- when to use the skill
- what input the skill expects
- which MCP tools it may call
- which RAG resources it may use
- what output format or schema it must follow

中文说明：

- 什么时候使用这个 skill
- skill 需要什么输入
- skill 可以调用哪些 MCP tools
- skill 可以使用哪些 RAG resources
- skill 必须遵守什么输出格式或 schema

### 3. MCP Server Registration / MCP Server 注册

The MCP files in this template are not enough by themselves. Codex must know how to start or connect to the MCP server.

本模板里的 MCP 文件本身还不够。Codex 需要知道如何启动或连接这个 MCP server。

Use `mcp/server.template.py` as the starting point, then:

以 `mcp/server.template.py` 为起点，然后：

1. Rename it to a real server file, for example `server.py`.
2. Implement real tools.
3. Install required Python dependencies.
4. Register the MCP server in the Codex MCP configuration.
5. Make sure the tool IDs match `mcp/mcp.config.yaml`, `agent.yaml`, and the related skill manifests.

中文说明：

1. 把模板文件改成真实 server 文件，例如 `server.py`。
2. 实现真实工具。
3. 安装需要的 Python 依赖。
4. 在 Codex 的 MCP 配置中注册这个 MCP server。
5. 确保 tool id 在 `mcp/mcp.config.yaml`、`agent.yaml` 和对应 skill manifest 里一致。

### 4. RAG Resources / RAG 资源

RAG documents can stay inside this template folder if your MCP/RAG tool reads from this path.

如果你的 MCP/RAG 工具会从本文件夹读取资料，那么 RAG 文档可以继续放在这里。

Recommended location:

推荐位置：

```text
rag/documents/
```

Register each resource in:

每个资源都需要注册在：

```text
rag/resources.yaml
```

Make sure each resource ID is also allowed in:

同时确保 resource id 也出现在：

```text
agent.yaml
skills/skill.template.yaml
```

### 5. Memory And Logs / Memory 与 Logs

Memory and logs can remain inside this agent folder.

Memory 和 logs 可以继续留在当前 agent 文件夹中。

Recommended usage:

推荐用法：

- `memory/outputs/`: save reusable agent outputs
- `memory/state/`: save runtime state or resumable state
- `logs/`: save execution traces, tool calls, validation failures, and errors

中文说明：

- `memory/outputs/`：保存可复用的 agent 输出
- `memory/state/`：保存运行状态或可恢复状态
- `logs/`：保存执行记录、工具调用、校验失败和错误

### 6. Practical Rule / 实用规则

Use this distinction:

请记住这个区别：

```text
Fill this folder = define the agent
Register Codex skills/MCP = make Codex able to use it
```

中文：

```text
填写这个文件夹 = 定义 agent
注册 Codex skills/MCP = 让 Codex 能真正调用它
```

## Design Rule

Do not put the top-level workflow inside this template.

This folder describes one agent only. The top-level workflow should call this agent and provide its assigned skill order.
