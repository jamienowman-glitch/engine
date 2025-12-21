from typing import Dict
from engines.audio_macro_engine.models import MacroDefinition, MacroNode

MACRO_DEFINITIONS: Dict[str, MacroDefinition] = {
    "reverse_swell": MacroDefinition(
        id="reverse_swell",
        nodes=[
            MacroNode(type="reverse"),
            MacroNode(type="reverb", params={"in_gain": 0.6, "out_gain": 0.3, "delays": 1000, "decays": 0.5}),
            MacroNode(type="limiter", params={"input": 3.0}) # Boost then limit
        ]
    ),
    "impact_crunch": MacroDefinition(
        id="impact_crunch",
        nodes=[
            MacroNode(type="distortion", params={"drive": 20.0, "gain": 5.0}),
            MacroNode(type="lowpass", params={"freq": 3000}),
            MacroNode(type="reverb", params={"in_gain": 0.8, "out_gain": 0.2, "delays": 200, "decays": 0.3}),
            MacroNode(type="limiter", params={"input": 0.0})
        ]
    ),
    "ethereal_wash": MacroDefinition(
        id="ethereal_wash",
        nodes=[
             MacroNode(type="reverb", params={"in_gain": 0.8, "out_gain": 0.8, "delays": 2000, "decays": 0.8}),
             MacroNode(type="reverse"), # Reverse the reverb
             MacroNode(type="limiter")
        ]
    ),
    "sparkle_tap": MacroDefinition(
        id="sparkle_tap",
        nodes=[
            MacroNode(type="distortion", params={"drive": 15.0, "gain": 5.0}),
            MacroNode(type="reverb", params={"in_gain": 0.7, "out_gain": 0.4, "delays": 450, "decays": 0.4}),
            MacroNode(type="lowpass", params={"freq": 8000}),
            MacroNode(type="limiter", params={"input": 1.5})
        ],
        meta={"intensity": 0.6}
    ),
    "breathing_cloud": MacroDefinition(
        id="breathing_cloud",
        nodes=[
            MacroNode(type="lowpass", params={"freq": 9000}),
            MacroNode(type="reverb", params={"in_gain": 0.6, "out_gain": 0.5, "delays": 1800, "decays": 0.7}),
            MacroNode(type="reverse"),
            MacroNode(type="limiter", params={"input": 0.8})
        ],
        meta={"intensity": 0.4}
    ),
    "tight_snap": MacroDefinition(
        id="tight_snap",
        nodes=[
            MacroNode(type="distortion", params={"drive": 12.0, "gain": 3.5}),
            MacroNode(type="lowpass", params={"freq": 4000}),
            MacroNode(type="limiter", params={"input": 0.1})
        ],
        meta={"intensity": 0.7}
    )
}
