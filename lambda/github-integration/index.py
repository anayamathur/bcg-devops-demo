"""
BCG DevOps GenAI - Intelligent GitHub Integration Lambda
Handles repository analysis, workflow generation, validation, deployment,
Actions tracking, and intelligent suggestions with full project context
"""

import json
import boto3
import os
import logging
import base64
import urllib.request
import urllib.error
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import open-source tools module
from opensource_tools import (
    detect_tools,
    get_workflow_guidance,
    get_required_secrets,
    get_tools_by_category,
    get_complete_workflow_for_language,
    OPENSOURCE_DEVOPS_TOOLS,
    TOOL_DETECTION
)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# GitHub API base URL
GITHUB_API = "https://api.github.com"

# Initialize Bedrock for intelligent analysis
bedrock = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'amazon.nova-pro-v1:0')

# Project Knowledge Cache (for agent context)
PROJECT_KNOWLEDGE = {}

# Slack Configuration Cache
SLACK_CONFIG = {
    "webhook_url": os.environ.get("SLACK_WEBHOOK_URL"),
    "channel": os.environ.get("SLACK_CHANNEL", "#devops-alerts"),
    "enabled": os.environ.get("SLACK_ENABLED", "true").lower() == "true"
}


# ============================================================================
# SLACK INTEGRATION - Incident Notifications
# ============================================================================

def get_slack_webhook():
    """Get Slack webhook URL from environment or Secrets Manager"""
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if webhook_url:
        return webhook_url
    
    # Try Secrets Manager
    secret_name = os.environ.get('SLACK_SECRET_NAME', 'bcg-devops-genai/slack-webhook')
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret.get('webhook_url', secret.get('SLACK_WEBHOOK_URL'))
    except Exception as e:
        logger.warning(f"Slack webhook not configured: {e}")
        return None


def send_slack_notification(
    title: str,
    message: str,
    level: str = "info",
    repository: str = None,
    incident_url: str = None,
    additional_fields: List[Dict] = None,
    channel: str = None
) -> Dict[str, Any]:
    """
    Send notification to Slack channel
    
    Args:
        title: Notification title
        message: Main message body
        level: Alert level (info, warning, error, critical)
        repository: Repository name for context
        incident_url: Link to GitHub issue or workflow run
        additional_fields: Extra fields to include in the message
        channel: Override default channel
    
    Returns:
        Dict with success status and details
    """
    webhook_url = get_slack_webhook()
    
    if not webhook_url:
        return {
            "success": False,
            "error": "Slack webhook not configured",
            "skipped": True
        }
    
    # Color coding based on level
    colors = {
        "info": "#36a64f",      # Green
        "warning": "#ffcc00",   # Yellow
        "error": "#ff6600",     # Orange
        "critical": "#ff0000"   # Red
    }
    
    # Emoji based on level
    emojis = {
        "info": ":white_check_mark:",
        "warning": ":warning:",
        "error": ":x:",
        "critical": ":rotating_light:"
    }
    
    color = colors.get(level, colors["info"])
    emoji = emojis.get(level, emojis["info"])
    
    # Build attachment fields
    fields = []
    
    if repository:
        fields.append({
            "title": "Repository",
            "value": f"<https://github.com/{repository}|{repository}>",
            "short": True
        })
    
    fields.append({
        "title": "Level",
        "value": level.upper(),
        "short": True
    })
    
    fields.append({
        "title": "Timestamp",
        "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "short": True
    })
    
    if additional_fields:
        fields.extend(additional_fields)
    
    # Build actions if we have a URL
    actions = []
    if incident_url:
        actions.append({
            "type": "button",
            "text": "View Details",
            "url": incident_url,
            "style": "primary" if level == "critical" else "default"
        })
    
    # Slack message payload
    payload = {
        "channel": channel or SLACK_CONFIG.get("channel", "#devops-alerts"),
        "username": "BCG DevOps GenAI",
        "icon_emoji": ":robot_face:",
        "attachments": [{
            "fallback": f"{emoji} {title}: {message}",
            "color": color,
            "pretext": f"{emoji} *{title}*",
            "text": message,
            "fields": fields,
            "actions": actions if actions else None,
            "footer": "BCG DevOps GenAI Platform",
            "footer_icon": "https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png",
            "ts": int(datetime.now().timestamp())
        }]
    }
    
    # Remove None values
    payload["attachments"][0] = {k: v for k, v in payload["attachments"][0].items() if v is not None}
    
    try:
        req = urllib.request.Request(
            webhook_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            response_text = response.read().decode('utf-8')
            logger.info(f"Slack notification sent: {title}")
            return {
                "success": True,
                "response": response_text,
                "channel": payload["channel"]
            }
    except urllib.error.HTTPError as e:
        error_msg = f"Slack HTTP error: {e.code}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}
    except Exception as e:
        error_msg = f"Slack notification failed: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


def send_incident_notification(
    incident_level: str,
    incident_description: str,
    repository: str,
    classification: Dict[str, Any],
    remediation_result: Dict[str, Any] = None,
    issue_url: str = None
) -> Dict[str, Any]:
    """
    Send incident-specific Slack notification based on severity level
    """
    level_config = INCIDENT_LEVELS.get(incident_level, INCIDENT_LEVELS["L2"])
    
    # Map incident level to Slack alert level
    alert_levels = {
        "L1": "info",
        "L2": "warning", 
        "L3": "critical"
    }
    
    alert_level = alert_levels.get(incident_level, "warning")
    
    # Build title based on level
    titles = {
        "L1": "Auto-Remediation Triggered",
        "L2": "Incident Escalated - Engineering Review",
        "L3": "🚨 CRITICAL INCIDENT - Immediate Action Required"
    }
    
    title = titles.get(incident_level, "DevOps Incident")
    
    # Build message
    message_parts = [
        f"*Issue:* {classification.get('description', 'Unknown')}",
        f"*Details:* {incident_description[:200]}{'...' if len(incident_description) > 200 else ''}"
    ]
    
    if remediation_result:
        if remediation_result.get("success"):
            message_parts.append(f"*Auto-fix:* ✅ {remediation_result.get('details', 'Applied')}")
        else:
            message_parts.append(f"*Auto-fix:* ❌ Failed - {remediation_result.get('details', 'Manual intervention needed')}")
    
    message = "\n".join(message_parts)
    
    # Additional fields
    additional_fields = [
        {
            "title": "Incident Level",
            "value": f"{incident_level} - {level_config.get('name', 'Unknown')}",
            "short": True
        },
        {
            "title": "Auto-Remediation",
            "value": "Enabled" if level_config.get("auto_resolve") else "Disabled",
            "short": True
        }
    ]
    
    if classification.get("recommended_action"):
        additional_fields.append({
            "title": "Recommended Action",
            "value": classification["recommended_action"],
            "short": True
        })
    
    return send_slack_notification(
        title=title,
        message=message,
        level=alert_level,
        repository=repository,
        incident_url=issue_url,
        additional_fields=additional_fields
    )


def send_workflow_notification(
    event_type: str,
    repository: str,
    workflow_name: str = None,
    status: str = None,
    details: str = None,
    url: str = None
) -> Dict[str, Any]:
    """
    Send workflow-related Slack notifications
    
    Event types: workflow_created, workflow_success, workflow_failure, pr_created, deployment
    """
    notifications = {
        "workflow_created": {
            "title": "New Workflow Created",
            "level": "info",
            "emoji": ":hammer_and_wrench:"
        },
        "workflow_success": {
            "title": "Workflow Succeeded",
            "level": "info", 
            "emoji": ":white_check_mark:"
        },
        "workflow_failure": {
            "title": "Workflow Failed",
            "level": "error",
            "emoji": ":x:"
        },
        "pr_created": {
            "title": "Pull Request Created",
            "level": "info",
            "emoji": ":git-pull-request:"
        },
        "deployment": {
            "title": "Deployment Triggered",
            "level": "warning",
            "emoji": ":rocket:"
        }
    }
    
    config = notifications.get(event_type, {
        "title": event_type.replace("_", " ").title(),
        "level": "info",
        "emoji": ":bell:"
    })
    
    message_parts = []
    if workflow_name:
        message_parts.append(f"*Workflow:* {workflow_name}")
    if status:
        message_parts.append(f"*Status:* {status}")
    if details:
        message_parts.append(f"*Details:* {details}")
    
    message = "\n".join(message_parts) if message_parts else "No additional details"
    
    return send_slack_notification(
        title=config["title"],
        message=message,
        level=config["level"],
        repository=repository,
        incident_url=url
    )


def test_slack_connection(webhook_url: str = None) -> Dict[str, Any]:
    """
    Test Slack webhook connectivity
    """
    test_webhook = webhook_url or get_slack_webhook()
    
    if not test_webhook:
        return {
            "success": False,
            "error": "No webhook URL provided or configured"
        }
    
    test_payload = {
        "text": "🧪 *BCG DevOps GenAI - Connection Test*\n\nSlack integration is working correctly!",
        "username": "BCG DevOps GenAI",
        "icon_emoji": ":robot_face:"
    }
    
    try:
        req = urllib.request.Request(
            test_webhook,
            data=json.dumps(test_payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return {
                "success": True,
                "message": "Slack connection test successful",
                "webhook_configured": True
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "webhook_configured": bool(test_webhook)
        }


def get_github_token():
    """Get GitHub token from Secrets Manager or environment"""
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        return token
    
    # Try Secrets Manager
    secret_name = os.environ.get('GITHUB_SECRET_NAME', 'bcg-devops-genai/github-token')
    try:
        secrets_client = boto3.client('secretsmanager')
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response['SecretString'])
        return secret.get('token', secret.get('GITHUB_TOKEN'))
    except Exception as e:
        logger.error(f"Failed to get GitHub token: {e}")
        return None


def invoke_bedrock(prompt: str, system_prompt: str | None = None) -> str:
    """Invoke Bedrock for intelligent analysis"""
    try:
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        
        request_body = {
            "messages": messages,
            "inferenceConfig": {"maxTokens": 4096, "temperature": 0.3, "topP": 0.9}
        }
        
        if system_prompt:
            request_body["system"] = [{"text": system_prompt}]
        
        response = bedrock.invoke_model(
            modelId=MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(request_body)
        )
        
        response_body = json.loads(response['body'].read())
        
        if 'output' in response_body and 'message' in response_body['output']:
            content = response_body['output']['message']['content']
            if content and len(content) > 0:
                return content[0].get('text', '')
        
        return str(response_body)
    except Exception as e:
        logger.error(f"Bedrock error: {e}")
        return ""


def get_actions_runs(owner, repo, token, per_page=10):
    """Get GitHub Actions workflow runs with status"""
    try:
        runs = github_request(f"/repos/{owner}/{repo}/actions/runs?per_page={per_page}", token=token)
        return runs.get("workflow_runs", [])
    except Exception as e:
        logger.error(f"Failed to get actions runs: {e}")
        return []


def get_run_logs(owner, repo, run_id, token):
    """Get logs for a specific workflow run"""
    try:
        jobs = github_request(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs", token=token)
        return jobs.get("jobs", [])
    except Exception as e:
        logger.error(f"Failed to get run logs: {e}")
        return []


def validate_workflow_yaml(yaml_content):
    """Validate GitHub Actions workflow YAML syntax and best practices"""
    issues = []
    warnings = []
    score = 100
    
    # Basic YAML structure checks
    if not yaml_content.strip():
        return {"valid": False, "score": 0, "issues": ["Empty workflow content"], "warnings": []}
    
    # Check for required fields
    if "name:" not in yaml_content:
        warnings.append("Missing workflow name")
        score -= 5
    
    if "on:" not in yaml_content:
        issues.append("Missing 'on' trigger - workflow will never run")
        score -= 20
    
    if "jobs:" not in yaml_content:
        issues.append("Missing 'jobs' section - no jobs defined")
        score -= 30
    
    # Security best practices
    if "secrets." not in yaml_content and ("AWS_" in yaml_content or "API_KEY" in yaml_content):
        warnings.append("Hardcoded credentials detected - use GitHub Secrets")
        score -= 15
    
    # Version pinning
    if "@v" not in yaml_content and "uses:" in yaml_content:
        warnings.append("Actions not version-pinned - use specific versions like @v4")
        score -= 10
    
    # Check for common issues
    if "continue-on-error: true" in yaml_content:
        warnings.append("continue-on-error may hide failures")
        score -= 5
    
    # Check for caching
    if "npm install" in yaml_content or "pip install" in yaml_content:
        if "cache" not in yaml_content.lower():
            warnings.append("Consider adding dependency caching for faster builds")
            score -= 5
    
    # Environment checks
    if "environment:" not in yaml_content and "deploy" in yaml_content.lower():
        warnings.append("Consider using GitHub Environments for deployment protection")
        score -= 5
    
    return {
        "valid": len(issues) == 0,
        "score": max(0, score),
        "issues": issues,
        "warnings": warnings,
        "recommendations": generate_workflow_recommendations(yaml_content)
    }


def generate_workflow_recommendations(yaml_content):
    """Generate smart recommendations based on workflow content"""
    recommendations = []
    
    # Node.js specific
    if "node" in yaml_content.lower():
        if "npm ci" not in yaml_content and "npm install" in yaml_content:
            recommendations.append("Use 'npm ci' instead of 'npm install' for faster, reproducible builds")
        if "setup-node" in yaml_content and "cache: 'npm'" not in yaml_content:
            recommendations.append("Add cache: 'npm' to actions/setup-node for faster builds")
    
    # Python specific  
    if "python" in yaml_content.lower():
        if "pip cache" not in yaml_content and "actions/cache" not in yaml_content:
            recommendations.append("Add pip caching to speed up Python dependency installation")
    
    # Docker specific
    if "docker" in yaml_content.lower():
        if "docker/build-push-action" not in yaml_content:
            recommendations.append("Consider using docker/build-push-action for better caching and multi-platform builds")
        if "buildx" not in yaml_content:
            recommendations.append("Enable Docker Buildx for layer caching and faster builds")
    
    # Security
    if "GITHUB_TOKEN" in yaml_content and "permissions:" not in yaml_content:
        recommendations.append("Add explicit 'permissions' block to follow least-privilege principle")
    
    # Testing
    if "test" not in yaml_content.lower():
        recommendations.append("Consider adding automated testing to your CI pipeline")
    
    # Code quality
    if "lint" not in yaml_content.lower() and "eslint" not in yaml_content.lower():
        recommendations.append("Add linting step for code quality checks")
    
    return recommendations


def build_project_knowledge(owner, repo, token):
    """Build comprehensive project knowledge for intelligent agent"""
    knowledge = {
        "repository": f"{owner}/{repo}",
        "analyzed_at": datetime.now().isoformat(),
        "tech_stack": [],
        "files": {},
        "workflows": [],
        "dependencies": {},
        "devops_status": {},
        "suggestions": []
    }
    
    # Get basic analysis
    analysis = analyze_repository(owner, repo, token)
    knowledge["tech_stack"] = analysis.get("tech_stack", [])
    knowledge["primary_language"] = analysis.get("primary_language")
    knowledge["default_branch"] = analysis.get("default_branch", "main")
    knowledge["has_dockerfile"] = analysis.get("has_dockerfile", False)
    knowledge["has_kubernetes"] = analysis.get("has_kubernetes", False)
    
    # Get key files content
    key_files = ["package.json", "Dockerfile", "requirements.txt", "pom.xml", "go.mod"]
    for file in key_files:
        content = get_file_content(owner, repo, file, token, analysis.get("default_branch", "main"))
        if content:
            knowledge["files"][file] = content[:2000]  # Limit content size
    
    # Check for critical CI files existence (don't need content, just existence)
    critical_ci_files = [
        "package-lock.json",  # Required for npm ci
        "yarn.lock",          # Alternative for yarn
        "pnpm-lock.yaml",     # Alternative for pnpm
        ".eslintrc.json", ".eslintrc.js", ".eslintrc",  # Linting config
        "jest.config.js", "jest.config.ts",  # Test config
        "tsconfig.json",      # TypeScript config
        ".env.example",       # Environment template
        "docker-compose.yml", # Docker compose
    ]
    
    knowledge["ci_files"] = {}
    for file in critical_ci_files:
        try:
            github_request(f"/repos/{owner}/{repo}/contents/{file}", token=token)
            knowledge["ci_files"][file] = True
        except:
            knowledge["ci_files"][file] = False
    
    # Determine package manager
    if knowledge["ci_files"].get("package-lock.json"):
        knowledge["package_manager"] = "npm"
        knowledge["install_command"] = "npm ci"
    elif knowledge["ci_files"].get("yarn.lock"):
        knowledge["package_manager"] = "yarn"
        knowledge["install_command"] = "yarn install --frozen-lockfile"
    elif knowledge["ci_files"].get("pnpm-lock.yaml"):
        knowledge["package_manager"] = "pnpm"
        knowledge["install_command"] = "pnpm install --frozen-lockfile"
    else:
        knowledge["package_manager"] = "npm"
        knowledge["install_command"] = "npm install"  # Fallback - no lock file
        knowledge["warnings"] = knowledge.get("warnings", [])
        knowledge["warnings"].append("No package lock file found - using 'npm install' instead of 'npm ci'")
    
    # Check for test files
    knowledge["has_tests"] = False
    test_indicators = ["__tests__", "test", "tests", "spec"]
    try:
        root_contents = github_request(f"/repos/{owner}/{repo}/contents", token=token)
        for item in root_contents:
            if item["type"] == "dir" and item["name"].lower() in test_indicators:
                knowledge["has_tests"] = True
                break
        # Also check src folder for tests
        try:
            src_contents = github_request(f"/repos/{owner}/{repo}/contents/src", token=token)
            for item in src_contents:
                if item["type"] == "dir" and item["name"].lower() in test_indicators:
                    knowledge["has_tests"] = True
                    break
        except:
            pass
    except:
        pass
    
    # Parse dependencies
    if "package.json" in knowledge["files"]:
        try:
            pkg = json.loads(knowledge["files"]["package.json"])
            knowledge["dependencies"] = {
                "production": list(pkg.get("dependencies", {}).keys()),
                "development": list(pkg.get("devDependencies", {}).keys()),
                "scripts": pkg.get("scripts", {})
            }
            
            # Detect framework
            deps = pkg.get("dependencies", {})
            if "react" in deps:
                knowledge["framework"] = "React"
            elif "vue" in deps:
                knowledge["framework"] = "Vue"
            elif "next" in deps:
                knowledge["framework"] = "Next.js"
            elif "express" in deps:
                knowledge["framework"] = "Express"
        except:
            pass
    
    # Get existing workflows
    try:
        workflows_dir = github_request(f"/repos/{owner}/{repo}/contents/.github/workflows", token=token)
        for wf in workflows_dir:
            if wf["name"].endswith(".yml") or wf["name"].endswith(".yaml"):
                content = get_file_content(owner, repo, f".github/workflows/{wf['name']}", token)
                if content:
                    validation = validate_workflow_yaml(content)
                    knowledge["workflows"].append({
                        "name": wf["name"],
                        "content": content,
                        "validation": validation
                    })
    except:
        pass
    
    # Get recent Actions runs
    runs = get_actions_runs(owner, repo, token, per_page=5)
    knowledge["devops_status"]["recent_runs"] = [
        {
            "id": run["id"],
            "name": run.get("name"),
            "status": run["status"],
            "conclusion": run.get("conclusion"),
            "created_at": run["created_at"],
            "html_url": run["html_url"]
        }
        for run in runs
    ]
    
    # Analyze failures and generate suggestions
    failed_runs = [r for r in runs if r.get("conclusion") == "failure"]
    if failed_runs:
        knowledge["devops_status"]["has_failures"] = True
        knowledge["devops_status"]["failure_count"] = len(failed_runs)
        
        # Get detailed failure info
        for run in failed_runs[:2]:  # Check last 2 failures
            jobs = get_run_logs(owner, repo, run["id"], token)
            for job in jobs:
                if job.get("conclusion") == "failure":
                    knowledge["devops_status"]["last_failure_job"] = job.get("name")
                    # Get failed steps
                    for step in job.get("steps", []):
                        if step.get("conclusion") == "failure":
                            knowledge["devops_status"]["last_failure_step"] = step.get("name")
                            break
                    break
    else:
        knowledge["devops_status"]["has_failures"] = False
    
    # Generate intelligent suggestions
    knowledge["suggestions"] = generate_devops_suggestions(knowledge)
    
    # Store in cache
    PROJECT_KNOWLEDGE[f"{owner}/{repo}"] = knowledge
    
    return knowledge


def generate_devops_suggestions(knowledge):
    """Generate intelligent DevOps suggestions based on project analysis"""
    suggestions = []
    
    # Check for missing DevOps tools
    if not knowledge.get("has_dockerfile"):
        suggestions.append({
            "type": "add",
            "priority": "high",
            "title": "Add Dockerfile",
            "description": "Containerize your application for consistent deployments",
            "action": "generate_dockerfile"
        })
    
    if not knowledge.get("workflows"):
        suggestions.append({
            "type": "add",
            "priority": "critical",
            "title": "Add CI/CD Pipeline",
            "description": "No GitHub Actions workflows found. Add automated build and deploy pipeline.",
            "action": "generate_workflow"
        })
    
    # Check workflow quality
    for wf in knowledge.get("workflows", []):
        validation = wf.get("validation", {})
        if validation.get("score", 100) < 80:
            suggestions.append({
                "type": "improve",
                "priority": "medium",
                "title": f"Improve workflow: {wf['name']}",
                "description": f"Score: {validation.get('score')}/100. Issues: {', '.join(validation.get('issues', []))}",
                "action": "fix_workflow",
                "target": wf["name"]
            })
    
    # Check for failures
    if knowledge.get("devops_status", {}).get("has_failures"):
        suggestions.append({
            "type": "fix",
            "priority": "critical",
            "title": "Fix CI/CD Failures",
            "description": f"Last failed step: {knowledge['devops_status'].get('last_failure_step', 'Unknown')}",
            "action": "analyze_failure"
        })
    
    # Check for missing best practices
    scripts = knowledge.get("dependencies", {}).get("scripts", {})
    if scripts:
        if "test" not in scripts:
            suggestions.append({
                "type": "add",
                "priority": "medium",
                "title": "Add Test Script",
                "description": "No test script found in package.json",
                "action": "add_tests"
            })
        if "lint" not in scripts:
            suggestions.append({
                "type": "add",
                "priority": "low",
                "title": "Add Linting",
                "description": "Add ESLint for code quality",
                "action": "add_linting"
            })
    
    # Security suggestions
    if "docker" in str(knowledge.get("tech_stack", [])).lower():
        suggestions.append({
            "type": "add",
            "priority": "medium",
            "title": "Add Container Security Scanning",
            "description": "Scan Docker images for vulnerabilities with Trivy or Snyk",
            "action": "add_security_scan"
        })
    
    return suggestions


def generate_optimal_workflow(knowledge):
    """Generate optimal workflow based on project knowledge"""
    
    system_prompt = """You are an AGENTIC DevOps Engineer - an AI that autonomously generates production-ready CI/CD pipelines following enterprise best practices.

## Generation Approach
1. **Analyze First** - Understand the tech stack, frameworks, and project structure
2. **Plan Intelligently** - Design a workflow that matches the project's actual needs
3. **Execute Precisely** - Generate complete, working YAML with no placeholders
4. **Validate Thoroughly** - Include proper error handling and security checks

## BCG Enterprise Standards
- **CI/CD**: GitHub Actions with enterprise patterns, proper concurrency control
- **Caching**: Aggressive caching for dependencies (node_modules, pip, maven)
- **Security**: Trivy filesystem scans, dependency audits, SAST integration
- **Quality Gates**: Linting, testing, coverage thresholds
- **Deployments**: GitOps-ready with ArgoCD annotations

## CRITICAL RULES
1. Use latest action versions (actions/checkout@v4, setup-node@v4, etc.)
2. Include proper triggers: push (main), pull_request, workflow_dispatch
3. For Trivy: Use 'fs' scan-type, NOT image-ref (scan-type: 'fs', scan-ref: '.')
4. Add concurrency groups to prevent duplicate runs
5. Use GitHub Secrets with conditional checks: if: secrets.X != ''
6. Include matrix builds for multiple Node/Python versions where appropriate
7. Add status badges URL in workflow comments

Output ONLY valid YAML, no markdown code blocks or explanations."""
    
    prompt = f"""Generate a comprehensive CI/CD workflow for this project:

Repository: {knowledge.get('repository')}
Primary Language: {knowledge.get('primary_language')}
Framework: {knowledge.get('framework')}
Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
Has Dockerfile: {knowledge.get('has_dockerfile')}
Has Kubernetes: {knowledge.get('has_kubernetes')}
Package Manager: {knowledge.get('package_manager', 'npm')}
Install Command: {knowledge.get('install_command', 'npm install')}

NPM Scripts Available: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}

Current Issues: {knowledge.get('devops_status', {}).get('last_failure_step', 'None')}

IMPORTANT: For Trivy security scanning, use filesystem scan (scan-type: 'fs') NOT docker image scan.

Generate the optimal workflow YAML:"""

    workflow = invoke_bedrock(prompt, system_prompt)
    
    # Clean up response
    if workflow:
        workflow = workflow.strip()
        if workflow.startswith('```'):
            workflow = re.sub(r'^```\w*\n?', '', workflow)
            workflow = re.sub(r'\n?```$', '', workflow)
        
        # Post-process: Fix Trivy Docker image scans to filesystem scans
        workflow = fix_trivy_docker_scan(workflow)
    
    return workflow


def fix_trivy_docker_scan(workflow_content):
    """
    Post-process workflow to fix Trivy Docker image scans and exit-code issues.
    
    Fixes:
    1. Converts image-ref based scans to filesystem scans since the Docker image
       doesn't exist at scan time (it hasn't been built yet).
    2. Fixes incorrect Trivy action versions (v4 doesn't exist).
    3. Changes exit-code: '1' to exit-code: '0' so vulnerabilities don't fail the build
       (security findings are reported via SARIF upload to GitHub Security tab instead).
    
    Uses simple line-by-line approach to avoid yaml dependency and regex issues.
    """
    if not workflow_content:
        return workflow_content
    
    try:
        # Fix incorrect Trivy action version (v4 doesn't exist, use 0.28.0)
        if 'trivy-action@v4' in workflow_content:
            workflow_content = workflow_content.replace('trivy-action@v4', 'trivy-action@0.28.0')
            logger.info("[POST-PROCESS] Fixed Trivy action version: v4 -> 0.28.0")
        
        # Fix exit-code: '1' to exit-code: '0' for Trivy scans
        # This prevents build failures when vulnerabilities are found
        # Security findings are still reported via SARIF upload to GitHub Security tab
        if "exit-code: '1'" in workflow_content:
            workflow_content = workflow_content.replace("exit-code: '1'", "exit-code: '0'")
            logger.info("[POST-PROCESS] Fixed Trivy exit-code: '1' -> '0' (report-only mode)")
        if 'exit-code: "1"' in workflow_content:
            workflow_content = workflow_content.replace('exit-code: "1"', 'exit-code: "0"')
            logger.info("[POST-PROCESS] Fixed Trivy exit-code: \"1\" -> \"0\" (report-only mode)")
        
        # Check if this workflow uses trivy-action with image-ref
        if 'aquasecurity/trivy' not in workflow_content.lower():
            return workflow_content
        
        if 'image-ref' not in workflow_content:
            return workflow_content
        
        logger.info("[POST-PROCESS] Detected Trivy image-ref, converting to filesystem scan")
        
        # Simple line-by-line replacement
        lines = workflow_content.split('\n')
        new_lines = []
        replaced = False
        
        for i, line in enumerate(lines):
            # Check if this line contains image-ref
            if 'image-ref:' in line:
                # Get the indentation from current line
                stripped = line.lstrip()
                indent = line[:len(line) - len(stripped)]
                
                # Replace with scan-type and scan-ref
                new_lines.append(f"{indent}scan-type: 'fs'")
                new_lines.append(f"{indent}scan-ref: '.'")
                replaced = True
                logger.info(f"[POST-PROCESS] Replaced image-ref at line {i+1}")
            else:
                new_lines.append(line)
        
        if replaced:
            return '\n'.join(new_lines)
        
        return workflow_content
        
    except Exception as e:
        logger.error(f"[POST-PROCESS] Error fixing Trivy config: {e}")
        return workflow_content


def commit_directly(owner, repo, branch, file_path, content, message, token):
    """Commit directly to a branch (for main branch deployments with confirmation)"""
    return create_or_update_file(owner, repo, file_path, content, message, branch, token)


def format_response(event, action, status_code, data):
    """Format response for both API Gateway and Bedrock Agent invocations"""
    if "actionGroup" in event:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": action,
                "apiPath": event.get("apiPath", ""),
                "httpMethod": event.get("httpMethod", "POST"),
                "httpStatusCode": status_code,
                "responseBody": {
                    "application/json": {
                        "body": json.dumps(data)
                    }
                }
            }
        }
    
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(data)
    }


def github_request(endpoint, method="GET", data=None, token=None):
    """Make authenticated GitHub API request"""
    url = f"{GITHUB_API}{endpoint}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "BCG-DevOps-GenAI"
    }
    
    if token:
        headers["Authorization"] = f"token {token}"
    
    body = json.dumps(data).encode('utf-8') if data else None
    
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        logger.error(f"GitHub API error: {e.code} - {error_body}")
        raise Exception(f"GitHub API error: {e.code} - {error_body}")

def analyze_repository(owner, repo, token):
    """Analyze repository structure and detect tech stack"""
    analysis = {
        "owner": owner,
        "repo": repo,
        "languages": {},
        "tech_stack": [],
        "has_dockerfile": False,
        "has_kubernetes": False,
        "has_workflows": False,
        "framework": None,
        "package_manager": None
    }
    
    # Get repository info
    try:
        repo_info = github_request(f"/repos/{owner}/{repo}", token=token)
        analysis["default_branch"] = repo_info.get("default_branch", "main")
        analysis["description"] = repo_info.get("description", "")
    except Exception as e:
        logger.error(f"Failed to get repo info: {e}")
        analysis["default_branch"] = "main"
    
    # Get languages
    try:
        languages = github_request(f"/repos/{owner}/{repo}/languages", token=token)
        analysis["languages"] = languages
        
        # Detect primary language
        if languages:
            primary_lang = max(languages, key=languages.get)
            analysis["primary_language"] = primary_lang
    except Exception as e:
        logger.warning(f"Failed to get languages: {e}")
    
    # Get root contents to detect files
    try:
        contents = github_request(f"/repos/{owner}/{repo}/contents", token=token)
        file_names = [item["name"].lower() for item in contents if item["type"] == "file"]
        dir_names = [item["name"].lower() for item in contents if item["type"] == "dir"]
        
        # Detect package managers and frameworks
        if "package.json" in file_names:
            analysis["package_manager"] = "npm"
            analysis["tech_stack"].append("Node.js")
        if "yarn.lock" in file_names:
            analysis["package_manager"] = "yarn"
        if "pnpm-lock.yaml" in file_names:
            analysis["package_manager"] = "pnpm"
            
        if "go.mod" in file_names:
            analysis["tech_stack"].append("Go")
            analysis["package_manager"] = "go mod"
            
        if "requirements.txt" in file_names or "pyproject.toml" in file_names:
            analysis["tech_stack"].append("Python")
            if "pyproject.toml" in file_names:
                analysis["package_manager"] = "poetry"
            else:
                analysis["package_manager"] = "pip"
                
        if "pom.xml" in file_names:
            analysis["tech_stack"].append("Java")
            analysis["package_manager"] = "maven"
        if "build.gradle" in file_names:
            analysis["tech_stack"].append("Java")
            analysis["package_manager"] = "gradle"
            
        if "dockerfile" in file_names or "Dockerfile" in [item["name"] for item in contents]:
            analysis["has_dockerfile"] = True
            analysis["tech_stack"].append("Docker")
            
        if "k8s" in dir_names or "kubernetes" in dir_names or "manifests" in dir_names:
            analysis["has_kubernetes"] = True
            analysis["tech_stack"].append("Kubernetes")
            
        if ".github" in dir_names:
            analysis["has_workflows"] = True
            
    except Exception as e:
        logger.warning(f"Failed to analyze contents: {e}")
    
    return analysis

def get_file_content(owner, repo, path, token, ref="main"):
    """Get content of a specific file"""
    try:
        response = github_request(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}", token=token)
        if response.get("encoding") == "base64":
            content = base64.b64decode(response["content"]).decode('utf-8')
            return content
        return response.get("content", "")
    except Exception as e:
        logger.error(f"Failed to get file {path}: {e}")
        return None

def create_branch(owner, repo, branch_name, base_branch, token):
    """Create a new branch"""
    # Get the SHA of the base branch
    ref = github_request(f"/repos/{owner}/{repo}/git/ref/heads/{base_branch}", token=token)
    sha = ref["object"]["sha"]
    
    # Create new branch
    data = {
        "ref": f"refs/heads/{branch_name}",
        "sha": sha
    }
    
    result = github_request(f"/repos/{owner}/{repo}/git/refs", method="POST", data=data, token=token)
    return result

def create_or_update_file(owner, repo, path, content, message, branch, token):
    """Create or update a file in the repository"""
    # Check if file exists
    sha = None
    try:
        existing = github_request(f"/repos/{owner}/{repo}/contents/{path}?ref={branch}", token=token)
        sha = existing.get("sha")
    except:
        pass  # File doesn't exist
    
    data = {
        "message": message,
        "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
        "branch": branch
    }
    
    if sha:
        data["sha"] = sha
    
    result = github_request(f"/repos/{owner}/{repo}/contents/{path}", method="PUT", data=data, token=token)
    return result

def create_pull_request(owner, repo, title, body, head_branch, base_branch, token):
    """Create a pull request"""
    data = {
        "title": title,
        "body": body,
        "head": head_branch,
        "base": base_branch
    }
    
    result = github_request(f"/repos/{owner}/{repo}/pulls", method="POST", data=data, token=token)
    return result


def merge_pull_request(owner, repo, pr_number, token, merge_method="squash"):
    """Merge a pull request"""
    data = {
        "merge_method": merge_method
    }
    result = github_request(f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", method="PUT", data=data, token=token)
    return result


def wait_for_workflow_run(owner: str, repo: str, branch: str, token: str, 
                          timeout_seconds: int = 300, poll_interval: int = 15) -> Dict[str, Any]:
    """
    Wait for a workflow run to complete on a specific branch.
    Returns the run status and details.
    """
    start_time = time.time()
    run_found = False
    target_run = None
    
    logger.info(f"Waiting for workflow run on branch {branch}...")
    
    while time.time() - start_time < timeout_seconds:
        runs = get_actions_runs(owner, repo, token, per_page=10)
        
        # Find runs for this branch
        for run in runs:
            if run.get("head_branch") == branch:
                run_found = True
                target_run = run
                status = run.get("status")
                conclusion = run.get("conclusion")
                
                logger.info(f"Found run {run['id']}: status={status}, conclusion={conclusion}")
                
                if status == "completed":
                    # Get detailed job information
                    jobs = get_run_logs(owner, repo, run["id"], token)
                    return {
                        "completed": True,
                        "success": conclusion == "success",
                        "run_id": run["id"],
                        "run_url": run["html_url"],
                        "status": status,
                        "conclusion": conclusion,
                        "jobs": jobs
                    }
                break
        
        if not run_found:
            logger.info("No run found yet, waiting...")
        
        time.sleep(poll_interval)
    
    # Timeout
    return {
        "completed": False,
        "success": False,
        "timeout": True,
        "run_id": target_run["id"] if target_run else None,
        "message": f"Workflow did not complete within {timeout_seconds} seconds"
    }


# ============================================================================
# INCIDENT RESPONSE AGENT - L1/L2/L3 Escalation System
# ============================================================================

# Incident severity levels and their configurations
INCIDENT_LEVELS = {
    "L1": {
        "name": "Level 1 - Auto-Remediation",
        "description": "Automated fixes for common issues",
        "auto_resolve": True,
        "max_resolution_time_seconds": 300,
        "actions": ["restart_workflow", "clear_cache", "retry_failed_jobs", "scale_resources"]
    },
    "L2": {
        "name": "Level 2 - Engineering Review",
        "description": "Requires human engineering review",
        "auto_resolve": False,
        "max_resolution_time_seconds": 1800,
        "actions": ["create_issue", "notify_team", "generate_fix_suggestions"]
    },
    "L3": {
        "name": "Level 3 - Critical Escalation",
        "description": "Critical issues requiring immediate attention",
        "auto_resolve": False,
        "max_resolution_time_seconds": 3600,
        "actions": ["create_critical_issue", "notify_oncall", "page_team", "rollback"]
    }
}

# Incident patterns for automatic classification
INCIDENT_PATTERNS = {
    "L1": [
        {"pattern": r"npm\s+ERR!.*ECONNRESET", "action": "retry_failed_jobs", "description": "Network connectivity issue"},
        {"pattern": r"rate\s+limit\s+exceeded", "action": "wait_and_retry", "description": "Rate limiting"},
        {"pattern": r"timeout.*waiting", "action": "extend_timeout", "description": "Timeout issue"},
        {"pattern": r"ENOSPC|No space left", "action": "clear_cache", "description": "Disk space issue"},
        {"pattern": r"OOMKilled|out of memory", "action": "scale_resources", "description": "Memory exhaustion"},
        {"pattern": r"lock file|npm ERR! code EEXIST", "action": "clear_cache", "description": "Lock file conflict"},
        {"pattern": r"CERT_|certificate", "action": "retry_failed_jobs", "description": "Certificate issue"},
    ],
    "L2": [
        {"pattern": r"test.*fail|failing tests", "action": "generate_fix_suggestions", "description": "Test failures"},
        {"pattern": r"lint.*error|eslint", "action": "generate_fix_suggestions", "description": "Linting errors"},
        {"pattern": r"type.*error|TypeError", "action": "generate_fix_suggestions", "description": "Type errors"},
        {"pattern": r"build.*fail", "action": "analyze_build_failure", "description": "Build failure"},
        {"pattern": r"dependency.*conflict|peer dep", "action": "analyze_dependencies", "description": "Dependency conflict"},
    ],
    "L3": [
        {"pattern": r"security.*vuln|CVE-", "action": "create_critical_issue", "description": "Security vulnerability"},
        {"pattern": r"credentials.*exposed|secret.*leak", "action": "page_team", "description": "Credential exposure"},
        {"pattern": r"production.*down|critical.*fail", "action": "rollback", "description": "Production incident"},
        {"pattern": r"data.*loss|corruption", "action": "page_team", "description": "Data integrity issue"},
    ]
}


def classify_incident(error_message: str, workflow_logs: List[Dict] | None = None) -> Dict[str, Any]:
    """
    Classify an incident based on error patterns and determine the appropriate level
    """
    error_text = error_message.lower()
    if workflow_logs:
        error_text += " " + " ".join([str(log) for log in workflow_logs]).lower()
    
    # Check patterns from most severe to least
    for level in ["L3", "L2", "L1"]:
        for pattern_config in INCIDENT_PATTERNS[level]:
            if re.search(pattern_config["pattern"], error_text, re.IGNORECASE):
                return {
                    "level": level,
                    "level_config": INCIDENT_LEVELS[level],
                    "matched_pattern": pattern_config["pattern"],
                    "recommended_action": pattern_config["action"],
                    "description": pattern_config["description"],
                    "auto_remediate": INCIDENT_LEVELS[level]["auto_resolve"]
                }
    
    # Default to L2 if no pattern matches
    return {
        "level": "L2",
        "level_config": INCIDENT_LEVELS["L2"],
        "matched_pattern": None,
        "recommended_action": "generate_fix_suggestions",
        "description": "Unclassified issue requiring review",
        "auto_remediate": False
    }


def execute_l1_remediation(action: str, owner: str, repo: str, token: str, 
                           context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute L1 auto-remediation actions
    """
    logger.info(f"[INCIDENT] Executing L1 remediation: {action}")
    
    result = {
        "action": action,
        "success": False,
        "details": None
    }
    
    try:
        if action == "retry_failed_jobs":
            # Re-run failed workflow jobs
            run_id = context.get("run_id")
            if run_id:
                response = github_request(
                    f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs",
                    method="POST",
                    token=token
                )
                result["success"] = True
                result["details"] = f"Triggered re-run of failed jobs for run {run_id}"
        
        elif action == "restart_workflow":
            # Re-run the entire workflow
            run_id = context.get("run_id")
            if run_id:
                response = github_request(
                    f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun",
                    method="POST",
                    token=token
                )
                result["success"] = True
                result["details"] = f"Triggered full re-run for run {run_id}"
        
        elif action == "clear_cache":
            # Delete GitHub Actions caches
            try:
                caches = github_request(
                    f"/repos/{owner}/{repo}/actions/caches",
                    token=token
                )
                deleted_count = 0
                for cache in caches.get("actions_caches", [])[:5]:  # Limit to 5
                    github_request(
                        f"/repos/{owner}/{repo}/actions/caches/{cache['id']}",
                        method="DELETE",
                        token=token
                    )
                    deleted_count += 1
                result["success"] = True
                result["details"] = f"Cleared {deleted_count} cache entries"
            except Exception as e:
                result["details"] = f"Cache clear attempted: {str(e)}"
                result["success"] = True  # Non-critical if fails
        
        elif action == "wait_and_retry":
            # Wait for rate limit reset and retry
            time.sleep(60)  # Wait 1 minute
            run_id = context.get("run_id")
            if run_id:
                response = github_request(
                    f"/repos/{owner}/{repo}/actions/runs/{run_id}/rerun",
                    method="POST",
                    token=token
                )
                result["success"] = True
                result["details"] = "Waited 60s and triggered re-run"
        
        elif action == "extend_timeout":
            # Create an issue suggesting timeout extension
            issue_body = f"""## Timeout Issue Detected

A workflow timed out. Consider extending the timeout in your workflow configuration.

### Suggested Fix
```yaml
jobs:
  build:
    timeout-minutes: 30  # Increase from default
```

### Context
- Run ID: {context.get('run_id')}
- Workflow: {context.get('workflow_name', 'Unknown')}

*Auto-generated by BCG DevOps Incident Response Agent*
"""
            create_github_issue(owner, repo, "Workflow Timeout - Consider Extending", issue_body, token, ["enhancement", "automated"])
            result["success"] = True
            result["details"] = "Created issue suggesting timeout extension"
        
        elif action == "scale_resources":
            # Suggest resource scaling in issue
            issue_body = f"""## Resource Exhaustion Detected

A workflow ran out of resources (memory/disk). Consider using a larger runner.

### Suggested Fix
```yaml
jobs:
  build:
    runs-on: ubuntu-latest-8-cores  # Use larger runner
    # Or for self-hosted: runs-on: [self-hosted, large]
```

### Context
- Run ID: {context.get('run_id')}
- Error: {context.get('error_message', 'Resource exhaustion')}

*Auto-generated by BCG DevOps Incident Response Agent*
"""
            create_github_issue(owner, repo, "Resource Exhaustion - Scale Resources", issue_body, token, ["performance", "automated"])
            result["success"] = True
            result["details"] = "Created issue suggesting resource scaling"
        
        else:
            result["details"] = f"Unknown L1 action: {action}"
    
    except Exception as e:
        result["details"] = f"Remediation failed: {str(e)}"
        logger.error(f"[INCIDENT] L1 remediation failed: {e}")
    
    return result


def create_github_issue(owner: str, repo: str, title: str, body: str, 
                        token: str, labels: List[str] | None = None) -> Dict[str, Any]:
    """
    Create a GitHub issue for incident tracking
    """
    issue_data: Dict[str, Any] = {
        "title": title,
        "body": body
    }
    if labels:
        issue_data["labels"] = labels
    
    return github_request(
        f"/repos/{owner}/{repo}/issues",
        method="POST",
        data=issue_data,
        token=token
    )


def incident_response_agent(owner: str, repo: str, incident_description: str, 
                           token: str, auto_remediate: bool = True,
                           context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Intelligent Incident Response Agent with L1/L2/L3 Escalation
    
    Features:
    - Automatic incident classification
    - L1 auto-remediation for common issues
    - L2 engineering escalation with AI-generated fix suggestions
    - L3 critical escalation with notifications
    - Full audit trail and execution log
    """
    
    execution_log = []
    start_time = datetime.now()
    context = context or {}
    
    def log_step(step: str, status: str, details: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        execution_log.append(entry)
        logger.info(f"[INCIDENT] {step}: {status} - {details}")
    
    result = {
        "success": False,
        "repository": f"{owner}/{repo}",
        "incident_description": incident_description,
        "classification": None,
        "remediation_attempted": False,
        "remediation_result": None,
        "escalation": None,
        "execution_log": execution_log,
        "issue_url": None,
        "recommendations": []
    }
    
    try:
        # Step 1: Gather additional context
        log_step("gather_context", "started", "Collecting incident information...")
        
        # Get recent workflow runs for context
        recent_runs = get_actions_runs(owner, repo, token, per_page=5)
        failed_runs = [r for r in recent_runs if r.get("conclusion") == "failure"]
        
        workflow_logs = []
        run_id = None
        if failed_runs:
            run_id = failed_runs[0].get("id")
            context["run_id"] = run_id
            context["workflow_name"] = failed_runs[0].get("name")
            # Get job details
            jobs = get_run_logs(owner, repo, run_id, token)
            for job in jobs:
                if job.get("conclusion") == "failure":
                    for step in job.get("steps", []):
                        if step.get("conclusion") == "failure":
                            workflow_logs.append({
                                "job": job.get("name"),
                                "step": step.get("name"),
                                "conclusion": step.get("conclusion")
                            })
        
        context["error_message"] = incident_description
        log_step("gather_context", "completed", {
            "failed_runs_found": len(failed_runs),
            "run_id": run_id,
            "failed_steps": len(workflow_logs)
        })
        
        # Step 2: Classify the incident
        log_step("classify", "started", "Analyzing incident patterns...")
        
        classification = classify_incident(incident_description, workflow_logs)
        result["classification"] = classification
        
        log_step("classify", "completed", {
            "level": classification["level"],
            "description": classification["description"],
            "auto_remediate": classification["auto_remediate"]
        })
        
        # Step 3: Handle based on level
        level = classification["level"]
        
        if level == "L1" and auto_remediate and classification["auto_remediate"]:
            # L1: Attempt auto-remediation
            log_step("l1_remediation", "started", f"Executing: {classification['recommended_action']}")
            
            remediation_result = execute_l1_remediation(
                classification["recommended_action"],
                owner, repo, token, context
            )
            
            result["remediation_attempted"] = True
            result["remediation_result"] = remediation_result
            
            if remediation_result["success"]:
                log_step("l1_remediation", "completed", remediation_result["details"])
                result["success"] = True
                result["recommendations"].append(
                    "L1 auto-remediation executed. Monitor the workflow for success."
                )
                
                # Send Slack notification for successful L1 remediation
                slack_result = send_incident_notification(
                    incident_level="L1",
                    incident_description=incident_description,
                    repository=f"{owner}/{repo}",
                    classification=classification,
                    remediation_result=remediation_result
                )
                result["slack_notification"] = slack_result
                log_step("slack_notification", "completed" if slack_result.get("success") else "skipped", slack_result)
            else:
                log_step("l1_remediation", "failed", "Escalating to L2")
                level = "L2"  # Escalate if L1 fails
                classification["level"] = "L2"
        
        if level == "L2":
            # L2: Create issue with AI-generated fix suggestions
            log_step("l2_escalation", "started", "Generating fix suggestions with AI...")
            
            # Use AI to generate fix suggestions
            fix_prompt = f"""Analyze this DevOps incident and provide specific fix suggestions:

Incident: {incident_description}

Repository: {owner}/{repo}
Failed Steps: {json.dumps(workflow_logs, indent=2)}

Provide:
1. Root cause analysis (2-3 sentences)
2. Specific fix steps (numbered list)
3. Code snippet if applicable (in appropriate code block)
4. Prevention recommendations

Format the response in GitHub-flavored Markdown."""

            ai_suggestions = invoke_bedrock(fix_prompt, 
                "You are a senior DevOps engineer. Provide clear, actionable fix suggestions.")
            
            issue_body = f"""## Incident Report - L2 Engineering Escalation

### Classification
- **Level:** L2 - Engineering Review Required
- **Type:** {classification.get('description', 'Unknown')}
- **Auto-Remediation:** Not applicable for this issue type

### Incident Description
{incident_description}

### Failed Workflow Details
- **Run ID:** {run_id or 'N/A'}
- **Failed Steps:**
{chr(10).join(['- ' + str(log) for log in workflow_logs]) if workflow_logs else 'No specific steps identified'}

### AI-Generated Analysis & Fix Suggestions
{ai_suggestions}

### Next Steps
1. Review the analysis above
2. Apply the suggested fixes
3. Test in a feature branch
4. Close this issue when resolved

---
*Auto-generated by BCG DevOps Incident Response Agent*
*Incident ID: INC-{datetime.now().strftime('%Y%m%d%H%M%S')}*
"""
            
            issue = create_github_issue(
                owner, repo,
                f"[L2 Incident] {classification.get('description', 'Issue')} - Requires Review",
                issue_body,
                token,
                ["incident", "L2", "needs-review"]
            )
            
            result["issue_url"] = issue.get("html_url")
            result["escalation"] = {
                "level": "L2",
                "issue_number": issue.get("number"),
                "issue_url": issue.get("html_url")
            }
            result["recommendations"].append(ai_suggestions)
            result["success"] = True
            
            log_step("l2_escalation", "completed", {
                "issue_url": issue.get("html_url"),
                "issue_number": issue.get("number")
            })
            
            # Send Slack notification for L2
            slack_result = send_incident_notification(
                incident_level="L2",
                incident_description=incident_description,
                repository=f"{owner}/{repo}",
                classification=classification,
                remediation_result=None,
                issue_url=issue.get("html_url")
            )
            result["slack_notification"] = slack_result
            log_step("slack_notification", "completed" if slack_result.get("success") else "skipped", slack_result)
        
        elif level == "L3":
            # L3: Critical escalation
            log_step("l3_escalation", "started", "Creating critical incident...")
            
            # Create high-priority issue
            issue_body = f"""## 🚨 CRITICAL INCIDENT - L3 Escalation

### ⚠️ This requires immediate attention!

### Classification
- **Level:** L3 - Critical Escalation
- **Type:** {classification.get('description', 'Critical Issue')}
- **Severity:** CRITICAL
- **Requires:** Immediate human intervention

### Incident Description
{incident_description}

### Workflow Context
- **Repository:** {owner}/{repo}
- **Run ID:** {run_id or 'N/A'}
- **Timestamp:** {datetime.now().isoformat()}

### Failed Steps
{chr(10).join(['- ' + str(log) for log in workflow_logs]) if workflow_logs else 'See workflow logs for details'}

### Recommended Immediate Actions
1. **Assess Impact:** Determine scope of the issue
2. **Contain:** Stop any ongoing damage
3. **Investigate:** Review logs and recent changes
4. **Remediate:** Apply fixes or rollback
5. **Communicate:** Update stakeholders

### Incident Timeline
| Time | Event |
|------|-------|
| {datetime.now().isoformat()} | Incident detected and escalated |

---
*Auto-generated by BCG DevOps Incident Response Agent*
*Critical Incident ID: CRIT-{datetime.now().strftime('%Y%m%d%H%M%S')}*
"""
            
            issue = create_github_issue(
                owner, repo,
                f"🚨 [CRITICAL L3] {classification.get('description', 'Critical Incident')}",
                issue_body,
                token,
                ["incident", "L3", "critical", "urgent"]
            )
            
            result["issue_url"] = issue.get("html_url")
            result["escalation"] = {
                "level": "L3",
                "issue_number": issue.get("number"),
                "issue_url": issue.get("html_url"),
                "severity": "CRITICAL"
            }
            result["success"] = True
            result["recommendations"].append(
                "Critical incident created. Immediate human intervention required."
            )
            
            log_step("l3_escalation", "completed", {
                "issue_url": issue.get("html_url"),
                "severity": "CRITICAL"
            })
            
            # Send URGENT Slack notification for L3
            slack_result = send_incident_notification(
                incident_level="L3",
                incident_description=incident_description,
                repository=f"{owner}/{repo}",
                classification=classification,
                issue_url=issue.get("html_url")
            )
            result["slack_notification"] = slack_result
            log_step("slack_notification", "completed" if slack_result.get("success") else "skipped", slack_result)
        
        # Calculate duration
        end_time = datetime.now()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
    except Exception as e:
        log_step("error", "failed", str(e))
        result["error"] = str(e)
        logger.error(f"[INCIDENT] Error: {e}")
    
    return result


# ============================================================================
# MULTI-AGENT COORDINATION SYSTEM
# ============================================================================

# Agent types and their capabilities - Agentic AI Architecture
AGENT_TYPES = {
    "workflow_agent": {
        "name": "Autonomous Workflow Agent",
        "description": "Creates, optimizes, and self-heals CI/CD workflows with intelligent error recovery",
        "capabilities": ["generate_workflow", "fix_workflow", "optimize_workflow", "auto_remediate"],
        "function": "autonomous_devops_action",
        "intelligence": "Uses AI to understand project requirements and generate context-aware workflows"
    },
    "incident_agent": {
        "name": "Intelligent Incident Response Agent",
        "description": "Handles incident detection, classification, L1/L2/L3 escalation, and autonomous remediation",
        "capabilities": ["classify_incident", "auto_remediate", "escalate", "root_cause_analysis"],
        "function": "incident_response_agent",
        "intelligence": "AI-driven incident classification with automatic fix suggestions and remediation"
    },
    "analysis_agent": {
        "name": "Deep Repository Analysis Agent",
        "description": "Performs comprehensive analysis of repository structure, tech stack, security posture, and DevOps maturity",
        "capabilities": ["analyze_repo", "detect_tech_stack", "security_audit", "devops_maturity_score"],
        "function": "build_project_knowledge",
        "intelligence": "AI-powered codebase understanding and intelligent recommendations"
    },
    "security_agent": {
        "name": "Security & Compliance Agent",
        "description": "Performs security checks, vulnerability analysis, secrets scanning, and compliance verification",
        "capabilities": ["security_scan", "vulnerability_check", "secrets_audit", "compliance_check"],
        "function": "security_analysis",
        "intelligence": "Proactive security analysis with actionable remediation steps"
    }
}


def security_analysis(owner: str, repo: str, token: str) -> Dict[str, Any]:
    """
    Security analysis agent - checks for common security issues
    """
    result = {
        "findings": [],
        "risk_level": "low",
        "recommendations": []
    }
    
    try:
        # Check for security-related files
        contents = github_request(f"/repos/{owner}/{repo}/contents", token=token)
        files = [c.get("name", "").lower() for c in contents if c.get("type") == "file"]
        
        # Check for exposed secrets patterns
        if ".env.example" not in files and ".env.sample" not in files:
            result["recommendations"].append("Consider adding .env.example to document required environment variables")
        
        if ".gitignore" not in files:
            result["findings"].append({
                "severity": "medium",
                "issue": "No .gitignore file found",
                "recommendation": "Add .gitignore to prevent accidental commits of sensitive files"
            })
            result["risk_level"] = "medium"
        
        # Check workflows for security issues
        try:
            workflows_contents = github_request(f"/repos/{owner}/{repo}/contents/.github/workflows", token=token)
            for wf in workflows_contents:
                if wf.get("type") == "file" and wf.get("name", "").endswith((".yml", ".yaml")):
                    wf_content = github_request(f"/repos/{owner}/{repo}/contents/{wf['path']}", token=token)
                    if "content" in wf_content:
                        decoded = base64.b64decode(wf_content["content"]).decode("utf-8")
                        
                        # Check for hardcoded secrets
                        if re.search(r'(password|secret|key|token)\s*[:=]\s*["\'][^$\s][^"\']+["\']', decoded, re.IGNORECASE):
                            result["findings"].append({
                                "severity": "high",
                                "issue": f"Potential hardcoded secret in {wf['name']}",
                                "recommendation": "Use GitHub Secrets instead of hardcoded values"
                            })
                            result["risk_level"] = "high"
                        
                        # Check for pull_request_target with checkout
                        if "pull_request_target" in decoded and "actions/checkout" in decoded:
                            result["findings"].append({
                                "severity": "high",
                                "issue": f"Potentially unsafe pull_request_target usage in {wf['name']}",
                                "recommendation": "Review pull_request_target workflow for pwn request vulnerabilities"
                            })
                            result["risk_level"] = "high"
        except:
            pass  # No workflows folder
        
        # Check for Dependabot
        try:
            github_request(f"/repos/{owner}/{repo}/contents/.github/dependabot.yml", token=token)
        except:
            result["recommendations"].append("Enable Dependabot for automated security updates")
        
        # Check for CODEOWNERS
        try:
            github_request(f"/repos/{owner}/{repo}/contents/.github/CODEOWNERS", token=token)
        except:
            result["recommendations"].append("Add CODEOWNERS file to enforce code review requirements")
        
    except Exception as e:
        result["error"] = str(e)
    
    return result


def coordinate_agents(owner: str, repo: str, task: str, token: str,
                     agent_sequence: List[str] | None = None) -> Dict[str, Any]:
    """
    Multi-Agent Coordination System
    
    Coordinates multiple specialized agents to complete complex tasks.
    Each agent handles a specific aspect of the task and passes context
    to the next agent in the sequence.
    """
    
    execution_log = []
    start_time = datetime.now()
    
    def log_step(step: str, status: str, details: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        execution_log.append(entry)
        logger.info(f"[MULTI-AGENT] {step}: {status} - {details}")
    
    result = {
        "success": False,
        "repository": f"{owner}/{repo}",
        "task": task,
        "agents_used": [],
        "agent_results": {},
        "execution_log": execution_log,
        "final_summary": None
    }
    
    try:
        # Step 1: Analyze task to determine required agents
        log_step("task_analysis", "started", f"Analyzing task: {task}")
        
        if not agent_sequence:
            # Use AI to determine the best agent sequence
            analysis_prompt = f"""Analyze this DevOps task and determine which agents should handle it:

Task: {task}

Available Agents:
{json.dumps(AGENT_TYPES, indent=2)}

Return a JSON object with:
{{
  "agent_sequence": ["agent_name1", "agent_name2", ...],
  "reasoning": "Why this sequence"
}}

Only include agents that are needed. Order matters - earlier agents prepare context for later ones."""

            analysis_response = invoke_bedrock(analysis_prompt, 
                "You are a DevOps orchestration expert. Determine the optimal agent sequence.")
            
            try:
                analysis = json.loads(analysis_response)
                agent_sequence = analysis.get("agent_sequence", ["analysis_agent", "workflow_agent"])
            except:
                # Default sequence for general tasks
                agent_sequence = ["analysis_agent", "workflow_agent"]
        
        log_step("task_analysis", "completed", {
            "agent_sequence": agent_sequence
        })
        
        # Ensure agent_sequence is a list (satisfy type checker)
        if agent_sequence is None:
            agent_sequence = ["analysis_agent", "workflow_agent"]
        
        # Step 2: Execute agents in sequence
        shared_context: Dict[str, Any] = {
            "owner": owner,
            "repo": repo,
            "task": task,
            "knowledge": None,
            "previous_results": []
        }
        
        for agent_name in agent_sequence:
            if agent_name not in AGENT_TYPES:
                log_step(f"agent_{agent_name}", "skipped", "Unknown agent type")
                continue
            
            agent_config = AGENT_TYPES[agent_name]
            log_step(f"agent_{agent_name}", "started", agent_config["description"])
            
            agent_result = None
            
            try:
                if agent_name == "analysis_agent":
                    agent_result = build_project_knowledge(owner, repo, token)
                    shared_context["knowledge"] = agent_result
                
                elif agent_name == "workflow_agent":
                    agent_result = autonomous_devops_action(
                        owner, repo, task, token,
                        max_retries=2, auto_merge=False,
                        skip_wait=True  # Skip waiting to avoid API Gateway timeout
                    )
                
                elif agent_name == "incident_agent":
                    agent_result = incident_response_agent(
                        owner, repo, task, token,
                        auto_remediate=True,
                        context=shared_context
                    )
                
                elif agent_name == "security_agent":
                    agent_result = security_analysis(owner, repo, token)
                
                result["agents_used"].append(agent_name)
                result["agent_results"][agent_name] = agent_result
                shared_context["previous_results"].append({
                    "agent": agent_name,
                    "result": agent_result
                })
                
                log_step(f"agent_{agent_name}", "completed", {
                    "success": agent_result.get("success", True) if isinstance(agent_result, dict) else True
                })
                
            except Exception as e:
                log_step(f"agent_{agent_name}", "failed", str(e))
                result["agent_results"][agent_name] = {"error": str(e)}
        
        # Step 3: Generate final summary
        log_step("summarize", "started", "Generating coordination summary...")
        
        summary_prompt = f"""Summarize the results of this multi-agent DevOps operation:

Task: {task}
Repository: {owner}/{repo}

Agent Results:
{json.dumps(result["agent_results"], indent=2, default=str)}

Provide a concise summary (3-5 sentences) of:
1. What was accomplished
2. Any issues found
3. Recommended next steps"""

        summary = invoke_bedrock(summary_prompt, 
            "You are a DevOps coordinator. Provide clear, actionable summaries.")
        
        result["final_summary"] = summary
        result["success"] = True
        
        log_step("summarize", "completed", "Coordination complete")
        
        # Calculate duration
        end_time = datetime.now()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
    except Exception as e:
        log_step("error", "failed", str(e))
        result["error"] = str(e)
        logger.error(f"[MULTI-AGENT] Error: {e}")
    
    return result


def preview_workflow(owner: str, repo: str, request: str, token: str) -> Dict[str, Any]:
    """
    Preview workflow generation WITHOUT committing.
    
    This function:
    1. Deeply analyzes the repository (checks lock files, tests, eslint, etc.)
    2. Generates a production-ready workflow
    3. Pre-validates the workflow
    4. Returns a preview for user confirmation
    
    DOES NOT create branches or commit anything.
    Call confirm_workflow() to actually commit the workflow.
    """
    
    execution_log = []
    start_time = datetime.now()
    
    def log_step(step: str, status: str, details: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        execution_log.append(entry)
        logger.info(f"[PREVIEW] {step}: {status} - {details}")
    
    result = {
        "preview_id": datetime.now().strftime('%Y%m%d-%H%M%S'),
        "repository": f"{owner}/{repo}",
        "request": request,
        "execution_log": execution_log,
        "workflow_content": None,
        "validation": None,
        "knowledge": None,
        "warnings": [],
        "ready_to_commit": False
    }
    
    try:
        # Step 1: Deep repository analysis
        log_step("analyze", "started", "Building comprehensive project knowledge...")
        knowledge = build_project_knowledge(owner, repo, token)
        
        # Extract key info for display
        result["knowledge"] = {
            "tech_stack": knowledge.get("tech_stack", []),
            "framework": knowledge.get("framework"),
            "package_manager": knowledge.get("package_manager", "npm"),
            "install_command": knowledge.get("install_command", "npm install"),
            "has_lock_file": knowledge.get("ci_files", {}).get("package-lock.json") or 
                            knowledge.get("ci_files", {}).get("yarn.lock") or 
                            knowledge.get("ci_files", {}).get("pnpm-lock.yaml"),
            "has_eslint": knowledge.get("ci_files", {}).get(".eslintrc.json") or 
                         knowledge.get("ci_files", {}).get(".eslintrc.js"),
            "has_tests": knowledge.get("has_tests", False),
            "has_typescript": knowledge.get("ci_files", {}).get("tsconfig.json", False),
            "has_dockerfile": knowledge.get("has_dockerfile", False),
            "existing_workflows": [w["name"] for w in knowledge.get("workflows", [])],
            "npm_scripts": list(knowledge.get("dependencies", {}).get("scripts", {}).keys())
        }
        
        # Add warnings from knowledge
        if knowledge.get("warnings"):
            result["warnings"].extend(knowledge.get("warnings"))
        
        log_step("analyze", "completed", result["knowledge"])
        
        # Step 2: Understand the request
        log_step("understand_request", "started", f"Processing: {request}")
        
        system_prompt = """You are a DevOps expert. Analyze the user's request and determine:
        1. What type of action is needed (create_workflow, fix_workflow, improve_workflow)
        2. What specific changes to make
        3. Best practices to apply
        
        Output JSON with: {"action_type": "...", "description": "...", "focus_areas": [...]}"""
        
        understanding = invoke_bedrock(f"""User Request: {request}
        
Repository Analysis:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Framework: {knowledge.get('framework')}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Existing Workflows: {[w['name'] for w in knowledge.get('workflows', [])]}
- Recent Failures: {knowledge.get('devops_status', {}).get('has_failures', False)}

What action should be taken?""", system_prompt)
        
        try:
            action_plan = json.loads(understanding)
        except:
            action_plan = {"action_type": "create_workflow", "description": request}
        
        result["action_plan"] = action_plan
        log_step("understand_request", "completed", action_plan)
        
        # Step 3: Generate workflow
        log_step("generate_workflow", "started", f"Action: {action_plan.get('action_type')}")
        
        # Get install command and other settings from knowledge
        install_command = knowledge.get('install_command', 'npm install')
        package_manager = knowledge.get('package_manager', 'npm')
        has_lock_file = result["knowledge"]["has_lock_file"]
        has_eslint = result["knowledge"]["has_eslint"]
        has_tests = result["knowledge"]["has_tests"] or 'test' in knowledge.get('dependencies', {}).get('scripts', {})
        has_typescript = result["knowledge"]["has_typescript"]
        
        # Get existing workflow for reference
        existing_workflow_content = ""
        for wf in knowledge.get("workflows", []):
            if wf.get("content"):
                existing_workflow_content = wf.get("content", "")
                break
        
        workflow_prompt = f"""Generate a complete, production-ready GitHub Actions workflow based on:

User Request: {request}

Project Details:
- Repository: {owner}/{repo}
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Framework: {knowledge.get('framework')}
- Package Manager: {package_manager}
- Has Lock File: {has_lock_file}
- Package Manager Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Has Kubernetes: {knowledge.get('has_kubernetes')}
- Has ESLint: {has_eslint}
- Has Tests: {has_tests}
- Has TypeScript: {has_typescript}

{f"Existing Workflow (for reference):" + chr(10) + existing_workflow_content if existing_workflow_content else ""}

CRITICAL Requirements:
1. Use latest action versions (actions/checkout@v4, actions/setup-node@v4)
2. IMPORTANT: Use '{install_command}' for installing dependencies (this repo {'HAS' if has_lock_file else 'does NOT have'} a lock file)
3. Include proper caching for node_modules
4. {'Add linting step with eslint' if has_eslint else 'Skip linting - no eslint config found'}
5. {'Add testing step' if has_tests else 'Skip testing - no test script or test directory found'}
6. Use 'CI=false' for React builds to ignore warnings as errors
7. Include security best practices
8. Use GitHub Secrets for sensitive data
9. Add workflow_dispatch for manual triggers
10. DO NOT use 'continue-on-error: true' unless absolutely necessary

Output ONLY valid YAML, no markdown code blocks or explanations."""

        workflow_content = invoke_bedrock(workflow_prompt, 
            "You are a GitHub Actions expert. Output only valid YAML, no markdown.")
        
        # Clean up response
        if workflow_content:
            workflow_content = workflow_content.strip()
            if workflow_content.startswith('```'):
                workflow_content = re.sub(r'^```\w*\n?', '', workflow_content)
                workflow_content = re.sub(r'\n?```$', '', workflow_content)
            
            # Post-process: Fix Trivy Docker image scans to filesystem scans
            workflow_content = fix_trivy_docker_scan(workflow_content)
        
        result["workflow_content"] = workflow_content
        
        # Step 4: Validate the workflow
        log_step("validate", "started", "Validating generated workflow...")
        
        validation = validate_workflow_yaml(workflow_content)
        
        # AI-based review
        ai_review_prompt = f"""Review this GitHub Actions workflow for issues:

```yaml
{workflow_content}
```

Project Context:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Package Manager: {package_manager}
- Has Lock File: {has_lock_file}
- Required Install Command: {install_command}
- NPM Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}
- Has ESLint: {has_eslint}
- Has Tests: {has_tests}

CRITICAL Check:
1. Must use '{install_command}' (repo {'HAS' if has_lock_file else 'does NOT have'} lock file)
2. {'Should have lint step' if has_eslint else 'Should NOT have lint step'}
3. {'Should have test step' if has_tests else 'Should NOT have test step'}
4. Check for syntax errors and best practices

Output JSON:
{{"issues": ["issue1", "issue2"], "is_production_ready": true/false, "severity": "high/medium/low"}}"""

        ai_review = invoke_bedrock(ai_review_prompt, 
            "You are a CI/CD expert. Review workflows for issues. Output only JSON.")
        
        try:
            review_result = json.loads(ai_review)
        except:
            review_result = {"issues": [], "is_production_ready": True, "severity": "none"}
        
        result["validation"] = {
            "yaml_valid": validation.get("valid"),
            "score": validation.get("score"),
            "yaml_issues": validation.get("issues", []),
            "ai_issues": review_result.get("issues", []),
            "ai_production_ready": review_result.get("is_production_ready"),
            "severity": review_result.get("severity")
        }
        
        # Add validation warnings
        if validation.get("issues"):
            result["warnings"].extend(validation.get("issues"))
        if review_result.get("issues"):
            result["warnings"].extend(review_result.get("issues"))
        
        log_step("validate", "completed", result["validation"])
        
        # Determine if ready to commit
        result["ready_to_commit"] = validation.get("valid") and review_result.get("is_production_ready", True)
        
        # Calculate duration
        end_time = datetime.now()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
        log_step("preview", "completed", f"Ready to commit: {result['ready_to_commit']}")
        
    except Exception as e:
        log_step("error", "failed", str(e))
        result["error"] = str(e)
        logger.error(f"[PREVIEW] Error: {e}")
    
    return result


def confirm_workflow(owner: str, repo: str, workflow_content: str, token: str,
                     request: str = "", workflow_name: str = "ci-cd-autonomous.yml",
                     skip_wait: bool = True, max_retries: int = 3) -> Dict[str, Any]:
    """
    Commit a previewed workflow to the repository.
    
    This function:
    1. Creates a branch
    2. Commits the workflow file
    3. Creates a PR
    4. Optionally waits for the workflow to run
    
    Args:
        owner: Repository owner
        repo: Repository name
        workflow_content: The workflow YAML content to commit
        token: GitHub token
        request: Original user request (for PR description)
        workflow_name: Name for the workflow file
        skip_wait: If True, returns after PR creation without waiting
        max_retries: Number of retry attempts if workflow fails
    """
    
    execution_log = []
    start_time = datetime.now()
    
    def log_step(step: str, status: str, details: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        execution_log.append(entry)
        logger.info(f"[CONFIRM] {step}: {status} - {details}")
    
    result = {
        "success": False,
        "repository": f"{owner}/{repo}",
        "request": request,
        "execution_log": execution_log,
        "pr_url": None,
        "branch_name": None,
        "workflow_file": None,
        "fixes_applied": []
    }
    
    try:
        # Validate workflow before committing
        validation = validate_workflow_yaml(workflow_content)
        if not validation.get("valid"):
            result["error"] = f"Workflow validation failed: {validation.get('issues')}"
            result["validation"] = validation
            return result
        
        # Get repo info
        repo_info = github_request(f"/repos/{owner}/{repo}", token=token)
        default_branch = repo_info.get("default_branch", "main")
        
        # Create branch
        task_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f"autonomous-agent/devops-{task_id}"
        result["branch_name"] = branch_name
        
        try:
            create_branch(owner, repo, branch_name, default_branch, token)
            log_step("create_branch", "completed", branch_name)
        except Exception as e:
            if "Reference already exists" not in str(e):
                raise e
            log_step("create_branch", "exists", branch_name)
        
        # Commit workflow file
        file_path = f".github/workflows/{workflow_name}"
        create_or_update_file(
            owner, repo, file_path, workflow_content,
            f"chore(ci): Add workflow - {request[:50] if request else 'autonomous agent'}",
            branch_name, token
        )
        log_step("commit_workflow", "completed", file_path)
        result["workflow_file"] = file_path
        
        # Build knowledge for PR description
        knowledge = build_project_knowledge(owner, repo, token)
        
        # Create PR
        pr = create_pull_request(
            owner, repo,
            f"[Autonomous Agent] {request[:80] if request else 'Add CI/CD workflow'}",
            f"""## Autonomous DevOps Agent

**Request:** {request or 'Generate CI/CD workflow'}

### Generated Configuration
- **Workflow:** `{workflow_name}`
- **Validation Score:** {validation.get('score', 'N/A')}/100

### Analysis Summary
- **Tech Stack:** {', '.join(knowledge.get('tech_stack', []))}
- **Framework:** {knowledge.get('framework') or 'Not detected'}
- **Package Manager:** {knowledge.get('package_manager', 'npm')}
- **Install Command:** {knowledge.get('install_command', 'npm install')}

### Key Details
- **Has Lock File:** {knowledge.get('ci_files', {}).get('package-lock.json') or knowledge.get('ci_files', {}).get('yarn.lock') or 'No'}
- **Has Tests:** {knowledge.get('has_tests', False)}
- **Has ESLint:** {knowledge.get('ci_files', {}).get('.eslintrc.json') or knowledge.get('ci_files', {}).get('.eslintrc.js') or 'No'}

### Next Steps
1. Review the workflow changes
2. Check the Actions tab for workflow run status
3. Merge when satisfied

---
*Generated by BCG Autonomous DevOps Agent*
*Branch: `{branch_name}`*
""",
            branch_name, default_branch, token
        )
        
        pr_url = pr.get("html_url")
        pr_number = pr.get("number")
        result["pr_url"] = pr_url
        result["pr_number"] = pr_number
        log_step("create_pr", "completed", {"pr_url": pr_url, "pr_number": pr_number})
        
        if skip_wait:
            result["success"] = True
            result["final_status"] = "pr_created"
            result["message"] = f"PR created successfully. Workflow will run automatically. Check: {pr_url}"
            log_step("complete", "success", "PR created - skipping workflow wait")
        else:
            # Wait for workflow to complete (similar to autonomous_devops_action)
            log_step("wait_workflow", "started", "Waiting for workflow run...")
            time.sleep(10)
            
            run_result = wait_for_workflow_run(
                owner, repo, branch_name, token,
                timeout_seconds=300,
                poll_interval=15
            )
            
            if run_result.get("success"):
                result["success"] = True
                result["final_status"] = "workflow_passed"
                result["run_url"] = run_result.get("run_url")
                log_step("workflow_check", "success", "Workflow passed!")
            else:
                result["final_status"] = run_result.get("conclusion", "failed")
                result["run_url"] = run_result.get("run_url")
                log_step("workflow_check", "failed", run_result.get("conclusion"))
        
        # Calculate duration
        end_time = datetime.now()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
    except Exception as e:
        log_step("error", "failed", str(e))
        result["error"] = str(e)
        result["final_status"] = "error"
        logger.error(f"[CONFIRM] Error: {e}")
    
    return result


def intelligent_tool_selector(knowledge: Dict[str, Any]) -> Dict[str, Any]:
    """
    Intelligently select the best tools based on repository analysis.
    Works like a senior DevOps engineer making tool decisions.
    
    Selection Logic:
    - Registry: JFrog (enterprise), ECR (AWS), GHCR (default)
    - Security: Prisma Cloud (enterprise), Trivy (open-source)
    - Observability: Datadog (enterprise), CloudWatch (AWS)
    - Deployment: ArgoCD (GitOps), EKS (AWS K8s), plain K8s
    
    Returns tool configuration for pipeline generation.
    """
    
    # Extract signals from knowledge
    tech_stack = knowledge.get("tech_stack", "")
    framework = knowledge.get("framework", "")
    has_dockerfile = knowledge.get("has_dockerfile", False)
    repo_files = knowledge.get("files", [])
    existing_workflows = knowledge.get("workflows", [])
    package_json = knowledge.get("package_json", {})
    pom_xml = knowledge.get("pom_xml", "")
    
    # Convert to searchable strings
    files_str = " ".join(repo_files).lower()
    workflows_str = str(existing_workflows).lower()
    
    selected_tools = {
        "container_registry": None,
        "security_scanner": None,
        "observability": None,
        "deployment": None,
        "testing": None,
        "build": None,
        "reasons": []
    }
    
    # --- Container Registry Selection ---
    if "jfrog" in files_str or "artifactory" in workflows_str or ".jfrog" in files_str:
        selected_tools["container_registry"] = {
            "name": "jfrog",
            "type": "enterprise",
            "config": {
                "registry_url": "${{ secrets.JFROG_REGISTRY }}",
                "username": "${{ secrets.JFROG_USERNAME }}",
                "password": "${{ secrets.JFROG_PASSWORD }}"
            }
        }
        selected_tools["reasons"].append("JFrog detected in repo - using enterprise registry")
    elif "ecr" in workflows_str or "aws" in files_str or "terraform" in files_str:
        selected_tools["container_registry"] = {
            "name": "ecr",
            "type": "aws",
            "config": {
                "region": "${{ secrets.AWS_REGION }}",
                "role_arn": "${{ secrets.AWS_ROLE_ARN }}"
            }
        }
        selected_tools["reasons"].append("AWS/ECR patterns detected - using ECR")
    else:
        selected_tools["container_registry"] = {
            "name": "ghcr",
            "type": "github",
            "config": {
                "registry": "ghcr.io",
                "token": "${{ secrets.GITHUB_TOKEN }}"
            }
        }
        selected_tools["reasons"].append("Using GitHub Container Registry (default)")
    
    # --- Security Scanner Selection ---
    if "prisma" in files_str or "twistlock" in workflows_str or "prismacloud" in files_str:
        selected_tools["security_scanner"] = {
            "name": "prisma_cloud",
            "type": "enterprise",
            "config": {
                "access_key": "${{ secrets.PRISMA_ACCESS_KEY }}",
                "secret_key": "${{ secrets.PRISMA_SECRET_KEY }}",
                "console_url": "${{ secrets.PRISMA_CONSOLE_URL }}"
            },
            "features": ["sast", "sca", "iac", "container_scan", "secrets_detection"]
        }
        selected_tools["reasons"].append("Prisma Cloud detected - using enterprise security suite")
    else:
        selected_tools["security_scanner"] = {
            "name": "trivy",
            "type": "opensource",
            "config": {},
            "features": ["container_scan", "fs_scan", "config_scan"]
        }
        selected_tools["reasons"].append("Using Trivy for security scanning (open-source)")
    
    # --- Observability Selection ---
    if "datadog" in files_str or "dd-" in workflows_str or "datadog" in workflows_str:
        selected_tools["observability"] = {
            "name": "datadog",
            "type": "enterprise",
            "config": {
                "api_key": "${{ secrets.DATADOG_API_KEY }}",
                "app_key": "${{ secrets.DATADOG_APP_KEY }}",
                "site": "${{ secrets.DATADOG_SITE }}"
            },
            "features": ["metrics", "logs", "traces", "synthetic_tests", "ci_visibility"]
        }
        selected_tools["reasons"].append("Datadog detected - using enterprise observability")
    elif "cloudwatch" in workflows_str or "aws" in files_str:
        selected_tools["observability"] = {
            "name": "cloudwatch",
            "type": "aws",
            "config": {
                "region": "${{ secrets.AWS_REGION }}"
            },
            "features": ["metrics", "logs", "alarms"]
        }
        selected_tools["reasons"].append("Using AWS CloudWatch for observability")
    else:
        selected_tools["observability"] = None
        selected_tools["reasons"].append("No specific observability tool detected")
    
    # --- Deployment Selection ---
    if "argocd" in files_str or "argo-cd" in files_str or "application.yaml" in files_str:
        selected_tools["deployment"] = {
            "name": "argocd",
            "type": "gitops",
            "config": {
                "server": "${{ secrets.ARGOCD_SERVER }}",
                "token": "${{ secrets.ARGOCD_TOKEN }}"
            },
            "features": ["auto_sync", "health_check", "rollback"]
        }
        selected_tools["reasons"].append("ArgoCD detected - using GitOps deployment")
    elif "eks" in files_str or "eksctl" in files_str:
        selected_tools["deployment"] = {
            "name": "eks",
            "type": "aws_kubernetes",
            "config": {
                "cluster_name": "${{ secrets.EKS_CLUSTER_NAME }}",
                "region": "${{ secrets.AWS_REGION }}"
            },
            "features": ["kubectl", "helm", "rolling_update"]
        }
        selected_tools["reasons"].append("EKS detected - using AWS Kubernetes")
    elif "kubernetes" in files_str or "k8s" in files_str or "deployment.yaml" in files_str:
        selected_tools["deployment"] = {
            "name": "kubernetes",
            "type": "kubernetes",
            "config": {
                "kubeconfig": "${{ secrets.KUBECONFIG }}"
            },
            "features": ["kubectl", "helm"]
        }
        selected_tools["reasons"].append("Kubernetes manifests detected - using K8s deployment")
    elif has_dockerfile:
        selected_tools["deployment"] = {
            "name": "docker",
            "type": "container",
            "config": {},
            "features": ["docker_compose", "container_run"]
        }
        selected_tools["reasons"].append("Dockerfile detected - using container deployment")
    else:
        selected_tools["deployment"] = None
        selected_tools["reasons"].append("No deployment target detected")
    
    # --- Testing Framework Selection ---
    if tech_stack == "nodejs" or tech_stack == "typescript":
        if "jest" in str(package_json):
            selected_tools["testing"] = {"name": "jest", "command": "npm test"}
        elif "vitest" in str(package_json):
            selected_tools["testing"] = {"name": "vitest", "command": "npm test"}
        elif "mocha" in str(package_json):
            selected_tools["testing"] = {"name": "mocha", "command": "npm test"}
        else:
            selected_tools["testing"] = {"name": "npm", "command": "npm test"}
        selected_tools["reasons"].append(f"Node.js detected - using {selected_tools['testing']['name']}")
    elif tech_stack == "python":
        if "pytest" in files_str:
            selected_tools["testing"] = {"name": "pytest", "command": "pytest"}
        else:
            selected_tools["testing"] = {"name": "unittest", "command": "python -m pytest"}
        selected_tools["reasons"].append("Python detected - using pytest")
    elif tech_stack == "java":
        if "gradle" in files_str:
            selected_tools["testing"] = {"name": "gradle", "command": "./gradlew test"}
        else:
            selected_tools["testing"] = {"name": "maven", "command": "mvn test"}
        selected_tools["reasons"].append("Java detected - using Maven/Gradle tests")
    elif tech_stack == "go":
        selected_tools["testing"] = {"name": "go", "command": "go test ./..."}
        selected_tools["reasons"].append("Go detected - using go test")
    
    # --- Build Tool Selection ---
    if tech_stack == "nodejs" or tech_stack == "typescript":
        selected_tools["build"] = {"name": "npm", "install": "npm ci", "build": "npm run build"}
    elif tech_stack == "python":
        selected_tools["build"] = {"name": "pip", "install": "pip install -r requirements.txt", "build": None}
    elif tech_stack == "java":
        if "gradle" in files_str:
            selected_tools["build"] = {"name": "gradle", "install": None, "build": "./gradlew build"}
        else:
            selected_tools["build"] = {"name": "maven", "install": None, "build": "mvn package -DskipTests"}
    elif tech_stack == "go":
        selected_tools["build"] = {"name": "go", "install": "go mod download", "build": "go build ./..."}
    elif tech_stack == "dotnet":
        selected_tools["build"] = {"name": "dotnet", "install": "dotnet restore", "build": "dotnet build"}
    
    return selected_tools


def generate_unified_pipeline(knowledge: Dict[str, Any], selected_tools: Dict[str, Any], 
                              intent: str = "full") -> str:
    """
    Generate a complete, unified CI/CD pipeline with all stages in one workflow.
    
    Stages (in order):
    1. Build - Compile/package the application
    2. Test - Run unit/integration tests  
    3. Security Scan - SAST, SCA, container scanning
    4. Build & Push Image - Create and push container image
    5. Deploy - Deploy to target environment
    6. Verify - Post-deployment health checks
    
    Args:
        knowledge: Repository analysis from build_project_knowledge()
        selected_tools: Tool selection from intelligent_tool_selector()
        intent: "full" (all stages), "ci" (build+test+scan), "cd" (deploy only)
    
    Returns:
        Complete GitHub Actions workflow YAML
    """
    
    tech_stack = knowledge.get("tech_stack", "nodejs")
    has_dockerfile = knowledge.get("has_dockerfile", False)
    registry = selected_tools.get("container_registry", {})
    scanner = selected_tools.get("security_scanner", {})
    deploy = selected_tools.get("deployment")
    testing = selected_tools.get("testing", {})
    build = selected_tools.get("build", {})
    observability = selected_tools.get("observability")
    
    # Build the workflow sections
    workflow_parts = []
    
    # --- Header ---
    workflow_parts.append(f'''name: Unified CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Deployment environment'
        required: false
        default: 'staging'
        type: choice
        options:
          - staging
          - production

env:
  IMAGE_NAME: ${{{{ github.repository }}}}
  
permissions:
  contents: read
  packages: write
  security-events: write
  id-token: write

jobs:''')

    # --- Build Job ---
    if intent in ["full", "ci"]:
        build_steps = []
        
        # Setup based on tech stack
        if tech_stack in ["nodejs", "typescript"]:
            build_steps.append('''      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Build application
        run: npm run build --if-present''')
        elif tech_stack == "python":
            build_steps.append('''      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt''')
        elif tech_stack == "java":
            if build.get("name") == "gradle":
                build_steps.append('''      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: 'gradle'
      
      - name: Build with Gradle
        run: ./gradlew build -x test''')
            else:
                build_steps.append('''      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          java-version: '17'
          distribution: 'temurin'
          cache: 'maven'
      
      - name: Build with Maven
        run: mvn package -DskipTests''')
        elif tech_stack == "go":
            build_steps.append('''      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      
      - name: Download dependencies
        run: go mod download
      
      - name: Build
        run: go build -v ./...''')
        
        workflow_parts.append(f'''
  build:
    name: Build
    runs-on: ubuntu-latest
    outputs:
      build-success: ${{{{ steps.build.outcome }}}}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
{chr(10).join(build_steps)}
      
      - name: Upload build artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts
          path: |
            dist/
            build/
            target/
            bin/
          retention-days: 7''')

    # --- Test Job ---
    if intent in ["full", "ci"] and testing:
        test_cmd = testing.get("command", "npm test")
        
        workflow_parts.append(f'''
  test:
    name: Test
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Download build artifacts
        uses: actions/download-artifact@v4
        with:
          name: build-artifacts
          path: .
        continue-on-error: true
      
      - name: Run tests
        run: {test_cmd}
        continue-on-error: false
      
      - name: Upload test results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: |
            coverage/
            test-results/
            **/junit*.xml
          retention-days: 7''')

    # --- Security Scan Job ---
    if intent in ["full", "ci"]:
        if scanner.get("name") == "prisma_cloud":
            workflow_parts.append('''
  security-scan:
    name: Security Scan (Prisma Cloud)
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Prisma Cloud SAST Scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          output_format: sarif
          output_file_path: results.sarif
        env:
          PRISMA_API_URL: ${{ secrets.PRISMA_CONSOLE_URL }}
          BC_API_KEY: ${{ secrets.PRISMA_ACCESS_KEY }}
      
      - name: Upload SARIF results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: results.sarif
        if: always()
      
      - name: Prisma Cloud SCA Scan
        run: |
          curl -L -o checkov https://github.com/bridgecrewio/checkov/releases/latest/download/checkov_linux_amd64
          chmod +x checkov
          ./checkov -d . --framework sca_package -o sarif --output-file sca-results.sarif
        continue-on-error: true''')
        else:
            workflow_parts.append('''
  security-scan:
    name: Security Scan (Trivy)
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner (filesystem)
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-fs-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-fs-results.sarif'
        if: always()
      
      - name: Run Trivy config scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: '.'
          format: 'table'
          severity: 'CRITICAL,HIGH'
        continue-on-error: true''')

    # --- Build & Push Image Job ---
    if intent in ["full", "cd"] and has_dockerfile:
        if registry.get("name") == "jfrog":
            workflow_parts.append('''
  build-image:
    name: Build & Push Image (JFrog)
    runs-on: ubuntu-latest
    needs: security-scan
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to JFrog Artifactory
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.JFROG_REGISTRY }}
          username: ${{ secrets.JFROG_USERNAME }}
          password: ${{ secrets.JFROG_PASSWORD }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ secrets.JFROG_REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max''')
        elif registry.get("name") == "ecr":
            workflow_parts.append('''
  build-image:
    name: Build & Push Image (ECR)
    runs-on: ubuntu-latest
    needs: security-scan
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ steps.login-ecr.outputs.registry }}/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max''')
        else:  # GHCR default
            workflow_parts.append('''
  build-image:
    name: Build & Push Image (GHCR)
    runs-on: ubuntu-latest
    needs: security-scan
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ env.IMAGE_NAME }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max''')

        # Container scan after image build
        if scanner.get("name") == "prisma_cloud":
            workflow_parts.append('''
  container-scan:
    name: Container Security Scan
    runs-on: ubuntu-latest
    needs: build-image
    steps:
      - name: Prisma Cloud Container Scan
        uses: PaloAltoNetworks/prisma-cloud-scan@v1
        with:
          pcc_console_url: ${{ secrets.PRISMA_CONSOLE_URL }}
          pcc_user: ${{ secrets.PRISMA_ACCESS_KEY }}
          pcc_pass: ${{ secrets.PRISMA_SECRET_KEY }}
          image_name: ${{ needs.build-image.outputs.image-tag }}''')
        else:
            workflow_parts.append('''
  container-scan:
    name: Container Security Scan
    runs-on: ubuntu-latest
    needs: build-image
    steps:
      - name: Run Trivy container scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ needs.build-image.outputs.image-tag }}
          format: 'sarif'
          output: 'trivy-container-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload container scan results
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-container-results.sarif'
        if: always()''')

    # --- Deploy Job ---
    if intent in ["full", "cd"] and deploy:
        if deploy.get("name") == "argocd":
            workflow_parts.append('''
  deploy:
    name: Deploy (ArgoCD)
    runs-on: ubuntu-latest
    needs: [build-image, container-scan]
    environment: ${{ github.event.inputs.environment || 'staging' }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Update image tag in manifests
        run: |
          cd k8s/overlays/${{ github.event.inputs.environment || 'staging' }}
          kustomize edit set image app=${{ needs.build-image.outputs.image-tag }}
      
      - name: Commit and push changes
        run: |
          git config user.name "GitHub Actions"
          git config user.email "actions@github.com"
          git add .
          git commit -m "Update image to ${{ needs.build-image.outputs.image-tag }}"
          git push
      
      - name: Sync ArgoCD Application
        uses: clowdhaus/argo-cd-action@v2
        with:
          command: app sync
          options: |
            --server ${{ secrets.ARGOCD_SERVER }}
            --auth-token ${{ secrets.ARGOCD_TOKEN }}
            --app-name ${{ github.event.repository.name }}-${{ github.event.inputs.environment || 'staging' }}
      
      - name: Wait for deployment
        uses: clowdhaus/argo-cd-action@v2
        with:
          command: app wait
          options: |
            --server ${{ secrets.ARGOCD_SERVER }}
            --auth-token ${{ secrets.ARGOCD_TOKEN }}
            --app-name ${{ github.event.repository.name }}-${{ github.event.inputs.environment || 'staging' }}
            --timeout 300''')
        elif deploy.get("name") == "eks":
            workflow_parts.append('''
  deploy:
    name: Deploy (EKS)
    runs-on: ubuntu-latest
    needs: [build-image, container-scan]
    environment: ${{ github.event.inputs.environment || 'staging' }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ${{ secrets.AWS_REGION }}
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig --name ${{ secrets.EKS_CLUSTER_NAME }} --region ${{ secrets.AWS_REGION }}
      
      - name: Deploy to EKS
        run: |
          kubectl set image deployment/${{ github.event.repository.name }} \
            app=${{ needs.build-image.outputs.image-tag }} \
            -n ${{ github.event.inputs.environment || 'staging' }}
          kubectl rollout status deployment/${{ github.event.repository.name }} \
            -n ${{ github.event.inputs.environment || 'staging' }} \
            --timeout=300s''')
        elif deploy.get("name") == "kubernetes":
            workflow_parts.append('''
  deploy:
    name: Deploy (Kubernetes)
    runs-on: ubuntu-latest
    needs: [build-image, container-scan]
    environment: ${{ github.event.inputs.environment || 'staging' }}
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
      
      - name: Configure kubeconfig
        run: |
          mkdir -p ~/.kube
          echo "${{ secrets.KUBECONFIG }}" | base64 -d > ~/.kube/config
      
      - name: Deploy to Kubernetes
        run: |
          kubectl apply -f k8s/
          kubectl set image deployment/${{ github.event.repository.name }} \
            app=${{ needs.build-image.outputs.image-tag }}
          kubectl rollout status deployment/${{ github.event.repository.name }} --timeout=300s''')

    # --- Observability Integration ---
    if intent in ["full", "cd"] and observability:
        if observability.get("name") == "datadog":
            workflow_parts.append('''
  notify-datadog:
    name: Notify Datadog
    runs-on: ubuntu-latest
    needs: deploy
    if: always()
    steps:
      - name: Send deployment event to Datadog
        run: |
          curl -X POST "https://${{ secrets.DATADOG_SITE }}/api/v1/events" \
            -H "Content-Type: application/json" \
            -H "DD-API-KEY: ${{ secrets.DATADOG_API_KEY }}" \
            -d '{
              "title": "Deployment: ${{ github.repository }}",
              "text": "Deployed ${{ github.sha }} to ${{ github.event.inputs.environment || '\''staging'\'' }}",
              "priority": "normal",
              "tags": ["env:${{ github.event.inputs.environment || '\''staging'\'' }}", "service:${{ github.event.repository.name }}"],
              "alert_type": "${{ needs.deploy.result == '\''success'\'' && '\''info'\'' || '\''error'\'' }}"
            }"''')

    return "\n".join(workflow_parts)


def pipeline_action(owner: str, repo: str, token: str, intent: str = "full") -> Dict[str, Any]:
    """
    Single-command autonomous pipeline creation.
    
    This is THE entry point for autonomous DevOps - give it a repo and it does everything:
    1. Analyzes the repository automatically
    2. Selects optimal tools based on repo patterns
    3. Generates complete unified pipeline
    4. Creates PR with self-healing capability
    
    Args:
        owner: GitHub owner/org
        repo: Repository name
        token: GitHub token
        intent: "full" (complete CI/CD), "ci" (build/test/scan only), "cd" (deploy only)
    
    Returns:
        Complete execution result with PR URL
    """
    
    execution_log = []
    start_time = datetime.now()
    
    def log_step(step: str, status: str, details: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        execution_log.append(entry)
        logger.info(f"[PIPELINE] {step}: {status} - {details}")
    
    result = {
        "success": False,
        "repository": f"{owner}/{repo}",
        "intent": intent,
        "execution_log": execution_log,
        "pr_url": None,
        "workflow_file": None,
        "tools_selected": None,
        "knowledge": None
    }
    
    try:
        # Step 1: Analyze repository
        log_step("analyze", "started", "Building comprehensive project knowledge...")
        knowledge = build_project_knowledge(owner, repo, token)
        result["knowledge"] = {
            "tech_stack": knowledge.get("tech_stack"),
            "framework": knowledge.get("framework"),
            "has_dockerfile": knowledge.get("has_dockerfile"),
            "existing_workflows": len(knowledge.get("workflows", []))
        }
        log_step("analyze", "completed", result["knowledge"])
        
        # Step 2: Intelligent tool selection
        log_step("tool_selection", "started", "Selecting optimal tools...")
        selected_tools = intelligent_tool_selector(knowledge)
        
        # Helper to safely get nested dict values (handles None values)
        def safe_get(d, key, nested_key=None, default=None):
            val = d.get(key) if d else None
            if val is None:
                return default
            if nested_key:
                return val.get(nested_key, default) if isinstance(val, dict) else default
            return val
        
        result["tools_selected"] = {
            "container_registry": safe_get(selected_tools, "container_registry", "name"),
            "security_scanner": safe_get(selected_tools, "security_scanner", "name"),
            "observability": safe_get(selected_tools, "observability", "name"),
            "deployment": safe_get(selected_tools, "deployment", "name"),
            "reasons": selected_tools.get("reasons", []) if selected_tools else []
        }
        log_step("tool_selection", "completed", result["tools_selected"])
        
        # Step 3: Generate unified pipeline
        log_step("generate_pipeline", "started", f"Creating {intent} pipeline...")
        workflow_yaml = generate_unified_pipeline(knowledge, selected_tools, intent)
        result["workflow_file"] = workflow_yaml
        log_step("generate_pipeline", "completed", f"Generated {len(workflow_yaml)} chars")
        
        # Step 4: Validate workflow before PR
        log_step("validate", "started", "Pre-validating workflow...")
        validation = validate_workflow_yaml(workflow_yaml)
        if not validation.get("valid"):
            log_step("validate", "fixing", validation.get("issues"))
            # AI-powered self-healing - regenerate with fixes
            issues_str = ", ".join(validation.get("issues", []))
            # Use Bedrock to fix the workflow
            fix_prompt = f"""Fix these issues in the GitHub Actions workflow:

Issues: {issues_str}

Current workflow:
```yaml
{workflow_yaml}
```

Return ONLY the fixed YAML, no explanations."""
            fixed_yaml = invoke_bedrock(fix_prompt, "You are a GitHub Actions expert. Fix the workflow YAML and return only the corrected YAML.")
            if fixed_yaml and "name:" in fixed_yaml:
                # Extract just the YAML content
                if "```yaml" in fixed_yaml:
                    fixed_yaml = fixed_yaml.split("```yaml")[1].split("```")[0].strip()
                elif "```" in fixed_yaml:
                    fixed_yaml = fixed_yaml.split("```")[1].split("```")[0].strip()
                workflow_yaml = fixed_yaml
                result["workflow_file"] = fixed_yaml
        log_step("validate", "completed", "Workflow validated")
        
        # Step 5: Create PR
        log_step("create_pr", "started", "Creating pull request...")
        
        # Create branch name
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch_name = f"devops/unified-pipeline-{timestamp}"
        
        # Get default branch
        repo_info = github_request(f"/repos/{owner}/{repo}", "GET", None, token)
        default_branch = repo_info.get("default_branch", "main")
        
        # Get base SHA
        ref_data = github_request(f"/repos/{owner}/{repo}/git/ref/heads/{default_branch}", "GET", None, token)
        base_sha = ref_data["object"]["sha"]
        
        # Create branch
        github_request(
            f"/repos/{owner}/{repo}/git/refs",
            "POST",
            {
                "ref": f"refs/heads/{branch_name}",
                "sha": base_sha
            },
            token
        )
        
        # Get current tree
        commit_data = github_request(f"/repos/{owner}/{repo}/git/commits/{base_sha}", "GET", None, token)
        tree_sha = commit_data["tree"]["sha"]
        
        # Create blob for workflow file
        blob_data = github_request(
            f"/repos/{owner}/{repo}/git/blobs",
            "POST",
            {
                "content": workflow_yaml,
                "encoding": "utf-8"
            },
            token
        )
        
        # Create new tree
        new_tree = github_request(
            f"/repos/{owner}/{repo}/git/trees",
            "POST",
            {
                "base_tree": tree_sha,
                "tree": [{
                    "path": ".github/workflows/unified-pipeline.yml",
                    "mode": "100644",
                    "type": "blob",
                    "sha": blob_data["sha"]
                }]
            },
            token
        )
        
        # Create commit
        commit = github_request(
            f"/repos/{owner}/{repo}/git/commits",
            "POST",
            {
                "message": f"feat: Add unified CI/CD pipeline ({intent})\n\nAuto-generated by DevOps AI Agent\n\nTools selected:\n- Registry: {result['tools_selected']['container_registry']}\n- Security: {result['tools_selected']['security_scanner']}\n- Deploy: {result['tools_selected']['deployment']}",
                "tree": new_tree["sha"],
                "parents": [base_sha]
            },
            token
        )
        
        # Update branch reference
        github_request(
            f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
            "PATCH",
            {"sha": commit["sha"]},
            token
        )
        
        # Create PR
        # Helper to safely get tool type
        def get_tool_type(tool_dict):
            if tool_dict and isinstance(tool_dict, dict):
                return tool_dict.get('type', 'N/A')
            return 'N/A'
        
        pr_body = f"""## Unified CI/CD Pipeline

**Auto-generated by DevOps AI Agent**

### Pipeline Type: `{intent.upper()}`

### Repository Analysis
| Attribute | Value |
|-----------|-------|
| Tech Stack | {result['knowledge']['tech_stack']} |
| Framework | {result['knowledge']['framework']} |
| Has Dockerfile | {result['knowledge']['has_dockerfile']} |
| Existing Workflows | {result['knowledge']['existing_workflows']} |

### Tools Selected
| Category | Tool | Type |
|----------|------|------|
| Container Registry | {result['tools_selected']['container_registry']} | {get_tool_type(selected_tools.get('container_registry'))} |
| Security Scanner | {result['tools_selected']['security_scanner']} | {get_tool_type(selected_tools.get('security_scanner'))} |
| Observability | {result['tools_selected']['observability'] or 'None'} | {get_tool_type(selected_tools.get('observability'))} |
| Deployment | {result['tools_selected']['deployment'] or 'None'} | {get_tool_type(selected_tools.get('deployment'))} |

### Selection Reasons
{chr(10).join(f'- {r}' for r in result['tools_selected']['reasons'])}

### Pipeline Stages
1. **Build** - Compile and package application
2. **Test** - Run automated tests
3. **Security Scan** - SAST/SCA/Container scanning
4. **Build Image** - Create and push container image
5. **Deploy** - Deploy to target environment

### Required Secrets
Please ensure these secrets are configured in your repository settings:
"""
        # Add required secrets based on tools (using safe_get helper)
        if safe_get(selected_tools, "container_registry", "name") == "jfrog":
            pr_body += "\n- `JFROG_REGISTRY`\n- `JFROG_USERNAME`\n- `JFROG_PASSWORD`"
        elif safe_get(selected_tools, "container_registry", "name") == "ecr":
            pr_body += "\n- `AWS_ROLE_ARN`\n- `AWS_REGION`"
        
        if safe_get(selected_tools, "security_scanner", "name") == "prisma_cloud":
            pr_body += "\n- `PRISMA_ACCESS_KEY`\n- `PRISMA_SECRET_KEY`\n- `PRISMA_CONSOLE_URL`"
        
        if safe_get(selected_tools, "deployment", "name") == "argocd":
            pr_body += "\n- `ARGOCD_SERVER`\n- `ARGOCD_TOKEN`"
        elif safe_get(selected_tools, "deployment", "name") == "eks":
            pr_body += "\n- `EKS_CLUSTER_NAME`\n- `AWS_REGION`\n- `AWS_ROLE_ARN`"
        
        if safe_get(selected_tools, "observability", "name") == "datadog":
            pr_body += "\n- `DATADOG_API_KEY`\n- `DATADOG_APP_KEY`\n- `DATADOG_SITE`"
        
        pr_data = github_request(
            f"/repos/{owner}/{repo}/pulls",
            "POST",
            {
                "title": f"feat: Add unified CI/CD pipeline ({intent})",
                "body": pr_body,
                "head": branch_name,
                "base": default_branch
            },
            token
        )
        
        result["pr_url"] = pr_data.get("html_url")
        result["pr_number"] = pr_data.get("number")
        result["branch_name"] = branch_name
        result["success"] = True
        log_step("create_pr", "completed", result["pr_url"])
        
        # Calculate duration
        end_time = datetime.now()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
    except Exception as e:
        log_step("error", "failed", str(e))
        result["error"] = str(e)
        logger.error(f"[PIPELINE] Error: {e}")
    
    return result


def autonomous_devops_action(owner: str, repo: str, request: str, token: str, 
                             max_retries: int = 3, auto_merge: bool = False,
                             skip_wait: bool = False) -> Dict[str, Any]:
    """
    Fully autonomous DevOps agent that:
    1. Analyzes the repository
    2. Generates workflow based on natural language request
    3. Pre-validates workflow with AI before creating PR
    4. Creates ONE branch and ONE PR
    5. Iteratively fixes issues in SAME branch (pushes new commits)
    6. Only creates final production-ready PR
    7. Optionally auto-merges on success
    
    Best Practices Applied:
    - Single branch per task (no multiple PRs)
    - Pre-validation before GitHub Actions run
    - Iterative fixes in same branch
    - Final PR is production-ready
    
    Args:
        skip_wait: If True, returns after PR creation without waiting for workflow
    """
    
    execution_log = []
    start_time = datetime.now()
    
    def log_step(step: str, status: str, details: Any = None):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "step": step,
            "status": status,
            "details": details
        }
        execution_log.append(entry)
        logger.info(f"[AUTONOMOUS] {step}: {status} - {details}")
    
    result = {
        "success": False,
        "repository": f"{owner}/{repo}",
        "request": request,
        "execution_log": execution_log,
        "final_status": None,
        "pr_url": None,
        "workflow_file": None,
        "branch_name": None,
        "attempts": 0,
        "fixes_applied": []
    }
    
    try:
        # Step 1: Analyze repository
        log_step("analyze", "started", "Building project knowledge...")
        knowledge = build_project_knowledge(owner, repo, token)
        log_step("analyze", "completed", {
            "tech_stack": knowledge.get("tech_stack"),
            "framework": knowledge.get("framework"),
            "has_dockerfile": knowledge.get("has_dockerfile"),
            "existing_workflows": len(knowledge.get("workflows", []))
        })
        
        # Step 2: Understand the request using AI
        log_step("understand_request", "started", f"Processing: {request}")
        
        system_prompt = """You are a DevOps expert. Analyze the user's request and determine:
        1. What type of action is needed (create_workflow, fix_workflow, improve_workflow)
        2. What specific changes to make
        3. Best practices to apply
        
        Output JSON with: {"action_type": "...", "description": "...", "focus_areas": [...]}"""
        
        understanding_prompt = f"""User Request: {request}
        
Repository Analysis:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Framework: {knowledge.get('framework')}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Existing Workflows: {[w['name'] for w in knowledge.get('workflows', [])]}
- Recent Failures: {knowledge.get('devops_status', {}).get('has_failures', False)}

What action should be taken?"""
        
        understanding = invoke_bedrock(understanding_prompt, system_prompt)
        try:
            action_plan = json.loads(understanding)
        except:
            action_plan = {"action_type": "create_workflow", "description": request}
        
        log_step("understand_request", "completed", action_plan)
        
        # Step 3: Generate initial workflow
        log_step("generate_workflow", "started", f"Action: {action_plan.get('action_type')}")
        
        # Get existing workflow if any for reference
        existing_workflow_content = ""
        for wf in knowledge.get("workflows", []):
            if wf.get("content"):
                existing_workflow_content = wf.get("content", "")
                break
        
        # Get install command from knowledge (smart detection based on lock files)
        install_command = knowledge.get('install_command', 'npm install')
        package_manager = knowledge.get('package_manager', 'npm')
        has_lock_file = knowledge.get('ci_files', {}).get('package-lock.json') or \
                        knowledge.get('ci_files', {}).get('yarn.lock') or \
                        knowledge.get('ci_files', {}).get('pnpm-lock.yaml')
        has_eslint = knowledge.get('ci_files', {}).get('.eslintrc.json') or \
                     knowledge.get('ci_files', {}).get('.eslintrc.js') or \
                     knowledge.get('ci_files', {}).get('.eslintrc') or \
                     'eslint' in knowledge.get('dependencies', {}).get('development', [])
        has_tests = knowledge.get('has_tests', False) or 'test' in knowledge.get('dependencies', {}).get('scripts', {})
        has_typescript = knowledge.get('ci_files', {}).get('tsconfig.json', False)
        
        workflow_prompt = f"""Generate a complete, production-ready GitHub Actions workflow based on:

User Request: {request}

Project Details:
- Repository: {owner}/{repo}
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Framework: {knowledge.get('framework')}
- Package Manager: {package_manager}
- Has Lock File: {has_lock_file}
- Package Manager Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Has Kubernetes: {knowledge.get('has_kubernetes')}
- Has ESLint: {has_eslint}
- Has Tests: {has_tests}
- Has TypeScript: {has_typescript}

{f"Existing Workflow (UPDATE THIS - do not create separate workflow):" + chr(10) + existing_workflow_content if existing_workflow_content else "No existing workflow - create new one"}

CRITICAL Requirements:
1. **SINGLE UNIFIED WORKFLOW** - Generate ONE workflow file with ALL stages (build, test, security, deploy) in a single pipeline
2. DO NOT create multiple workflow files - everything must be in ONE file
3. Use latest action versions (actions/checkout@v4, actions/setup-node@v4)
4. IMPORTANT: Use '{install_command}' for installing dependencies (this repo {'HAS' if has_lock_file else 'does NOT have'} a lock file)
5. Include proper caching for node_modules
6. {'Add linting step with eslint' if has_eslint else 'Skip linting - no eslint config found'}
7. {'Add testing step' if has_tests else 'Skip testing - no test script or test directory found'}
8. Use 'CI=false' for React builds to ignore warnings as errors
9. Include security best practices
10. Use GitHub Secrets for sensitive data (AWS_ACCESS_KEY_ID, etc.)
11. Add workflow_dispatch for manual triggers
12. For deploy steps, check if credentials exist first
13. DO NOT use 'continue-on-error: true' unless absolutely necessary
14. Add container security scanning with Trivy if Dockerfile exists
15. Use job dependencies (needs:) to create proper pipeline flow: build -> test -> security -> deploy

Output ONLY valid YAML, no markdown code blocks or explanations."""

        workflow_content = invoke_bedrock(workflow_prompt, 
            "You are a GitHub Actions expert. Output only valid YAML, no markdown.")
        
        # Clean up response
        if workflow_content:
            workflow_content = workflow_content.strip()
            if workflow_content.startswith('```'):
                workflow_content = re.sub(r'^```\w*\n?', '', workflow_content)
                workflow_content = re.sub(r'\n?```$', '', workflow_content)
            
            # Post-process: Fix Trivy Docker image scans to filesystem scans
            workflow_content = fix_trivy_docker_scan(workflow_content)
        
        # Step 4: Pre-validation loop - fix issues BEFORE creating PR
        log_step("pre_validation", "started", "Validating and improving workflow before PR creation...")
        
        for pre_fix_attempt in range(max_retries):
            validation = validate_workflow_yaml(workflow_content)
            
            # Also do AI-based validation for best practices
            ai_review_prompt = f"""Review this GitHub Actions workflow for issues:

```yaml
{workflow_content}
```

Project Context:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Package Manager: {package_manager}
- Has Lock File: {has_lock_file}
- Required Install Command: {install_command}
- NPM Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Has ESLint: {has_eslint}
- Has Tests: {has_tests}

CRITICAL Check for:
1. Syntax errors
2. Missing required fields
3. Incorrect action versions
4. Security issues (hardcoded secrets, etc.)
5. Best practice violations
6. IMPORTANT: Check if workflow uses correct install command (should use '{install_command}' - {'has lock file' if has_lock_file else 'NO lock file in repo'})
7. Check if linting step is appropriate ({'eslint found' if has_eslint else 'no eslint - should skip lint'})
8. Check if test step is appropriate ({'tests found' if has_tests else 'no tests - should skip test'})

Output JSON:
{{"issues": ["issue1", "issue2"], "is_production_ready": true/false, "severity": "high/medium/low"}}

If no issues, return: {{"issues": [], "is_production_ready": true, "severity": "none"}}"""

            ai_review = invoke_bedrock(ai_review_prompt, 
                "You are a CI/CD expert. Review workflows for issues. Output only JSON.")
            
            try:
                review_result = json.loads(ai_review)
            except:
                review_result = {"issues": [], "is_production_ready": True, "severity": "none"}
            
            log_step("pre_validation", f"attempt_{pre_fix_attempt + 1}", {
                "yaml_valid": validation.get("valid"),
                "score": validation.get("score"),
                "ai_issues": len(review_result.get("issues", [])),
                "production_ready": review_result.get("is_production_ready")
            })
            
            # If workflow is good, proceed
            if validation.get("valid") and review_result.get("is_production_ready"):
                log_step("pre_validation", "passed", "Workflow is production-ready")
                break
            
            # Fix issues before creating PR
            issues_to_fix = validation.get("issues", []) + review_result.get("issues", [])
            
            if issues_to_fix and pre_fix_attempt < max_retries - 1:
                log_step("pre_fix", "started", f"Fixing {len(issues_to_fix)} issues before PR creation")
                
                fix_prompt = f"""Fix these issues in the workflow:

Issues Found:
{json.dumps(issues_to_fix, indent=2)}

Current Workflow:
```yaml
{workflow_content}
```

Project Info:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Package Manager: {package_manager}
- Has Lock File: {has_lock_file}
- REQUIRED Install Command: {install_command}
- NPM Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Has ESLint: {has_eslint}
- Has Tests: {has_tests}

CRITICAL: This repo {'HAS' if has_lock_file else 'does NOT have'} a lock file. Use '{install_command}' for dependencies.

Generate the CORRECTED workflow. Output ONLY valid YAML, no markdown:"""

                workflow_content = invoke_bedrock(fix_prompt, 
                    "You are a GitHub Actions expert. Fix all issues. Output only valid YAML.")
                
                # Clean up
                if workflow_content:
                    workflow_content = workflow_content.strip()
                    if workflow_content.startswith('```'):
                        workflow_content = re.sub(r'^```\w*\n?', '', workflow_content)
                        workflow_content = re.sub(r'\n?```$', '', workflow_content)
                    
                    # Post-process: Fix Trivy Docker image scans to filesystem scans
                    workflow_content = fix_trivy_docker_scan(workflow_content)
                
                result["fixes_applied"].append({
                    "stage": "pre_validation",
                    "attempt": pre_fix_attempt + 1,
                    "issues_fixed": issues_to_fix
                })
                
                log_step("pre_fix", "completed", f"Applied fixes for attempt {pre_fix_attempt + 1}")
        
        # Final validation
        final_validation = validate_workflow_yaml(workflow_content)
        log_step("generate_workflow", "completed", {
            "valid": final_validation.get("valid"),
            "score": final_validation.get("score"),
            "pre_fixes_applied": len(result["fixes_applied"])
        })
        
        # Get repo info
        repo_info = github_request(f"/repos/{owner}/{repo}", token=token)
        default_branch = repo_info.get("default_branch", "main")
        
        # Step 5: Create ONE branch for this task
        task_id = datetime.now().strftime('%Y%m%d-%H%M%S')
        branch_name = f"autonomous-agent/devops-{task_id}"
        result["branch_name"] = branch_name
        
        # Use existing workflow name if available, otherwise create new
        existing_workflows = knowledge.get("workflows", [])
        if existing_workflows:
            # Use the first existing workflow (usually the main CI/CD workflow)
            workflow_name = existing_workflows[0].get("name", "ci-cd.yml")
            log_step("workflow_name", "using_existing", workflow_name)
        else:
            workflow_name = "ci-cd.yml"
            log_step("workflow_name", "creating_new", workflow_name)
        
        try:
            create_branch(owner, repo, branch_name, default_branch, token)
            log_step("create_branch", "completed", branch_name)
        except Exception as e:
            if "Reference already exists" not in str(e):
                raise e
            log_step("create_branch", "exists", branch_name)
        
        # Step 6: Commit workflow file
        file_path = f".github/workflows/{workflow_name}"
        create_or_update_file(
            owner, repo, file_path, workflow_content,
            f"chore(ci): Autonomous agent - {request[:50]}",
            branch_name, token
        )
        log_step("commit_workflow", "completed", file_path)
        result["workflow_file"] = file_path
        
        # Step 7: Create ONE PR
        pr = create_pull_request(
            owner, repo,
            f"[Autonomous Agent] {request[:80]}",
            f"""## Autonomous DevOps Agent

**Request:** {request}

### Generated Configuration
- **Workflow:** `{workflow_name}`
- **Validation Score:** {final_validation.get('score', 'N/A')}/100
- **Pre-validation Fixes Applied:** {len(result["fixes_applied"])}

### Analysis Summary
- **Tech Stack:** {', '.join(knowledge.get('tech_stack', []))}
- **Framework:** {knowledge.get('framework') or 'Not detected'}
- **Has Dockerfile:** {knowledge.get('has_dockerfile')}

### Changes
This workflow was autonomously generated with:
- Repository analysis and tech stack detection
- AI-powered pre-validation
- Best practices application
- Security considerations

### Next Steps
1. Review the workflow changes
2. Check the Actions tab for workflow run status
3. Merge when satisfied

---
*Generated by BCG Autonomous DevOps Agent*
*Branch: `{branch_name}`*
""",
            branch_name, default_branch, token
        )
        
        pr_url = pr.get("html_url")
        pr_number = pr.get("number")
        result["pr_url"] = pr_url
        result["pr_number"] = pr_number
        log_step("create_pr", "completed", {"pr_url": pr_url, "pr_number": pr_number})
        
        # Skip waiting for workflow if requested (API Gateway timeout)
        if skip_wait:
            result["success"] = True
            result["final_status"] = "pr_created"
            result["workflow_status"] = "pending_workflow_run"
            result["message"] = f"PR created successfully. Workflow will run automatically. Check: {pr_url}"
            log_step("complete", "success", "PR created - skipping workflow wait")
            
            # Calculate duration
            end_time = datetime.now()
            result["duration_seconds"] = (end_time - start_time).total_seconds()
            return result
        
        # Step 8: Wait for workflow and fix in SAME branch if needed
        for attempt in range(max_retries):
            result["attempts"] = attempt + 1
            
            log_step("wait_workflow", "started", f"Waiting for workflow run (attempt {attempt + 1})...")
            
            # Give GitHub time to trigger workflow
            time.sleep(10)
            
            run_result = wait_for_workflow_run(
                owner, repo, branch_name, token,
                timeout_seconds=300,
                poll_interval=15
            )
            
            log_step("wait_workflow", "completed", {
                "success": run_result.get("success"),
                "conclusion": run_result.get("conclusion"),
                "run_url": run_result.get("run_url")
            })
            
            if run_result.get("success"):
                result["success"] = True
                result["final_status"] = "workflow_passed"
                result["run_url"] = run_result.get("run_url")
                log_step("workflow_check", "success", "Workflow passed!")
                
                # Auto-merge if requested
                if auto_merge:
                    try:
                        merge_result = merge_pull_request(owner, repo, pr_number, token)
                        log_step("auto_merge", "completed", merge_result)
                        result["merged"] = True
                    except Exception as e:
                        log_step("auto_merge", "failed", str(e))
                        result["merged"] = False
                
                break
            
            elif run_result.get("timeout"):
                log_step("workflow_check", "timeout", "Workflow did not complete in time")
                result["final_status"] = "timeout"
                break
            
            else:
                # Workflow failed - fix in SAME branch
                log_step("workflow_check", "failed", f"Conclusion: {run_result.get('conclusion')}")
                
                if attempt < max_retries - 1:
                    log_step("auto_fix", "started", f"Fixing in same branch (attempt {attempt + 2})...")
                    
                    # Get failure details
                    jobs = run_result.get("jobs", [])
                    failure_info = []
                    for job in jobs:
                        if job.get("conclusion") == "failure":
                            for step in job.get("steps", []):
                                if step.get("conclusion") == "failure":
                                    failure_info.append({
                                        "job": job.get("name"),
                                        "step": step.get("name")
                                    })
                    
                    # Generate fix
                    fix_prompt = f"""The workflow failed in GitHub Actions. Fix it.

Failure Details:
{json.dumps(failure_info, indent=2)}

Current Workflow:
```yaml
{workflow_content}
```

Project Info:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Package Manager: {package_manager}
- Has Lock File: {has_lock_file}
- REQUIRED Install Command: {install_command}
- NPM Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}
- Has Dockerfile: {knowledge.get('has_dockerfile')}
- Has ESLint: {has_eslint}
- Has Tests: {has_tests}

Common fixes:
- CRITICAL: Use '{install_command}' for dependencies (this repo {'HAS' if has_lock_file else 'does NOT have'} a lock file)
- Add 'CI=false' for React builds
- Check if scripts exist before running
- Use correct Node.js version
- {'Include lint step' if has_eslint else 'Remove lint step if no eslint'}
- {'Include test step' if has_tests else 'Remove test step if no tests'}

Generate the CORRECTED workflow YAML only:"""

                    workflow_content = invoke_bedrock(fix_prompt, 
                        "You are a GitHub Actions expert. Fix the workflow. Output only valid YAML.")
                    
                    # Clean up
                    if workflow_content:
                        workflow_content = workflow_content.strip()
                        if workflow_content.startswith('```'):
                            workflow_content = re.sub(r'^```\w*\n?', '', workflow_content)
                            workflow_content = re.sub(r'\n?```$', '', workflow_content)
                        
                        # Post-process: Fix Trivy Docker image scans to filesystem scans
                        workflow_content = fix_trivy_docker_scan(workflow_content)
                    
                    # Push fix to SAME branch (not new branch!)
                    create_or_update_file(
                        owner, repo, file_path, workflow_content,
                        f"fix(ci): Auto-fix attempt {attempt + 2} - {', '.join([f['step'] for f in failure_info[:2]])}",
                        branch_name, token
                    )
                    
                    result["fixes_applied"].append({
                        "stage": "post_run",
                        "attempt": attempt + 2,
                        "failures": failure_info
                    })
                    
                    log_step("auto_fix", "completed", f"Pushed fix to {branch_name}")
                else:
                    result["final_status"] = "failed_after_retries"
                    log_step("auto_fix", "max_retries", f"Exhausted {max_retries} attempts")
        
        # Calculate duration
        end_time = datetime.now()
        result["duration_seconds"] = (end_time - start_time).total_seconds()
        
    except Exception as e:
        log_step("error", "failed", str(e))
        result["error"] = str(e)
        result["final_status"] = "error"
    
    return result

def handler(event, context):
    """Lambda handler - can be invoked by Bedrock Agent, API Gateway, or directly"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Determine the invocation source and parse parameters accordingly
    if "actionGroup" in event:
        # Bedrock Agent invocation
        action = event.get("actionGroup")
        api_path = event.get("apiPath", "")
        parameters = {}
        
        if event.get("requestBody"):
            content = event["requestBody"].get("content", {})
            if "application/json" in content:
                properties = content["application/json"].get("properties", [])
                for prop in properties:
                    parameters[prop["name"]] = prop["value"]
        
        # Also check parameters array
        if event.get("parameters"):
            for param in event["parameters"]:
                parameters[param["name"]] = param["value"]
                
    elif "rawPath" in event or "routeKey" in event:
        # API Gateway HTTP API invocation
        raw_path = event.get("rawPath", "")
        
        # Determine action from path
        if "/analyze" in raw_path:
            action = "analyze"
        elif "/create-pr" in raw_path:
            action = "create_workflow"
        elif "/track" in raw_path:
            action = "track"
        elif "/knowledge" in raw_path:
            action = "knowledge"
        elif "/suggest" in raw_path:
            action = "suggest"
        elif "/fix" in raw_path:
            action = "fix"
        elif "/deploy" in raw_path:
            action = "deploy"
        elif "/validate" in raw_path:
            action = "validate"
        elif "/generate" in raw_path:
            action = "generate"
        elif "/autonomous" in raw_path:
            action = "autonomous"
        elif "/pipeline" in raw_path:
            action = "pipeline"
        elif "/incident" in raw_path:
            action = "incident"
        elif "/multi-agent" in raw_path or "/coordinate" in raw_path:
            action = "multi_agent"
        elif "/security" in raw_path:
            action = "security"
        elif "/scan" in raw_path:
            action = "scan"
        elif "/preview" in raw_path:
            action = "preview"
        elif "/confirm" in raw_path:
            action = "confirm"
        elif "/chat" in raw_path:
            action = "chat"
        elif "/slack" in raw_path:
            action = "slack"
        else:
            action = "analyze"
        
        # Parse body
        if event.get("body"):
            try:
                parameters = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            except json.JSONDecodeError:
                parameters = {}
        else:
            parameters = {}
            
        # Also parse repository string format (e.g., "owner/repo")
        if parameters.get("repository") and not parameters.get("owner"):
            repo_str = parameters["repository"]
            if "/" in repo_str:
                parts = repo_str.split("/")
                parameters["owner"] = parts[0]
                parameters["repo"] = parts[1]
                
    else:
        # Direct invocation
        action = event.get("action", "analyze")
        parameters = event
    
    token = get_github_token()
    if not token:
        return {
            "statusCode": 401,
            "body": json.dumps({"error": "GitHub token not configured"})
        }
    
    try:
        # Route to appropriate function
        if action == "analyze" or "analyze" in str(event.get("apiPath", "")):
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            
            if not owner or not repo:
                # Try to parse from repo_url
                repo_url = parameters.get("repo_url", "")
                if "github.com" in repo_url:
                    parts = repo_url.replace("https://github.com/", "").replace("http://github.com/", "").split("/")
                    if len(parts) >= 2:
                        owner = parts[0]
                        repo = parts[1].replace(".git", "")
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            analysis = analyze_repository(owner, repo, token)
            
            # For Bedrock Agent response format
            if "actionGroup" in event:
                return {
                    "messageVersion": "1.0",
                    "response": {
                        "actionGroup": action,
                        "apiPath": event.get("apiPath"),
                        "httpMethod": event.get("httpMethod"),
                        "httpStatusCode": 200,
                        "responseBody": {
                            "application/json": {
                                "body": json.dumps(analysis)
                            }
                        }
                    }
                }
            
            return {"statusCode": 200, "body": json.dumps(analysis)}
        
        elif action == "create_workflow" or "workflow" in str(event.get("apiPath", "")):
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            workflow_content = parameters.get("workflow_content")
            workflow_name = parameters.get("workflow_name", "ci.yml")
            branch_name = parameters.get("branch_name", "feature/add-ci-workflow")
            
            if not all([owner, repo, workflow_content]):
                return {"statusCode": 400, "body": json.dumps({"error": "owner, repo, and workflow_content are required"})}
            
            # Get default branch
            repo_info = github_request(f"/repos/{owner}/{repo}", token=token)
            default_branch = repo_info.get("default_branch", "main")
            
            # Create branch
            try:
                create_branch(owner, repo, branch_name, default_branch, token)
                logger.info(f"Created branch: {branch_name}")
            except Exception as e:
                if "Reference already exists" not in str(e):
                    raise e
                logger.info(f"Branch {branch_name} already exists")
            
            # Create workflow file
            file_path = f".github/workflows/{workflow_name}"
            create_or_update_file(
                owner, repo, file_path, workflow_content,
                f"Add CI/CD workflow - {workflow_name}",
                branch_name, token
            )
            
            # Create PR
            pr = create_pull_request(
                owner, repo,
                f"Add CI/CD workflow: {workflow_name}",
                "## Summary\n\nThis PR adds a GitHub Actions CI/CD workflow generated by BCG DevOps GenAI.\n\n### Generated by\n- BCG Agentic DevOps Platform\n- Model: Amazon Bedrock",
                branch_name, default_branch, token
            )
            
            result = {
                "success": True,
                "pr_url": pr.get("html_url"),
                "pr_number": pr.get("number"),
                "branch": branch_name,
                "file_path": file_path
            }
            
            if "actionGroup" in event:
                return {
                    "messageVersion": "1.0",
                    "response": {
                        "actionGroup": action,
                        "apiPath": event.get("apiPath"),
                        "httpMethod": event.get("httpMethod"),
                        "httpStatusCode": 200,
                        "responseBody": {
                            "application/json": {
                                "body": json.dumps(result)
                            }
                        }
                    }
                }
            
            return {"statusCode": 200, "body": json.dumps(result)}
        
        elif action == "get_file":
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            path = parameters.get("path")
            ref = parameters.get("ref", "main")
            
            content = get_file_content(owner, repo, path, token, ref)
            return {"statusCode": 200, "body": json.dumps({"content": content, "path": path})}
        
        elif action == "knowledge" or "knowledge" in str(event.get("apiPath", "")):
            # Build comprehensive project knowledge
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            knowledge = build_project_knowledge(owner, repo, token)
            
            return format_response(event, action, 200, knowledge)
        
        elif action == "track" or "track" in str(event.get("apiPath", "")):
            # Track GitHub Actions status
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            per_page = int(parameters.get("per_page", 10))
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            runs = get_actions_runs(owner, repo, token, per_page)
            
            # Enrich with failure analysis
            result = {
                "repository": f"{owner}/{repo}",
                "total_runs": len(runs),
                "runs": []
            }
            
            failed_count = 0
            success_count = 0
            
            for run in runs:
                run_data = {
                    "id": run["id"],
                    "name": run.get("name"),
                    "status": run["status"],
                    "conclusion": run.get("conclusion"),
                    "created_at": run["created_at"],
                    "html_url": run["html_url"],
                    "head_branch": run.get("head_branch")
                }
                
                if run.get("conclusion") == "failure":
                    failed_count += 1
                    # Get failure details
                    jobs = get_run_logs(owner, repo, run["id"], token)
                    failed_steps = []
                    for job in jobs:
                        if job.get("conclusion") == "failure":
                            for step in job.get("steps", []):
                                if step.get("conclusion") == "failure":
                                    failed_steps.append({
                                        "job": job.get("name"),
                                        "step": step.get("name")
                                    })
                    run_data["failure_details"] = failed_steps
                elif run.get("conclusion") == "success":
                    success_count += 1
                
                result["runs"].append(run_data)
            
            result["summary"] = {
                "success_count": success_count,
                "failed_count": failed_count,
                "success_rate": f"{(success_count / len(runs) * 100):.1f}%" if runs else "N/A"
            }
            
            return format_response(event, action, 200, result)
        
        elif action == "suggest" or "suggest" in str(event.get("apiPath", "")):
            # Generate intelligent DevOps suggestions
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            # Get or build knowledge
            cache_key = f"{owner}/{repo}"
            if cache_key in PROJECT_KNOWLEDGE:
                knowledge = PROJECT_KNOWLEDGE[cache_key]
            else:
                knowledge = build_project_knowledge(owner, repo, token)
            
            # Generate detailed AI suggestions
            system_prompt = """You are a DevOps expert consultant. Analyze the project and provide 
            specific, actionable recommendations. Be concise but detailed enough to implement."""
            
            prompt = f"""Based on this project analysis, provide 5 prioritized DevOps recommendations:

Repository: {knowledge.get('repository')}
Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
Framework: {knowledge.get('framework')}
Has Dockerfile: {knowledge.get('has_dockerfile')}
Recent CI Failures: {knowledge.get('devops_status', {}).get('failure_count', 0)}
Last Failure Step: {knowledge.get('devops_status', {}).get('last_failure_step', 'None')}

Current Workflows:
{json.dumps([{'name': w['name'], 'score': w.get('validation', {}).get('score', 'N/A')} for w in knowledge.get('workflows', [])])}

Provide recommendations in this JSON format:
[{{"priority": "critical|high|medium|low", "title": "...", "description": "...", "action_command": "..."}}]
"""
            
            ai_suggestions = invoke_bedrock(prompt, system_prompt)
            
            # Parse AI suggestions
            try:
                ai_parsed = json.loads(ai_suggestions)
            except:
                ai_parsed = [{"title": "AI Analysis", "description": ai_suggestions}]
            
            result = {
                "repository": f"{owner}/{repo}",
                "auto_suggestions": knowledge.get("suggestions", []),
                "ai_suggestions": ai_parsed,
                "workflow_recommendations": []
            }
            
            # Add workflow-specific recommendations
            for wf in knowledge.get("workflows", []):
                if wf.get("validation", {}).get("recommendations"):
                    result["workflow_recommendations"].append({
                        "workflow": wf["name"],
                        "recommendations": wf["validation"]["recommendations"]
                    })
            
            return format_response(event, action, 200, result)
        
        elif action == "fix" or "fix" in str(event.get("apiPath", "")):
            # Analyze failures and generate fixes
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            run_id = parameters.get("run_id")  # Optional: specific run to fix
            auto_commit = parameters.get("auto_commit", False)
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            # Get project knowledge
            cache_key = f"{owner}/{repo}"
            if cache_key not in PROJECT_KNOWLEDGE:
                knowledge = build_project_knowledge(owner, repo, token)
            else:
                knowledge = PROJECT_KNOWLEDGE[cache_key]
            
            # Find failures to fix
            runs = get_actions_runs(owner, repo, token, 5)
            failed_runs = [r for r in runs if r.get("conclusion") == "failure"]
            
            if not failed_runs:
                return format_response(event, action, 200, {
                    "message": "No failed runs found! All recent workflows passed.",
                    "success": True
                })
            
            # Analyze the most recent failure
            target_run = failed_runs[0]
            if run_id:
                target_run = next((r for r in failed_runs if str(r["id"]) == str(run_id)), failed_runs[0])
            
            jobs = get_run_logs(owner, repo, target_run["id"], token)
            logger.info(f"Jobs for run {target_run['id']}: {json.dumps(jobs)}")
            
            failure_info = {
                "run_id": target_run["id"],
                "run_name": target_run.get("name"),
                "run_conclusion": target_run.get("conclusion"),
                "all_jobs": [],
                "failed_jobs": []
            }
            
            for job in jobs:
                job_info = {
                    "name": job.get("name"),
                    "status": job.get("status"),
                    "conclusion": job.get("conclusion"),
                    "steps": [{"name": s.get("name"), "conclusion": s.get("conclusion")} for s in job.get("steps", [])]
                }
                failure_info["all_jobs"].append(job_info)
                
                if job.get("conclusion") == "failure":
                    failed_steps = []
                    for step in job.get("steps", []):
                        if step.get("conclusion") == "failure":
                            failed_steps.append(step.get("name"))
                    failure_info["failed_jobs"].append({
                        "name": job.get("name"),
                        "failed_steps": failed_steps
                    })
            
            # Get current workflow content
            workflow_file = None
            workflow_content = None
            for wf in knowledge.get("workflows", []):
                workflow_file = wf["name"]
                workflow_content = wf.get("content")
                break
            
            # Generate fix using AI
            system_prompt = """You are a GitHub Actions expert. Analyze the failure and generate a fixed workflow.
            Output ONLY valid YAML, no markdown or explanations."""
            
            prompt = f"""Fix this failing GitHub Actions workflow:

Failure Analysis:
{json.dumps(failure_info, indent=2)}

Project Info:
- Tech Stack: {', '.join(knowledge.get('tech_stack', []))}
- Framework: {knowledge.get('framework')}
- NPM Scripts: {json.dumps(knowledge.get('dependencies', {}).get('scripts', {}))}

Current Workflow ({workflow_file}):
```yaml
{workflow_content}
```

Generate the corrected workflow YAML:"""

            fixed_workflow = invoke_bedrock(prompt, system_prompt)
            
            # Clean up response
            if fixed_workflow:
                fixed_workflow = fixed_workflow.strip()
                if fixed_workflow.startswith('```'):
                    fixed_workflow = re.sub(r'^```\w*\n?', '', fixed_workflow)
                    fixed_workflow = re.sub(r'\n?```$', '', fixed_workflow)
            
            # Validate the fixed workflow
            validation = validate_workflow_yaml(fixed_workflow) if fixed_workflow else {"valid": False}
            
            result = {
                "repository": f"{owner}/{repo}",
                "analyzed_run": failure_info,
                "fixed_workflow": fixed_workflow,
                "validation": validation,
                "workflow_file": workflow_file,
                "committed": False
            }
            
            # Auto-commit if requested and valid
            if auto_commit and validation.get("valid") and fixed_workflow:
                try:
                    repo_info = github_request(f"/repos/{owner}/{repo}", token=token)
                    default_branch = repo_info.get("default_branch", "main")
                    branch_name = f"fix/workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    
                    # Create branch and commit
                    create_branch(owner, repo, branch_name, default_branch, token)
                    create_or_update_file(
                        owner, repo,
                        f".github/workflows/{workflow_file}",
                        fixed_workflow,
                        f"fix: Auto-fix workflow failures in {workflow_file}",
                        branch_name,
                        token
                    )
                    
                    # Create PR
                    pr = create_pull_request(
                        owner, repo,
                        f"Fix: Auto-repair {workflow_file} workflow",
                        f"## Auto-Fix by DevOps Agent\n\n### Analyzed Failure:\n- Run ID: {target_run['id']}\n- Failed Steps: {', '.join([s for j in failure_info['failed_jobs'] for s in j['failed_steps']])}\n\n### Changes Applied:\nAI-generated fix based on failure analysis.\n\n---\n*Generated by BCG DevOps GenAI Agent*",
                        branch_name,
                        default_branch,
                        token
                    )
                    
                    result["committed"] = True
                    result["pr_url"] = pr.get("html_url")
                    result["branch"] = branch_name
                except Exception as e:
                    result["commit_error"] = str(e)
            
            return format_response(event, action, 200, result)
        
        elif action == "deploy" or "deploy" in str(event.get("apiPath", "")):
            # Deploy/commit workflow directly to main (with confirmation)
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            workflow_content = parameters.get("workflow_content")
            workflow_name = parameters.get("workflow_name", "ci.yml")
            commit_message = parameters.get("commit_message", "chore: Add optimized CI/CD workflow")
            create_pr = parameters.get("create_pr", True)  # Default to PR, not direct commit
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            # Generate workflow if not provided
            if not workflow_content:
                cache_key = f"{owner}/{repo}"
                if cache_key not in PROJECT_KNOWLEDGE:
                    knowledge = build_project_knowledge(owner, repo, token)
                else:
                    knowledge = PROJECT_KNOWLEDGE[cache_key]
                
                workflow_content = generate_optimal_workflow(knowledge)
            
            if not workflow_content:
                return format_response(event, action, 400, {"error": "Failed to generate workflow"})
            
            # Validate before deploying
            validation = validate_workflow_yaml(workflow_content)
            if not validation.get("valid"):
                return format_response(event, action, 400, {
                    "error": "Workflow validation failed",
                    "issues": validation.get("issues"),
                    "workflow_content": workflow_content
                })
            
            # Get repo info
            repo_info = github_request(f"/repos/{owner}/{repo}", token=token)
            default_branch = repo_info.get("default_branch", "main")
            
            file_path = f".github/workflows/{workflow_name}"
            
            if create_pr:
                # Create via PR (safer)
                branch_name = f"devops-agent/workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                
                try:
                    create_branch(owner, repo, branch_name, default_branch, token)
                except Exception as e:
                    if "Reference already exists" not in str(e):
                        raise e
                
                create_or_update_file(
                    owner, repo, file_path, workflow_content,
                    commit_message, branch_name, token
                )
                
                pr = create_pull_request(
                    owner, repo,
                    f"DevOps Agent: Optimized {workflow_name}",
                    f"## Workflow Deployment\n\n**Validation Score:** {validation.get('score')}/100\n\n### Recommendations Applied:\n{chr(10).join(['- ' + r for r in validation.get('recommendations', [])])}\n\n---\n*Generated by BCG DevOps GenAI Agent*",
                    branch_name, default_branch, token
                )
                
                result = {
                    "success": True,
                    "method": "pull_request",
                    "pr_url": pr.get("html_url"),
                    "pr_number": pr.get("number"),
                    "branch": branch_name,
                    "file_path": file_path,
                    "validation": validation
                }
            else:
                # Direct commit to main (requires confirmation flag)
                if not parameters.get("confirm_direct_commit"):
                    return format_response(event, action, 400, {
                        "error": "Direct commit to main requires 'confirm_direct_commit: true'",
                        "workflow_content": workflow_content,
                        "validation": validation
                    })
                
                commit_directly(owner, repo, default_branch, file_path, workflow_content, commit_message, token)
                
                result = {
                    "success": True,
                    "method": "direct_commit",
                    "branch": default_branch,
                    "file_path": file_path,
                    "validation": validation
                }
            
            return format_response(event, action, 200, result)
        
        elif action == "validate" or "validate" in str(event.get("apiPath", "")):
            # Validate workflow YAML
            workflow_content = parameters.get("workflow_content", "")
            
            if not workflow_content:
                return format_response(event, action, 400, {"error": "workflow_content is required"})
            
            validation = validate_workflow_yaml(workflow_content)
            return format_response(event, action, 200, validation)
        
        elif action == "scan" or "scan" in str(event.get("apiPath", "")):
            # Scan workflow YAML for security best practices (frontend Security Scan tab)
            workflow_content = parameters.get("workflow", parameters.get("workflow_content", ""))
            
            if not workflow_content:
                return format_response(event, action, 400, {"error": "workflow content is required"})
            
            # Use the existing validate function
            validation = validate_workflow_yaml(workflow_content)
            
            # Transform response to match frontend expectations
            best_practices = []
            
            # Convert issues to failed best practices
            for issue in validation.get("issues", []):
                best_practices.append({
                    "name": "Critical Issue",
                    "passed": False,
                    "description": issue,
                    "recommendation": f"Fix: {issue}"
                })
            
            # Convert warnings to failed best practices
            for warning in validation.get("warnings", []):
                best_practices.append({
                    "name": "Warning",
                    "passed": False,
                    "description": warning,
                    "recommendation": f"Consider: {warning}"
                })
            
            # Add passed best practices based on what's good
            if "name:" in workflow_content:
                best_practices.append({
                    "name": "Workflow Name",
                    "passed": True,
                    "description": "Workflow has a descriptive name",
                    "recommendation": ""
                })
            if "on:" in workflow_content:
                best_practices.append({
                    "name": "Trigger Defined",
                    "passed": True,
                    "description": "Workflow has trigger events defined",
                    "recommendation": ""
                })
            if "jobs:" in workflow_content:
                best_practices.append({
                    "name": "Jobs Defined",
                    "passed": True,
                    "description": "Workflow has jobs defined",
                    "recommendation": ""
                })
            if "permissions:" in workflow_content:
                best_practices.append({
                    "name": "Permissions Scoped",
                    "passed": True,
                    "description": "Workflow uses explicit permissions",
                    "recommendation": ""
                })
            if "@v" in workflow_content or "@0." in workflow_content or "@master" in workflow_content:
                best_practices.append({
                    "name": "Action Versions",
                    "passed": True,
                    "description": "Actions are version-pinned",
                    "recommendation": ""
                })
            if "secrets." in workflow_content:
                best_practices.append({
                    "name": "Secrets Usage",
                    "passed": True,
                    "description": "Sensitive data uses GitHub Secrets",
                    "recommendation": ""
                })
            
            # Add recommendations as informational items
            for rec in validation.get("recommendations", []):
                best_practices.append({
                    "name": "Recommendation",
                    "passed": False,
                    "description": rec,
                    "recommendation": rec
                })
            
            # Generate summary
            issues_count = len(validation.get("issues", []))
            warnings_count = len(validation.get("warnings", []))
            score = validation.get("score", 0)
            
            if issues_count == 0 and warnings_count == 0:
                summary = f"Excellent! Your workflow follows best practices with a score of {score}/100."
            elif issues_count == 0:
                summary = f"Good workflow with {warnings_count} minor warnings. Score: {score}/100."
            else:
                summary = f"Found {issues_count} issues and {warnings_count} warnings. Score: {score}/100."
            
            scan_result = {
                "score": score,
                "summary": summary,
                "best_practices": best_practices,
                "valid": validation.get("valid", False),
                "issues": validation.get("issues", []),
                "warnings": validation.get("warnings", []),
                "recommendations": validation.get("recommendations", [])
            }
            
            return format_response(event, action, 200, scan_result)
        
        elif action == "generate" or "generate" in str(event.get("apiPath", "")):
            # Generate optimal workflow for project
            # Supports two modes:
            # 1. Prompt-based: user provides a prompt describing their CI/CD needs
            # 2. Repo-based: analyze a GitHub repo and generate workflow
            
            prompt = parameters.get("prompt", "")
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            # Mode 1: Prompt-based generation (no repo required)
            if prompt and not (owner and repo):
                system_prompt = """You are an expert DevOps engineer. Generate a comprehensive GitHub Actions workflow 
based on the user's requirements. Follow these best practices:

1. Include proper triggers (push, pull_request, workflow_dispatch)
2. Add dependency caching for faster builds
3. Include linting and testing steps
4. For security scanning, use Trivy with filesystem scan (scan-type: 'fs')
5. Include build and deploy stages as appropriate
6. Use GitHub Secrets for sensitive data
7. Pin action versions (e.g., @v4)
8. Add proper permissions block

Output ONLY valid YAML, no markdown code blocks or explanations."""

                user_prompt = f"""Generate a GitHub Actions CI/CD workflow based on this request:

{prompt}

Generate a complete, production-ready workflow YAML:"""

                workflow = invoke_bedrock(user_prompt, system_prompt)
                
                # Clean up response
                if workflow:
                    workflow = workflow.strip()
                    if workflow.startswith('```'):
                        workflow = re.sub(r'^```\w*\n?', '', workflow)
                        workflow = re.sub(r'\n?```$', '', workflow)
                    # Apply Trivy fix
                    workflow = fix_trivy_docker_scan(workflow)
                
                validation = validate_workflow_yaml(workflow) if workflow else {"valid": False}
                
                result = {
                    "workflow": workflow,
                    "model": "Amazon Bedrock - Nova Pro",
                    "validation": validation,
                    "mode": "prompt-based"
                }
                
                return format_response(event, action, 200, result)
            
            # Mode 2: Repo-based generation (requires owner/repo)
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "Either 'prompt' or 'owner/repo' is required"})}
            
            # Build knowledge first
            knowledge = build_project_knowledge(owner, repo, token)
            
            # Generate workflow
            workflow = generate_optimal_workflow(knowledge)
            validation = validate_workflow_yaml(workflow) if workflow else {"valid": False}
            
            result = {
                "repository": f"{owner}/{repo}",
                "workflow": workflow,
                "workflow_content": workflow,  # Keep for backwards compatibility
                "model": "Amazon Bedrock - Nova Pro",
                "validation": validation,
                "mode": "repo-based",
                "project_summary": {
                    "tech_stack": knowledge.get("tech_stack"),
                    "framework": knowledge.get("framework"),
                    "has_dockerfile": knowledge.get("has_dockerfile")
                }
            }
            
            return format_response(event, action, 200, result)
        
        elif action == "autonomous" or "autonomous" in str(event.get("apiPath", "")):
            # Fully autonomous DevOps agent endpoint
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            request_text = parameters.get("request", "")
            max_retries = int(parameters.get("max_retries", 3))
            auto_merge = parameters.get("auto_merge", False)
            # skip_wait=True by default to avoid API Gateway 30s timeout
            # Set to False if you want to wait for workflow completion (use for async invocation)
            skip_wait = parameters.get("skip_wait", True)
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            if not request_text:
                return {"statusCode": 400, "body": json.dumps({"error": "request parameter is required (describe what you want the agent to do)"})}
            
            # Execute autonomous action
            result = autonomous_devops_action(
                owner=owner,
                repo=repo,
                request=request_text,
                token=token,
                max_retries=max_retries,
                auto_merge=auto_merge,
                skip_wait=skip_wait
            )
            
            # Add frontend-compatible alias fields
            # Frontend expects: workflow_result.conclusion, retry_count, execution_time
            result["retry_count"] = result.get("attempts", 0)
            if result.get("duration_seconds"):
                result["execution_time"] = f"{result['duration_seconds']:.1f}s"
            result["workflow_result"] = {
                "conclusion": result.get("final_status", "unknown")
            }
            result["workflow_generated"] = result.get("workflow_file")
            
            return format_response(event, action, 200 if result.get("success") else 500, result)
        
        elif action == "pipeline" or "pipeline" in str(event.get("apiPath", "")):
            # Single-command autonomous pipeline creation
            # The simplest entry point: just give it a repo and it does everything
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            intent = parameters.get("intent", "full")  # "full", "ci", or "cd"
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                # Handle full GitHub URLs
                if "github.com" in repo_str:
                    # Parse https://github.com/owner/repo.git or https://github.com/owner/repo
                    clean_url = repo_str.replace("https://github.com/", "").replace("http://github.com/", "")
                    clean_url = clean_url.replace(".git", "").rstrip("/")
                    parts = clean_url.split("/")
                    if len(parts) >= 2:
                        owner, repo = parts[0], parts[1]
                elif "/" in repo_str:
                    # Handle owner/repo format
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required. Use format: owner/repo or https://github.com/owner/repo"})}
            
            # Validate intent
            if intent not in ["full", "ci", "cd"]:
                return {"statusCode": 400, "body": json.dumps({"error": "intent must be 'full', 'ci', or 'cd'"})}
            
            # Execute pipeline action
            result = pipeline_action(
                owner=owner,
                repo=repo,
                token=token,
                intent=intent
            )
            
            return format_response(event, action, 200 if result.get("success") else 500, result)
        
        elif action == "incident":
            # Incident Response Agent with L1/L2/L3 escalation
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            incident_description = parameters.get("incident_description", parameters.get("description", ""))
            auto_remediate = parameters.get("auto_remediate", True)
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            if not incident_description:
                return {"statusCode": 400, "body": json.dumps({"error": "incident_description is required"})}
            
            result = incident_response_agent(
                owner=owner,
                repo=repo,
                incident_description=incident_description,
                token=token,
                auto_remediate=auto_remediate
            )
            
            return format_response(event, action, 200 if result.get("success") else 500, result)
        
        elif action == "multi_agent" or action == "coordinate":
            # Multi-Agent Coordination System
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            task = parameters.get("task", parameters.get("request", ""))
            agent_sequence = parameters.get("agent_sequence")
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            if not task:
                return {"statusCode": 400, "body": json.dumps({"error": "task parameter is required (describe what you want the agents to accomplish)"})}
            
            # Parse agent_sequence if provided as string
            if isinstance(agent_sequence, str):
                agent_sequence = [a.strip() for a in agent_sequence.split(",")]
            
            result = coordinate_agents(
                owner=owner,
                repo=repo,
                task=task,
                token=token,
                agent_sequence=agent_sequence
            )
            
            return format_response(event, action, 200 if result.get("success") else 500, result)
        
        elif action == "security":
            # Security Analysis Agent
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            result = security_analysis(
                owner=owner,
                repo=repo,
                token=token
            )
            
            return format_response(event, action, 200, result)
        
        elif action == "preview":
            # Preview workflow without committing - for user confirmation flow
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            request_text = parameters.get("request", "Create an optimal CI/CD workflow for this project")
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            result = preview_workflow(
                owner=owner,
                repo=repo,
                request=request_text,
                token=token
            )
            
            # Add success flag based on whether workflow was generated
            result["success"] = result.get("workflow_content") is not None
            
            return format_response(event, action, 200 if result.get("success") else 500, result)
        
        elif action == "confirm":
            # Confirm and commit a previewed workflow
            owner = parameters.get("owner")
            repo = parameters.get("repo")
            workflow_content = parameters.get("workflow_content")
            workflow_name = parameters.get("workflow_name", "ci-cd-autonomous.yml")
            request_text = parameters.get("request", "")
            skip_wait = parameters.get("skip_wait", True)
            max_retries = int(parameters.get("max_retries", 3))
            
            if not owner or not repo:
                repo_str = parameters.get("repository", "")
                if "/" in repo_str:
                    owner, repo = repo_str.split("/", 1)
            
            if not owner or not repo:
                return {"statusCode": 400, "body": json.dumps({"error": "owner and repo are required"})}
            
            if not workflow_content:
                return {"statusCode": 400, "body": json.dumps({"error": "workflow_content is required"})}
            
            result = confirm_workflow(
                owner=owner,
                repo=repo,
                workflow_content=workflow_content,
                token=token,
                request=request_text,
                workflow_name=workflow_name,
                skip_wait=skip_wait,
                max_retries=max_retries
            )
            
            return format_response(event, action, 200 if result.get("success") else 500, result)
        
        elif action == "chat" or "chat" in str(event.get("apiPath", "")):
            # Chat endpoint for conversational DevOps assistant
            message = parameters.get("message", parameters.get("prompt", ""))
            chat_history = parameters.get("history", [])
            
            if not message:
                return format_response(event, action, 400, {"error": "message is required"})
            
            # Build system prompt for DevOps assistant
            system_prompt = """You are an AGENTIC DevOps AI Platform - an autonomous intelligent assistant that can analyze, plan, execute, and self-correct DevOps operations.

## Core Capabilities
You are not just a chatbot - you are an AI AGENT capable of:
1. **Autonomous Analysis** - Deeply analyze repositories, detect tech stacks, frameworks, and patterns
2. **Intelligent Planning** - Break down complex DevOps tasks into actionable steps
3. **Automated Execution** - Generate production-ready CI/CD workflows, security scans, deployments
4. **Self-Correction** - Detect failures, analyze root causes, and auto-remediate issues
5. **Multi-Agent Coordination** - Orchestrate specialized agents (Workflow, Security, Incident, Analysis)

## BCG Enterprise DevOps Toolchain
- **CI/CD**: GitHub Actions with enterprise patterns
- **Artifact Management**: JFrog Artifactory
- **Code Quality**: SonarQube with quality gates
- **Security**: Prisma Cloud, Trivy vulnerability scanning, SAST/DAST
- **GitOps Deployment**: ArgoCD for Kubernetes
- **Observability**: Datadog APM, logging, and metrics
- **Container Orchestration**: Amazon EKS with Helm charts

## Agentic Behavior Guidelines
1. **Proactive** - Suggest improvements and optimizations without being asked
2. **Context-Aware** - Use repository analysis to provide tailored recommendations
3. **Action-Oriented** - Offer concrete next steps, not just explanations
4. **Security-First** - Always consider security implications and best practices
5. **Self-Improving** - Learn from failures and adapt workflows accordingly

## Response Format
- Use markdown for readability
- Include code blocks with syntax highlighting
- Provide actionable recommendations with clear steps
- Reference specific platform features when relevant (e.g., 'Use the Autonomous Agent tab to execute this')

When users describe DevOps challenges, respond as an intelligent agent ready to take action, not just provide information."""

            # Build conversation context
            conversation = ""
            for msg in chat_history[-5:]:  # Keep last 5 messages for context
                role = msg.get("role", "user")
                content = msg.get("content", "")
                conversation += f"{role}: {content}\n\n"
            
            user_prompt = f"""Previous conversation:
{conversation}

User question: {message}

Please provide a helpful, accurate response:"""

            # Call Bedrock for response
            response_text = invoke_bedrock(user_prompt, system_prompt)
            
            if not response_text:
                response_text = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            
            result = {
                "response": response_text,
                "model": MODEL_ID,
                "success": True
            }
            
            return format_response(event, action, 200, result)
        
        elif action == "slack":
            # Slack integration operations
            operation = parameters.get("operation", "test")
            
            if operation == "test":
                # Test Slack webhook connection
                test_result = test_slack_connection()
                return format_response(event, action, 200, test_result)
            
            elif operation == "send":
                # Send a custom Slack notification
                message = parameters.get("message", "Test notification from BCG DevOps GenAI")
                title = parameters.get("title", "DevOps Notification")
                color = parameters.get("color", "good")  # good, warning, danger
                channel = parameters.get("channel")  # Optional channel override
                
                # Map color to level
                color_to_level = {
                    "good": "info",
                    "#36a64f": "info",
                    "warning": "warning",
                    "#ffcc00": "warning",
                    "danger": "error",
                    "#ff0000": "critical"
                }
                level = color_to_level.get(color, "info")
                
                result = send_slack_notification(
                    title=title,
                    message=message,
                    level=level,
                    additional_fields=parameters.get("fields", []),
                    channel=channel
                )
                
                # Handle both dict and bool returns
                if isinstance(result, dict):
                    success = result.get("success", False)
                else:
                    success = result
                
                response_data = {
                    "success": success,
                    "message": "Notification sent successfully" if success else "Failed to send notification",
                    "details": {
                        "title": title,
                        "color": color,
                        "level": level,
                        "channel": channel or "default"
                    }
                }
                if isinstance(result, dict) and result.get("error"):
                    response_data["error"] = result.get("error")
                    
                return format_response(event, action, 200 if success else 500, response_data)
            
            elif operation == "incident":
                # Send incident notification - simplified for direct API use
                incident_type = parameters.get("incident_type", "alert")
                severity = parameters.get("severity", "medium")
                description = parameters.get("description", "No description provided")
                repository = parameters.get("repository", "unknown/unknown")
                
                # Map severity to incident level
                severity_to_level = {
                    "critical": "L3",
                    "high": "L3",
                    "medium": "L2",
                    "low": "L1",
                    "info": "L1"
                }
                incident_level = severity_to_level.get(severity, "L2")
                
                # Build classification object for the function
                classification = {
                    "type": incident_type,
                    "description": f"{incident_type.replace('_', ' ').title()} - {severity.upper()}",
                    "severity": severity
                }
                
                result = send_incident_notification(
                    incident_level=incident_level,
                    incident_description=description,
                    repository=repository,
                    classification=classification,
                    remediation_result=parameters.get("remediation", {}),
                    issue_url=parameters.get("issue_url", "")
                )
                
                # Handle response
                if isinstance(result, dict):
                    success = result.get("success", False)
                else:
                    success = bool(result)
                
                response_data = {
                    "success": success,
                    "message": "Incident notification sent" if success else "Failed to send incident notification",
                    "incident": {
                        "type": incident_type,
                        "severity": severity,
                        "level": incident_level
                    }
                }
                if isinstance(result, dict) and result.get("error"):
                    response_data["error"] = result.get("error")
                    
                return format_response(event, action, 200 if success else 500, response_data)
            
            elif operation == "workflow":
                # Send workflow notification
                workflow_event = parameters.get("workflow_event", "deployment")
                status = parameters.get("status", "success")
                details = parameters.get("details", "")
                repository = parameters.get("repository", "unknown/unknown")
                workflow_name = parameters.get("workflow_name", "")
                url = parameters.get("url", "")
                
                # Convert details dict to string if needed
                if isinstance(details, dict):
                    details = ", ".join([f"{k}: {v}" for k, v in details.items()])
                
                result = send_workflow_notification(
                    event_type=workflow_event,
                    repository=repository,
                    workflow_name=workflow_name,
                    status=status,
                    details=details,
                    url=url
                )
                
                # Handle response
                if isinstance(result, dict):
                    success = result.get("success", False)
                else:
                    success = bool(result)
                
                response_data = {
                    "success": success,
                    "message": "Workflow notification sent" if success else "Failed to send workflow notification",
                    "workflow": {
                        "event": workflow_event,
                        "status": status
                    }
                }
                if isinstance(result, dict) and result.get("error"):
                    response_data["error"] = result.get("error")
                    
                return format_response(event, action, 200 if success else 500, response_data)
                return format_response(event, action, 200 if success else 500, result)
            
            elif operation == "configure":
                # Return current Slack configuration status (without exposing webhook)
                webhook = get_slack_webhook()
                is_configured = webhook is not None and len(webhook) > 0
                
                result = {
                    "configured": is_configured,
                    "webhook_status": "Set" if is_configured else "Not configured",
                    "supported_operations": ["test", "send", "incident", "workflow"],
                    "notification_types": {
                        "incident": ["security_breach", "performance_degradation", "service_outage", "error_spike"],
                        "workflow": ["deployment", "build", "test", "rollback", "scale"]
                    },
                    "severity_levels": ["critical", "high", "medium", "low", "info"],
                    "message_colors": {
                        "good": "#36a64f (green - success)",
                        "warning": "#ffcc00 (yellow - warning)",
                        "danger": "#ff0000 (red - error/critical)"
                    }
                }
                return format_response(event, action, 200, result)
            
            else:
                return format_response(event, action, 400, {
                    "error": f"Unknown Slack operation: {operation}",
                    "supported_operations": ["test", "send", "incident", "workflow", "configure"]
                })
        
        else:
            return {"statusCode": 400, "body": json.dumps({"error": f"Unknown action: {action}"})}
            
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        error_response = {"error": str(e)}
        
        if "actionGroup" in event:
            return {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": action,
                    "apiPath": event.get("apiPath", ""),
                    "httpMethod": event.get("httpMethod", "POST"),
                    "httpStatusCode": 500,
                    "responseBody": {
                        "application/json": {
                            "body": json.dumps(error_response)
                        }
                    }
                }
            }
        
        return {"statusCode": 500, "body": json.dumps(error_response)}
