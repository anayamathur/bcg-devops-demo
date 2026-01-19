import { useState, useCallback, useEffect, useRef } from 'react'

// API Configuration
const API_BASE = '/api'
const GITHUB_REPO = 'anayamathur/bcg' // Pre-configured demo repo

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function apiCall<T>(endpoint: string, data?: object): Promise<T> {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
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
    details?: object
}

interface Message {
    id: string
    type: 'user' | 'agent'
    content: string
    timestamp: Date
    agentType?: string
    activities?: AgentActivity[]
}

interface ApprovalRequest {
    id: string
    title: string
    description: string
    actions: string[]
    status: 'pending' | 'approved' | 'rejected'
}

type View = 'dashboard' | 'workflow' | 'security' | 'incident' | 'chat'

// Natural language formatter
function formatAgentResponse(result: object, action: string): string {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const r = result as any

    if (!r.success) {
        return `❌ I encountered an error: ${r.error || 'Unknown error'}`
    }

    switch (action) {
        case 'analyze':
            const analysis = r.analysis || r
            return `✅ **Repository Analysis Complete**

📦 **Repository**: ${analysis.repository || r.repository}
🔧 **Tech Stack**: ${(analysis.tech_stack || []).join(', ') || 'Not detected'}
📋 **Package Manager**: ${analysis.package_manager || 'Unknown'}
🌐 **Primary Language**: ${analysis.primary_language || 'Unknown'}

**CI/CD Status**:
${analysis.has_github_actions ? '✅ GitHub Actions configured' : '⚠️ No CI/CD workflows found'}
${analysis.existing_workflows?.length > 0 ? `📁 Found ${analysis.existing_workflows.length} existing workflows` : ''}

**Dependencies**: ${(analysis.dependencies || []).slice(0, 10).join(', ')}${(analysis.dependencies || []).length > 10 ? ` and ${analysis.dependencies.length - 10} more...` : ''}

**Recommendations**:
${(analysis.recommendations || []).map((rec: string) => `• ${rec}`).join('\n') || '• No specific recommendations'}

*Would you like me to generate a BCG-compliant CI/CD workflow for this repository?*`

        case 'generate':
            return `✅ **CI/CD Workflow Generated**

I've created a BCG-compliant workflow with the following integrations:
• ⚙️ **Build & Test**: Automated testing pipeline
• 🔒 **SonarQube**: Code quality and security analysis
• 📦 **JFrog Artifactory**: Artifact management
• 🛡️ **Prisma Cloud**: Container security scanning
• 🚀 **ArgoCD**: GitOps deployment
• 📊 **Datadog**: Monitoring and observability

\`\`\`yaml
${r.workflow ? r.workflow.substring(0, 500) + '...' : 'Workflow generated successfully'}
\`\`\`

*Would you like me to create a PR with this workflow?*`

        case 'triage':
            const severity = r.severity?.toUpperCase() || 'UNKNOWN'
            const severityEmoji = {
                'CRITICAL': '🔴',
                'HIGH': '🟠',
                'MEDIUM': '🟡',
                'LOW': '🟢'
            }[severity] || '⚪'

            return `${severityEmoji} **Incident Triaged**

**ID**: ${r.incident_id}
**Severity**: ${severity}
**Category**: ${r.category || 'Unknown'}

**Recommended Runbook**:
${r.runbook || 'Manual investigation required'}

${r.requires_immediate_action ? '⚠️ **IMMEDIATE ACTION REQUIRED**\n\nThis is a high-priority incident. I recommend:' : 'Suggested next steps:'}
• Check recent deployments for changes
• Review application logs
• Monitor system metrics

*Would you like me to generate an RCA report or execute a runbook?*`

        case 'scan':
            const findings = r.findings || {}
            const summary = findings.summary || {}

            return `🔒 **Security Scan Complete**

**Summary**:
• 🔴 Critical: ${summary.critical || 0}
• 🟠 High: ${summary.high || 0}
• 🟡 Medium: ${summary.medium || 0}
• 🟢 Low: ${summary.low || 0}

${(findings.dependency_vulnerabilities || []).length > 0 ? `**Vulnerabilities Found**:
${findings.dependency_vulnerabilities.slice(0, 5).map((v: any) => `• **${v.package}** - ${v.cve || 'Security issue'} (${v.severity})\n  Recommendation: ${v.recommendation}`).join('\n')}` : '✅ No dependency vulnerabilities detected!'}

${(findings.secret_leaks || []).length > 0 ? `\n**⚠️ Secret Leaks Detected**:
${findings.secret_leaks.map((s: any) => `• ${s.file}: ${s.issue}`).join('\n')}` : ''}

*Would you like me to create a PR to fix these issues automatically?*`

        case 'report':
            return `📊 **Security Report Generated**

${r.report ? r.report.substring(0, 1500) : 'Report generated successfully'}

*Would you like me to export this report or create fix PRs?*`

        case 'rca':
            return `📋 **Root Cause Analysis Report**

${r.rca_report || 'RCA report generated successfully'}

*Would you like me to create action items from this RCA?*`

        default:
            return `✅ **Action Completed**

${JSON.stringify(result, null, 2)}`
    }
}

function App() {
    const [activeView, setActiveView] = useState<View>('chat')
    const [loading, setLoading] = useState(false)
    const [messages, setMessages] = useState<Message[]>([])
    const [activities, setActivities] = useState<AgentActivity[]>([])
    const [approvals, setApprovals] = useState<ApprovalRequest[]>([])
    const [chatInput, setChatInput] = useState('')
    const [repo, setRepo] = useState(GITHUB_REPO)
    const messagesEndRef = useRef<HTMLDivElement>(null)

    // Auto-scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Add activity
    const addActivity = useCallback((agent: string, action: string, status: AgentActivity['status'], message: string) => {
        const activity: AgentActivity = {
            id: Date.now().toString(),
            agent,
            action,
            status,
            message,
            timestamp: new Date()
        }
        setActivities(prev => [activity, ...prev].slice(0, 20))
        return activity
    }, [])

    // Update activity
    const updateActivity = useCallback((id: string, updates: Partial<AgentActivity>) => {
        setActivities(prev => prev.map(a => a.id === id ? { ...a, ...updates } : a))
    }, [])

    // Process natural language command
    const processCommand = useCallback(async (input: string) => {
        const lowerInput = input.toLowerCase()

        // Detect intent
        if (lowerInput.includes('analyze') || lowerInput.includes('check') || lowerInput.includes('what is')) {
            return { action: 'analyze', endpoint: '/workflow/analyze' }
        } else if (lowerInput.includes('generate') || lowerInput.includes('create workflow') || lowerInput.includes('setup ci')) {
            return { action: 'generate', endpoint: '/workflow/generate' }
        } else if (lowerInput.includes('security') || lowerInput.includes('scan') || lowerInput.includes('vulnerab')) {
            return { action: 'scan', endpoint: '/security/scan' }
        } else if (lowerInput.includes('report')) {
            return { action: 'report', endpoint: '/security/report' }
        } else if (lowerInput.includes('triage') || lowerInput.includes('alert') || lowerInput.includes('incident') || lowerInput.includes('cpu') || lowerInput.includes('error')) {
            return { action: 'triage', endpoint: '/incident/triage' }
        } else if (lowerInput.includes('rca') || lowerInput.includes('root cause')) {
            return { action: 'rca', endpoint: '/incident/rca' }
        } else if (lowerInput.includes('fix') || lowerInput.includes('remediate')) {
            return { action: 'fix', endpoint: '/security/fix' }
        }

        // Default to chat analysis
        return { action: 'analyze', endpoint: '/chat' }
    }, [])

    // Send message
    const sendMessage = useCallback(async () => {
        if (!chatInput.trim()) return

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

        // Add activity
        const activityId = addActivity('Supervisor', 'Analyzing request', 'running', 'Processing your request...')

        try {
            const { action, endpoint } = await processCommand(inputText)

            // Prepare data based on action
            let data: object = {}

            if (action === 'triage') {
                data = {
                    title: inputText,
                    details: inputText,
                    source: 'user',
                    service: 'unknown'
                }
            } else if (endpoint === '/chat') {
                data = { message: inputText, repository: repo }
            } else {
                data = { repository: repo }
            }

            updateActivity(activityId, { message: `Executing ${action}...`, status: 'running' })
            addActivity(action === 'triage' ? 'Incident Agent' : action === 'scan' ? 'Security Agent' : 'Workflow Agent', action, 'running', `Processing ${action}...`)

            const result = await apiCall<object>(endpoint, data)

            updateActivity(activityId, { status: 'completed', message: 'Request completed' })

            const response = formatAgentResponse(result, action)

            const agentMsg: Message = {
                id: (Date.now() + 1).toString(),
                type: 'agent',
                content: response,
                timestamp: new Date(),
                agentType: action === 'triage' ? 'Incident Agent' : action.includes('scan') || action.includes('security') ? 'Security Agent' : 'Workflow Agent'
            }
            setMessages(prev => [...prev, agentMsg])

            addActivity(agentMsg.agentType!, action, 'completed', `${action} completed successfully`)

            // Check for approval requests
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const r = result as any
            if (r.requires_approval || action === 'generate' || action === 'fix') {
                setApprovals(prev => [...prev, {
                    id: Date.now().toString(),
                    title: `Approve ${action}?`,
                    description: `The agent wants to ${action === 'generate' ? 'create a PR with the generated workflow' : action === 'fix' ? 'create a PR with security fixes' : 'perform this action'}`,
                    actions: ['Approve', 'Reject'],
                    status: 'pending'
                }])
            }

        } catch (e) {
            updateActivity(activityId, { status: 'failed', message: `Error: ${String(e)}` })

            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                type: 'agent',
                content: `❌ I encountered an error while processing your request. Please try again or be more specific.\n\nError: ${String(e)}`,
                timestamp: new Date(),
                agentType: 'System'
            }
            setMessages(prev => [...prev, errorMsg])
        } finally {
            setLoading(false)
        }
    }, [chatInput, repo, addActivity, updateActivity, processCommand])

    // Handle approval
    const handleApproval = useCallback((id: string, approved: boolean) => {
        setApprovals(prev => prev.map(a =>
            a.id === id ? { ...a, status: approved ? 'approved' : 'rejected' } : a
        ))

        if (approved) {
            const agentMsg: Message = {
                id: Date.now().toString(),
                type: 'agent',
                content: '✅ **Approved!** I will proceed with the requested action. Creating PR...\n\n*This action has been logged and will be tracked.*',
                timestamp: new Date(),
                agentType: 'Supervisor'
            }
            setMessages(prev => [...prev, agentMsg])
            addActivity('Supervisor', 'Approval', 'completed', 'Action approved by user')
        }
    }, [addActivity])

    // Quick actions
    const quickActions = [
        { label: '🔍 Analyze Repository', action: 'Analyze the repository and tell me about its tech stack' },
        { label: '⚡ Generate CI/CD', action: 'Generate a BCG-compliant CI/CD workflow for this repository' },
        { label: '🔒 Security Scan', action: 'Scan this repository for security vulnerabilities' },
        { label: '🚨 Triage Alert', action: 'There is a high CPU alert on the production server' },
    ]

    return (
        <div className="app-container">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="logo">
                    <div className="logo-icon">🤖</div>
                    <h2>
                        BCG DevOps
                        <span>Agentic Platform</span>
                    </h2>
                </div>

                {/* Repository Context */}
                <div style={{ marginBottom: '1.5rem' }}>
                    <div className="nav-title">Repository Context</div>
                    <input
                        type="text"
                        value={repo}
                        onChange={(e) => setRepo(e.target.value)}
                        placeholder="owner/repo"
                        style={{ marginBottom: 0, fontSize: '0.8rem' }}
                    />
                    <div className="badge success" style={{ marginTop: '0.5rem' }}>Connected</div>
                </div>

                <nav className="nav-section">
                    <div className="nav-title">Navigation</div>
                    <div
                        className={`nav-item ${activeView === 'chat' ? 'active' : ''}`}
                        onClick={() => setActiveView('chat')}
                    >
                        <span className="nav-icon">💬</span>
                        Agentic Chat
                    </div>
                    <div
                        className={`nav-item ${activeView === 'dashboard' ? 'active' : ''}`}
                        onClick={() => setActiveView('dashboard')}
                    >
                        <span className="nav-icon">📊</span>
                        Dashboard
                    </div>
                </nav>

                {/* Agent Activity */}
                <div className="nav-section">
                    <div className="nav-title">Agent Activity</div>
                    <div className="agent-activity">
                        {activities.slice(0, 5).map(activity => (
                            <div className="activity-item" key={activity.id}>
                                <div className={`activity-dot ${activity.status}`}></div>
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: '0.75rem', fontWeight: 500 }}>{activity.agent}</div>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{activity.message}</div>
                                </div>
                            </div>
                        ))}
                        {activities.length === 0 && (
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', padding: '0.5rem' }}>
                                No recent activity
                            </div>
                        )}
                    </div>
                </div>

                {/* BCG Integrations */}
                <div style={{ marginTop: 'auto' }}>
                    <div className="nav-title">BCG Integrations</div>
                    <div className="badge success">GitHub ✓</div>
                    <div className="badge success">JFrog ✓</div>
                    <div className="badge success">SonarQube ✓</div>
                    <div className="badge success">Prisma ✓</div>
                    <div className="badge success">ArgoCD ✓</div>
                    <div className="badge success">Datadog ✓</div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <header className="header">
                    <h1>🤖 BCG Agentic DevOps</h1>
                    <p>Talk to me in natural language - I'll analyze, generate workflows, scan for security issues, and triage incidents</p>
                </header>

                {/* Approval Requests */}
                {approvals.filter(a => a.status === 'pending').length > 0 && (
                    <div style={{ padding: '1rem 2rem', background: 'rgba(99, 102, 241, 0.1)', borderBottom: '1px solid var(--border)' }}>
                        {approvals.filter(a => a.status === 'pending').map(approval => (
                            <div key={approval.id} style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontWeight: 600 }}>🔔 {approval.title}</div>
                                    <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{approval.description}</div>
                                </div>
                                <button className="btn btn-primary" onClick={() => handleApproval(approval.id, true)}>
                                    ✅ Approve
                                </button>
                                <button className="btn btn-secondary" onClick={() => handleApproval(approval.id, false)}>
                                    ❌ Reject
                                </button>
                            </div>
                        ))}
                    </div>
                )}

                {/* Chat View */}
                {activeView === 'chat' && (
                    <div className="chat-container" style={{ height: 'calc(100vh - 180px)', display: 'flex', flexDirection: 'column' }}>
                        <div className="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem' }}>
                            {messages.length === 0 && (
                                <div style={{ textAlign: 'center', padding: '2rem' }}>
                                    <div style={{ fontSize: '4rem', marginBottom: '1rem' }}>🤖</div>
                                    <h3>Hi! I'm your Agentic DevOps Assistant</h3>
                                    <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem', maxWidth: '500px', margin: '0.5rem auto' }}>
                                        I can analyze repositories, generate CI/CD workflows, scan for security vulnerabilities,
                                        and help triage incidents. Just tell me what you need in natural language!
                                    </p>
                                    <div style={{ marginTop: '2rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center' }}>
                                        {quickActions.map((qa, i) => (
                                            <button
                                                key={i}
                                                className="btn btn-secondary"
                                                onClick={() => { setChatInput(qa.action); }}
                                                style={{ fontSize: '0.8rem' }}
                                            >
                                                {qa.label}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {messages.map(msg => (
                                <div className="message" key={msg.id}>
                                    <div className={`message-avatar ${msg.type}`}>
                                        {msg.type === 'user' ? '👤' : '🤖'}
                                    </div>
                                    <div className="message-content">
                                        <div className="message-header">
                                            <span className="message-name">
                                                {msg.type === 'user' ? 'You' : msg.agentType || 'Agent'}
                                            </span>
                                            <span className="message-time">
                                                {msg.timestamp.toLocaleTimeString()}
                                            </span>
                                        </div>
                                        <div
                                            className="message-text"
                                            style={{ whiteSpace: 'pre-wrap' }}
                                            dangerouslySetInnerHTML={{
                                                __html: msg.content
                                                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                                                    .replace(/`([^`]+)`/g, '<code style="background: var(--bg-secondary); padding: 0.1rem 0.3rem; border-radius: 4px;">$1</code>')
                                                    .replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre style="background: var(--bg-secondary); padding: 1rem; border-radius: 8px; overflow-x: auto; margin: 0.5rem 0;"><code>$2</code></pre>')
                                            }}
                                        />
                                    </div>
                                </div>
                            ))}

                            {loading && (
                                <div className="message">
                                    <div className="message-avatar agent">🤖</div>
                                    <div className="message-content">
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <div className="loading"></div>
                                            <span style={{ color: 'var(--text-muted)' }}>Thinking...</span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div ref={messagesEndRef} />
                        </div>

                        <div className="chat-input-area" style={{ borderTop: '1px solid var(--border)', padding: '1.5rem' }}>
                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                <input
                                    type="text"
                                    placeholder="Ask me anything about DevOps... (e.g., 'Analyze this repository' or 'Generate CI/CD workflow')"
                                    value={chatInput}
                                    onChange={(e) => setChatInput(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                                    style={{ marginBottom: 0 }}
                                />
                                <button
                                    className="btn btn-primary"
                                    onClick={sendMessage}
                                    disabled={loading || !chatInput.trim()}
                                    style={{ minWidth: '120px' }}
                                >
                                    {loading ? <div className="loading"></div> : '🚀 Send'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Dashboard View */}
                {activeView === 'dashboard' && (
                    <div className="content">
                        <div className="grid grid-2">
                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon workflow">⚡</div>
                                    <div>
                                        <h3>Workflow Generator</h3>
                                        <p>BCG-compliant CI/CD pipelines</p>
                                    </div>
                                </div>
                                <button
                                    className="btn btn-primary btn-full"
                                    onClick={() => {
                                        setActiveView('chat')
                                        setChatInput('Generate a CI/CD workflow for this repository')
                                    }}
                                >
                                    Generate Workflow
                                </button>
                            </div>

                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon security">🔒</div>
                                    <div>
                                        <h3>Security Agent</h3>
                                        <p>Vulnerability scanning & fixes</p>
                                    </div>
                                </div>
                                <button
                                    className="btn btn-primary btn-full"
                                    onClick={() => {
                                        setActiveView('chat')
                                        setChatInput('Scan this repository for security vulnerabilities')
                                    }}
                                >
                                    Run Security Scan
                                </button>
                            </div>

                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon incident">🚨</div>
                                    <div>
                                        <h3>Incident Agent</h3>
                                        <p>L1 triage & RCA</p>
                                    </div>
                                </div>
                                <button
                                    className="btn btn-primary btn-full"
                                    onClick={() => {
                                        setActiveView('chat')
                                        setChatInput('There is a high CPU alert on production server')
                                    }}
                                >
                                    Triage Alert
                                </button>
                            </div>

                            <div className="card">
                                <div className="card-header">
                                    <div className="card-icon chat">📊</div>
                                    <div>
                                        <h3>Repository Analysis</h3>
                                        <p>Tech stack detection</p>
                                    </div>
                                </div>
                                <button
                                    className="btn btn-primary btn-full"
                                    onClick={() => {
                                        setActiveView('chat')
                                        setChatInput('Analyze this repository and tell me about its tech stack')
                                    }}
                                >
                                    Analyze Repo
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* Status Bar */}
                <div className="status-bar">
                    <div className="status-item">
                        <div className="status-dot"></div>
                        <span>Platform Active</span>
                    </div>
                    <div className="status-item">
                        <span>🧠 AWS Bedrock Nova Pro</span>
                    </div>
                    <div className="status-item">
                        <span>📍 us-east-1</span>
                    </div>
                    <div className="status-item">
                        <span>🔧 {activities.filter(a => a.status === 'running').length} agents working</span>
                    </div>
                </div>
            </main>
        </div>
    )
}

export default App
