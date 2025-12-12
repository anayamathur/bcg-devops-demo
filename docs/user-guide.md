# BCG DevOps + GenAI PoC - User Guide

## Overview

The BCG DevOps + GenAI platform is an AI-powered assistant that helps you manage CI/CD pipelines using natural language. You can chat with the agent to analyze repositories, generate workflows, fix failures, and deploy changes automatically.

---

## Getting Started

### Access Methods

1. **Web Interface**: Open the frontend in your browser
2. **API Direct**: Use curl or any HTTP client
3. **Slack Integration**: (Coming soon)

### Web Interface

1. Navigate to the frontend URL (local: http://localhost:8080)
2. Enter a repository in the format `owner/repo`
3. Type your request in natural language
4. The agent will respond with actions and results

---

## Common Tasks

### 1. Analyze a Repository

Ask the agent to understand your project:

```
"Analyze github.com/myorg/my-app"
```

The agent will detect:
- Programming language
- Framework (React, FastAPI, Spring, etc.)
- Package manager (npm, pip, maven, etc.)
- Docker configuration
- Kubernetes manifests
- Existing CI/CD workflows

### 2. Generate a CI/CD Pipeline

Request a new pipeline:

```
"Create a CI/CD pipeline for my Node.js project"
```

```
"Add GitHub Actions workflow with testing and Docker build"
```

```
"Setup deployment pipeline to EKS with security scanning"
```

### 3. Fix Failing Workflows

When your CI is broken:

```
"My CI is failing, can you fix it?"
```

```
"Analyze and fix the latest workflow failure"
```

The agent will:
1. Find the failed run
2. Analyze error logs
3. Generate a fix
4. Create a PR with the solution

### 4. Get Suggestions

Ask for improvements:

```
"How can I make my pipeline faster?"
```

```
"What security improvements should I add?"
```

### 5. Track Pipeline Status

Monitor your workflows:

```
"Show me recent workflow runs"
```

```
"What's the status of my CI/CD?"
```

---

## Autonomous Mode

### What is Autonomous Mode?

The autonomous agent can handle complex requests end-to-end without human intervention. It will:

1. Analyze your repository
2. Generate appropriate workflow
3. Create a PR
4. Monitor the pipeline run
5. Auto-fix if it fails
6. Retry up to 3 times
7. Report final status

### Using Autonomous Mode

**Via API:**

```bash
curl -X POST https://YOUR_API/prod/autonomous \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "owner/repo",
    "request": "Add complete CI/CD with testing, security scan, and deployment",
    "max_retries": 3,
    "auto_merge": false
  }'
```

**Via Chat:**

```
"Autonomously add a complete CI/CD pipeline with auto-fix enabled"
```

### Autonomous Request Examples

```
"Create and deploy a full CI/CD pipeline - fix any issues automatically"
```

```
"Setup GitHub Actions for my Python project, auto-fix if tests fail"
```

```
"Add Kubernetes deployment workflow and ensure it works"
```

---

## API Endpoints

### Quick Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Check API status |
| `/analyze` | POST | Analyze repository |
| `/generate` | POST | Generate workflow |
| `/create-pr` | POST | Create PR with workflow |
| `/track` | POST | Track Actions status |
| `/suggest` | POST | Get suggestions |
| `/fix` | POST | Auto-fix failures |
| `/validate` | POST | Validate workflow |
| `/knowledge` | POST | Build project knowledge |
| `/autonomous` | POST | Full autonomous agent |

### Request Format

All POST requests use JSON:

```json
{
  "repository": "owner/repo",
  "additional_params": "..."
}
```

### Response Format

```json
{
  "success": true,
  "repository": "owner/repo",
  "data": {...}
}
```

---

## Example Conversations

### Example 1: New Project Setup

**You:** I need a CI/CD pipeline for my Python FastAPI project at github.com/bcg/user-service. Include tests, security scanning, Docker build, and EKS deployment.

**Agent:** Analyzing github.com/bcg/user-service...

Detected:
- Python 3.11 with FastAPI
- Poetry for dependencies  
- Dockerfile present (multi-stage)
- Kubernetes manifests in /k8s
- Existing pytest configuration

Creating workflow with:
1. Lint & Format (ruff, black)
2. Unit Tests (pytest with coverage)
3. Security Scan (Trivy + SonarQube)
4. Build Docker image
5. Push to JFrog Artifactory
6. Deploy to EKS via ArgoCD

PR Created: https://github.com/bcg/user-service/pull/42

---

### Example 2: Fix Failing Pipeline

**You:** My CI is failing, can you fix it?

**Agent:** Analyzing recent workflow runs...

Found Failure:
- Run ID: #156
- Failed Step: "Install dependencies"
- Error: "npm ERR! ERESOLVE could not resolve"

Root Cause:
- Dependency conflict in package-lock.json

Fix Applied:
- Updated npm ci to npm ci --legacy-peer-deps
- Added Node.js version matrix for compatibility

PR Created: https://github.com/bcg/app/pull/157

Monitoring new run... SUCCESS!
All checks passed.

---

### Example 3: Get Optimization Suggestions

**You:** How can I make my pipeline faster?

**Agent:** Analyzing your current workflow...

Current build time: ~8 minutes

Suggestions:
1. **Add dependency caching** (Est. savings: 2 min)
   - Cache node_modules with actions/cache
   
2. **Parallelize test jobs** (Est. savings: 3 min)
   - Split tests into unit/integration/e2e
   
3. **Use matrix builds** (Est. savings: 1 min)
   - Run Node 18/20 tests in parallel

Estimated new build time: ~3 minutes

Would you like me to apply these optimizations?

---

## Best Practices

### Writing Good Requests

**Be Specific:**
- "Add CI for Python with pytest" 
- "Add CI for Node.js using npm with Jest tests"

**Include Context:**
- "My app deploys to AWS EKS"
- "We use JFrog for artifacts"

**State Requirements:**
- "Include security scanning with Trivy"
- "Add Slack notifications on failure"

### What to Avoid

- "Fix everything" (too vague)
- "Make it better" (no specific goal)
- "Deploy somewhere" (missing target)

---

## Understanding Results

### Workflow Validation

The agent validates workflows with a score:

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent - production ready |
| 70-89 | Good - minor improvements possible |
| 50-69 | Fair - needs attention |
| < 50 | Poor - significant issues |

### Validation Checks

- YAML syntax validity
- Action version pinning
- Security best practices
- Hardcoded secrets detection
- Permission scope analysis

---

## Troubleshooting

### Common Issues

**"Repository not found"**
- Verify repository name format: `owner/repo`
- Ensure GitHub token has access

**"Workflow generation failed"**
- Check if repository has supported files (package.json, etc.)
- Try being more specific about tech stack

**"Auto-fix failed"**
- Some failures need manual intervention
- Check the failure logs for details

**"Timeout during autonomous run"**
- Complex pipelines may take longer
- Check GitHub Actions is running

### Getting Help

1. Check error message details
2. Review CloudWatch logs
3. Contact DevOps team

---

## Security Notes

### What the Agent Can Access

- Public repository content
- Repository metadata
- GitHub Actions logs
- Workflow files

### What the Agent Cannot Access

- Private code without token
- Secrets values
- Production systems directly
- Database content

### Best Practices

1. Use repository-scoped tokens
2. Review PRs before merging
3. Enable branch protection
4. Keep auto_merge disabled for production

---

## FAQ

**Q: Can the agent break my production?**
A: No. The agent only creates PRs. You must approve and merge changes.

**Q: How does auto-fix work?**
A: The agent analyzes failure logs, identifies issues, and generates fixes using AI.

**Q: What languages are supported?**
A: Python, Node.js, Go, Java, and more. Any language with common build tools.

**Q: Can I customize generated workflows?**
A: Yes. Edit the workflow after generation or provide specific requirements.

**Q: Is my code sent to external services?**
A: Code analysis happens via GitHub API. AI processing uses AWS Bedrock (within AWS).

---

*Last Updated: December 2024*
