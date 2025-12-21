import math
import random

from engines.animation_kernel.ik_solver import (
    solve_chain_ik,
    vec_len,
    vec_sub,
)


def vec_equal(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def initial_stretched_end(root, joint_lengths, target):
    # If target direction is zero, pick X axis
    dir_rt = (target[0] - root[0], target[1] - root[1], target[2] - root[2])
    mag = math.sqrt(dir_rt[0] ** 2 + dir_rt[1] ** 2 + dir_rt[2] ** 2)
    if mag < 1e-6:
        dir_rt = (1.0, 0.0, 0.0)
        mag = 1.0
    dir_rt = (dir_rt[0] / mag, dir_rt[1] / mag, dir_rt[2] / mag)
    pos = root
    end = (
        root[0] + dir_rt[0] * sum(joint_lengths),
        root[1] + dir_rt[1] * sum(joint_lengths),
        root[2] + dir_rt[2] * sum(joint_lengths),
    )
    return end


def test_colinear_case_improves_distance():
    root = (0.0, 0.0, 0.0)
    lengths = [1.0, 1.0, 1.0]
    target = (2.0, 0.5, 0.0)

    initial_end = initial_stretched_end(root, lengths, target)
    initial_dist = vec_len(vec_sub(initial_end, target))

    positions = solve_chain_ik(root, lengths, target, max_iters=80, tolerance=1e-6)
    end = positions[-1]
    dist = vec_len(vec_sub(end, target))

    assert dist < initial_dist - 1e-12

    # Determinism: repeat call gives identical final positions
    positions2 = solve_chain_ik(root, lengths, target, max_iters=80, tolerance=1e-6)
    assert all(vec_equal(p, q, tol=1e-9) for p, q in zip(positions, positions2))


def test_unreachable_stretches_to_max_length():
    root = (0.0, 0.0, 0.0)
    lengths = [1.0, 1.0, 1.0]
    target = (10.0, 0.0, 0.0)

    positions = solve_chain_ik(root, lengths, target)
    end = positions[-1]

    # End should be at distance equal to sum(lengths) from root in direction of target
    expected_end = initial_stretched_end(root, lengths, target)
    assert vec_len(vec_sub(end, expected_end)) < 1e-9


def test_degenerate_target_at_root():
    root = (0.0, 0.0, 0.0)
    lengths = [0.5, 0.7, 1.2]
    target = (0.0, 0.0, 0.0)

    positions = solve_chain_ik(root, lengths, target)
    end = positions[-1]

    # Sanity: end is finite and deterministic
    assert all(math.isfinite(c) for p in positions for c in p)
    positions2 = solve_chain_ik(root, lengths, target)
    assert all(vec_equal(p, q) for p, q in zip(positions, positions2))


def test_random_reachable_cases_deterministic_and_converge():
    root = (0.0, 0.0, 0.0)
    lengths = [0.8, 1.1, 0.9, 0.6]
    total = sum(lengths)

    random.seed(12345)
    for _ in range(10):
        # Random point within reach
        theta = random.random() * math.pi * 2.0
        phi = (random.random() - 0.5) * math.pi
        r = random.random() * total * 0.9
        x = r * math.cos(theta) * math.cos(phi)
        y = r * math.sin(phi)
        z = r * math.sin(theta) * math.cos(phi)
        target = (x, y, z)

        initial_end = initial_stretched_end(root, lengths, target)
        initial_dist = vec_len(vec_sub(initial_end, target))

        positions = solve_chain_ik(root, lengths, target, max_iters=100, tolerance=1e-6)
        end = positions[-1]
        dist = vec_len(vec_sub(end, target))

        assert dist < initial_dist - 1e-12

        # Determinism check
        positions2 = solve_chain_ik(root, lengths, target, max_iters=100, tolerance=1e-6)
        assert all(vec_equal(p, q, tol=1e-9) for p, q in zip(positions, positions2))
