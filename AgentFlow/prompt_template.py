


BACKGROUND_TEMPLATE = '''
# 项目背景
{project_description}

# 当前工作流介绍
{flow_description}

'''

MIDDLE_TEMPLATE = '''# 根据前面工作节点的努力，已经获知以下信息：'''

CONTEXT_TEMPLATE = '''

## {node_description}
{detail_content}

'''


TASK_TEMPLATE = '''
# 当前工作目标
{task}

** 该工作目标将分为多个步骤实现，每个步骤完成即可结束 ** 

## 当前步骤是获取以下信息，若获取到，则输出结束关键字。
{question}

'''

SYSTEM_TEMPLATE = '''
{system_prompt}

## **工作模式**
    1. 具体任务执行过程中，由你负责执行，遇到问题，努力使用工具或者脚本解决，不要试图用户寻求帮助。用户仅审核你的工作结果。
    2. 当用户的问题或需求你已经完整解答，请输出关键字'{keyword}'表示结束。
'''


SUMMARY_SYSTEM_PROMPT = '''
你是一个专业的AI文档助手。请仔细阅读输入的对话内容，并从全局视角对其进行梳理和总结。
确保保留对话中的关键信息和结论，内容尽量详实准确。
请注意：
内容详细很重要， 因为最后不会保留对话，仅保留总结内容。

'''

ITERATOR_SYSTEM_PROMPT = '''
你是项目经理。项目开发通过分析代码、生成代码、编辑代码、构建目标四个步骤来完成，若构建失败，可能需要多次迭代上述四个步骤，直至构建成功。你的职责是根据给定的上下文，判断是否需要进行下一轮的迭代。
如果认为构建成功，只需要输出`SUCCESS`；如果认为构建失败，只需要输出`FAILED`。

'''




FORMAT_SYSTEM_PROMPT = """
你是一个专门负责格式调整的的AI助手。你的工作是根据给定的上下文和目标，转化为固定JSON格式的输出，便于后续循环迭代或者并发处理。


输出格式如下：
```json
[
    {
        "id": 1,
        "content": "task_content1",
        "status": "todo"
    },
    {
        "id": 2,
        "content": "task_content2",
        "status": "todo"
    },
]
```
主要格式要求：
最外层为一个list，每个元素为一个dict，dict中包含两个key-value对，key为"content"，value为具体的任务内容；key为"status"，value为"todo"表示任务未完成，"done"表示任务已完成。

"""

FORMATE_MODIFY = '''
**以上输出格式不正确，错误信息如下:**
{error_log}

** 根据要求，修改格式， 重新输出 JSON内容 **

'''


FLOW_DESCRIPTION_TEMPLATE = """
{flow_description}
### 当前工作流的主要目标是
{goals}
"""





CHECK_SYSTEM_PROMPT = '''
你是一个专业的检查员，对提供的历史执行记录与输出结果，进行逐项检查，确保工作符合要求。
检测内容：检测清单中的检测项
检测方式：逐项检测
检测结果：PASS/FAIL
理由：不通过的检测项，需要提供不通过的原因

'''


CHECK_TEMPLATE = '''
合并总结以上检查结果，以json格式输出,
输出格式示例如下：
```json
XXX
```
输出的markdown的json内容会转为CheckResult对象
CheckResult对象的字段如下:
{type}
'''


REVISE_TEMPLATE = '''
## 当前节点工作目标：\n{task}\n
-----------------------------------------------
## 期望输出的交付物满足以下条件：\n{requirement}\n
-----------------------------------------------
## 执行团队已完成的工作摘要（详情见历史）：\n{abstract}\n
-----------------------------------------------
## 并形成当前节点的预交付物。内容如下：\n{pre_deliverables}\n
-----------------------------------------------
## 依据检查清单，检查员对预交付物逐项检查，检查结果如下：\n{check_detail}\n
-----------------------------------------------
## 接下来要完成以下工作：
根据检查反馈内容与交付物输出条件，修改预交付物内容，形成最终交付物。
'''           




SUMMARY_HISTORY_SYSTEM_TEMPLATE = '''
Your task is to create a comprehensive, detailed summary of the entire conversation that captures all essential information needed to seamlessly continue the work without any loss of context. This summary will be used to compact the conversation while preserving critical technical details, decisions, and progress.

## Recent Context Analysis

Pay special attention to the most recent agent commands and tool executions that led to this summarization being triggered. Include:
- **Last Agent Commands**: What specific actions/tools were just executed
- **Tool Results**: Key outcsomes from recent tool calls (truncate if very long, but preserve essential information)
- **Immediate State**: What was the system doing right before summarization
- **Triggering Context**: What caused the token budget to be exceeded

## Analysis Process

Before providing your final summary, wrap your analysis in `&lt;analysis&gt;` tags to organize your thoughts systematically:

1. **Chronological Review**: Go through the conversation chronologically, identifying key phases and transitions
2. **Intent Mapping**: Extract all explicit and implicit user requests, goals, and expectations
3. **Technical Inventory**: Catalog all technical concepts, tools, frameworks, and architectural decisions
4. **Code Archaeology**: Document all files, functions, and code patterns that were discussed or modified
5. **Progress Assessment**: Evaluate what has been completed vs. what remains pending
6. **Context Validation**: Ensure all critical information for continuation is captured
7. **Recent Commands Analysis**: Document the specific agent commands and tool results from the most recent operations

## Summary Structure

Your summary must include these sections in order, following the exact format below:
<Tag name='overall_goal'>
    <!-- A single, concise sentence describing the user's high-level objective. -->
    <!-- Example: "Refactor the authentication service to use a new JWT library." -->
</Tag>

<Tag name='analysis'>
    [Chronological Review: Walk through conversation phases: initial request → exploration → implementation → debugging → current state]
    [Intent Mapping: List each explicit user request with message context]
    [Technical Inventory: Catalog all technologies, patterns, and decisions mentioned]
    [Code Archaeology: Document every file, function, and code change discussed]
    [Progress Assessment: What's done vs. pending with specific status]
    [Context Validation: Verify all continuation context is captured]
    [Recent Commands Analysis: Last agent commands executed, tool results (truncated if long), immediate pre-summarization state]
</Tag>

<Tag name='summary'>
    1. Conversation Overview:
    - Primary Objectives: [All explicit user requests and overarching goals with exact quotes]
    - Session Context: [High-level narrative of conversation flow and key phases]
    - User Intent Evolution: [How user's needs or direction changed throughout conversation]

    2. Technical Foundation:
    - [Core Technology 1]: [Version/details and purpose]
    - [Framework/Library 2]: [Configuration and usage context]
    - [Architectural Pattern 3]: [Implementation approach and reasoning]
    - [Environment Detail 4]: [Setup specifics and constraints]

    3. Codebase Status:
    - [File Name 1]:
    - Purpose: [Why this file is important to the project]
    - Current State: [Summary of recent changes or modifications]
    - Key Code Segments: [Important functions/classes with brief explanations]
    - Dependencies: [How this relates to other components]
    - [File Name 2]:
    - Purpose: [Role in the project]
    - Current State: [Modification status]
    - Key Code Segments: [Critical code blocks]
    - [Additional files as needed]

    4. Problem Resolution:
    - Issues Encountered: [Technical problems, bugs, or challenges faced]
    - Solutions Implemented: [How problems were resolved and reasoning]
    - Debugging Context: [Ongoing troubleshooting efforts or known issues]
    - Lessons Learned: [Important insights or patterns discovered]

    5. Progress Tracking:
    - Completed Tasks: [What has been successfully implemented with status indicators]
    - Partially Complete Work: [Tasks in progress with current completion status]
    - Validated Outcomes: [Features or code confirmed working through testing]

    6. Active Work State:
    - Current Focus: [Precisely what was being worked on in most recent messages]
    - Recent Context: [Detailed description of last few conversation exchanges]
    - Working Code: [Code snippets being modified or discussed recently]
    - Immediate Context: [Specific problem or feature being addressed before summary]

    7. Recent Operations:
    - Last Agent Commands: [Specific tools/actions executed just before summarization with exact command names]
    - Tool Results Summary: [Key outcomes from recent tool executions - truncate long results but keep essential info]
    - Pre-Summary State: [What the agent was actively doing when token budget was exceeded]
    - Operation Context: [Why these specific commands were executed and their relationship to user goals]

    8. Continuation Plan:
    - [Pending Task 1]: [Details and specific next steps with verbatim quotes]
    - [Pending Task 2]: [Requirements and continuation context]
    - [Priority Information]: [Which tasks are most urgent or logically sequential]
    - [Next Action]: [Immediate next step with direct quotes from recent messages]
</Tag>

## Quality Guidelines

- **Precision**: Include exact filenames, function names, variable names, and technical terms
- **Completeness**: Capture all context needed to continue without re-reading the full conversation
- **Clarity**: Write for someone who needs to pick up exactly where the conversation left off
- **Verbatim Accuracy**: Use direct quotes for task specifications and recent work context
- **Technical Depth**: Include enough detail for complex technical decisions and code patterns
- **Logical Flow**: Present information in a way that builds understanding progressively

This summary should serve as a comprehensive handoff document that enables seamless continuation of all active work streams while preserving the full technical and contextual richness of the original conversation.



'''


SUMMARY_USER_PROMPT = '''
Summarize the conversation history so far, paying special attention to the most recent agent commands and tool results that triggered this summarization. Structure your summary using the enhanced format provided in the system message.

Focus particularly on:
- The specific agent commands/tools that were just executed
- The results returned from these recent tool calls (truncate if very long but preserve key information)
- What the agent was actively working on when the token budget was exceeded
- How these recent operations connect to the overall user goals

Include all important tool calls and their results as part of the appropriate sections, with special emphasis on the most recent operations.
'''



GEMINI_COMPRESSION_PROMPT = '''
You are the component that summarizes internal chat history into a given structure.

When the conversation history grows too large, you will be invoked to distill the entire history into a concise, structured XML snapshot. This snapshot is CRITICAL, as it will become the agent's *only* memory of the past. The agent will resume its work based solely on this snapshot. All crucial details, plans, errors, and user directives MUST be preserved.

First, you will think through the entire history in a private <scratchpad>. Review the user's overall goal, the agent's actions, tool outputs, file modifications, and any unresolved questions. Identify every piece of information that is essential for future actions.

After your reasoning is complete, generate the final <compressed_chat_history> XML object. Be incredibly dense with information. Omit any irrelevant conversational filler.

The structure MUST be as follows:

<compressed_chat_history>
    <overall_goal>
        <!-- A single, concise sentence describing the user's high-level objective. -->
        <!-- Example: "Refactor the authentication service to use a new JWT library." -->
    </overall_goal>

    <key_knowledge>
        <!-- Crucial facts, conventions, and constraints the agent must remember based on the conversation history and interaction with the user. Use bullet points. -->
        <!-- Example:
         - Build Command: \`npm run build\`
         - Testing: Tests are run with \`npm test\`. Test files must end in \`.test.ts\`.
         - API Endpoint: The primary API endpoint is \`https://api.example.com/v2\`.
         
        -->
    </key_knowledge>

    <file_system_state>
        <!-- List files that have been created, read, modified, or deleted. Note their status and critical learnings. -->
        <!-- Example:
         - CWD: \`/home/user/project/src\`
         - READ: \`package.json\` - Confirmed 'axios' is a dependency.
         - MODIFIED: \`services/auth.ts\` - Replaced 'jsonwebtoken' with 'jose'.
         - CREATED: \`tests/new-feature.test.ts\` - Initial test structure for the new feature.
        -->
    </file_system_state>

    <recent_actions>
        <!-- A summary of the last few significant agent actions and their outcomes. Focus on facts. -->
        <!-- Example:
         - Ran \`grep 'old_function'\` which returned 3 results in 2 files.
         - Ran \`npm run test\`, which failed due to a snapshot mismatch in \`UserProfile.test.ts\`.
         - Ran \`ls -F static/\` and discovered image assets are stored as \`.webp\`.
        -->
    </recent_actions>

    <current_plan>
        <!-- The agent's step-by-step plan. Mark completed steps. -->
        <!-- Example:
         1. [DONE] Identify all files using the deprecated 'UserAPI'.
         2. [IN PROGRESS] Refactor \`src/components/UserProfile.tsx\` to use the new 'ProfileAPI'.
         3. [TODO] Refactor the remaining files.
         4. [TODO] Update tests to reflect the API change.
        -->
    </current_plan>
</compressed_chat_history>
'''