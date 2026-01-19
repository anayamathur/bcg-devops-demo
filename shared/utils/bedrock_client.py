"""
BCG Agentic DevOps - Bedrock AI Client
=======================================
Unified Bedrock client using Nova Pro model for all agents.
"""

import json
import boto3
import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BedrockClient:
    """
    AWS Bedrock client for Nova Pro model.
    Provides unified AI capabilities for all agents.
    """
    
    def __init__(
        self,
        model_id: str = "amazon.nova-pro-v1:0",
        region: str = "us-east-1",
        profile: str = "credit"
    ):
        self.model_id = model_id
        self.region = region
        
        # Initialize boto3 session with profile
        session = boto3.Session(profile_name=profile, region_name=region)
        self.client = session.client('bedrock-runtime')
        
        logger.info(f"Initialized BedrockClient with model: {model_id}")
    
    def invoke(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        top_p: float = 0.9
    ) -> str:
        """
        Invoke Bedrock Nova Pro model with a prompt.
        
        Args:
            prompt: User prompt/query
            system_prompt: Optional system context
            max_tokens: Maximum response tokens
            temperature: Creativity level (0-1)
            top_p: Nucleus sampling parameter
            
        Returns:
            Model response text
        """
        try:
            # Build messages
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            
            # Build request body
            request_body = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": temperature,
                    "topP": top_p
                }
            }
            
            # Add system prompt if provided
            if system_prompt:
                request_body["system"] = [{"text": system_prompt}]
            
            # Invoke model
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            
            if 'output' in response_body and 'message' in response_body['output']:
                content = response_body['output']['message']['content']
                if content and len(content) > 0:
                    return content[0].get('text', '')
            
            logger.warning(f"Unexpected response format: {response_body}")
            return str(response_body)
            
        except Exception as e:
            logger.error(f"Bedrock invocation error: {e}")
            raise
    
    def invoke_with_tools(
        self,
        prompt: str,
        tools: List[Dict[str, Any]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192
    ) -> Dict[str, Any]:
        """
        Invoke model with tool definitions for function calling.
        
        Args:
            prompt: User prompt
            tools: List of tool definitions
            system_prompt: Optional system context
            max_tokens: Maximum tokens
            
        Returns:
            Dict with response and any tool calls
        """
        try:
            messages = [{"role": "user", "content": [{"text": prompt}]}]
            
            request_body = {
                "messages": messages,
                "inferenceConfig": {
                    "maxTokens": max_tokens,
                    "temperature": 0.2  # Lower for tool use
                },
                "toolConfig": {
                    "tools": tools
                }
            }
            
            if system_prompt:
                request_body["system"] = [{"text": system_prompt}]
            
            response = self.client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            
            # Extract tool calls if any
            result = {
                "response": "",
                "tool_calls": [],
                "stop_reason": response_body.get("stopReason", "")
            }
            
            if 'output' in response_body and 'message' in response_body['output']:
                content = response_body['output']['message']['content']
                for item in content:
                    if 'text' in item:
                        result["response"] = item['text']
                    elif 'toolUse' in item:
                        result["tool_calls"].append(item['toolUse'])
            
            return result
            
        except Exception as e:
            logger.error(f"Bedrock tool invocation error: {e}")
            raise
    
    def analyze_code(self, code: str, language: str, task: str = "analyze") -> Dict[str, Any]:
        """
        Analyze code using AI.
        
        Args:
            code: Source code to analyze
            language: Programming language
            task: Type of analysis (analyze, security, quality, etc.)
            
        Returns:
            Analysis results
        """
        prompts = {
            "analyze": f"""Analyze this {language} code and provide:
1. Purpose and functionality
2. Dependencies used
3. Potential issues
4. Recommendations

Code:
```{language}
{code}
```""",
            "security": f"""Perform a security analysis on this {language} code:
1. Identify vulnerabilities (CWE, OWASP)
2. Rate severity (Critical/High/Medium/Low)
3. Suggest fixes

Code:
```{language}
{code}
```

Respond in JSON format.""",
            "quality": f"""Analyze code quality for this {language} code:
1. Code smells
2. Complexity issues
3. Best practice violations
4. Refactoring suggestions

Code:
```{language}
{code}
```"""
        }
        
        prompt = prompts.get(task, prompts["analyze"])
        response = self.invoke(prompt)
        
        return {
            "task": task,
            "language": language,
            "analysis": response
        }


# Singleton instance
_bedrock_client = None

def get_bedrock_client(
    model_id: str = "amazon.nova-pro-v1:0",
    region: str = "us-east-1",
    profile: str = "credit"
) -> BedrockClient:
    """Get or create Bedrock client instance"""
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = BedrockClient(model_id, region, profile)
    return _bedrock_client
