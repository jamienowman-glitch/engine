"""
PERLIN NOISE UTILS
------------------
Pure Python 2D Noise.
"""
import math
import random

# Permutation table
_P = [x for x in range(256)]
random.shuffle(_P)
_P = _P * 2

def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def _lerp(t, max_val, min_val): # Wrong arg order but standard lerp is a + t(b-a)
    return max_val + t * (min_val - max_val)

def _grad(hash_val, x, y):
    h = hash_val & 15
    grad_x = 1 + (h & 7) 
    if (h & 8): grad_x = -grad_x
    grad_y = 1 + (h & 7) # Should use different method?
    # Standard:
    # h & 1: u < v ? x : y
    # h & 2: v < u ? y : x (etc)
    # Simple Unit Vect approach
    u = x if h < 8 else y
    v = y if h < 4 else (x if h==12 or h==14 else 0)
    return ((u if (h&1)==0 else -u) + (v if (h&2)==0 else -v))

def perlin_2d(x, y):
    """Calculates 2D Perlin Noise at x,y."""
    X = int(math.floor(x)) & 255
    Y = int(math.floor(y)) & 255
    
    xf = x - math.floor(x)
    yf = y - math.floor(y)
    
    u = _fade(xf)
    v = _fade(yf)
    
    aaa = _P[_P[X]+Y]
    aba = _P[_P[X]+Y+1]
    baa = _P[_P[X+1]+Y]
    bba = _P[_P[X+1]+Y+1]
    
    g1 = _grad(aaa, xf, yf)
    g2 = _grad(baa, xf-1, yf)
    g3 = _grad(aba, xf, yf-1)
    g4 = _grad(bba, xf-1, yf-1)
    
    l1 = (1.0 - u)*g1 + u*g2
    l2 = (1.0 - u)*g3 + u*g4
    
    res = (1.0 - v)*l1 + v*l2
    return (res + 1.0) / 2.0 # Normalize 0-1
