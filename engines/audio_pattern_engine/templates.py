from typing import Dict, List
from engines.audio_pattern_engine.models import PatternTemplate, PatternTrackTemplate

# Helper to create steps easily
def steps_16(indices: List[int], velocity: float = 1.0) -> List[float]:
    s = [0.0] * 16
    for i in indices:
        if 0 <= i < 16:
            s[i] = velocity
    return s

def steps_fill(velocity: float = 1.0) -> List[float]:
    return [velocity] * 16

TEMPLATES: Dict[str, PatternTemplate] = {
    "four_on_the_floor": PatternTemplate(
        id="four_on_the_floor",
        name="House Basic",
        bpm_default=124.0,
        swing_default=0.0,
        tracks=[
            PatternTrackTemplate(role="kick", steps=steps_16([0, 4, 8, 12], 1.0)),
            PatternTrackTemplate(role="snare", steps=steps_16([4, 12], 0.9)), # Clap/Snare on 2 and 4
            PatternTrackTemplate(role="hat", steps=steps_16([2, 6, 10, 14], 0.7)), # Off-beat hat
        ]
    ),
    "boom_bap_90": PatternTemplate(
        id="boom_bap_90",
        name="Boom Bap",
        bpm_default=90.0,
        swing_default=25.0, # Slight MPC swing
        tracks=[
            PatternTrackTemplate(role="kick", steps=steps_16([0, 2, 7, 10], 1.0)), # Kick pattern
            PatternTrackTemplate(role="snare", steps=steps_16([4, 12], 1.0)),
            PatternTrackTemplate(role="hat", steps=steps_fill(0.6)), # 8th notes or 16ths? 16ths for swing test
        ]
    ),
    "trap_140": PatternTemplate(
        id="trap_140",
        name="Trap Basic",
        bpm_default=140.0,
        swing_default=0.0,
        tracks=[
            PatternTrackTemplate(role="kick", steps=steps_16([0, 8], 1.0)),
            PatternTrackTemplate(role="snare", steps=steps_16([8], 1.0)), # Snare on 3 (step 8 of 16? wait. 4/4 16ths: 0, 4, 8, 12 are beats 1,2,3,4. Snare on 3 is index 8.)
            PatternTrackTemplate(role="hat", steps=steps_fill(0.8)), # Rolling hats
        ]
    )
}
