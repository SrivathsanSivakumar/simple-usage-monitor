#!/usr/bin/env python3

# calculate tokens and dollar cost for user input in real-time
# uses Anthropic's pricing table

from __future__ import annotations
import os, json, socket, shutil, subprocess

SOCK_PATH  = os.path.expanduser(os.getenv('SOCK_PATH', '~/.cache/claude_tokend.sock'))
SONNET_INPUT_TIER_BREAK=200000
SONNET_INPUT_PRICE_LE_200K=3.00
SONNET_INPUT_PRICE_GT_200K=6.00
SONNET_OUTPUT_PRICE_LE_200K=15.00
SONNET_OUTPUT_PRICE_GE_200K=22.50
HAIKU_INPUT_PRICE=1.00
HAIKU_OUTPUT_PRICE=5.00

TOKEN_COUNTER_JS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'anthropic_est.js'
)

_node_path = shutil.which("node")

def _count_via_node(text:str):
    if not _node_path or not os.path.exists(TOKEN_COUNTER_JS):
        return str(-1)
    try:
        p = subprocess.Popen(
            [_node_path, TOKEN_COUNTER_JS],
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = p.communicate(text.encode(), timeout=0.4)
        return int((out.decode().strip() or "0"))
    
    except Exception as e:
        return e

def count_tokens(text:str) -> int:
    t = _count_via_node(text)
    if t is not None: 
        return t
    return -1

def input_cost_usd(tokens:int) -> tuple:
    """identifies tier for Sonnet4.5 and calculates pricing accordingly

        Args:
            tokens: input token count

        Returns:
            dollar cost for tokens and tier
    """
    if tokens <= SONNET_INPUT_TIER_BREAK:
        tier = "<=200k"  
    else:
        tier = ">200k"

    if tier == "<=200k":
        rate = SONNET_INPUT_PRICE_LE_200K 
    else:
        rate = SONNET_INPUT_PRICE_GT_200K
        
    return (tokens/1_000_000)*rate, tier