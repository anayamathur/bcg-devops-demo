"""
BCG Agentic DevOps - GitHub Integration
========================================
GitHub API integration for repository operations.
"""

import json
import base64
import urllib.request
import urllib.error
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"


class GitHubClient:
    """
    GitHub API client for repository operations.
    Supports: repo analysis, file ops, workflow management, PR creation.
    """
    
    def __init__(self, token: str):
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'BCG-Agentic-DevOps/1.0',
            'Content-Type': 'application/json'
        }
    
    def _request(
        self,
        endpoint: str,
        method: str = 'GET',
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make GitHub API request"""
        url = f"{GITHUB_API}{endpoint}" if not endpoint.startswith('http') else endpoint
        
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, headers=self.headers, method=method)
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            logger.error(f"GitHub API error: {e.code} - {error_body}")
            raise Exception(f"GitHub API error: {e.code} - {error_body}")
    
    # =========================================================================
    # Repository Operations
    # =========================================================================
    
    def get_repo(self, owner: str, repo: str) -> Dict[str, Any]:
        """Get repository information"""
        return self._request(f"/repos/{owner}/{repo}")
    
    def get_repo_languages(self, owner: str, repo: str) -> Dict[str, int]:
        """Get repository languages"""
        return self._request(f"/repos/{owner}/{repo}/languages")
    
    def get_repo_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        ref: str = "main"
    ) -> List[Dict[str, Any]]:
        """Get repository contents at path"""
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        if ref:
            endpoint += f"?ref={ref}"
        return self._request(endpoint)
    
    def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str = "main"
    ) -> str:
        """Get file content decoded from base64"""
        try:
            result = self._request(f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
            if result.get('content'):
                return base64.b64decode(result['content']).decode('utf-8')
            return ""
        except Exception as e:
            logger.warning(f"Could not get file {path}: {e}")
            return ""
    
    # =========================================================================
    # Repository Analysis
    # =========================================================================
    
    def analyze_repository(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Comprehensive repository analysis.
        Detects: language, framework, dependencies, CI/CD status, etc.
        """
        analysis = {
            "repository": f"{owner}/{repo}",
            "analyzed_at": datetime.now().isoformat(),
            "primary_language": None,
            "languages": {},
            "tech_stack": [],
            "framework": None,
            "package_manager": None,
            "has_dockerfile": False,
            "has_docker_compose": False,
            "has_kubernetes": False,
            "has_terraform": False,
            "has_github_actions": False,
            "existing_workflows": [],
            "dependencies": [],
            "default_branch": "main",
            "confidence": 0.0
        }
        
        try:
            # Get repo info
            repo_info = self.get_repo(owner, repo)
            analysis["default_branch"] = repo_info.get("default_branch", "main")
            lang = repo_info.get("language")
            analysis["primary_language"] = lang.lower() if lang else None
            
            # Get languages
            languages = self.get_repo_languages(owner, repo)
            analysis["languages"] = languages
            
            # Map to our supported languages
            lang_map = {
                "javascript": "nodejs", "typescript": "nodejs",
                "python": "python",
                "go": "golang",
                "java": "java", "kotlin": "java",
                "c#": "dotnet", "f#": "dotnet",
                "rust": "rust"
            }
            
            if analysis["primary_language"]:
                analysis["tech_stack"].append(
                    lang_map.get(analysis["primary_language"], analysis["primary_language"])
                )
            
            # Get root contents
            contents = self.get_repo_contents(owner, repo, "", analysis["default_branch"])
            file_names = [item['name'] for item in contents if item['type'] == 'file']
            dir_names = [item['name'] for item in contents if item['type'] == 'dir']
            
            # Detect files
            analysis["has_dockerfile"] = "Dockerfile" in file_names
            analysis["has_docker_compose"] = any(f.startswith("docker-compose") for f in file_names)
            analysis["has_kubernetes"] = "k8s" in dir_names or "kubernetes" in dir_names
            analysis["has_terraform"] = "terraform" in dir_names or any(f.endswith('.tf') for f in file_names)
            analysis["has_github_actions"] = ".github" in dir_names
            
            # Detect package manager and framework
            if "package.json" in file_names:
                analysis["tech_stack"].append("nodejs")
                pkg_content = self.get_file_content(owner, repo, "package.json", analysis["default_branch"])
                if pkg_content:
                    self._analyze_package_json(pkg_content, analysis)
            
            if "requirements.txt" in file_names:
                analysis["tech_stack"].append("python")
                analysis["package_manager"] = "pip"
                req_content = self.get_file_content(owner, repo, "requirements.txt", analysis["default_branch"])
                if req_content:
                    self._analyze_requirements_txt(req_content, analysis)
            
            if "go.mod" in file_names:
                analysis["tech_stack"].append("golang")
                analysis["package_manager"] = "go mod"
            
            if "pom.xml" in file_names:
                analysis["tech_stack"].append("java")
                analysis["package_manager"] = "maven"
            
            if "build.gradle" in file_names or "build.gradle.kts" in file_names:
                analysis["tech_stack"].append("java")
                analysis["package_manager"] = "gradle"
            
            if any(f.endswith('.csproj') for f in file_names):
                analysis["tech_stack"].append("dotnet")
                analysis["package_manager"] = "dotnet"
            
            if "Cargo.toml" in file_names:
                analysis["tech_stack"].append("rust")
                analysis["package_manager"] = "cargo"
            
            # Get existing workflows
            if analysis["has_github_actions"]:
                try:
                    workflows_dir = self.get_repo_contents(
                        owner, repo, ".github/workflows", analysis["default_branch"]
                    )
                    analysis["existing_workflows"] = [
                        wf['name'] for wf in workflows_dir 
                        if wf['name'].endswith(('.yml', '.yaml'))
                    ]
                except:
                    pass
            
            # Remove duplicates
            analysis["tech_stack"] = list(set(analysis["tech_stack"]))
            analysis["confidence"] = 0.95 if analysis["framework"] else 0.85
            
        except Exception as e:
            logger.error(f"Error analyzing repository: {e}")
            analysis["error"] = str(e)
        
        return analysis
    
    def _analyze_package_json(self, content: str, analysis: Dict):
        """Analyze package.json for Node.js projects"""
        try:
            pkg = json.loads(content)
            deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
            analysis["dependencies"] = list(deps.keys())
            
            # Detect package manager
            if "yarn.lock" in analysis.get("file_names", []):
                analysis["package_manager"] = "yarn"
            elif "pnpm-lock.yaml" in analysis.get("file_names", []):
                analysis["package_manager"] = "pnpm"
            else:
                analysis["package_manager"] = "npm"
            
            # Detect framework
            framework_map = {
                "next": "nextjs",
                "react": "react",
                "vue": "vue",
                "@angular/core": "angular",
                "express": "express",
                "@nestjs/core": "nestjs",
                "fastify": "fastify"
            }
            
            for pkg_name, framework in framework_map.items():
                if pkg_name in deps:
                    analysis["framework"] = framework
                    break
                    
        except json.JSONDecodeError:
            pass
    
    def _analyze_requirements_txt(self, content: str, analysis: Dict):
        """Analyze requirements.txt for Python projects"""
        deps = []
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                pkg = line.split('==')[0].split('>=')[0].split('<=')[0].split('[')[0].strip()
                if pkg:
                    deps.append(pkg)
        
        analysis["dependencies"] = deps
        
        # Detect framework
        framework_map = {
            "django": "django",
            "flask": "flask",
            "fastapi": "fastapi"
        }
        
        for pkg, framework in framework_map.items():
            if pkg in [d.lower() for d in deps]:
                analysis["framework"] = framework
                break
    
    # =========================================================================
    # Workflow & PR Operations
    # =========================================================================
    
    def create_branch(self, owner: str, repo: str, branch_name: str, from_ref: str = "main") -> Dict:
        """Create a new branch"""
        # Get SHA of source branch
        ref = self._request(f"/repos/{owner}/{repo}/git/ref/heads/{from_ref}")
        sha = ref['object']['sha']
        
        # Create new branch
        return self._request(
            f"/repos/{owner}/{repo}/git/refs",
            method='POST',
            data={"ref": f"refs/heads/{branch_name}", "sha": sha}
        )
    
    def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str = "main",
        sha: Optional[str] = None
    ) -> Dict:
        """Create or update a file in repository"""
        data = {
            "message": message,
            "content": base64.b64encode(content.encode('utf-8')).decode('utf-8'),
            "branch": branch
        }
        
        if sha:
            data["sha"] = sha
        else:
            # Check if file exists
            try:
                existing = self._request(f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
                data["sha"] = existing.get('sha')
            except:
                pass
        
        return self._request(
            f"/repos/{owner}/{repo}/contents/{path}",
            method='PUT',
            data=data
        )
    
    def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main"
    ) -> Dict:
        """Create a pull request"""
        return self._request(
            f"/repos/{owner}/{repo}/pulls",
            method='POST',
            data={
                "title": title,
                "body": body,
                "head": head,
                "base": base
            }
        )
    
    def get_workflow_runs(
        self,
        owner: str,
        repo: str,
        per_page: int = 10
    ) -> List[Dict]:
        """Get recent workflow runs"""
        result = self._request(f"/repos/{owner}/{repo}/actions/runs?per_page={per_page}")
        return result.get('workflow_runs', [])
    
    def get_workflow_run_status(
        self,
        owner: str,
        repo: str,
        run_id: int
    ) -> Dict:
        """Get status of a specific workflow run"""
        run = self._request(f"/repos/{owner}/{repo}/actions/runs/{run_id}")
        jobs = self._request(f"/repos/{owner}/{repo}/actions/runs/{run_id}/jobs")
        
        return {
            "run_id": run_id,
            "status": run.get('status'),
            "conclusion": run.get('conclusion'),
            "html_url": run.get('html_url'),
            "created_at": run.get('created_at'),
            "jobs": [
                {
                    "name": j.get('name'),
                    "status": j.get('status'),
                    "conclusion": j.get('conclusion')
                }
                for j in jobs.get('jobs', [])
            ]
        }


# Singleton
_github_client = None

def get_github_client(token: str = None) -> GitHubClient:
    """Get or create GitHub client"""
    global _github_client
    if _github_client is None:
        if not token:
            import os
            token = os.environ.get("GITHUB_TOKEN", "")
        _github_client = GitHubClient(token)
    return _github_client
