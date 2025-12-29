from typing import Dict
from engines.audio_structure_engine.models import StructureTemplate, StructureSection

STRUCTURE_TEMPLATES: Dict[str, StructureTemplate] = {
    "pop_structure_1": StructureTemplate(
        id="pop_structure_1",
        name="Pop Standard",
        sections=[
            StructureSection(name="Intro", bars=4, active_roles=["hat", "fx"]),
            StructureSection(name="Verse 1", bars=8, active_roles=["kick", "snare", "hat"]),
            StructureSection(name="Chorus 1", bars=8, active_roles=["kick", "snare", "hat", "percs", "fx"]),
            StructureSection(name="Verse 2", bars=8, active_roles=["kick", "snare", "hat"]),
            StructureSection(name="Chorus 2", bars=16, active_roles=["kick", "snare", "hat", "percs", "fx"]), # Double chorus
            StructureSection(name="Outro", bars=4, active_roles=["hat", "fx"])
        ]
    )
}
