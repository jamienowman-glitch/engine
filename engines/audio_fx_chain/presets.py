from typing import Dict, Any, List

# Structure: 
# { 
#   "preset_id": {
#       "hpf_hz": 80,
#       "lpf_hz": 18000,
#       "eq": [ {"f": 200, "g": -2, "q": 1.0, "type": "bell"} ],
#       "comp": { "thresh": -12, "ratio": 4, "attack": 5, "release": 50, "makeup": 2},
#       "sat": { "type": "soft", "drive": 0.1 },
#       "reverb": None,
#       "limiter": { "thresh": -1.0 }
#   }
# }

FX_PRESETS: Dict[str, Dict[str, Any]] = {
    "clean_hit": {
        "hpf_hz": 60,
        "lpf_hz": 20000,
        "eq": [
            {"f": 300, "g": -3, "q": 1.5, "type": "bell"} # Cleanup mud
        ],
        "comp": {"thresh": -15, "ratio": 3, "attack": 10, "release": 100, "makeup": 2},
        "sat": None,
        "limiter": {"thresh": -0.5}
    },
    "lofi_crunch": {
        "hpf_hz": 300,
        "lpf_hz": 6000,
        "comp": {"thresh": -20, "ratio": 8, "attack": 2, "release": 200, "makeup": 6},
        "sat": {"type": "hard", "drive": 0.5},
        "limiter": {"thresh": -1.0}
    },
    "bright_snare": {
        "hpf_hz": 120,
        "eq": [
            {"f": 200, "g": -2, "q": 1.0, "type": "bell"},
            {"f": 5000, "g": 4, "q": 0.7, "type": "highshelf"}
        ],
        "comp": {"thresh": -10, "ratio": 4, "attack": 15, "release": 80, "makeup": 1},
        "sat": {"type": "soft", "drive": 0.1},
        "limiter": {"thresh": -0.5}
    },
    "warm_pad": {
        "hpf_hz": 100,
        "lpf_hz": 8000,
        "eq": [
            {"f": 800, "g": -2, "q": 2.0, "type": "bell"}
        ],
        "comp": {"thresh": -18, "ratio": 2.5, "attack": 50, "release": 500, "makeup": 3},
        "reverb": {"decay": 2.5, "mix": 0.3},
        "limiter": {"thresh": -2.0}
    },
    "vocal_presence": {
        "hpf_hz": 90,
        "eq": [
            {"f": 3000, "g": 2, "q": 1.0, "type": "bell", "width_type": "h"},
            {"f": 10000, "g": 1, "q": 0.7, "type": "highshelf"}
        ],
        "comp": {"thresh": -16, "ratio": 3, "attack": 20, "release": 150, "makeup": 3},
        "limiter": {"thresh": -1.0}
    },
    "bass_glue": {
        "hpf_hz": 30, 
        "lpf_hz": 15000,
        "comp": {"thresh": -12, "ratio": 5, "attack": 30, "release": 100, "makeup": 1},
        "sat": {"type": "soft", "drive": 0.2},
        "limiter": {"thresh": -0.2}
    },
    "sub_rumble": {
        "hpf_hz": 20,
        "lpf_hz": 150,
        "sat": {"type": "cubic", "drive": 0.8},
        "comp": {"thresh": -10, "ratio": 6, "attack": 80, "release": 200, "makeup": 4},
        "limiter": {"thresh": -0.5}
    },
    "tape_warmth": {
        "hpf_hz": 40,
        "lpf_hz": 16000,
        "sat": {"type": "soft", "drive": 0.3},
        "comp": {"thresh": -12, "ratio": 2, "attack": 10, "release": 200, "makeup": 1},
        "limiter": {"thresh": -0.5}
    },
    "wide_chorus": {
        # Using EQ to differentiate mid/side or just simple filters for now as width not fully impl
        "hpf_hz": 150,
        "eq": [
             {"f": 500, "g": -2, "q": 0.5, "type": "bell"},
             {"f": 8000, "g": 2, "q": 0.7, "type": "highshelf"}
        ],
        "reverb": {"decay": 1.5, "mix": 0.4},
        "limiter": {"thresh": -1.0}
    },
    "transient_snap": {
        # Slow attack to let transient through, fast release
        "comp": {"thresh": -15, "ratio": 4, "attack": 40, "release": 50, "makeup": 3},
        "eq": [
            {"f": 2000, "g": 3, "q": 1.5, "type": "bell"}
        ],
        "limiter": {"thresh": -0.2}
    },
    "saturation_sizzle": {
        "hpf_hz": 80,
        "lpf_hz": 12000,
        "eq": [
            {"f": 250, "g": -1.5, "q": 1.2, "type": "bell"},
            {"f": 6000, "g": 2.5, "q": 0.8, "type": "highshelf"}
        ],
        "comp": {"thresh": -12, "ratio": 3.5, "attack": 8, "release": 110, "makeup": 2},
        "sat": {"type": "soft", "drive": 0.35},
        "limiter": {"thresh": -0.8}
    },
    "delay_dream": {
        "hpf_hz": 100,
        "lpf_hz": 18000,
        "eq": [
            {"f": 400, "g": -2, "q": 1.3, "type": "bell"},
        ],
        "comp": {"thresh": -16, "ratio": 2.2, "attack": 25, "release": 200, "makeup": 1},
        "reverb": {"decay": 3.0, "mix": 0.45},
        "limiter": {"thresh": -1.2}
    },
    "wide_spread": {
        "hpf_hz": 120,
        "lpf_hz": 15000,
        "eq": [
            {"f": 600, "g": -2, "q": 0.8, "type": "bell"},
            {"f": 9000, "g": 3, "q": 0.6, "type": "highshelf"}
        ],
        "reverb": {"decay": 1.2, "mix": 0.35},
        "limiter": {"thresh": -0.8}
    },
    "ambient_tail": {
        "hpf_hz": 60,
        "lpf_hz": 10000,
        "eq": [
            {"f": 800, "g": -1, "q": 1.5, "type": "bell"}
        ],
        "reverb": {"decay": 4.0, "mix": 0.55},
        "sat": {"type": "soft", "drive": 0.25},
        "limiter": {"thresh": -1.5}
    }
}

FX_PRESET_METADATA: Dict[str, Dict[str, Any]] = {
    "clean_hit": {"intensity": 0.4, "latency_ms": 8},
    "lofi_crunch": {"intensity": 0.8, "latency_ms": 12},
    "bright_snare": {"intensity": 0.5, "latency_ms": 6},
    "warm_pad": {"intensity": 0.35, "latency_ms": 20},
    "vocal_presence": {"intensity": 0.6, "latency_ms": 5},
    "bass_glue": {"intensity": 0.6, "latency_ms": 9},
    "sub_rumble": {"intensity": 0.9, "latency_ms": 4},
    "tape_warmth": {"intensity": 0.45, "latency_ms": 18},
    "wide_chorus": {"intensity": 0.55, "latency_ms": 25},
    "transient_snap": {"intensity": 0.65, "latency_ms": 3},
    "saturation_sizzle": {"intensity": 0.7, "latency_ms": 10},
    "delay_dream": {"intensity": 0.5, "latency_ms": 30},
    "wide_spread": {"intensity": 0.4, "latency_ms": 28},
    "ambient_tail": {"intensity": 0.35, "latency_ms": 40},
}
