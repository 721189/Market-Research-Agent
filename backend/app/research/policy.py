from pydantic import BaseModel

class ResearchPolicy(BaseModel):
    max_sources: int
    max_llm_calls: int
    max_context_tokens: int
    validation_level: str
    claim_depth: str

def get_research_policy(mode: str) -> ResearchPolicy:
    if mode == "quick":
        return ResearchPolicy(
            max_sources=5,
            max_llm_calls=15,
            max_context_tokens=15000,
            validation_level="basic",
            claim_depth="lightweight"
        )
    elif mode == "batch":
        return ResearchPolicy(
            max_sources=3,
            max_llm_calls=10,
            max_context_tokens=10000,
            validation_level="basic",
            claim_depth="minimal"
        )
    else:  # deep
        return ResearchPolicy(
            max_sources=20,
            max_llm_calls=50,
            max_context_tokens=100000,
            validation_level="strict",
            claim_depth="comprehensive"
        )
