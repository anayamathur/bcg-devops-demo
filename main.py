"""
BCG Agentic DevOps Platform - Main Entry Point
================================================
Provides CLI and API interface for the agentic platform.
"""

import json
import logging
import argparse
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("bcg-devops")

# Import agents
from agents.supervisor.agent import SupervisorAgent, AgentType
from agents.workflow.agent import WorkflowGeneratorAgent
from agents.security.agent import SecurityAgent
from agents.incident.agent import IncidentAgent


class BCGDevOpsPlatform:
    """
    BCG Agentic DevOps Platform
    
    Central interface for all DevOps automation using AI agents.
    
    Agents:
    - Supervisor: Orchestrates and routes requests
    - Workflow Generator: Creates CI/CD workflows
    - Security: Scans and remediates vulnerabilities
    - Incident: Handles alert triage and RCA
    """
    
    def __init__(
        self,
        github_token: str,
        aws_profile: str = "credit",
        aws_region: str = "us-east-1",
        slack_webhook: str = None
    ):
        self.github_token = github_token
        self.aws_profile = aws_profile
        self.aws_region = aws_region
        
        # Initialize agents
        logger.info("Initializing BCG DevOps Platform...")
        
        self.supervisor = SupervisorAgent(
            bedrock_profile=aws_profile,
            region=aws_region
        )
        
        self.workflow_agent = WorkflowGeneratorAgent(
            github_token=github_token,
            bedrock_profile=aws_profile,
            region=aws_region
        )
        
        self.security_agent = SecurityAgent(
            github_token=github_token,
            bedrock_profile=aws_profile,
            region=aws_region
        )
        
        self.incident_agent = IncidentAgent(
            bedrock_profile=aws_profile,
            region=aws_region,
            slack_webhook=slack_webhook
        )
        
        # Register agents with supervisor
        self.supervisor.register_agent(AgentType.WORKFLOW, self.workflow_agent)
        self.supervisor.register_agent(AgentType.SECURITY, self.security_agent)
        self.supervisor.register_agent(AgentType.INCIDENT, self.incident_agent)
        
        logger.info("BCG DevOps Platform initialized successfully")
    
    def process_request(self, request: str, context: Dict = None) -> Dict[str, Any]:
        """
        Process a natural language request.
        
        Args:
            request: User's natural language request
            context: Optional context (repository, etc.)
            
        Returns:
            Response with plan and/or execution results
        """
        logger.info(f"Processing request: {request[:100]}...")
        
        try:
            # Analyze and create plan
            plan = self.supervisor.create_execution_plan(request, context)
            
            # If requires approval, return plan for review
            if plan.requires_approval:
                return {
                    "success": True,
                    "status": "awaiting_approval",
                    "plan_id": plan.plan_id,
                    "message": plan.approval_message,
                    "plan_summary": self.supervisor.get_plan_status(plan.plan_id)
                }
            
            # Auto-execute if no approval needed
            result = self.supervisor.execute_plan(plan.plan_id)
            return result
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {"success": False, "error": str(e)}
    
    def approve_and_execute(self, plan_id: str) -> Dict[str, Any]:
        """
        Approve and execute a pending plan.
        """
        return self.supervisor.execute_plan(plan_id, approved=True)
    
    # ==========================================================================
    # Direct Agent Access
    # ==========================================================================
    
    def analyze_repository(self, repository: str) -> Dict[str, Any]:
        """Analyze a GitHub repository"""
        return self.workflow_agent.analyze_repository(repository)
    
    def generate_workflow(self, repository: str, **kwargs) -> Dict[str, Any]:
        """Generate CI/CD workflow for a repository"""
        return self.workflow_agent.generate_workflow(repository, **kwargs)
    
    def create_workflow_pr(self, repository: str) -> Dict[str, Any]:
        """Create a PR with generated workflow"""
        return self.workflow_agent.create_pr_with_workflow(repository)
    
    def scan_security(self, repository: str) -> Dict[str, Any]:
        """Scan repository for security issues"""
        return self.security_agent.scan_repository(repository)
    
    def create_security_fix_pr(self, repository: str) -> Dict[str, Any]:
        """Create PR with security fixes"""
        return self.security_agent.create_fix_pr(repository)
    
    def triage_alert(
        self,
        title: str,
        details: str,
        source: str = "datadog",
        service: str = None
    ) -> Dict[str, Any]:
        """Triage an incoming alert"""
        return self.incident_agent.triage_alert(title, details, source, service)
    
    def generate_rca(self, incident_id: str, resolution: str = None) -> Dict[str, Any]:
        """Generate RCA report"""
        return self.incident_agent.generate_rca(incident_id, resolution)


def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(
        description="BCG Agentic DevOps Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a repository
  python main.py analyze --repo owner/repo
  
  # Generate CI/CD workflow
  python main.py workflow --repo owner/repo
  
  # Create workflow PR
  python main.py workflow-pr --repo owner/repo
  
  # Scan for security issues
  python main.py security-scan --repo owner/repo
  
  # Triage an alert
  python main.py triage --title "High CPU" --details "CPU at 95%"
  
  # Natural language request
  python main.py ask "Setup CI/CD for my Node.js repo"
        """
    )
    
    parser.add_argument("command", choices=[
        "analyze", "workflow", "workflow-pr",
        "security-scan", "security-fix",
        "triage", "rca",
        "ask"
    ], help="Command to execute")
    
    parser.add_argument("--repo", "-r", help="Repository (owner/repo)")
    parser.add_argument("--title", "-t", help="Alert title (for triage)")
    parser.add_argument("--details", "-d", help="Alert details (for triage)")
    parser.add_argument("--incident-id", "-i", help="Incident ID (for RCA)")
    parser.add_argument("--request", help="Natural language request (for ask)")
    parser.add_argument("--profile", default="credit", help="AWS profile")
    parser.add_argument("--region", default="us-east-1", help="AWS region")
    
    args = parser.parse_args()
    
    # Get GitHub token from environment
    github_token = os.environ.get("GITHUB_TOKEN", "")
    if not github_token:
        print("Warning: GITHUB_TOKEN environment variable not set")
    
    # Initialize platform
    platform = BCGDevOpsPlatform(
        github_token=github_token,
        aws_profile=args.profile,
        aws_region=args.region
    )
    
    result = {}
    
    if args.command == "analyze":
        if not args.repo:
            print("Error: --repo required")
            return
        result = platform.analyze_repository(args.repo)
    
    elif args.command == "workflow":
        if not args.repo:
            print("Error: --repo required")
            return
        result = platform.generate_workflow(args.repo)
    
    elif args.command == "workflow-pr":
        if not args.repo:
            print("Error: --repo required")
            return
        result = platform.create_workflow_pr(args.repo)
    
    elif args.command == "security-scan":
        if not args.repo:
            print("Error: --repo required")
            return
        result = platform.scan_security(args.repo)
    
    elif args.command == "security-fix":
        if not args.repo:
            print("Error: --repo required")
            return
        result = platform.create_security_fix_pr(args.repo)
    
    elif args.command == "triage":
        if not args.title or not args.details:
            print("Error: --title and --details required")
            return
        result = platform.triage_alert(args.title, args.details)
    
    elif args.command == "rca":
        if not args.incident_id:
            print("Error: --incident-id required")
            return
        result = platform.generate_rca(args.incident_id)
    
    elif args.command == "ask":
        request = args.request or " ".join(args._get_args())
        if not request:
            print("Error: request text required")
            return
        result = platform.process_request(request, {"repository": args.repo})
    
    # Output result
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
