"""Tests for pricing.py - Model pricing and plan limits"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data.pricing import _get_pricing, _get_plan_limits
from data.log_reader import _calculate_total_cost


class TestModelPricingLookup:
    """Test _get_pricing() model matching logic"""

    def test_sonnet_model_match(self):
        pricing = _get_pricing("claude-sonnet-4-5-20250929")
        assert pricing.input_base == 3.00
        assert pricing.tiered == True

    def test_opus_model_match(self):
        pricing = _get_pricing("claude-opus-4-5-20251101")
        assert pricing.input_base == 5.00
        assert pricing.tiered == False

    def test_haiku_model_match(self):
        pricing = _get_pricing("claude-haiku-4-5")
        assert pricing.input_base == 1.00

    def test_unknown_model_returns_zero_cost(self):
        pricing = _get_pricing("unknown-model-xyz")
        assert pricing.input_base == 0.0
        assert pricing.output_base == 0.0

    def test_case_insensitive_matching(self):
        pricing = _get_pricing("CLAUDE-SONNET-4-5")
        assert pricing.input_base == 3.00

    def test_partial_model_name_needs_version(self):
        # Substring "sonnet" alone doesn't match - needs "sonnet-4-5"
        pricing = _get_pricing("sonnet")
        assert pricing.input_base == 0.0  # Returns zero-cost for unknown

    def test_none_model_name_raises_error(self):
        # None model causes AttributeError - this is a known edge case
        with pytest.raises(AttributeError):
            _get_pricing(None)


class TestTieredPricing:
    """Test tiered pricing for Sonnet 4.5 (>200k token threshold)"""

    def test_sonnet_below_tier_break(self):
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5",
            input_tokens=100_000,
            output_tokens=50_000,
            cache_write_tokens=0,
            cache_read_tokens=0
        )
        # (100k/1M * 3.00) + (50k/1M * 15.00) = 1.05
        assert cost == pytest.approx(1.05)

    def test_sonnet_at_exact_tier_break(self):
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5",
            input_tokens=200_000,
            output_tokens=0,
            cache_write_tokens=0,
            cache_read_tokens=0
        )
        assert cost == pytest.approx(0.60)

    def test_sonnet_above_tier_break(self):
        # ALL tokens charged at tier rate when threshold exceeded
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5",
            input_tokens=250_000,
            output_tokens=100_000,
            cache_write_tokens=0,
            cache_read_tokens=0
        )
        # (250k/1M * 6.00) + (100k/1M * 22.50) = 3.75
        assert cost == pytest.approx(3.75)

    def test_cache_tokens_count_toward_tier_break(self):
        cost = _calculate_total_cost(
            model="claude-sonnet-4-5",
            input_tokens=100_000,
            output_tokens=0,
            cache_write_tokens=50_000,
            cache_read_tokens=60_000,  # Total input: 210k > 200k
        )
        # Tier rates apply: input*6.00 + cache_write*7.50 + cache_read*0.60
        expected = 0.60 + 0.375 + 0.036
        assert cost == pytest.approx(expected)

    def test_opus_no_tiering(self):
        cost_small = _calculate_total_cost("opus-4-5", 10_000, 5_000, 0, 0)
        cost_large = _calculate_total_cost("opus-4-5", 300_000, 150_000, 0, 0)

        assert cost_small == pytest.approx(0.175)
        assert cost_large == pytest.approx(5.25)

    def test_haiku_no_tiering(self):
        cost_small = _calculate_total_cost("haiku-4-5", 50_000, 25_000, 0, 0)
        cost_large = _calculate_total_cost("haiku-4-5", 500_000, 250_000, 0, 0)

        assert cost_small == pytest.approx(0.175)
        assert cost_large == pytest.approx(1.75)


class TestPlanLimits:
    """Test plan limit lookups"""

    def test_pro_plan_limits(self):
        limits = _get_plan_limits("pro")
        assert limits.tokens == 19_000
        assert limits.cost == 18.00
        assert limits.messages == 250

    def test_max5_plan_limits(self):
        limits = _get_plan_limits("max5")
        assert limits.tokens == 88_000
        assert limits.cost == 35.00
        assert limits.messages == 1000

    def test_max20_plan_limits(self):
        limits = _get_plan_limits("max20")
        assert limits.tokens == 220_000
        assert limits.cost == 140.00
        assert limits.messages == 2000

    def test_case_insensitive_plan_lookup(self):
        limits = _get_plan_limits("PRO")
        assert limits.tokens == 19_000

    def test_unknown_plan_defaults_to_pro(self):
        limits = _get_plan_limits("unknown-plan")
        assert limits.tokens == 19_000


class TestPricingEdgeCases:
    """Edge cases and numerical precision"""

    def test_zero_tokens_zero_cost(self):
        cost = _calculate_total_cost("sonnet-4-5", 0, 0, 0, 0)
        assert cost == 0.0

    def test_very_large_token_counts(self):
        cost = _calculate_total_cost("sonnet-4-5", 10_000_000, 5_000_000, 0, 0)
        expected = (10_000_000 / 1_000_000) * 6.00 + (5_000_000 / 1_000_000) * 22.50
        assert cost == pytest.approx(expected, rel=1e-6)

    def test_fractional_cost_precision(self):
        cost = _calculate_total_cost("haiku-4-5", 123, 456, 0, 0)
        expected = (123/1_000_000)*1.00 + (456/1_000_000)*5.00
        assert cost == pytest.approx(expected, abs=1e-6)

    def test_all_cache_tokens_only(self):
        cost = _calculate_total_cost(
            "sonnet-4-5",
            input_tokens=0,
            output_tokens=0,
            cache_write_tokens=10_000,
            cache_read_tokens=5_000
        )
        expected = 0.0375 + 0.0015
        assert cost == pytest.approx(expected)

    def test_mixed_all_token_types(self):
        cost = _calculate_total_cost(
            "sonnet-4-5",
            input_tokens=50_000,
            output_tokens=25_000,
            cache_write_tokens=10_000,
            cache_read_tokens=5_000
        )
        expected = 0.15 + 0.375 + 0.0375 + 0.0015
        assert cost == pytest.approx(expected)

    def test_tier_break_boundary_with_cache(self):
        # Cache tokens push total input just over tier_break
        cost = _calculate_total_cost(
            "sonnet-4-5",
            input_tokens=190_000,
            output_tokens=0,
            cache_write_tokens=10_001,
            cache_read_tokens=0
        )
        expected = 1.14 + 0.0750075
        assert cost == pytest.approx(expected)


class TestModelPricingAttributes:
    """Verify ModelPricing dataclass structure"""

    def test_sonnet_has_tier_fields(self):
        pricing = _get_pricing("sonnet-4-5")
        assert pricing.tiered == True
        assert pricing.tier_break == 200_000
        assert pricing.input_tier == 6.00
        assert pricing.output_tier == 22.50
        assert pricing.cache_write_tier == 7.50
        assert pricing.cache_read_tier == 0.60

    def test_opus_tier_fields_none(self):
        pricing = _get_pricing("opus-4-5")
        assert pricing.tiered == False
        assert pricing.tier_break is None
        assert pricing.input_tier is None

    def test_haiku_tier_fields_none(self):
        pricing = _get_pricing("haiku-4-5")
        assert pricing.tiered == False
        assert pricing.tier_break is None


class TestCostCalculationConsistency:
    """Verify deterministic and consistent cost calculations"""

    def test_same_inputs_same_output(self):
        cost1 = _calculate_total_cost("sonnet-4-5", 100_000, 50_000, 10_000, 5_000)
        cost2 = _calculate_total_cost("sonnet-4-5", 100_000, 50_000, 10_000, 5_000)
        assert cost1 == cost2

    def test_token_type_matters_not_order(self):
        # Different input/cache splits should produce different costs
        cost1 = _calculate_total_cost("sonnet-4-5", 100_000, 50_000, 50_000, 0)
        cost2 = _calculate_total_cost("sonnet-4-5", 50_000, 50_000, 100_000, 0)

        expected1 = (100_000/1e6)*3.00 + (50_000/1e6)*15.00 + (50_000/1e6)*3.75
        expected2 = (50_000/1e6)*3.00 + (50_000/1e6)*15.00 + (100_000/1e6)*3.75

        assert cost1 == pytest.approx(expected1)
        assert cost2 == pytest.approx(expected2)
        assert cost1 != cost2  # Different token types have different rates
