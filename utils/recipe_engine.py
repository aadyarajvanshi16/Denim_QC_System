def generate_recipe(lab_ref, lab_test):

    recipe = []

    # LAB DIFFERENCES

    delta_l = lab_ref[0] - lab_test[0]
    delta_a = lab_ref[1] - lab_test[1]
    delta_b = lab_ref[2] - lab_test[2]

    # ----------------------------
    # LIGHTNESS ANALYSIS
    # ----------------------------

    if delta_l > 2:

        recipe.append({
            "action": "Increase",
            "dye": "White Tint",
            "amount": round(abs(delta_l) * 1.5, 2)
        })

    elif delta_l < -2:

        recipe.append({
            "action": "Increase",
            "dye": "Black Sulfur",
            "amount": round(abs(delta_l) * 1.5, 2)
        })

    # ----------------------------
    # RED/GREEN ANALYSIS
    # ----------------------------

    if delta_a > 1:

        recipe.append({
            "action": "Increase",
            "dye": "Warm Tone",
            "amount": round(abs(delta_a) * 1.2, 2)
        })

    elif delta_a < -1:

        recipe.append({
            "action": "Increase",
            "dye": "Cool Green Tone",
            "amount": round(abs(delta_a) * 1.2, 2)
        })

    # ----------------------------
    # BLUE/YELLOW ANALYSIS
    # ----------------------------

    if delta_b > 1:

        recipe.append({
            "action": "Increase",
            "dye": "Yellow Tint",
            "amount": round(abs(delta_b) * 1.2, 2)
        })

    elif delta_b < -1:

        recipe.append({
            "action": "Increase",
            "dye": "Indigo Blue",
            "amount": round(abs(delta_b) * 1.2, 2)
        })

    # ----------------------------
    # ADVANCED DENIM LOGIC
    # ----------------------------

    if delta_l < -4 and delta_b < -3:

        recipe.append({
            "action": "Reduce",
            "dye": "Black Sulfur",
            "amount": 5
        })

        recipe.append({
            "action": "Increase",
            "dye": "Indigo Blue",
            "amount": 8
        })

    # ----------------------------
    # PERFECT MATCH CASE
    # ----------------------------

    if len(recipe) == 0:

        recipe.append({
            "action": "Maintain",
            "dye": "Current Recipe",
            "amount": 0
        })

    return recipe


# =========================================================
# SINGLE IMAGE RECIPE EXTRACTION
# =========================================================

def extract_recipe_from_image(lab, dominant_colors):

    l, a, b = lab

    recipe = []

    # -----------------------------
    # INDIGO BLUE ESTIMATION
    # -----------------------------

    indigo = max(0, min(100, abs(b) * 4))

    # -----------------------------
    # BLACK SULFUR ESTIMATION
    # -----------------------------

    black = max(0, min(100, (100 - l) * 0.8))

    # -----------------------------
    # GREY TINT ESTIMATION
    # -----------------------------

    grey = max(0, min(100, abs(a) * 3))

    # -----------------------------
    # WHITE TINT ESTIMATION
    # -----------------------------

    white = max(0, min(100, l * 0.3))

    # -----------------------------
    # NORMALIZATION
    # -----------------------------

    total = indigo + black + grey + white

    indigo = round((indigo / total) * 100, 2)
    black = round((black / total) * 100, 2)
    grey = round((grey / total) * 100, 2)
    white = round((white / total) * 100, 2)

    recipe.append({
        "dye": "Indigo Blue",
        "percentage": indigo
    })

    recipe.append({
        "dye": "Black Sulfur",
        "percentage": black
    })

    recipe.append({
        "dye": "Grey Tint",
        "percentage": grey
    })

    recipe.append({
        "dye": "White Tint",
        "percentage": white
    })

    recipe = sorted(
        recipe,
        key=lambda x: x["percentage"],
        reverse=True
    )

    return recipe