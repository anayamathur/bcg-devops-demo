"""
BCG Agentic DevOps - Configuration Settings
============================================
Central configuration for all agents and integrations.
"""

import os
from dataclasses import dataclass
from typing import Optional

# =============================================================================
# AWS Configuration
# =============================================================================
AWS_PROFILE = os.environ.get("AWS_PROFILE", "credit")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Bedrock Model Configuration
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
BEDROCK_MAX_TOKENS = int(os.environ.get("BEDROCK_MAX_TOKENS", "8192"))
BEDROCK_TEMPERATURE = float(os.environ.get("BEDROCK_TEMPERATURE", "0.3"))

# =============================================================================
# GitHub Configuration
# =============================================================================
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API_BASE = "https://api.github.com"
GITHUB_DEFAULT_BRANCH = "main"

# =============================================================================
# BCG Tool Chain Configuration
# =============================================================================

@dataclass
class ToolConfig:
    """Configuration for external DevOps tools"""
    name: str
    enabled: bool
    base_url: str
    api_key: Optional[str] = None
    token: Optional[str] = None

# JFrog Artifactory
JFROG_CONFIG = ToolConfig(
    name="JFrog Artifactory",
    enabled=True,
    base_url=os.environ.get("JFROG_URL", ""),
    api_key=os.environ.get("JFROG_API_KEY", "")
)

# SonarQube
SONARQUBE_CONFIG = ToolConfig(
    name="SonarQube",
    enabled=True,
    base_url=os.environ.get("SONARQUBE_URL", ""),
    token=os.environ.get("SONARQUBE_TOKEN", "")
)

# Prisma Cloud
PRISMA_CONFIG = ToolConfig(
    name="Prisma Cloud",
    enabled=True,
    base_url=os.environ.get("PRISMA_URL", ""),
    api_key=os.environ.get("PRISMA_ACCESS_KEY", "")
)

# ArgoCD
ARGOCD_CONFIG = ToolConfig(
    name="ArgoCD",
    enabled=True,
    base_url=os.environ.get("ARGOCD_URL", ""),
    token=os.environ.get("ARGOCD_TOKEN", "")
)

# Octopus Deploy
OCTOPUS_CONFIG = ToolConfig(
    name="Octopus Deploy",
    enabled=True,
    base_url=os.environ.get("OCTOPUS_URL", ""),
    api_key=os.environ.get("OCTOPUS_API_KEY", "")
)

# Datadog
DATADOG_CONFIG = ToolConfig(
    name="Datadog",
    enabled=True,
    base_url=os.environ.get("DATADOG_SITE", "datadoghq.com"),
    api_key=os.environ.get("DATADOG_API_KEY", "")
)

# Slack
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#devops-alerts")

# =============================================================================
# Agent Configuration
# =============================================================================

# Agent Types
class AgentType:
    SUPERVISOR = "supervisor"
    WORKFLOW = "workflow_generator"
    SECURITY = "security_remediation"
    INCIDENT = "incident_response"

# Agent Capabilities
AGENT_CAPABILITIES = {
    AgentType.SUPERVISOR: [
        "route_request",
        "orchestrate_agents",
        "manage_context",
        "human_approval"
    ],
    AgentType.WORKFLOW: [
        "analyze_repository",
        "detect_tech_stack",
        "generate_workflow",
        "create_pr",
        "validate_workflow"
    ],
    AgentType.SECURITY: [
        "aggregate_findings",
        "analyze_vulnerabilities",
        "suggest_fixes",
        "create_fix_pr",
        "generate_report"
    ],
    AgentType.INCIDENT: [
        "triage_alert",
        "correlate_events",
        "generate_rca",
        "execute_runbook",
        "notify_team"
    ]
}

# =============================================================================
# Supported Tech Stacks (BCG Requirement)
# =============================================================================

SUPPORTED_LANGUAGES = {
    "nodejs": {
        "name": "Node.js",
        "files": ["package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"],
        "extensions": [".js", ".ts", ".jsx", ".tsx", ".mjs"],
        "frameworks": ["react", "vue", "angular", "express", "nestjs", "nextjs", "fastify"],
        "package_managers": ["npm", "yarn", "pnpm"]
    },
    "python": {
        "name": "Python",
        "files": ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile", "poetry.lock"],
        "extensions": [".py", ".pyx"],
        "frameworks": ["django", "flask", "fastapi", "pytorch", "tensorflow"],
        "package_managers": ["pip", "poetry", "pipenv", "conda"]
    },
    "golang": {
        "name": "Go",
        "files": ["go.mod", "go.sum"],
        "extensions": [".go"],
        "frameworks": ["gin", "echo", "fiber", "chi", "gorilla"],
        "package_managers": ["go mod"]
    },
    "java": {
        "name": "Java",
        "files": ["pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle"],
        "extensions": [".java", ".kt"],
        "frameworks": ["spring", "springboot", "quarkus", "micronaut"],
        "package_managers": ["maven", "gradle"]
    },
    "dotnet": {
        "name": ".NET",
        "files": ["*.csproj", "*.fsproj", "*.sln", "nuget.config"],
        "extensions": [".cs", ".fs", ".vb"],
        "frameworks": ["aspnet", "blazor", "maui"],
        "package_managers": ["nuget", "dotnet"]
    },
    "rust": {
        "name": "Rust",
        "files": ["Cargo.toml", "Cargo.lock"],
        "extensions": [".rs"],
        "frameworks": ["actix", "rocket", "axum", "warp"],
        "package_managers": ["cargo"]
    }
}

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
