"""
Rule-based dye recipe recommendation from LAB deltas / single-image
LAB + dominant color estimates. Logic is unchanged from the original
app — only cleaned up, typed and documented.
"""

from __future__ import annotations

from typing import List, TypedDict


class RecipeStep(TypedDict):
    action: str
    dye: str
    amount: float


def generate_recipe(lab_ref: List[float], lab_test: List[float]) -> List[RecipeStep]:
    """Suggest dye adjustments to move the test fabric toward the reference."""
    recipe: List[RecipeStep] = []

    delta_l = lab_ref[0] - lab_test[0]
    delta_a = lab_ref[1] - lab_test[1]
    delta_b = lab_ref[2] - lab_test[2]

    if delta_l > 2:
        recipe.append({"action": "Increase", "dye": "White Tint", "amount": round(abs(delta_l) * 1.5, 2)})
    elif delta_l < -2:
        recipe.append({"action": "Increase", "dye": "Black Sulfur", "amount": round(abs(delta_l) * 1.5, 2)})

    if delta_a > 1:
        recipe.append({"action": "Increase", "dye": "Warm Tone", "amount": round(abs(delta_a) * 1.2, 2)})
    elif delta_a < -1:
        recipe.append({"action": "Increase", "dye": "Cool Green Tone", "amount": round(abs(delta_a) * 1.2, 2)})

    if delta_b > 1:
        recipe.append({"action": "Increase", "dye": "Yellow Tint", "amount": round(abs(delta_b) * 1.2, 2)})
    elif delta_b < -1:
        recipe.append({"action": "Increase", "dye": "Indigo Blue", "amount": round(abs(delta_b) * 1.2, 2)})

    if delta_l < -4 and delta_b < -3:
        recipe.append({"action": "Reduce", "dye": "Black Sulfur", "amount": 5})
        recipe.append({"action": "Increase", "dye": "Indigo Blue", "amount": 8})

    if not recipe:
        recipe.append({"action": "Maintain", "dye": "Current Recipe", "amount": 0})

    return recipe


def extract_recipe_from_image(lab: List[float], dominant_colors) -> List[dict]:
    """Estimate a starting dye composition from a single fabric sample's LAB values."""
    l, a, b = lab

    indigo = max(0.0, min(100.0, abs(b) * 4))
    black = max(0.0, min(100.0, (100 - l) * 0.8))
    grey = max(0.0, min(100.0, abs(a) * 3))
    white = max(0.0, min(100.0, l * 0.3))

    total = indigo + black + grey + white
    if total <= 0:
        total = 1.0  # avoid a divide-by-zero on a fully black/degenerate ROI

    recipe = [
        {"dye": "Indigo Blue", "percentage": round((indigo / total) * 100, 2)},
        {"dye": "Black Sulfur", "percentage": round((black / total) * 100, 2)},
        {"dye": "Grey Tint", "percentage": round((grey / total) * 100, 2)},
        {"dye": "White Tint", "percentage": round((white / total) * 100, 2)},
    ]
    return sorted(recipe, key=lambda x: x["percentage"], reverse=True)
