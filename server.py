"""
BCG Agentic DevOps Platform - FastAPI Server
==============================================
Production-ready API server for BCG DevOps demos.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bcg-devops-api")

# Import agents
from agents.supervisor.agent import SupervisorAgent, AgentType
from agents.workflow.agent import WorkflowGeneratorAgent
from agents.security.agent import SecurityAgent
from agents.incident.agent import IncidentAgent

# =============================================================================
# Configuration
# =============================================================================

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
AWS_PROFILE = os.environ.get("AWS_PROFILE", "credit")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")

# Global agent instances
platform = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agents on startup"""
    global platform
    logger.info("🚀 Starting BCG Agentic DevOps Platform...")
    
    platform = {
        "supervisor": SupervisorAgent(bedrock_profile=AWS_PROFILE, region=AWS_REGION),
        "workflow": WorkflowGeneratorAgent(github_token=GITHUB_TOKEN, bedrock_profile=AWS_PROFILE, region=AWS_REGION),
        "security": SecurityAgent(github_token=GITHUB_TOKEN, bedrock_profile=AWS_PROFILE, region=AWS_REGION),
        "incident": IncidentAgent(bedrock_profile=AWS_PROFILE, region=AWS_REGION)
    }
    
    # Register agents with supervisor
    platform["supervisor"].register_agent(AgentType.WORKFLOW, platform["workflow"])
    platform["supervisor"].register_agent(AgentType.SECURITY, platform["security"])
    platform["supervisor"].register_agent(AgentType.INCIDENT, platform["incident"])
    
    logger.info("✅ All agents initialized successfully")
    yield
    logger.info("👋 Shutting down BCG DevOps Platform")

# =============================================================================
# FastAPI App
# =============================================================================

app = FastAPI(
    title="BCG Agentic DevOps Platform",
    description="""
## 🚀 Intelligent DevOps Automation

Agentic AI platform for BCG's DevOps automation:

- **Workflow Generator**: Auto-generate CI/CD pipelines for any tech stack
- **Security Agent**: Scan vulnerabilities, create fix PRs
- **Incident Agent**: L1 triage, RCA generation, runbook execution

### BCG Tool Integrations
GitHub Actions, JFrog Artifactory, SonarQube, Prisma Cloud, ArgoCD, Datadog
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Request/Response Models
# =============================================================================

class ChatRequest(BaseModel):
    message: str = Field(..., description="Natural language request")
    repository: Optional[str] = Field(None, description="Repository context (owner/repo)")
    
class ChatResponse(BaseModel):
    success: bool
    response: str
    plan_id: Optional[str] = None
    actions: Optional[List[Dict]] = None

class RepoRequest(BaseModel):
    repository: str = Field(..., description="Repository in format owner/repo")

class WorkflowRequest(BaseModel):
    repository: str
    language: Optional[str] = None
    include_security: bool = True
    include_deploy: bool = True
    create_pr: bool = False

class AlertRequest(BaseModel):
    title: str = Field(..., description="Alert title")
    details: str = Field(..., description="Alert details")
    source: str = Field(default="datadog", description="Alert source")
    service: Optional[str] = Field(None, description="Affected service")

class RCARequest(BaseModel):
    incident_id: str
    resolution: Optional[str] = None

# =============================================================================
# API Endpoints
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Landing page with interactive demo"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BCG Agentic DevOps Platform</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #2563eb;
            --primary-dark: #1d4ed8;
            --secondary: #10b981;
            --dark: #1e293b;
            --light: #f8fafc;
            --gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Inter', sans-serif; 
            background: #0f172a;
            min-height: 100vh;
            color: #e2e8f0;
        }
        
        .header {
            background: linear-gradient(135deg, rgba(37,99,235,0.2) 0%, rgba(124,58,237,0.2) 100%);
            border-bottom: 1px solid rgba(255,255,255,0.1);
            padding: 1.5rem 2rem;
            backdrop-filter: blur(20px);
        }
        
        .header h1 {
            font-size: 1.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, #60a5fa, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p { color: #94a3b8; font-size: 0.9rem; margin-top: 0.25rem; }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-top: 1.5rem;
        }
        
        .card {
            background: rgba(30, 41, 59, 0.8);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px;
            padding: 1.5rem;
            transition: all 0.3s;
        }
        
        .card:hover {
            border-color: rgba(99, 102, 241, 0.5);
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.3);
        }
        
        .card-header {
            display: flex;
            align-items: center;
            gap: 1rem;
            margin-bottom: 1rem;
        }
        
        .card-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }
        
        .icon-workflow { background: linear-gradient(135deg, #3b82f6, #8b5cf6); }
        .icon-security { background: linear-gradient(135deg, #ef4444, #f97316); }
        .icon-incident { background: linear-gradient(135deg, #10b981, #14b8a6); }
        .icon-chat { background: linear-gradient(135deg, #6366f1, #ec4899); }
        
        .card h3 { font-size: 1.1rem; font-weight: 600; }
        .card p { color: #94a3b8; font-size: 0.875rem; margin-top: 0.5rem; line-height: 1.6; }
        
        .input-group {
            margin-top: 1rem;
        }
        
        input, textarea, select {
            width: 100%;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 0.75rem 1rem;
            color: #e2e8f0;
            font-size: 0.875rem;
            margin-bottom: 0.75rem;
            transition: all 0.2s;
        }
        
        input:focus, textarea:focus {
            outline: none;
            border-color: #6366f1;
            box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.2);
        }
        
        button {
            width: 100%;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.5rem;
            color: white;
            font-weight: 600;
            font-size: 0.875rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .result {
            margin-top: 1rem;
            background: rgba(15, 23, 42, 0.8);
            border-radius: 8px;
            padding: 1rem;
            font-family: 'Monaco', monospace;
            font-size: 0.75rem;
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            display: none;
        }
        
        .result.show { display: block; }
        .result.success { border-left: 3px solid #10b981; }
        .result.error { border-left: 3px solid #ef4444; }
        
        .badges {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }
        
        .badge {
            background: rgba(99, 102, 241, 0.2);
            border: 1px solid rgba(99, 102, 241, 0.3);
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.7rem;
            color: #a5b4fc;
        }
        
        .status-bar {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(30, 41, 59, 0.95);
            border-top: 1px solid rgba(255,255,255,0.1);
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            backdrop-filter: blur(20px);
        }
        
        .status-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.8rem;
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .loading {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 BCG Agentic DevOps Platform</h1>
        <p>Intelligent DevOps Automation powered by AWS Bedrock Nova Pro</p>
    </div>
    
    <div class="container">
        <div class="grid">
            <!-- Chat Agent -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-chat">💬</div>
                    <div>
                        <h3>Agentic Chat</h3>
                        <p>Natural language DevOps requests</p>
                    </div>
                </div>
                <div class="input-group">
                    <textarea id="chatInput" rows="3" placeholder="e.g., Setup CI/CD for my Node.js app with security scanning"></textarea>
                    <input type="text" id="chatRepo" placeholder="Repository (optional): owner/repo">
                    <button onclick="sendChat()">🚀 Send Request</button>
                </div>
                <div id="chatResult" class="result"></div>
            </div>
            
            <!-- Workflow Generator -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-workflow">⚡</div>
                    <div>
                        <h3>Workflow Generator</h3>
                        <p>Auto-generate BCG-compliant CI/CD</p>
                    </div>
                </div>
                <div class="input-group">
                    <input type="text" id="workflowRepo" placeholder="Repository: owner/repo">
                    <select id="workflowAction">
                        <option value="analyze">🔍 Analyze Repository</option>
                        <option value="generate">⚙️ Generate Workflow</option>
                        <option value="create-pr">📝 Create PR with Workflow</option>
                    </select>
                    <button onclick="runWorkflow()">Generate</button>
                </div>
                <div class="badges">
                    <span class="badge">GitHub Actions</span>
                    <span class="badge">JFrog</span>
                    <span class="badge">SonarQube</span>
                    <span class="badge">ArgoCD</span>
                </div>
                <div id="workflowResult" class="result"></div>
            </div>
            
            <!-- Security Agent -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-security">🔒</div>
                    <div>
                        <h3>Security Agent</h3>
                        <p>Scan vulnerabilities & auto-fix</p>
                    </div>
                </div>
                <div class="input-group">
                    <input type="text" id="securityRepo" placeholder="Repository: owner/repo">
                    <select id="securityAction">
                        <option value="scan">🔍 Scan Repository</option>
                        <option value="report">📊 Generate Report</option>
                        <option value="fix-pr">🔧 Create Fix PR</option>
                    </select>
                    <button onclick="runSecurity()">Run Scan</button>
                </div>
                <div class="badges">
                    <span class="badge">CVE Detection</span>
                    <span class="badge">Secret Scan</span>
                    <span class="badge">Prisma Cloud</span>
                </div>
                <div id="securityResult" class="result"></div>
            </div>
            
            <!-- Incident Agent -->
            <div class="card">
                <div class="card-header">
                    <div class="card-icon icon-incident">🚨</div>
                    <div>
                        <h3>Incident Agent</h3>
                        <p>L1 Triage & RCA Generation</p>
                    </div>
                </div>
                <div class="input-group">
                    <input type="text" id="alertTitle" placeholder="Alert Title: e.g., High CPU Usage">
                    <textarea id="alertDetails" rows="2" placeholder="Alert Details: e.g., CPU at 95% on api-server"></textarea>
                    <input type="text" id="alertService" placeholder="Service: e.g., api-gateway">
                    <button onclick="triageAlert()">🔔 Triage Alert</button>
                </div>
                <div class="badges">
                    <span class="badge">Auto Triage</span>
                    <span class="badge">RCA</span>
                    <span class="badge">Runbooks</span>
                </div>
                <div id="incidentResult" class="result"></div>
            </div>
        </div>
    </div>
    
    <div class="status-bar">
        <div class="status-item">
            <div class="status-dot"></div>
            <span>Platform Active</span>
        </div>
        <div class="status-item">
            <span>🧠 Bedrock Nova Pro</span>
        </div>
        <div class="status-item">
            <span>📍 us-east-1</span>
        </div>
    </div>
    
    <script>
        const API = '';
        
        async function apiCall(endpoint, data) {
            const response = await fetch(API + endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await response.json();
        }
        
        async function sendChat() {
            const input = document.getElementById('chatInput');
            const repo = document.getElementById('chatRepo');
            const result = document.getElementById('chatResult');
            
            result.className = 'result show';
            result.textContent = '⏳ Processing...';
            
            try {
                const data = await apiCall('/api/chat', {
                    message: input.value,
                    repository: repo.value || null
                });
                result.className = 'result show success';
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result show error';
                result.textContent = 'Error: ' + e.message;
            }
        }
        
        async function runWorkflow() {
            const repo = document.getElementById('workflowRepo');
            const action = document.getElementById('workflowAction');
            const result = document.getElementById('workflowResult');
            
            result.className = 'result show';
            result.textContent = '⏳ Processing...';
            
            try {
                let endpoint = '/api/workflow/analyze';
                if (action.value === 'generate') endpoint = '/api/workflow/generate';
                if (action.value === 'create-pr') endpoint = '/api/workflow/create-pr';
                
                const data = await apiCall(endpoint, { repository: repo.value });
                result.className = 'result show success';
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result show error';
                result.textContent = 'Error: ' + e.message;
            }
        }
        
        async function runSecurity() {
            const repo = document.getElementById('securityRepo');
            const action = document.getElementById('securityAction');
            const result = document.getElementById('securityResult');
            
            result.className = 'result show';
            result.textContent = '⏳ Processing...';
            
            try {
                let endpoint = '/api/security/scan';
                if (action.value === 'report') endpoint = '/api/security/report';
                if (action.value === 'fix-pr') endpoint = '/api/security/fix';
                
                const data = await apiCall(endpoint, { repository: repo.value });
                result.className = 'result show success';
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result show error';
                result.textContent = 'Error: ' + e.message;
            }
        }
        
        async function triageAlert() {
            const title = document.getElementById('alertTitle');
            const details = document.getElementById('alertDetails');
            const service = document.getElementById('alertService');
            const result = document.getElementById('incidentResult');
            
            result.className = 'result show';
            result.textContent = '⏳ Triaging...';
            
            try {
                const data = await apiCall('/api/incident/triage', {
                    title: title.value,
                    details: details.value,
                    source: 'datadog',
                    service: service.value || null
                });
                result.className = 'result show success';
                result.textContent = JSON.stringify(data, null, 2);
            } catch (e) {
                result.className = 'result show error';
                result.textContent = 'Error: ' + e.message;
            }
        }
    </script>
</body>
</html>
    """

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "platform": "BCG Agentic DevOps",
        "version": "1.0.0",
        "agents": ["supervisor", "workflow", "security", "incident"],
        "timestamp": datetime.now().isoformat()
    }

# =============================================================================
# Chat/Agentic Endpoint
# =============================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Natural language DevOps requests.
    The Supervisor agent will analyze and route to appropriate agents.
    """
    try:
        context = {"repository": request.repository} if request.repository else {}
        
        # Analyze request
        analysis = platform["supervisor"].analyze_request(request.message, context)
        
        if not analysis.get("success"):
            raise HTTPException(status_code=500, detail=analysis.get("error"))
        
        plan_data = analysis.get("analysis", {})
        
        return ChatResponse(
            success=True,
            response=f"Analyzed request. Intent: {plan_data.get('intent', 'Unknown')}",
            plan_id=None,
            actions=plan_data.get("execution_plan", [])
        )
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Workflow Endpoints
# =============================================================================

@app.post("/api/workflow/analyze")
async def analyze_repository(request: RepoRequest):
    """Analyze a GitHub repository to detect tech stack"""
    try:
        result = platform["workflow"].analyze_repository(request.repository)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflow/generate")
async def generate_workflow(request: WorkflowRequest):
    """Generate BCG-compliant CI/CD workflow"""
    try:
        result = platform["workflow"].generate_workflow(
            request.repository,
            language=request.language,
            include_security=request.include_security,
            include_deploy=request.include_deploy
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/workflow/create-pr")
async def create_workflow_pr(request: RepoRequest):
    """Create a PR with generated workflow"""
    try:
        result = platform["workflow"].create_pr_with_workflow(request.repository)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/workflow/status/{repository:path}")
async def get_workflow_status(repository: str):
    """Get workflow run status"""
    try:
        result = platform["workflow"].get_workflow_status(repository)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Security Endpoints
# =============================================================================

@app.post("/api/security/scan")
async def security_scan(request: RepoRequest):
    """Scan repository for security vulnerabilities"""
    try:
        result = platform["security"].scan_repository(request.repository)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/security/report")
async def security_report(request: RepoRequest):
    """Generate security compliance report"""
    try:
        result = platform["security"].generate_report(request.repository)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/security/fix")
async def create_security_fix(request: RepoRequest):
    """Create PR with security fixes"""
    try:
        result = platform["security"].create_fix_pr(request.repository)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# Incident Endpoints
# =============================================================================

@app.post("/api/incident/triage")
async def triage_incident(request: AlertRequest):
    """Triage an incoming alert (L1 automation)"""
    try:
        result = platform["incident"].triage_alert(
            alert_title=request.title,
            alert_details=request.details,
            source=request.source,
            service=request.service
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/incident/rca")
async def generate_rca(request: RCARequest):
    """Generate Root Cause Analysis report"""
    try:
        result = platform["incident"].generate_rca(
            incident_id=request.incident_id,
            resolution_details=request.resolution
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incident/status")
async def get_incidents():
    """Get all active incidents"""
    try:
        result = platform["incident"].get_incident_status()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/incident/{incident_id}")
async def get_incident(incident_id: str):
    """Get specific incident details"""
    try:
        result = platform["incident"].get_incident_status(incident_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Run Server
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
