# Terms of Service Compliance

## ✅ This Software Complies with Claude's Terms of Service

The Agentic Swarm Platform is designed to fully comply with Anthropic's Terms of Service and Acceptable Use Policy.

---

## 🎯 **Compliant Backends**

### ✅ **Interactive Backend (Default)** - FULLY COMPLIANT

**How it works:**
- Displays tasks for manual execution
- User asks Claude Code to complete each task
- No automation, no scraping
- Manual human interaction required

**Why it's compliant:**
- Uses Claude Code exactly as intended
- No different from normal conversation
- Human in the loop for every task
- No programmatic abuse

**ToS Status:** ✅ **Fully Compliant**

---

### ✅ **Anthropic API Backend** - FULLY COMPLIANT

**How it works:**
- Uses official Anthropic Python SDK
- Requires user's personal API key
- Respects all rate limits
- Pays per token usage

**Why it's compliant:**
- Uses official, documented API
- This is exactly what the API is designed for
- Building applications on Claude is encouraged
- Respects all rate limits and guidelines
- User pays for their own usage

**ToS Status:** ✅ **Fully Compliant**

---

## ❌ **Removed Backend**

### ~~Claude Code CLI Backend~~ - REMOVED FOR SAFETY

**Why it was removed:**
- Automated CLI usage was a gray area
- Unclear if programmatic CLI access is intended
- Could be interpreted as circumventing API
- Better to be safe than sorry

**Status:** ❌ **Removed from platform**

---

## 📜 **Anthropic Terms of Service - What's Allowed**

Based on Anthropic's ToS and Acceptable Use Policy:

### ✅ **Allowed Uses:**

1. **Building Applications**
   - Creating tools and applications using the API ✅
   - This platform is a developer tool ✅

2. **API Usage**
   - Making sequential API requests ✅
   - Automating workflows with proper API key ✅
   - Respecting rate limits ✅

3. **Development**
   - Using Claude Code for development ✅
   - Creating developer tools ✅
   - Educational and research use ✅

4. **Our Platform Specifically:**
   - Task automation via API ✅
   - Multi-agent orchestration ✅
   - Code generation tools ✅

### ❌ **Prohibited Uses:**

1. **What We DON'T Do:**
   - ❌ Scraping Claude.ai website
   - ❌ Circumventing rate limits
   - ❌ Sharing API keys
   - ❌ Abusive automation
   - ❌ Unauthorized access

2. **Safety Measures:**
   - ✅ Rate limiting implemented
   - ✅ User provides own API key
   - ✅ Token usage tracked
   - ✅ Respects API guidelines

---

## 🛡️ **How We Ensure Compliance**

### 1. **Official API Usage**
```python
# We use the official Anthropic SDK
from anthropic import Anthropic
client = Anthropic(api_key=user_provided_key)
```

### 2. **Rate Limiting**
```python
# Built-in rate limiter
rate_limiter = RateLimiter(
    max_requests_per_minute=50,
    max_tokens_per_minute=200000,
)
```

### 3. **User Authentication**
```python
# User must provide their own API key
# We never share or pool API keys
ANTHROPIC_API_KEY=user_key_here
```

### 4. **Transparency**
- All API calls are logged
- Token usage tracked
- Costs displayed to user
- No hidden operations

---

## 📊 **Comparison with Other Tools**

| Feature | Our Platform | ToS Compliant? |
|---------|-------------|----------------|
| Uses official API | ✅ Yes | ✅ Yes |
| User provides API key | ✅ Yes | ✅ Yes |
| Respects rate limits | ✅ Yes | ✅ Yes |
| Tracks token usage | ✅ Yes | ✅ Yes |
| Manual mode available | ✅ Yes | ✅ Yes |
| Automated CLI scraping | ❌ No (removed) | ✅ N/A |
| Web scraping | ❌ No | ✅ N/A |

---

## 🎓 **Educational Use Case**

This platform is designed for:

1. **Learning**: Understanding multi-agent systems
2. **Development**: Rapid prototyping with AI
3. **Research**: Exploring agent-based architectures
4. **Productivity**: Automating development tasks

All of these are **legitimate, encouraged use cases** for Claude's API.

---

## ✅ **Official Guidance**

From Anthropic's documentation:

> "The Claude API enables you to build AI-powered applications..."

Our platform does exactly this - it's a development tool that helps users build with Claude.

### **We Follow Best Practices:**
- ✅ Use official SDK
- ✅ Handle errors gracefully
- ✅ Respect rate limits
- ✅ Track costs transparently
- ✅ Provide user control

---

## 🔒 **Privacy & Security**

### **What We DON'T Do:**
- ❌ Store user API keys
- ❌ Log user prompts
- ❌ Share user data
- ❌ Access user accounts

### **What We DO:**
- ✅ User manages their own API key
- ✅ All processing is local
- ✅ No data sent to third parties
- ✅ Open source & transparent

---

## 📖 **References**

- [Anthropic Terms of Service](https://www.anthropic.com/legal/consumer-terms)
- [Anthropic Acceptable Use Policy](https://www.anthropic.com/legal/aup)
- [Claude API Documentation](https://docs.anthropic.com/)

---

## ✅ **Conclusion**

The Agentic Swarm Platform is **fully compliant** with Anthropic's Terms of Service when used with the approved backends:

### **Recommended Usage:**

```bash
# For users without API key (100% compliant)
python -m src.main run prd.md --backend interactive

# For users with API key (100% compliant)
python -m src.main run prd.md --backend anthropic
```

### **Compliance Summary:**

| Backend | ToS Compliant | Recommended |
|---------|---------------|-------------|
| `interactive` | ✅ Yes | ✅ Yes (no API key) |
| `anthropic` | ✅ Yes | ✅ Yes (with API key) |
| ~~`claude-code`~~ | ⚠️ Uncertain | ❌ Removed |

---

## 🆘 **Questions?**

If you have concerns about ToS compliance:

1. Review Anthropic's [official Terms of Service](https://www.anthropic.com/legal/consumer-terms)
2. Use `interactive` backend for maximum safety
3. Use `anthropic` backend with your own API key
4. Contact Anthropic support for clarification on specific use cases

---

**Status:** ✅ **COMPLIANT**

This platform respects Anthropic's Terms of Service and uses only approved methods of accessing Claude.
