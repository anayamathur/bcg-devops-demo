#!/usr/bin/env python3
"""
BCG Agentic DevOps - Test Script
=================================
Test all agents and their capabilities.
"""

import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configuration
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "credit")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_bedrock():
    """Test Bedrock Nova Pro connection"""
    print_section("Testing AWS Bedrock Nova Pro")
    
    from shared.utils.bedrock_client import get_bedrock_client
    
    try:
        client = get_bedrock_client(profile=AWS_PROFILE, region=AWS_REGION)
        response = client.invoke(
            "List 3 key DevOps practices in one line each",
            "You are a DevOps expert. Be concise."
        )
        print("✅ Bedrock Nova Pro is working!")
        print(f"Response: {response[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Bedrock error: {e}")
        return False

def test_github():
    """Test GitHub API connection"""
    print_section("Testing GitHub API")
    
    from shared.integrations.github_client import GitHubClient
    
    try:
        client = GitHubClient(GITHUB_TOKEN)
        # Test with a public repo
        result = client.analyze_repository("expressjs", "express")
        print(f"✅ GitHub API is working!")
        print(f"Repository: expressjs/express")
        print(f"Tech Stack: {result.get('tech_stack')}")
        print(f"Has CI/CD: {result.get('has_github_actions')}")
        return True
    except Exception as e:
        print(f"❌ GitHub API error: {e}")
        return False

def test_workflow_agent():
    """Test Workflow Generator Agent"""
    print_section("Testing Workflow Generator Agent")
    
    from agents.workflow.agent import WorkflowGeneratorAgent
    
    try:
        agent = WorkflowGeneratorAgent(
            github_token=GITHUB_TOKEN,
            bedrock_profile=AWS_PROFILE,
            region=AWS_REGION
        )
        
        # Test analysis
        result = agent.analyze_repository("vercel/next.js")
        print(f"✅ Workflow Agent is working!")
        print(f"Repository: vercel/next.js")
        print(f"Detected: {result.get('analysis', {}).get('tech_stack')}")
        return True
    except Exception as e:
        print(f"❌ Workflow Agent error: {e}")
        return False

def test_security_agent():
    """Test Security Agent"""
    print_section("Testing Security Agent")
    
    from agents.security.agent import SecurityAgent
    
    try:
        agent = SecurityAgent(
            github_token=GITHUB_TOKEN,
            bedrock_profile=AWS_PROFILE,
            region=AWS_REGION
        )
        
        # Test scan
        result = agent.scan_repository("expressjs/express")
        findings = result.get("findings", {})
        print(f"✅ Security Agent is working!")
        print(f"Total issues found: {findings.get('summary', {}).get('total_issues', 0)}")
        return True
    except Exception as e:
        print(f"❌ Security Agent error: {e}")
        return False

def test_incident_agent():
    """Test Incident Agent"""
    print_section("Testing Incident Agent")
    
    from agents.incident.agent import IncidentAgent
    
    try:
        agent = IncidentAgent(
            bedrock_profile=AWS_PROFILE,
            region=AWS_REGION
        )
        
        # Test triage
        result = agent.triage_alert(
            alert_title="High CPU Usage Alert",
            alert_details="CPU usage at 95% on api-server for last 10 minutes",
            service="api-gateway"
        )
        print(f"✅ Incident Agent is working!")
        print(f"Incident ID: {result.get('incident_id')}")
        print(f"Severity: {result.get('severity')}")
        print(f"Category: {result.get('category')}")
        return True
    except Exception as e:
        print(f"❌ Incident Agent error: {e}")
        return False

def test_supervisor():
    """Test Supervisor Agent"""
    print_section("Testing Supervisor Agent")
    
    from agents.supervisor.agent import SupervisorAgent
    
    try:
        supervisor = SupervisorAgent(
            bedrock_profile=AWS_PROFILE,
            region=AWS_REGION
        )
        
        # Test request analysis
        result = supervisor.analyze_request(
            "Setup CI/CD for a Node.js application with security scanning"
        )
        print(f"✅ Supervisor Agent is working!")
        print(f"Analysis successful: {result.get('success')}")
        return True
    except Exception as e:
        print(f"❌ Supervisor Agent error: {e}")
        return False

def main():
    print("\n")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║       BCG AGENTIC DEVOPS PLATFORM - TEST SUITE             ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print(f"║  AWS Profile: {AWS_PROFILE:<44} ║")
    print(f"║  AWS Region:  {AWS_REGION:<44} ║")
    print(f"║  GitHub Token: {'***' + GITHUB_TOKEN[-4:] if GITHUB_TOKEN else 'NOT SET':<43} ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    results = {
        "Bedrock": test_bedrock(),
        "GitHub API": test_github(),
        "Workflow Agent": test_workflow_agent(),
        "Security Agent": test_security_agent(),
        "Incident Agent": test_incident_agent(),
        "Supervisor Agent": test_supervisor()
    }
    
    # Summary
    print_section("TEST SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {name}: {status}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 All tests passed! Platform is ready.")
    else:
        print("\n  ⚠️  Some tests failed. Check configuration.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
