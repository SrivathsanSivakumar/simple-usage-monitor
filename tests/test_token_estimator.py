### unit test token estimator

import pytest
from unittest.mock import patch, Mock
from tokens.token_cost_estimator import count_via_node, count_tokens, input_cost_usd

def test_count_via_node():
    num_tokens = count_via_node('test')
    assert num_tokens > 0

def test_count_via_node_empty_string():
    num_tokens = count_via_node('')
    assert num_tokens == 0
    
@patch('tokens.token_cost_estimator._node_path', None)
def test_count_via_node_no_node_path():
    ret = count_via_node('test')
    assert ret == -1

@patch('os.path.exists', return_value=False)
def test_count_via_node_no_js_backend(mock_exists):
    ret = count_via_node('test')
    assert ret == -1

def test_count_tokens():
    ret = count_tokens('test')
    assert ret > 0

def test_input_cost_usd():
    tokens = 10
    rate, tier = input_cost_usd(tokens)
    assert rate == pytest.approx(3e-5) and tier == "<=200k"
    tokens = 200_001
    rate, tier = input_cost_usd(tokens)
    assert rate == pytest.approx(1.2, rel=1e-5) and tier == ">200k"