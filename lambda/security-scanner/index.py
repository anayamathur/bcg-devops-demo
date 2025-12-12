"""
BCG DevOps GenAI - Security Scanner Lambda
Validates GitHub Actions workflows for security best practices
"""

import json
import logging
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Security rules for workflow validation
SECURITY_RULES = [
    {
        "id": "SEC001",
        "name": "Hardcoded Secrets",
        "description": "Check for hardcoded secrets or API keys",
        "severity": "HIGH",
        "patterns": [
            r"password\s*[:=]\s*['\"][^'\"]+['\"]",
            r"api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]",
            r"secret\s*[:=]\s*['\"][^'\"]+['\"]",
            r"token\s*[:=]\s*['\"][^'\"]+['\"]",
            r"aws_access_key_id\s*[:=]\s*['\"][A-Z0-9]{20}['\"]",
            r"aws_secret_access_key\s*[:=]\s*['\"][A-Za-z0-9/+=]{40}['\"]",
        ]
    },
    {
        "id": "SEC002", 
        "name": "Unpinned Actions",
        "description": "Actions should use specific versions, not @master or @main",
        "severity": "MEDIUM",
        "patterns": [
            r"uses:\s+[^@]+@(master|main)\s*$",
        ]
    },
    {
        "id": "SEC003",
        "name": "Script Injection",
        "description": "Potential script injection via untrusted input",
        "severity": "HIGH",
        "patterns": [
            r"\$\{\{\s*github\.event\.(issue|pull_request|comment)\.body\s*\}\}",
            r"\$\{\{\s*github\.event\.(issue|pull_request)\.title\s*\}\}",
        ]
    },
    {
        "id": "SEC004",
        "name": "Excessive Permissions",
        "description": "Workflow has write-all permissions",
        "severity": "MEDIUM",
        "patterns": [
            r"permissions:\s*write-all",
        ]
    },
    {
        "id": "SEC005",
        "name": "Pull Request Target Trigger",
        "description": "pull_request_target can be dangerous with checkout",
        "severity": "HIGH",
        "patterns": [
            r"on:\s*\n\s*pull_request_target:",
        ]
    },
    {
        "id": "SEC006",
        "name": "Remote Script Execution",
        "description": "Piping curl/wget to shell is dangerous - scripts can be modified",
        "severity": "HIGH",
        "patterns": [
            r"curl[^|]*\|\s*(ba)?sh",
            r"wget[^|]*\|\s*(ba)?sh",
            r"curl[^>]*>\s*[^;]*;\s*(ba)?sh",
            r"wget[^>]*>\s*[^;]*;\s*(ba)?sh",
        ]
    },
    {
        "id": "SEC007",
        "name": "HTTP URLs (Not HTTPS)",
        "description": "Use HTTPS instead of HTTP for secure connections",
        "severity": "MEDIUM",
        "patterns": [
            r"http://(?!localhost|127\.0\.0\.1)",
        ]
    }
]

# Best practices to check
BEST_PRACTICES = [
    {
        "id": "BP001",
        "name": "Uses GitHub Secrets",
        "description": "Credentials should use GitHub Secrets",
        "check": lambda content: "${{ secrets." in content,
        "recommendation": "Use ${{ secrets.SECRET_NAME }} for sensitive values"
    },
    {
        "id": "BP002",
        "name": "Has Timeout",
        "description": "Jobs should have timeout-minutes set",
        "check": lambda content: "timeout-minutes:" in content,
        "recommendation": "Add timeout-minutes to prevent hung jobs"
    },
    {
        "id": "BP003",
        "name": "Uses Caching",
        "description": "Workflow should use dependency caching",
        "check": lambda content: "actions/cache@" in content or "cache:" in content,
        "recommendation": "Use actions/cache to speed up builds"
    },
    {
        "id": "BP004",
        "name": "Has Environment Protection",
        "description": "Production deployments should use environments",
        "check": lambda content: "environment:" in content if "prod" in content.lower() else True,
        "recommendation": "Use GitHub Environments for production deployments"
    },
    {
        "id": "BP005",
        "name": "Pinned Action Versions",
        "description": "Actions should use specific versions (v4, not @main)",
        "check": lambda content: "@v" in content or "@sha" in content,
        "recommendation": "Pin actions to specific versions (e.g., actions/checkout@v4)"
    }
]

def scan_workflow(workflow_content: str) -> dict:
    """Scan workflow for security issues and best practices"""
    
    results = {
        "valid": True,
        "security_issues": [],
        "best_practices": [],
        "score": 100,
        "summary": ""
    }
    
    # Check security rules
    for rule in SECURITY_RULES:
        for pattern in rule["patterns"]:
            matches = re.findall(pattern, workflow_content, re.MULTILINE | re.IGNORECASE)
            if matches:
                results["security_issues"].append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "description": rule["description"],
                    "severity": rule["severity"],
                    "matches": len(matches)
                })
                
                # Deduct points based on severity
                if rule["severity"] == "HIGH":
                    results["score"] -= 25
                    results["valid"] = False
                elif rule["severity"] == "MEDIUM":
                    results["score"] -= 10
    
    # Check best practices
    for bp in BEST_PRACTICES:
        passed = bp["check"](workflow_content)
        results["best_practices"].append({
            "id": bp["id"],
            "name": bp["name"],
            "description": bp["description"],
            "passed": passed,
            "recommendation": bp["recommendation"] if not passed else None
        })
        
        if not passed:
            results["score"] -= 5
    
    # Ensure score doesn't go below 0
    results["score"] = max(0, results["score"])
    
    # Basic YAML structure validation (without external yaml library)
    # Check for required GitHub Actions structure
    has_name = 'name:' in workflow_content
    has_on = bool(re.search(r'^on:', workflow_content, re.MULTILINE))
    has_jobs = 'jobs:' in workflow_content
    
    if not (has_on and has_jobs):
        results["valid"] = False
        missing = []
        if not has_on:
            missing.append('on:')
        if not has_jobs:
            missing.append('jobs:')
        results["security_issues"].append({
            "id": "YAML001",
            "name": "Invalid Workflow Structure",
            "description": f"Missing required GitHub Actions fields: {', '.join(missing)}",
            "severity": "HIGH"
        })
        results["score"] -= 25
    
    # Generate summary
    high_issues = len([i for i in results["security_issues"] if i.get("severity") == "HIGH"])
    medium_issues = len([i for i in results["security_issues"] if i.get("severity") == "MEDIUM"])
    bp_passed = len([bp for bp in results["best_practices"] if bp["passed"]])
    bp_total = len(results["best_practices"])
    
    if results["score"] >= 90:
        results["summary"] = f"✅ Excellent! Score: {results['score']}/100. Workflow follows security best practices."
    elif results["score"] >= 70:
        results["summary"] = f"⚠️ Good with minor issues. Score: {results['score']}/100. {medium_issues} medium issues found."
    elif results["score"] >= 50:
        results["summary"] = f"⚠️ Needs improvement. Score: {results['score']}/100. {high_issues} high, {medium_issues} medium issues."
    else:
        results["summary"] = f"❌ Security review required. Score: {results['score']}/100. {high_issues} critical issues found."
    
    results["summary"] += f" Best practices: {bp_passed}/{bp_total} passed."
    
    return results

def handler(event, context):
    """Lambda handler"""
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Parse request
    if "actionGroup" in event:
        # Bedrock Agent invocation
        parameters = {}
        if event.get("requestBody"):
            content = event["requestBody"].get("content", {})
            if "application/json" in content:
                properties = content["application/json"].get("properties", [])
                for prop in properties:
                    parameters[prop["name"]] = prop["value"]
        
        if event.get("parameters"):
            for param in event["parameters"]:
                parameters[param["name"]] = param["value"]
                
        workflow_content = parameters.get("workflow_content", "")
    else:
        # Direct invocation or API Gateway
        if event.get("body"):
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        else:
            body = event
        workflow_content = body.get("workflow_content", body.get("workflow", ""))
    
    if not workflow_content:
        error = {"error": "workflow_content is required"}
        if "actionGroup" in event:
            return {
                "messageVersion": "1.0",
                "response": {
                    "actionGroup": event.get("actionGroup"),
                    "apiPath": event.get("apiPath"),
                    "httpMethod": event.get("httpMethod"),
                    "httpStatusCode": 400,
                    "responseBody": {
                        "application/json": {"body": json.dumps(error)}
                    }
                }
            }
        return {"statusCode": 400, "body": json.dumps(error)}
    
    # Scan the workflow
    results = scan_workflow(workflow_content)
    
    logger.info(f"Scan complete. Score: {results['score']}, Valid: {results['valid']}")
    
    # Return response
    if "actionGroup" in event:
        return {
            "messageVersion": "1.0",
            "response": {
                "actionGroup": event.get("actionGroup"),
                "apiPath": event.get("apiPath"),
                "httpMethod": event.get("httpMethod"),
                "httpStatusCode": 200,
                "responseBody": {
                    "application/json": {"body": json.dumps(results)}
                }
            }
        }
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(results)
    }
