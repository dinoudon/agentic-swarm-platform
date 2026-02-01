# Using Without API Key (Claude Code / Interactive Mode)

Good news! You can use the Agentic Swarm Platform **without an Anthropic API key** by using the interactive backend.

## 🎯 Quick Start (No API Key)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run in Interactive Mode

```bash
python -m src.main run examples/sample_prd.md --backend interactive --output ./output
```

**No API key needed!** ✨

## 🤖 How Interactive Mode Works

When you run with `--backend interactive`:

1. **The platform analyzes the PRD** and creates a task breakdown
2. **Tasks are displayed one by one** with full instructions
3. **You execute each task** by asking Claude Code (me!) to complete it
4. **You save the response** to a file
5. **The platform continues** to the next task
6. **Final results are aggregated** just like with API mode

## 📝 Step-by-Step Example

### Step 1: Start the Platform

```bash
python -m src.main run examples/sample_prd.md --backend interactive
```

### Step 2: You'll See Task Prompts

```
======================================================================
📝 TASK #1
======================================================================

📌 SYSTEM INSTRUCTIONS:
----------------------------------------------------------------------
You are an expert project manager analyzing a Product Requirements Document...

📌 TASK:
----------------------------------------------------------------------
Please analyze the following PRD and break it down into actionable tasks...

======================================================================
Task saved to: ./interactive_tasks/task_001.md

💡 You can now:
  1. Copy the task above
  2. Ask Claude Code to complete it
  3. Copy the response
  4. Paste it in the response file
======================================================================

⏳ Waiting for response file: ./interactive_tasks/task_001_response.txt
```

### Step 3: Execute with Claude Code

Open the task file or copy the prompt, then ask me (Claude Code):

```
Please complete this task:

[Paste the system instructions and task]

Then save your response to: ./interactive_tasks/task_001_response.txt
```

### Step 4: I'll Execute and Save

I'll:
1. Read the task
2. Complete it
3. Save the response to the specified file

### Step 5: Platform Continues

Once the file is saved, the platform:
1. Reads my response
2. Proceeds to the next task
3. Repeats until all tasks are done

## 🎨 Benefits of Interactive Mode

### ✅ Advantages

- **No API Key Required** - Use it immediately
- **No API Costs** - Completely free (using your existing Claude Code access)
- **Full Control** - Review each task before execution
- **Educational** - See exactly what each agent does
- **Flexible** - Can modify tasks on the fly

### ⚠️ Limitations

- **Slower** - Manual intervention required for each task
- **Not Parallel** - Tasks execute sequentially
- **Requires Interaction** - Can't run unattended

## 🔧 Configuration

### Use Interactive by Default

Edit `config/default.yaml`:

```yaml
backend:
  type: "interactive"
```

### Or Use Environment Variable

```bash
export BACKEND__TYPE=interactive
```

### Or Use CLI Flag

```bash
python -m src.main run my-prd.md --backend interactive
```

## 🚀 Alternative: Claude Code Backend

If you have Claude Code CLI installed:

```bash
python -m src.main run examples/sample_prd.md --backend claude-code
```

This attempts to use the `claude` CLI command to execute tasks automatically.

## 📊 Comparison

| Feature | Anthropic API | Interactive | Claude Code |
|---------|---------------|-------------|-------------|
| API Key | Required ✗ | Not Required ✓ | Not Required ✓ |
| Cost | $2-3 per PRD | Free ✓ | Free ✓ |
| Speed | Fast (2-5 min) | Slow (manual) | Medium |
| Parallel | Yes | No | Limited |
| Automation | Full | None | Partial |
| Best For | Production | Learning, No API key | Local development |

## 💡 Tips for Interactive Mode

### 1. Keep Tasks Organized

The platform creates:
- `interactive_tasks/task_001.md` - Task description
- `interactive_tasks/task_001_response.txt` - Your response

### 2. Use a Template

For each task, I'll complete it and save following this pattern:

```bash
# Read task
cat interactive_tasks/task_001.md

# Complete task (I'll help with this)

# Save response
cat > interactive_tasks/task_001_response.txt << 'EOF'
[My complete response here]
EOF
```

### 3. Review Before Saving

Since you see each task, you can:
- Modify the task if needed
- Add additional context
- Skip tasks that aren't needed

### 4. Resume If Interrupted

If the process is interrupted:
1. Check which task file was last created
2. Complete any pending task_xxx_response.txt files
3. The platform will resume from where it stopped

## 🎯 Recommended Workflow

### For Learning
Use **interactive mode** to understand how the platform works:
```bash
python -m src.main run examples/sample_prd.md --backend interactive
```

### For Production (with API key)
Use **anthropic mode** for speed:
```bash
python -m src.main run my-prd.md --backend anthropic
```

### For Local Development (with Claude CLI)
Use **claude-code mode**:
```bash
python -m src.main run my-prd.md --backend claude-code
```

## 📖 Full Example Session

```bash
# Terminal 1: Start the platform
$ python -m src.main run examples/sample_prd.md --backend interactive

# You see:
# 📝 TASK #1
# [Task description]
# Waiting for: interactive_tasks/task_001_response.txt

# Terminal 2: Ask me (Claude Code)
$ # You ask: "Please read interactive_tasks/task_001.md and complete it,
$ #           then save to interactive_tasks/task_001_response.txt"

# I execute the task and create the file

# Terminal 1: Platform continues
# ✅ Task #1 completed!
# 📝 TASK #2
# [Next task...]
```

## 🆘 Troubleshooting

**Q: The platform says "waiting for response file"**
A: Create the file with your response:
```bash
cat > interactive_tasks/task_NNN_response.txt << 'EOF'
Your response here
EOF
```

**Q: Can I skip a task?**
A: Yes, just create an empty or minimal response file to proceed.

**Q: How do I stop and resume?**
A: Ctrl+C to stop. To resume, restart and complete any pending response files.

## 🎉 You're Ready!

No API key? No problem! Run:

```bash
python -m src.main run examples/sample_prd.md --backend interactive
```

And I'll help you execute each task! 🚀
