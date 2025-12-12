"""
BCG DevOps GenAI - Autonomous Agentic Workflow Generator
========================================================
A FULLY AUTONOMOUS AI-powered DevOps agent that can:
- AUTO-DETECT: Language, framework, dependencies from repository
- AUTO-GENERATE: Production-ready CI/CD workflows
- AUTO-PUSH: Commit and push workflows to GitHub
- AUTO-TRACK: Monitor pipeline execution in real-time
- AUTO-HEAL: Detect failures and auto-fix issues

BCG Toolchain Integration:
- JFrog Artifactory (Artifact Management)
- Prisma Cloud (Security Scanning)
- SonarQube (Code Quality)
- Datadog (Monitoring & Observability)
- ArgoCD (GitOps CD)
- Octopus Deploy (Release Management)
- AWS EKS (Kubernetes)
- GitHub Actions (CI)
- Slack (Notifications)

Agent Capabilities:
1. Repository Analysis & Auto-Detection
2. Intelligent Workflow Generation
3. GitHub Integration (Push, PR, Actions)
4. Pipeline Monitoring & Tracking
5. Auto-Healing & Error Recovery
6. Multi-language support (Node.js, Python, Go, Java, .NET)
"""

import json
import boto3
import os
import logging
import hashlib
import base64
import re
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
import uuid

# Setup logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Configuration
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')
KB_BUCKET = os.environ.get('KB_BUCKET', '')
AUDIT_TABLE = os.environ.get('AUDIT_TABLE', '')
SESSIONS_TABLE = os.environ.get('SESSIONS_TABLE', '')
GITHUB_SECRET_NAME = os.environ.get('GITHUB_SECRET_NAME', 'bcg-devops-genai-poc/github-token')


# ============================================================================
# AUTONOMOUS AGENT STATUS TRACKING
# ============================================================================

class AgentStatus(str, Enum):
    INITIALIZING = "initializing"
    DETECTING = "detecting"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    PUSHING = "pushing"
    MONITORING = "monitoring"
    HEALING = "healing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"


# ============================================================================
# GITHUB API INTEGRATION
# ============================================================================

def get_github_token() -> str:
    """Get GitHub token from Secrets Manager"""
    try:
        response = secrets_manager.get_secret_value(SecretId=GITHUB_SECRET_NAME)
        secret = json.loads(response['SecretString'])
        return secret.get('token', secret.get('GITHUB_TOKEN', ''))
    except Exception as e:
        logger.error(f"Failed to get GitHub token: {str(e)}")
        return os.environ.get('GITHUB_TOKEN', '')


def github_api_request(endpoint: str, method: str = 'GET', data: dict = None, token: str = None) -> dict:
    """Make GitHub API request"""
    if not token:
        token = get_github_token()
    
    url = f"https://api.github.com{endpoint}" if not endpoint.startswith('http') else endpoint
    
    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'BCG-DevOps-GenAI-Agent/2.0',
        'Content-Type': 'application/json'
    }
    
    request_data = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        logger.error(f"GitHub API error: {e.code} - {error_body}")
        raise Exception(f"GitHub API error: {e.code} - {error_body}")
    except Exception as e:
        logger.error(f"GitHub API request failed: {str(e)}")
        raise


# ============================================================================
# AUTO-DETECTION ENGINE
# ============================================================================

DETECTION_PATTERNS = {
    "nodejs": {
        "files": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
        "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs"],
        "frameworks": {
            "react": ["react", "react-dom", "next", "gatsby"],
            "vue": ["vue", "@vue/cli"],
            "angular": ["@angular/core"],
            "express": ["express"],
            "nestjs": ["@nestjs/core"],
            "fastify": ["fastify"]
        }
    },
    "python": {
        "files": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "poetry.lock"],
        "extensions": [".py", ".pyx"],
        "frameworks": {
            "django": ["django"],
            "flask": ["flask"],
            "fastapi": ["fastapi"],
            "pytorch": ["torch"],
            "tensorflow": ["tensorflow"]
        }
    },
    "golang": {
        "files": ["go.mod", "go.sum"],
        "extensions": [".go"],
        "frameworks": {
            "gin": ["github.com/gin-gonic/gin"],
            "echo": ["github.com/labstack/echo"],
            "fiber": ["github.com/gofiber/fiber"]
        }
    },
    "java": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
        "extensions": [".java", ".kt"],
        "frameworks": {
            "spring": ["org.springframework"],
            "springboot": ["spring-boot-starter"],
            "quarkus": ["io.quarkus"],
            "micronaut": ["io.micronaut"]
        }
    },
    "dotnet": {
        "files": ["*.csproj", "*.fsproj", "*.sln", "nuget.config"],
        "extensions": [".cs", ".fs", ".vb"],
        "frameworks": {
            "aspnet": ["Microsoft.AspNetCore"],
            "blazor": ["Microsoft.AspNetCore.Components"],
            "maui": ["Microsoft.Maui"]
        }
    }
}


def detect_language_from_repo(owner: str, repo: str, token: str = None) -> Dict[str, Any]:
    """Auto-detect language and framework from GitHub repository"""
    
    detection_result = {
        "language": None,
        "framework": None,
        "package_manager": None,
        "dependencies": [],
        "has_dockerfile": False,
        "has_kubernetes": False,
        "has_terraform": False,
        "has_existing_workflow": False,
        "confidence": 0.0,
        "detected_files": []
    }
    
    try:
        # Get repository languages
        languages = github_api_request(f"/repos/{owner}/{repo}/languages", token=token)
        if languages:
            primary_language = max(languages, key=languages.get).lower()
            detection_result["detected_languages"] = languages
            
            # Map GitHub language to our supported languages
            lang_map = {
                "javascript": "nodejs", "typescript": "nodejs",
                "python": "python",
                "go": "golang",
                "java": "java", "kotlin": "java",
                "c#": "dotnet", "f#": "dotnet"
            }
            detection_result["language"] = lang_map.get(primary_language, primary_language)
        
        # Get repository contents
        contents = github_api_request(f"/repos/{owner}/{repo}/contents", token=token)
        
        file_names = [item['name'] for item in contents if item['type'] == 'file']
        dir_names = [item['name'] for item in contents if item['type'] == 'dir']
        
        detection_result["detected_files"] = file_names
        
        # Check for specific files
        detection_result["has_dockerfile"] = "Dockerfile" in file_names or "dockerfile" in file_names
        detection_result["has_kubernetes"] = "k8s" in dir_names or "kubernetes" in dir_names or any("kube" in d.lower() for d in dir_names)
        detection_result["has_terraform"] = "terraform" in dir_names or any(f.endswith('.tf') for f in file_names)
        detection_result["has_existing_workflow"] = ".github" in dir_names
        
        # Detect language from files
        for lang, patterns in DETECTION_PATTERNS.items():
            for pattern_file in patterns["files"]:
                if any(f == pattern_file or (pattern_file.startswith("*") and f.endswith(pattern_file[1:])) for f in file_names):
                    detection_result["language"] = lang
                    detection_result["confidence"] = 0.9
                    break
        
        # Detect package manager
        if detection_result["language"] == "nodejs":
            if "yarn.lock" in file_names:
                detection_result["package_manager"] = "yarn"
            elif "pnpm-lock.yaml" in file_names:
                detection_result["package_manager"] = "pnpm"
            else:
                detection_result["package_manager"] = "npm"
        elif detection_result["language"] == "python":
            if "poetry.lock" in file_names:
                detection_result["package_manager"] = "poetry"
            elif "Pipfile" in file_names:
                detection_result["package_manager"] = "pipenv"
            else:
                detection_result["package_manager"] = "pip"
        elif detection_result["language"] == "java":
            if "build.gradle" in file_names or "build.gradle.kts" in file_names:
                detection_result["package_manager"] = "gradle"
            else:
                detection_result["package_manager"] = "maven"
        
        # Try to detect framework from package file
        if detection_result["language"] == "nodejs" and "package.json" in file_names:
            try:
                pkg_content = github_api_request(f"/repos/{owner}/{repo}/contents/package.json", token=token)
                if pkg_content.get('content'):
                    pkg_json = json.loads(base64.b64decode(pkg_content['content']).decode('utf-8'))
                    deps = {**pkg_json.get('dependencies', {}), **pkg_json.get('devDependencies', {})}
                    detection_result["dependencies"] = list(deps.keys())
                    
                    # Detect framework
                    for fw_name, fw_packages in DETECTION_PATTERNS["nodejs"]["frameworks"].items():
                        if any(pkg in deps for pkg in fw_packages):
                            detection_result["framework"] = fw_name
                            break
            except Exception as e:
                logger.warning(f"Could not parse package.json: {e}")
        
        # Detect Python framework
        if detection_result["language"] == "python" and "requirements.txt" in file_names:
            try:
                req_content = github_api_request(f"/repos/{owner}/{repo}/contents/requirements.txt", token=token)
                if req_content.get('content'):
                    requirements = base64.b64decode(req_content['content']).decode('utf-8')
                    detection_result["dependencies"] = [line.split('==')[0].split('>=')[0].strip() 
                                                        for line in requirements.split('\n') 
                                                        if line.strip() and not line.startswith('#')]
                    
                    for fw_name, fw_packages in DETECTION_PATTERNS["python"]["frameworks"].items():
                        if any(pkg.lower() in [d.lower() for d in detection_result["dependencies"]] for pkg in fw_packages):
                            detection_result["framework"] = fw_name
                            break
            except Exception as e:
                logger.warning(f"Could not parse requirements.txt: {e}")
        
        detection_result["confidence"] = 0.95 if detection_result["framework"] else 0.85
        
    except Exception as e:
        logger.error(f"Error detecting language: {str(e)}")
        detection_result["error"] = str(e)
    
    return detection_result


# ============================================================================
# AUTONOMOUS AGENT SESSION MANAGEMENT
# ============================================================================

def create_agent_session(repo_url: str, task_type: str) -> Dict[str, Any]:
    """Create a new autonomous agent session"""
    session_id = str(uuid.uuid4())
    
    session = {
        "session_id": session_id,
        "repo_url": repo_url,
        "task_type": task_type,
        "status": AgentStatus.INITIALIZING.value,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
        "steps": [],
        "current_step": 0,
        "detection_result": None,
        "workflow_content": None,
        "github_commit_sha": None,
        "github_pr_url": None,
        "pipeline_run_id": None,
        "pipeline_status": None,
        "error": None,
        "auto_heal_attempts": 0
    }
    
    # Store in DynamoDB if available
    if SESSIONS_TABLE:
        try:
            table = dynamodb.Table(SESSIONS_TABLE)
            table.put_item(Item=session)
        except Exception as e:
            logger.warning(f"Could not store session: {e}")
    
    return session


def update_agent_session(session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update agent session"""
    updates["updated_at"] = datetime.now().isoformat()
    
    if SESSIONS_TABLE:
        try:
            table = dynamodb.Table(SESSIONS_TABLE)
            update_expr = "SET " + ", ".join(f"#{k} = :{k}" for k in updates.keys())
            expr_names = {f"#{k}": k for k in updates.keys()}
            expr_values = {f":{k}": v for k, v in updates.items()}
            
            table.update_item(
                Key={"session_id": session_id},
                UpdateExpression=update_expr,
                ExpressionAttributeNames=expr_names,
                ExpressionAttributeValues=expr_values
            )
        except Exception as e:
            logger.warning(f"Could not update session: {e}")
    
    return updates


def add_session_step(session_id: str, step_name: str, status: str, details: str = None) -> Dict[str, Any]:
    """Add a step to session tracking"""
    step = {
        "step": step_name,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "details": details
    }
    
    logger.info(f"[{session_id}] Step: {step_name} - {status}")
    return step


# ============================================================================
# GITHUB WORKFLOW PUSH & PR CREATION
# ============================================================================

def push_workflow_to_github(
    owner: str,
    repo: str,
    workflow_content: str,
    workflow_name: str = "ci-cd.yml",
    branch: str = "main",
    create_pr: bool = True,
    token: str = None
) -> Dict[str, Any]:
    """Push workflow to GitHub and optionally create PR"""
    
    result = {
        "success": False,
        "commit_sha": None,
        "pr_url": None,
        "workflow_path": None,
        "error": None
    }
    
    try:
        workflow_path = f".github/workflows/{workflow_name}"
        result["workflow_path"] = workflow_path
        
        # Create a new branch for the workflow
        pr_branch = f"devops-agent/add-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        # Get default branch SHA
        ref_data = github_api_request(f"/repos/{owner}/{repo}/git/ref/heads/{branch}", token=token)
        base_sha = ref_data['object']['sha']
        
        # Create new branch
        github_api_request(
            f"/repos/{owner}/{repo}/git/refs",
            method='POST',
            data={
                "ref": f"refs/heads/{pr_branch}",
                "sha": base_sha
            },
            token=token
        )
        
        # Check if workflow file exists
        try:
            existing_file = github_api_request(
                f"/repos/{owner}/{repo}/contents/{workflow_path}?ref={pr_branch}",
                token=token
            )
            file_sha = existing_file.get('sha')
        except:
            file_sha = None
        
        # Create/Update workflow file
        commit_data = {
            "message": f"feat(ci): Add BCG-compliant CI/CD workflow\n\nGenerated by BCG DevOps GenAI Agent\n- Auto-detected project configuration\n- Integrated security scanning (Prisma, Trivy, Gitleaks)\n- Added code quality (SonarQube)\n- Configured deployment automation",
            "content": base64.b64encode(workflow_content.encode('utf-8')).decode('utf-8'),
            "branch": pr_branch
        }
        
        if file_sha:
            commit_data["sha"] = file_sha
        
        commit_response = github_api_request(
            f"/repos/{owner}/{repo}/contents/{workflow_path}",
            method='PUT',
            data=commit_data,
            token=token
        )
        
        result["commit_sha"] = commit_response.get('commit', {}).get('sha')
        result["success"] = True
        
        # Create Pull Request
        if create_pr:
            pr_response = github_api_request(
                f"/repos/{owner}/{repo}/pulls",
                method='POST',
                data={
                    "title": "feat(ci): Add BCG-compliant CI/CD Pipeline",
                    "body": """## 🚀 BCG DevOps GenAI Agent - Automated CI/CD Pipeline

### What's Included
- ✅ **Build & Test**: Automated build with dependency caching
- ✅ **Security Scanning**: Prisma Cloud SAST/SCA, Trivy, Gitleaks
- ✅ **Code Quality**: SonarQube analysis with quality gates
- ✅ **Artifact Management**: JFrog Artifactory integration
- ✅ **Container Build**: Docker multi-stage builds with Trivy scanning
- ✅ **Deployment**: ArgoCD GitOps / Octopus Deploy
- ✅ **Monitoring**: Datadog DORA metrics tracking
- ✅ **Notifications**: Slack alerts for pipeline status

### Auto-Detected Configuration
This workflow was automatically generated based on your repository analysis.

### Required Secrets
Please configure the following secrets in your repository:
- `JFROG_ARTIFACTORY_URL`, `JFROG_USER`, `JFROG_ACCESS_TOKEN`
- `SONAR_TOKEN`, `SONAR_HOST_URL`
- `PRISMA_API_URL`, `PRISMA_ACCESS_KEY`
- `DATADOG_API_KEY`
- `ARGOCD_SERVER`, `ARGOCD_USERNAME`, `ARGOCD_PASSWORD`
- `SLACK_WEBHOOK_URL`

---
*Generated by BCG DevOps GenAI Autonomous Agent*
""",
                    "head": pr_branch,
                    "base": branch
                },
                token=token
            )
            
            result["pr_url"] = pr_response.get('html_url')
            result["pr_number"] = pr_response.get('number')
        
    except Exception as e:
        logger.error(f"Error pushing workflow: {str(e)}")
        result["error"] = str(e)
    
    return result


# ============================================================================
# PIPELINE MONITORING & TRACKING
# ============================================================================

def get_workflow_runs(owner: str, repo: str, workflow_id: str = None, token: str = None) -> List[Dict]:
    """Get GitHub Actions workflow runs"""
    try:
        endpoint = f"/repos/{owner}/{repo}/actions/runs"
        if workflow_id:
            endpoint = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
        
        response = github_api_request(endpoint, token=token)
        return response.get('workflow_runs', [])
    except Exception as e:
        logger.error(f"Error getting workflow runs: {e}")
        return []


def get_workflow_run_status(owner: str, repo: str, run_id: int, token: str = None) -> Dict[str, Any]:
    """Get detailed status of a workflow run"""
    try:
        run = github_api_request(f"/repos/{owner}/{repo}/actions/runs/{run_id}", token=token)
        jobs = github_api_request(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs", token=token)
        
        return {
            "run_id": run_id,
            "status": run.get('status'),
            "conclusion": run.get('conclusion'),
            "html_url": run.get('html_url'),
            "created_at": run.get('created_at'),
            "updated_at": run.get('updated_at'),
            "jobs": [
                {
                    "id": job.get('id'),
                    "name": job.get('name'),
                    "status": job.get('status'),
                    "conclusion": job.get('conclusion'),
                    "started_at": job.get('started_at'),
                    "completed_at": job.get('completed_at'),
                    "steps": [
                        {
                            "name": step.get('name'),
                            "status": step.get('status'),
                            "conclusion": step.get('conclusion')
                        }
                        for step in job.get('steps', [])
                    ]
                }
                for job in jobs.get('jobs', [])
            ]
        }
    except Exception as e:
        logger.error(f"Error getting run status: {e}")
        return {"error": str(e)}


def get_workflow_logs(owner: str, repo: str, run_id: int, token: str = None) -> str:
    """Get workflow run logs for analysis"""
    try:
        # Get failed job logs
        jobs = github_api_request(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs", token=token)
        
        failed_logs = []
        for job in jobs.get('jobs', []):
            if job.get('conclusion') == 'failure':
                for step in job.get('steps', []):
                    if step.get('conclusion') == 'failure':
                        failed_logs.append(f"Job: {job['name']}, Step: {step['name']}")
        
        return "\n".join(failed_logs) if failed_logs else "No failure details available"
    except Exception as e:
        return f"Error getting logs: {e}"


# ============================================================================
# AUTO-HEALING ENGINE
# ============================================================================

COMMON_FIXES = {
    "npm ci": {
        "patterns": ["npm ERR!", "ENOENT", "package-lock.json"],
        "fix": "Try 'npm install' instead of 'npm ci', or regenerate package-lock.json"
    },
    "permission_denied": {
        "patterns": ["Permission denied", "EACCES"],
        "fix": "Add 'chmod +x' before executing scripts"
    },
    "docker_build": {
        "patterns": ["docker build", "Dockerfile", "failed to compute cache key"],
        "fix": "Check Dockerfile path and build context"
    },
    "test_failure": {
        "patterns": ["test failed", "FAIL", "AssertionError"],
        "fix": "Review test failures - may need to update tests or fix code"
    },
    "sonarqube": {
        "patterns": ["sonar", "Quality Gate", "QUALITY_GATE_FAILURE"],
        "fix": "Review SonarQube report and fix code quality issues"
    },
    "timeout": {
        "patterns": ["timeout", "exceeded", "timed out"],
        "fix": "Increase timeout-minutes in workflow or optimize long-running steps"
    }
}


def analyze_failure_and_suggest_fix(logs: str, workflow_content: str) -> Dict[str, Any]:
    """Analyze pipeline failure and suggest fixes"""
    
    analysis = {
        "identified_issues": [],
        "suggested_fixes": [],
        "auto_fixable": False,
        "fixed_workflow": None
    }
    
    for issue_name, issue_data in COMMON_FIXES.items():
        for pattern in issue_data["patterns"]:
            if pattern.lower() in logs.lower():
                analysis["identified_issues"].append(issue_name)
                analysis["suggested_fixes"].append(issue_data["fix"])
                break
    
    # Try to auto-fix common issues
    if "timeout" in analysis["identified_issues"]:
        # Increase timeouts
        fixed_workflow = re.sub(
            r'timeout-minutes:\s*(\d+)',
            lambda m: f'timeout-minutes: {int(m.group(1)) * 2}',
            workflow_content
        )
        if fixed_workflow != workflow_content:
            analysis["auto_fixable"] = True
            analysis["fixed_workflow"] = fixed_workflow
    
    return analysis


def auto_heal_pipeline(
    owner: str,
    repo: str,
    run_id: int,
    session_id: str,
    token: str = None
) -> Dict[str, Any]:
    """Attempt to auto-heal a failed pipeline"""
    
    result = {
        "healed": False,
        "action_taken": None,
        "new_run_id": None,
        "error": None
    }
    
    try:
        # Get failure logs
        logs = get_workflow_logs(owner, repo, run_id, token)
        
        # Get current workflow content
        workflow_path = ".github/workflows/ci-cd.yml"
        try:
            file_content = github_api_request(
                f"/repos/{owner}/{repo}/contents/{workflow_path}",
                token=token
            )
            workflow_content = base64.b64decode(file_content['content']).decode('utf-8')
        except:
            workflow_content = ""
        
        # Analyze and get fix suggestions
        analysis = analyze_failure_and_suggest_fix(logs, workflow_content)
        
        if analysis["auto_fixable"] and analysis["fixed_workflow"]:
            # Push fixed workflow
            push_result = push_workflow_to_github(
                owner, repo,
                analysis["fixed_workflow"],
                workflow_name="ci-cd.yml",
                create_pr=False,
                token=token
            )
            
            if push_result["success"]:
                result["healed"] = True
                result["action_taken"] = f"Applied auto-fix for: {', '.join(analysis['identified_issues'])}"
                
                # Trigger new run
                github_api_request(
                    f"/repos/{owner}/{repo}/actions/workflows/ci-cd.yml/dispatches",
                    method='POST',
                    data={"ref": "main"},
                    token=token
                )
        else:
            result["action_taken"] = "Manual intervention required"
            result["suggestions"] = analysis["suggested_fixes"]
        
    except Exception as e:
        logger.error(f"Auto-heal error: {e}")
        result["error"] = str(e)
    
    return result

# ============================================================================
# BCG DEVOPS TOOLCHAIN KNOWLEDGE BASE
# Complete knowledge of all tools BCG uses and their integrations
# ============================================================================

BCG_TOOLCHAIN = {
    "ci_cd": {
        "github_actions": {
            "description": "Primary CI platform for BCG",
            "category": "Continuous Integration",
            "features": [
                "Workflow automation",
                "Matrix builds",
                "Reusable workflows",
                "Self-hosted runners",
                "Environment protection rules"
            ],
            "best_practices": [
                "Use pinned action versions (@v4, not @main)",
                "Set timeout-minutes on all jobs",
                "Use GitHub Environments for deployments",
                "Cache dependencies for faster builds",
                "Use concurrency to prevent duplicate runs"
            ],
            "secrets_required": [
                "GITHUB_TOKEN (auto-provided)",
                "Repository secrets for external services"
            ]
        },
        "argocd": {
            "description": "GitOps-based Continuous Delivery for Kubernetes",
            "category": "Continuous Delivery",
            "features": [
                "GitOps workflows",
                "Automated sync",
                "Rollback capabilities",
                "Multi-cluster support",
                "Application sets"
            ],
            "integration_steps": [
                "Install ArgoCD CLI in workflow",
                "Login to ArgoCD server",
                "Update application image tag",
                "Sync application",
                "Wait for rollout completion"
            ],
            "secrets_required": [
                "ARGOCD_SERVER",
                "ARGOCD_USERNAME", 
                "ARGOCD_PASSWORD"
            ],
            "workflow_snippet": """
      - name: Deploy via ArgoCD
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          ./argocd login ${{ secrets.ARGOCD_SERVER }} --username ${{ secrets.ARGOCD_USERNAME }} --password ${{ secrets.ARGOCD_PASSWORD }} --insecure
          ./argocd app set $APP_NAME --helm-set image.tag=${{ github.sha }}
          ./argocd app sync $APP_NAME --prune
          ./argocd app wait $APP_NAME --timeout 300
"""
        },
        "octopus_deploy": {
            "description": "Release orchestration and deployment automation",
            "category": "Release Management",
            "features": [
                "Multi-environment deployments",
                "Runbook automation",
                "Release versioning",
                "Approval workflows",
                "Deployment targets"
            ],
            "integration_steps": [
                "Create release via API",
                "Trigger deployment to environment",
                "Pass image tag and repository info"
            ],
            "secrets_required": [
                "OCTOPUS_SERVER_URL",
                "OCTOPUS_API_KEY",
                "OCTOPUS_PROJECT_ID",
                "OCTOPUS_ENVIRONMENT_ID"
            ],
            "workflow_snippet": """
      - name: Trigger Octopus Deploy
        run: |
          curl -X POST "${{ secrets.OCTOPUS_SERVER_URL }}/api/deployments" \\
            -H "X-Octopus-ApiKey: ${{ secrets.OCTOPUS_API_KEY }}" \\
            -H "Content-Type: application/json" \\
            -d '{
              "ProjectId": "${{ secrets.OCTOPUS_PROJECT_ID }}",
              "EnvironmentId": "${{ secrets.OCTOPUS_ENV_ID }}",
              "FormValues": {
                "ImageTag": "${{ github.sha }}",
                "ImageRepository": "${{ env.IMAGE_FULL }}"
              }
            }'
"""
        }
    },
    "artifact_management": {
        "jfrog_artifactory": {
            "description": "Universal artifact repository for BCG",
            "category": "Artifact Management",
            "features": [
                "Docker registry",
                "npm/PyPI/Maven/Go proxies",
                "Build info tracking",
                "Xray security scanning",
                "Replication"
            ],
            "repository_types": {
                "docker": "docker-local, docker-remote",
                "npm": "npm-local, npm-remote",
                "pypi": "pypi-local, pypi-remote",
                "maven": "maven-local, maven-remote",
                "go": "go-local, go-remote",
                "nuget": "nuget-local, nuget-remote"
            },
            "secrets_required": [
                "JFROG_ARTIFACTORY_URL",
                "JFROG_USER",
                "JFROG_ACCESS_TOKEN"
            ],
            "setup_snippets": {
                "docker": """
      - name: Login to JFrog Artifactory
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.JFROG_ARTIFACTORY_URL }}
          username: ${{ secrets.JFROG_USER }}
          password: ${{ secrets.JFROG_ACCESS_TOKEN }}
""",
                "npm": """
      - name: Configure JFrog npm registry
        run: |
          npm config set registry https://${{ secrets.JFROG_ARTIFACTORY_URL }}/artifactory/api/npm/npm-remote/
          npm config set ///${{ secrets.JFROG_ARTIFACTORY_URL }}/artifactory/api/npm/npm-remote/:_authToken ${{ secrets.JFROG_ACCESS_TOKEN }}
""",
                "python": """
      - name: Configure JFrog PyPI
        run: |
          pip config set global.index-url https://${{ secrets.JFROG_USER }}:${{ secrets.JFROG_ACCESS_TOKEN }}@${{ secrets.JFROG_ARTIFACTORY_URL }}/artifactory/api/pypi/pypi-remote/simple
""",
                "maven": """
      - name: Configure JFrog Maven
        run: |
          mkdir -p ~/.m2
          cat > ~/.m2/settings.xml << 'EOF'
          <settings>
            <servers>
              <server>
                <id>jfrog</id>
                <username>${{ secrets.JFROG_USER }}</username>
                <password>${{ secrets.JFROG_ACCESS_TOKEN }}</password>
              </server>
            </servers>
          </settings>
          EOF
""",
                "go": """
      - name: Configure Go proxy via JFrog
        run: |
          go env -w GOPROXY="https://${{ secrets.JFROG_ARTIFACTORY_URL }}/artifactory/api/go/go-remote,direct"
""",
                "nuget": """
      - name: Configure JFrog NuGet
        run: |
          dotnet nuget add source https://${{ secrets.JFROG_ARTIFACTORY_URL }}/artifactory/api/nuget/nuget-remote \\
            --name jfrog --username ${{ secrets.JFROG_USER }} --password ${{ secrets.JFROG_ACCESS_TOKEN }}
"""
            },
            "xray_scan": """
      - name: JFrog Xray Scan
        run: |
          jf docker scan ${{ env.IMAGE_FULL }}
"""
        }
    },
    "security_scanning": {
        "prisma_cloud": {
            "description": "Cloud-native security platform by Palo Alto Networks",
            "category": "Security",
            "scan_types": {
                "sast": "Static Application Security Testing",
                "sca": "Software Composition Analysis",
                "container": "Container image scanning",
                "iac": "Infrastructure as Code scanning"
            },
            "secrets_required": [
                "PRISMA_API_URL",
                "PRISMA_ACCESS_KEY",
                "PRISMA_SECRET_KEY",
                "PRISMA_CONSOLE_URL"
            ],
            "workflow_snippets": {
                "sast": """
      - name: Prisma Cloud SAST Scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          output_format: sarif
          output_file_path: prisma-sast-results.sarif
          soft_fail: false
        env:
          PRISMA_API_URL: ${{ secrets.PRISMA_API_URL }}
          BC_API_KEY: ${{ secrets.PRISMA_ACCESS_KEY }}
""",
                "sca": """
      - name: Prisma Cloud SCA Scan
        run: |
          curl -L -o checkov https://github.com/bridgecrewio/checkov/releases/latest/download/checkov_linux_amd64
          chmod +x checkov
          ./checkov -f package-lock.json --framework sca_package --bc-api-key ${{ secrets.PRISMA_ACCESS_KEY }} --repo-id ${{ github.repository }} --branch ${{ github.ref_name }}
        continue-on-error: true
""",
                "container": """
      - name: Prisma Cloud Container Scan
        uses: PaloAltoNetworks/prisma-cloud-scan@v1
        with:
          pcc_console_url: ${{ secrets.PRISMA_CONSOLE_URL }}
          pcc_user: ${{ secrets.PRISMA_ACCESS_KEY }}
          pcc_pass: ${{ secrets.PRISMA_SECRET_KEY }}
          image_name: ${{ env.IMAGE_FULL }}
"""
            }
        },
        "sonarqube": {
            "description": "Code quality and security analysis platform",
            "category": "Code Quality",
            "features": [
                "Code coverage",
                "Code smells detection",
                "Security hotspots",
                "Quality gates",
                "Multi-language support"
            ],
            "secrets_required": [
                "SONAR_TOKEN",
                "SONAR_HOST_URL"
            ],
            "language_configs": {
                "nodejs": "-Dsonar.sources=src -Dsonar.tests=src -Dsonar.test.inclusions=**/*.test.js,**/*.test.ts -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info",
                "python": "-Dsonar.sources=src -Dsonar.tests=tests -Dsonar.python.coverage.reportPaths=coverage.xml",
                "go": "-Dsonar.sources=. -Dsonar.exclusions=**/*_test.go,**/vendor/** -Dsonar.tests=. -Dsonar.test.inclusions=**/*_test.go -Dsonar.go.coverage.reportPaths=coverage.out",
                "java": "-Dsonar.sources=src/main/java -Dsonar.tests=src/test/java -Dsonar.java.binaries=target/classes -Dsonar.coverage.jacoco.xmlReportPaths=target/site/jacoco/jacoco.xml",
                "dotnet": "-Dsonar.sources=. -Dsonar.cs.opencover.reportsPaths=**/coverage.opencover.xml"
            },
            "workflow_snippet": """
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@v2
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
        with:
          args: >
            -Dsonar.projectKey=${{ github.repository_owner }}_${{ github.event.repository.name }}
            {language_config}
      
      - name: SonarQube Quality Gate
        uses: sonarsource/sonarqube-quality-gate-action@v1
        timeout-minutes: 5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
"""
        },
        "trivy": {
            "description": "Comprehensive vulnerability scanner",
            "category": "Security",
            "scan_types": ["fs", "image", "config", "sbom"],
            "workflow_snippet": """
      - name: Trivy Vulnerability Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy Results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
"""
        },
        "gitleaks": {
            "description": "Secret detection in code repositories",
            "category": "Security",
            "workflow_snippet": """
      - name: Gitleaks Secret Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
        }
    },
    "monitoring": {
        "datadog": {
            "description": "Cloud monitoring and analytics platform",
            "category": "Observability",
            "features": [
                "APM (Application Performance Monitoring)",
                "Log management",
                "Infrastructure monitoring",
                "DORA metrics",
                "CI visibility",
                "Deployment tracking"
            ],
            "secrets_required": [
                "DATADOG_API_KEY",
                "DATADOG_APP_KEY",
                "DATADOG_SITE"
            ],
            "integration_snippets": {
                "ci_visibility": """
      - name: Configure Datadog CI
        run: |
          npm install -g @datadog/datadog-ci
          datadog-ci junit upload --service ${{ github.repository }} ./test-results/
        env:
          DATADOG_API_KEY: ${{ secrets.DATADOG_API_KEY }}
          DD_ENV: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
""",
                "deployment_tracking": """
      - name: Datadog Deployment Tracking
        run: |
          curl -X POST "https://api.datadoghq.com/api/v2/dora/deployment" \\
            -H "Content-Type: application/json" \\
            -H "DD-API-KEY: ${{ secrets.DATADOG_API_KEY }}" \\
            -d '{
              "data": {
                "attributes": {
                  "started_at": "'$(date -u +%s)'000000000",
                  "finished_at": "'$(date -u +%s)'000000000",
                  "git": {
                    "commit_sha": "${{ github.sha }}",
                    "repository_url": "https://github.com/${{ github.repository }}"
                  },
                  "service": "${{ github.event.repository.name }}",
                  "version": "${{ env.IMAGE_TAG }}",
                  "env": "${{ env.DEPLOY_ENV }}"
                }
              }
            }'
""",
                "deployment_event": """
      - name: Datadog Deployment Event
        run: |
          curl -X POST "https://api.datadoghq.com/api/v1/events" \\
            -H "Content-Type: application/json" \\
            -H "DD-API-KEY: ${{ secrets.DATADOG_API_KEY }}" \\
            -d '{
              "title": "Deployment: ${{ github.event.repository.name }}",
              "text": "Deployed version ${{ env.IMAGE_TAG }} to ${{ env.DEPLOY_ENV }}",
              "priority": "normal",
              "tags": ["environment:${{ env.DEPLOY_ENV }}", "service:${{ github.event.repository.name }}", "version:${{ env.IMAGE_TAG }}"],
              "alert_type": "info"
            }'
"""
            }
        }
    },
    "notifications": {
        "slack": {
            "description": "Team communication and alerting",
            "category": "Notifications",
            "secrets_required": ["SLACK_WEBHOOK_URL"],
            "workflow_snippet": """
      - name: Slack Notification
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          fields: repo,message,commit,author,workflow,job
          text: ':rocket: Deployment ${{ job.status }}'
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
"""
        }
    },
    "infrastructure": {
        "aws_eks": {
            "description": "Self-managed Kubernetes on AWS",
            "category": "Container Orchestration",
            "secrets_required": [
                "AWS_ROLE_ARN",
                "EKS_CLUSTER_NAME",
                "AWS_REGION"
            ],
            "workflow_snippet": """
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name ${{ secrets.EKS_CLUSTER_NAME }} --region ${{ secrets.AWS_REGION }}
"""
        }
    }
}

# ============================================================================
# LANGUAGE-SPECIFIC CONFIGURATIONS
# ============================================================================

LANGUAGE_CONFIGS = {
    "nodejs": {
        "name": "Node.js / React / TypeScript",
        "runtime_versions": ["18", "20", "22"],
        "default_version": "20",
        "setup_action": "actions/setup-node@v4",
        "package_managers": ["npm", "yarn", "pnpm"],
        "cache_paths": ["~/.npm", "node_modules"],
        "cache_key": "node-${{ hashFiles('**/package-lock.json') }}",
        "install_command": "npm ci",
        "test_command": "npm test -- --coverage --watchAll=false",
        "build_command": "npm run build",
        "lint_command": "npm run lint --if-present",
        "dockerfile_base": "node:20-alpine",
        "security_tools": ["npm audit", "trivy", "gitleaks"],
        "quality_tools": ["eslint", "prettier", "sonarqube"],
        # React/CRA specific - CRITICAL: CI=false prevents warnings being treated as errors
        "framework_configs": {
            "react": {
                "build_env": {"CI": "false"},
                "test_env": {"CI": "true"},
                "build_command": "CI=false npm run build",
                "test_command": "npm test -- --coverage --watchAll=false --passWithNoTests"
            },
            "nextjs": {
                "build_command": "npm run build",
                "test_command": "npm test -- --passWithNoTests"
            },
            "vue": {
                "build_command": "npm run build",
                "test_command": "npm test -- --passWithNoTests"
            }
        }
    },
    "python": {
        "name": "Python / Django / FastAPI / Flask",
        "runtime_versions": ["3.9", "3.10", "3.11", "3.12"],
        "default_version": "3.12",
        "setup_action": "actions/setup-python@v5",
        "package_managers": ["pip", "poetry", "pipenv"],
        "cache_paths": ["~/.cache/pip", ".venv"],
        "cache_key": "python-${{ hashFiles('**/requirements.txt', '**/pyproject.toml') }}",
        "install_command": "pip install -r requirements.txt",
        "test_command": "pytest --cov=. --cov-report=xml",
        "build_command": "python setup.py build",
        "lint_command": "flake8 . && black --check .",
        "dockerfile_base": "python:3.12-slim",
        "security_tools": ["safety", "bandit", "trivy", "gitleaks"],
        "quality_tools": ["pylint", "flake8", "black", "mypy", "sonarqube"]
    },
    "golang": {
        "name": "Go / Golang",
        "runtime_versions": ["1.21", "1.22", "1.23"],
        "default_version": "1.22",
        "setup_action": "actions/setup-go@v5",
        "package_managers": ["go mod"],
        "cache_paths": ["~/go/pkg/mod", "~/.cache/go-build"],
        "cache_key": "go-${{ hashFiles('**/go.sum') }}",
        "install_command": "go mod download",
        "test_command": "go test -v -race -coverprofile=coverage.out ./...",
        "build_command": "CGO_ENABLED=0 GOOS=linux go build -ldflags=\"-s -w\" -o app .",
        "lint_command": "golangci-lint run",
        "dockerfile_base": "golang:1.22-alpine",
        "security_tools": ["gosec", "govulncheck", "trivy", "gitleaks"],
        "quality_tools": ["golangci-lint", "go vet", "sonarqube"]
    },
    "java": {
        "name": "Java / Spring Boot / Maven / Gradle",
        "runtime_versions": ["11", "17", "21"],
        "default_version": "21",
        "setup_action": "actions/setup-java@v4",
        "package_managers": ["maven", "gradle"],
        "cache_paths": ["~/.m2/repository", "~/.gradle/caches"],
        "cache_key": "java-${{ hashFiles('**/pom.xml', '**/build.gradle') }}",
        "install_command": "mvn dependency:resolve",
        "test_command": "mvn test jacoco:report",
        "build_command": "mvn package -DskipTests",
        "lint_command": "mvn checkstyle:check",
        "dockerfile_base": "eclipse-temurin:21-jre-alpine",
        "security_tools": ["spotbugs", "dependency-check", "trivy", "gitleaks"],
        "quality_tools": ["checkstyle", "pmd", "spotbugs", "sonarqube"]
    },
    "dotnet": {
        "name": ".NET / C# / ASP.NET Core",
        "runtime_versions": ["6.0", "7.0", "8.0"],
        "default_version": "8.0",
        "setup_action": "actions/setup-dotnet@v4",
        "package_managers": ["nuget"],
        "cache_paths": ["~/.nuget/packages"],
        "cache_key": "dotnet-${{ hashFiles('**/*.csproj', '**/packages.lock.json') }}",
        "install_command": "dotnet restore",
        "test_command": "dotnet test --collect:\"XPlat Code Coverage\"",
        "build_command": "dotnet publish -c Release -o out",
        "lint_command": "dotnet format --verify-no-changes",
        "dockerfile_base": "mcr.microsoft.com/dotnet/aspnet:8.0-alpine",
        "security_tools": ["security-scan", "trivy", "gitleaks"],
        "quality_tools": ["dotnet format", "sonarqube"]
    }
}

# ============================================================================
# AI AGENT SYSTEM PROMPT
# ============================================================================

def get_system_prompt(tools_enabled=None, language=None, framework=None):
    """Generate comprehensive system prompt with BCG toolchain knowledge"""
    
    tools_knowledge = ""
    if tools_enabled:
        for tool in tools_enabled:
            for category, items in BCG_TOOLCHAIN.items():
                if tool.lower() in items:
                    tool_info = items[tool.lower()]
                    tools_knowledge += f"\n### {tool.upper()}\n"
                    tools_knowledge += f"- Description: {tool_info.get('description', '')}\n"
                    tools_knowledge += f"- Secrets Required: {', '.join(tool_info.get('secrets_required', []))}\n"
                    if 'workflow_snippet' in tool_info:
                        tools_knowledge += f"- Integration Code:\n```yaml\n{tool_info['workflow_snippet']}\n```\n"
    
    language_knowledge = ""
    framework_knowledge = ""
    if language and language.lower() in LANGUAGE_CONFIGS:
        lang_config = LANGUAGE_CONFIGS[language.lower()]
        language_knowledge = f"""
### {lang_config['name']} Configuration:
- Runtime Version: {lang_config['default_version']}
- Setup Action: {lang_config['setup_action']}
- Cache Key: {lang_config['cache_key']}
- Install: {lang_config['install_command']}
- Test: {lang_config['test_command']}
- Build: {lang_config['build_command']}
- Security Tools: {', '.join(lang_config['security_tools'])}
- Quality Tools: {', '.join(lang_config['quality_tools'])}
"""
        # Add framework-specific configuration if detected
        if framework and 'framework_configs' in lang_config:
            fw_key = framework.lower()
            if fw_key in lang_config['framework_configs']:
                fw_config = lang_config['framework_configs'][fw_key]
                framework_knowledge = f"""
### CRITICAL - {framework.upper()} FRAMEWORK SPECIFIC REQUIREMENTS:
"""
                if fw_key == 'react':
                    framework_knowledge += """
**React/Create-React-App (CRA) builds REQUIRE special handling:**
- CRA treats ALL warnings as errors in CI mode by default
- You MUST set CI=false for the build step or the build will FAIL

**MANDATORY BUILD STEP FOR REACT:**
```yaml
- name: Build
  run: npm run build
  env:
    CI: 'false'  # CRITICAL: Prevents CRA treating warnings as errors
```

**Test step should use:**
```yaml
- name: Test
  run: npm test -- --coverage --watchAll=false --passWithNoTests
  env:
    CI: 'true'
```
"""
                else:
                    if 'build_command' in fw_config:
                        framework_knowledge += f"- Build Command: {fw_config['build_command']}\n"
                    if 'test_command' in fw_config:
                        framework_knowledge += f"- Test Command: {fw_config['test_command']}\n"
                    if 'build_env' in fw_config:
                        framework_knowledge += f"- Build Environment: {fw_config['build_env']}\n"
    
    return f"""You are an expert DevOps AI Agent for BCG (Boston Consulting Group).
You have deep knowledge of BCG's complete DevOps toolchain and best practices.

## YOUR CAPABILITIES:
1. Generate production-ready GitHub Actions workflows
2. Integrate BCG's standard tools (JFrog, Prisma, SonarQube, Datadog, ArgoCD, Octopus)
3. Provide security-first CI/CD pipelines
4. Support multiple languages (Node.js, Python, Go, Java, .NET)
5. Configure environment-specific deployments

## BCG STANDARD TOOLCHAIN:
- **Artifact Management**: JFrog Artifactory
- **Security Scanning**: Prisma Cloud (SAST, SCA, Container), Trivy, Gitleaks
- **Code Quality**: SonarQube with Quality Gates
- **Monitoring**: Datadog (APM, Logs, DORA metrics)
- **GitOps CD**: ArgoCD for Kubernetes deployments
- **Release Management**: Octopus Deploy
- **Container Orchestration**: AWS EKS (self-managed)
- **Notifications**: Slack

## MANDATORY REQUIREMENTS FOR ALL WORKFLOWS:

1. **TIMEOUTS**: Every job MUST have timeout-minutes (build: 30, test: 15, deploy: 60)

2. **CACHING**: Always include dependency caching for faster builds:
   - Node.js: cache npm/node_modules
   - Python: cache pip
   - Go: cache go mod
   - Java: cache maven/gradle
   - .NET: cache nuget

3. **SECRETS**: All sensitive values MUST use GitHub Secrets
   - Format: ${{{{ secrets.SECRET_NAME }}}}
   - Never hardcode tokens, passwords, or API keys

4. **ACTION VERSIONS**: Always use pinned versions (@v4, @v3, etc.)
   - actions/checkout@v4
   - actions/setup-node@v4
   - actions/cache@v4

5. **SECURITY SCANNING**: Include in every workflow:
   - Gitleaks for secret detection
   - Trivy for vulnerability scanning
   - Prisma Cloud for SAST/SCA
   - SonarQube for code quality

6. **ENVIRONMENTS**: Use GitHub Environments for deployments
   - development, staging, production
   - Add protection rules for production

{tools_knowledge}

{language_knowledge}

{framework_knowledge}

## OUTPUT REQUIREMENTS:
- Return ONLY valid YAML workflow content
- NO markdown code blocks
- Include helpful comments
- Ensure proper indentation
- Group related steps logically

Generate a comprehensive, production-ready GitHub Actions workflow based on the user's requirements.
"""


# ============================================================================
# WORKFLOW GENERATION ENGINE
# ============================================================================

def invoke_bedrock(prompt: str, system_prompt: str) -> str:
    """Invoke Amazon Bedrock Nova Pro model"""
    try:
        request_body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": f"{system_prompt}\n\nUser Request: {prompt}\n\nGenerate the GitHub Actions workflow:"}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 8192,
                "temperature": 0.2,
                "topP": 0.9
            }
        }
        
        logger.info(f"Invoking model: {MODEL_ID}")
        
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        # Extract text from Nova Pro response
        if 'output' in response_body and 'message' in response_body['output']:
            content = response_body['output']['message']['content']
            if content and len(content) > 0:
                return content[0].get('text', '')
        
        if 'content' in response_body:
            return response_body['content'][0].get('text', '')
        
        return str(response_body)
        
    except Exception as e:
        logger.error(f"Error invoking Bedrock: {str(e)}")
        raise e


def clean_workflow_output(workflow: str) -> str:
    """Clean up AI-generated workflow output"""
    workflow = workflow.strip()
    
    # Remove markdown code blocks
    if workflow.startswith('```yaml'):
        workflow = workflow[7:]
    if workflow.startswith('```yml'):
        workflow = workflow[6:]
    if workflow.startswith('```'):
        workflow = workflow[3:]
    if workflow.endswith('```'):
        workflow = workflow[:-3]
    
    return workflow.strip()


def generate_workflow(
    prompt,
    language=None,
    framework=None,
    tools=None,
    environments=None,
    include_security=True,
    include_quality=True
):
    """
    Generate a comprehensive CI/CD workflow based on user requirements
    
    Args:
        prompt: User's natural language description
        language: Programming language (nodejs, python, golang, java, dotnet)
        framework: Detected framework (react, nextjs, django, etc.)
        tools: List of tools to integrate (jfrog, prisma, sonarqube, datadog, argocd, octopus)
        environments: Deployment environments (development, staging, production)
        include_security: Include security scanning steps
        include_quality: Include code quality steps
    
    Returns:
        Dictionary with generated workflow and metadata
    """
    
    # Default tools if not specified
    if not tools:
        tools = ["jfrog_artifactory", "prisma_cloud", "sonarqube", "datadog", "argocd", "slack"]
    
    if not environments:
        environments = ["development", "production"]
    
    # Build enhanced prompt
    framework_info = f" ({framework})" if framework else ""
    enhanced_prompt = f"""
Generate a GitHub Actions CI/CD workflow with these requirements:

**User Request**: {prompt}

**Language/Framework**: {language or 'Detect from user request'}{framework_info}

**Required Tools Integration**:
{chr(10).join(f'- {tool}' for tool in tools)}

**Deployment Environments**:
{chr(10).join(f'- {env}' for env in environments)}

**Include Security Scanning**: {include_security}
**Include Code Quality**: {include_quality}

Generate a complete, production-ready workflow with all specified integrations.
"""
    
    # Get system prompt with tool knowledge (including framework-specific configs)
    system_prompt = get_system_prompt(tools_enabled=tools, language=language, framework=framework)
    
    # Generate workflow
    workflow = invoke_bedrock(enhanced_prompt, system_prompt)
    workflow = clean_workflow_output(workflow)
    
    # Calculate required secrets
    required_secrets = set()
    for tool in tools:
        for category, items in BCG_TOOLCHAIN.items():
            if tool.lower().replace('_', '') in str(items).lower():
                for item_name, item_data in items.items():
                    if isinstance(item_data, dict) and 'secrets_required' in item_data:
                        required_secrets.update(item_data['secrets_required'])
    
    return {
        "workflow": workflow,
        "language": language,
        "framework": framework,
        "tools_integrated": tools,
        "environments": environments,
        "required_secrets": list(required_secrets),
        "model": MODEL_ID,
        "generated_at": datetime.now().isoformat()
    }


# ============================================================================
# API HANDLERS
# ============================================================================

def handle_generate(body: Dict) -> Dict:
    """Handle workflow generation request"""
    prompt = body.get('prompt', '')
    language = body.get('language')
    framework = body.get('framework')
    tools = body.get('tools', [])
    environments = body.get('environments', [])
    include_security = body.get('include_security', True)
    include_quality = body.get('include_quality', True)
    
    if not prompt:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: prompt'})
        }
    
    result = generate_workflow(
        prompt=prompt,
        language=language,
        framework=framework,
        tools=tools,
        environments=environments,
        include_security=include_security,
        include_quality=include_quality
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(result)
    }


def handle_tools_info(body: Dict) -> Dict:
    """Return information about available tools"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'toolchain': BCG_TOOLCHAIN,
            'languages': LANGUAGE_CONFIGS
        })
    }


def handle_health() -> Dict:
    """Health check endpoint"""
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'healthy',
            'model': MODEL_ID,
            'service': 'bcg-devops-genai-agent',
            'version': '2.0.0',
            'capabilities': [
                'workflow_generation',
                'multi_language_support',
                'bcg_toolchain_integration',
                'security_scanning',
                'deployment_automation',
                'autonomous_agent',
                'auto_detect',
                'github_integration',
                'pipeline_tracking',
                'auto_healing'
            ]
        })
    }


# ============================================================================
# AUTONOMOUS AGENT ENDPOINT HANDLERS
# ============================================================================

def parse_repo_url(repo_url: str) -> tuple:
    """Parse GitHub repository URL to get owner and repo name"""
    # Handle various GitHub URL formats
    # https://github.com/owner/repo
    # https://github.com/owner/repo.git
    # git@github.com:owner/repo.git
    # owner/repo
    
    repo_url = repo_url.strip()
    
    if repo_url.startswith('git@github.com:'):
        parts = repo_url.replace('git@github.com:', '').replace('.git', '').split('/')
    elif 'github.com' in repo_url:
        parts = repo_url.split('github.com/')[-1].replace('.git', '').split('/')
    else:
        parts = repo_url.replace('.git', '').split('/')
    
    if len(parts) >= 2:
        return parts[0], parts[1]
    raise ValueError(f"Invalid repository URL: {repo_url}")


def handle_detect(body: Dict) -> Dict:
    """Handle auto-detection request - Analyze GitHub repository"""
    repo_url = body.get('repo_url') or body.get('repository')
    
    if not repo_url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: repo_url'})
        }
    
    try:
        owner, repo = parse_repo_url(repo_url)
        
        # Create agent session
        session = create_agent_session(repo_url, "detect")
        session_id = session['session_id']
        
        update_agent_session(session_id, {"status": AgentStatus.DETECTING.value})
        add_session_step(session_id, "detection", "started", f"Analyzing {owner}/{repo}")
        
        # Perform detection
        detection_result = detect_language_from_repo(owner, repo)
        
        update_agent_session(session_id, {
            "status": AgentStatus.COMPLETED.value,
            "detection_result": detection_result
        })
        add_session_step(session_id, "detection", "completed", 
                        f"Detected: {detection_result.get('language')} - {detection_result.get('framework')}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'session_id': session_id,
                'repository': f"{owner}/{repo}",
                'detection': detection_result
            })
        }
        
    except Exception as e:
        logger.error(f"Detection error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_push(body: Dict) -> Dict:
    """Handle GitHub push request - Push workflow to repository"""
    repo_url = body.get('repo_url') or body.get('repository')
    workflow_content = body.get('workflow') or body.get('workflow_content')
    workflow_name = body.get('workflow_name', 'ci-cd.yml')
    branch = body.get('branch', 'main')
    create_pr = body.get('create_pr', True)
    
    if not repo_url or not workflow_content:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required fields: repo_url, workflow'})
        }
    
    try:
        owner, repo = parse_repo_url(repo_url)
        
        # Create agent session
        session = create_agent_session(repo_url, "push")
        session_id = session['session_id']
        
        update_agent_session(session_id, {"status": AgentStatus.PUSHING.value})
        add_session_step(session_id, "push", "started", f"Pushing to {owner}/{repo}")
        
        # Push workflow to GitHub
        push_result = push_workflow_to_github(
            owner=owner,
            repo=repo,
            workflow_content=workflow_content,
            workflow_name=workflow_name,
            branch=branch,
            create_pr=create_pr
        )
        
        if push_result['success']:
            update_agent_session(session_id, {
                "status": AgentStatus.COMPLETED.value,
                "github_commit_sha": push_result.get('commit_sha'),
                "github_pr_url": push_result.get('pr_url')
            })
            add_session_step(session_id, "push", "completed", 
                            f"PR created: {push_result.get('pr_url')}")
        else:
            update_agent_session(session_id, {
                "status": AgentStatus.FAILED.value,
                "error": push_result.get('error')
            })
            add_session_step(session_id, "push", "failed", push_result.get('error'))
        
        return {
            'statusCode': 200 if push_result['success'] else 500,
            'body': json.dumps({
                'success': push_result['success'],
                'session_id': session_id,
                'repository': f"{owner}/{repo}",
                'commit_sha': push_result.get('commit_sha'),
                'pr_url': push_result.get('pr_url'),
                'workflow_path': push_result.get('workflow_path'),
                'error': push_result.get('error')
            })
        }
        
    except Exception as e:
        logger.error(f"Push error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_track(body: Dict) -> Dict:
    """Handle pipeline tracking request - Monitor GitHub Actions workflow runs"""
    repo_url = body.get('repo_url') or body.get('repository')
    run_id = body.get('run_id')
    workflow_id = body.get('workflow_id')
    
    if not repo_url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: repo_url'})
        }
    
    try:
        owner, repo = parse_repo_url(repo_url)
        
        if run_id:
            # Get specific run status
            run_status = get_workflow_run_status(owner, repo, int(run_id))
            
            # Map GitHub status to our PipelineStatus
            status_map = {
                'queued': PipelineStatus.QUEUED.value,
                'in_progress': PipelineStatus.IN_PROGRESS.value,
                'completed': PipelineStatus.SUCCESS.value if run_status.get('conclusion') == 'success' 
                            else PipelineStatus.FAILURE.value
            }
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'repository': f"{owner}/{repo}",
                    'run_id': run_id,
                    'status': status_map.get(run_status.get('status'), run_status.get('status')),
                    'conclusion': run_status.get('conclusion'),
                    'details': run_status
                })
            }
        else:
            # List recent runs
            runs = get_workflow_runs(owner, repo, workflow_id)
            
            # Format runs
            formatted_runs = []
            for run in runs[:10]:  # Limit to 10 most recent
                formatted_runs.append({
                    'run_id': run.get('id'),
                    'name': run.get('name'),
                    'status': run.get('status'),
                    'conclusion': run.get('conclusion'),
                    'created_at': run.get('created_at'),
                    'html_url': run.get('html_url'),
                    'head_branch': run.get('head_branch'),
                    'head_sha': run.get('head_sha')[:7] if run.get('head_sha') else None
                })
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'success': True,
                    'repository': f"{owner}/{repo}",
                    'total_runs': len(runs),
                    'runs': formatted_runs
                })
            }
        
    except Exception as e:
        logger.error(f"Track error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_heal(body: Dict) -> Dict:
    """Handle auto-heal request - Attempt to fix failed pipeline"""
    repo_url = body.get('repo_url') or body.get('repository')
    run_id = body.get('run_id')
    
    if not repo_url or not run_id:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required fields: repo_url, run_id'})
        }
    
    try:
        owner, repo = parse_repo_url(repo_url)
        
        # Create agent session
        session = create_agent_session(repo_url, "heal")
        session_id = session['session_id']
        
        update_agent_session(session_id, {"status": AgentStatus.HEALING.value})
        add_session_step(session_id, "heal", "started", f"Analyzing failure for run {run_id}")
        
        # Attempt auto-heal
        heal_result = auto_heal_pipeline(owner, repo, int(run_id), session_id)
        
        if heal_result['healed']:
            update_agent_session(session_id, {
                "status": AgentStatus.COMPLETED.value,
                "auto_heal_attempts": 1
            })
            add_session_step(session_id, "heal", "completed", heal_result.get('action_taken'))
        else:
            update_agent_session(session_id, {
                "status": AgentStatus.COMPLETED.value,
                "auto_heal_attempts": 1
            })
            add_session_step(session_id, "heal", "manual_required", 
                            f"Suggestions: {heal_result.get('suggestions', [])}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'session_id': session_id,
                'repository': f"{owner}/{repo}",
                'run_id': run_id,
                'healed': heal_result.get('healed', False),
                'action_taken': heal_result.get('action_taken'),
                'suggestions': heal_result.get('suggestions', []),
                'new_run_id': heal_result.get('new_run_id'),
                'error': heal_result.get('error')
            })
        }
        
    except Exception as e:
        logger.error(f"Heal error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


def handle_autonomous(body: Dict) -> Dict:
    """
    Handle FULLY AUTONOMOUS workflow generation and deployment
    
    This is the main autonomous agent endpoint that:
    1. DETECT - Auto-detects language/framework from repository
    2. GENERATE - Creates BCG-compliant CI/CD workflow
    3. PUSH - Commits workflow and creates PR
    4. TRACK - Monitors pipeline execution (optional)
    5. HEAL - Auto-fixes failures (optional)
    """
    repo_url = body.get('repo_url') or body.get('repository')
    auto_push = body.get('auto_push', True)
    auto_track = body.get('auto_track', False)
    auto_heal = body.get('auto_heal', False)
    custom_prompt = body.get('prompt', '')
    additional_tools = body.get('tools', [])
    environments = body.get('environments', ['development', 'production'])
    workflow_name = body.get('workflow_name', 'ci-cd.yml')
    
    if not repo_url:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: repo_url'})
        }
    
    try:
        owner, repo = parse_repo_url(repo_url)
        
        # Create autonomous agent session
        session = create_agent_session(repo_url, "autonomous")
        session_id = session['session_id']
        
        result = {
            'success': True,
            'session_id': session_id,
            'repository': f"{owner}/{repo}",
            'steps': [],
            'detection': None,
            'workflow': None,
            'push_result': None,
            'tracking': None,
            'healing': None
        }
        
        # ====================================================================
        # STEP 1: AUTO-DETECT
        # ====================================================================
        update_agent_session(session_id, {"status": AgentStatus.DETECTING.value})
        step1 = add_session_step(session_id, "1_detect", "started", "Auto-detecting repository configuration")
        result['steps'].append({"step": "detect", "status": "in_progress"})
        
        detection = detect_language_from_repo(owner, repo)
        result['detection'] = detection
        
        if not detection.get('language'):
            # Fallback to prompt-based detection
            detection['language'] = 'nodejs'  # Default
            detection['confidence'] = 0.5
        
        update_agent_session(session_id, {"detection_result": detection})
        result['steps'][-1] = {"step": "detect", "status": "completed", "result": detection}
        add_session_step(session_id, "1_detect", "completed", 
                        f"Detected: {detection.get('language')} ({detection.get('framework', 'generic')})")
        
        # ====================================================================
        # STEP 2: GENERATE WORKFLOW
        # ====================================================================
        update_agent_session(session_id, {"status": AgentStatus.GENERATING.value})
        step2 = add_session_step(session_id, "2_generate", "started", "Generating BCG-compliant workflow")
        result['steps'].append({"step": "generate", "status": "in_progress"})
        
        # Build prompt with detection results
        generation_prompt = f"""
Generate a production-ready CI/CD workflow for this repository:
- Repository: {owner}/{repo}
- Language: {detection.get('language')}
- Framework: {detection.get('framework', 'generic')}
- Package Manager: {detection.get('package_manager', 'auto-detect')}
- Has Dockerfile: {detection.get('has_dockerfile', False)}
- Has Kubernetes: {detection.get('has_kubernetes', False)}
- Dependencies: {', '.join(detection.get('dependencies', [])[:10])}

{custom_prompt if custom_prompt else 'Create a comprehensive workflow with all BCG toolchain integrations.'}
"""
        
        # Determine tools to integrate
        default_tools = ["jfrog_artifactory", "prisma_cloud", "sonarqube", "datadog", "argocd", "slack"]
        tools = list(set(default_tools + additional_tools))
        
        # Generate workflow
        workflow_result = generate_workflow(
            prompt=generation_prompt,
            language=detection.get('language'),
            framework=detection.get('framework'),  # Pass detected framework for framework-specific configs
            tools=tools,
            environments=environments,
            include_security=True,
            include_quality=True
        )
        
        result['workflow'] = workflow_result
        update_agent_session(session_id, {"workflow_content": workflow_result.get('workflow')})
        result['steps'][-1] = {"step": "generate", "status": "completed"}
        add_session_step(session_id, "2_generate", "completed", 
                        f"Generated {len(workflow_result.get('workflow', ''))} character workflow")
        
        # ====================================================================
        # STEP 3: PUSH TO GITHUB (if enabled)
        # ====================================================================
        if auto_push:
            update_agent_session(session_id, {"status": AgentStatus.PUSHING.value})
            step3 = add_session_step(session_id, "3_push", "started", "Pushing workflow to GitHub")
            result['steps'].append({"step": "push", "status": "in_progress"})
            
            push_result = push_workflow_to_github(
                owner=owner,
                repo=repo,
                workflow_content=workflow_result.get('workflow', ''),
                workflow_name=workflow_name,
                branch='main',
                create_pr=True
            )
            
            result['push_result'] = push_result
            
            if push_result['success']:
                update_agent_session(session_id, {
                    "github_commit_sha": push_result.get('commit_sha'),
                    "github_pr_url": push_result.get('pr_url')
                })
                result['steps'][-1] = {"step": "push", "status": "completed", "pr_url": push_result.get('pr_url')}
                add_session_step(session_id, "3_push", "completed", f"PR: {push_result.get('pr_url')}")
            else:
                result['steps'][-1] = {"step": "push", "status": "failed", "error": push_result.get('error')}
                add_session_step(session_id, "3_push", "failed", push_result.get('error'))
        
        # ====================================================================
        # STEP 4: TRACK PIPELINE (if enabled and PR was created)
        # ====================================================================
        if auto_track and auto_push and result.get('push_result', {}).get('success'):
            update_agent_session(session_id, {"status": AgentStatus.MONITORING.value})
            step4 = add_session_step(session_id, "4_track", "started", "Monitoring pipeline execution")
            result['steps'].append({"step": "track", "status": "in_progress"})
            
            # Wait a moment for GitHub Actions to pick up the workflow
            import time
            time.sleep(5)
            
            # Get recent workflow runs
            runs = get_workflow_runs(owner, repo)
            if runs:
                latest_run = runs[0]
                run_status = get_workflow_run_status(owner, repo, latest_run['id'])
                result['tracking'] = {
                    'run_id': latest_run['id'],
                    'status': run_status.get('status'),
                    'conclusion': run_status.get('conclusion'),
                    'html_url': run_status.get('html_url')
                }
                update_agent_session(session_id, {"pipeline_run_id": latest_run['id']})
                result['steps'][-1] = {"step": "track", "status": "completed", "run_id": latest_run['id']}
                add_session_step(session_id, "4_track", "completed", f"Run ID: {latest_run['id']}")
            else:
                result['steps'][-1] = {"step": "track", "status": "no_runs_found"}
                add_session_step(session_id, "4_track", "no_runs", "No workflow runs found yet")
        
        # ====================================================================
        # STEP 5: AUTO-HEAL (if enabled and tracking shows failure)
        # ====================================================================
        if auto_heal and result.get('tracking', {}).get('conclusion') == 'failure':
            update_agent_session(session_id, {"status": AgentStatus.HEALING.value})
            step5 = add_session_step(session_id, "5_heal", "started", "Auto-healing failed pipeline")
            result['steps'].append({"step": "heal", "status": "in_progress"})
            
            run_id = result['tracking']['run_id']
            heal_result = auto_heal_pipeline(owner, repo, run_id, session_id)
            result['healing'] = heal_result
            
            if heal_result.get('healed'):
                result['steps'][-1] = {"step": "heal", "status": "healed", "action": heal_result.get('action_taken')}
                add_session_step(session_id, "5_heal", "healed", heal_result.get('action_taken'))
            else:
                result['steps'][-1] = {"step": "heal", "status": "manual_required", "suggestions": heal_result.get('suggestions')}
                add_session_step(session_id, "5_heal", "manual_required", str(heal_result.get('suggestions')))
        
        # ====================================================================
        # COMPLETE
        # ====================================================================
        update_agent_session(session_id, {"status": AgentStatus.COMPLETED.value})
        add_session_step(session_id, "complete", "success", "Autonomous workflow completed")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Autonomous agent error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'success': False
            })
        }


# ============================================================================
# DATADOG INCIDENT RESPONSE AGENT
# Autonomous L1 incident analysis and remediation
# ============================================================================

INCIDENT_RUNBOOKS = {
    "high_cpu": {
        "symptoms": ["cpu", "high cpu", "cpu spike", "processor"],
        "checks": [
            "Check top processes consuming CPU",
            "Verify if it's a legitimate traffic spike",
            "Check for runaway processes or infinite loops",
            "Verify auto-scaling is working"
        ],
        "auto_actions": [
            "Scale up EKS deployment replicas",
            "Restart problematic pods",
            "Enable auto-scaling if not configured"
        ],
        "severity_threshold": 80,
        "escalation_threshold": 95
    },
    "high_memory": {
        "symptoms": ["memory", "oom", "out of memory", "ram"],
        "checks": [
            "Check for memory leaks",
            "Verify pod memory limits",
            "Check for large data processing jobs"
        ],
        "auto_actions": [
            "Increase pod memory limits",
            "Restart pods with memory issues",
            "Scale horizontally"
        ],
        "severity_threshold": 85,
        "escalation_threshold": 95
    },
    "high_error_rate": {
        "symptoms": ["error rate", "5xx", "500 errors", "errors"],
        "checks": [
            "Check application logs for exceptions",
            "Verify downstream dependencies",
            "Check database connectivity",
            "Verify external API availability"
        ],
        "auto_actions": [
            "Restart failing pods",
            "Rollback to previous deployment",
            "Enable circuit breaker"
        ],
        "severity_threshold": 5,
        "escalation_threshold": 15
    },
    "high_latency": {
        "symptoms": ["latency", "slow", "response time", "p99"],
        "checks": [
            "Check database query performance",
            "Verify network connectivity",
            "Check for resource contention",
            "Review recent deployments"
        ],
        "auto_actions": [
            "Scale up replicas",
            "Clear application cache",
            "Enable query caching"
        ],
        "severity_threshold": 2000,
        "escalation_threshold": 5000
    },
    "pod_crash": {
        "symptoms": ["crashloopbackoff", "pod crash", "restart", "oomkilled"],
        "checks": [
            "Check pod logs for crash reason",
            "Verify resource limits",
            "Check for missing dependencies"
        ],
        "auto_actions": [
            "Increase resource limits",
            "Rollback deployment",
            "Restart deployment"
        ],
        "severity_threshold": 1,
        "escalation_threshold": 5
    },
    "disk_full": {
        "symptoms": ["disk", "storage", "volume", "no space"],
        "checks": [
            "Identify large files/logs",
            "Check log rotation settings",
            "Verify PVC sizes"
        ],
        "auto_actions": [
            "Clean up old logs",
            "Expand PVC",
            "Clear tmp files"
        ],
        "severity_threshold": 80,
        "escalation_threshold": 95
    }
}


def analyze_incident(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze incident and determine root cause and remediation"""
    
    incident_type = incident_data.get('type', '').lower()
    description = incident_data.get('description', '').lower()
    metrics = incident_data.get('metrics', {})
    service = incident_data.get('service', 'unknown')
    
    analysis = {
        "incident_type": None,
        "severity": "medium",
        "root_cause_hypothesis": [],
        "recommended_checks": [],
        "auto_remediation_possible": False,
        "auto_remediation_actions": [],
        "escalation_required": False,
        "escalation_reason": None,
        "runbook_reference": None
    }
    
    # Match incident to runbook
    for runbook_name, runbook in INCIDENT_RUNBOOKS.items():
        for symptom in runbook["symptoms"]:
            if symptom in incident_type or symptom in description:
                analysis["incident_type"] = runbook_name
                analysis["runbook_reference"] = runbook_name
                analysis["recommended_checks"] = runbook["checks"]
                analysis["auto_remediation_actions"] = runbook["auto_actions"]
                analysis["auto_remediation_possible"] = True
                
                # Check severity based on metrics
                if metrics:
                    metric_value = metrics.get('value', 0)
                    if metric_value >= runbook.get('escalation_threshold', 100):
                        analysis["severity"] = "critical"
                        analysis["escalation_required"] = True
                        analysis["escalation_reason"] = f"Metric value {metric_value} exceeds escalation threshold"
                    elif metric_value >= runbook.get('severity_threshold', 50):
                        analysis["severity"] = "high"
                
                break
        if analysis["incident_type"]:
            break
    
    # Generate root cause hypotheses
    if analysis["incident_type"]:
        analysis["root_cause_hypothesis"] = [
            f"Potential {analysis['incident_type'].replace('_', ' ')} issue in service {service}",
            f"Resource constraint or configuration issue",
            f"Recent deployment may have introduced performance regression"
        ]
    
    return analysis


def generate_incident_response(incident_data: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Generate automated incident response actions"""
    
    response = {
        "actions_taken": [],
        "slack_message": None,
        "jira_ticket": None,
        "auto_remediated": False,
        "next_steps": []
    }
    
    service = incident_data.get('service', 'unknown')
    environment = incident_data.get('environment', 'production')
    
    # Generate Slack notification
    severity_emoji = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢"
    }
    
    response["slack_message"] = {
        "channel": "#incident-response",
        "text": f"{severity_emoji.get(analysis['severity'], '⚪')} *Incident Alert*",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚨 Incident: {analysis.get('incident_type', 'Unknown').replace('_', ' ').title()}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Service:*\n{service}"},
                    {"type": "mrkdwn", "text": f"*Environment:*\n{environment}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{analysis['severity'].upper()}"},
                    {"type": "mrkdwn", "text": f"*Auto-Remediation:*\n{'Enabled' if analysis['auto_remediation_possible'] else 'Manual'}"}
                ]
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Root Cause Hypothesis:*\n" + "\n".join(f"• {h}" for h in analysis.get('root_cause_hypothesis', []))}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommended Checks:*\n" + "\n".join(f"• {c}" for c in analysis.get('recommended_checks', [])[:3])}
            }
        ]
    }
    
    # Determine next steps
    if analysis["escalation_required"]:
        response["next_steps"] = [
            "Page on-call engineer immediately",
            "Initiate incident bridge call",
            "Prepare for potential rollback"
        ]
    else:
        response["next_steps"] = analysis.get("auto_remediation_actions", [])[:3]
    
    # Mark as auto-remediated if actions were taken
    if analysis["auto_remediation_possible"] and not analysis["escalation_required"]:
        response["auto_remediated"] = True
        response["actions_taken"] = [f"Auto-remediation initiated: {analysis['auto_remediation_actions'][0]}"]
    
    return response


def handle_incident(body: Dict) -> Dict:
    """Handle incident response request - Analyze and respond to Datadog incidents"""
    
    incident_id = body.get('incident_id') or str(uuid.uuid4())
    incident_type = body.get('type') or body.get('incident_type', '')
    description = body.get('description', '')
    service = body.get('service', 'unknown')
    environment = body.get('environment', 'production')
    metrics = body.get('metrics', {})
    datadog_alert = body.get('datadog_alert', {})
    auto_remediate = body.get('auto_remediate', True)
    
    try:
        # Create incident data structure
        incident_data = {
            "incident_id": incident_id,
            "type": incident_type,
            "description": description,
            "service": service,
            "environment": environment,
            "metrics": metrics,
            "datadog_alert": datadog_alert,
            "timestamp": datetime.now().isoformat()
        }
        
        # Analyze incident
        analysis = analyze_incident(incident_data)
        
        # Generate response
        response = generate_incident_response(incident_data, analysis)
        
        # If auto-remediation is enabled and possible, simulate taking action
        remediation_status = None
        if auto_remediate and analysis["auto_remediation_possible"] and not analysis["escalation_required"]:
            remediation_status = {
                "action": analysis["auto_remediation_actions"][0] if analysis["auto_remediation_actions"] else None,
                "status": "initiated",
                "timestamp": datetime.now().isoformat(),
                "estimated_resolution": "5-10 minutes"
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'incident_id': incident_id,
                'incident_data': incident_data,
                'analysis': analysis,
                'response': response,
                'remediation': remediation_status,
                'summary': {
                    'incident_type': analysis.get('incident_type'),
                    'severity': analysis.get('severity'),
                    'auto_remediated': response.get('auto_remediated', False),
                    'escalation_required': analysis.get('escalation_required', False)
                }
            })
        }
        
    except Exception as e:
        logger.error(f"Incident response error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ============================================================================
# SECURITY REMEDIATION AGENT
# Auto-fix Prisma Cloud and SonarQube security findings
# ============================================================================

SECURITY_REMEDIATIONS = {
    "sql_injection": {
        "severity": "critical",
        "cwe": "CWE-89",
        "description": "SQL Injection vulnerability",
        "remediation_patterns": {
            "nodejs": {
                "vulnerable": r"query\(['\"].*\+.*['\"]|query\(`.*\$\{",
                "fix": "Use parameterized queries: db.query('SELECT * FROM users WHERE id = ?', [userId])",
                "example_before": "db.query(`SELECT * FROM users WHERE id = ${userId}`)",
                "example_after": "db.query('SELECT * FROM users WHERE id = ?', [userId])"
            },
            "python": {
                "vulnerable": r"execute\(['\"].*%.*['\"]|execute\(f['\"]",
                "fix": "Use parameterized queries: cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))",
                "example_before": "cursor.execute(f'SELECT * FROM users WHERE id = {user_id}')",
                "example_after": "cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))"
            },
            "java": {
                "vulnerable": r"createQuery\(['\"].*\+",
                "fix": "Use PreparedStatement with parameter binding",
                "example_before": "statement.executeQuery(\"SELECT * FROM users WHERE id = \" + userId)",
                "example_after": "PreparedStatement ps = conn.prepareStatement(\"SELECT * FROM users WHERE id = ?\"); ps.setInt(1, userId);"
            }
        }
    },
    "xss": {
        "severity": "high",
        "cwe": "CWE-79",
        "description": "Cross-Site Scripting (XSS) vulnerability",
        "remediation_patterns": {
            "nodejs": {
                "vulnerable": r"innerHTML\s*=|dangerouslySetInnerHTML",
                "fix": "Use textContent or sanitize HTML with DOMPurify",
                "example_before": "element.innerHTML = userInput",
                "example_after": "element.textContent = userInput // or DOMPurify.sanitize(userInput)"
            },
            "python": {
                "vulnerable": r"Markup\(|safe\s*=\s*True|\|safe",
                "fix": "Use proper escaping or sanitization",
                "example_before": "return Markup(user_input)",
                "example_after": "return escape(user_input)"
            }
        }
    },
    "hardcoded_secret": {
        "severity": "critical",
        "cwe": "CWE-798",
        "description": "Hardcoded credentials or secrets",
        "remediation_patterns": {
            "generic": {
                "vulnerable": r"password\s*=\s*['\"][^'\"]+['\"]|api_key\s*=\s*['\"][^'\"]+['\"]|secret\s*=\s*['\"][^'\"]+['\"]",
                "fix": "Use environment variables or secrets manager",
                "example_before": "password = 'hardcoded_password'",
                "example_after": "password = os.environ.get('DB_PASSWORD') # or use AWS Secrets Manager"
            }
        }
    },
    "insecure_deserialization": {
        "severity": "critical",
        "cwe": "CWE-502",
        "description": "Insecure deserialization vulnerability",
        "remediation_patterns": {
            "python": {
                "vulnerable": r"pickle\.loads|yaml\.load\(",
                "fix": "Use safe loading methods",
                "example_before": "data = pickle.loads(user_input)",
                "example_after": "data = json.loads(user_input) # Use JSON instead of pickle for user input"
            },
            "nodejs": {
                "vulnerable": r"serialize-javascript|node-serialize",
                "fix": "Avoid deserializing untrusted data",
                "example_before": "serialize.unserialize(userInput)",
                "example_after": "JSON.parse(userInput) // Validate input before parsing"
            }
        }
    },
    "path_traversal": {
        "severity": "high",
        "cwe": "CWE-22",
        "description": "Path traversal vulnerability",
        "remediation_patterns": {
            "nodejs": {
                "vulnerable": r"readFileSync\(.*\+|readFile\(.*\+",
                "fix": "Use path.join and validate paths",
                "example_before": "fs.readFileSync('/uploads/' + userFile)",
                "example_after": "const safePath = path.join('/uploads', path.basename(userFile)); fs.readFileSync(safePath)"
            },
            "python": {
                "vulnerable": r"open\(.*\+|read\(.*\+",
                "fix": "Use os.path.join and validate paths",
                "example_before": "open('/uploads/' + user_file)",
                "example_after": "safe_path = os.path.join('/uploads', os.path.basename(user_file)); open(safe_path)"
            }
        }
    },
    "weak_crypto": {
        "severity": "medium",
        "cwe": "CWE-327",
        "description": "Use of weak cryptographic algorithm",
        "remediation_patterns": {
            "generic": {
                "vulnerable": r"MD5|SHA1|DES|RC4",
                "fix": "Use strong algorithms like SHA-256, AES-256",
                "example_before": "hashlib.md5(password.encode())",
                "example_after": "hashlib.sha256(password.encode())"
            }
        }
    },
    "missing_authentication": {
        "severity": "high",
        "cwe": "CWE-306",
        "description": "Missing authentication for critical function",
        "remediation_patterns": {
            "nodejs": {
                "fix": "Add authentication middleware",
                "example_after": "router.post('/admin/delete', authMiddleware, adminController.delete)"
            },
            "python": {
                "fix": "Add @login_required decorator",
                "example_after": "@login_required\ndef admin_delete(request): ..."
            }
        }
    }
}

SONARQUBE_RULES = {
    "S1481": {"name": "Unused local variables", "severity": "minor", "auto_fix": True},
    "S1144": {"name": "Unused private methods", "severity": "major", "auto_fix": True},
    "S1186": {"name": "Empty methods", "severity": "major", "auto_fix": False},
    "S2068": {"name": "Hardcoded credentials", "severity": "blocker", "auto_fix": True},
    "S2077": {"name": "SQL injection", "severity": "blocker", "auto_fix": True},
    "S2631": {"name": "Regular expressions DoS", "severity": "major", "auto_fix": False},
    "S4790": {"name": "Weak hashing", "severity": "critical", "auto_fix": True},
    "S5131": {"name": "XSS", "severity": "blocker", "auto_fix": True},
    "S5443": {"name": "Insecure temporary file", "severity": "major", "auto_fix": True},
    "S5542": {"name": "Weak encryption", "severity": "blocker", "auto_fix": True}
}


def analyze_security_finding(finding: Dict[str, Any], language: str = "generic") -> Dict[str, Any]:
    """Analyze a security finding and determine remediation"""
    
    finding_type = finding.get('type', '').lower().replace(' ', '_').replace('-', '_')
    rule_id = finding.get('rule_id', finding.get('ruleId', ''))
    file_path = finding.get('file', finding.get('filePath', ''))
    line_number = finding.get('line', finding.get('lineNumber', 0))
    code_snippet = finding.get('code', finding.get('snippet', ''))
    
    analysis = {
        "finding_type": finding_type,
        "rule_id": rule_id,
        "file": file_path,
        "line": line_number,
        "severity": "medium",
        "can_auto_fix": False,
        "remediation": None,
        "fix_code": None,
        "pr_description": None
    }
    
    # Match against known remediations
    for vuln_type, vuln_data in SECURITY_REMEDIATIONS.items():
        if vuln_type in finding_type or finding_type in vuln_type:
            analysis["severity"] = vuln_data.get("severity", "medium")
            analysis["cwe"] = vuln_data.get("cwe")
            analysis["description"] = vuln_data.get("description")
            
            # Get language-specific remediation
            patterns = vuln_data.get("remediation_patterns", {})
            lang_pattern = patterns.get(language, patterns.get("generic", {}))
            
            if lang_pattern:
                analysis["remediation"] = lang_pattern.get("fix")
                analysis["example_before"] = lang_pattern.get("example_before")
                analysis["example_after"] = lang_pattern.get("example_after")
                analysis["can_auto_fix"] = True
            break
    
    # Check SonarQube rules
    if rule_id and rule_id in SONARQUBE_RULES:
        rule = SONARQUBE_RULES[rule_id]
        analysis["sonar_rule"] = rule.get("name")
        analysis["can_auto_fix"] = rule.get("auto_fix", False)
    
    # Generate PR description
    if analysis["can_auto_fix"]:
        analysis["pr_description"] = f"""## Security Fix: {analysis.get('description', finding_type)}

### Vulnerability Details
- **Type**: {finding_type}
- **Severity**: {analysis['severity'].upper()}
- **CWE**: {analysis.get('cwe', 'N/A')}
- **File**: {file_path}:{line_number}

### Remediation
{analysis.get('remediation', 'Manual review required')}

### Before
```
{analysis.get('example_before', code_snippet)}
```

### After
```
{analysis.get('example_after', 'See remediation guidance')}
```

---
*Generated by BCG DevOps GenAI Security Agent*
"""
    
    return analysis


def generate_security_fix_pr(findings: List[Dict], repo_url: str, language: str) -> Dict[str, Any]:
    """Generate a PR with security fixes"""
    
    analyzed_findings = []
    auto_fixable = []
    manual_review = []
    
    for finding in findings:
        analysis = analyze_security_finding(finding, language)
        analyzed_findings.append({**finding, "analysis": analysis})
        
        if analysis["can_auto_fix"]:
            auto_fixable.append(analysis)
        else:
            manual_review.append(analysis)
    
    pr_body = f"""## 🔒 Security Remediation - Automated Fix

### Summary
- **Total Findings**: {len(findings)}
- **Auto-Fixed**: {len(auto_fixable)}
- **Manual Review Required**: {len(manual_review)}

### Auto-Fixed Issues
"""
    
    for i, fix in enumerate(auto_fixable, 1):
        pr_body += f"""
#### {i}. {fix.get('description', fix.get('finding_type', 'Unknown'))}
- **Severity**: {fix.get('severity', 'medium').upper()}
- **File**: {fix.get('file', 'N/A')}:{fix.get('line', 'N/A')}
- **Remediation**: {fix.get('remediation', 'Applied standard fix')}
"""
    
    if manual_review:
        pr_body += "\n### ⚠️ Issues Requiring Manual Review\n"
        for issue in manual_review:
            pr_body += f"- {issue.get('description', issue.get('finding_type'))}: {issue.get('file', 'N/A')}\n"
    
    pr_body += """
---
*Generated by BCG DevOps GenAI Security Remediation Agent*
"""
    
    return {
        "analyzed_findings": analyzed_findings,
        "auto_fixable_count": len(auto_fixable),
        "manual_review_count": len(manual_review),
        "pr_title": f"fix(security): Remediate {len(auto_fixable)} security vulnerabilities",
        "pr_body": pr_body,
        "branch_name": f"security-fix/{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    }


def handle_security_remediate(body: Dict) -> Dict:
    """Handle security remediation request - Analyze and fix security findings"""
    
    findings = body.get('findings', [])
    repo_url = body.get('repo_url', body.get('repository', ''))
    language = body.get('language', 'generic')
    source = body.get('source', 'unknown')  # prisma, sonarqube, trivy, etc.
    auto_create_pr = body.get('auto_create_pr', False)
    
    if not findings:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: findings (array of security findings)'})
        }
    
    try:
        # Generate fix PR content
        pr_data = generate_security_fix_pr(findings, repo_url, language)
        
        # Calculate statistics
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for finding in pr_data["analyzed_findings"]:
            sev = finding.get("analysis", {}).get("severity", "medium")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        
        result = {
            'success': True,
            'source': source,
            'statistics': {
                'total_findings': len(findings),
                'auto_fixable': pr_data['auto_fixable_count'],
                'manual_review': pr_data['manual_review_count'],
                'by_severity': severity_counts
            },
            'analyzed_findings': pr_data['analyzed_findings'],
            'pr_ready': {
                'title': pr_data['pr_title'],
                'body': pr_data['pr_body'],
                'branch': pr_data['branch_name']
            }
        }
        
        # If auto-create PR is enabled and repo_url provided
        if auto_create_pr and repo_url:
            try:
                owner, repo = parse_repo_url(repo_url)
                result['pr_creation'] = {
                    'status': 'ready',
                    'repository': f"{owner}/{repo}",
                    'message': 'PR can be created via /push endpoint with the generated content'
                }
            except:
                result['pr_creation'] = {'status': 'skipped', 'reason': 'Invalid repository URL'}
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Security remediation error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ============================================================================
# RCA REPORT GENERATOR
# Generate comprehensive Root Cause Analysis reports
# ============================================================================

RCA_TEMPLATE = """
# Root Cause Analysis Report

## Incident Overview
- **Incident ID**: {incident_id}
- **Service**: {service}
- **Environment**: {environment}
- **Start Time**: {start_time}
- **End Time**: {end_time}
- **Duration**: {duration}
- **Severity**: {severity}
- **Status**: {status}

## Executive Summary
{executive_summary}

## Timeline of Events
{timeline}

## Impact Assessment
### Business Impact
{business_impact}

### Technical Impact
{technical_impact}

### Users Affected
{users_affected}

## Root Cause Analysis

### Primary Root Cause
{primary_cause}

### Contributing Factors
{contributing_factors}

### 5 Whys Analysis
{five_whys}

## Resolution
### Immediate Actions Taken
{immediate_actions}

### Resolution Details
{resolution_details}

## Prevention & Recommendations

### Short-term Actions (1-2 weeks)
{short_term_actions}

### Long-term Actions (1-3 months)
{long_term_actions}

### Process Improvements
{process_improvements}

## Lessons Learned
{lessons_learned}

## Appendix
### Related Logs
{related_logs}

### Metrics During Incident
{metrics_data}

### Related Tickets
{related_tickets}

---
*Report Generated: {generated_at}*
*Generated by BCG DevOps GenAI RCA Agent*
"""


def generate_rca_report(incident_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a comprehensive RCA report using AI"""
    
    incident_id = incident_data.get('incident_id', str(uuid.uuid4()))
    service = incident_data.get('service', 'Unknown Service')
    environment = incident_data.get('environment', 'production')
    start_time = incident_data.get('start_time', datetime.now().isoformat())
    end_time = incident_data.get('end_time', datetime.now().isoformat())
    severity = incident_data.get('severity', 'high')
    description = incident_data.get('description', '')
    symptoms = incident_data.get('symptoms', [])
    actions_taken = incident_data.get('actions_taken', [])
    metrics = incident_data.get('metrics', {})
    logs = incident_data.get('logs', [])
    
    # Calculate duration
    try:
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
        duration = f"{duration_minutes} minutes"
    except:
        duration = "Unknown"
    
    # Generate 5 Whys based on symptoms
    five_whys = []
    if symptoms:
        five_whys = [
            f"1. Why did {symptoms[0] if symptoms else 'the issue'} occur?\n   - Initial trigger detected in monitoring",
            "2. Why was this not caught earlier?\n   - Monitoring thresholds may need adjustment",
            "3. Why were the thresholds not appropriate?\n   - Based on historical data that may be outdated",
            "4. Why was historical data not updated?\n   - No regular review process in place",
            "5. Why is there no review process?\n   - Need to implement quarterly threshold reviews"
        ]
    
    # Generate timeline from actions
    timeline_entries = []
    for i, action in enumerate(actions_taken):
        timeline_entries.append(f"- **T+{i*5}m**: {action}")
    timeline = "\n".join(timeline_entries) if timeline_entries else "- Timeline data not provided"
    
    # Build the report
    report_data = {
        "incident_id": incident_id,
        "service": service,
        "environment": environment,
        "start_time": start_time,
        "end_time": end_time,
        "duration": duration,
        "severity": severity.upper(),
        "status": "Resolved",
        "executive_summary": f"On {start_time[:10]}, the {service} service experienced a {severity} severity incident lasting {duration}. {description}",
        "timeline": timeline,
        "business_impact": incident_data.get('business_impact', 'Impact assessment pending'),
        "technical_impact": incident_data.get('technical_impact', f"Service degradation in {service}"),
        "users_affected": incident_data.get('users_affected', 'To be determined based on service metrics'),
        "primary_cause": incident_data.get('root_cause', 'Root cause analysis in progress'),
        "contributing_factors": "\n".join(f"- {f}" for f in incident_data.get('contributing_factors', ['Analysis pending'])),
        "five_whys": "\n".join(five_whys) if five_whys else "5 Whys analysis pending",
        "immediate_actions": "\n".join(f"- {a}" for a in actions_taken) if actions_taken else "- Immediate response actions documented",
        "resolution_details": incident_data.get('resolution', 'Resolution details pending'),
        "short_term_actions": "\n".join([
            "- [ ] Review and update monitoring thresholds",
            "- [ ] Add additional alerting for early detection",
            "- [ ] Update runbooks with lessons learned"
        ]),
        "long_term_actions": "\n".join([
            "- [ ] Implement automated remediation for this failure mode",
            "- [ ] Review architecture for resilience improvements",
            "- [ ] Conduct chaos engineering tests"
        ]),
        "process_improvements": "\n".join([
            "- Implement post-incident review process",
            "- Add this scenario to on-call training",
            "- Update incident response playbooks"
        ]),
        "lessons_learned": incident_data.get('lessons_learned', '- Post-incident review scheduled'),
        "related_logs": "\n".join(f"```\n{log}\n```" for log in logs[:5]) if logs else "No logs attached",
        "metrics_data": json.dumps(metrics, indent=2) if metrics else "No metrics attached",
        "related_tickets": incident_data.get('tickets', 'No related tickets'),
        "generated_at": datetime.now().isoformat()
    }
    
    # Generate markdown report
    report_markdown = RCA_TEMPLATE.format(**report_data)
    
    return {
        "report_markdown": report_markdown,
        "report_data": report_data,
        "summary": {
            "incident_id": incident_id,
            "service": service,
            "severity": severity,
            "duration": duration,
            "status": "Resolved"
        }
    }


def handle_rca(body: Dict) -> Dict:
    """Handle RCA report generation request"""
    
    incident_id = body.get('incident_id', str(uuid.uuid4()))
    service = body.get('service')
    
    if not service:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: service'})
        }
    
    try:
        # Generate RCA report
        rca_result = generate_rca_report(body)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'incident_id': incident_id,
                'summary': rca_result['summary'],
                'report': rca_result['report_markdown'],
                'structured_data': rca_result['report_data']
            })
        }
        
    except Exception as e:
        logger.error(f"RCA generation error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ============================================================================
# ARGOCD MANIFEST GENERATOR
# Generate ArgoCD Application manifests for GitOps deployments
# ============================================================================

ARGOCD_APP_TEMPLATE = """apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: {app_name}
  namespace: argocd
  labels:
    app.kubernetes.io/name: {app_name}
    app.kubernetes.io/part-of: {project}
    environment: {environment}
  annotations:
    notifications.argoproj.io/subscribe.on-sync-succeeded.slack: {slack_channel}
    notifications.argoproj.io/subscribe.on-sync-failed.slack: {slack_channel}
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: {project}
  source:
    repoURL: {repo_url}
    targetRevision: {target_revision}
    path: {manifest_path}
{helm_config}
  destination:
    server: {cluster_url}
    namespace: {namespace}
  syncPolicy:
    automated:
      prune: {auto_prune}
      selfHeal: {self_heal}
      allowEmpty: false
    syncOptions:
      - CreateNamespace=true
      - PrunePropagationPolicy=foreground
      - PruneLast=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
  revisionHistoryLimit: 10
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
"""

ARGOCD_APPSET_TEMPLATE = """apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: {appset_name}
  namespace: argocd
spec:
  generators:
    - list:
        elements:
{environment_list}
  template:
    metadata:
      name: '{{{{app_name}}}}-{{{{environment}}}}'
      namespace: argocd
      labels:
        app.kubernetes.io/name: '{{{{app_name}}}}'
        environment: '{{{{environment}}}}'
    spec:
      project: {project}
      source:
        repoURL: {repo_url}
        targetRevision: '{{{{branch}}}}'
        path: '{{{{path}}}}'
      destination:
        server: '{{{{cluster}}}}'
        namespace: '{{{{namespace}}}}'
      syncPolicy:
        automated:
          prune: true
          selfHeal: true
        syncOptions:
          - CreateNamespace=true
"""


def generate_argocd_manifest(config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate ArgoCD Application or ApplicationSet manifest"""
    
    app_name = config.get('app_name', 'my-app')
    repo_url = config.get('repo_url', '')
    manifest_path = config.get('manifest_path', 'k8s')
    target_revision = config.get('target_revision', 'HEAD')
    namespace = config.get('namespace', app_name)
    cluster_url = config.get('cluster_url', 'https://kubernetes.default.svc')
    project = config.get('project', 'default')
    environment = config.get('environment', 'production')
    environments = config.get('environments', [])
    slack_channel = config.get('slack_channel', 'deployments')
    auto_prune = str(config.get('auto_prune', True)).lower()
    self_heal = str(config.get('self_heal', True)).lower()
    use_helm = config.get('use_helm', False)
    helm_values_file = config.get('helm_values_file', f'values-{environment}.yaml')
    
    # Generate Helm configuration if needed
    helm_config = ""
    if use_helm:
        helm_config = f"""    helm:
      valueFiles:
        - {helm_values_file}
      parameters: []
"""
    else:
        helm_config = "    # Kustomize or plain YAML manifests"
    
    result = {
        "manifests": [],
        "files": [],
        "instructions": []
    }
    
    # Generate ApplicationSet for multiple environments
    if environments and len(environments) > 1:
        env_list = []
        for env in environments:
            env_config = env if isinstance(env, dict) else {"name": env}
            env_name = env_config.get('name', env)
            env_list.append(f"""          - app_name: {app_name}
            environment: {env_name}
            cluster: {env_config.get('cluster', cluster_url)}
            namespace: {env_config.get('namespace', f'{app_name}-{env_name}')}
            branch: {env_config.get('branch', 'main' if env_name == 'production' else env_name)}
            path: {env_config.get('path', f'{manifest_path}/{env_name}')}""")
        
        appset_manifest = ARGOCD_APPSET_TEMPLATE.format(
            appset_name=f"{app_name}-appset",
            project=project,
            repo_url=repo_url,
            environment_list="\n".join(env_list)
        )
        
        result["manifests"].append({
            "type": "ApplicationSet",
            "name": f"{app_name}-appset",
            "content": appset_manifest
        })
        result["files"].append({
            "filename": f"argocd/{app_name}-appset.yaml",
            "content": appset_manifest
        })
        
    else:
        # Generate single Application
        app_manifest = ARGOCD_APP_TEMPLATE.format(
            app_name=app_name,
            project=project,
            repo_url=repo_url,
            target_revision=target_revision,
            manifest_path=manifest_path,
            cluster_url=cluster_url,
            namespace=namespace,
            environment=environment,
            slack_channel=slack_channel,
            auto_prune=auto_prune,
            self_heal=self_heal,
            helm_config=helm_config
        )
        
        result["manifests"].append({
            "type": "Application",
            "name": app_name,
            "content": app_manifest
        })
        result["files"].append({
            "filename": f"argocd/{app_name}-app.yaml",
            "content": app_manifest
        })
    
    # Add instructions
    result["instructions"] = [
        f"1. Create the ArgoCD Application by running: kubectl apply -f argocd/{app_name}-app.yaml",
        "2. Verify the application in ArgoCD UI or CLI: argocd app get " + app_name,
        "3. Sync the application: argocd app sync " + app_name,
        "4. Configure Slack notifications webhook in ArgoCD ConfigMap",
        "5. Set up RBAC if using non-default project"
    ]
    
    return result


def handle_argocd_manifest(body: Dict) -> Dict:
    """Handle ArgoCD manifest generation request"""
    
    app_name = body.get('app_name', body.get('name'))
    repo_url = body.get('repo_url', body.get('repository'))
    
    if not app_name:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Missing required field: app_name'})
        }
    
    try:
        # Generate manifests
        result = generate_argocd_manifest(body)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'app_name': app_name,
                'manifests': result['manifests'],
                'files': result['files'],
                'instructions': result['instructions']
            })
        }
        
    except Exception as e:
        logger.error(f"ArgoCD manifest generation error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ============================================================================
# GITHUB ACTIONS REUSABLE WORKFLOW GENERATOR
# Generate BCG-standard reusable workflows
# ============================================================================

def generate_reusable_workflow(workflow_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Generate BCG-standard reusable GitHub Actions workflow"""
    
    workflows = {
        "security-scan": {
            "name": "BCG Security Scan",
            "filename": "security-scan.yml",
            "content": """name: BCG Security Scan
on:
  workflow_call:
    inputs:
      scan_type:
        description: 'Type of security scan (sast, sca, container, all)'
        required: false
        type: string
        default: 'all'
      fail_on_critical:
        description: 'Fail workflow on critical findings'
        required: false
        type: boolean
        default: true
    secrets:
      PRISMA_API_URL:
        required: true
      PRISMA_ACCESS_KEY:
        required: true

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Gitleaks Secret Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Trivy Vulnerability Scan
        if: inputs.scan_type == 'all' || inputs.scan_type == 'sca'
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Prisma Cloud SAST
        if: inputs.scan_type == 'all' || inputs.scan_type == 'sast'
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          soft_fail: ${{ !inputs.fail_on_critical }}
        env:
          BC_API_KEY: ${{ secrets.PRISMA_ACCESS_KEY }}
      
      - name: Upload Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
"""
        },
        "build-push": {
            "name": "BCG Build & Push",
            "filename": "build-push.yml",
            "content": """name: BCG Build & Push
on:
  workflow_call:
    inputs:
      image_name:
        required: true
        type: string
      dockerfile:
        required: false
        type: string
        default: 'Dockerfile'
      context:
        required: false
        type: string
        default: '.'
    secrets:
      JFROG_ARTIFACTORY_URL:
        required: true
      JFROG_USER:
        required: true
      JFROG_ACCESS_TOKEN:
        required: true
    outputs:
      image_tag:
        description: 'The built image tag'
        value: ${{ jobs.build.outputs.tag }}

jobs:
  build:
    runs-on: ubuntu-latest
    outputs:
      tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to JFrog
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.JFROG_ARTIFACTORY_URL }}
          username: ${{ secrets.JFROG_USER }}
          password: ${{ secrets.JFROG_ACCESS_TOKEN }}
      
      - name: Docker Meta
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ secrets.JFROG_ARTIFACTORY_URL }}/${{ inputs.image_name }}
          tags: |
            type=sha
            type=ref,event=branch
            type=semver,pattern={{version}}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: ${{ inputs.context }}
          file: ${{ inputs.dockerfile }}
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
"""
        },
        "deploy-argocd": {
            "name": "BCG Deploy ArgoCD",
            "filename": "deploy-argocd.yml",
            "content": """name: BCG Deploy ArgoCD
on:
  workflow_call:
    inputs:
      app_name:
        required: true
        type: string
      image_tag:
        required: true
        type: string
      environment:
        required: false
        type: string
        default: 'staging'
    secrets:
      ARGOCD_SERVER:
        required: true
      ARGOCD_USERNAME:
        required: true
      ARGOCD_PASSWORD:
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - name: Install ArgoCD CLI
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          sudo mv argocd /usr/local/bin/
      
      - name: Login to ArgoCD
        run: |
          argocd login ${{ secrets.ARGOCD_SERVER }} \\
            --username ${{ secrets.ARGOCD_USERNAME }} \\
            --password ${{ secrets.ARGOCD_PASSWORD }} \\
            --insecure
      
      - name: Update Image Tag
        run: |
          argocd app set ${{ inputs.app_name }} \\
            --helm-set image.tag=${{ inputs.image_tag }}
      
      - name: Sync Application
        run: |
          argocd app sync ${{ inputs.app_name }} --prune
      
      - name: Wait for Rollout
        run: |
          argocd app wait ${{ inputs.app_name }} --timeout 300
"""
        },
        "quality-gate": {
            "name": "BCG Quality Gate",
            "filename": "quality-gate.yml",
            "content": """name: BCG Quality Gate
on:
  workflow_call:
    inputs:
      language:
        required: true
        type: string
        description: 'Programming language (nodejs, python, java, golang, dotnet)'
    secrets:
      SONAR_TOKEN:
        required: true
      SONAR_HOST_URL:
        required: true

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: SonarQube Scan
        uses: sonarsource/sonarqube-scan-action@v2
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
          SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
        with:
          args: >
            -Dsonar.projectKey=${{ github.repository_owner }}_${{ github.event.repository.name }}
      
      - name: Quality Gate Check
        uses: sonarsource/sonarqube-quality-gate-action@v1
        timeout-minutes: 5
        env:
          SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
"""
        }
    }
    
    if workflow_type not in workflows:
        return {
            "error": f"Unknown workflow type: {workflow_type}",
            "available_types": list(workflows.keys())
        }
    
    workflow = workflows[workflow_type]
    return {
        "name": workflow["name"],
        "filename": workflow["filename"],
        "content": workflow["content"],
        "usage_example": f"""
# In your calling workflow:
jobs:
  call-{workflow_type}:
    uses: ./.github/workflows/{workflow["filename"]}
    with:
      # Add required inputs
    secrets: inherit
"""
    }


def handle_reusable_workflow(body: Dict) -> Dict:
    """Handle reusable workflow generation request"""
    
    workflow_type = body.get('type', body.get('workflow_type', ''))
    
    available_types = ["security-scan", "build-push", "deploy-argocd", "quality-gate"]
    
    if not workflow_type:
        return {
            'statusCode': 200,
            'body': json.dumps({
                'available_workflows': available_types,
                'message': 'Specify workflow type with "type" parameter'
            })
        }
    
    try:
        result = generate_reusable_workflow(workflow_type, body)
        
        if "error" in result:
            return {
                'statusCode': 400,
                'body': json.dumps(result)
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'success': True,
                'workflow_type': workflow_type,
                'workflow': result
            })
        }
        
    except Exception as e:
        logger.error(f"Reusable workflow generation error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# ============================================================================
# LAMBDA HANDLER
# ============================================================================

def handler(event, context):
    """Main Lambda handler"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # CORS headers
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-Amz-Date,X-Api-Key',
        'Access-Control-Allow-Methods': 'GET,POST,OPTIONS'
    }
    
    # Get request info
    raw_path = event.get('rawPath', event.get('path', ''))
    http_method = event.get('requestContext', {}).get('http', {}).get('method', 
                  event.get('httpMethod', 'GET'))
    
    # Handle CORS preflight
    if http_method == 'OPTIONS':
        return {'statusCode': 200, 'headers': headers, 'body': ''}
    
    # Handle health check
    if 'health' in raw_path:
        result = handle_health()
        return {**result, 'headers': headers}
    
    # Parse request body
    try:
        if event.get('body'):
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        else:
            body = event
    except json.JSONDecodeError as e:
        return {
            'statusCode': 400,
            'headers': headers,
            'body': json.dumps({'error': f'Invalid JSON: {str(e)}'})
        }
    
    # Route request to appropriate handler
    try:
        if 'autonomous' in raw_path:
            # Full autonomous agent: detect -> generate -> push -> track -> heal
            result = handle_autonomous(body)
        elif 'detect' in raw_path:
            # Auto-detect language/framework from repository
            result = handle_detect(body)
        elif 'push' in raw_path:
            # Push workflow to GitHub and create PR
            result = handle_push(body)
        elif 'track' in raw_path:
            # Track pipeline execution status
            result = handle_track(body)
        elif 'heal' in raw_path:
            # Auto-heal failed pipeline
            result = handle_heal(body)
        elif 'tools' in raw_path:
            # Get available tools information
            result = handle_tools_info(body)
        elif 'incident' in raw_path:
            # Datadog Incident Response Agent
            result = handle_incident(body)
        elif 'security-remediate' in raw_path:
            # Security Remediation Agent (Prisma/SonarQube)
            result = handle_security_remediate(body)
        elif 'rca' in raw_path:
            # RCA Report Generator
            result = handle_rca(body)
        elif 'argocd-manifest' in raw_path:
            # ArgoCD Manifest Generator
            result = handle_argocd_manifest(body)
        elif 'reusable-workflow' in raw_path:
            # Reusable Workflow Generator
            result = handle_reusable_workflow(body)
        elif 'generate' in raw_path or http_method == 'POST':
            # Generate workflow (default POST behavior)
            result = handle_generate(body)
        else:
            # Default: return API info
            result = {
                'statusCode': 200,
                'body': json.dumps({
                    'service': 'BCG DevOps GenAI Autonomous Agent',
                    'version': '3.0.0',
                    'endpoints': {
                        '/health': 'GET - Health check',
                        '/generate': 'POST - Generate CI/CD workflow',
                        '/autonomous': 'POST - Full autonomous agent (detect + generate + push + track + heal)',
                        '/detect': 'POST - Auto-detect repository language/framework',
                        '/push': 'POST - Push workflow to GitHub',
                        '/track': 'POST - Track pipeline execution',
                        '/heal': 'POST - Auto-heal failed pipeline',
                        '/tools': 'GET - List available tools',
                        '/incident': 'POST - Datadog incident response agent',
                        '/security-remediate': 'POST - Security remediation (Prisma/SonarQube)',
                        '/rca': 'POST - Root Cause Analysis report generator',
                        '/argocd-manifest': 'POST - ArgoCD manifest generator',
                        '/reusable-workflow': 'POST - Generate reusable workflows'
                    },
                    'capabilities': [
                        'Auto-detect language and framework',
                        'Generate BCG-compliant workflows',
                        'Push to GitHub and create PRs',
                        'Monitor pipeline execution',
                        'Auto-heal failed pipelines',
                        'Multi-language support (Node.js, Python, Go, Java, .NET)',
                        'Datadog incident response and auto-remediation',
                        'Security vulnerability remediation',
                        'Root Cause Analysis reporting',
                        'ArgoCD GitOps manifest generation',
                        'Reusable workflow templates'
                    ]
                })
            }
    except Exception as e:
        logger.error(f"Handler error: {str(e)}")
        result = {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    
    return {**result, 'headers': headers}
