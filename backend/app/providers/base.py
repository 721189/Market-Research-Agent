import enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, TypeVar, Generic

class ExtractionResultState(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    UNVERIFIED = "UNVERIFIED"

@dataclass
class LLMUsage:
    provider: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    duration_ms: int = 0
    search_queries_count: int = 0
    cost_usd: float = 0.0

@dataclass
class LLMRequest:
    prompt: str
    system_instruction: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.2
    max_output_tokens: Optional[int] = None
    response_mime_type: str = "text/plain" # or "application/json"
    timeout_seconds: float = 30.0

@dataclass
class LLMResponse:
    text: str
    parsed_json: Optional[Any] = None
    provider: str = "google-gemini"
    model: str = "gemini-1.5-flash"
    usage: Optional[LLMUsage] = None
    finish_reason: Optional[str] = "STOP"
    raw_response: Optional[Dict[str, Any]] = None

T = TypeVar("T")

@dataclass
class ExtractionResult(Generic[T]):
    data: Optional[T] = None
    state: ExtractionResultState = ExtractionResultState.UNVERIFIED
    error_message: Optional[str] = None
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    usage: Optional[LLMUsage] = None
    raw_text: Optional[str] = None

class ProviderError(Exception):
    """Base exception for LLM provider errors."""
    def __init__(self, message: str, provider: str = "unknown", retryable: bool = True, status_code: Optional[int] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.retryable = retryable
        self.status_code = status_code

class RateLimitError(ProviderError):
    """Raised when rate limits or quotas are hit."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, provider=provider, retryable=True, status_code=429)

class AuthenticationError(ProviderError):
    """Raised when API key is missing or invalid."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, provider=provider, retryable=False, status_code=401)

class ModelUnavailableError(ProviderError):
    """Raised when the requested model is not accessible."""
    def __init__(self, message: str, provider: str = "unknown"):
        super().__init__(message, provider=provider, retryable=True, status_code=503)

class BaseLLMProvider:
    """Abstract base class for all LLM providers."""
    
    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    async def generate(self, request: LLMRequest) -> LLMResponse:
        raise NotImplementedError

    def is_available(self) -> bool:
        raise NotImplementedError
