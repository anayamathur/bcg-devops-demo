# BCG Agentic DevOps Platform

🤖 **Intelligent DevOps Automation** powered by AWS Bedrock Nova Pro

## Overview

This is a fully agentic DevOps platform that automates CI/CD workflow generation, security scanning, and incident response using AI.

## Features

- **Workflow Generator Agent**: Auto-generate BCG-compliant CI/CD pipelines
- **Security Agent**: Scan for vulnerabilities and create fix PRs
- **Incident Agent**: L1 triage automation and RCA generation
- **Natural Language Interface**: Talk to agents in plain English

## Quick Start

### Backend

```bash
cd bcg-devops-genai-poc
source venv/bin/activate
export GITHUB_TOKEN="your_token"
export AWS_PROFILE=credit
python server.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Access

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

## BCG Tool Integrations

- ✅ GitHub Actions
- ✅ JFrog Artifactory
- ✅ SonarQube
- ✅ Prisma Cloud
- ✅ ArgoCD
- ✅ Datadog

## License

Proprietary - BCG
