# BCG DevOps Security Policies
# These policies are enforced by the Security Agent

## Workflow Security Requirements

### 1. Authentication & Secrets
- All credentials MUST use GitHub Secrets
- No hardcoded passwords, API keys, or tokens
- Use OIDC for AWS authentication when possible
- Rotate secrets regularly

### 2. Action Versions
- Always pin actions to specific versions (e.g., @v4)
- Never use @master or @main
- Prefer SHA-pinned versions for critical actions

### 3. Permissions
- Use least privilege principle
- Avoid write-all permissions
- Explicitly define required permissions per job

### 4. Security Scanning
- All workflows must include security scanning
- Use Trivy for container and filesystem scanning
- Use SonarQube for code quality
- Use language-specific security tools (Bandit, Gosec, npm audit)

### 5. Deployment
- Production deployments require manual approval
- Use GitHub Environments with protection rules
- Implement rollback mechanisms
- Enable deployment notifications

## Required Checks

### Pre-merge
- [ ] All tests pass
- [ ] Code coverage >= 80%
- [ ] Security scan passes (no HIGH/CRITICAL)
- [ ] SonarQube quality gate passes
- [ ] Peer review approved

### Pre-deploy (Production)
- [ ] All pre-merge checks pass
- [ ] Security team approval (for sensitive changes)
- [ ] Change ticket linked
- [ ] Rollback plan documented

## Forbidden Patterns

1. `password:` with inline values
2. `api_key:` with inline values
3. `uses: action@master`
4. `permissions: write-all`
5. Unencrypted secrets in logs
6. `pull_request_target` with checkout

## Approved Tools

| Category | Tool | Version |
|----------|------|---------|
| Code Quality | SonarQube | Latest |
| Security Scan | Trivy | Latest |
| Container Registry | JFrog / ECR | - |
| Deployment | ArgoCD | 2.x |
| Monitoring | Datadog | Latest |
| Notifications | Slack | - |
