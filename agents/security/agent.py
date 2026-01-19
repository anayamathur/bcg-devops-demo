"""
BCG Agentic DevOps - Security Remediation Agent
=================================================
Aggregates security findings and creates automated fix PRs.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utils.bedrock_client import get_bedrock_client
from shared.integrations.github_client import get_github_client

logger = logging.getLogger(__name__)


# Known vulnerable packages and fixes
VULNERABILITY_DATABASE = {
    "npm": {
        "lodash": {"fixed_version": "4.17.21", "cve": "CVE-2021-23337"},
        "axios": {"fixed_version": "1.6.0", "cve": "CVE-2023-45857"},
        "express": {"fixed_version": "4.18.2", "cve": "CVE-2022-24999"},
        "jsonwebtoken": {"fixed_version": "9.0.0", "cve": "CVE-2022-23529"},
        "minimist": {"fixed_version": "1.2.8", "cve": "CVE-2021-44906"},
        "node-fetch": {"fixed_version": "3.3.2", "cve": "CVE-2022-0235"},
    },
    "pip": {
        "django": {"fixed_version": "4.2.8", "cve": "CVE-2023-46695"},
        "flask": {"fixed_version": "3.0.0", "cve": "CVE-2023-30861"},
        "requests": {"fixed_version": "2.31.0", "cve": "CVE-2023-32681"},
        "cryptography": {"fixed_version": "41.0.6", "cve": "CVE-2023-49083"},
        "pillow": {"fixed_version": "10.1.0", "cve": "CVE-2023-44271"},
    }
}


class SecurityAgent:
    """
    Security Remediation Agent
    
    Capabilities:
    1. Aggregate findings from SonarQube, Prisma, Snyk
    2. Analyze vulnerabilities with AI
    3. Generate fix suggestions
    4. Create automated fix PRs
    5. Generate compliance reports
    """
    
    SYSTEM_PROMPT = """You are the Security Remediation Agent for BCG's DevOps platform.

Your role is to:
1. Analyze security vulnerabilities in code and dependencies
2. Suggest specific fixes with code changes
3. Prioritize vulnerabilities by severity
4. Generate compliance-ready reports

When analyzing vulnerabilities:
- Reference CVE IDs when available
- Provide specific remediation steps
- Consider BCG's security policies
- Flag critical issues that need immediate attention

Output format for fixes:
{
    "vulnerability": "description",
    "severity": "CRITICAL|HIGH|MEDIUM|LOW",
    "cve": "CVE-XXXX-XXXXX",
    "affected_file": "path/to/file",
    "fix_type": "upgrade|patch|config",
    "fix_description": "what to do",
    "fix_code": "actual code change if applicable"
}"""

    def __init__(
        self,
        github_token: str,
        bedrock_profile: str = "credit",
        region: str = "us-east-1"
    ):
        self.github = get_github_client(github_token)
        self.bedrock = get_bedrock_client(profile=bedrock_profile, region=region)
        logger.info("Security Agent initialized")
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action"""
        actions = {
            "scan_repository": self.scan_repository,
            "analyze_dependencies": self.analyze_dependencies,
            "suggest_fixes": self.suggest_fixes,
            "create_fix_pr": self.create_fix_pr,
            "generate_report": self.generate_report
        }
        
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        
        return handler(**parameters)
    
    def scan_repository(self, repository: str) -> Dict[str, Any]:
        """
        Scan repository for security issues.
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            findings = {
                "repository": repository,
                "scanned_at": datetime.now().isoformat(),
                "dependency_vulnerabilities": [],
                "code_vulnerabilities": [],
                "secret_leaks": [],
                "misconfigurations": [],
                "summary": {}
            }
            
            # Analyze dependencies
            analysis = self.github.analyze_repository(owner, repo)
            deps = analysis.get("dependencies", [])
            
            # Check against known vulnerabilities
            package_manager = analysis.get("package_manager", "npm")
            vuln_db = VULNERABILITY_DATABASE.get(package_manager, {})
            
            for dep in deps:
                dep_lower = dep.lower()
                if dep_lower in vuln_db:
                    vuln = vuln_db[dep_lower]
                    findings["dependency_vulnerabilities"].append({
                        "package": dep,
                        "cve": vuln["cve"],
                        "severity": "HIGH",
                        "fixed_version": vuln["fixed_version"],
                        "recommendation": f"Upgrade {dep} to {vuln['fixed_version']}"
                    })
            
            # Scan key files for common issues
            files_to_check = ["package.json", "Dockerfile", ".env", ".env.example"]
            
            for file_path in files_to_check:
                try:
                    content = self.github.get_file_content(
                        owner, repo, file_path, analysis.get("default_branch", "main")
                    )
                    if content:
                        self._check_file_security(file_path, content, findings)
                except:
                    pass
            
            # Summary
            findings["summary"] = {
                "total_issues": (
                    len(findings["dependency_vulnerabilities"]) +
                    len(findings["code_vulnerabilities"]) +
                    len(findings["secret_leaks"]) +
                    len(findings["misconfigurations"])
                ),
                "critical": sum(1 for v in findings["dependency_vulnerabilities"] if v.get("severity") == "CRITICAL"),
                "high": sum(1 for v in findings["dependency_vulnerabilities"] if v.get("severity") == "HIGH"),
                "medium": sum(1 for v in findings["dependency_vulnerabilities"] if v.get("severity") == "MEDIUM"),
                "low": sum(1 for v in findings["dependency_vulnerabilities"] if v.get("severity") == "LOW")
            }
            
            return {
                "success": True,
                "action": "scan_repository",
                "findings": findings
            }
            
        except Exception as e:
            logger.error(f"Error scanning repository: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_file_security(self, file_path: str, content: str, findings: Dict):
        """Check file for security issues"""
        import re
        
        # Check for secrets in code
        secret_patterns = [
            (r'(?i)(password|passwd|pwd)\s*[=:]\s*["\'][^"\']+["\']', "Hardcoded password"),
            (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\'][^"\']+["\']', "Hardcoded API key"),
            (r'(?i)(secret|token)\s*[=:]\s*["\'][a-zA-Z0-9]{20,}["\']', "Hardcoded secret/token"),
            (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
            (r'(?i)private[_-]?key', "Private key reference"),
        ]
        
        for pattern, description in secret_patterns:
            if re.search(pattern, content):
                findings["secret_leaks"].append({
                    "file": file_path,
                    "issue": description,
                    "severity": "CRITICAL",
                    "recommendation": "Remove hardcoded secret and use environment variables or secrets manager"
                })
        
        # Dockerfile checks
        if file_path == "Dockerfile":
            if re.search(r'FROM\s+\S+:latest', content):
                findings["misconfigurations"].append({
                    "file": file_path,
                    "issue": "Using 'latest' tag in FROM instruction",
                    "severity": "MEDIUM",
                    "recommendation": "Pin to specific image version for reproducibility"
                })
            
            if "USER" not in content:
                findings["misconfigurations"].append({
                    "file": file_path,
                    "issue": "No USER instruction - container runs as root",
                    "severity": "HIGH",
                    "recommendation": "Add non-root USER instruction"
                })
    
    def analyze_dependencies(self, repository: str) -> Dict[str, Any]:
        """Analyze dependencies for vulnerabilities"""
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            analysis = self.github.analyze_repository(owner, repo)
            deps = analysis.get("dependencies", [])
            
            # Use AI to analyze
            prompt = f"""Analyze these dependencies for known vulnerabilities:

Dependencies: {json.dumps(deps[:50], indent=2)}

For each vulnerable package, provide:
1. CVE number if known
2. Severity (CRITICAL/HIGH/MEDIUM/LOW)
3. Fixed version
4. Brief description

Output as JSON array."""

            response = self.bedrock.invoke(prompt, self.SYSTEM_PROMPT)
            
            return {
                "success": True,
                "action": "analyze_dependencies",
                "repository": repository,
                "dependencies_count": len(deps),
                "analysis": response
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def suggest_fixes(
        self,
        repository: str,
        vulnerability: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Suggest fixes for vulnerabilities.
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            # If no specific vulnerability, scan first
            if not vulnerability:
                scan_result = self.scan_repository(repository)
                if not scan_result.get("success"):
                    return scan_result
                
                findings = scan_result.get("findings", {})
                vulnerabilities = findings.get("dependency_vulnerabilities", [])
            else:
                vulnerabilities = [vulnerability]
            
            fixes = []
            
            for vuln in vulnerabilities:
                fix = {
                    "vulnerability": vuln,
                    "fix_type": "upgrade",
                    "changes": []
                }
                
                # For dependency upgrades
                if vuln.get("package") and vuln.get("fixed_version"):
                    fix["changes"].append({
                        "file": "package.json",  # or requirements.txt
                        "action": "upgrade_dependency",
                        "package": vuln["package"],
                        "to_version": vuln["fixed_version"]
                    })
                
                fixes.append(fix)
            
            return {
                "success": True,
                "action": "suggest_fixes",
                "repository": repository,
                "fixes": fixes,
                "total_fixes": len(fixes),
                "auto_fixable": len([f for f in fixes if f["fix_type"] == "upgrade"])
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def create_fix_pr(
        self,
        repository: str,
        fixes: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a PR with security fixes.
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            # Get fixes if not provided
            if not fixes:
                fix_result = self.suggest_fixes(repository)
                if not fix_result.get("success"):
                    return fix_result
                fixes = fix_result.get("fixes", [])
            
            if not fixes:
                return {"success": True, "message": "No fixes needed"}
            
            # Get analysis for package manager info
            analysis = self.github.analyze_repository(owner, repo)
            default_branch = analysis.get("default_branch", "main")
            package_manager = analysis.get("package_manager", "npm")
            
            # Create branch
            branch_name = f"security/auto-fix-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            self.github.create_branch(owner, repo, branch_name, default_branch)
            
            # Prepare fix content
            if package_manager == "npm":
                pkg_content = self.github.get_file_content(owner, repo, "package.json", default_branch)
                if pkg_content:
                    pkg = json.loads(pkg_content)
                    
                    for fix in fixes:
                        for change in fix.get("changes", []):
                            if change.get("action") == "upgrade_dependency":
                                package = change["package"]
                                version = change["to_version"]
                                
                                if package in pkg.get("dependencies", {}):
                                    pkg["dependencies"][package] = f"^{version}"
                                elif package in pkg.get("devDependencies", {}):
                                    pkg["devDependencies"][package] = f"^{version}"
                    
                    # Push updated package.json
                    self.github.create_or_update_file(
                        owner, repo,
                        "package.json",
                        json.dumps(pkg, indent=2),
                        f"fix(security): upgrade vulnerable dependencies\n\n{self._format_fix_message(fixes)}",
                        branch_name
                    )
            
            # Create PR
            pr = self.github.create_pull_request(
                owner, repo,
                title="fix(security): Automated vulnerability remediation",
                body=f"""## 🔒 Security Fix - Automated by BCG DevOps Agent

This PR contains automated fixes for security vulnerabilities.

### Fixes Applied

{self._format_fix_message(fixes)}

### Review Required

Please review the changes before merging:
1. Run tests to ensure compatibility
2. Check for breaking changes
3. Update lock file after merge

---
*Generated by BCG Agentic DevOps Platform*""",
                head=branch_name,
                base=default_branch
            )
            
            return {
                "success": True,
                "action": "create_fix_pr",
                "repository": repository,
                "pr_number": pr.get("number"),
                "pr_url": pr.get("html_url"),
                "fixes_applied": len(fixes)
            }
            
        except Exception as e:
            logger.error(f"Error creating fix PR: {e}")
            return {"success": False, "error": str(e)}
    
    def _format_fix_message(self, fixes: List[Dict]) -> str:
        """Format fixes for PR/commit message"""
        lines = []
        for fix in fixes:
            vuln = fix.get("vulnerability", {})
            for change in fix.get("changes", []):
                if change.get("action") == "upgrade_dependency":
                    lines.append(
                        f"- Upgrade `{change['package']}` to `{change['to_version']}` "
                        f"({vuln.get('cve', 'security fix')})"
                    )
        return "\n".join(lines) if lines else "Security improvements"
    
    def generate_report(
        self,
        repository: str,
        format: str = "markdown"
    ) -> Dict[str, Any]:
        """
        Generate a security compliance report.
        """
        parts = repository.split('/')
        if len(parts) != 2:
            return {"error": "Invalid repository format"}
        
        owner, repo = parts
        
        try:
            # Scan repository
            scan_result = self.scan_repository(repository)
            if not scan_result.get("success"):
                return scan_result
            
            findings = scan_result.get("findings", {})
            summary = findings.get("summary", {})
            
            # Generate report
            report = f"""# Security Scan Report

## Repository: {repository}
**Scan Date:** {findings.get('scanned_at', datetime.now().isoformat())}

---

## Executive Summary

| Severity | Count |
|----------|-------|
| 🔴 Critical | {summary.get('critical', 0)} |
| 🟠 High | {summary.get('high', 0)} |
| 🟡 Medium | {summary.get('medium', 0)} |
| 🟢 Low | {summary.get('low', 0)} |
| **Total** | **{summary.get('total_issues', 0)}** |

---

## Dependency Vulnerabilities

"""
            for vuln in findings.get("dependency_vulnerabilities", []):
                report += f"""### {vuln.get('package')}
- **CVE:** {vuln.get('cve', 'N/A')}
- **Severity:** {vuln.get('severity')}
- **Recommendation:** {vuln.get('recommendation')}

"""

            if findings.get("secret_leaks"):
                report += "## Secret Leaks Detected\n\n"
                for leak in findings["secret_leaks"]:
                    report += f"- **{leak['file']}**: {leak['issue']} ({leak['severity']})\n"

            if findings.get("misconfigurations"):
                report += "\n## Misconfigurations\n\n"
                for issue in findings["misconfigurations"]:
                    report += f"- **{issue['file']}**: {issue['issue']} ({issue['severity']})\n"

            report += """
---

## Recommendations

1. Address all CRITICAL and HIGH severity issues immediately
2. Update dependencies to patched versions
3. Remove any hardcoded secrets
4. Enable automated security scanning in CI/CD

---
*Generated by BCG Agentic DevOps Platform*
"""

            return {
                "success": True,
                "action": "generate_report",
                "repository": repository,
                "report": report,
                "format": format,
                "summary": summary
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    token = os.environ.get("GITHUB_TOKEN", "")
    agent = SecurityAgent(token)
    
    # Test scan
    result = agent.scan_repository("octocat/Hello-World")
    print(json.dumps(result, indent=2))
