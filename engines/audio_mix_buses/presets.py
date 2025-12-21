from typing import Dict
from engines.audio_mix_buses.models import MixGraph, BusConfig

MIX_GRAPHS: Dict[str, MixGraph] = {
    "default_mix": MixGraph(
        id="default_mix",
        name="Lane A Default Mix",
        buses=[
            BusConfig(
                id="bus_dialogue", name="Dialogue",
                roles=["vox", "lead", "backing", "voice", "dialogue", "talk"],
                gain_db=0.0
            ),
            BusConfig(
                id="bus_drums", name="Drums",
                roles=["kick", "snare", "hat", "tom", "cymbals", "percs", "drums"],
                gain_db=0.0
            ),
            BusConfig(
                id="bus_bass", name="Bass",
                roles=["bass", "sub", "808"],
                gain_db=0.0
            ),
            BusConfig(
                id="bus_music", name="Music",
                roles=["keys", "pad", "synth", "guitar", "piano", "strings", "brass"],
                gain_db=-1.0
            ),
            BusConfig(
                id="bus_fx", name="FX",
                roles=["fx", "riser", "impact", "atm", "sfx"],
                gain_db=-2.0
            ),
            BusConfig(
                id="bus_ambience", name="Ambience",
                roles=["ambience", "pads", "field", "atmo"],
                gain_db=-3.0
            )
        ],
        master_gain_db=0.0
    )
}
