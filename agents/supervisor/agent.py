"""
BCG Agentic DevOps - Supervisor Agent
======================================
Central orchestrator that routes requests to specialized agents.
Implements multi-step planning and agent coordination.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass, asdict

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utils.bedrock_client import get_bedrock_client

logger = logging.getLogger(__name__)


class AgentType(str, Enum):
    WORKFLOW = "workflow_generator"
    SECURITY = "security_remediation"
    INCIDENT = "incident_response"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    """Represents a task assigned to an agent"""
    task_id: str
    agent_type: AgentType
    action: str
    parameters: Dict[str, Any]
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = None
    completed_at: str = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class ExecutionPlan:
    """Multi-step execution plan"""
    plan_id: str
    user_request: str
    steps: List[AgentTask]
    current_step: int = 0
    status: TaskStatus = TaskStatus.PENDING
    requires_approval: bool = False
    approval_message: str = ""


class SupervisorAgent:
    """
    Supervisor Agent - Central Orchestrator
    
    Responsibilities:
    1. Understand user intent
    2. Create execution plans
    3. Route to specialized agents
    4. Manage approvals
    5. Track progress
    """
    
    SYSTEM_PROMPT = """You are the Supervisor Agent for BCG's Agentic DevOps platform.

Your role is to:
1. Understand user requests about DevOps operations
2. Create step-by-step execution plans
3. Route tasks to specialized agents:
   - workflow_generator: CI/CD pipeline creation, GitHub Actions workflows
   - security_remediation: Security scanning, vulnerability fixes, compliance
   - incident_response: Alert handling, RCA, runbook execution

BCG Tool Chain (always consider these):
- GitHub + GitHub Actions (CI)
- JFrog Artifactory (artifacts)
- SonarQube (code quality)
- Prisma Cloud (security)
- ArgoCD (GitOps CD)
- Octopus Deploy (deployment)
- Datadog (monitoring)
- EKS (Kubernetes)

When analyzing requests:
1. Identify the primary intent
2. Determine which agent(s) are needed
3. Create a logical sequence of steps
4. Identify if human approval is needed (for deployments, security changes)

Respond in JSON format:
{
    "intent": "brief description of user intent",
    "agents_needed": ["agent_type1", "agent_type2"],
    "requires_approval": true/false,
    "approval_reason": "why approval is needed (if applicable)",
    "execution_plan": [
        {
            "step": 1,
            "agent": "agent_type",
            "action": "action_name",
            "parameters": {},
            "description": "what this step does"
        }
    ]
}"""

    def __init__(self, bedrock_profile: str = "credit", region: str = "us-east-1"):
        self.bedrock = get_bedrock_client(profile=bedrock_profile, region=region)
        self.active_plans: Dict[str, ExecutionPlan] = {}
        self.agents: Dict[AgentType, Any] = {}
        logger.info("Supervisor Agent initialized")
    
    def register_agent(self, agent_type: AgentType, agent_instance):
        """Register a specialized agent"""
        self.agents[agent_type] = agent_instance
        logger.info(f"Registered agent: {agent_type.value}")
    
    def analyze_request(self, user_request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze user request and create execution plan.
        
        Args:
            user_request: Natural language request from user
            context: Optional context (repository, previous actions, etc.)
            
        Returns:
            Execution plan with steps
        """
        prompt = f"""Analyze this DevOps request and create an execution plan.

User Request: {user_request}

Context: {json.dumps(context or {}, indent=2)}

Create a detailed execution plan following the JSON format specified."""

        try:
            response = self.bedrock.invoke(prompt, self.SYSTEM_PROMPT)
            
            # Parse JSON from response
            plan_data = self._extract_json(response)
            
            return {
                "success": True,
                "request": user_request,
                "analysis": plan_data,
                "raw_response": response
            }
            
        except Exception as e:
            logger.error(f"Error analyzing request: {e}")
            return {
                "success": False,
                "error": str(e),
                "request": user_request
            }
    
    def create_execution_plan(self, user_request: str, context: Dict = None) -> ExecutionPlan:
        """
        Create a full execution plan from user request.
        """
        import uuid
        
        analysis = self.analyze_request(user_request, context)
        
        if not analysis.get("success"):
            raise Exception(f"Failed to analyze request: {analysis.get('error')}")
        
        plan_data = analysis.get("analysis", {})
        plan_id = str(uuid.uuid4())[:8]
        
        # Create tasks from plan
        tasks = []
        for step in plan_data.get("execution_plan", []):
            task = AgentTask(
                task_id=f"{plan_id}-{step.get('step', len(tasks)+1)}",
                agent_type=AgentType(step.get("agent", "workflow_generator")),
                action=step.get("action", ""),
                parameters=step.get("parameters", {})
            )
            tasks.append(task)
        
        plan = ExecutionPlan(
            plan_id=plan_id,
            user_request=user_request,
            steps=tasks,
            requires_approval=plan_data.get("requires_approval", False),
            approval_message=plan_data.get("approval_reason", "")
        )
        
        self.active_plans[plan_id] = plan
        return plan
    
    def execute_plan(self, plan_id: str, approved: bool = True) -> Dict[str, Any]:
        """
        Execute an approved plan.
        
        Args:
            plan_id: ID of the plan to execute
            approved: Whether the plan was approved (for plans requiring approval)
            
        Returns:
            Execution results
        """
        plan = self.active_plans.get(plan_id)
        if not plan:
            return {"success": False, "error": f"Plan {plan_id} not found"}
        
        if plan.requires_approval and not approved:
            return {
                "success": False,
                "status": "rejected",
                "message": "Plan requires approval but was not approved"
            }
        
        plan.status = TaskStatus.IN_PROGRESS
        results = []
        
        for task in plan.steps:
            try:
                task.status = TaskStatus.IN_PROGRESS
                
                # Get the appropriate agent
                agent = self.agents.get(task.agent_type)
                if not agent:
                    raise Exception(f"Agent {task.agent_type} not registered")
                
                # Execute the task
                result = agent.execute(task.action, task.parameters)
                
                task.result = result
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now().isoformat()
                
                results.append({
                    "task_id": task.task_id,
                    "agent": task.agent_type.value,
                    "action": task.action,
                    "status": "completed",
                    "result": result
                })
                
            except Exception as e:
                logger.error(f"Task {task.task_id} failed: {e}")
                task.status = TaskStatus.FAILED
                task.error = str(e)
                
                results.append({
                    "task_id": task.task_id,
                    "agent": task.agent_type.value,
                    "action": task.action,
                    "status": "failed",
                    "error": str(e)
                })
                
                # For critical failures, stop execution
                break
        
        # Update plan status
        all_completed = all(t.status == TaskStatus.COMPLETED for t in plan.steps)
        plan.status = TaskStatus.COMPLETED if all_completed else TaskStatus.FAILED
        
        return {
            "success": all_completed,
            "plan_id": plan_id,
            "status": plan.status.value,
            "results": results
        }
    
    def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """Get current status of a plan"""
        plan = self.active_plans.get(plan_id)
        if not plan:
            return {"error": f"Plan {plan_id} not found"}
        
        return {
            "plan_id": plan.plan_id,
            "request": plan.user_request,
            "status": plan.status.value,
            "current_step": plan.current_step,
            "total_steps": len(plan.steps),
            "requires_approval": plan.requires_approval,
            "steps": [
                {
                    "task_id": t.task_id,
                    "agent": t.agent_type.value,
                    "action": t.action,
                    "status": t.status.value
                }
                for t in plan.steps
            ]
        }
    
    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from text response"""
        import re
        
        # Try to find JSON in code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            return json.loads(json_match.group(1))
        
        # Try to parse entire response as JSON
        try:
            return json.loads(text)
        except:
            pass
        
        # Try to find JSON object in text
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            return json.loads(json_match.group())
        
        return {"raw_text": text}


# Direct execution capability
def handle_request(request: str, context: Dict = None) -> Dict[str, Any]:
    """
    Handle a user request - main entry point.
    
    Args:
        request: User's natural language request
        context: Optional context (repository, etc.)
        
    Returns:
        Response with plan or execution results
    """
    supervisor = SupervisorAgent()
    
    # Analyze and create plan
    plan = supervisor.create_execution_plan(request, context)
    
    return {
        "plan_id": plan.plan_id,
        "status": plan.status.value,
        "requires_approval": plan.requires_approval,
        "approval_message": plan.approval_message,
        "steps": [
            {
                "step": i + 1,
                "agent": t.agent_type.value,
                "action": t.action,
                "description": t.parameters.get("description", "")
            }
            for i, t in enumerate(plan.steps)
        ]
    }


if __name__ == "__main__":
    # Test the supervisor
    logging.basicConfig(level=logging.INFO)
    
    test_request = "Setup CI/CD pipeline for a Node.js application with security scanning"
    result = handle_request(test_request)
    print(json.dumps(result, indent=2))
