# .ai-context — AI Shared Context Layer

This directory is the single source of truth for AI coding assistants working on
this project. Commit it alongside your code.

## Files

| File | Purpose | Update frequency |
|---|---|---|
| `CONTEXT.md` | Stack, structure, conventions, known issues | Rarely (when stack changes) |
| `PROGRESS.md` | What's done, what's in flight, blockers | End of every session |
| `TASKS.md` | Current sprint tasks | As tasks are added/completed |
| `DECISIONS.md` | Architecture decision records (why things are how they are) | When a design decision is made |

## How to use with each tool

### Aider (recommended for file edits)
```bash
aider --read .ai-context/CONTEXT.md \
      --read .ai-context/PROGRESS.md \
      --read .ai-context/TASKS.md
```

Or add to `~/.aider.conf.yml`:
```yaml
read:
  - .ai-context/CONTEXT.md
  - .ai-context/PROGRESS.md
```

### Claude Code
```bash
# Paste context at session start
cat .ai-context/CONTEXT.md .ai-context/PROGRESS.md | claude
```

### Zed AI panel
Paste the contents of CONTEXT.md into the system prompt field in Zed's AI settings.

### Shell alias (add to ~/.zshrc)
```bash
alias vcamon-ai='aider \
  --read .ai-context/CONTEXT.md \
  --read .ai-context/PROGRESS.md \
  --read .ai-context/TASKS.md'
```

## End-of-session checklist

1. Update `PROGRESS.md` — move completed tasks, note new blockers
2. Update `TASKS.md` — tick off done items, add anything discovered
3. Commit: `git add .ai-context/ && git commit -m "chore: update ai context"`
