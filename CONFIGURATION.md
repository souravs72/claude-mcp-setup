# .env Configuration Guide

## 🔧 Complete `.env` File Setup

Copy this template and fill in your actual values:

```bash
# ============================================
# BRAVE SEARCH (Optional - for web search)
# ============================================
BRAVE_API_KEY=your_brave_api_key_here

# ============================================
# GITHUB (Required for GitHub integration)
# ============================================
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_yourGitHubTokenHere

# ============================================
# FRAPPE (Required for Frappe/ERPNext)
# ============================================
FRAPPE_SITE_URL=http://127.0.0.1:8005
FRAPPE_API_KEY=your_frappe_api_key
FRAPPE_API_SECRET=your_frappe_api_secret

# ============================================
# GOOGLE SEARCH (Required for web search)
# ============================================
GOOGLE_API_KEY=AIzaSyYourGoogleAPIKeyHere
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# ============================================
# JIRA (Required for Jira integration)
# ============================================
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_API_TOKEN=your_jira_api_token_here
JIRA_PROJECT_KEY=CGV2
JIRA_RATE_LIMIT_DELAY=0.5
```

---

## 📝 How to Get Each Credential

### 1. BRAVE_API_KEY (Optional)
**Used for:** Alternative web search

**How to get:**
1. Go to https://brave.com/search/api/
2. Sign up for Brave Search API
3. Get your API key from dashboard
4. **Note:** This is optional if you're using Google Search

---

### 2. GITHUB_PERSONAL_ACCESS_TOKEN
**Used for:** GitHub repository access, issues, PRs

**How to get:**
1. Go to https://github.com/settings/tokens
2. Click "Generate new token" → "Generate new token (classic)"
3. Give it a name: `MCP Server Token`
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `read:org` (Read org data)
   - ✅ `workflow` (Update GitHub Actions workflows)
5. Click "Generate token"
6. **Copy immediately** (you won't see it again!)
7. Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**Example:**
```bash
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_1234567890abcdefghijklmnopqrstuvwxyz
```

---

### 3. FRAPPE Configuration
**Used for:** Frappe Framework / ERPNext integration

#### FRAPPE_SITE_URL
Your Frappe site URL:
```bash
# Local development
FRAPPE_SITE_URL=http://127.0.0.1:8005

# Or custom port
FRAPPE_SITE_URL=http://localhost:8000

# Production
FRAPPE_SITE_URL=https://your-site.frappe.cloud
```

#### FRAPPE_API_KEY & FRAPPE_API_SECRET
**How to get:**
1. Login to your Frappe site
2. Go to: **User Menu** → **API Access**
3. Or direct URL: `http://your-site/app/user-api-keys`
4. Click "Generate Keys" for your user
5. Copy both API Key and API Secret

**Alternative method (via console):**
```python
# In Frappe console
from frappe.core.doctype.user.user import generate_keys
generate_keys("your-email@example.com")
```

**Example:**
```bash
FRAPPE_API_KEY=1234567890abcdef
FRAPPE_API_SECRET=abcdefghijklmnop
```

---

### 4. GOOGLE_API_KEY
**Used for:** Google Custom Search API

**How to get:**
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing
3. Enable **Custom Search API**:
   - Go to "APIs & Services" → "Library"
   - Search for "Custom Search API"
   - Click "Enable"
4. Create credentials:
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "API Key"
   - Copy the API key
5. (Optional) Restrict the key to Custom Search API only

**Example:**
```bash
GOOGLE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

### 5. GOOGLE_SEARCH_ENGINE_ID
**Used for:** Custom Search Engine configuration

**How to get:**
1. Go to https://programmablesearchengine.google.com/
2. Click "Add" to create a new search engine
3. Configure:
   - **Sites to search:** `www.google.com` (or your specific sites)
   - **Name:** Any name you want
   - **Search entire web:** Turn ON (recommended)
4. Click "Create"
5. Go to "Setup" → Copy your "Search engine ID"

**Example:**
```bash
GOOGLE_SEARCH_ENGINE_ID=a1b2c3d4e5f6g7h8i
```

**💡 Tip:** You get 100 free searches per day. For more, you need billing enabled.

---

### 6. JIRA Configuration
**Used for:** Jira Cloud integration

#### JIRA_BASE_URL
Your Jira Cloud URL:
```bash
# Format: https://YOUR-DOMAIN.atlassian.net
JIRA_BASE_URL=https://clapgrow.atlassian.net
```

**How to find:** Look at your Jira URL when logged in.

---

#### JIRA_EMAIL
The email you use to login to Jira:
```bash
JIRA_EMAIL=your-email@example.com
```

---

#### JIRA_API_TOKEN
**How to get:**
1. Go to https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Give it a label: `MCP Server Token`
4. Click "Create"
5. **Copy immediately** (you won't see it again!)

**Example:**
```bash
JIRA_API_TOKEN=ATATT3xFfGF0123456789abcdefghijklmnopqrstuvwxyz
```

---

#### JIRA_PROJECT_KEY
Your default Jira project key:
```bash
JIRA_PROJECT_KEY=CGV2
```

**How to find:**
1. Go to your Jira project
2. Look at the URL: `https://domain.atlassian.net/browse/CGV2`
3. The project key is `CGV2` (the part after `/browse/`)

**Or:**
- Look at any issue: `CGV2-123` → project key is `CGV2`

---

#### JIRA_RATE_LIMIT_DELAY
Delay between API requests (in seconds):
```bash
JIRA_RATE_LIMIT_DELAY=0.5
```

**Recommended values:**
- `0.5` - Default (2 requests per second)
- `1.0` - Conservative (1 request per second)
- `0.25` - Aggressive (4 requests per second)

---

## 📋 Complete Example

Here's a filled example (use your own values!):

```bash
# ============================================
# BRAVE SEARCH (Optional)
# ============================================
BRAVE_API_KEY=BSAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============================================
# GITHUB
# ============================================
GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# ============================================
# FRAPPE
# ============================================
FRAPPE_SITE_URL=http://127.0.0.1:8005
FRAPPE_API_KEY=1a2b3c4d5e6f7g8h
FRAPPE_API_SECRET=9i8h7g6f5e4d3c2b

# ============================================
# GOOGLE SEARCH
# ============================================
GOOGLE_API_KEY=AIzaSyDxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_SEARCH_ENGINE_ID=a1b2c3d4e5f6g7h8i

# ============================================
# JIRA
# ============================================
JIRA_BASE_URL=https://clapgrow.atlassian.net
JIRA_EMAIL=developer@clapgrow.com
JIRA_API_TOKEN=ATATT3xFfGF0xxxxxxxxxxxxxxxxxxxxxxxxxx
JIRA_PROJECT_KEY=CGV2
JIRA_RATE_LIMIT_DELAY=0.5
```

---

## 🔒 Security Best Practices

### ✅ DO:
- Keep `.env` file in `.gitignore`
- Use separate tokens for dev/prod
- Rotate tokens every 90 days
- Use minimal required scopes
- Store backups securely (encrypted)

### ❌ DON'T:
- Commit `.env` to git
- Share tokens in chat/email
- Use same token across projects
- Give tokens excessive permissions
- Store in plain text outside project

---

## 🧪 Testing Your Configuration

After filling the `.env` file, test each service:

### Test Script
```bash
# Run the configuration checker
python scripts/start_all_servers.py
```

### Manual Tests in Claude

**Test Jira:**
```
"List my Jira projects"
"What issue types are in CGV2?"
```

**Test GitHub:**
```
"List my GitHub repositories"
```

**Test Frappe:**
```
"Get list of customers from Frappe"
```

**Test Google Search:**
```
"Search the web for Python tutorials"
```

---

## 🚨 Troubleshooting

### Issue: "Configuration validation failed"
**Solution:** Check that all required fields are filled in the `.env` file

### Issue: "Authentication failed" (Jira)
**Solutions:**
- Verify `JIRA_EMAIL` matches your Atlassian account
- Regenerate `JIRA_API_TOKEN` if expired
- Check `JIRA_BASE_URL` format (include `https://`)

### Issue: "Authentication failed" (GitHub)
**Solutions:**
- Verify token hasn't expired
- Check token has correct scopes (repo access)
- Regenerate token if needed

### Issue: "API quota exceeded" (Google)
**Solutions:**
- You have 100 free searches/day
- Enable billing for more quota
- Use Brave Search as alternative

### Issue: "Connection refused" (Frappe)
**Solutions:**
- Verify Frappe is running: `bench start`
- Check correct port in `FRAPPE_SITE_URL`
- Test URL in browser first

---

## 📁 File Location

Your `.env` file should be in your project root:

```
your-mcp-project/
├── .env                    ← Put your .env here
├── servers/
│   ├── jira_server.py
│   ├── github_server.py
│   └── ...
├── scripts/
└── logs/
```

---

## ✅ Verification Checklist

After setup, verify:

- [ ] `.env` file exists in project root
- [ ] All required variables are filled
- [ ] No quotes around values
- [ ] No spaces around `=` signs
- [ ] `.env` is in `.gitignore`
- [ ] Tokens are valid and not expired
- [ ] Services respond to test commands
- [ ] Claude Desktop restarted after changes

---

## Updating Credentials

If you need to change credentials:

1. Update the `.env` file
2. **Completely quit** Claude Desktop
3. Restart Claude Desktop
4. Test the affected service

Changes take effect after Claude Desktop restart!

---

## 💡 Pro Tips

1. **Create a `.env.example` file** with empty values for team members:
   ```bash
   cp .env .env.example
   # Then remove actual values from .env.example
   ```

2. **Use different keys for different environments:**
   ```bash
   # Development
   .env

   # Production  
   .env.production
   ```

3. **Document which services you're using:**
   ```bash
   # Add comments in .env
   # ✅ Using Jira
   # ❌ Not using Brave Search
   ```

4. **Keep a secure backup:**
   - Store in password manager
   - Or encrypted file
   - Never in plain text cloud storage

---

## 📞 Need Help?

If you have issues:

1. Check the logs: `logs/jira_server.log`
2. Verify credentials in original service
3. Test API access with curl
4. Review error messages carefully
5. Check this guide's troubleshooting section

Good luck!