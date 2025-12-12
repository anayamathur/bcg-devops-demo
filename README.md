# BCG DevOps + GenAI Agentic Solution

<p align="center">
  <img src="https://img.shields.io/badge/AWS-Bedrock-orange?style=for-the-badge&logo=amazon-aws" />
  <img src="https://img.shields.io/badge/AI-Nova%20Pro-blue?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Status-Production%20Ready-green?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Version-2.0-purple?style=for-the-badge" />
</p>

## Executive Summary

This POC demonstrates an **Agentic AI-powered DevOps platform** built on AWS Bedrock that enables:

| Capability | Description |
|------------|-------------|
| **Conversational DevOps** | Chat-based interface for all DevOps operations |
| **Intelligent Template Generation** | Auto-generate CI/CD workflows for any tech stack |
| **Autonomous Agent** | Self-healing CI/CD - auto-fix failures, retry, and deploy |
| **Security-First Approach** | AI-powered security gatekeeper for all changes |
| **Full Repository Awareness** | Agents understand complete codebase context |
| **Incident Response** | L1 auto-remediation, L2/L3 human-in-loop |

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Key Features](#key-features)
3. [Live Demo](#live-demo)
4. [API Reference](#api-reference)
5. [Autonomous Agent](#autonomous-agent)
6. [Incident Response Agent](#incident-response-agent)
7. [Multi-Agent Coordination](#multi-agent-coordination)
8. [Security Analysis](#security-analysis)
9. [Quick Start](#quick-start)
10. [Integration Guide](#integration-guide)
11. [Security Policies](#security-policies)
12. [Sample Conversations](#sample-conversations)
13. [Cost Estimation](#cost-estimation)
14. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
+------------------+     +-------------------+     +------------------+
|                  |     |                   |     |                  |
|  Chat Interface  |---->|   API Gateway     |---->|  Lambda Function |
|  (Web/Slack)     |     |   (REST API)      |     |  (Python 3.12)   |
|                  |     |                   |     |                  |
+------------------+     +-------------------+     +--------+---------+
                                                           |
                              +----------------------------+
                              |
              +---------------+---------------+---------------+
              |               |               |               |
              v               v               v               v
      +-------+-----+ +-------+-----+ +-------+-----+ +-------+-----+
      |             | |             | |             | |             |
      |  Bedrock    | |  GitHub     | |  Secrets    | | CloudWatch  |
      |  Nova Pro   | |  API        | |  Manager    | | Logs        |
      |  (AI)       | |  (Repos)    | |  (Tokens)   | | (Monitor)   |
      |             | |             | |             | |             |
      +-------------+ +-------------+ +-------------+ +-------------+
```

### Core Components

| Component | AWS Service | Purpose |
|-----------|-------------|---------|
| **DevOps Agent** | Lambda + Bedrock | Main orchestrator for CI/CD operations |
| **AI Engine** | Bedrock Nova Pro | Natural language processing and generation |
| **API Layer** | API Gateway | REST endpoints for all operations |
| **Repository Integration** | GitHub API | Clone, commit, PR, Actions tracking |
| **Secrets Management** | Secrets Manager | Secure credential storage |
| **Monitoring** | CloudWatch | Logs and metrics |

---

## Key Features

### 1. Autonomous DevOps Agent

The crown jewel - a fully autonomous agent that:

```
User Request: "Add CI/CD pipeline for my Node.js project"
         |
         v
+------------------+
|  1. ANALYZE      |  <- Scans repo: package.json, Dockerfile, etc.
+------------------+
         |
         v
+------------------+
|  2. UNDERSTAND   |  <- AI interprets request, plans action
+------------------+
         |
         v
+------------------+
|  3. GENERATE     |  <- Creates optimized workflow YAML
+------------------+
         |
         v
+------------------+
|  4. DEPLOY       |  <- Creates branch, commits, opens PR
+------------------+
         |
         v
+------------------+
|  5. MONITOR      |  <- Watches GitHub Actions run
+------------------+
         |
    PASS?  FAIL?
      |      |
      v      v
  +-----+  +------------------+
  | END |  |  6. AUTO-FIX     |  <- Analyzes failure, generates fix
  +-----+  +------------------+
                  |
                  v
           +------------------+
           |  7. RETRY        |  <- Up to 3 attempts
           +------------------+
```

### 2. Dynamic Chat Agent

```
Developer: "Setup CI/CD for my new Golang microservice"

Agent: "I'll analyze your repository and create a GitHub Actions workflow..."
       
       Detected:
       - Go 1.21, uses gin-gonic, PostgreSQL
       - Dockerfile present (multi-stage build)
       
       Creating workflow with:
       - Build & test stages
       - Security scan (Trivy)
       - Docker image build
       - Deployment to EKS
       
       Shall I commit this to .github/workflows/ci.yml?
```

### 3. Intelligent Template Generation

- **Auto-detects**: Language, framework, package manager
- **Generates**: Optimized CI/CD workflows with caching
- **Validates**: Security best practices enforcement
- **Integrates**: BCG-approved tools (SonarQube, JFrog, Prisma)

### 4. Complete Repository Understanding

The agent analyzes:
- `package.json`, `go.mod`, `requirements.txt`, `pom.xml`
- `Dockerfile`, `docker-compose.yml`
- `k8s/`, `kubernetes/`, `manifests/` directories
- Existing `.github/workflows/` files
- Recent Actions run history and failures

### 5. Self-Healing CI/CD

When workflows fail, the agent:
1. Fetches failure logs from GitHub Actions
2. Identifies failed steps and jobs
3. Generates intelligent fixes using AI
4. Commits fix and retries automatically
5. Reports final status

---

## Live Demo

### Deployed Infrastructure

The platform is currently deployed and live in AWS:

| Component | Details |
|-----------|---------|
| **API Endpoint** | `https://4dyb4z9kgk.execute-api.us-east-1.amazonaws.com/prod` |
| **AI Model** | Amazon Bedrock Nova Pro (`amazon.nova-pro-v1:0`) |
| **Region** | `us-east-1` |
| **Lambda Timeout** | 300 seconds (for autonomous operations) |

### Frontend

```bash
# Start local frontend
cd bcg-devops-genai-poc/frontend
python3 -m http.server 8080
# Open http://localhost:8080
```

---

## API Reference

### Base URL
```
https://4dyb4z9kgk.execute-api.us-east-1.amazonaws.com/prod
```

### Endpoints

#### 1. Health Check
```bash
GET /health
```
Response:
```json
{
  "status": "healthy",
  "model": "amazon.nova-pro-v1:0"
}
```

#### 2. Analyze Repository
```bash
POST /analyze
Content-Type: application/json

{
  "repository": "owner/repo"
}
```
Response:
```json
{
  "owner": "owner",
  "repo": "repo",
  "primary_language": "JavaScript",
  "tech_stack": ["Node.js", "Docker"],
  "has_dockerfile": true,
  "has_kubernetes": false,
  "has_workflows": true,
  "package_manager": "npm",
  "framework": "React"
}
```

#### 3. Generate Workflow
```bash
POST /generate
Content-Type: application/json

{
  "repository": "owner/repo"
}
```
Response:
```json
{
  "repository": "owner/repo",
  "workflow_content": "name: CI\non: push...",
  "validation": {
    "valid": true,
    "score": 95
  }
}
```

#### 4. Create PR with Workflow
```bash
POST /create-pr
Content-Type: application/json

{
  "repository": "owner/repo",
  "workflow_content": "name: CI\non: push...",
  "workflow_name": "ci.yml"
}
```
Response:
```json
{
  "success": true,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_number": 123,
  "branch": "feature/add-ci-workflow"
}
```

#### 5. Track Actions Status
```bash
POST /track
Content-Type: application/json

{
  "repository": "owner/repo"
}
```
Response:
```json
{
  "repository": "owner/repo",
  "total_runs": 10,
  "summary": {
    "success_count": 8,
    "failed_count": 2,
    "success_rate": "80.0%"
  },
  "runs": [...]
}
```

#### 6. Get Intelligent Suggestions
```bash
POST /suggest
Content-Type: application/json

{
  "repository": "owner/repo"
}
```
Response:
```json
{
  "repository": "owner/repo",
  "auto_suggestions": [...],
  "ai_suggestions": [
    {
      "priority": "high",
      "title": "Add caching",
      "description": "Speed up builds by 60%"
    }
  ]
}
```

#### 7. Auto-Fix Failures
```bash
POST /fix
Content-Type: application/json

{
  "repository": "owner/repo",
  "auto_commit": true
}
```
Response:
```json
{
  "repository": "owner/repo",
  "analyzed_run": {...},
  "fixed_workflow": "...",
  "committed": true,
  "pr_url": "https://github.com/owner/repo/pull/124"
}
```

#### 8. Validate Workflow
```bash
POST /validate
Content-Type: application/json

{
  "workflow_content": "name: CI\non: push..."
}
```
Response:
```json
{
  "valid": true,
  "score": 95,
  "issues": [],
  "warnings": ["Consider adding dependency caching"],
  "recommendations": [...]
}
```

#### 9. Build Project Knowledge
```bash
POST /knowledge
Content-Type: application/json

{
  "repository": "owner/repo"
}
```
Response:
```json
{
  "repository": "owner/repo",
  "tech_stack": ["Node.js", "React", "Docker"],
  "framework": "React",
  "dependencies": {...},
  "workflows": [...],
  "devops_status": {
    "has_failures": false,
    "recent_runs": [...]
  },
  "suggestions": [...]
}
```

---

## Autonomous Agent

### The `/autonomous` Endpoint

This is the most powerful endpoint - a fully autonomous DevOps agent.

```bash
POST /autonomous
Content-Type: application/json

{
  "repository": "owner/repo",
  "request": "Add a complete CI/CD pipeline with testing, security scanning, and deployment to AWS",
  "max_retries": 3,
  "auto_merge": false
}
```

### How It Works

```
Step 1: ANALYZE
├── Clones repository (virtual)
├── Detects tech stack
├── Reads package.json, Dockerfile, etc.
└── Builds comprehensive project knowledge

Step 2: UNDERSTAND REQUEST
├── AI processes natural language request
├── Determines action type (create/fix/improve)
└── Plans implementation strategy

Step 3: GENERATE WORKFLOW
├── Creates optimized GitHub Actions YAML
├── Applies best practices
├── Validates syntax and security
└── Includes BCG-approved integrations

Step 4: DEPLOY
├── Creates feature branch
├── Commits workflow file
├── Opens Pull Request
└── Links to monitoring

Step 5: MONITOR
├── Waits for GitHub Actions to trigger
├── Polls run status every 15 seconds
├── Timeout after 5 minutes
└── Captures detailed job/step status

Step 6: EVALUATE
├── If SUCCESS → Report and optionally auto-merge
├── If FAILURE → Proceed to auto-fix
└── If TIMEOUT → Report partial status

Step 7: AUTO-FIX (if failed)
├── Analyzes failure logs
├── Identifies failed steps
├── Generates AI-powered fix
└── Creates new commit

Step 8: RETRY
├── Up to max_retries attempts
├── Each retry uses improved workflow
└── Final status reported
```

### Response Structure

```json
{
  "success": true,
  "repository": "owner/repo",
  "request": "Add CI/CD pipeline",
  "execution_log": [
    {
      "timestamp": "2024-12-10T10:00:00",
      "step": "analyze",
      "status": "completed",
      "details": {...}
    },
    {
      "timestamp": "2024-12-10T10:00:05",
      "step": "generate_workflow",
      "status": "completed",
      "details": {...}
    }
  ],
  "final_status": "success",
  "pr_url": "https://github.com/owner/repo/pull/123",
  "workflow_file": ".github/workflows/ci-cd-autonomous.yml",
  "attempts": 1,
  "duration_seconds": 120.5
}
```

---

## Incident Response Agent

### The `/incident` Endpoint

Intelligent incident response with L1/L2/L3 escalation system.

```bash
POST /incident
Content-Type: application/json

{
  "repository": "owner/repo",
  "incident_description": "CI pipeline failing with npm install error on main branch",
  "auto_remediate": true
}
```

### Escalation Levels

```
┌─────────────────────────────────────────────────────────────────┐
│                    INCIDENT RESPONSE FLOW                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Incident Detected                                               │
│        │                                                         │
│        ▼                                                         │
│  ┌─────────────┐                                                 │
│  │  CLASSIFY   │  ← Pattern matching + AI analysis               │
│  └─────────────┘                                                 │
│        │                                                         │
│        ├──────────────────┬──────────────────┐                   │
│        ▼                  ▼                  ▼                   │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐            │
│  │  L1: AUTO   │   │  L2: HUMAN  │   │ L3: CRITICAL│            │
│  │  REMEDIATE  │   │  IN LOOP    │   │  ESCALATION │            │
│  └─────────────┘   └─────────────┘   └─────────────┘            │
│        │                  │                  │                   │
│        ▼                  ▼                  ▼                   │
│  • Retry jobs       • Create issue    • PagerDuty alert         │
│  • Clear cache      • AI suggestions  • Security team           │
│  • Restart workflow • Notify team     • Management notify       │
│  • Scale resources  • Document fix    • Incident bridge         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### L1 Auto-Remediation Actions

| Incident Type | Auto-Fix Action |
|---------------|-----------------|
| Build failures | Retry failed jobs, clear cache |
| Test failures | Retry with extended timeout |
| Deployment errors | Rollback to previous version |
| Rate limiting | Wait and retry with backoff |
| Resource issues | Scale up resources |

### Response Structure

```json
{
  "success": true,
  "repository": "owner/repo",
  "incident": {
    "description": "CI pipeline failing...",
    "classification": {
      "level": "L1",
      "category": "build_failure",
      "confidence": 0.95
    }
  },
  "remediation": {
    "attempted": true,
    "action": "retry_failed_jobs",
    "result": "success"
  },
  "execution_log": [...],
  "duration_seconds": 45.2
}
```

---

## Multi-Agent Coordination

### The `/multi-agent` Endpoint

Orchestrates multiple specialized agents for complex tasks.

```bash
POST /multi-agent
Content-Type: application/json

{
  "repository": "owner/repo",
  "task": "Perform complete security audit, fix any issues, and add CI/CD pipeline",
  "agent_sequence": ["security_agent", "workflow_agent", "incident_agent"]
}
```

### Available Agent Types

| Agent | Purpose |
|-------|---------|
| `workflow_agent` | CI/CD workflow creation and optimization |
| `security_agent` | Security scanning and vulnerability fixes |
| `incident_agent` | Incident response and auto-remediation |
| `analysis_agent` | Repository analysis and recommendations |

### How Multi-Agent Works

```
┌────────────────────────────────────────────────────────────────┐
│                  MULTI-AGENT COORDINATION                       │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Complex Task                                                   │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐                                                │
│  │ AI PLANNER  │  ← Analyzes task, determines agent sequence    │
│  └─────────────┘                                                │
│       │                                                         │
│       ▼                                                         │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │  AGENT 1    │ → │  AGENT 2    │ → │  AGENT 3    │           │
│  │  Security   │   │  Workflow   │   │  Incident   │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│       │                  │                  │                   │
│       └──────────────────┴──────────────────┘                   │
│                          │                                      │
│                          ▼                                      │
│                   ┌─────────────┐                               │
│                   │   SUMMARY   │  ← Combined results           │
│                   └─────────────┘                               │
│                                                                 │
└────────────────────────────────────────────────────────────────┘
```

### Response Structure

```json
{
  "success": true,
  "repository": "owner/repo",
  "task": "Perform complete security audit...",
  "agents_executed": ["security_agent", "workflow_agent", "incident_agent"],
  "agent_results": {
    "security_agent": {
      "findings": [...],
      "fixes_applied": 3
    },
    "workflow_agent": {
      "workflow_created": true,
      "pr_url": "..."
    },
    "incident_agent": {
      "issues_detected": 0
    }
  },
  "summary": "Completed security audit with 3 fixes, created CI/CD pipeline, no incidents detected",
  "execution_log": [...],
  "duration_seconds": 180.5
}
```

---

## Security Analysis

### The `/security` Endpoint

Dedicated security scanning and analysis endpoint.

```bash
POST /security
Content-Type: application/json

{
  "repository": "owner/repo"
}
```

### Security Checks Performed

| Check | Description |
|-------|-------------|
| **Secrets Detection** | Scans for exposed API keys, tokens, passwords |
| **Dependency Audit** | Checks for vulnerable dependencies |
| **Workflow Security** | Validates GitHub Actions security best practices |
| **Configuration Files** | Checks for security misconfigurations |
| **Access Controls** | Reviews repository permission settings |

### Response Structure

```json
{
  "findings": [
    {
      "severity": "high",
      "issue": "Exposed AWS credentials in config file",
      "file": "src/config.js",
      "line": 15,
      "recommendation": "Move to environment variables or AWS Secrets Manager"
    }
  ],
  "risk_level": "high",
  "recommendations": [
    "Enable branch protection on main",
    "Add CODEOWNERS file",
    "Enable secret scanning"
  ],
  "scan_completed": true,
  "files_scanned": 142
}
```

---

## Quick Start

### Prerequisites

- AWS Account with Bedrock access (Nova Pro enabled)
- Terraform >= 1.5.0
- AWS CLI configured
- GitHub Personal Access Token

### Deployment

```bash
# Clone repository
git clone https://github.com/your-org/bcg-devops-genai-poc.git
cd bcg-devops-genai-poc

# Deploy infrastructure
cd infrastructure/terraform
terraform init
terraform plan -var="aws_region=us-east-1"
terraform apply

# Note the API Gateway URL from outputs
```

### Configure GitHub Token

```bash
# Store GitHub token in Secrets Manager
aws secretsmanager put-secret-value \
  --secret-id bcg-devops-genai/github-token \
  --secret-string '{"token": "ghp_YOUR_TOKEN_HERE"}' \
  --region us-east-1
```

### Test the API

```bash
# Health check
curl https://YOUR_API_GATEWAY_URL/prod/health

# Analyze a repository
curl -X POST https://YOUR_API_GATEWAY_URL/prod/analyze \
  -H "Content-Type: application/json" \
  -d '{"repository": "facebook/react"}'

# Run autonomous agent
curl -X POST https://YOUR_API_GATEWAY_URL/prod/autonomous \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "your-org/your-repo",
    "request": "Add CI/CD pipeline with tests and deployment"
  }'
```

---

## Integration Guide

### BCG Standard Tools Integration

| Tool | Integration Method | Workflow Example |
|------|-------------------|------------------|
| **SonarQube** | `sonarqube-scan-action` | Code quality gates |
| **JFrog Artifactory** | `jfrog/setup-jfrog-cli` | Artifact storage |
| **Prisma Cloud** | `prisma-cloud-scan` | Security scanning |
| **Trivy** | `aquasecurity/trivy-action` | Container scanning |
| **ArgoCD** | `argocd-sync` | GitOps deployment |
| **Datadog** | `datadog-agent` | Monitoring |
| **Slack** | `slack-notify` | Notifications |

### Example: Full BCG Pipeline

```yaml
name: BCG Standard Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Run tests
        run: npm test -- --coverage
      
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@v2
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Trivy Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
      
      - name: Prisma Cloud Scan
        uses: prisma-cloud/scan-action@v1
        with:
          prisma_cloud_access_key: ${{ secrets.PRISMA_ACCESS_KEY }}

  deploy:
    needs: [build-test, security-scan]
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Deploy via ArgoCD
        run: |
          argocd app sync ${{ env.APP_NAME }}
      
      - name: Notify Slack
        uses: slackapi/slack-github-action@v1
        with:
          channel-id: 'deployments'
          slack-message: 'Deployed ${{ github.sha }} to production'
```

---

## Security Policies

### Workflow Security Requirements

| Category | Requirement |
|----------|-------------|
| **Secrets** | Use `${{ secrets.NAME }}` - no hardcoded values |
| **Action Versions** | Pin to specific versions (`@v4`, not `@main`) |
| **Permissions** | Use least privilege principle |
| **Scanning** | Required for all workflows |
| **Production Deploy** | Requires manual approval |

### Forbidden Patterns

```yaml
# FORBIDDEN - Never do these:
password: "my-secret-password"      # Hardcoded secret
uses: actions/checkout@main          # Unpinned version
permissions: write-all               # Overly permissive
```

### Required Security Checks

- [ ] All tests pass
- [ ] Code coverage >= 80%
- [ ] Security scan passes (no HIGH/CRITICAL)
- [ ] SonarQube quality gate passes
- [ ] Peer review approved

---

## Sample Conversations

### Example 1: New Project Setup

```
User: I need a CI/CD pipeline for my Python FastAPI project at 
      github.com/bcg/user-service. Include tests, security scanning,
      Docker build, and EKS deployment.

Agent: Analyzing github.com/bcg/user-service...

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

       The workflow includes:
       - Dependency caching for 60% faster builds
       - Parallel test execution
       - Slack notifications on failure
       - Auto-rollback on deployment failure
```

### Example 2: Fix Failing Pipeline

```
User: My CI is failing, can you fix it?

Agent: Analyzing recent workflow runs...

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
```

---

## Cost Estimation

### Monthly Estimate (Production)

| Service | Usage | Estimated Cost |
|---------|-------|----------------|
| Bedrock (Nova Pro) | 1M input + 500K output tokens | $18.00 |
| Lambda | 1M invocations, 512MB | $15.00 |
| API Gateway | 1M requests | $3.50 |
| Secrets Manager | 5 secrets | $2.00 |
| CloudWatch | Logs + Metrics | $30.00 |
| **Total** | | **~$70/month** |

*Note: Costs scale with usage. Enterprise deployments with OpenSearch may be higher.*

---

## Troubleshooting

### Common Issues

#### 1. GitHub Token Not Working
```bash
# Verify token in Secrets Manager
aws secretsmanager get-secret-value \
  --secret-id bcg-devops-genai/github-token \
  --region us-east-1

# Token needs these scopes:
# - repo (full control)
# - workflow (Actions access)
```

#### 2. Bedrock Model Access
```bash
# Check model access in Bedrock console
# Ensure Nova Pro is enabled in us-east-1

# Test model access
aws bedrock-runtime invoke-model \
  --model-id amazon.nova-pro-v1:0 \
  --body '{"messages":[{"role":"user","content":[{"text":"Hello"}]}]}' \
  --region us-east-1 \
  output.json
```

#### 3. Lambda Timeout
```bash
# Increase timeout for autonomous operations
aws lambda update-function-configuration \
  --function-name bcg-github-integration \
  --timeout 300
```

#### 4. Workflow Not Triggering
- Check if `.github/workflows/` directory exists
- Verify workflow YAML syntax
- Check GitHub Actions is enabled for repo

---

## Project Structure

```
bcg-devops-genai-poc/
├── README.md                          # This file
├── agents/
│   └── devops-agent/
│       ├── agent-instructions.txt     # Agent behavior config
│       └── openapi-schema.json        # API schema for Bedrock
├── frontend/
│   └── index.html                     # Web chat interface
├── infrastructure/
│   └── terraform/
│       ├── main.tf                    # Main infrastructure
│       └── variables.tf               # Configuration
├── lambda/
│   ├── github-integration/
│   │   └── index.py                   # Main Lambda (1600+ lines)
│   ├── security-scanner/
│   │   └── index.py                   # Security validation
│   └── workflow-generator/
│       └── index.py                   # Template generation
├── templates/
│   ├── github-actions/
│   │   ├── golang.yml
│   │   ├── nodejs.yml
│   │   └── python.yml
│   └── policies/
│       └── security-policy.md         # BCG security rules
└── docs/
    ├── deployment-guide.md
    ├── user-guide.md
    └── api-reference.md
```

---

## Support

For questions or issues, contact the i2k2 team:

| Role | Contact |
|------|---------|
| Architecture | i2k2 Networks |
| Implementation | DevOps Team |
| AWS Support | AWS SA |

---

## Changelog

### v2.0.0 (December 2024)
- Added fully autonomous `/autonomous` endpoint
- Self-healing CI/CD with auto-fix and retry
- Comprehensive project knowledge building
- Enhanced AI-powered suggestions
- Detailed execution logging

### v1.0.0 (November 2024)
- Initial release
- Basic workflow generation
- Repository analysis
- PR creation

---

*Last Updated: December 2024*
*Built with AWS Bedrock Nova Pro*
