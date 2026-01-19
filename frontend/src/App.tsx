import { useState, useCallback, useEffect, useRef } from 'react'

// API Configuration
const API_BASE = '/api'
const DEMO_REPOS = [
    'expressjs/express',
    'facebook/react',
    'vercel/next.js',
    'pallets/flask',
    'golang/go'
]

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function apiCall<T>(endpoint: string, data?: object): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: data ? 'POST' : 'GET',
        headers: { 'Content-Type': 'application/json' },
        body: data ? JSON.stringify(data) : undefined
    })
    return response.json()
}

// Types
interface AgentActivity {
    id: string
    agent: string
    action: string
    status: 'running' | 'completed' | 'failed' | 'pending'
    message: string
    timestamp: Date
}

interface Message {
    id: string
    type: 'user' | 'agent' | 'system'
    content: string
    timestamp: Date
    agentType?: string
}

interface ApprovalRequest {
    id: string
    title: string
    description: string
    status: 'pending' | 'approved' | 'rejected'
}

interface PipelineStatus {
    name: string
    status: 'success' | 'running' | 'failed' | 'pending'
    duration?: string
}

type View = 'dashboard' | 'chat' | 'pipelines'

// Format agent response to natural language
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function formatAgentResponse(result: any, action: string): string {
    if (!result.success) {
        return `❌ I encountered an error: ${result.error || 'Unknown error'}\n\nPlease try again or check the repository name.`
    }

    switch (action) {
        case 'analyze':
            const analysis = result.analysis || result
            const techStack = (analysis.tech_stack || []).join(', ') || 'Not detected'
            const workflows = (analysis.existing_workflows || []).slice(0, 5).join(', ')

            return `## ✅ Repository Analysis Complete

**📦 Repository**: \`${analysis.repository || result.repository}\`
**🔧 Tech Stack**: ${techStack}
**📋 Package Manager**: ${analysis.package_manager || 'Unknown'}
**🌐 Primary Language**: ${analysis.primary_language || 'Unknown'}

### CI/CD Status
${analysis.has_github_actions ? '✅ **GitHub Actions configured**' : '⚠️ No CI/CD workflows found'}
${workflows ? `\n📁 Workflows: ${workflows}` : ''}

### Infrastructure
${analysis.has_dockerfile ? '🐳 Dockerfile: ✅' : '🐳 Dockerfile: ❌'}
${analysis.has_kubernetes ? '☸️ Kubernetes: ✅' : ''}
${analysis.has_terraform ? '🏗️ Terraform: ✅' : ''}

### Recommendations
${(analysis.recommendations || ['Add CI/CD workflow', 'Add Docker support']).map((r: string) => `• ${r}`).join('\n')}

---
*Would you like me to **generate a CI/CD workflow** or **run a security scan**?*`

        case 'generate':
            return `## ⚡ CI/CD Workflow Generated

I've created a **BCG-compliant workflow** with:

| Stage | Integration |
|-------|-------------|
| 🔨 Build & Test | npm/pip/go |
| 🔍 Code Quality | **SonarQube** |
| 🔒 Security | **Prisma Cloud** |
| 📦 Artifacts | **JFrog Artifactory** |
| 🚀 Deployment | **ArgoCD** (GitOps) |
| 📊 Monitoring | **Datadog** |

### Preview
\`\`\`yaml
name: BCG DevOps Pipeline
on: [push, pull_request]
jobs:
  build-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build & Test
        run: npm ci && npm test
  sonarqube:
    needs: build-test
    uses: SonarSource/sonarqube-scan-action@v2
  security:
    uses: bridgecrewio/checkov-action@v12
  deploy:
    needs: [sonarqube, security]
    # ArgoCD GitOps deployment
\`\`\`

---
🔔 **Approval Required**: Create PR with this workflow?`

        case 'triage':
            const severityColors: Record<string, string> = {
                'critical': '🔴',
                'high': '🟠',
                'medium': '🟡',
                'low': '🟢'
            }
            const emoji = severityColors[result.severity] || '⚪'

            return `## ${emoji} Incident Triaged

**ID**: \`${result.incident_id}\`
**Severity**: ${result.severity?.toUpperCase()}
**Category**: ${result.category}

### Recommended Runbook
${result.runbook}

### Suggested Actions
1. Check recent deployments for changes
2. Review application logs
3. Monitor system metrics
4. ${result.requires_immediate_action ? '**⚠️ ESCALATE IMMEDIATELY**' : 'Schedule investigation'}

---
*Would you like me to **generate an RCA report** or **execute a runbook**?*`

        case 'scan':
            const findings = result.findings || {}
            const summary = findings.summary || {}
            const vulns = findings.dependency_vulnerabilities || []

            return `## 🔒 Security Scan Complete

### Summary
| Severity | Count |
|----------|-------|
| 🔴 Critical | ${summary.critical || 0} |
| 🟠 High | ${summary.high || 0} |
| 🟡 Medium | ${summary.medium || 0} |
| 🟢 Low | ${summary.low || 0} |

${vulns.length > 0 ? `### Vulnerabilities Found
${vulns.slice(0, 5).map((v: any) => `• **${v.package}** (${v.severity}) - ${v.cve || 'Security fix needed'}\n  → Upgrade to \`${v.fixed_version || 'latest'}\``).join('\n')}` : '### ✅ No Critical Vulnerabilities!'}

${(findings.secret_leaks || []).length > 0 ? `\n### ⚠️ Secret Leaks Detected!
${findings.secret_leaks.map((s: any) => `• \`${s.file}\`: ${s.issue}`).join('\n')}` : ''}

---
🔔 **Approval Required**: Create PR with security fixes?`

        case 'report':
            return `## 📊 Security Report\n\n${result.report?.substring(0, 2000) || 'Report generated successfully'}`

        default:
            return `## ✅ Action Completed\n\n${JSON.stringify(result, null, 2)}`
    }
}

function App() {
    const [activeView, setActiveView] = useState<View>('chat')
    const [loading, setLoading] = useState(false)
    const [messages, setMessages] = useState<Message[]>([])
    const [activities, setActivities] = useState<AgentActivity[]>([])
    const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
    const [chatInput, setChatInput] = useState('')
    const [repo, setRepo] = useState('expressjs/express')
    const [pipelines, setPipelines] = useState<PipelineStatus[]>([
        { name: 'Build & Test', status: 'success', duration: '2m 15s' },
        { name: 'Code Quality (SonarQube)', status: 'success', duration: '1m 45s' },
        { name: 'Security Scan (Prisma)', status: 'running' },
        { name: 'Container Build', status: 'pending' },
        { name: 'Deploy (ArgoCD)', status: 'pending' }
    ])
    const messagesEndRef = useRef<HTMLDivElement>(null)

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Simulate pipeline progress
    useEffect(() => {
        const timer = setInterval(() => {
            setPipelines(prev => {
                const current = prev.findIndex(p => p.status === 'running')
                if (current === -1) return prev

                return prev.map((p, i) => {
                    if (i === current) return { ...p, status: 'success' as const, duration: '1m 30s' }
                    if (i === current + 1) return { ...p, status: 'running' as const }
                    return p
                })
            })
        }, 5000)
        return () => clearInterval(timer)
    }, [])

    const addActivity = useCallback((agent: string, action: string, status: AgentActivity['status'], message: string) => {
        const activity: AgentActivity = {
            id: Date.now().toString(),
            agent,
            action,
            status,
            message,
            timestamp: new Date()
        }
        setActivities(prev => [activity, ...prev].slice(0, 15))
        return activity.id
    }, [])

    const updateActivity = useCallback((id: string, updates: Partial<AgentActivity>) => {
        setActivities(prev => prev.map(a => a.id === id ? { ...a, ...updates } : a))
    }, [])

    const processCommand = useCallback((input: string) => {
        const lower = input.toLowerCase()
        if (lower.includes('analyze') || lower.includes('check') || lower.includes('what')) {
            return { action: 'analyze', endpoint: '/workflow/analyze' }
        } else if (lower.includes('generate') || lower.includes('workflow') || lower.includes('ci/cd') || lower.includes('pipeline')) {
            return { action: 'generate', endpoint: '/workflow/generate' }
        } else if (lower.includes('security') || lower.includes('scan') || lower.includes('vulnerab')) {
            return { action: 'scan', endpoint: '/security/scan' }
        } else if (lower.includes('report')) {
            return { action: 'report', endpoint: '/security/report' }
        } else if (lower.includes('alert') || lower.includes('incident') || lower.includes('cpu') || lower.includes('error') || lower.includes('triage')) {
            return { action: 'triage', endpoint: '/incident/triage' }
        }
        return { action: 'analyze', endpoint: '/workflow/analyze' }
    }, [])

    const sendMessage = useCallback(async () => {
        if (!chatInput.trim() || loading) return

        const userMsg: Message = {
            id: Date.now().toString(),
            type: 'user',
            content: chatInput,
            timestamp: new Date()
        }
        setMessages(prev => [...prev, userMsg])
        const inputText = chatInput
        setChatInput('')
        setLoading(true)

        const activityId = addActivity('Supervisor', 'Processing', 'running', 'Analyzing your request...')

        try {
            const { action, endpoint } = processCommand(inputText)

            let data: object = action === 'triage'
                ? { title: inputText, details: inputText, source: 'user', service: 'unknown' }
                : { repository: repo }

            updateActivity(activityId, { message: `Routing to ${action} agent...` })

            const agentName = action === 'triage' ? 'Incident Agent' : action === 'scan' ? 'Security Agent' : 'Workflow Agent'
            const subActivityId = addActivity(agentName, action, 'running', `Executing ${action}...`)

            const result = await apiCall<object>(endpoint, data)

            updateActivity(activityId, { status: 'completed', message: 'Request completed' })
            updateActivity(subActivityId, { status: 'completed', message: `${action} completed` })

            const response = formatAgentResponse(result, action)

            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                type: 'agent',
                content: response,
                timestamp: new Date(),
                agentType: agentName
            }])

            // Add approval for certain actions
            if (action === 'generate' || action === 'scan') {
                setApprovals(prev => [...prev, {
                    id: Date.now().toString(),
                    title: action === 'generate' ? 'Create Workflow PR?' : 'Create Security Fix PR?',
                    description: action === 'generate'
                        ? 'The agent wants to create a PR with the generated CI/CD workflow'
                        : 'The agent wants to create a PR with security fixes',
                    status: 'pending'
                }])
            }

        } catch (e) {
            updateActivity(activityId, { status: 'failed', message: `Error: ${e}` })
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                type: 'agent',
                content: `❌ Error processing request: ${e}`,
                timestamp: new Date(),
                agentType: 'System'
            }])
        } finally {
            setLoading(false)
        }
    }, [chatInput, repo, loading, addActivity, updateActivity, processCommand])

    const handleApproval = useCallback((id: string, approved: boolean) => {
        setApprovals(prev => prev.map(a => a.id === id ? { ...a, status: approved ? 'approved' : 'rejected' } : a))

        if (approved) {
            addActivity('GitHub', 'Creating PR', 'running', 'Creating pull request...')
            setTimeout(() => {
                addActivity('GitHub', 'PR Created', 'completed', 'PR #42 created successfully')
                setMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    type: 'system',
                    content: '✅ **PR Created!** Pull request #42 has been created.\n\n[View PR on GitHub →](https://github.com)',
                    timestamp: new Date()
                }])
            }, 2000)
        }
    }, [addActivity])

    const quickActions = [
        { icon: '🔍', label: 'Analyze Repo', cmd: 'Analyze this repository and tell me about it' },
        { icon: '⚡', label: 'Generate CI/CD', cmd: 'Generate a CI/CD workflow for this repository' },
        { icon: '🔒', label: 'Security Scan', cmd: 'Scan this repository for security vulnerabilities' },
        { icon: '🚨', label: 'Triage Alert', cmd: 'High CPU alert on production server at 95% for 10 minutes' },
    ]

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="logo">
                    <div className="logo-icon">🤖</div>
                    <h2>BCG DevOps<span>Agentic Platform</span></h2>
                </div>

                {/* Repo Selector */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <div className="nav-title">Repository</div>
                    <select
                        value={repo}
                        onChange={(e) => setRepo(e.target.value)}
                        style={{ marginBottom: '0.5rem' }}
                    >
                        {DEMO_REPOS.map(r => <option key={r} value={r}>{r}</option>)}
                    </select>
                    <div className="badge success">✓ Connected</div>
                </div>

                {/* Nav */}
                <nav className="nav-section">
                    <div className="nav-title">Navigation</div>
                    {[
                        { id: 'chat' as View, icon: '💬', label: 'Agentic Chat' },
                        { id: 'pipelines' as View, icon: '🚀', label: 'Pipelines' },
                        { id: 'dashboard' as View, icon: '📊', label: 'Dashboard' },
                    ].map(item => (
                        <div
                            key={item.id}
                            className={`nav-item ${activeView === item.id ? 'active' : ''}`}
                            onClick={() => setActiveView(item.id)}
                        >
                            <span className="nav-icon">{item.icon}</span>
                            {item.label}
                        </div>
                    ))}
                </nav>

                {/* Agent Activity */}
                <div className="nav-section" style={{ flex: 1, overflow: 'hidden' }}>
                    <div className="nav-title">Agent Activity</div>
                    <div className="agent-activity" style={{ maxHeight: '200px', overflowY: 'auto' }}>
                        {activities.length === 0 ? (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.5rem' }}>
                                No recent activity
                            </div>
                        ) : activities.slice(0, 8).map(a => (
                            <div className="activity-item" key={a.id}>
                                <div className={`activity-dot ${a.status}`}></div>
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: '0.7rem', fontWeight: 600, color: 'var(--text-primary)' }}>{a.agent}</div>
                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.message}</div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Integrations */}
                <div style={{ marginTop: 'auto', paddingTop: '1rem', borderTop: '1px solid var(--border)' }}>
                    <div className="nav-title">BCG Integrations</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                        {['GitHub', 'JFrog', 'SonarQube', 'Prisma', 'ArgoCD', 'Datadog'].map(tool => (
                            <div key={tool} className="badge success" style={{ fontSize: '0.6rem' }}>{tool}</div>
                        ))}
                    </div>
                </div>
            </aside>

            {/* Main */}
            <main className="main-content">
                <header className="header">
                    <h1>🤖 BCG Agentic DevOps</h1>
                    <p>Natural language DevOps automation • CI/CD • Security • Incident Response</p>
                </header>

                {/* Approvals */}
                {approvals.filter(a => a.status === 'pending').map(approval => (
                    <div key={approval.id} style={{ padding: '1rem 2rem', background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1))', borderBottom: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                            <span style={{ fontSize: '1.5rem' }}>🔔</span>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontWeight: 600 }}>{approval.title}</div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{approval.description}</div>
                            </div>
                            <button className="btn btn-primary" onClick={() => handleApproval(approval.id, true)}>✅ Approve</button>
                            <button className="btn btn-secondary" onClick={() => handleApproval(approval.id, false)}>❌ Reject</button>
                        </div>
                    </div>
                ))}

                {/* Chat View */}
                {activeView === 'chat' && (
                    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 180px)' }}>
                        <div style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
                            {messages.length === 0 && (
                                <div style={{ textAlign: 'center', padding: '3rem' }}>
                                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🤖</div>
                                    <h3>Hi! I'm your DevOps Agent</h3>
                                    <p style={{ color: 'var(--text-muted)', margin: '0.5rem auto', maxWidth: '500px' }}>
                                        I can analyze repos, generate CI/CD workflows, scan for vulnerabilities, and triage incidents.
                                    </p>
                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center', marginTop: '2rem' }}>
                                        {quickActions.map((qa, i) => (
                                            <button key={i} className="btn btn-secondary" style={{ fontSize: '0.8rem' }} onClick={() => { setChatInput(qa.cmd) }}>
                                                {qa.icon} {qa.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {messages.map(msg => (
                                <div className="message" key={msg.id}>
                                    <div className={`message-avatar ${msg.type}`}>
                                        {msg.type === 'user' ? '👤' : msg.type === 'system' ? '⚙️' : '🤖'}
                                    </div>
                                    <div className="message-content">
                                        <div className="message-header">
                                            <span className="message-name">{msg.type === 'user' ? 'You' : msg.agentType || 'System'}</span>
                                            <span className="message-time">{msg.timestamp.toLocaleTimeString()}</span>
                                        </div>
                                        <div className="message-text" style={{ whiteSpace: 'pre-wrap' }}
                                            dangerouslySetInnerHTML={{
                                                __html: msg.content
                                                    .replace(/## (.*?)\n/g, '<h4 style="font-size:1rem;margin:0.5rem 0">$1</h4>')
                                                    .replace(/### (.*?)\n/g, '<h5 style="font-size:0.9rem;margin:0.5rem 0;color:var(--accent-light)">$1</h5>')
                                                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                                    .replace(/`([^`]+)`/g, '<code style="background:var(--bg-secondary);padding:0.1rem 0.4rem;border-radius:4px;font-size:0.8rem">$1</code>')
                                                    .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre style="background:var(--bg-secondary);padding:1rem;border-radius:8px;margin:0.5rem 0;overflow-x:auto;font-size:0.75rem"><code>$2</code></pre>')
                                                    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" style="color:var(--accent-light)">$1</a>')
                                                    .replace(/\n\|(.+)\|/g, (m) => `<div style="font-family:monospace;font-size:0.75rem">${m}</div>`)
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}

                            {loading && (
                                <div className="message">
                                    <div className="message-avatar agent">🤖</div>
                                    <div className="message-content" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                        <div className="loading"></div>
                                        <span style={{ color: 'var(--text-muted)' }}>Agent is thinking...</span>
                                    </div>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)', background: 'var(--bg-secondary)' }}>
                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                <input
                                    type="text"
                                    placeholder="Ask anything about DevOps..."
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                                    style={{ marginBottom: 0 }}
                                />
                                <button className="btn btn-primary" onClick={sendMessage} disabled={loading || !chatInput.trim()} style={{ minWidth: '120px' }}>
                                    {loading ? <div className="loading"></div> : '🚀 Send'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Pipelines View */}
                {activeView === 'pipelines' && (
                    <div className="content">
                        <h3 style={{ marginBottom: '1.5rem' }}>🚀 Pipeline Status - {repo}</h3>
                        <div className="card">
                            {pipelines.map((p, i) => (
                                <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '1rem', borderBottom: i < pipelines.length - 1 ? '1px solid var(--border)' : 'none' }}>
                                    <div style={{ width: '24px', height: '24px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', background: p.status === 'success' ? 'var(--success)' : p.status === 'running' ? 'var(--warning)' : p.status === 'failed' ? 'var(--error)' : 'var(--text-muted)', fontSize: '0.8rem' }}>
                                        {p.status === 'success' ? '✓' : p.status === 'running' ? '⟳' : p.status === 'failed' ? '✗' : '○'}
                                    </div>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: 500 }}>{p.name}</div>
                                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                            {p.status === 'running' ? 'In progress...' : p.status === 'pending' ? 'Waiting...' : p.duration || 'Completed'}
                                        </div>
                                    </div>
                                    <div className={`badge ${p.status === 'success' ? 'success' : p.status === 'running' ? 'warning' : p.status === 'failed' ? 'error' : ''}`}>
                                        {p.status}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Dashboard */}
                {activeView === 'dashboard' && (
                    <div className="content">
                        <div className="grid grid-2">
                            {[
                                { icon: '⚡', title: 'Workflow Generator', desc: 'Auto-generate CI/CD', color: 'workflow', cmd: 'Generate a CI/CD workflow' },
                                { icon: '🔒', title: 'Security Agent', desc: 'Scan & auto-fix', color: 'security', cmd: 'Scan for security vulnerabilities' },
                                { icon: '🚨', title: 'Incident Agent', desc: 'L1 triage & RCA', color: 'incident', cmd: 'High CPU alert on production' },
                                { icon: '📊', title: 'Repo Analysis', desc: 'Tech stack detection', color: 'chat', cmd: 'Analyze this repository' },
                            ].map((card, i) => (
                                <div key={i} className="card" onClick={() => { setActiveView('chat'); setChatInput(card.cmd); }} style={{ cursor: 'pointer' }}>
                                    <div className="card-header">
                                        <div className={`card-icon ${card.color}`}>{card.icon}</div>
                                        <div>
                                            <h3>{card.title}</h3>
                                            <p>{card.desc}</p>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Status Bar */}
                <div className="status-bar">
                    <div className="status-item"><div className="status-dot"></div> Platform Active</div>
                    <div className="status-item">🧠 AWS Bedrock Nova Pro</div>
                    <div className="status-item">📍 us-east-1</div>
                    <div className="status-item">🔧 {activities.filter(a => a.status === 'running').length} agents working</div>
                </div>
            </main>
        </div>
    )
}

export default App
