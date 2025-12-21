from __future__ import annotations

import math
from typing import Tuple, Sequence, Optional

from PIL import Image, ImageDraw, ImageColor

from engines.vector_core.models import (
    BooleanOperation,
    CircleNode,
    GroupNode,
    PathNode,
    RectNode,
    VectorNode,
    VectorScene,
)

try:
    from shapely.geometry import Polygon
except ImportError:  # pragma: no cover - may not exist in every env
    Polygon = None


class VectorRenderer:
    def render(self, scene: VectorScene, width: int = None, height: int = None) -> Image.Image:
        if scene.boolean_ops:
            self._apply_boolean_ops(scene)

        w = width or int(scene.width)
        h = height or int(scene.height)

        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        identity = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
        self._render_node(draw, scene.root, identity)

        return img

    def _apply_boolean_ops(self, scene: VectorScene) -> None:
        if Polygon is None:
            scene.meta["boolean_ops"] = "NOT_IMPLEMENTED"
            return

        for op in scene.boolean_ops:
            geoms = []
            for operand_id in op.operands:
                node = self._find_node_by_id(scene.root, operand_id)
                if not node:
                    continue
                geom = self._node_to_polygon(node)
                if geom:
                    geoms.append(geom)
            if len(geoms) < 2:
                continue

            base = geoms[0]
            for geom in geoms[1:]:
                if op.operation == "union":
                    base = base.union(geom)
                elif op.operation == "subtract":
                    base = base.difference(geom)
                elif op.operation == "intersect":
                    base = base.intersection(geom)

            if not base.is_empty:
                coords = list(base.exterior.coords)
                path = PathNode(points=[(float(x), float(y)) for x, y in coords], closed=True)
                if op.result_id:
                    path.id = op.result_id
                scene.root.children.append(path)
        scene.meta["boolean_ops"] = "APPLIED"

    def _find_node_by_id(self, node: VectorNode, target: str) -> VectorNode | None:
        if node.id == target:
            return node
        if isinstance(node, GroupNode):
            for child in node.children:
                found = self._find_node_by_id(child, target)
                if found:
                    return found
        return None

    def _node_to_polygon(self, node: VectorNode):
        if isinstance(node, RectNode):
            points = [
                (0, 0),
                (node.width, 0),
                (node.width, node.height),
                (0, node.height),
            ]
        elif isinstance(node, CircleNode):
            points = []
            segments = 32
            for i in range(segments):
                theta = 2 * math.pi * i / segments
                points.append((math.cos(theta) * node.radius + node.radius, math.sin(theta) * node.radius + node.radius))
        elif isinstance(node, PathNode):
            points = node.points
        else:
            return None

        matrix = node.transform.matrix()
        transformed = [self._apply_matrix(matrix, p) for p in points]
        if len(transformed) >= 3:
            return Polygon(transformed)
        return None

    def _render_node(self, draw: ImageDraw.ImageDraw, node: VectorNode, matrix: Tuple[float, float, float, float, float, float]):
        combined = self._combine_matrix(matrix, node.transform.matrix())
        if isinstance(node, GroupNode):
            for child in node.children:
                self._render_node(draw, child, combined)
            return

        fill = self._color_with_opacity(node.style.fill_color, node.style.opacity)
        stroke = self._color_with_opacity(node.style.stroke_color, node.style.opacity)
        stroke_width = max(1, int(node.style.stroke_width))

        if isinstance(node, RectNode):
            poly = self._rect_polygon(node, combined)
            self._draw_polygon(draw, poly, fill, stroke, stroke_width)
        elif isinstance(node, CircleNode):
            poly = self._circle_polygon(node, combined)
            self._draw_polygon(draw, poly, fill, stroke, stroke_width)
        elif isinstance(node, PathNode):
            poly = [self._apply_matrix(combined, point) for point in node.points]
            if node.closed and len(poly) >= 3:
                self._draw_polygon(draw, poly, fill, stroke, stroke_width)
            elif len(poly) >= 2:
                draw.line(poly, fill=stroke or fill, width=stroke_width)

    def _rect_polygon(self, node: RectNode, matrix: Tuple[float, float, float, float, float, float]):
        corners = [
            (0, 0),
            (node.width, 0),
            (node.width, node.height),
            (0, node.height),
        ]
        return [self._apply_matrix(matrix, corner) for corner in corners]

    def _circle_polygon(self, node: CircleNode, matrix: Tuple[float, float, float, float, float, float]):
        segments = 32
        points = []
        for i in range(segments):
            theta = 2 * math.pi * i / segments
            x = math.cos(theta) * node.radius + node.radius
            y = math.sin(theta) * node.radius + node.radius
            points.append(self._apply_matrix(matrix, (x, y)))
        return points

    def _draw_polygon(
        self,
        draw: ImageDraw.ImageDraw,
        points: Sequence[Tuple[float, float]],
        fill: Optional[Tuple[int, int, int, int]],
        stroke: Optional[Tuple[int, int, int, int]],
        stroke_width: int,
    ):
        if fill:
            draw.polygon(points, fill=fill)
        if stroke:
            closed = points[0] == points[-1] if points else False
            loop = points + [points[0]] if points and not closed else points
            if len(loop) >= 2:
                draw.line(loop, fill=stroke, width=stroke_width)

    def _color_with_opacity(self, color: Optional[str], opacity: float):
        if not color:
            return None
        try:
            rgb = ImageColor.getrgb(color)
        except Exception:
            return None
        alpha = int(opacity * 255)
        return (*rgb, alpha)

    def _apply_matrix(self, matrix: Tuple[float, float, float, float, float, float], point: Tuple[float, float]):
        a, b, c, d, tx, ty = matrix
        x, y = point
        return (a * x + c * y + tx, b * x + d * y + ty)

    def _combine_matrix(self, base: Tuple[float, float, float, float, float, float], overlay: Tuple[float, float, float, float, float, float]):
        a1, b1, c1, d1, tx1, ty1 = base
        a2, b2, c2, d2, tx2, ty2 = overlay
        a = a1 * a2 + c1 * b2
        b = b1 * a2 + d1 * b2
        c = a1 * c2 + c1 * d2
        d = b1 * c2 + d1 * d2
        tx = a1 * tx2 + c1 * ty2 + tx1
        ty = b1 * tx2 + d1 * ty2 + ty1
        return (a, b, c, d, tx, ty)
