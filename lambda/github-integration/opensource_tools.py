"""
Open Source DevOps Tools Configuration
Complete CI/CD workflow templates using 100% open-source and free tools
"""

from typing import Dict, List

# =============================================================================
# OPEN SOURCE DEVOPS TOOLS
# Comprehensive workflow templates for open-source DevOps toolchain
# =============================================================================

OPENSOURCE_DEVOPS_TOOLS = {
    # =========================================================================
    # TESTING FRAMEWORKS
    # =========================================================================
    
    "testing_nodejs": {
        "name": "Node.js Testing (Jest/Vitest/Mocha)",
        "description": "Comprehensive testing for Node.js applications with coverage",
        "category": "testing",
        "languages": ["javascript", "typescript"],
        "secrets_required": [],
        "workflow_snippet": """
  # Testing - Node.js
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install Dependencies
        run: npm ci
      
      - name: Run Unit Tests
        run: npm test -- --coverage --watchAll=false
      
      - name: Upload Coverage Report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage/
          retention-days: 7
      
      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: false
""",
        "unit_test_snippet": """
      - name: Run Unit Tests
        run: npm test -- --coverage --watchAll=false
""",
        "e2e_test_snippet": """
      - name: Run E2E Tests
        run: npm run test:e2e
        env:
          CI: true
""",
        "integration_test_snippet": """
      - name: Run Integration Tests
        run: npm run test:integration
        env:
          CI: true
"""
    },
    
    "testing_python": {
        "name": "Python Testing (Pytest)",
        "description": "Comprehensive testing for Python applications with coverage",
        "category": "testing",
        "languages": ["python"],
        "secrets_required": [],
        "workflow_snippet": """
  # Testing - Python
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      
      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run Tests with Coverage
        run: |
          pytest --cov=. --cov-report=xml --cov-report=html -v
      
      - name: Upload Coverage Report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/
          retention-days: 7
      
      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false
"""
    },
    
    "testing_go": {
        "name": "Go Testing",
        "description": "Comprehensive testing for Go applications",
        "category": "testing",
        "languages": ["go"],
        "secrets_required": [],
        "workflow_snippet": """
  # Testing - Go
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
          cache: true
      
      - name: Run Tests
        run: go test -v -race -coverprofile=coverage.out ./...
      
      - name: Upload Coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.out
          fail_ci_if_error: false
"""
    },
    
    "testing_java": {
        "name": "Java Testing (JUnit/Maven/Gradle)",
        "description": "Comprehensive testing for Java applications",
        "category": "testing",
        "languages": ["java"],
        "secrets_required": [],
        "workflow_snippet": """
  # Testing - Java
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Java
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          cache: 'maven'
      
      - name: Run Tests with Maven
        run: mvn test -B
      
      - name: Upload Test Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: test-results
          path: target/surefire-reports/
"""
    },
    
    # =========================================================================
    # LINTING & CODE QUALITY
    # =========================================================================
    
    "linting_nodejs": {
        "name": "Node.js Linting (ESLint + Prettier)",
        "description": "Code quality and formatting for JavaScript/TypeScript",
        "category": "linting",
        "languages": ["javascript", "typescript"],
        "secrets_required": [],
        "workflow_snippet": """
  # Linting - Node.js
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install Dependencies
        run: npm ci
      
      - name: Run ESLint
        run: npm run lint || npx eslint . --ext .js,.jsx,.ts,.tsx --max-warnings 0
      
      - name: Check Prettier Formatting
        run: npm run format:check || npx prettier --check "**/*.{js,jsx,ts,tsx,json,md}"
      
      - name: TypeScript Type Check
        if: hashFiles('tsconfig.json') != ''
        run: npm run type-check || npx tsc --noEmit
""",
        "eslint_snippet": """
      - name: Run ESLint
        run: npx eslint . --ext .js,.jsx,.ts,.tsx --format stylish --max-warnings 0
""",
        "prettier_snippet": """
      - name: Check Prettier Formatting
        run: npx prettier --check "**/*.{js,jsx,ts,tsx,json,css,scss,md}"
""",
        "typescript_snippet": """
      - name: TypeScript Type Check
        run: npx tsc --noEmit
"""
    },
    
    "linting_python": {
        "name": "Python Linting (Ruff + Black + MyPy)",
        "description": "Code quality and formatting for Python",
        "category": "linting",
        "languages": ["python"],
        "secrets_required": [],
        "workflow_snippet": """
  # Linting - Python
  lint:
    name: Lint & Format Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Linting Tools
        run: pip install ruff black mypy
      
      - name: Run Ruff Linter
        run: ruff check .
      
      - name: Check Black Formatting
        run: black --check .
      
      - name: Run MyPy Type Check
        run: mypy . --ignore-missing-imports || true
""",
        "ruff_snippet": """
      - name: Run Ruff Linter
        run: |
          pip install ruff
          ruff check . --output-format=github
""",
        "black_snippet": """
      - name: Check Black Formatting
        run: |
          pip install black
          black --check --diff .
"""
    },
    
    "linting_go": {
        "name": "Go Linting (golangci-lint)",
        "description": "Code quality for Go applications",
        "category": "linting",
        "languages": ["go"],
        "secrets_required": [],
        "workflow_snippet": """
  # Linting - Go
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
          cache: true
      
      - name: Run golangci-lint
        uses: golangci/golangci-lint-action@v4
        with:
          version: latest
          args: --timeout=5m
"""
    },
    
    # =========================================================================
    # SECURITY SCANNING (ALL FREE/OPEN SOURCE)
    # =========================================================================
    
    "security_trivy": {
        "name": "Trivy Security Scanner",
        "description": "Comprehensive vulnerability scanner for containers, filesystems, and IaC",
        "category": "security",
        "secrets_required": [],
        "workflow_snippet": """
  # Security - Trivy Vulnerability Scanning
  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy Filesystem Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-fs-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy FS Results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-fs-results.sarif'
""",
        "container_scan_snippet": """
      - name: Build Docker Image for Scanning
        run: docker build -t ${{ github.repository }}:${{ github.sha }} .
      
      - name: Run Trivy Container Scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ github.repository }}:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-container-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
      
      - name: Upload Trivy Container Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-container-results.sarif'
""",
        "iac_scan_snippet": """
      - name: Run Trivy IaC Scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'config'
          scan-ref: '.'
          format: 'sarif'
          output: 'trivy-iac-results.sarif'
          severity: 'CRITICAL,HIGH,MEDIUM'
"""
    },
    
    "security_codeql": {
        "name": "GitHub CodeQL Analysis",
        "description": "Free semantic code analysis for security vulnerabilities",
        "category": "security",
        "secrets_required": [],
        "workflow_snippet": """
  # Security - CodeQL Analysis
  codeql-analysis:
    name: CodeQL Analysis
    runs-on: ubuntu-latest
    permissions:
      security-events: write
      actions: read
      contents: read
    strategy:
      fail-fast: false
      matrix:
        language: ['javascript', 'python']  # Add languages as needed
    steps:
      - uses: actions/checkout@v4
      
      - name: Initialize CodeQL
        uses: github/codeql-action/init@v3
        with:
          languages: ${{ matrix.language }}
          queries: +security-extended
      
      - name: Autobuild
        uses: github/codeql-action/autobuild@v3
      
      - name: Perform CodeQL Analysis
        uses: github/codeql-action/analyze@v3
        with:
          category: "/language:${{ matrix.language }}"
"""
    },
    
    "security_dependency_check": {
        "name": "Dependency Vulnerability Check",
        "description": "Check dependencies for known vulnerabilities (npm audit, pip-audit, etc.)",
        "category": "security",
        "secrets_required": [],
        "workflow_snippet": """
  # Security - Dependency Vulnerability Check
  dependency-check:
    name: Dependency Security Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        if: hashFiles('package.json') != ''
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: NPM Audit
        if: hashFiles('package.json') != ''
        run: npm audit --audit-level=high || true
        continue-on-error: true
      
      - name: Setup Python
        if: hashFiles('requirements.txt') != ''
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Pip Audit
        if: hashFiles('requirements.txt') != ''
        run: |
          pip install pip-audit
          pip-audit -r requirements.txt || true
        continue-on-error: true
""",
        "npm_audit_snippet": """
      - name: NPM Security Audit
        run: |
          npm audit --audit-level=high
          npm audit fix --dry-run
""",
        "snyk_free_snippet": """
      - name: Snyk Security Scan (Free Tier)
        uses: snyk/actions/node@master
        continue-on-error: true
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high
"""
    },
    
    "security_gitleaks": {
        "name": "Gitleaks Secret Detection",
        "description": "Detect hardcoded secrets and credentials in code",
        "category": "security",
        "secrets_required": [],
        "workflow_snippet": """
  # Security - Secret Detection
  secret-scan:
    name: Secret Detection
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Run Gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
"""
    },
    
    # =========================================================================
    # CONTAINER REGISTRY (FREE OPTIONS)
    # =========================================================================
    
    "registry_ghcr": {
        "name": "GitHub Container Registry (GHCR)",
        "description": "Free container registry integrated with GitHub",
        "category": "registry",
        "secrets_required": [],
        "workflow_snippet": """
  # Build, Scan and Push to GitHub Container Registry
  build-scan-push:
    name: Build, Scan & Push to GHCR
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Extract Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
      
      # Step 1: Build Docker Image (local only)
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{ github.repository }}:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # Step 2: Scan Docker Image with Trivy
      - name: Scan Docker Image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ github.repository }}:scan'
          format: 'sarif'
          output: 'trivy-image-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
        continue-on-error: true
        id: trivy-scan
      
      - name: Upload Trivy Scan Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-image-results.sarif'
      
      # Step 3: Check scan results before push
      - name: Check Scan Results
        if: steps.trivy-scan.outcome == 'failure'
        run: |
          echo "::warning::Security vulnerabilities found in Docker image!"
          echo "Review the security tab for details before pushing."
          exit 1
      
      # Step 4: Login and Push (only if scan passes)
      - name: Login to GitHub Container Registry
        if: success()
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Push to GHCR
        if: success()
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
"""
    },
    
    "registry_dockerhub": {
        "name": "Docker Hub Registry",
        "description": "Push images to Docker Hub (free tier available)",
        "category": "registry",
        "secrets_required": ["DOCKERHUB_USERNAME", "DOCKERHUB_TOKEN"],
        "workflow_snippet": """
  # Build, Scan and Push to Docker Hub
  build-scan-push:
    name: Build, Scan & Push to Docker Hub
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Extract Metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ secrets.DOCKERHUB_USERNAME }}/${{ github.event.repository.name }}
          tags: |
            type=sha,prefix=
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=raw,value=latest,enable=${{ github.ref == 'refs/heads/main' }}
      
      # Step 1: Build Docker Image (local only)
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{ github.event.repository.name }}:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # Step 2: Scan Docker Image with Trivy
      - name: Scan Docker Image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ github.event.repository.name }}:scan'
          format: 'sarif'
          output: 'trivy-image-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
        continue-on-error: true
        id: trivy-scan
      
      - name: Upload Trivy Scan Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-image-results.sarif'
      
      # Step 3: Check scan results before push
      - name: Check Scan Results
        if: steps.trivy-scan.outcome == 'failure'
        run: |
          echo "::warning::Security vulnerabilities found in Docker image!"
          echo "Review the security tab for details before pushing."
          exit 1
      
      # Step 4: Login and Push (only if scan passes)
      - name: Login to Docker Hub
        if: success()
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Push to Docker Hub
        if: success()
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
"""
    },
    
    "registry_ecr": {
        "name": "Amazon ECR",
        "description": "Push Docker images to Amazon Elastic Container Registry",
        "category": "registry",
        "secrets_required": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
        "workflow_snippet": """
  # Build, Scan and Push to Amazon ECR
  build-scan-push:
    name: Build, Scan & Push to ECR
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    outputs:
      image: ${{ steps.build-push.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}
      
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      # Step 1: Build Docker Image (local only)
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{ github.event.repository.name }}:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # Step 2: Scan Docker Image with Trivy
      - name: Scan Docker Image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ github.event.repository.name }}:scan'
          format: 'sarif'
          output: 'trivy-image-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
        continue-on-error: true
        id: trivy-scan
      
      - name: Upload Trivy Scan Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-image-results.sarif'
      
      # Step 3: Check scan results before push
      - name: Check Scan Results
        if: steps.trivy-scan.outcome == 'failure'
        run: |
          echo "::warning::Security vulnerabilities found in Docker image!"
          echo "Review the security tab for details before pushing."
          exit 1
      
      # Step 4: Push to ECR (only if scan passes)
      - name: Push to ECR
        id: build-push
        if: success()
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ steps.login-ecr.outputs.registry }}/${{ github.event.repository.name }}:${{ github.sha }}
            ${{ steps.login-ecr.outputs.registry }}/${{ github.event.repository.name }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Output Image URI
        if: success()
        run: echo "image=${{ steps.login-ecr.outputs.registry }}/${{ github.event.repository.name }}:${{ github.sha }}" >> $GITHUB_OUTPUT
"""
    },
    
    # =========================================================================
    # DEPLOYMENT (OPEN SOURCE + CLOUD OPTIONS)
    # =========================================================================
    
    "deploy_argocd": {
        "name": "ArgoCD GitOps Deployment",
        "description": "Declarative GitOps continuous delivery for Kubernetes (Open Source)",
        "category": "deployment",
        "secrets_required": ["ARGOCD_SERVER", "ARGOCD_AUTH_TOKEN"],
        "workflow_snippet": """
  # ArgoCD - GitOps Deployment
  deploy:
    name: Deploy via ArgoCD
    runs-on: ubuntu-latest
    needs: [build-and-push, security-scan]
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Install ArgoCD CLI
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          sudo mv argocd /usr/local/bin/
      
      - name: Login to ArgoCD
        run: |
          argocd login ${{ secrets.ARGOCD_SERVER }} \
            --auth-token ${{ secrets.ARGOCD_AUTH_TOKEN }} \
            --grpc-web
      
      - name: Update Application Image
        run: |
          argocd app set ${{ github.event.repository.name }} \
            --parameter image.tag=${{ github.sha }}
      
      - name: Sync Application
        run: |
          argocd app sync ${{ github.event.repository.name }} --prune --timeout 300
          argocd app wait ${{ github.event.repository.name }} --health --timeout 300
"""
    },
    
    "deploy_kubernetes": {
        "name": "Kubernetes Direct Deployment",
        "description": "Deploy directly to Kubernetes cluster using kubectl",
        "category": "deployment",
        "secrets_required": ["KUBE_CONFIG"],
        "workflow_snippet": """
  # Kubernetes Direct Deployment
  deploy:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    needs: [build-and-push, security-scan]
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup kubectl
        uses: azure/setup-kubectl@v3
        with:
          version: 'latest'
      
      - name: Configure kubectl
        run: |
          mkdir -p $HOME/.kube
          echo "${{ secrets.KUBE_CONFIG }}" | base64 -d > $HOME/.kube/config
          chmod 600 $HOME/.kube/config
      
      - name: Update Deployment Image
        run: |
          kubectl set image deployment/${{ github.event.repository.name }} \
            ${{ github.event.repository.name }}=${{ needs.build-and-push.outputs.image }} \
            -n ${{ vars.K8S_NAMESPACE || 'default' }}
      
      - name: Wait for Rollout
        run: |
          kubectl rollout status deployment/${{ github.event.repository.name }} \
            -n ${{ vars.K8S_NAMESPACE || 'default' }} \
            --timeout=300s
      
      - name: Verify Deployment
        run: |
          kubectl get pods -l app=${{ github.event.repository.name }} \
            -n ${{ vars.K8S_NAMESPACE || 'default' }}
"""
    },
    
    "deploy_eks": {
        "name": "Amazon EKS Deployment",
        "description": "Deploy to Amazon Elastic Kubernetes Service",
        "category": "deployment",
        "secrets_required": ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "EKS_CLUSTER_NAME"],
        "workflow_snippet": """
  # Amazon EKS Deployment
  deploy:
    name: Deploy to EKS
    runs-on: ubuntu-latest
    needs: [build-and-push, security-scan]
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}
      
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \
            --region ${{ vars.AWS_REGION || 'us-east-1' }} \
            --name ${{ secrets.EKS_CLUSTER_NAME }}
      
      - name: Deploy to EKS
        run: |
          kubectl set image deployment/${{ github.event.repository.name }} \
            ${{ github.event.repository.name }}=${{ needs.build-and-push.outputs.image }} \
            -n ${{ vars.K8S_NAMESPACE || 'default' }}
          
          kubectl rollout status deployment/${{ github.event.repository.name }} \
            -n ${{ vars.K8S_NAMESPACE || 'default' }} \
            --timeout=300s
"""
    },
    
    # =========================================================================
    # BCG ENTERPRISE TOOLS
    # JFrog Artifactory, Prisma Cloud, Datadog - Specific BCG Requirements
    # =========================================================================
    
    "registry_jfrog": {
        "name": "JFrog Artifactory",
        "description": "Enterprise artifact repository for Docker images, npm, Maven, PyPI packages",
        "category": "registry",
        "secrets_required": ["JFROG_URL", "JFROG_USERNAME", "JFROG_PASSWORD"],
        "workflow_snippet": """
  # Build, Scan and Push to JFrog Artifactory
  build-scan-push:
    name: Build, Scan & Push to JFrog Artifactory
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    outputs:
      image: ${{ steps.build-push.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      # Step 1: Build Docker Image (local only)
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{ github.event.repository.name }}:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # Step 2: Scan Docker Image with Trivy
      - name: Scan Docker Image with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ github.event.repository.name }}:scan'
          format: 'sarif'
          output: 'trivy-image-results.sarif'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
        continue-on-error: true
        id: trivy-scan
      
      - name: Upload Trivy Scan Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-image-results.sarif'
      
      # Step 3: Check scan results before push
      - name: Check Scan Results
        if: steps.trivy-scan.outcome == 'failure'
        run: |
          echo "::warning::Security vulnerabilities found in Docker image!"
          echo "Review the security tab for details before pushing."
          exit 1
      
      # Step 4: Login and Push to JFrog Artifactory (only if scan passes)
      - name: Login to JFrog Artifactory
        if: success()
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.JFROG_URL }}
          username: ${{ secrets.JFROG_USERNAME }}
          password: ${{ secrets.JFROG_PASSWORD }}
      
      - name: Push to JFrog Artifactory
        id: build-push
        if: success()
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }}:${{ github.sha }}
            ${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }}:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Output Image URI
        if: success()
        run: echo "image=${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }}:${{ github.sha }}" >> $GITHUB_OUTPUT
""",
        "npm_publish_snippet": """
      # NPM Package Publishing to JFrog Artifactory
      - name: Setup Node.js with JFrog NPM Registry
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          registry-url: 'https://${{ secrets.JFROG_URL }}/artifactory/api/npm/${{ vars.NPM_REPO || 'npm-local' }}/'
      
      - name: Configure JFrog NPM Authentication
        run: |
          npm config set //${{ secrets.JFROG_URL }}/artifactory/api/npm/${{ vars.NPM_REPO || 'npm-local' }}/:_authToken=${{ secrets.JFROG_NPM_TOKEN }}
      
      - name: Publish to JFrog Artifactory
        run: npm publish
        env:
          NODE_AUTH_TOKEN: ${{ secrets.JFROG_NPM_TOKEN }}
""",
        "maven_publish_snippet": """
      # Maven Package Publishing to JFrog Artifactory
      - name: Setup Java with JFrog Maven Settings
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '17'
          server-id: jfrog-artifactory
          server-username: ${{ secrets.JFROG_USERNAME }}
          server-password: ${{ secrets.JFROG_PASSWORD }}
      
      - name: Deploy to JFrog Artifactory
        run: |
          mvn deploy -B \
            -DaltDeploymentRepository=jfrog-artifactory::default::https://${{ secrets.JFROG_URL }}/artifactory/${{ vars.MAVEN_REPO || 'libs-release-local' }}
""",
        "python_publish_snippet": """
      # Python Package Publishing to JFrog Artifactory
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install Twine
        run: pip install twine build
      
      - name: Build Python Package
        run: python -m build
      
      - name: Publish to JFrog Artifactory
        run: |
          twine upload --repository-url https://${{ secrets.JFROG_URL }}/artifactory/api/pypi/${{ vars.PYPI_REPO || 'pypi-local' }} \
            -u ${{ secrets.JFROG_USERNAME }} \
            -p ${{ secrets.JFROG_PASSWORD }} \
            dist/*
""",
        "jfrog_cli_snippet": """
      # JFrog CLI Setup for Advanced Operations
      - name: Setup JFrog CLI
        uses: jfrog/setup-jfrog-cli@v4
        env:
          JF_URL: https://${{ secrets.JFROG_URL }}
          JF_USER: ${{ secrets.JFROG_USERNAME }}
          JF_PASSWORD: ${{ secrets.JFROG_PASSWORD }}
      
      - name: Configure JFrog CLI
        run: |
          jf config add --url=https://${{ secrets.JFROG_URL }} --user=${{ secrets.JFROG_USERNAME }} --password=${{ secrets.JFROG_PASSWORD }} --interactive=false
      
      - name: Run JFrog Build Scan
        run: |
          jf audit --watches bcg-security-watch
"""
    },
    
    "security_prisma": {
        "name": "Prisma Cloud Security Scanning",
        "description": "Enterprise cloud-native security platform for container and IaC scanning",
        "category": "security",
        "secrets_required": ["PRISMA_API_URL", "PRISMA_ACCESS_KEY", "PRISMA_SECRET_KEY"],
        "workflow_snippet": """
  # Prisma Cloud Security Scanning
  prisma-security-scan:
    name: Prisma Cloud Security Scan
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      # IaC Security Scanning (Terraform, CloudFormation, Kubernetes)
      - name: Prisma Cloud IaC Scan
        id: iac-scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          output_format: sarif
          output_file_path: prisma-iac-results.sarif
          soft_fail: true
          download_external_modules: true
      
      - name: Upload Prisma IaC Results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: prisma-iac-results.sarif
          category: prisma-iac
""",
        "container_scan_snippet": """
      # Prisma Cloud Container Scanning with twistcli
      - name: Build Docker Image for Scanning
        run: docker build -t ${{ github.repository }}:${{ github.sha }} .
      
      - name: Download Prisma Cloud twistcli
        run: |
          curl -k -u ${{ secrets.PRISMA_ACCESS_KEY }}:${{ secrets.PRISMA_SECRET_KEY }} \
            -o twistcli \
            "${{ secrets.PRISMA_API_URL }}/api/v1/util/twistcli"
          chmod +x twistcli
      
      - name: Scan Container Image with Prisma Cloud
        run: |
          ./twistcli images scan \
            --address ${{ secrets.PRISMA_API_URL }} \
            --user ${{ secrets.PRISMA_ACCESS_KEY }} \
            --password ${{ secrets.PRISMA_SECRET_KEY }} \
            --details \
            --output-file prisma-container-results.json \
            ${{ github.repository }}:${{ github.sha }}
      
      - name: Check Prisma Scan Results
        run: |
          if [ -f prisma-container-results.json ]; then
            cat prisma-container-results.json | jq '.results[] | select(.vulnerabilities != null) | .vulnerabilities[] | select(.severity == "critical" or .severity == "high")'
            CRITICAL_COUNT=$(cat prisma-container-results.json | jq '[.results[].vulnerabilities[]? | select(.severity == "critical")] | length')
            if [ "$CRITICAL_COUNT" -gt "0" ]; then
              echo "::error::Found $CRITICAL_COUNT critical vulnerabilities!"
              exit 1
            fi
          fi
      
      - name: Upload Prisma Container Results
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: prisma-container-scan-results
          path: prisma-container-results.json
          retention-days: 30
""",
        "runtime_protection_snippet": """
      # Prisma Cloud Runtime Protection (Defender Deployment)
      - name: Verify Prisma Defender Status
        run: |
          curl -k -s -u ${{ secrets.PRISMA_ACCESS_KEY }}:${{ secrets.PRISMA_SECRET_KEY }} \
            "${{ secrets.PRISMA_API_URL }}/api/v1/defenders" | jq '.[] | {hostname, status, version}'
""",
        "compliance_scan_snippet": """
      # Prisma Cloud Compliance Scanning
      - name: Run Compliance Scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          check: CKV_AWS_,CKV_GCP_,CKV_AZURE_  # Cloud compliance checks
          soft_fail: true
          output_format: cli
""",
        "secrets_scan_snippet": """
      # Prisma Cloud Secrets Detection
      - name: Scan for Hardcoded Secrets
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: secrets
          soft_fail: true
          output_format: sarif
          output_file_path: prisma-secrets-results.sarif
      
      - name: Upload Secrets Scan Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: prisma-secrets-results.sarif
          category: prisma-secrets
"""
    },
    
    "observability_datadog": {
        "name": "Datadog Observability",
        "description": "Enterprise observability platform for monitoring, APM, and log management",
        "category": "observability",
        "secrets_required": ["DD_API_KEY", "DD_APP_KEY"],
        "workflow_snippet": """
  # Datadog CI/CD Observability
  datadog-ci:
    name: Datadog CI Visibility
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Enable Datadog CI Visibility
      - name: Setup Datadog CI
        uses: datadog/agent-github-action@v1
        with:
          api_key: ${{ secrets.DD_API_KEY }}
          
      - name: Configure Datadog Environment
        run: |
          echo "DD_ENV=${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}" >> $GITHUB_ENV
          echo "DD_SERVICE=${{ github.event.repository.name }}" >> $GITHUB_ENV
          echo "DD_VERSION=${{ github.sha }}" >> $GITHUB_ENV
          echo "DD_GIT_REPOSITORY_URL=${{ github.server_url }}/${{ github.repository }}" >> $GITHUB_ENV
          echo "DD_GIT_COMMIT_SHA=${{ github.sha }}" >> $GITHUB_ENV
""",
        "test_visibility_snippet": """
      # Datadog Test Visibility - Node.js
      - name: Run Tests with Datadog Tracing (Node.js)
        run: |
          npm install --save-dev dd-trace
          DD_CIVISIBILITY_AGENTLESS_ENABLED=true \
          DD_API_KEY=${{ secrets.DD_API_KEY }} \
          DD_SITE=${{ vars.DD_SITE || 'datadoghq.com' }} \
          DD_ENV=${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }} \
          DD_SERVICE=${{ github.event.repository.name }} \
          NODE_OPTIONS="-r dd-trace/ci/init" \
          npm test
""",
        "test_visibility_python_snippet": """
      # Datadog Test Visibility - Python
      - name: Run Tests with Datadog Tracing (Python)
        run: |
          pip install ddtrace pytest-cov
          DD_CIVISIBILITY_AGENTLESS_ENABLED=true \
          DD_API_KEY=${{ secrets.DD_API_KEY }} \
          DD_SITE=${{ vars.DD_SITE || 'datadoghq.com' }} \
          DD_ENV=${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }} \
          DD_SERVICE=${{ github.event.repository.name }} \
          ddtrace-run pytest --cov=. --cov-report=xml -v
""",
        "deployment_tracking_snippet": """
      # Datadog Deployment Tracking
      - name: Create Datadog Deployment Event
        run: |
          curl -X POST "https://api.${{ vars.DD_SITE || 'datadoghq.com' }}/api/v1/events" \
            -H "Content-Type: application/json" \
            -H "DD-API-KEY: ${{ secrets.DD_API_KEY }}" \
            -d '{
              "title": "Deployment: ${{ github.event.repository.name }}",
              "text": "Deployed version ${{ github.sha }} to ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}",
              "priority": "normal",
              "tags": [
                "env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}",
                "service:${{ github.event.repository.name }}",
                "version:${{ github.sha }}",
                "source:github-actions"
              ],
              "alert_type": "info",
              "source_type_name": "GITHUB"
            }'
""",
        "synthetics_snippet": """
      # Datadog Synthetic Tests (Post-Deployment Validation)
      - name: Run Datadog Synthetic Tests
        uses: DataDog/synthetics-ci-github-action@v1
        with:
          api_key: ${{ secrets.DD_API_KEY }}
          app_key: ${{ secrets.DD_APP_KEY }}
          public_ids: ${{ vars.DD_SYNTHETIC_TEST_IDS }}
          variables: 'ENVIRONMENT=${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}'
""",
        "service_catalog_snippet": """
      # Datadog Service Catalog Registration
      - name: Register Service in Datadog Catalog
        run: |
          curl -X POST "https://api.${{ vars.DD_SITE || 'datadoghq.com' }}/api/v2/services/definitions" \
            -H "Content-Type: application/json" \
            -H "DD-API-KEY: ${{ secrets.DD_API_KEY }}" \
            -H "DD-APPLICATION-KEY: ${{ secrets.DD_APP_KEY }}" \
            -d '{
              "schema-version": "v2.1",
              "dd-service": "${{ github.event.repository.name }}",
              "team": "${{ vars.DD_TEAM || 'platform' }}",
              "contacts": [
                {
                  "name": "Repository",
                  "type": "url",
                  "contact": "${{ github.server_url }}/${{ github.repository }}"
                }
              ],
              "repos": [
                {
                  "name": "${{ github.repository }}",
                  "provider": "github",
                  "url": "${{ github.server_url }}/${{ github.repository }}"
                }
              ],
              "links": [
                {
                  "name": "CI/CD Pipeline",
                  "type": "runbook",
                  "url": "${{ github.server_url }}/${{ github.repository }}/actions"
                }
              ],
              "tags": [
                "env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}",
                "team:${{ vars.DD_TEAM || 'platform' }}"
              ],
              "integrations": {
                "pagerduty": {
                  "service-url": "${{ vars.PAGERDUTY_SERVICE_URL || '' }}"
                }
              }
            }'
""",
        "monitors_snippet": """
      # Datadog Monitor Creation for New Deployments
      - name: Create Datadog Error Rate Monitor
        run: |
          curl -X POST "https://api.${{ vars.DD_SITE || 'datadoghq.com' }}/api/v1/monitor" \
            -H "Content-Type: application/json" \
            -H "DD-API-KEY: ${{ secrets.DD_API_KEY }}" \
            -H "DD-APPLICATION-KEY: ${{ secrets.DD_APP_KEY }}" \
            -d '{
              "name": "[${{ github.event.repository.name }}] High Error Rate",
              "type": "metric alert",
              "query": "sum(last_5m):sum:trace.http.request.errors{service:${{ github.event.repository.name }},env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}}.as_count() / sum:trace.http.request.hits{service:${{ github.event.repository.name }},env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}}.as_count() > 0.05",
              "message": "Error rate is above 5% for ${{ github.event.repository.name }}. @slack-devops-alerts",
              "tags": [
                "service:${{ github.event.repository.name }}",
                "env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}",
                "team:${{ vars.DD_TEAM || 'platform' }}"
              ],
              "priority": 2,
              "options": {
                "thresholds": {
                  "critical": 0.05,
                  "warning": 0.02
                },
                "notify_no_data": false,
                "renotify_interval": 60
              }
            }'
"""
    },
    
    # =========================================================================
    # COMPLETE WORKFLOW TEMPLATES
    # =========================================================================
    
    "complete_nodejs": {
        "name": "Complete Node.js CI/CD",
        "description": "Full CI/CD pipeline for Node.js applications",
        "category": "complete",
        "languages": ["javascript", "typescript"],
        "secrets_required": [],
        "workflow_snippet": """
name: Node.js CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  packages: write
  security-events: write

jobs:
  # Code Quality
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run lint || npx eslint . --ext .js,.jsx,.ts,.tsx
      - run: npm run format:check || npx prettier --check "**/*.{js,jsx,ts,tsx,json,md}" || true

  # Testing
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm test -- --coverage --watchAll=false
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: false

  # Security Scanning
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
      - run: npm audit --audit-level=high || true

  # Build
  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-artifact@v4
        with:
          name: build-output
          path: dist/
          retention-days: 7
"""
    },
    
    "complete_python": {
        "name": "Complete Python CI/CD",
        "description": "Full CI/CD pipeline for Python applications",
        "category": "complete",
        "languages": ["python"],
        "secrets_required": [],
        "workflow_snippet": """
name: Python CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  security-events: write

jobs:
  # Code Quality
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: pip install ruff black mypy
      - run: ruff check .
      - run: black --check .
      - run: mypy . --ignore-missing-imports || true

  # Testing
  test:
    name: Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
      - run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      - run: pytest --cov=. --cov-report=xml -v
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: false

  # Security Scanning
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install pip-audit
      - run: pip-audit -r requirements.txt || true
      - uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          scan-ref: '.'
          severity: 'CRITICAL,HIGH'
"""
    },
    
    "complete_bcg_enterprise": {
        "name": "Complete BCG Enterprise CI/CD",
        "description": "Full enterprise CI/CD pipeline with JFrog, Prisma Cloud, Datadog, ArgoCD, and EKS",
        "category": "complete",
        "languages": ["javascript", "typescript", "python", "go", "java"],
        "secrets_required": [
            "JFROG_URL", "JFROG_USERNAME", "JFROG_PASSWORD",
            "PRISMA_API_URL", "PRISMA_ACCESS_KEY", "PRISMA_SECRET_KEY",
            "DD_API_KEY", "DD_APP_KEY",
            "ARGOCD_SERVER", "ARGOCD_AUTH_TOKEN",
            "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "EKS_CLUSTER_NAME"
        ],
        "workflow_snippet": """
name: BCG Enterprise CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  packages: write
  security-events: write

env:
  DD_ENV: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
  DD_SERVICE: ${{ github.event.repository.name }}
  DD_VERSION: ${{ github.sha }}

jobs:
  # ============================================
  # Stage 1: Code Quality & Testing
  # ============================================
  lint-and-test:
    name: Lint & Test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
      
      - name: Install Dependencies
        run: npm ci
      
      - name: Run Linting
        run: npm run lint || npx eslint . --ext .js,.jsx,.ts,.tsx
      
      - name: Run Tests with Datadog Tracing
        run: |
          npm install --save-dev dd-trace
          DD_CIVISIBILITY_AGENTLESS_ENABLED=true \\
          DD_API_KEY=${{ secrets.DD_API_KEY }} \\
          DD_SITE=${{ vars.DD_SITE || 'datadoghq.com' }} \\
          NODE_OPTIONS="-r dd-trace/ci/init" \\
          npm test -- --coverage --watchAll=false
        env:
          DD_ENV: ${{ env.DD_ENV }}
          DD_SERVICE: ${{ env.DD_SERVICE }}
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: false

  # ============================================
  # Stage 2: Security Scanning (Prisma Cloud)
  # ============================================
  security-scan:
    name: Prisma Cloud Security Scan
    runs-on: ubuntu-latest
    permissions:
      security-events: write
    steps:
      - uses: actions/checkout@v4
      
      # IaC Security Scanning
      - name: Prisma Cloud IaC Scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: all
          output_format: sarif
          output_file_path: prisma-iac-results.sarif
          soft_fail: true
      
      - name: Upload Prisma IaC Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: prisma-iac-results.sarif
          category: prisma-iac
      
      # Secrets Detection
      - name: Prisma Secrets Scan
        uses: bridgecrewio/checkov-action@v12
        with:
          directory: .
          framework: secrets
          soft_fail: true
      
      # Dependency Scanning
      - name: NPM Security Audit
        run: npm audit --audit-level=high || true

  # ============================================
  # Stage 3: Build & Push to JFrog Artifactory
  # ============================================
  build-and-push:
    name: Build & Push to JFrog
    runs-on: ubuntu-latest
    needs: [lint-and-test, security-scan]
    permissions:
      security-events: write
    outputs:
      image: ${{ steps.build-push.outputs.image }}
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      # Build Docker Image
      - name: Build Docker Image
        uses: docker/build-push-action@v5
        with:
          context: .
          load: true
          tags: ${{ github.event.repository.name }}:scan
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      # Scan with Prisma Cloud twistcli
      - name: Download Prisma Cloud Scanner
        run: |
          curl -k -u ${{ secrets.PRISMA_ACCESS_KEY }}:${{ secrets.PRISMA_SECRET_KEY }} \\
            -o twistcli \\
            "${{ secrets.PRISMA_API_URL }}/api/v1/util/twistcli"
          chmod +x twistcli
      
      - name: Scan Container with Prisma Cloud
        id: prisma-scan
        continue-on-error: true
        run: |
          ./twistcli images scan \\
            --address ${{ secrets.PRISMA_API_URL }} \\
            --user ${{ secrets.PRISMA_ACCESS_KEY }} \\
            --password ${{ secrets.PRISMA_SECRET_KEY }} \\
            --details \\
            ${{ github.event.repository.name }}:scan
      
      # Also scan with Trivy for comparison
      - name: Scan with Trivy
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ github.event.repository.name }}:scan'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
        continue-on-error: true
      
      - name: Upload Trivy Results
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'
      
      # Login and Push to JFrog Artifactory
      - name: Login to JFrog Artifactory
        uses: docker/login-action@v3
        with:
          registry: ${{ secrets.JFROG_URL }}
          username: ${{ secrets.JFROG_USERNAME }}
          password: ${{ secrets.JFROG_PASSWORD }}
      
      - name: Push to JFrog Artifactory
        id: build-push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            ${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }}:${{ github.sha }}
            ${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }}:${{ github.ref == 'refs/heads/main' && 'latest' || 'develop' }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Output Image URI
        run: |
          echo "image=${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }}:${{ github.sha }}" >> $GITHUB_OUTPUT

  # ============================================
  # Stage 4: Deploy via ArgoCD to EKS
  # ============================================
  deploy:
    name: Deploy to EKS via ArgoCD
    runs-on: ubuntu-latest
    needs: [build-and-push]
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    steps:
      - uses: actions/checkout@v4
      
      # Configure AWS credentials for EKS
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ vars.AWS_REGION || 'us-east-1' }}
      
      # Install ArgoCD CLI
      - name: Install ArgoCD CLI
        run: |
          curl -sSL -o argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
          chmod +x argocd
          sudo mv argocd /usr/local/bin/
      
      # Login to ArgoCD
      - name: Login to ArgoCD
        run: |
          argocd login ${{ secrets.ARGOCD_SERVER }} \\
            --auth-token ${{ secrets.ARGOCD_AUTH_TOKEN }} \\
            --grpc-web
      
      # Update and sync application
      - name: Update Application Image
        run: |
          argocd app set ${{ github.event.repository.name }}-${{ github.ref == 'refs/heads/main' && 'prod' || 'staging' }} \\
            --parameter image.repository=${{ secrets.JFROG_URL }}/${{ vars.JFROG_REPO || 'docker-local' }}/${{ github.event.repository.name }} \\
            --parameter image.tag=${{ github.sha }}
      
      - name: Sync Application
        run: |
          argocd app sync ${{ github.event.repository.name }}-${{ github.ref == 'refs/heads/main' && 'prod' || 'staging' }} --prune --timeout 300
          argocd app wait ${{ github.event.repository.name }}-${{ github.ref == 'refs/heads/main' && 'prod' || 'staging' }} --health --timeout 300
      
      # Verify deployment on EKS
      - name: Update kubeconfig
        run: |
          aws eks update-kubeconfig \\
            --region ${{ vars.AWS_REGION || 'us-east-1' }} \\
            --name ${{ secrets.EKS_CLUSTER_NAME }}
      
      - name: Verify Deployment
        run: |
          kubectl get pods -l app=${{ github.event.repository.name }} -n ${{ vars.K8S_NAMESPACE || 'default' }}
          kubectl rollout status deployment/${{ github.event.repository.name }} -n ${{ vars.K8S_NAMESPACE || 'default' }} --timeout=300s

  # ============================================
  # Stage 5: Datadog Observability
  # ============================================
  observability:
    name: Datadog Observability
    runs-on: ubuntu-latest
    needs: [deploy]
    if: success()
    steps:
      # Create Deployment Event in Datadog
      - name: Create Datadog Deployment Event
        run: |
          curl -X POST "https://api.${{ vars.DD_SITE || 'datadoghq.com' }}/api/v1/events" \\
            -H "Content-Type: application/json" \\
            -H "DD-API-KEY: ${{ secrets.DD_API_KEY }}" \\
            -d '{
              "title": "Deployment: ${{ github.event.repository.name }}",
              "text": "Deployed version ${{ github.sha }} to ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }} via ArgoCD",
              "priority": "normal",
              "tags": [
                "env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}",
                "service:${{ github.event.repository.name }}",
                "version:${{ github.sha }}",
                "source:github-actions",
                "registry:jfrog",
                "orchestration:argocd"
              ],
              "alert_type": "info",
              "source_type_name": "GITHUB"
            }'
      
      # Run Synthetic Tests (if configured)
      - name: Run Datadog Synthetic Tests
        if: vars.DD_SYNTHETIC_TEST_IDS != ''
        uses: DataDog/synthetics-ci-github-action@v1
        with:
          api_key: ${{ secrets.DD_API_KEY }}
          app_key: ${{ secrets.DD_APP_KEY }}
          public_ids: ${{ vars.DD_SYNTHETIC_TEST_IDS }}
          variables: 'ENVIRONMENT=${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}'
      
      # Update Service Catalog
      - name: Update Datadog Service Catalog
        run: |
          curl -X POST "https://api.${{ vars.DD_SITE || 'datadoghq.com' }}/api/v2/services/definitions" \\
            -H "Content-Type: application/json" \\
            -H "DD-API-KEY: ${{ secrets.DD_API_KEY }}" \\
            -H "DD-APPLICATION-KEY: ${{ secrets.DD_APP_KEY }}" \\
            -d '{
              "schema-version": "v2.1",
              "dd-service": "${{ github.event.repository.name }}",
              "team": "${{ vars.DD_TEAM || 'bcg-platform' }}",
              "repos": [
                {
                  "name": "${{ github.repository }}",
                  "provider": "github",
                  "url": "${{ github.server_url }}/${{ github.repository }}"
                }
              ],
              "tags": [
                "env:${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}",
                "team:${{ vars.DD_TEAM || 'bcg-platform' }}",
                "registry:jfrog"
              ]
            }'
"""
    }
}

# =============================================================================
# TOOL DETECTION CONFIGURATION
# =============================================================================

TOOL_DETECTION = {
    # Testing Detection
    "testing_nodejs": {
        "files": ["package.json", "jest.config.js", "jest.config.ts", "vitest.config.ts"],
        "directories": ["__tests__", "test", "tests", "spec"],
        "keywords": ["jest", "vitest", "mocha", "test"]
    },
    "testing_python": {
        "files": ["requirements.txt", "setup.py", "pyproject.toml", "pytest.ini", "conftest.py"],
        "directories": ["tests", "test"],
        "keywords": ["pytest", "unittest", "python test"]
    },
    "testing_go": {
        "files": ["go.mod", "go.sum"],
        "directories": [],
        "keywords": ["go test"]
    },
    "testing_java": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "directories": ["src/test"],
        "keywords": ["junit", "maven test", "gradle test"]
    },
    
    # Linting Detection
    "linting_nodejs": {
        "files": ["package.json", ".eslintrc", ".eslintrc.json", ".eslintrc.js", ".prettierrc"],
        "directories": [],
        "keywords": ["eslint", "prettier", "lint"]
    },
    "linting_python": {
        "files": ["requirements.txt", "pyproject.toml", "ruff.toml", ".flake8"],
        "directories": [],
        "keywords": ["ruff", "black", "flake8", "pylint"]
    },
    "linting_go": {
        "files": ["go.mod", ".golangci.yml"],
        "directories": [],
        "keywords": ["golangci-lint"]
    },
    
    # Security Detection
    "security_trivy": {
        "files": ["Dockerfile", ".trivyignore", "trivy.yaml"],
        "directories": ["k8s", "kubernetes", "helm"],
        "keywords": ["trivy", "security scan", "vulnerability"]
    },
    "security_codeql": {
        "files": [".github/codeql"],
        "directories": [],
        "keywords": ["codeql", "code analysis"]
    },
    "security_gitleaks": {
        "files": [".gitleaks.toml"],
        "directories": [],
        "keywords": ["gitleaks", "secret scan"]
    },
    
    # Registry Detection
    "registry_ghcr": {
        "files": ["Dockerfile"],
        "directories": [],
        "keywords": ["ghcr", "github container registry", "github packages"]
    },
    "registry_dockerhub": {
        "files": ["Dockerfile"],
        "directories": [],
        "keywords": ["docker hub", "dockerhub"]
    },
    "registry_ecr": {
        "files": ["Dockerfile"],
        "directories": [],
        "keywords": ["ecr", "aws ecr", "elastic container registry"]
    },
    
    # Deployment Detection
    "deploy_argocd": {
        "files": ["argocd-app.yaml", ".argocd"],
        "directories": ["argocd"],
        "keywords": ["argocd", "gitops"]
    },
    "deploy_kubernetes": {
        "files": ["deployment.yaml", "service.yaml"],
        "directories": ["k8s", "kubernetes", "manifests"],
        "keywords": ["kubernetes", "k8s", "kubectl"]
    },
    "deploy_eks": {
        "files": ["eksctl.yaml", "eks-config.yaml"],
        "directories": ["k8s", "kubernetes"],
        "keywords": ["eks", "amazon eks", "aws kubernetes"]
    },
    
    # BCG Enterprise Tools Detection
    "registry_jfrog": {
        "files": [".jfrog", "jfrog-cli.conf", "artifactory.json"],
        "directories": [],
        "keywords": ["jfrog", "artifactory", "jfrog artifactory", "artifact repository"]
    },
    "security_prisma": {
        "files": [".prismacloud", "prisma-cloud.yaml", ".checkov.yaml", ".checkov.yml"],
        "directories": [],
        "keywords": ["prisma", "prisma cloud", "twistlock", "checkov", "bridgecrew"]
    },
    "observability_datadog": {
        "files": ["datadog.yaml", "dd-agent.yaml", ".datadogci.json"],
        "directories": [],
        "keywords": ["datadog", "dd-trace", "apm", "observability", "monitoring"]
    }
}

# =============================================================================
# WORKFLOW REQUIREMENTS MAPPING
# Customer can specify what they need, and we map to tools
# =============================================================================

WORKFLOW_REQUIREMENTS = {
    "testing": {
        "description": "Automated testing (unit, integration, e2e)",
        "tools": {
            "javascript": "testing_nodejs",
            "typescript": "testing_nodejs",
            "python": "testing_python",
            "go": "testing_go",
            "java": "testing_java"
        }
    },
    "linting": {
        "description": "Code quality and formatting checks",
        "tools": {
            "javascript": "linting_nodejs",
            "typescript": "linting_nodejs",
            "python": "linting_python",
            "go": "linting_go"
        }
    },
    "security": {
        "description": "Security scanning and vulnerability detection",
        "tools": ["security_trivy", "security_codeql", "security_dependency_check", "security_gitleaks", "security_prisma"]
    },
    "container_build": {
        "description": "Build and push Docker images",
        "tools": ["registry_ghcr", "registry_dockerhub", "registry_ecr", "registry_jfrog"]
    },
    "deployment": {
        "description": "Deploy to production/staging environments",
        "tools": ["deploy_argocd", "deploy_kubernetes", "deploy_eks"]
    },
    "observability": {
        "description": "Monitoring, APM, and log management",
        "tools": ["observability_datadog"]
    },
    # BCG-specific combined requirements
    "bcg_enterprise": {
        "description": "BCG enterprise toolchain (JFrog + Prisma + Datadog + ArgoCD + EKS)",
        "tools": ["registry_jfrog", "security_prisma", "observability_datadog", "deploy_argocd", "deploy_eks"]
    }
}


def detect_tools(knowledge: Dict, user_request: str = "") -> Dict[str, dict]:
    """
    Detect which open-source tools should be included in the workflow
    based on repository analysis and user request.
    """
    detected_tools = {}
    
    for tool_name, detection in TOOL_DETECTION.items():
        detected = False
        reasons = []
        
        # Check for files
        config_files = knowledge.get("config_files", [])
        root_files = knowledge.get("root_files", [])
        all_files = config_files + root_files + list(knowledge.get("files", {}).keys())
        
        for file_pattern in detection.get("files", []):
            if any(file_pattern.lower() in f.lower() for f in all_files):
                detected = True
                reasons.append(f"Found file: {file_pattern}")
        
        # Check for directories
        directories = knowledge.get("directories", [])
        for dir_pattern in detection.get("directories", []):
            if any(dir_pattern.lower() in d.lower() for d in directories):
                detected = True
                reasons.append(f"Found directory: {dir_pattern}")
        
        # Check user request for keywords
        request_lower = user_request.lower()
        for keyword in detection.get("keywords", []):
            if keyword.lower() in request_lower:
                detected = True
                reasons.append(f"User requested: {keyword}")
        
        # Language-based detection for testing/linting
        primary_language = knowledge.get("primary_language", "").lower()
        if "nodejs" in tool_name and primary_language in ["javascript", "typescript"]:
            detected = True
            reasons.append(f"Detected language: {primary_language}")
        elif "python" in tool_name and primary_language == "python":
            detected = True
            reasons.append(f"Detected language: {primary_language}")
        elif "go" in tool_name and primary_language == "go":
            detected = True
            reasons.append(f"Detected language: {primary_language}")
        elif "java" in tool_name and primary_language == "java":
            detected = True
            reasons.append(f"Detected language: {primary_language}")
        
        # Always recommend security scanning
        if "security_trivy" in tool_name:
            detected = True
            reasons.append("Security scanning recommended for all projects")
        
        # Container registry if Dockerfile exists
        if "registry" in tool_name and knowledge.get("has_dockerfile"):
            if "ghcr" in tool_name:  # Default to GHCR (free)
                detected = True
                reasons.append("Dockerfile detected - GHCR recommended (free)")
        
        detected_tools[tool_name] = {
            "detected": detected,
            "reasons": reasons,
            "config": OPENSOURCE_DEVOPS_TOOLS.get(tool_name, {})
        }
    
    return detected_tools


def get_workflow_guidance(detected_tools: Dict) -> str:
    """
    Generate workflow generation guidance for detected tools.
    """
    guidance_parts = []
    
    for tool_name, info in detected_tools.items():
        if info.get("detected"):
            tool_config = info.get("config", {})
            if tool_config:
                guidance_parts.append(f"""
### {tool_config.get('name', tool_name)}
- Category: {tool_config.get('category', 'general')}
- Description: {tool_config.get('description', 'N/A')}
- Required Secrets: {', '.join(tool_config.get('secrets_required', [])) or 'None (uses GITHUB_TOKEN)'}

Include this in the workflow:
{tool_config.get('workflow_snippet', '')}
""")
    
    return "\n".join(guidance_parts) if guidance_parts else ""


def get_required_secrets(detected_tools: Dict) -> List[str]:
    """
    Get list of all required secrets for detected tools.
    """
    secrets = set()
    for tool_name, info in detected_tools.items():
        if info.get("detected"):
            tool_config = info.get("config", {})
            secrets.update(tool_config.get("secrets_required", []))
    return sorted(list(secrets))


def get_tools_by_category(category: str) -> Dict:
    """
    Get all tools in a specific category.
    """
    return {
        name: config 
        for name, config in OPENSOURCE_DEVOPS_TOOLS.items() 
        if config.get("category") == category
    }


def get_complete_workflow_for_language(language: str) -> str:
    """
    Get a complete workflow template for a specific language.
    """
    language_map = {
        "javascript": "complete_nodejs",
        "typescript": "complete_nodejs",
        "python": "complete_python"
    }
    
    tool_key = language_map.get(language.lower())
    if tool_key and tool_key in OPENSOURCE_DEVOPS_TOOLS:
        return OPENSOURCE_DEVOPS_TOOLS[tool_key].get("workflow_snippet", "")
    
    return ""
