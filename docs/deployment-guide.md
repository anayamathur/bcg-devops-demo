# BCG DevOps + GenAI PoC - Deployment Guide

## Prerequisites

### AWS Requirements
- AWS Account with administrator access
- AWS CLI v2 installed and configured
- Bedrock access enabled (Nova Pro model)
- IAM permissions for:
  - Lambda
  - API Gateway
  - Secrets Manager
  - CloudWatch
  - Bedrock

### Development Tools
- Terraform >= 1.5.0
- Python 3.12+
- Git

### External Integrations
- GitHub Personal Access Token with scopes:
  - `repo` (full control of repositories)
  - `workflow` (Actions access)

---

## Step 1: Clone Repository

```bash
git clone https://github.com/your-org/bcg-devops-genai-poc.git
cd bcg-devops-genai-poc
```

---

## Step 2: Configure AWS Credentials

```bash
# Verify AWS CLI is configured
aws sts get-caller-identity

# Expected output:
# {
#     "UserId": "AIDAEXAMPLE",
#     "Account": "123456789012",
#     "Arn": "arn:aws:iam::123456789012:user/your-user"
# }
```

---

## Step 3: Enable Bedrock Nova Pro

1. Navigate to AWS Console > Amazon Bedrock
2. Go to **Model access** in the left sidebar
3. Click **Manage model access**
4. Enable **Amazon Nova Pro** (`amazon.nova-pro-v1:0`)
5. Wait for access to be granted (usually instant)

### Verify Model Access

```bash
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?modelId=='amazon.nova-pro-v1:0']"
```

---

## Step 4: Store GitHub Token

```bash
# Create secret in Secrets Manager
aws secretsmanager create-secret \
  --name bcg-devops-genai/github-token \
  --description "GitHub PAT for DevOps GenAI PoC" \
  --secret-string '{"token": "ghp_YOUR_GITHUB_TOKEN_HERE"}' \
  --region us-east-1

# Or update existing secret
aws secretsmanager put-secret-value \
  --secret-id bcg-devops-genai/github-token \
  --secret-string '{"token": "ghp_YOUR_GITHUB_TOKEN_HERE"}' \
  --region us-east-1
```

---

## Step 5: Deploy Infrastructure

### Initialize Terraform

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init
```

### Review Plan

```bash
# Create execution plan
terraform plan -var="aws_region=us-east-1" -out=tfplan

# Review the plan
terraform show tfplan
```

### Apply Changes

```bash
# Deploy infrastructure
terraform apply tfplan

# Note the outputs:
# api_gateway_url = "https://xxxxxx.execute-api.us-east-1.amazonaws.com/prod"
```

---

## Step 6: Verify Deployment

### Health Check

```bash
# Get API URL from Terraform output
API_URL=$(terraform output -raw api_gateway_url)

# Test health endpoint
curl $API_URL/health
```

Expected response:
```json
{
  "status": "healthy",
  "model": "amazon.nova-pro-v1:0"
}
```

### Test Repository Analysis

```bash
curl -X POST $API_URL/analyze \
  -H "Content-Type: application/json" \
  -d '{"repository": "facebook/react"}'
```

---

## Step 7: Configure Frontend (Optional)

### Local Development

```bash
cd ../frontend

# Update API endpoint in index.html
# Replace API_GATEWAY_URL with your actual URL

# Start local server
python3 -m http.server 8080
```

Open http://localhost:8080 in your browser.

### Production Deployment

For production, deploy the frontend to:
- **S3 + CloudFront** (recommended)
- **Amplify Hosting**
- **EC2/ECS**

---

## Infrastructure Components

| Resource | Name | Purpose |
|----------|------|---------|
| Lambda | `bcg-github-integration` | Main API handler |
| API Gateway | `bcg-devops-genai-api` | REST API |
| IAM Role | `bcg-lambda-role` | Lambda permissions |
| CloudWatch | `bcg-devops-genai-logs` | Logging |

---

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `AWS_REGION` | AWS region | Yes |
| `GITHUB_TOKEN_SECRET_ID` | Secrets Manager ID | Yes |
| `BEDROCK_MODEL_ID` | Bedrock model | Yes |

---

## Terraform Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `aws_region` | `us-east-1` | AWS region |
| `lambda_timeout` | `300` | Lambda timeout (seconds) |
| `lambda_memory` | `512` | Lambda memory (MB) |

### Override Variables

```bash
# Using tfvars file
terraform apply -var-file="production.tfvars"

# Using command line
terraform apply -var="aws_region=eu-west-1" -var="lambda_memory=1024"
```

---

## Updating the Deployment

### Update Lambda Code

```bash
cd infrastructure/terraform

# Re-package Lambda
zip -r ../lambda_function.zip ../lambda/github-integration/

# Apply changes
terraform apply
```

### Update Configuration

```bash
# Modify variables.tf or terraform.tfvars
terraform plan
terraform apply
```

---

## Cleanup

To destroy all resources:

```bash
cd infrastructure/terraform

# Review what will be destroyed
terraform plan -destroy

# Destroy infrastructure
terraform destroy
```

### Manual Cleanup

If Terraform destroy fails, manually delete:
1. CloudWatch log groups
2. Secrets Manager secrets
3. S3 buckets (if any)

---

## Troubleshooting Deployment

### Common Issues

#### 1. Terraform Init Fails

```bash
# Clear Terraform cache
rm -rf .terraform .terraform.lock.hcl
terraform init
```

#### 2. Lambda Deployment Package Too Large

```bash
# Use Lambda Layers for dependencies
# Or use container image deployment
```

#### 3. API Gateway 500 Error

```bash
# Check Lambda logs
aws logs tail /aws/lambda/bcg-github-integration --follow
```

#### 4. Bedrock Access Denied

```bash
# Verify model access
aws bedrock list-foundation-models --region us-east-1

# Check IAM policy has bedrock:InvokeModel permission
```

---

## Security Considerations

1. **Secrets Management**: Never commit tokens to Git
2. **IAM Policies**: Use least privilege
3. **API Authentication**: Add API keys for production
4. **VPC**: Consider VPC deployment for private access
5. **Logging**: Enable CloudTrail for audit

---

## Next Steps

After deployment:
1. Test all API endpoints
2. Configure GitHub webhook (optional)
3. Set up monitoring alerts
4. Review [User Guide](user-guide.md)

---

*Last Updated: December 2024*
