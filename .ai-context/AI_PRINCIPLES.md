ai_principles_content = """# AI Interaction Principles for VCA Monitor Project

These principles guide the interaction with AI coding assistants (like Zed Agent, Claude Code, Aider) working on the VCA Monitor project.

## 1. Using Sub-Agents for "Context-Heavy" Research

When comprehensive research across many files is needed, prefer to abstract this work.

*   **Inefficient Way:** Reading many files in the main chat, flooding the context window, leading to context loss and re-reads.
*   **Efficient Way (for tools that support it):** Spawning an isolated "Explore Agent" to read, analyze, and return a concise summary (e.g., 5-bullet points) to the main chat. The raw file content noise never hits the main chat.
*   **Application for vcamon-app:** When tackling tasks like "Align with PH Terminology," an Explore agent (if available in the tool) would map "draft" terms across the repo and provide a summary report.

## 2. Using the Task System as a "State Machine"

Leverage the task management system (e.g., TaskCreate, TaskUpdate tools, or `TASKS.md` file) as an "external memory" to track project progress.

*   **The Strategy:** Break complex refactors or migrations into atomic tasks. Marking a task as completed signals that its technical details can be "compressed" or considered resolved.
*   **Benefit:** In case of session restarts or context compression, the AI can query the task list (`TaskList` equivalent) to immediately ascertain the exact state of the project, avoiding "Where were we?" questions.

## 3. Leveraging Persistent Memory for "Global Constraints"

Critical project-specific rules, architectural decisions, and glossaries should be stored in a persistent, efficiently accessible manner.

*   **The Strategy (for tools that support it):** Migrate `PRINCIPLES.md` and `GLOSSARY.md` content into the AI's native persistent memory (e.g., `~/.claude/projects/.../memory/`).
*   **Benefit:** Native memory injection by the system is more efficient. This ensures constraints (like "The Clinical Wall") are implicitly part of the AI's operating personality for the project, reducing the need for explicit "reminders" or repetitive file reads.
*   **For tools without native memory (like Zed Agent):** These constraints should be present in project-level context files (e.g., `.ai-context/`) that are loaded at the start of each session.

---

### Summary for AI Workflow

| Need             | Inefficient Approach           | Efficient Skill/Tool/Mechanism           |
| :--------------- | :----------------------------- | :--------------------------------------- |
| Finding a symbol | Read 5 files manually          | Agent(subagent_type="Explore") (if supported) / Request summary from AI |
| Tracking progress| "What's left to do?"           | `TASKS.md` / TaskList                    |
| Enforcing rules  | "Remember to use the glossary" | Persistent memory (if supported) / `.ai-context` files |
| Analyzing a bug  | Dumping 200 lines of logs      | Bash $\rightarrow$ grep $\rightarrow$ concise output / Focused log snippets + AI analysis |

---
"""
# This is a simulated action. I cannot directly write to your file system.
# Please create this file yourself or instruct me to do so with a tool.
# I will proceed as if this file has been created.
print(f"I am simulating creating the file: `vcamon-app/.ai-context/AI_PRINCIPLES.md` with the provided content.")
