"""
AI Client for LLM-based Extraction

Provides a unified interface for calling LLM APIs (Claude, GPT-4) for data extraction.
Includes retry logic, rate limiting, and error handling.
"""

import os
import json
import time
from typing import Dict, Any, Optional
from anthropic import Anthropic
import anthropic

# Try importing OpenAI (optional)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AIExtractionClient:
    """Client for LLM-based data extraction with retry logic."""
    
    def __init__(
        self,
        provider: str = 'claude',  # or 'openai'
        model: str = None,
        api_key: str = None,
        max_retries: int = 3,
        retry_delay: float = 2.0
    ):
        """
        Initialize AI extraction client.
        
        Args:
            provider: 'claude' or 'openai'
            model: Model name (defaults based on provider)
            api_key: API key (or from environment)
            max_retries: Maximum retry attempts on failure
            retry_delay: Delay between retries in seconds
        """
        self.provider = provider.lower()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Get API key
        if api_key is None:
            if self.provider == 'claude':
                api_key = os.getenv('ANTHROPIC_API_KEY')
            elif self.provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
        
        if not api_key:
            raise ValueError(f"API key not provided for {provider}")
        
        # Set default models
        if model is None:
            if self.provider == 'claude':
                model = 'claude-3-5-sonnet-20241022'
            elif self.provider == 'openai':
                model = 'gpt-4-turbo-preview'
        
        self.model = model
        
        # Initialize client
        if self.provider == 'claude':
            self.client = Anthropic(api_key=api_key)
        elif self.provider == 'openai':
            if not OPENAI_AVAILABLE:
                raise ImportError("OpenAI library not installed. Run: pip install openai")
            self.client = OpenAI(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        print(f"Initialized {provider} client with model: {model}")
    
    def extract(
        self,
        prompt: str,
        system_prompt: str = "You are a data extraction assistant. Extract information accurately and return only valid JSON.",
        temperature: float = 0.0,
        max_tokens: int = 4096
    ) -> Dict[str, Any]:
        """
        Extract structured data using LLM.
        
        Args:
            prompt: Extraction prompt with data and instructions
            system_prompt: System message
            temperature: Sampling temperature (0 = deterministic)
            max_tokens: Maximum response tokens
            
        Returns:
            Extracted data as dictionary
        """
        for attempt in range(self.max_retries):
            try:
                if self.provider == 'claude':
                    response = self._extract_claude(
                        prompt, system_prompt, temperature, max_tokens
                    )
                elif self.provider == 'openai':
                    response = self._extract_openai(
                        prompt, system_prompt, temperature, max_tokens
                    )
                
                # Parse JSON response
                parsed = self._parse_json_response(response)
                return parsed
                
            except json.JSONDecodeError as e:
                print(f"JSON parsing error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
                    
            except anthropic.RateLimitError as e:
                print(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * 2)  # Longer delay for rate limits
                else:
                    raise
                    
            except Exception as e:
                print(f"Extraction error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                else:
                    raise
    
    def _extract_claude(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Extract using Claude API."""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    
    def _extract_openai(
        self,
        prompt: str,
        system_prompt: str,
        temperature: float,
        max_tokens: int
    ) -> str:
        """Extract using OpenAI API."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"}  # Force JSON output
        )
        
        return response.choices[0].message.content
    
    def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse JSON from LLM response, handling common formatting issues.
        
        Args:
            response_text: Raw response text from LLM
            
        Returns:
            Parsed JSON as dictionary
        """
        # Remove markdown code blocks if present
        text = response_text.strip()
        if text.startswith('```json'):
            text = text[7:]  # Remove ```json
        if text.startswith('```'):
            text = text[3:]  # Remove ```
        if text.endswith('```'):
            text = text[:-3]  # Remove trailing ```
        
        text = text.strip()
        
        # Parse JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON. Response text:\n{text[:500]}...")
            raise


def create_extraction_client(provider: str = None) -> AIExtractionClient:
    """
    Factory function to create extraction client with defaults.
    
    Args:
        provider: 'claude' or 'openai', defaults to Claude if available
        
    Returns:
        Configured AIExtractionClient
    """
    if provider is None:
        # Try Claude first (best for extraction), fall back to OpenAI
        if os.getenv('ANTHROPIC_API_KEY'):
            provider = 'claude'
        elif os.getenv('OPENAI_API_KEY'):
            provider = 'openai'
        else:
            raise ValueError("No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY")
    
    return AIExtractionClient(provider=provider)


# Export
__all__ = ['AIExtractionClient', 'create_extraction_client']
