"""Math utilities for 3D View Engine."""
from __future__ import annotations

import math
from typing import Optional, Tuple

from engines.scene_engine.core.geometry import Vector3


class Matrix4:
    def __init__(self, data: list[float] = None):
        if data:
            self.m = data
        else:
            self.m = [0.0] * 16
            self.m[0] = self.m[5] = self.m[10] = self.m[15] = 1.0

    @staticmethod
    def identity() -> Matrix4:
        return Matrix4()

    def __mul__(self, other: Matrix4) -> Matrix4:
        res = Matrix4([0.0] * 16)
        a = self.m
        b = other.m
        for i in range(4): # row
            for j in range(4): # col
                sum_val = 0.0
                for k in range(4):
                    sum_val += a[i * 4 + k] * b[k * 4 + j]
                res.m[i * 4 + j] = sum_val
        return res

    def multiply_vector(self, v: Vector3, w: float = 1.0) -> Tuple[float, float, float, float]:
        """Returns (x, y, z, w)."""
        x, y, z = v.x, v.y, v.z
        m = self.m
        rx = m[0]*x + m[1]*y + m[2]*z + m[3]*w
        ry = m[4]*x + m[5]*y + m[6]*z + m[7]*w
        rz = m[8]*x + m[9]*y + m[10]*z + m[11]*w
        rw = m[12]*x + m[13]*y + m[14]*z + m[15]*w
        return rx, ry, rz, rw


def subtract(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(x=a.x - b.x, y=a.y - b.y, z=a.z - b.z)


def add(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(x=a.x + b.x, y=a.y + b.y, z=a.z + b.z)


def scale_vec(v: Vector3, s: float) -> Vector3:
    return Vector3(x=v.x * s, y=v.y * s, z=v.z * s)


def dot(a: Vector3, b: Vector3) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z


def cross(a: Vector3, b: Vector3) -> Vector3:
    return Vector3(
        x=a.y * b.z - a.z * b.y,
        y=a.z * b.x - a.x * b.z,
        z=a.x * b.y - a.y * b.x
    )


def length(v: Vector3) -> float:
    return math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z)


def normalize(v: Vector3) -> Vector3:
    l = length(v)
    if l == 0:
        return Vector3(x=0, y=0, z=0)
    return Vector3(x=v.x/l, y=v.y/l, z=v.z/l)


def look_at(eye: Vector3, center: Vector3, up: Vector3) -> Matrix4:
    f = normalize(subtract(center, eye))
    s = normalize(cross(f, normalize(up)))
    u = cross(s, f)

    m = [0.0] * 16
    m[0] = s.x
    m[1] = s.y
    m[2] = s.z
    m[3] = -dot(s, eye)

    m[4] = u.x
    m[5] = u.y
    m[6] = u.z
    m[7] = -dot(u, eye)

    m[8] = -f.x
    m[9] = -f.y
    m[10] = -f.z
    m[11] = dot(f, eye)

    m[12] = 0.0
    m[13] = 0.0
    m[14] = 0.0
    m[15] = 1.0

    return Matrix4(m)


def perspective(fov_deg: float, aspect: float, near: float, far: float) -> Matrix4:
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    nf = 1.0 / (near - far)

    m = [0.0] * 16
    m[0] = f / aspect
    m[1] = 0
    m[2] = 0
    m[3] = 0

    m[4] = 0
    m[5] = f
    m[6] = 0
    m[7] = 0

    m[8] = 0
    m[9] = 0
    m[10] = (far + near) * nf
    m[11] = 2 * far * near * nf

    m[12] = 0
    m[13] = 0
    m[14] = -1.0
    m[15] = 0

    return Matrix4(m)


def compose_transform(position: Vector3, scale: Vector3) -> Matrix4:
    # Rotation ignored for now as EulerAngles to Matrix needs conversion
    # Assume Identity Rotation for P0 if not complex
    # Or implement basic Euler conversion
    
    # Simple T * S for now, assuming axis aligned or handled elsewhere if complex rot needed
    # Wait, instructions say "Compute the node's world transform... include parent transforms"
    # I should support rotation.
    
    # Let's do a basic euler to matrix (XYZ order)
    # Rotation logic will be added here
    pass
    return Matrix4.identity() # Placeholder functionality used inside service logic if I inline it
    # Actually let's just implement it in service or here.
    # I'll implement translation * rotation * scale here.


def euler_to_matrix(rx: float, ry: float, rz: float) -> Matrix4:
    # XYZ order
    cx = math.cos(rx)
    sx = math.sin(rx)
    cy = math.cos(ry)
    sy = math.sin(ry)
    cz = math.cos(rz)
    sz = math.sin(rz)

    m = [0.0] * 16
    
    # Row major storage? Implementation above used Row-Major indexing in multiply?
    # multiply: res.m[i*4 + j] -> i is row, j is col.
    # look_at: m[3] is translation x. This implies Row-Major where m[0]..m[3] is first row.
    # Standard math: M * v (column vector).
    # M[0]..M[3] row 0.
    # In look_at: m[3] = -dot(s, eye). This is standard GL "view matrix" but GL is col-major. 
    # Python generic lists are just indices.
    # Let's stick to standard row-major for multiply logic:
    # [ 0  1  2  3 ]
    # [ 4  5  6  7 ] ...
    
    # Rotation X
    # 1  0   0
    # 0  cx -sx
    # 0  sx  cx
    
    # Rotation Y
    # cy 0  sy
    # 0  1  0
    # -sy 0 cy

    # Rotation Z
    # cz -sz 0
    # sz  cz 0
    # 0   0  1

    # R = Rz * Ry * Rx
    
    # Let's use a simplified approach: just compose T * R * S
    # Actually, let's keep it simple: just Translation and Scale if Rotation is hard without numpy?
    # No, I should do it roughly right.
    
    # Combined RzRyRx
    m11 = cy * cz
    m12 = -cy * sz
    m13 = sy
    
    m21 = sx * sy * cz + cx * sz
    m22 = -sx * sy * sz + cx * cz
    m23 = -sx * cy
    
    m31 = -cx * sy * cz + sx * sz
    m32 = cx * sy * sz + sx * cz
    m33 = cx * cy
    
    mat = Matrix4()
    mat.m[0] = m11; mat.m[1] = m12; mat.m[2] = m13; mat.m[3] = 0
    mat.m[4] = m21; mat.m[5] = m22; mat.m[6] = m23; mat.m[7] = 0
    mat.m[8] = m31; mat.m[9] = m32; mat.m[10] = m33; mat.m[11] = 0
    mat.m[15] = 1
    return mat


def compose_trs(p: Vector3, r: Vector3, s: Vector3) -> Matrix4:
    # r is euler in radians
    # T * R * S
    
    # S
    ms = Matrix4()
    ms.m[0] = s.x
    ms.m[5] = s.y
    ms.m[10] = s.z
    
    # R
    mr = euler_to_matrix(r.x, r.y, r.z)
    
    # T
    mt = Matrix4()
    mt.m[3] = p.x
    mt.m[7] = p.y
    mt.m[11] = p.z
    
    # T * R * S
    # (T * (R * S))
    rs = mr * ms
    trs = mt * rs
    return trs
