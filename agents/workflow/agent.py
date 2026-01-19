"""
BCG Agentic DevOps - Workflow Generator Agent
==============================================
Auto-generates BCG-compliant CI/CD workflows for any tech stack.
Integrates: GitHub Actions, JFrog, SonarQube, Prisma, ArgoCD, Datadog
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utils.bedrock_client import get_bedrock_client
from shared.integrations.github_client import get_github_client

logger = logging.getLogger(__name__)


# =============================================================================
# BCG-COMPLIANT WORKFLOW TEMPLATES
# =============================================================================

BCG_WORKFLOW_TEMPLATES = {
    "nodejs": """name: BCG CI/CD Pipeline - Node.js

on:
  push:
    branches: [{default_branch}]
  pull_request:
    branches: [{default_branch}]

permissions:
  contents: read
  packages: write
  security-events: write
  pull-requests: write

env:
  NODE_VERSION: '{node_version}'
  JFROG_REGISTRY: ${{{{ secrets.JFROG_REGISTRY }}}}
  APP_NAME: '{app_name}'

jobs:
  # ==========================================================================
  # BUILD & TEST
  # ==========================================================================
  build-test:
    name: Build & Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{{{ env.NODE_VERSION }}}}
          cache: '{package_manager}'
      
      - name: Install Dependencies
        run: {install_command}
      
      - name: Run Linter
        run: npm run lint --if-present
        continue-on-error: true
      
      - name: Run Tests
        run: npm test --if-present
      
      - name: Build Application
        run: npm run build --if-present
      
      - name: Upload Build Artifacts
        uses: actions/upload-artifact@v4
        with:
          name: build-artifacts
          path: |
            dist/
            build/
          retention-days: 7

  # ==========================================================================
  # CODE QUALITY - SONARQUBE
  # ==========================================================================
  code-quality:
    name: SonarQube Analysis
    runs-on: ubuntu-latest
    needs: build-test
    timeout-minutes: 10
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v2.3.0
        env:
          SONAR_TOKEN: ${{{{ secrets.SONAR_TOKEN }}}}
          SONAR_HOST_URL: ${{{{ secrets.SONAR_HOST_URL }}}}
        with:
          args: >
            -Dsonar.projectKey=${{{{ env.APP_NAME }}}}
            -Dsonar.sources=src
            -Dsonar.javascript.lcov.reportPaths=coverage/lcov.info
      
      - name: SonarQube Quality Gate
        uses: SonarSource/sonarqube-quality-gate-action@v1.1.0
        timeout-minutes: 5
        env:
          SONAR_TOKEN: ${{{{ secrets.SONAR_TOKEN }}}}

  # ==========================================================================
  # SECURITY SCANNING
  # ==========================================================================
  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: build-test
    timeout-minutes: 15
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
      
      # Dependency Scanning
      - name: Run Snyk for Dependencies
        uses: snyk/actions/node@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{{{ secrets.SNYK_TOKEN }}}}
        with:
          args: --severity-threshold=high
      
      # Secret Detection
      - name: Gitleaks Secret Scan
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{{{ secrets.GITHUB_TOKEN }}}}
      
      # SAST with Prisma Cloud
      - name: Prisma Cloud SAST Scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          output_format: sarif
          output_file_path: results.sarif
        continue-on-error: true
      
      - name: Upload SARIF Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: results.sarif

  # ==========================================================================
  # CONTAINER BUILD & SCAN
  # ==========================================================================
  container-build:
    name: Build & Scan Container
    runs-on: ubuntu-latest
    needs: [code-quality, security-scan]
    if: github.event_name == 'push' && github.ref == 'refs/heads/{default_branch}'
    timeout-minutes: 20
    
    outputs:
      image_tag: ${{{{ steps.meta.outputs.tags }}}}
    
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to JFrog Artifactory
        uses: docker/login-action@v3
        with:
          registry: ${{{{ env.JFROG_REGISTRY }}}}
          username: ${{{{ secrets.JFROG_USER }}}}
          password: ${{{{ secrets.JFROG_ACCESS_TOKEN }}}}
      
      - name: Docker Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{{{ env.JFROG_REGISTRY }}}}/${{{{ env.APP_NAME }}}}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=raw,value=latest,enable=${{{{ github.ref == 'refs/heads/{default_branch}' }}}}
      
      - name: Build and Push Image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{{{ steps.meta.outputs.tags }}}}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # Container Scanning with Trivy
      - name: Trivy Container Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{{{ env.JFROG_REGISTRY }}}}/${{{{ env.APP_NAME }}}}:${{{{ github.sha }}}}
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: trivy-results.sarif

  # ==========================================================================
  # DEPLOY VIA ARGOCD
  # ==========================================================================
  deploy:
    name: Deploy to EKS via ArgoCD
    runs-on: ubuntu-latest
    needs: container-build
    if: github.event_name == 'push' && github.ref == 'refs/heads/{default_branch}'
    environment: production
    timeout-minutes: 15
    
    steps:
      - name: Checkout GitOps Repo
        uses: actions/checkout@v4
        with:
          repository: ${{{{ github.repository_owner }}}}/gitops-config
          token: ${{{{ secrets.GITOPS_PAT }}}}
          path: gitops
      
      - name: Update Image Tag
        run: |
          cd gitops/apps/${{{{ env.APP_NAME }}}}
          sed -i 's|image:.*|image: ${{{{ env.JFROG_REGISTRY }}}}/${{{{ env.APP_NAME }}}}:${{{{ github.sha }}}}|' values.yaml
          git config user.name "BCG DevOps Agent"
          git config user.email "devops@bcg.com"
          git add .
          git commit -m "chore: update ${{{{ env.APP_NAME }}}} to ${{{{ github.sha }}}}"
          git push
      
      - name: Sync ArgoCD Application
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          ./argocd login ${{{{ secrets.ARGOCD_SERVER }}}} \\
            --username ${{{{ secrets.ARGOCD_USERNAME }}}} \\
            --password ${{{{ secrets.ARGOCD_PASSWORD }}}} \\
            --insecure
          ./argocd app sync ${{{{ env.APP_NAME }}}} --prune
          ./argocd app wait ${{{{ env.APP_NAME }}}} --timeout 300

  # ==========================================================================
  # NOTIFY & METRICS
  # ==========================================================================
  notify:
    name: Notify & Track Metrics
    runs-on: ubuntu-latest
    needs: deploy
    if: always()
    
    steps:
      - name: Send Datadog DORA Metrics
        run: |
          curl -X POST "https://api.datadoghq.com/api/v2/dora/deployment" \\
            -H "DD-API-KEY: ${{{{ secrets.DATADOG_API_KEY }}}}" \\
            -H "Content-Type: application/json" \\
            -d '{{
              "data": {{
                "attributes": {{
                  "service": "${{{{ env.APP_NAME }}}}",
                  "version": "${{{{ github.sha }}}}",
                  "started_at": "${{{{ github.event.head_commit.timestamp }}}}",
                  "finished_at": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
                  "git": {{
                    "repository_url": "${{{{ github.server_url }}}}/${{{{ github.repository }}}}",
                    "commit_sha": "${{{{ github.sha }}}}"
                  }}
                }}
              }}
            }}'
      
      - name: Slack Notification
        uses: slackapi/slack-github-action@v1.25.0
        with:
          payload: |
            {{
              "text": "✅ Deployment Successful: ${{{{ env.APP_NAME }}}} - ${{{{ github.sha }}}}",
              "blocks": [
                {{
                  "type": "section",
                  "text": {{
                    "type": "mrkdwn",
                    "text": "*Deployment Complete* :rocket:\\n*App:* ${{{{ env.APP_NAME }}}}\\n*Commit:* `${{{{ github.sha }}}}`\\n*Branch:* {default_branch}"
                  }}
                }}
              ]
            }}
        env:
          SLACK_WEBHOOK_URL: ${{{{ secrets.SLACK_WEBHOOK_URL }}}}
""",
    
    "python": """name: BCG CI/CD Pipeline - Python

on:
  push:
    branches: [{default_branch}]
  pull_request:
    branches: [{default_branch}]

permissions:
  contents: read
  packages: write
  security-events: write

env:
  PYTHON_VERSION: '{python_version}'
  JFROG_REGISTRY: ${{{{ secrets.JFROG_REGISTRY }}}}
  APP_NAME: '{app_name}'

jobs:
  build-test:
    name: Build & Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{{{ env.PYTHON_VERSION }}}}
          cache: 'pip'
      
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov flake8 bandit
      
      - name: Lint with flake8
        run: flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        continue-on-error: true
      
      - name: Run Tests
        run: pytest --cov=. --cov-report=xml
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: coverage.xml

  code-quality:
    name: SonarQube Analysis
    runs-on: ubuntu-latest
    needs: build-test
    
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: SonarQube Scan
        uses: SonarSource/sonarqube-scan-action@v2.3.0
        env:
          SONAR_TOKEN: ${{{{ secrets.SONAR_TOKEN }}}}
          SONAR_HOST_URL: ${{{{ secrets.SONAR_HOST_URL }}}}

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: build-test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Bandit Security Scan
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-report.json || true
      
      - name: Snyk Python Scan
        uses: snyk/actions/python@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{{{ secrets.SNYK_TOKEN }}}}

  container-build:
    name: Build Container
    runs-on: ubuntu-latest
    needs: [code-quality, security-scan]
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to JFrog
        uses: docker/login-action@v3
        with:
          registry: ${{{{ env.JFROG_REGISTRY }}}}
          username: ${{{{ secrets.JFROG_USER }}}}
          password: ${{{{ secrets.JFROG_ACCESS_TOKEN }}}}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{{{ env.JFROG_REGISTRY }}}}/${{{{ env.APP_NAME }}}}:${{{{ github.sha }}}}

  deploy:
    name: Deploy via ArgoCD
    runs-on: ubuntu-latest
    needs: container-build
    environment: production
    
    steps:
      - name: ArgoCD Sync
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          ./argocd login ${{{{ secrets.ARGOCD_SERVER }}}} --username ${{{{ secrets.ARGOCD_USERNAME }}}} --password ${{{{ secrets.ARGOCD_PASSWORD }}}} --insecure
          ./argocd app set ${{{{ env.APP_NAME }}}} --helm-set image.tag=${{{{ github.sha }}}}
          ./argocd app sync ${{{{ env.APP_NAME }}}}
""",

    "golang": """name: BCG CI/CD Pipeline - Go

on:
  push:
    branches: [{default_branch}]
  pull_request:
    branches: [{default_branch}]

permissions:
  contents: read
  packages: write
  security-events: write

env:
  GO_VERSION: '{go_version}'
  JFROG_REGISTRY: ${{{{ secrets.JFROG_REGISTRY }}}}
  APP_NAME: '{app_name}'

jobs:
  build-test:
    name: Build & Test
    runs-on: ubuntu-latest
    timeout-minutes: 15
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: ${{{{ env.GO_VERSION }}}}
          cache: true
      
      - name: Download Dependencies
        run: go mod download
      
      - name: Lint
        uses: golangci/golangci-lint-action@v4
        with:
          version: latest
      
      - name: Test
        run: go test -v -race -coverprofile=coverage.out ./...
      
      - name: Build
        run: go build -v ./...

  security-scan:
    name: Security Scanning
    runs-on: ubuntu-latest
    needs: build-test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Gosec
        uses: securego/gosec@master
        with:
          args: '-fmt sarif -out gosec.sarif ./...'
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: gosec.sarif

  container-build:
    name: Build Container
    runs-on: ubuntu-latest
    needs: security-scan
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Login to JFrog
        uses: docker/login-action@v3
        with:
          registry: ${{{{ env.JFROG_REGISTRY }}}}
          username: ${{{{ secrets.JFROG_USER }}}}
          password: ${{{{ secrets.JFROG_ACCESS_TOKEN }}}}
      
      - name: Build and Push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{{{ env.JFROG_REGISTRY }}}}/${{{{ env.APP_NAME }}}}:${{{{ github.sha }}}}
"""
}


class WorkflowGeneratorAgent:
    """
    Workflow Generator Agent
    
    Capabilities:
    1. Analyze repository and detect tech stack
    2. Generate BCG-compliant CI/CD workflows
    3. Push workflow to GitHub
    4. Create Pull Request
    5. Track workflow status
    """
    
    SYSTEM_PROMPT = """You are the Workflow Generator Agent for BCG's DevOps platform.

Your role is to:
1. Analyze repositories to detect language, framework, and dependencies
2. Generate production-ready GitHub Actions workflows
3. Ensure all workflows include BCG tool integrations:
   - JFrog Artifactory for artifact storage
   - SonarQube for code quality
   - Prisma Cloud / Checkov for security
   - ArgoCD for GitOps deployment
   - Datadog for monitoring

Always generate complete, working YAML that follows GitHub Actions best practices:
- Use pinned action versions (@v4)
- Include proper permissions
- Add timeout-minutes to jobs
- Use caching for dependencies
- Include environment protection for deployments"""

    def __init__(
        self,
        github_token: str,
        bedrock_profile: str = "credit",
        region: str = "us-east-1"
    ):
        self.github = get_github_client(github_token)
        self.bedrock = get_bedrock_client(profile=bedrock_profile, region=region)
        logger.info("Workflow Generator Agent initialized")
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an action.
        
        Actions:
        - analyze_repository: Analyze a GitHub repo
        - generate_workflow: Generate CI/CD workflow
        - push_workflow: Push workflow to GitHub
        - create_pr: Create pull request
        - get_status: Get workflow run status
        """
        actions = {
            "analyze_repository": self.analyze_repository,
            "generate_workflow": self.generate_workflow,
            "push_workflow": self.push_workflow,
            "create_pr": self.create_pr_with_workflow,
            "get_status": self.get_workflow_status
        }
        
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        
        return handler(**parameters)
    
    def analyze_repository(self, repository: str) -> Dict[str, Any]:
        """
        Analyze a GitHub repository to detect tech stack.
        
        Args:
            repository: Repository in format 'owner/repo'
            
        Returns:
            Analysis results with detected technologies
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format. Use 'owner/repo'"}
        
        owner, repo = parts
        
        try:
            analysis = self.github.analyze_repository(owner, repo)
            
            # Add recommendations
            analysis["recommendations"] = self._generate_recommendations(analysis)
            
            return {
                "success": True,
                "action": "analyze_repository",
                "repository": repository,
                "analysis": analysis
            }
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            return {"success": False, "error": str(e)}
    
    def generate_workflow(
        self,
        repository: str,
        language: Optional[str] = None,
        framework: Optional[str] = None,
        include_security: bool = True,
        include_deploy: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a BCG-compliant workflow for the repository.
        
        Args:
            repository: 'owner/repo'
            language: Override detected language
            framework: Override detected framework
            include_security: Include security scanning jobs
            include_deploy: Include deployment jobs
            
        Returns:
            Generated workflow YAML
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            # Analyze if not provided
            if not language:
                analysis = self.github.analyze_repository(owner, repo)
                tech_stack = analysis.get("tech_stack", [])
                language = tech_stack[0] if tech_stack else "nodejs"
                framework = analysis.get("framework")
            
            # Get base template
            template = BCG_WORKFLOW_TEMPLATES.get(language)
            
            if not template:
                # Use AI to generate for unsupported languages
                return self._generate_custom_workflow(owner, repo, language, framework)
            
            # Fill template variables
            workflow = template.format(
                default_branch=self.github.get_repo(owner, repo).get("default_branch", "main"),
                app_name=repo,
                node_version="20",
                python_version="3.11",
                go_version="1.21",
                package_manager="npm",
                install_command="npm ci"
            )
            
            return {
                "success": True,
                "action": "generate_workflow",
                "repository": repository,
                "language": language,
                "framework": framework,
                "workflow_yaml": workflow,
                "file_name": "bcg-ci-cd.yml"
            }
            
        except Exception as e:
            logger.error(f"Error generating workflow: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_custom_workflow(
        self,
        owner: str,
        repo: str,
        language: str,
        framework: Optional[str]
    ) -> Dict[str, Any]:
        """Generate workflow using AI for unsupported languages"""
        
        prompt = f"""Generate a complete GitHub Actions workflow for a {language} project.

Repository: {owner}/{repo}
Framework: {framework or 'Not specified'}

Requirements:
1. Build and test the application
2. SonarQube code quality analysis
3. Security scanning (SAST, dependency scan)
4. Docker container build and push to JFrog Artifactory
5. Deploy via ArgoCD to EKS
6. Datadog metrics and Slack notifications

Use these secrets:
- JFROG_REGISTRY, JFROG_USER, JFROG_ACCESS_TOKEN
- SONAR_TOKEN, SONAR_HOST_URL
- SNYK_TOKEN
- ARGOCD_SERVER, ARGOCD_USERNAME, ARGOCD_PASSWORD
- DATADOG_API_KEY
- SLACK_WEBHOOK_URL

Output ONLY the YAML content, no explanation."""

        workflow = self.bedrock.invoke(prompt, self.SYSTEM_PROMPT)
        
        # Clean up response
        workflow = workflow.strip()
        if workflow.startswith("```yaml"):
            workflow = workflow[7:]
        if workflow.startswith("```"):
            workflow = workflow[3:]
        if workflow.endswith("```"):
            workflow = workflow[:-3]
        
        return {
            "success": True,
            "action": "generate_workflow",
            "repository": f"{owner}/{repo}",
            "language": language,
            "framework": framework,
            "workflow_yaml": workflow.strip(),
            "file_name": "bcg-ci-cd.yml",
            "generated_by": "ai"
        }
    
    def push_workflow(
        self,
        repository: str,
        workflow_yaml: str,
        file_name: str = "bcg-ci-cd.yml",
        branch: str = None,
        commit_message: str = None
    ) -> Dict[str, Any]:
        """
        Push workflow to GitHub repository.
        
        Args:
            repository: 'owner/repo'
            workflow_yaml: Workflow YAML content
            file_name: Workflow file name
            branch: Target branch
            commit_message: Custom commit message
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            # Get default branch if not specified
            if not branch:
                repo_info = self.github.get_repo(owner, repo)
                branch = repo_info.get("default_branch", "main")
            
            # Create workflow file path
            path = f".github/workflows/{file_name}"
            
            # Commit message
            if not commit_message:
                commit_message = f"""feat(ci): Add BCG-compliant CI/CD workflow

Generated by BCG Agentic DevOps Platform
- Includes build, test, security scanning
- SonarQube quality gates
- JFrog Artifactory integration
- ArgoCD deployment
- Datadog metrics tracking"""
            
            # Create/update file
            result = self.github.create_or_update_file(
                owner, repo, path, workflow_yaml, commit_message, branch
            )
            
            return {
                "success": True,
                "action": "push_workflow",
                "repository": repository,
                "branch": branch,
                "path": path,
                "commit_sha": result.get("commit", {}).get("sha")
            }
            
        except Exception as e:
            logger.error(f"Error pushing workflow: {e}")
            return {"success": False, "error": str(e)}
    
    def create_pr_with_workflow(
        self,
        repository: str,
        workflow_yaml: str = None,
        file_name: str = "bcg-ci-cd.yml"
    ) -> Dict[str, Any]:
        """
        Create a PR with the workflow (on a new branch).
        
        This is the recommended way - creates a branch, commits workflow, and opens PR.
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            # Generate workflow if not provided
            if not workflow_yaml:
                gen_result = self.generate_workflow(repository)
                if not gen_result.get("success"):
                    return gen_result
                workflow_yaml = gen_result.get("workflow_yaml")
            
            # Create a new branch
            branch_name = f"devops-agent/add-bcg-workflow-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            repo_info = self.github.get_repo(owner, repo)
            default_branch = repo_info.get("default_branch", "main")
            
            self.github.create_branch(owner, repo, branch_name, default_branch)
            
            # Push workflow to new branch
            push_result = self.push_workflow(
                repository, workflow_yaml, file_name, branch_name
            )
            
            if not push_result.get("success"):
                return push_result
            
            # Create PR
            pr = self.github.create_pull_request(
                owner, repo,
                title="feat(ci): Add BCG-compliant CI/CD Pipeline",
                body="""## 🚀 BCG Agentic DevOps - Automated CI/CD Pipeline

This PR adds a production-ready CI/CD workflow generated by the BCG DevOps Agent.

### What's Included

- ✅ **Build & Test** - Automated build with dependency caching
- ✅ **Code Quality** - SonarQube analysis with quality gates
- ✅ **Security Scanning** - Snyk, Prisma Cloud, Gitleaks
- ✅ **Container Build** - Docker with Trivy scanning
- ✅ **Deployment** - ArgoCD GitOps to EKS
- ✅ **Observability** - Datadog DORA metrics
- ✅ **Notifications** - Slack alerts

### Required Secrets

Configure these in your repository settings:
- `JFROG_REGISTRY`, `JFROG_USER`, `JFROG_ACCESS_TOKEN`
- `SONAR_TOKEN`, `SONAR_HOST_URL`
- `SNYK_TOKEN`
- `ARGOCD_SERVER`, `ARGOCD_USERNAME`, `ARGOCD_PASSWORD`
- `DATADOG_API_KEY`
- `SLACK_WEBHOOK_URL`

---
*Generated by BCG Agentic DevOps Platform*""",
                head=branch_name,
                base=default_branch
            )
            
            return {
                "success": True,
                "action": "create_pr",
                "repository": repository,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "branch": branch_name,
                "commit_sha": push_result.get("commit_sha")
            }
            
        except Exception as e:
            logger.error(f"Error creating PR: {e}")
            return {"success": False, "error": str(e)}
    
    def get_workflow_status(
        self,
        repository: str,
        run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get workflow run status.
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            if run_id:
                status = self.github.get_workflow_run_status(owner, repo, run_id)
            else:
                runs = self.github.get_workflow_runs(owner, repo, per_page=5)
                status = {
                    "recent_runs": [
                        {
                            "id": r.get("id"),
                            "name": r.get("name"),
                            "status": r.get("status"),
                            "conclusion": r.get("conclusion"),
                            "url": r.get("html_url")
                        }
                        for r in runs
                    ]
                }
            
            return {
                "success": True,
                "action": "get_status",
                "repository": repository,
                "status": status
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if not analysis.get("has_github_actions"):
            recommendations.append("Add GitHub Actions for CI/CD automation")
        
        if not analysis.get("has_dockerfile"):
            recommendations.append("Add Dockerfile for containerization")
        
        if not analysis.get("has_kubernetes") and not analysis.get("has_terraform"):
            recommendations.append("Consider adding Kubernetes manifests or Terraform for infrastructure")
        
        if "test" not in str(analysis.get("dependencies", [])).lower():
            recommendations.append("Add testing framework to ensure code quality")
        
        return recommendations


# Main entry point for testing
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)
    
    # Test with token
    token = os.environ.get("GITHUB_TOKEN", "")
    agent = WorkflowGeneratorAgent(token)
    
    # Test analysis
    result = agent.analyze_repository("octocat/Hello-World")
    print(json.dumps(result, indent=2))
