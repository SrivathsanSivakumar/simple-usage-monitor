### Pricing configuration for Claude models
### Ref: https://claude.com/pricing#api

from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ModelPricing:
    """Model pricing configuration for Claude models"""
    input_base: int
    output_base: int
    cache_write: int
    cache_read: int
    tiered: bool = False
    tier_break: Optional[int] = None
    input_tier: Optional[int] = None
    output_tier: Optional[int] = None
    cache_write_tier: Optional[int] = None
    cache_read_tier: Optional[int] = None

OPUS_4_5 = ModelPricing(
    input_base=5.00,
    output_base=25.00,
    cache_write=6.25,
    cache_read=0.50
)

SONNET_4_5 = ModelPricing(
    input_base=3.00,
    output_base=15.00,
    cache_write=3.75,
    cache_read=0.30,
    tiered=True,
    tier_break=200_000,
    input_tier=6.00,
    output_tier=22.50,
    cache_write_tier=7.50,
    cache_read_tier=0.60
)

HAIKU_4_5 = ModelPricing(
    input_base=1.00,
    output_base=5.00,
    cache_write=1.25,
    cache_read=0.10
)

MODEL_PRICING: Dict[str, ModelPricing] = {
    "opus-4-5": OPUS_4_5,
    "sonnet-4-5": SONNET_4_5,
    "haiku-4-5": HAIKU_4_5
}

def _get_pricing(model: str) -> ModelPricing:
    """Get pricing for a model name
    
        Args:
            model: Claude model used for message
        
        Returns:
            ModelPricing configuration for claude model
        
        Raises:
            ValueError: if model is unknown
    """
    model_lower = model.lower()
    for key, pricing in MODEL_PRICING.items():
        if key in model_lower:
            return pricing
    
    # Return zero-cost pricing for unknown/synthetic models
    return ModelPricing(
        input_base=0.0,
        output_base=0.0,
        cache_write=0.0,
        cache_read=0.0,
        tiered=False
    )

# Ref: https://github.com/Maciek-roboblog/Claude-Code-Usage-Monitor
@dataclass
class PlanLimits:
    """Session limits for Claude Code subscription plans (per 5-hour window)"""
    tokens: int
    cost: float
    messages: int

PRO = PlanLimits(
    tokens=19_000,
    cost=18.00,
    messages=250
)

MAX5 = PlanLimits(
    tokens=88_000,
    cost=35.00,
    messages=1000
)

MAX20 = PlanLimits(
    tokens=220_000,
    cost=140.00,
    messages=2000
)

PLAN_LIMITS: Dict[str, PlanLimits] = {
    "pro": PRO,
    "max5": MAX5,
    "max20": MAX20
}

def _get_plan_limits(plan: str) -> PlanLimits:
    """Get limits for a subscription plan

        Args:
            plan: Plan name ('pro', 'max5', or 'max20')

        Returns:
            PlanLimits for the specified plan (defaults to Pro if unknown)
    """
    return PLAN_LIMITS.get(plan.lower(), PRO)
