# BCG DevOps + GenAI PoC - API Reference

## Base URL

```
https://4dyb4z9kgk.execute-api.us-east-1.amazonaws.com/prod
```

## Authentication

Currently, the API does not require authentication. For production, implement API keys or IAM authentication.

---

## Endpoints

### 1. Health Check

Check API and AI model status.

**Request:**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "model": "amazon.nova-pro-v1:0"
}
```

---

### 2. Analyze Repository

Analyze a GitHub repository to detect tech stack, frameworks, and configuration.

**Request:**
```http
POST /analyze
Content-Type: application/json

{
  "repository": "owner/repo"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| repository | string | Yes | GitHub repository (owner/repo format) |

**Response:**
```json
{
  "owner": "facebook",
  "repo": "react",
  "primary_language": "JavaScript",
  "tech_stack": ["Node.js", "React", "Jest"],
  "has_dockerfile": true,
  "has_kubernetes": false,
  "has_workflows": true,
  "package_manager": "yarn",
  "framework": "React",
  "existing_workflows": ["ci.yml", "release.yml"]
}
```

---

### 3. Generate Workflow

Generate an optimized CI/CD workflow for a repository.

**Request:**
```http
POST /generate
Content-Type: application/json

{
  "repository": "owner/repo"
}
```

**Response:**
```json
{
  "repository": "owner/repo",
  "workflow_content": "name: CI\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      ...",
  "validation": {
    "valid": true,
    "score": 95,
    "issues": [],
    "warnings": ["Consider adding dependency caching"]
  }
}
```

---

### 4. Create Pull Request

Create a PR with a workflow file.

**Request:**
```http
POST /create-pr
Content-Type: application/json

{
  "repository": "owner/repo",
  "workflow_content": "name: CI\non: push...",
  "workflow_name": "ci.yml",
  "branch_name": "feature/add-ci",
  "pr_title": "Add CI workflow",
  "pr_body": "This PR adds a CI workflow"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| repository | string | Yes | GitHub repository |
| workflow_content | string | Yes | YAML workflow content |
| workflow_name | string | No | Filename (default: ci.yml) |
| branch_name | string | No | Branch name (auto-generated if not provided) |
| pr_title | string | No | PR title |
| pr_body | string | No | PR description |

**Response:**
```json
{
  "success": true,
  "pr_url": "https://github.com/owner/repo/pull/123",
  "pr_number": 123,
  "branch": "feature/add-ci-workflow-abc123"
}
```

---

### 5. Track Actions Status

Get status of GitHub Actions workflow runs.

**Request:**
```http
POST /track
Content-Type: application/json

{
  "repository": "owner/repo",
  "limit": 10
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| repository | string | Yes | GitHub repository |
| limit | integer | No | Number of runs to fetch (default: 10) |

**Response:**
```json
{
  "repository": "owner/repo",
  "total_runs": 50,
  "summary": {
    "success_count": 45,
    "failed_count": 5,
    "success_rate": "90.0%"
  },
  "runs": [
    {
      "id": 12345,
      "name": "CI",
      "status": "completed",
      "conclusion": "success",
      "created_at": "2024-12-10T10:00:00Z",
      "run_url": "https://github.com/owner/repo/actions/runs/12345"
    }
  ]
}
```

---

### 6. Get Suggestions

Get AI-powered improvement suggestions.

**Request:**
```http
POST /suggest
Content-Type: application/json

{
  "repository": "owner/repo"
}
```

**Response:**
```json
{
  "repository": "owner/repo",
  "auto_suggestions": [
    {
      "type": "caching",
      "title": "Add dependency caching",
      "description": "Cache npm dependencies to speed up builds"
    }
  ],
  "ai_suggestions": [
    {
      "priority": "high",
      "title": "Add security scanning",
      "description": "Include Trivy for container vulnerability scanning",
      "estimated_impact": "Improved security posture"
    },
    {
      "priority": "medium",
      "title": "Parallelize tests",
      "description": "Split test suite into parallel jobs",
      "estimated_impact": "50% faster builds"
    }
  ]
}
```

---

### 7. Auto-Fix Failures

Analyze and fix failing workflows.

**Request:**
```http
POST /fix
Content-Type: application/json

{
  "repository": "owner/repo",
  "run_id": 12345,
  "auto_commit": true
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| repository | string | Yes | GitHub repository |
| run_id | integer | No | Specific run to fix (latest if not provided) |
| auto_commit | boolean | No | Create PR with fix (default: false) |

**Response:**
```json
{
  "repository": "owner/repo",
  "analyzed_run": {
    "id": 12345,
    "conclusion": "failure",
    "failed_jobs": ["build"],
    "error_message": "npm ERR! ERESOLVE could not resolve"
  },
  "root_cause": "Dependency resolution conflict in package-lock.json",
  "fixed_workflow": "name: CI\non: push...",
  "committed": true,
  "pr_url": "https://github.com/owner/repo/pull/124"
}
```

---

### 8. Validate Workflow

Validate workflow YAML content.

**Request:**
```http
POST /validate
Content-Type: application/json

{
  "workflow_content": "name: CI\non: push..."
}
```

**Response:**
```json
{
  "valid": true,
  "score": 95,
  "issues": [],
  "warnings": [
    "Consider adding dependency caching for faster builds"
  ],
  "recommendations": [
    {
      "category": "security",
      "message": "Pin action versions to specific SHA or tag"
    }
  ]
}
```

**Score Interpretation:**

| Score | Meaning |
|-------|---------|
| 90-100 | Excellent - production ready |
| 70-89 | Good - minor improvements possible |
| 50-69 | Fair - needs attention |
| < 50 | Poor - significant issues |

---

### 9. Security Scan

Perform security analysis on a GitHub repository, scanning for vulnerabilities, misconfigurations, and security issues.

**Request:**
```http
POST /scan
Content-Type: application/json

{
  "repository": "owner/repo",
  "scan_type": "full"
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| repository | string | Yes | GitHub repository (owner/repo format) |
| scan_type | string | No | Type of scan: "full", "quick", "deep" (default: "full") |

**Response:**
```json
{
  "success": true,
  "repository": "owner/repo",
  "scan_type": "full",
  "scan_results": {
    "summary": {
      "critical": 2,
      "high": 5,
      "medium": 12,
      "low": 8,
      "info": 15
    },
    "findings": [
      {
        "severity": "critical",
        "category": "secrets",
        "title": "Hardcoded API key detected",
        "file": "src/config.js",
        "line": 42,
        "description": "API key found in source code",
        "recommendation": "Use environment variables or a secrets manager"
      },
      {
        "severity": "high",
        "category": "dependencies",
        "title": "Vulnerable dependency",
        "package": "lodash@4.17.15",
        "cve": "CVE-2021-23337",
        "recommendation": "Upgrade to lodash@4.17.21 or later"
      }
    ],
    "categories_scanned": [
      "secrets",
      "dependencies",
      "dockerfile",
      "iac",
      "code_quality"
    ]
  },
  "recommendations": [
    {
      "priority": "critical",
      "action": "Remove hardcoded secrets and use environment variables",
      "impact": "Prevents credential exposure"
    },
    {
      "priority": "high",
      "action": "Update vulnerable dependencies",
      "impact": "Addresses known security vulnerabilities"
    }
  ],
  "score": 65,
  "grade": "C"
}
```

**Security Grade Scale:**

| Grade | Score | Meaning |
|-------|-------|---------|
| A | 90-100 | Excellent security posture |
| B | 80-89 | Good with minor issues |
| C | 70-79 | Fair - needs improvement |
| D | 60-69 | Poor - significant issues |
| F | < 60 | Critical - immediate action required |

---

### 10. Build Knowledge

Build comprehensive project knowledge.

**Request:**
```http
POST /knowledge
Content-Type: application/json

{
  "repository": "owner/repo"
}
```

**Response:**
```json
{
  "repository": "owner/repo",
  "tech_stack": ["Node.js", "React", "Docker", "Kubernetes"],
  "framework": "React",
  "package_manager": "npm",
  "dependencies": {
    "production": ["react", "react-dom", "express"],
    "development": ["jest", "eslint", "prettier"]
  },
  "structure": {
    "has_dockerfile": true,
    "has_kubernetes": true,
    "has_workflows": true,
    "has_tests": true
  },
  "workflows": [
    {
      "name": "ci.yml",
      "triggers": ["push", "pull_request"],
      "jobs": ["build", "test", "deploy"]
    }
  ],
  "devops_status": {
    "has_failures": false,
    "recent_runs": [...],
    "success_rate": "95%"
  },
  "suggestions": [...]
}
```

---

### 11. Autonomous Agent

Run fully autonomous DevOps agent.

**Request:**
```http
POST /autonomous
Content-Type: application/json

{
  "repository": "owner/repo",
  "request": "Add CI/CD pipeline with testing and deployment",
  "max_retries": 3,
  "auto_merge": false
}
```

**Parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| repository | string | Yes | GitHub repository |
| request | string | Yes | Natural language request |
| max_retries | integer | No | Max fix attempts (default: 3) |
| auto_merge | boolean | No | Auto-merge PR if successful (default: false) |

**Response:**
```json
{
  "success": true,
  "repository": "owner/repo",
  "request": "Add CI/CD pipeline",
  "execution_log": [
    {
      "timestamp": "2024-12-10T10:00:00Z",
      "step": "analyze",
      "status": "completed",
      "details": {
        "tech_stack": ["Node.js", "React"],
        "framework": "React"
      }
    },
    {
      "timestamp": "2024-12-10T10:00:05Z",
      "step": "generate_workflow",
      "status": "completed",
      "details": {
        "workflow_name": "ci-cd-autonomous.yml"
      }
    },
    {
      "timestamp": "2024-12-10T10:00:10Z",
      "step": "create_pr",
      "status": "completed",
      "details": {
        "pr_number": 123,
        "pr_url": "https://github.com/owner/repo/pull/123"
      }
    },
    {
      "timestamp": "2024-12-10T10:02:00Z",
      "step": "monitor",
      "status": "completed",
      "details": {
        "run_status": "success"
      }
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

## Error Responses

All errors follow this format:

```json
{
  "error": true,
  "message": "Error description",
  "code": "ERROR_CODE"
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `REPOSITORY_NOT_FOUND` | Repository doesn't exist or no access |
| `INVALID_REQUEST` | Missing or invalid parameters |
| `GITHUB_API_ERROR` | GitHub API failure |
| `BEDROCK_ERROR` | AI model error |
| `VALIDATION_FAILED` | Workflow validation failed |
| `TIMEOUT` | Operation timed out |

---

## Rate Limits

| Service | Limit |
|---------|-------|
| API Gateway | 10,000 requests/second |
| Lambda | 1,000 concurrent executions |
| Bedrock | Model-dependent |
| GitHub API | 5,000 requests/hour |

---

## Examples

### cURL

```bash
# Health check
curl https://API_URL/prod/health

# Analyze repository
curl -X POST https://API_URL/prod/analyze \
  -H "Content-Type: application/json" \
  -d '{"repository": "facebook/react"}'

# Run autonomous agent
curl -X POST https://API_URL/prod/autonomous \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "myorg/myapp",
    "request": "Add CI/CD pipeline with tests"
  }'
```

### Python

```python
import requests

API_URL = "https://4dyb4z9kgk.execute-api.us-east-1.amazonaws.com/prod"

# Analyze repository
response = requests.post(
    f"{API_URL}/analyze",
    json={"repository": "owner/repo"}
)
print(response.json())

# Run autonomous agent
response = requests.post(
    f"{API_URL}/autonomous",
    json={
        "repository": "owner/repo",
        "request": "Add CI/CD pipeline"
    }
)
print(response.json())
```

### JavaScript

```javascript
const API_URL = 'https://4dyb4z9kgk.execute-api.us-east-1.amazonaws.com/prod';

// Analyze repository
const response = await fetch(`${API_URL}/analyze`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ repository: 'owner/repo' })
});
const data = await response.json();
console.log(data);
```

---

## Webhooks (Coming Soon)

Future support for GitHub webhooks to trigger autonomous actions.

---

*Last Updated: December 2024*
