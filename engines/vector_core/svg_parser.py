from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from engines.vector_core.models import (
    BooleanOperation,
    CircleNode,
    GroupNode,
    PathNode,
    RectNode,
    VectorNode,
    VectorScene,
    VectorStyle,
    VectorTransform,
)


class SVGParser:
    def parse(self, content: str, tenant_id: str, env: str) -> VectorScene:
        root = ET.fromstring(content)
        width = float(self._strip_px(root.attrib.get("width", "1920")))
        height = float(self._strip_px(root.attrib.get("height", "1080")))

        scene = VectorScene(tenant_id=tenant_id, env=env, width=width, height=height)
        scene.root.children = self._parse_children(root)
        return scene

    def _parse_children(self, element: ET.Element) -> List[VectorNode]:
        nodes: List[VectorNode] = []
        for child in element:
            tag = child.tag.split("}")[-1]
            style = self._parse_style(child)
            transform = self._parse_transform(child.attrib.get("transform", ""))
            node: Optional[VectorNode] = None
            node_id = child.attrib.get("id")

            if tag == "g":
                node = GroupNode(style=style, transform=transform)
                node.children = self._parse_children(child)
            elif tag == "rect":
                w = float(child.attrib.get("width", "0"))
                h = float(child.attrib.get("height", "0"))
                x = float(child.attrib.get("x", "0"))
                y = float(child.attrib.get("y", "0"))
                transform.x += x
                transform.y += y
                node = RectNode(width=w, height=h, style=style, transform=transform)
            elif tag == "circle":
                r = float(child.attrib.get("r", "0"))
                cx = float(child.attrib.get("cx", "0"))
                cy = float(child.attrib.get("cy", "0"))
                transform.x += cx - r
                transform.y += cy - r
                node = CircleNode(radius=r, style=style, transform=transform)
            elif tag == "path":
                d = child.attrib.get("d", "")
                points, closed = self._parse_path(d)
                node = PathNode(points=points, closed=closed, style=style, transform=transform)

            if node and node_id:
                node.id = node_id
            if node:
                nodes.append(node)
        return nodes

    def _parse_style(self, element: ET.Element) -> VectorStyle:
        style = VectorStyle()
        if "fill" in element.attrib:
            style.fill_color = element.attrib["fill"]
        if "stroke" in element.attrib:
            style.stroke_color = element.attrib["stroke"]
        if "stroke-width" in element.attrib:
            style.stroke_width = float(element.attrib["stroke-width"])
        if "opacity" in element.attrib:
            style.opacity = float(element.attrib["opacity"])
        return style

    def _parse_transform(self, attr: str) -> VectorTransform:
        transform = VectorTransform()
        for match in re.finditer(r"([a-zA-Z]+)\(([^)]+)\)", attr):
            name = match.group(1)
            params = [float(v) for v in re.split(r"[ ,]+", match.group(2).strip()) if v]
            if name == "translate":
                transform.x += params[0]
                if len(params) > 1:
                    transform.y += params[1]
            elif name == "scale":
                transform.scale_x *= params[0]
                transform.scale_y *= params[1] if len(params) > 1 else params[0]
            elif name == "rotate":
                transform.rotation += params[0]
        return transform

    def _parse_path(self, data: str):
        tokens = re.findall(r"[A-Za-z]|-?\d+\.?\d*", data)
        points: List[Tuple[float, float]] = []
        closed = False
        pending: List[float] = []
        cmd: Optional[str] = None
        for token in tokens:
            if token.isalpha():
                cmd = token.upper()
                if cmd == "Z":
                    closed = True
                pending = []
                continue
            pending.append(float(token))
            if len(pending) >= 2 and cmd in {"M", "L"}:
                x, y = pending[:2]
                points.append((x, y))
                pending = []
        return points, closed

    def _strip_px(self, value: str) -> str:
        return value.replace("px", "")


class SVGExporter:
    def export(self, scene: VectorScene) -> str:
        lines = [
            f'<svg width="{scene.width}" height="{scene.height}" xmlns="http://www.w3.org/2000/svg">'
        ]
        lines.extend(self._export_node(scene.root))
        lines.append("</svg>")
        return "\n".join(lines)

    def _export_node(self, node: VectorNode) -> List[str]:
        lines: List[str] = []
        attrs = []
        if node.style.fill_color:
            attrs.append(f'fill="{node.style.fill_color}"')
        if node.style.stroke_color:
            attrs.append(f'stroke="{node.style.stroke_color}"')
            attrs.append(f'stroke-width="{node.style.stroke_width}"')
        if node.style.opacity != 1.0:
            attrs.append(f'opacity="{node.style.opacity}"')

        if any((node.transform.x, node.transform.y, node.transform.rotation != 0.0, node.transform.scale_x != 1.0, node.transform.scale_y != 1.0)):
            attrs.append(self._transform_attr(node.transform))

        attr_str = " ".join(attrs)
        if isinstance(node, GroupNode):
            lines.append(f"<g {attr_str}>".strip())
            for child in node.children:
                lines.extend(self._export_node(child))
            lines.append("</g>")
        elif isinstance(node, RectNode):
            lines.append(
                f'<rect x="{node.transform.x}" y="{node.transform.y}" width="{node.width}" height="{node.height}" {attr_str} />'.strip()
            )
        elif isinstance(node, CircleNode):
            cx = node.transform.x + node.radius
            cy = node.transform.y + node.radius
            lines.append(
                f'<circle cx="{cx}" cy="{cy}" r="{node.radius}" {attr_str} />'.strip()
            )
        elif isinstance(node, PathNode):
            d = " ".join(f"{x},{y}" for x, y in node.points)
            if node.closed:
                d += " Z"
            lines.append(f'<path d="{d}" {attr_str} />'.strip())
        return lines

    def _transform_attr(self, transform: VectorTransform) -> str:
        parts = []
        if transform.x or transform.y:
            parts.append(f"translate({transform.x},{transform.y})")
        if transform.rotation:
            parts.append(f"rotate({transform.rotation})")
        if transform.scale_x != 1.0 or transform.scale_y != 1.0:
            parts.append(f"scale({transform.scale_x},{transform.scale_y})")
        return f'transform="{" ".join(parts)}"'
