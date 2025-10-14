# Claude MCP Servers

Enterprise-grade Model Context Protocol servers that transform Claude into a full-stack development assistant with GitHub, Jira, Frappe ERP, and web capabilities.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0+-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/your-org/claude-mcp-setup.git
cd claude-mcp-setup

# Install everything
make setup

# Configure credentials
cp config/mcp_settings.json.template config/mcp_settings.json
nano config/mcp_settings.json

# Start all servers
make start
```

## 📚 Documentation

- **[Getting Started](GETTING_STARTED.md)** - Complete setup guide
- **[Configuration](CONFIGURATION.md)** - Environment setup and CLI usage
- **[Architecture](ARCHITECTURE.md)** - Technical implementation details
- **[API Reference](API_REFERENCE.md)** - Complete API documentation
- **[Troubleshooting](TROUBLESHOOTING.md)** - Common issues and solutions

## 🎯 What This Does

Transform Claude into an intelligent development assistant that can:

- **📋 Goal-Based Task Management** - Create complex projects with automatic task breakdown
- **💻 GitHub Integration** - Manage repositories, branches, PRs, and issues
- **🎫 Jira Management** - Create/update issues, manage sprints, link tickets
- **🌐 Web Access** - Google search, fetch web content, batch operations
- **💾 Persistent Storage** - PostgreSQL for durable state, Redis for caching
- **📊 Real-time Dashboard** - Monitor goals, tasks, and server status

## 🛠️ Management

```bash
# Check status
make status

# View dashboard
open http://localhost:8000

# CLI management
mcpctl status
mcpctl goal create "Test Goal" "Testing the system"
```

## 📊 GitHub Stats

<div align="center">

![GitHub Stats](https://github-readme-stats.vercel.app/api?username=souravs72&show_icons=true&theme=dark&hide_border=true&count_private=true)

![Top Languages](https://github-readme-stats.vercel.app/api/top-langs/?username=souravs72&layout=compact&theme=dark&hide_border=true&count_private=true)

![GitHub Streak](https://github-readme-streak-stats.herokuapp.com/?user=souravs72&theme=dark&hide_border=true)

</div>

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

---
