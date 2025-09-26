# Claude MCP Server Setup

A complete Model Context Protocol (MCP) server implementation that extends Claude Pro with internet search, GitHub integration, and Frappe database connectivity.

## 🚀 Features

- **Internet Search**: Web search capabilities using Google Custom Search API
- **GitHub Integration**: Repository management, file access, and issue tracking
- **Frappe Database**: Direct database queries and document management
- **Easy Management**: Scripts for starting, stopping, and monitoring all servers
- **Comprehensive Logging**: Detailed logs for debugging and monitoring
- **Environment Management**: Secure credential handling with `.env` files

## 📋 Prerequisites

- Python 3.8 or higher
- Claude Pro (Desktop application)
- API credentials for:
  - Google Custom Search API
  - GitHub Personal Access Token
  - Frappe site (optional)

## 🛠️ Installation

1. **Clone or create the project directory:**
   ```bash
   mkdir claude-mcp-setup
   cd claude-mcp-setup
   ```

2. **Create the folder structure:**
   ```
   claude-mcp-setup/
   ├── servers/
   ├── scripts/
   ├── config/
   ├── requirements/
   ├── logs/
   └── pids/
   ```

3. **Set up Python virtual environment:**
   ```bash
   python -m venv mcp-env
   source mcp-env/bin/activate  # On Windows: mcp-env\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install mcp python-dotenv requests PyGithub
   ```

## ⚙️ Configuration

### 1. Environment Variables

Create a `.env` file in the project root:

```env
# Google Custom Search API
GOOGLE_API_KEY=your_google_api_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id

# GitHub Integration
GITHUB_PERSONAL_ACCESS_TOKEN=your_github_token

# Frappe Database (optional)
FRAPPE_SITE_URL=https://your-frappe-site.com
FRAPPE_API_KEY=your_frappe_api_key
FRAPPE_API_SECRET=your_frappe_api_secret
```

### 2. Claude Pro Configuration

Add to your Claude Pro configuration file:

**Location:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "internet-access": {
      "command": "python",
      "args": ["/full/path/to/claude-mcp-setup/servers/internet_server.py"],
      "env": {
        "GOOGLE_API_KEY": "your_google_api_key",
        "GOOGLE_SEARCH_ENGINE_ID": "your_search_engine_id"
      }
    },
    "github-integration": {
      "command": "python",
      "args": ["/full/path/to/claude-mcp-setup/servers/github_server.py"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "your_github_token"
      }
    },
    "frappe-database": {
      "command": "python",
      "args": ["/full/path/to/claude-mcp-setup/servers/frappe_server.py"],
      "env": {
        "FRAPPE_SITE_URL": "https://your-frappe-site.com",
        "FRAPPE_API_KEY": "your_frappe_api_key",
        "FRAPPE_API_SECRET": "your_frappe_api_secret"
      }
    }
  }
}
```

## 🎯 Usage

### Starting Servers

```bash
# Start all servers
python scripts/start_all_servers.py

# Check server status
python scripts/check_server_status.py
```

### Stopping Servers

```bash
# Stop all servers
python scripts/stop_all_servers.py
```

### Testing Environment

```bash
# Test environment variable loading
python scripts/test_env.py
```

## 💬 Claude Pro Integration

Once configured, you can use these tools through natural language with Claude Pro:

### Internet Search Examples

```
Claude, search for "latest AI developments 2024"
Claude, find information about Python web scraping
Claude, look up the current Bitcoin price
```

### GitHub Integration Examples

```
Claude, list my GitHub repositories
Claude, show me the README from my project "website-backend"
Claude, create an issue titled "Fix login bug" in my repository
Claude, list open issues in my project
```

### Frappe Database Examples

```
Claude, get me a list of all customers from Frappe
Claude, show details of customer "CUST-001"
Claude, list all sales orders from this month
```

## 🔧 Available Tools

### Internet Server Tools
- `web_search(query, max_results)` - Search the web using Google Custom Search
- `web_fetch(url)` - Fetch content from a specific URL

### GitHub Server Tools
- `list_repositories(username)` - List repositories for a user
- `get_file_content(repo_name, file_path, branch)` - Get file content
- `list_issues(repo_name, state)` - List repository issues
- `create_issue(repo_name, title, body)` - Create new issues

### Frappe Server Tools
- `frappe_get_document(doctype, name)` - Get specific document
- `frappe_get_list(doctype, filters, fields, limit)` - List documents with filters
- `frappe_create_document(doctype, data)` - Create new documents

## 📁 Project Structure

```
claude-mcp-setup/
├── servers/
│   ├── internet_server.py      # Google Custom Search integration
│   ├── github_server.py        # GitHub API integration
│   └── frappe_server.py        # Frappe database connectivity
├── scripts/
│   ├── start_all_servers.py    # Start all MCP servers
│   ├── stop_all_servers.py     # Stop all MCP servers
│   ├── check_server_status.py  # Check server status
│   └── test_env.py             # Test environment loading
├── config/
│   └── mcp_settings.json       # MCP configuration template
├── requirements/
│   ├── common.txt              # Common dependencies
│   ├── internet_requirements.txt
│   ├── github_requirements.txt
│   └── frappe_requirements.txt
├── logs/                       # Server log files
├── pids/                       # Process ID files
├── .env                        # Environment variables
└── README.md                   # This file
```

## 🛡️ Security Notes

- Never commit your `.env` file to version control
- Use environment variables for all sensitive data
- Regularly rotate your API keys
- Monitor API usage to avoid exceeding quotas

## 📊 API Limits

### Google Custom Search API
- **Free Tier**: 100 queries per day
- **Paid Plans**: Starting at $5 per 1,000 queries

### GitHub API
- **Authenticated**: 5,000 requests per hour
- **Unauthenticated**: 60 requests per hour

### Frappe API
- Depends on your Frappe instance configuration

## 🐛 Troubleshooting

### Servers Won't Start
1. Check Python virtual environment is activated
2. Verify all dependencies are installed
3. Check file permissions
4. Review log files in `logs/` directory

### Claude Pro Can't Find Tools
1. Verify MCP configuration file path and syntax
2. Ensure servers are running before starting Claude Pro
3. Restart Claude Pro after configuration changes
4. Check server logs for connection errors

### API Authentication Errors
1. Verify API keys in `.env` file
2. Check API key permissions and quotas
3. Test API credentials independently
4. Review API documentation for changes

### Environment Variables Not Loading
1. Ensure `python-dotenv` is installed
2. Check `.env` file formatting (no spaces around `=`)
3. Verify `.env` file is in project root
4. Run `python scripts/test_env.py` to debug

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- [Anthropic](https://www.anthropic.com/) for Claude and MCP protocol
- [Google Custom Search API](https://developers.google.com/custom-search)
- [GitHub API](https://docs.github.com/en/rest)
- [Frappe Framework](https://frappeframework.com/)

## 📚 Additional Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Pro Documentation](https://support.claude.com/)
- [Google Custom Search Setup Guide](https://developers.google.com/custom-search/v1/introduction)
- [GitHub Personal Access Tokens](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)

---

**Note**: This is a development setup. For production use, consider implementing additional security measures, error handling, and monitoring capabilities.