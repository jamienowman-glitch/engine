"""
Test fixtures for CAD ingest tests.

Provides sample DXF and IFC-lite files for testing.
"""

import json


# Simple DXF floorplan fixture
DXF_FLOORPLAN_FIXTURE = b"""0
SECTION
2
HEADER
9
$UNITS
70
4
9
$EXTMIN
10
0.0
20
0.0
9
$EXTMAX
10
100.0
20
100.0
0
ENDSEC
0
SECTION
2
TABLES
0
TABLE
2
LAYER
70
1
0
LAYER
2
Wall
62
5
0
LAYER
2
Door
62
1
0
LAYER
2
Window
62
3
0
ENDTAB
0
ENDSEC
0
SECTION
2
ENTITIES
0
LINE
5
1
8
Wall
10
0.0
20
0.0
30
0.0
11
100.0
21
0.0
31
0.0
0
LINE
5
2
8
Wall
10
100.0
20
0.0
30
0.0
11
100.0
21
100.0
31
0.0
0
LINE
5
3
8
Wall
10
100.0
20
100.0
30
0.0
11
0.0
21
100.0
31
0.0
0
LINE
5
4
8
Wall
10
0.0
20
100.0
30
0.0
11
0.0
21
0.0
31
0.0
0
CIRCLE
5
5
8
Door
10
50.0
20
10.0
40
2.0
0
CIRCLE
5
6
8
Window
10
75.0
20
50.0
40
3.0
0
0
ENDSEC
0
EOF
"""

# Simple IFC-lite fixture (JSON format)
IFC_LITE_FIXTURE = {
    "units": "mm",
    "elements": [
        {
            "id": "W1",
            "type": "Wall",
            "layer": "Walls",
            "geometry": {
                "x": 0.0,
                "y": 0.0,
                "z": 0.0,
                "width": 100.0,
                "height": 3000.0,
                "length": 300.0,
            },
            "placement": {"location": {"x": 0, "y": 0, "z": 0}},
        },
        {
            "id": "W2",
            "type": "Wall",
            "layer": "Walls",
            "geometry": {
                "x": 100.0,
                "y": 0.0,
                "z": 0.0,
                "width": 100.0,
                "height": 3000.0,
                "length": 100.0,
            },
            "placement": {"location": {"x": 0, "y": 0, "z": 0}},
        },
        {
            "id": "S1",
            "type": "Slab",
            "layer": "Floors",
            "geometry": {
                "x": 50.0,
                "y": 50.0,
                "z": 0.0,
                "width": 100.0,
                "height": 100.0,
                "length": 200.0,
            },
            "placement": {"location": {"x": 0, "y": 0, "z": 0}},
        },
    ],
    "layers": [{"name": "Walls"}, {"name": "Floors"}],
}

IFC_LITE_FIXTURE_JSON = json.dumps(IFC_LITE_FIXTURE).encode("utf-8")
