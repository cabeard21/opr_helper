from __future__ import annotations

from collections.abc import Iterable


def convolve(left: list[float], right: list[float]) -> list[float]:
    result = [0.0] * (len(left) + len(right) - 1)
    for left_wounds, left_probability in enumerate(left):
        if left_probability == 0:
            continue
        for right_wounds, right_probability in enumerate(right):
            if right_probability == 0:
                continue
            result[left_wounds + right_wounds] += left_probability * right_probability
    return result


def repeated_convolution(single_attack: list[float], attacks: int) -> list[float]:
    distribution = [1.0]
    for _ in range(max(0, attacks)):
        distribution = convolve(distribution, single_attack)
    return distribution


def points(distribution: Iterable[float]) -> list[dict[str, float | int]]:
    return [
        {"wounds": wounds, "probability": round(probability, 6)}
        for wounds, probability in enumerate(distribution)
    ]
