# Security Policy

## Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security vulnerability, please follow these steps:

### 1. **DO NOT** create a public issue

Security vulnerabilities should be reported privately to prevent exploitation.

### 2. Report via Email

Send an email to: **security@your-domain.com** (replace with your actual email)

Include the following information:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact
- Any suggested fixes (if you have them)

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Resolution**: As quickly as possible, typically within 30 days

### 4. What to Expect

- We will acknowledge receipt of your report
- We will investigate the vulnerability
- We will provide regular updates on our progress
- We will credit you in our security advisories (unless you prefer to remain anonymous)

## Security Best Practices

### For Users

1. **Keep Dependencies Updated**
   ```bash
   pip install --upgrade -r requirements.txt
   ```

2. **Use Environment Variables for Secrets**
   - Never commit API keys or tokens to version control
   - Use `config/mcp_settings.json.template` as a reference
   - Keep your actual `mcp_settings.json` in `.gitignore`

3. **Restrict File System Access**
   - The file and bash servers have built-in security restrictions
   - Only allow access to necessary directories
   - Review allowed paths in your configuration

4. **Monitor Logs**
   - Regularly check server logs for suspicious activity
   - Logs are stored in the `logs/` directory

### For Developers

1. **Input Validation**
   - Always validate user inputs
   - Use type hints and validation libraries
   - Sanitize file paths and commands

2. **Error Handling**
   - Don't expose sensitive information in error messages
   - Log errors appropriately
   - Use structured error responses

3. **Dependency Management**
   - Keep dependencies up to date
   - Use `pip-audit` to check for known vulnerabilities
   - Pin dependency versions in production

## Security Features

### Built-in Protections

1. **Path Validation**
   - Restricted directory access
   - Path traversal protection
   - File system boundary enforcement

2. **Command Validation**
   - Dangerous command blocking
   - Command timeout limits
   - Working directory restrictions

3. **API Security**
   - Input sanitization
   - Rate limiting (where applicable)
   - Authentication token validation

4. **Logging and Monitoring**
   - Comprehensive audit logs
   - Error tracking
   - Performance monitoring

### Configuration Security

1. **Environment Variables**
   - Sensitive data stored in environment variables
   - Template configuration for easy setup
   - Clear separation of secrets and code

2. **Access Control**
   - Configurable allowed paths
   - Restricted command execution
   - User permission validation

## Security Updates

### How We Handle Security Updates

1. **Critical Vulnerabilities**
   - Immediate patch release
   - Security advisory published
   - Users notified via GitHub releases

2. **High Priority Issues**
   - Patch within 7 days
   - Security advisory published
   - Regular updates provided

3. **Medium/Low Priority Issues**
   - Included in next regular release
   - Documented in changelog
   - Security notes in release

### Staying Informed

- **GitHub Releases**: Subscribe to repository notifications
- **Security Advisories**: Check the Security tab in GitHub
- **Dependencies**: Run `pip-audit` regularly

## Security Checklist

### Before Deployment

- [ ] All dependencies updated
- [ ] Environment variables configured securely
- [ ] File system permissions reviewed
- [ ] API keys rotated and secured
- [ ] Logging configured appropriately
- [ ] Security restrictions enabled
- [ ] Backup procedures in place

### Regular Maintenance

- [ ] Monthly dependency updates
- [ ] Quarterly security review
- [ ] Annual penetration testing (if applicable)
- [ ] Regular log analysis
- [ ] Access control review

## Contact Information

- **Security Email**: security@your-domain.com
- **General Issues**: Use GitHub Issues
- **Documentation**: Check project README and docs

## Acknowledgments

We appreciate the security researchers and community members who help keep this project secure. Responsible disclosure helps us maintain the security and integrity of our software.

---

**Remember**: Security is everyone's responsibility. If you see something, say something!
