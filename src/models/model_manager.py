"""
Model Manager
Enhanced model routing adapters for CCR Claude, GLM, MiniMax, and Ollama
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ModelConfig:
    """Configuration for a specific model"""
    name: str
    model: str
    endpoint: Optional[str] = None
    base_url: Optional[str] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.3
    timeout: int = 30
    retries: int = 2
    headers: Dict[str, str] = None

@dataclass
class ModelResponse:
    """Standardized model response format"""
    content: str
    model: str
    confidence: float = 0.8
    tokens_used: int = 0
    metadata: Dict[str, Any] = None

class ModelManager:
    """Enhanced model manager with better error handling and routing"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.models = self._parse_model_configs(config.get('models', {}))
        self.api_keys = self._parse_api_keys(config.get('api_keys', {}))
        self.session = requests.Session()
        self.default_model = config.get('agents', {}).get('pain_point_analyzer', {}).get('primary_model', 'glm_4_6')
        
    def _parse_model_configs(self, models_config: Dict) -> Dict[str, ModelConfig]:
        """Parse model configurations into ModelConfig objects"""
        parsed = {}
        for key, cfg in models_config.items():
            parsed[key] = ModelConfig(
                name=key,
                endpoint=cfg.get('endpoint'),
                base_url=cfg.get('base_url'),
                model=cfg.get('model', key),
                max_tokens=cfg.get('max_tokens'),
                temperature=cfg.get('temperature', 0.3),
                timeout=cfg.get('timeout', 30),
                retries=cfg.get('retries', 2)
            )
        return parsed
    
    def _parse_api_keys(self, api_keys_config: Dict) -> Dict[str, str]:
        """Parse API keys using explicit provider mapping and env fallback"""
        # Accept both provider-named keys and env vars mapped in ConfigLoader
        merged = dict(api_keys_config)
        # Merge env if present (pre-expanded by ConfigLoader)
        for env_key in ['github_token','glm_api_key','minimax_api_key','openrouter_api_key','google_search_key']:
            val = os.getenv(env_key.upper())
            if val and not merged.get(env_key):
                merged[env_key] = val
        return merged
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        return list(self.models.keys())
    
    def is_model_available(self, model_name: str) -> bool:
        """Check if a model is available"""
        if model_name == 'ollama':
            return model_name in self.models
        if model_name == 'glm_4_6':
            return model_name in self.models and bool(self.api_keys.get('glm_api_key'))
        if model_name == 'minimax':
            return model_name in self.models and bool(self.api_keys.get('minimax_api_key') or self.api_keys.get('openrouter_api_key'))
        return model_name in self.models
    
    def call_model(self, model_name: str, prompt: str, data: Dict = None, 
                  fallback_models: List[str] = None) -> ModelResponse:
        """Call a specific model with fallback support"""
        models_to_try = [model_name]
        if fallback_models:
            models_to_try.extend(fallback_models)
        
        last_error = None
        for attempt_model in models_to_try:
            if not self.is_model_available(attempt_model):
                logger.warning(f"Model {attempt_model} not available, skipping")
                continue
            
            try:
                logger.info(f"Attempting to call model: {attempt_model}")
                return self._call_specific_model(attempt_model, prompt, data)
            except Exception as e:
                logger.error(f"Model {attempt_model} call failed: {e}")
                last_error = e
                continue
        
        if last_error:
            raise RuntimeError(f"All model attempts failed. Last error: {last_error}")
    
    def _call_specific_model(self, model_name: str, prompt: str, data: Dict = None) -> ModelResponse:
        """Call a specific model by name"""
        model_config = self.models.get(model_name)
        if not model_config:
            raise ValueError(f"Model configuration missing for {model_name}")
        
        api_key = None
        if model_name == 'glm_4_6':
            api_key = self.api_keys.get('glm_api_key')
        elif model_name == 'minimax':
            api_key = self.api_keys.get('minimax_api_key') or self.api_keys.get('openrouter_api_key')
        elif model_name == 'ollama':
            api_key = None
        else:
            api_key = self.api_keys.get(model_name)
        if model_name != 'ollama' and not api_key:
            raise ValueError(f"API key missing for {model_name}")
        
        # Route to specific model implementation
        if model_name == 'glm_4_6':
            return self._call_glm_4_6(model_config, api_key, prompt, data)
        elif model_name == 'minimax':
            return self._call_minimax(model_config, api_key, prompt, data)
        elif model_name == 'ollama':
            return self._call_ollama(model_config, prompt, data)
        else:
            # Generic API call
            return self._call_generic_api(model_config, api_key, prompt, data)
    
    def _call_glm_4_6(self, config: ModelConfig, api_key: str, prompt: str, data: Dict = None) -> ModelResponse:
        """Call GLM 4.6 model"""
        endpoint = config.base_url or "https://open.bigmodel.cn/api/paas/v4/"
        url = f"{endpoint.rstrip('/')}/chat/completions"
        
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens or 4000
        }
        
        if data:
            payload["data"] = data
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        
        response = self._make_request("POST", url, headers, payload, config.timeout, config.retries)
        return self._parse_response(response, "glm-4.6")
    
    def _call_minimax(self, config: ModelConfig, api_key: str, prompt: str, data: Dict = None) -> ModelResponse:
        """Call MiniMax model"""
        endpoint = config.base_url or "https://api.minimax.chat/v1/"
        url = f"{endpoint.rstrip('/')}/text/chatcompletion_pro"
        
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens or 2000
        }
        
        if data:
            payload["data"] = data
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        response = self._make_request("POST", url, headers, payload, config.timeout, config.retries)
        return self._parse_response(response, "minimax")
    
    def _call_ollama(self, config: ModelConfig, prompt: str, data: Dict = None) -> ModelResponse:
        """Call Ollama model (local)"""
        endpoint = config.base_url or "http://localhost:11434/v1/"
        url = f"{endpoint.rstrip('/')}/chat/completions"
        
        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "stream": False
        }
        
        if data:
            payload["data"] = data
        
        headers = {"Content-Type": "application/json"}
        
        response = self._make_request("POST", url, headers, payload, config.timeout, config.retries)
        return self._parse_response(response, "ollama")
    
    def _call_generic_api(self, config: ModelConfig, api_key: str, prompt: str, data: Dict = None) -> ModelResponse:
        """Generic API call for unknown models"""
        url = config.endpoint or config.base_url
        if not url:
            raise ValueError(f"No endpoint specified for model {config.name}")
        
        payload = {
            "model": config.model,
            "prompt": prompt,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens
        }
        
        if data:
            payload["data"] = data
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        response = self._make_request("POST", url, headers, payload, config.timeout, config.retries)
        return self._parse_response(response, config.name)
    
    def _make_request(self, method: str, url: str, headers: Dict[str, str], 
                    payload: Dict, timeout: int, retries: int) -> Dict:
        """Make HTTP request with retry logic"""
        for attempt in range(retries):
            try:
                response = self.session.request(method, url, headers=headers, json=payload, timeout=timeout)
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                logger.warning(f"Request attempt {attempt + 1}/{retries} failed: {exc}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
    
    def _parse_response(self, response: Dict, model_label: str) -> ModelResponse:
        """Parse standardized response from different APIs"""
        if not response:
            raise RuntimeError("Empty response received")
        
        # Extract content based on response format
        content = None
        tokens_used = 0
        confidence = 0.8
        
        if 'choices' in response and response['choices']:
            choice = response['choices'][0]
            content = choice.get('message', {}).get('content') or choice.get('text')
        elif 'output' in response:
            content = response['output']
        elif 'message' in response:
            content = response['message']
        elif 'data' in response:
            content = response['data']
        else:
            # Fallback to string representation
            content = str(response)
        
        # Extract usage information
        if 'usage' in response:
            usage = response['usage']
            tokens_used = usage.get('total_tokens', usage.get('prompt_tokens', 0))
        
        # Try to extract confidence if available
        if 'confidence' in response:
            confidence = float(response['confidence'])
        elif 'model_analysis' in response and isinstance(response['model_analysis'], dict):
            confidence = response['model_analysis'].get('confidence', 0.8)
        
        if not content:
            raise RuntimeError(f"Unable to extract content from {model_label} response")
        
        return ModelResponse(
            content=content,
            model=model_label,
            confidence=confidence,
            tokens_used=tokens_used,
            metadata=response
        )
    
    def analyze_pain_points(self, repository_data: Dict, pr_data: List[Dict] = None) -> ModelResponse:
        """Analyze repository for pain points using default model"""
        prompt = self._build_pain_point_prompt(repository_data, pr_data)
        
        # Try primary model first, then fallback
        fallback_models = ['minimax', 'ollama']
        return self.call_model(self.default_model, prompt, 
                           data={"repository": repository_data, "pull_requests": pr_data},
                           fallback_models=fallback_models)
    
    def _build_pain_point_prompt(self, repository_data: Dict, pr_data: List[Dict] = None) -> str:
        """Build prompt for pain point analysis"""
        prompt = f"""
        Analyze the following repository for potential pain points and issues:
        
        Repository Information:
        - Name: {repository_data.get('name', 'Unknown')}
        - Owner: {repository_data.get('owner', 'Unknown')}
        - Language: {repository_data.get('language', 'Unknown')}
        - Health Score: {repository_data.get('health_score', 'Unknown')}
        - Open PRs: {len(pr_data or [])}
        
        Recent Pull Requests:
        """
        
        if pr_data:
            for i, pr in enumerate(pr_data[:5], 1):  # Limit to first 5 PRs
                prompt += f"""
        PR #{i}: {pr.get('title', 'No title')}
        - Author: {pr.get('author', 'Unknown')}
        - State: {pr.get('state', 'Unknown')}
        - Changes: +{pr.get('additions', 0)}/-{pr.get('deletions', 0)}
        - Comments: {pr.get('review_comments', 0)}
        - Mergeable: {pr.get('mergeable', 'Unknown')}
                """
        
        prompt += """
        
        Please analyze this repository and identify:
        1. Code quality issues
        2. CI/CD problems
        3. Merge conflicts or collaboration issues
        4. Performance or scalability concerns
        5. Security vulnerabilities
        6. Documentation gaps
        7. Testing deficiencies
        
        For each issue identified, provide:
        - Type of issue
        - Severity level (1-5, where 5 is most severe)
        - Description of the problem
        - Recommended solution approach
        - Confidence score (0-1)
        
        Format your response as JSON with the following structure:
        {
            "pain_points": [
                {
                    "type": "issue_type",
                    "severity": 1-5,
                    "description": "detailed description",
                    "recommendation": "solution approach",
                    "confidence": 0.0-1.0
                }
            ],
            "summary": "overall assessment",
            "confidence": 0.0-1.0
        }
        """
        
        return prompt
    
    def generate_recommendations(self, pain_point: Dict) -> ModelResponse:
        """Generate recommendations for a specific pain point"""
        prompt = self._build_recommendation_prompt(pain_point)
        
        # Use lighter model for recommendations
        return self.call_model('minimax', prompt, 
                           fallback_models=['glm_4_6', 'ollama'])
    
    def _build_recommendation_prompt(self, pain_point: Dict) -> str:
        """Build prompt for recommendation generation"""
        prompt = f"""
        Generate specific, actionable recommendations for the following pain point:
        
        Pain Point Details:
        - Type: {pain_point.get('type', 'Unknown')}
        - Severity: {pain_point.get('severity', 'Unknown')}/5
        - Description: {pain_point.get('description', 'No description')}
        - Current Confidence: {pain_point.get('confidence', 'Unknown')}
        
        Please provide:
        1. 3-5 specific, actionable recommendations
        2. Implementation priority (high/medium/low)
        3. Estimated effort (hours/days)
        4. Risk level if not addressed
        5. Reference to best practices or documentation
        
        Format your response as JSON:
        {
            "recommendations": [
                {
                    "text": "specific recommendation",
                    "priority": "high/medium/low",
                    "effort": "time estimate",
                    "risk": "risk level",
                    "reference": "documentation link"
                }
            ],
            "summary": "implementation strategy"
        }
        """
        
        return prompt
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all models"""
        return {
            "available_models": self.get_available_models(),
            "default_model": self.default_model,
            "model_configs": {name: {
                "model": cfg.model,
                "temperature": cfg.temperature,
                "max_tokens": cfg.max_tokens,
                "timeout": cfg.timeout
            } for name, cfg in self.models.items()
            }
        }