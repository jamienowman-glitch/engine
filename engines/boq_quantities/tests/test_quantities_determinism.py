"""
Tests for BoQ scope tagging and deterministic output.
"""

import pytest
from engines.cad_semantics.models import SemanticElement, SemanticModel, SemanticType, Level
from engines.boq_quantities.service import BoQQuantitiesService

def create_elem(id: str, type: SemanticType, level_id: str, zone: str = None) -> SemanticElement:
    return SemanticElement(
        id=id, cad_entity_id=f"cad_{id}", semantic_type=type, layer="L",
        geometry_ref={"length": 5000, "height": 3000, "area": 15000000}, # valid geometry for wall/slab
        level_id=level_id,
        attributes={"zone": zone} if zone else {}
    )

class TestQuantitiesDeterminism:
    
    def test_scope_tagging(self):
        """Verify items are tagged with correct scope (Level + Zone) and aggregated."""
        service = BoQQuantitiesService()
        
        # Elements: 
        # - Wall 1 on L1, Zone A
        # - Wall 2 on L1, Zone B
        # - Wall 3 on L1 (no zone)
        # - Slab 1 on L2 (no zone)
        
        w1 = create_elem("w1", SemanticType.WALL, "L1", "Zone A")
        w2 = create_elem("w2", SemanticType.WALL, "L1", "Zone B")
        w3 = create_elem("w3", SemanticType.WALL, "L1", None)
        s1 = create_elem("s1", SemanticType.SLAB, "L2", None)
        
        model = SemanticModel(
            cad_model_id="c1",
            elements=[w1, w2, w3, s1],
            levels=[
                Level(id="L1", name="Ground Floor", elevation=0, index=0),
                Level(id="L2", name="Level 1", elevation=3000, index=1),
            ]
        )
        
        boq, _ = service.quantify(model)
        
        # Should have 4 scopes:
        # 1. L1 - Zone A
        # 2. L1 - Zone B
        # 3. L1 (default)
        # 4. L2 (default)
        
        scope_names = {s.scope_name for s in boq.scopes}
        assert "Ground Floor - Zone A" in scope_names
        assert "Ground Floor - Zone B" in scope_names
        assert "Ground Floor" in scope_names
        assert "Level 1" in scope_names
        
        # Check totals
        # W1 area: 5*3 = 15m2 -> Zone A total should be 15
        zone_a = next(s for s in boq.scopes if s.scope_name == "Ground Floor - Zone A")
        assert zone_a.total_area == 15.0
        
        # Check items scope linkage
        item_w1 = next(i for i in boq.items if "w1" in i.source_element_ids[0])
        assert item_w1.scope_id == zone_a.scope_id
        assert item_w1.zone_tag == "Zone A"

    def test_determinism_sort_and_hash(self):
        """Verify that item order input doesn't affect output order or hash."""
        service = BoQQuantitiesService()
        
        e1 = create_elem("e1", SemanticType.WALL, "L1")
        e2 = create_elem("e2", SemanticType.WALL, "L1")
        e3 = create_elem("e3", SemanticType.DOOR, "L1")
        
        # Run 1: Order 1
        model1 = SemanticModel(cad_model_id="c1", elements=[e1, e2, e3], levels=[Level(id="L1", name="L1", elevation=0)])
        boq1, _ = service.quantify(model1)
        
        # Run 2: Shuffled input
        model2 = SemanticModel(cad_model_id="c1", elements=[e3, e2, e1], levels=[Level(id="L1", name="L1", elevation=0)])
        boq2, _ = service.quantify(model2)
        
        # Check integrity
        assert boq1.model_hash == boq2.model_hash
        assert len(boq1.items) == len(boq2.items)
        
        # Items should be sorted by (type, id)
        # Type order: Door < Wall? Alphabetical?
        # Door vs Wall. 'd' < 'w'. So Door first.
        assert boq1.items[0].element_type == "door"
        assert boq1.items[1].element_type == "wall"
        assert boq1.items[2].element_type == "wall"
        
        # ID sort within type
        # e1 vs e2. e1 id="e1", e2 id="e2".
        # But item IDs are hashes of element ID.
        # "e1" vs "e2".
        # We rely on sort.
        ids1 = [i.id for i in boq1.items]
        ids2 = [i.id for i in boq2.items]
        assert ids1 == ids2
