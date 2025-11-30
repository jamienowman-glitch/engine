"""Atomic engine: TAG.FLOW.AUTO_V1"""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class FlowAutoRequest:
    bars: List[Dict[str, Any]]


@dataclass
class FlowAutoResponse:
    bars: List[Dict[str, Any]]
    flow_pairs: List[Dict[str, Any]]


def run(request: FlowAutoRequest) -> FlowAutoResponse:
    # TODO: port flow tagging logic in Phase 3
    return FlowAutoResponse(bars=request.bars, flow_pairs=[])
