"""
BCG Agentic DevOps - Incident Response Agent
=============================================
Handles alert triage, RCA generation, and runbook execution.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.utils.bedrock_client import get_bedrock_client

logger = logging.getLogger(__name__)


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"  # P1 - Immediate response
    HIGH = "high"          # P2 - Within 1 hour
    MEDIUM = "medium"      # P3 - Within 4 hours
    LOW = "low"            # P4 - Best effort


class IncidentStatus(str, Enum):
    OPEN = "open"
    TRIAGING = "triaging"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


# Common incident patterns and runbooks
INCIDENT_PATTERNS = {
    "high_cpu": {
        "indicators": ["cpu usage", "cpu high", "processor", "100%"],
        "severity": IncidentSeverity.HIGH,
        "category": "performance",
        "runbook": "Scale horizontally, check for resource leaks, identify hot paths"
    },
    "high_memory": {
        "indicators": ["memory", "oom", "out of memory", "heap"],
        "severity": IncidentSeverity.HIGH,
        "category": "performance",
        "runbook": "Restart pod, increase memory limits, check for memory leaks"
    },
    "database_slow": {
        "indicators": ["database", "query", "slow", "db connection", "timeout"],
        "severity": IncidentSeverity.CRITICAL,
        "category": "database",
        "runbook": "Check connection pool, analyze slow queries, verify indexes"
    },
    "high_error_rate": {
        "indicators": ["error rate", "5xx", "500", "errors"],
        "severity": IncidentSeverity.CRITICAL,
        "category": "application",
        "runbook": "Check recent deployments, rollback if needed, analyze error logs"
    },
    "deployment_failure": {
        "indicators": ["deploy", "rollout", "failed", "crashloopbackoff"],
        "severity": IncidentSeverity.HIGH,
        "category": "deployment",
        "runbook": "Check pod logs, verify image, rollback to previous version"
    },
    "ssl_certificate": {
        "indicators": ["ssl", "certificate", "tls", "https", "expired"],
        "severity": IncidentSeverity.CRITICAL,
        "category": "security",
        "runbook": "Renew certificate, update secrets, restart ingress"
    }
}


class IncidentAgent:
    """
    Incident Response Agent
    
    Capabilities:
    1. Triage incoming alerts (L1 automation)
    2. Correlate events and identify root cause
    3. Generate RCA reports
    4. Execute runbooks
    5. Send notifications
    """
    
    SYSTEM_PROMPT = """You are the Incident Response Agent for BCG's DevOps platform.

Your role is to:
1. Triage incoming alerts and determine severity
2. Correlate events to identify root cause
3. Generate detailed RCA (Root Cause Analysis) reports
4. Suggest and execute remediation steps
5. Provide status updates

BCG Incident Response Framework:
- P1/Critical: Immediate response, all hands
- P2/High: Response within 1 hour
- P3/Medium: Response within 4 hours
- P4/Low: Best effort

When analyzing incidents:
1. Identify the symptoms
2. Determine the scope (which services affected)
3. Correlate with recent changes (deployments, configs)
4. Identify the root cause
5. Suggest remediation steps

Output format:
{
    "incident_id": "INC-XXXXX",
    "severity": "critical|high|medium|low",
    "category": "performance|database|application|deployment|security|infrastructure",
    "summary": "brief summary",
    "root_cause": "identified root cause",
    "affected_services": ["service1", "service2"],
    "timeline": [
        {"time": "ISO timestamp", "event": "description"}
    ],
    "remediation": {
        "immediate": ["step1", "step2"],
        "long_term": ["step1", "step2"]
    }
}"""

    def __init__(
        self,
        bedrock_profile: str = "credit",
        region: str = "us-east-1",
        slack_webhook: str = None
    ):
        self.bedrock = get_bedrock_client(profile=bedrock_profile, region=region)
        self.slack_webhook = slack_webhook
        self.active_incidents: Dict[str, Dict] = {}
        logger.info("Incident Agent initialized")
    
    def execute(self, action: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action"""
        actions = {
            "triage_alert": self.triage_alert,
            "analyze_incident": self.analyze_incident,
            "generate_rca": self.generate_rca,
            "execute_runbook": self.execute_runbook,
            "send_notification": self.send_notification,
            "get_status": self.get_incident_status
        }
        
        handler = actions.get(action)
        if not handler:
            return {"error": f"Unknown action: {action}"}
        
        return handler(**parameters)
    
    def triage_alert(
        self,
        alert_title: str,
        alert_details: str,
        source: str = "datadog",
        service: str = None
    ) -> Dict[str, Any]:
        """
        Triage an incoming alert (L1 automation).
        
        Args:
            alert_title: Alert title/summary
            alert_details: Full alert details
            source: Alert source (datadog, prometheus, etc.)
            service: Affected service name
        """
        try:
            # Generate incident ID
            incident_id = f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Pattern matching for quick triage
            alert_text = f"{alert_title} {alert_details}".lower()
            matched_pattern = None
            
            for pattern_name, pattern_info in INCIDENT_PATTERNS.items():
                for indicator in pattern_info["indicators"]:
                    if indicator.lower() in alert_text:
                        matched_pattern = pattern_info
                        matched_pattern["pattern_name"] = pattern_name
                        break
                if matched_pattern:
                    break
            
            # Determine severity
            if matched_pattern:
                severity = matched_pattern["severity"]
                category = matched_pattern["category"]
                runbook = matched_pattern["runbook"]
            else:
                # Use AI for unknown patterns
                ai_triage = self._ai_triage(alert_title, alert_details)
                severity = ai_triage.get("severity", IncidentSeverity.MEDIUM)
                category = ai_triage.get("category", "unknown")
                runbook = ai_triage.get("runbook", "Investigate and escalate")
            
            # Create incident record
            incident = {
                "incident_id": incident_id,
                "title": alert_title,
                "details": alert_details,
                "source": source,
                "service": service,
                "severity": severity.value if isinstance(severity, IncidentSeverity) else severity,
                "category": category,
                "status": IncidentStatus.TRIAGING.value,
                "created_at": datetime.now().isoformat(),
                "pattern_matched": matched_pattern.get("pattern_name") if matched_pattern else None,
                "runbook": runbook,
                "auto_triaged": True
            }
            
            self.active_incidents[incident_id] = incident
            
            return {
                "success": True,
                "action": "triage_alert",
                "incident_id": incident_id,
                "severity": incident["severity"],
                "category": category,
                "runbook": runbook,
                "requires_immediate_action": severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH, "critical", "high"]
            }
            
        except Exception as e:
            logger.error(f"Error triaging alert: {e}")
            return {"success": False, "error": str(e)}
    
    def _ai_triage(self, title: str, details: str) -> Dict[str, Any]:
        """Use AI for triage when pattern not matched"""
        prompt = f"""Triage this alert:

Title: {title}
Details: {details}

Determine:
1. Severity (critical/high/medium/low)
2. Category (performance/database/application/deployment/security/infrastructure)
3. Recommended runbook steps

Output as JSON."""

        response = self.bedrock.invoke(prompt, self.SYSTEM_PROMPT)
        
        try:
            # Extract JSON
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except:
            pass
        
        return {
            "severity": "medium",
            "category": "unknown",
            "runbook": "Manual investigation required"
        }
    
    def analyze_incident(
        self,
        incident_id: str = None,
        description: str = None,
        logs: List[str] = None,
        metrics: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Analyze an incident to identify root cause.
        """
        try:
            # Build context
            context = {
                "description": description or "No description provided",
                "logs": logs[:20] if logs else [],
                "metrics": metrics or {}
            }
            
            if incident_id and incident_id in self.active_incidents:
                incident = self.active_incidents[incident_id]
                context["incident_details"] = incident
            
            prompt = f"""Analyze this incident and identify root cause:

{json.dumps(context, indent=2)}

Provide:
1. Root cause analysis
2. Contributing factors
3. Affected services/components
4. Timeline of events (if determinable)
5. Recommended actions

Output as JSON."""

            response = self.bedrock.invoke(prompt, self.SYSTEM_PROMPT)
            
            return {
                "success": True,
                "action": "analyze_incident",
                "incident_id": incident_id,
                "analysis": response
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def generate_rca(
        self,
        incident_id: str,
        resolution_details: str = None
    ) -> Dict[str, Any]:
        """
        Generate a formal RCA report.
        """
        try:
            incident = self.active_incidents.get(incident_id, {})
            
            prompt = f"""Generate a formal Root Cause Analysis (RCA) report for this incident:

Incident ID: {incident_id}
Title: {incident.get('title', 'Unknown')}
Details: {incident.get('details', 'No details')}
Service: {incident.get('service', 'Unknown')}
Severity: {incident.get('severity', 'Unknown')}
Resolution: {resolution_details or 'Pending'}

Generate a complete RCA following this format:

# Root Cause Analysis Report

## Incident Summary
## Timeline
## Root Cause
## Impact Assessment
## Resolution Steps
## Lessons Learned
## Action Items (with owners and due dates)
## Prevention Measures"""

            response = self.bedrock.invoke(prompt, self.SYSTEM_PROMPT)
            
            return {
                "success": True,
                "action": "generate_rca",
                "incident_id": incident_id,
                "rca_report": response,
                "format": "markdown"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def execute_runbook(
        self,
        runbook_name: str,
        parameters: Dict[str, Any] = None,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """
        Execute a runbook (with approval if needed).
        """
        try:
            # Define available runbooks
            runbooks = {
                "restart_pod": {
                    "description": "Restart a Kubernetes pod",
                    "command": "kubectl rollout restart deployment/{deployment}",
                    "requires_approval": True
                },
                "scale_deployment": {
                    "description": "Scale deployment replicas",
                    "command": "kubectl scale deployment/{deployment} --replicas={replicas}",
                    "requires_approval": True
                },
                "rollback_deployment": {
                    "description": "Rollback to previous version",
                    "command": "kubectl rollout undo deployment/{deployment}",
                    "requires_approval": True
                },
                "clear_cache": {
                    "description": "Clear application cache",
                    "command": "redis-cli FLUSHDB",
                    "requires_approval": True
                }
            }
            
            runbook = runbooks.get(runbook_name)
            if not runbook:
                return {
                    "success": False,
                    "error": f"Unknown runbook: {runbook_name}",
                    "available_runbooks": list(runbooks.keys())
                }
            
            # Format command with parameters
            command = runbook["command"]
            if parameters:
                for key, value in parameters.items():
                    command = command.replace(f"{{{key}}}", str(value))
            
            result = {
                "success": True,
                "action": "execute_runbook",
                "runbook": runbook_name,
                "command": command,
                "dry_run": dry_run,
                "requires_approval": runbook["requires_approval"]
            }
            
            if dry_run:
                result["message"] = "Dry run - command not executed"
            else:
                if runbook["requires_approval"]:
                    result["status"] = "awaiting_approval"
                    result["message"] = "Requires human approval before execution"
                else:
                    result["status"] = "executed"
                    result["message"] = "Runbook executed successfully"
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def send_notification(
        self,
        incident_id: str,
        channel: str = "slack",
        message: str = None
    ) -> Dict[str, Any]:
        """
        Send incident notification to Slack.
        """
        try:
            incident = self.active_incidents.get(incident_id, {})
            
            if not message:
                severity = incident.get("severity", "medium")
                emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(severity, "⚪")
                
                message = f"""{emoji} *Incident Alert*

*ID:* {incident_id}
*Title:* {incident.get('title', 'Unknown')}
*Severity:* {severity.upper()}
*Service:* {incident.get('service', 'Unknown')}
*Status:* {incident.get('status', 'open')}

*Runbook:* {incident.get('runbook', 'Check logs and investigate')}
"""
            
            if self.slack_webhook:
                import urllib.request
                
                payload = {"text": message}
                req = urllib.request.Request(
                    self.slack_webhook,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={'Content-Type': 'application/json'}
                )
                urllib.request.urlopen(req, timeout=10)
            
            return {
                "success": True,
                "action": "send_notification",
                "incident_id": incident_id,
                "channel": channel,
                "message_sent": True
            }
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return {"success": False, "error": str(e)}
    
    def get_incident_status(self, incident_id: str = None) -> Dict[str, Any]:
        """Get status of incident(s)"""
        if incident_id:
            incident = self.active_incidents.get(incident_id)
            if not incident:
                return {"error": f"Incident {incident_id} not found"}
            return {"success": True, "incident": incident}
        
        return {
            "success": True,
            "active_incidents": len(self.active_incidents),
            "incidents": list(self.active_incidents.values())
        }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = IncidentAgent()
    
    # Test triage
    result = agent.triage_alert(
        alert_title="High CPU Usage Alert",
        alert_details="CPU usage at 95% on production-api-1 for last 10 minutes",
        service="api-gateway"
    )
    print(json.dumps(result, indent=2))
