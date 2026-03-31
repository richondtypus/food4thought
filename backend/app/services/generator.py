from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

from app.models import AnalysisResponse, DishSuggestion, IngredientGroup
from app.services.menu_parser import (
    derive_restaurant_name,
    extract_source_items,
    infer_animal_ingredients,
    infer_available_ingredients,
    infer_cuisine_signals,
    phrase_present,
)

GREENS = {"arugula", "greens", "kale", "spinach", "cabbage", "radicchio"}
HERBS = {"basil", "cilantro", "herbs", "mint", "oregano", "thai basil"}
ACIDS = {"lemon", "lime", "white balsamic"}
FINISHES = ACIDS | HERBS | {
    "coconut milk",
    "curry",
    "hummus",
    "marinara",
    "olive oil",
    "salsa",
    "salsa verde",
    "tahini",
}
GRAINS = {"fregola", "quinoa", "rice"}
PASTA_BASES = {"fregola", "pasta"}
BREAD_CARRIERS = {"bread", "bun", "flour tortilla", "pita"}
LEGUMES = {"beans", "black beans", "chickpea", "lentils", "tofu", "white beans"}
ROASTABLES = {
    "asparagus",
    "bell pepper",
    "broccoli",
    "brussels sprouts",
    "butternut squash",
    "carrot",
    "cauliflower",
    "eggplant",
    "mushroom",
    "onion",
    "potato",
    "zucchini",
}
FRESH_PRODUCE = {
    "avocado",
    "corn",
    "cucumber",
    "heirloom tomato",
    "jalapeno",
    "tomato",
}
VEGETABLES = GREENS | ROASTABLES | FRESH_PRODUCE | LEGUMES
FOUNDATIONS = GRAINS | PASTA_BASES | BREAD_CARRIERS | {"coconut milk", "hummus", "marinara"}


@dataclass
class MenuContext:
    filename: str
    raw_text: str


@dataclass(frozen=True)
class CandidateDish:
    name: str
    category: str
    reasoning: str
    ingredients_used: tuple[str, ...]
    score: int


def build_analysis(context: MenuContext) -> AnalysisResponse:
    source_items = extract_source_items(context.raw_text)
    cuisine_signals = infer_cuisine_signals(source_items)
    available = infer_available_ingredients(source_items)
    animal_based = infer_animal_ingredients(source_items)

    restaurant_name = derive_restaurant_name(context.filename, context.raw_text)
    dishes = generate_dishes(cuisine_signals, available, source_items)

    return AnalysisResponse(
        restaurant_name=restaurant_name,
        cuisine_signals=cuisine_signals,
        source_items=source_items,
        ingredients=IngredientGroup(
            available=available,
            animal_based=animal_based,
            likely_missing=[],
        ),
        vegan_dishes=dishes,
        notes=build_consumer_notes(animal_based),
    )


def generate_dishes(
    cuisine_signals: list[str],
    available: list[str],
    source_items: list[str],
) -> list[DishSuggestion]:
    primary_cuisine = cuisine_signals[0] if cuisine_signals else "Contemporary Casual"
    cuisine_set = set(cuisine_signals)

    candidates: list[CandidateDish] = []
    candidates.extend(build_toasts_and_bruschetta(available, primary_cuisine))
    candidates.extend(build_salads(available, primary_cuisine))
    candidates.extend(build_grain_bowls(available, primary_cuisine))
    candidates.extend(build_pasta_dishes(available, primary_cuisine))
    candidates.extend(build_tacos(available, primary_cuisine))
    candidates.extend(build_wraps(available, primary_cuisine))
    candidates.extend(build_roasted_plates(available, primary_cuisine))
    candidates.extend(build_curries(available, primary_cuisine))
    candidates.extend(build_mezze(available, primary_cuisine))
    candidates.extend(build_sandwiches(available, primary_cuisine))

    if "Italian" in cuisine_set:
        candidates.extend(build_italian_specials(available))
    if "Mediterranean" in cuisine_set:
        candidates.extend(build_mediterranean_specials(available))
    if "Mexican" in cuisine_set:
        candidates.extend(build_mexican_specials(available))

    deduped = dedupe_candidates(candidates)

    return [
        candidate_to_dish_suggestion(dish, source_items)
        for dish in deduped
    ]


def build_toasts_and_bruschetta(available: list[str], cuisine: str) -> list[CandidateDish]:
    bread = first_present(available, {"bread"})
    if not bread:
        return []

    dishes: list[CandidateDish] = []
    herb = first_present(available, HERBS)
    acid = first_present(available, ACIDS | {"olive oil"})

    if "avocado" in available:
        dishes.append(
            make_candidate(
                name="Crushed Avocado Toast",
                category="Shareables",
                cuisine=cuisine,
                ingredients=[bread, "avocado", herb, acid],
                bonus=8,
            )
        )

    tomato = first_present(available, {"heirloom tomato", "tomato"})
    if tomato and first_present(available, {"basil", "oregano", "herbs"}) and "olive oil" in available:
        topping_herb = first_present(available, {"basil", "oregano", "herbs"})
        dishes.append(
            make_candidate(
                name=f"{ingredient_title(tomato)} {ingredient_title(topping_herb)} Bruschetta",
                category="Shareables",
                cuisine=cuisine,
                ingredients=[bread, tomato, topping_herb, "olive oil"],
                bonus=10,
            )
        )

    bean = first_present(available, {"white beans", "chickpea"})
    if bean:
        dishes.append(
            make_candidate(
                name=f"{ingredient_title(bean)} Herb Crostini",
                category="Shareables",
                cuisine=cuisine,
                ingredients=[bread, bean, herb, "olive oil"],
                bonus=8,
            )
        )

    return dishes


def build_salads(available: list[str], cuisine: str) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []
    greens = ordered_present(available, GREENS)
    dressing = first_present(available, {"white balsamic", "lemon", "lime", "olive oil", "tahini"})
    herb = first_present(available, HERBS)

    if greens:
        accents = ordered_present(available, (VEGETABLES - GREENS) | {"avocado", "corn", "cucumber", "tomato"})
        for combo in limited_combinations(accents, size=2, limit=2):
            dishes.append(
                make_candidate(
                    name=salad_name(cuisine, combo),
                    category="Salads",
                    cuisine=cuisine,
                    ingredients=[greens[0], *combo, herb, dressing],
                    bonus=10,
                )
            )

    if "cabbage" in available:
        crunch = ordered_present(available, {"carrot", "cucumber", "avocado", "corn", "jalapeno", "tomato"})
        if len(crunch) >= 2:
            dishes.append(
                make_candidate(
                    name="Cabbage Crunch Slaw",
                    category="Salads",
                    cuisine=cuisine,
                    ingredients=["cabbage", crunch[0], crunch[1], dressing, herb],
                    bonus=8,
                )
            )

    return dishes


def build_grain_bowls(available: list[str], cuisine: str) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []
    base = first_present(available, GRAINS)
    veggies = ordered_present(available, (VEGETABLES - GRAINS) | {"avocado", "corn", "cucumber", "tomato"})
    herb = first_present(available, HERBS)
    finish = first_present(available, {"olive oil", "lemon", "lime", "tahini", "white balsamic"})

    if base and len(veggies) >= 2:
        for combo in limited_combinations(veggies, size=2, limit=2):
            dishes.append(
                make_candidate(
                    name=bowl_name(cuisine, base, combo, herb, finish),
                    category="Bowls",
                    cuisine=cuisine,
                    ingredients=[base, *combo, herb, finish],
                    bonus=12,
                )
            )

    if not base:
        legume_base = first_present(available, {"chickpea", "lentils", "white beans"})
        if legume_base and veggies:
            dishes.append(
                make_candidate(
                    name=f"{ingredient_title(legume_base)} Vegetable Bowl",
                    category="Bowls",
                    cuisine=cuisine,
                    ingredients=[legume_base, veggies[0], veggies[1] if len(veggies) > 1 else None, herb, finish],
                    bonus=8,
                )
            )

    return dishes


def build_pasta_dishes(available: list[str], cuisine: str) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []
    base = first_present(available, PASTA_BASES)
    if not base:
        return dishes

    vegetables = ordered_present(
        available,
        {"asparagus", "bell pepper", "broccoli", "butternut squash", "cauliflower", "eggplant", "kale", "mushroom", "spinach", "tomato", "heirloom tomato", "zucchini"},
    )
    sauce = first_present(available, {"marinara", "olive oil"})
    aromatics = first_present(available, {"basil", "garlic", "oregano", "herbs"})
    if not vegetables:
        return dishes

    combo_size = 2 if len(vegetables) > 1 else 1
    for combo in limited_combinations(vegetables, size=combo_size, limit=2):
        dishes.append(
            make_candidate(
                name=pasta_name(base, combo, sauce, aromatics),
                category="Mains",
                cuisine=cuisine,
                ingredients=[base, *combo, sauce, aromatics],
                bonus=14,
            )
        )

    return dishes


def build_tacos(available: list[str], cuisine: str) -> list[CandidateDish]:
    tortilla = first_present(available, {"flour tortilla"})
    if not tortilla:
        return []

    fillings = ordered_present(
        available,
        {"avocado", "beans", "black beans", "bell pepper", "cabbage", "cauliflower", "chickpea", "corn", "mushroom", "onion", "potato", "zucchini"},
    )
    herb = first_present(available, {"cilantro"})
    finish = first_present(available, {"lime", "salsa", "salsa verde"})
    if len(fillings) < 2:
        return []

    dishes: list[CandidateDish] = []
    for combo in limited_combinations(fillings, size=2, limit=2):
        dishes.append(
            make_candidate(
                name=taco_name(combo, finish),
                category="Tacos",
                cuisine=cuisine,
                ingredients=[tortilla, *combo, herb, finish],
                bonus=12,
            )
        )
    return dishes


def build_wraps(available: list[str], cuisine: str) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []
    carrier = first_present(available, {"pita", "flour tortilla"})
    if not carrier:
        return dishes

    greens = first_present(available, GREENS)
    fillings = ordered_present(
        available,
        {"avocado", "bell pepper", "cabbage", "cauliflower", "chickpea", "cucumber", "eggplant", "mushroom", "onion", "tomato", "white beans", "zucchini"},
    )
    finish = first_present(available, {"hummus", "tahini", "olive oil", "lime", "lemon"})
    if len(fillings) < 2:
        return dishes

    if carrier == "pita" and "chickpea" in available:
        dishes.append(
            make_candidate(
                name="Garden Chickpea Pita",
                category="Wraps",
                cuisine=cuisine,
                ingredients=[carrier, "chickpea", greens, fillings[0], finish],
                bonus=12,
            )
        )

    dishes.append(
        make_candidate(
            name="Roasted Veggie Wrap",
            category="Wraps",
            cuisine=cuisine,
            ingredients=[carrier, greens, fillings[0], fillings[1], finish],
            bonus=10,
        )
    )

    return dishes


def build_roasted_plates(available: list[str], cuisine: str) -> list[CandidateDish]:
    roastables = ordered_present(available, ROASTABLES)
    if len(roastables) < 2:
        return []

    finish = first_present(available, {"olive oil", "lemon", "marinara", "tahini", "herbs", "oregano"})
    dishes: list[CandidateDish] = []
    for combo in limited_combinations(roastables, size=2, limit=2):
        dishes.append(
            make_candidate(
                name=plate_name(cuisine, combo, finish),
                category="Plates",
                cuisine=cuisine,
                ingredients=[*combo, finish],
                bonus=9,
            )
        )
    return dishes


def build_curries(available: list[str], cuisine: str) -> list[CandidateDish]:
    if "coconut milk" not in available and "curry" not in available:
        return []

    vegetables = ordered_present(
        available,
        {"bell pepper", "broccoli", "carrot", "cauliflower", "mushroom", "onion", "spinach", "zucchini"},
    )
    protein = first_present(available, {"lentils", "tofu", "chickpea"})
    rice = first_present(available, {"rice"})
    herb = first_present(available, {"thai basil", "cilantro", "mint"})
    if len(vegetables) < 2 and not protein:
        return []

    dishes = [
        make_candidate(
            name=curry_name(protein, herb),
            category="Curries",
            cuisine=cuisine,
            ingredients=[protein, vegetables[0] if vegetables else None, vegetables[1] if len(vegetables) > 1 else None, "coconut milk" if "coconut milk" in available else "curry", rice, herb],
            bonus=16,
        )
    ]

    if rice and len(vegetables) >= 2:
        dishes.append(
            make_candidate(
                name="Vegetable Curry Bowl",
                category="Curries",
                cuisine=cuisine,
                ingredients=[rice, vegetables[0], vegetables[1], "coconut milk" if "coconut milk" in available else "curry", herb],
                bonus=12,
            )
        )

    return dishes


def build_mezze(available: list[str], cuisine: str) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []
    pita = first_present(available, {"pita"})
    if not pita:
        return dishes

    cucumber = first_present(available, {"cucumber"})
    tomato = first_present(available, {"heirloom tomato", "tomato"})
    finish = first_present(available, {"hummus", "tahini", "olive oil"})

    if "chickpea" in available:
        dishes.append(
            make_candidate(
                name="Herbed Chickpea Mezze Plate",
                category="Shareables",
                cuisine=cuisine,
                ingredients=[pita, "chickpea", cucumber, tomato, finish],
                bonus=14,
            )
        )

    if "eggplant" in available:
        dishes.append(
            make_candidate(
                name="Roasted Eggplant Mezze",
                category="Shareables",
                cuisine=cuisine,
                ingredients=[pita, "eggplant", cucumber, tomato, finish],
                bonus=12,
            )
        )

    return dishes


def build_sandwiches(available: list[str], cuisine: str) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []
    carrier = first_present(available, {"bun", "bread"})
    if not carrier:
        return dishes

    greens = first_present(available, GREENS)
    fillings = ordered_present(
        available,
        {"avocado", "bell pepper", "cauliflower", "mushroom", "onion", "potato", "tomato", "heirloom tomato", "zucchini"},
    )
    finish = first_present(available, {"olive oil", "hummus", "tahini", "herb oil"})
    if len(fillings) < 2:
        return dishes

    if carrier == "bun":
        dishes.append(
            make_candidate(
                name="Roasted Veggie Bun",
                category="Sandwiches",
                cuisine=cuisine,
                ingredients=[carrier, fillings[0], fillings[1], greens, finish],
                bonus=12,
            )
        )

    dishes.append(
        make_candidate(
            name="Garden Stack Sandwich",
            category="Sandwiches",
            cuisine=cuisine,
            ingredients=[carrier, fillings[0], fillings[1], greens, finish],
            bonus=10,
        )
    )

    return dishes


def build_italian_specials(available: list[str]) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []

    if {"eggplant", "marinara"} <= set(available):
        dishes.append(
            make_candidate(
                name="Charred Eggplant Marinara",
                category="Mains",
                cuisine="Italian",
                ingredients=["eggplant", "marinara", "basil" if "basil" in available else "olive oil"],
                bonus=14,
            )
        )

    if {"fregola", "olive oil"} <= set(available):
        vegetables = ordered_present(available, {"asparagus", "butternut squash", "cauliflower", "mushroom", "zucchini"})
        if vegetables:
            dishes.append(
                make_candidate(
                    name="Roasted Vegetable Fregola",
                    category="Bowls",
                    cuisine="Italian",
                    ingredients=["fregola", vegetables[0], vegetables[1] if len(vegetables) > 1 else None, "olive oil", first_present(available, {"basil", "oregano", "herbs"})],
                    bonus=12,
                )
            )

    return dishes


def build_mediterranean_specials(available: list[str]) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []

    if {"pita", "cucumber", "tomato"} <= set(available):
        dishes.append(
            make_candidate(
                name="Cucumber Tomato Pita Plate",
                category="Shareables",
                cuisine="Mediterranean",
                ingredients=["pita", "cucumber", "tomato", first_present(available, {"tahini", "olive oil", "hummus"}), first_present(available, {"mint", "herbs"})],
                bonus=12,
            )
        )

    return dishes


def build_mexican_specials(available: list[str]) -> list[CandidateDish]:
    dishes: list[CandidateDish] = []

    if {"rice", "lime"} <= set(available):
        toppings = ordered_present(available, {"avocado", "beans", "black beans", "bell pepper", "corn", "tomato"})
        if len(toppings) >= 2:
            dishes.append(
                make_candidate(
                    name="Cilantro Lime Rice Bowl",
                    category="Bowls",
                    cuisine="Mexican",
                    ingredients=["rice", toppings[0], toppings[1], "lime", first_present(available, {"cilantro", "salsa", "salsa verde"})],
                    bonus=14,
                )
            )

    return dishes


def dedupe_candidates(candidates: list[CandidateDish]) -> list[CandidateDish]:
    ranked = sorted(candidates, key=lambda dish: (-dish.score, dish.category, dish.name))
    deduped: list[CandidateDish] = []
    seen: set[str] = set()

    for dish in ranked:
        key = dish.name.lower()
        if key in seen:
            continue
        if any(looks_like_same_category_dish(dish, existing) for existing in deduped):
            continue
        seen.add(key)
        deduped.append(dish)

    return deduped


def candidate_to_dish_suggestion(dish: CandidateDish, source_items: list[str]) -> DishSuggestion:
    consumer_confidence = consumer_confidence_for_score(dish.score)

    return DishSuggestion(
        name=dish.name,
        category=dish.category,
        feasibility=feasibility_for_score(dish.score),
        consumer_confidence=consumer_confidence,
        reasoning=dish.reasoning,
        ordering_tip=build_ordering_tip(dish.category, list(dish.ingredients_used), consumer_confidence),
        evidence_lines=select_evidence_lines(list(dish.ingredients_used), source_items),
        ingredients_used=list(dish.ingredients_used),
        ingredients_needed=[],
    )


def make_candidate(
    *,
    name: str,
    category: str,
    cuisine: str,
    ingredients: list[str | None],
    bonus: int = 0,
) -> CandidateDish:
    used = unique_preserve_order(ingredients)
    score = len(used) * 14 + bonus
    if any(item in FOUNDATIONS for item in used):
        score += 6
    if any(item in FINISHES for item in used):
        score += 6

    return CandidateDish(
        name=name,
        category=category,
        reasoning=build_reasoning(category, cuisine, used),
        ingredients_used=tuple(used),
        score=score,
    )


def build_reasoning(category: str, cuisine: str, ingredients_used: list[str]) -> str:
    highlighted = human_join(ingredients_used[:3])
    if cuisine == "Contemporary Casual":
        cuisine_phrase = "the restaurant's current menu language"
    else:
        cuisine_phrase = f"the restaurant's {cuisine.lower()} menu language"

    return (
        f"Uses only menu-signaled ingredients like {highlighted}, "
        f"making this {singularize(category)} a natural fit for {cuisine_phrase}."
    )


def salad_name(cuisine: str, combo: tuple[str, ...]) -> str:
    pair = ingredient_pair(combo)
    if cuisine == "Italian":
        return f"{pair} Insalata"
    if cuisine == "Mexican":
        return f"{pair} Lime Salad"
    return f"{pair} Salad"


def bowl_name(
    cuisine: str,
    base: str,
    combo: tuple[str, ...],
    herb: str | None,
    finish: str | None,
) -> str:
    pair = ingredient_pair(combo)
    if cuisine == "Italian" and base == "fregola":
        return f"{pair} Fregola Bowl"
    if cuisine == "Mexican" and base == "rice" and (herb == "cilantro" or finish == "lime"):
        return "Cilantro Lime Rice Bowl"
    if base == "quinoa":
        return f"{pair} Quinoa Bowl"
    if base == "rice":
        return f"{pair} Rice Bowl"
    return f"{pair} {ingredient_title(base)} Bowl"


def pasta_name(
    base: str,
    combo: tuple[str, ...],
    sauce: str | None,
    aromatics: str | None,
) -> str:
    pair = ingredient_pair(combo)
    base_title = ingredient_title(base)
    if sauce == "marinara":
        return f"{pair} Marinara {base_title}"
    if aromatics in {"basil", "oregano", "herbs"}:
        return f"{pair} Herb {base_title}"
    return f"{pair} {base_title}"


def taco_name(combo: tuple[str, ...], finish: str | None) -> str:
    if "cauliflower" in combo and finish == "lime":
        return "Crispy Cauliflower Lime Tacos"
    if {"bell pepper", "onion"} <= set(combo):
        return "Charred Pepper & Onion Tacos"
    if "mushroom" in combo:
        return "Mushroom Street Tacos"
    return f"{ingredient_pair(combo)} Tacos"


def plate_name(cuisine: str, combo: tuple[str, ...], finish: str | None) -> str:
    pair = ingredient_pair(combo)
    if cuisine == "Italian" and finish == "marinara":
        return f"{pair} Marinara Plate"
    return f"Roasted {pair} Plate"


def curry_name(protein: str | None, herb: str | None) -> str:
    if protein == "lentils":
        return "Coconut Lentil Curry"
    if herb == "thai basil":
        return "Thai Basil Vegetable Curry"
    if protein == "tofu":
        return "Tofu Coconut Curry"
    return "Vegetable Coconut Curry"


def feasibility_for_score(score: int) -> str:
    if score >= 88:
        return "Ready now"
    if score >= 72:
        return "Strong pantry fit"
    return "Possible now"


def consumer_confidence_for_score(score: int) -> str:
    if score >= 88:
        return "Likely available now"
    if score >= 72:
        return "Likely available if you ask"
    return "Worth asking about"


def build_ordering_tip(category: str, ingredients_used: list[str], consumer_confidence: str) -> str:
    ingredient_phrase = human_join(ingredients_used[:4])
    order_shape = order_shape_for_category(category)

    if consumer_confidence == "Likely available now":
        return f'Ask: "Could you do {order_shape} with {ingredient_phrase}?"'
    if consumer_confidence == "Likely available if you ask":
        return (
            f'Ask: "Could you do {order_shape} with {ingredient_phrase} '
            'and keep it free of dairy, egg, and meat?"'
        )
    return (
        f'Ask: "Is there any way to do {order_shape} with {ingredient_phrase} '
        'using ingredients already on the menu?"'
    )


def order_shape_for_category(category: str) -> str:
    shapes = {
        "Shareables": "a vegan small plate",
        "Salads": "a vegan salad",
        "Bowls": "a vegan bowl",
        "Mains": "a vegan entree",
        "Tacos": "vegan tacos",
        "Wraps": "a vegan wrap",
        "Plates": "a vegan plate",
        "Curries": "a vegan curry",
        "Sandwiches": "a vegan sandwich",
    }
    return shapes.get(category, f"a vegan {singularize(category)}")


def select_evidence_lines(ingredients_used: list[str], source_items: list[str], limit: int = 2) -> list[str]:
    ranked_matches: list[tuple[int, int, str]] = []
    for index, source_item in enumerate(source_items):
        lowered = source_item.lower()
        match_count = sum(1 for ingredient in ingredients_used if phrase_present(lowered, ingredient))
        if match_count:
            ranked_matches.append((match_count, index, source_item))

    ranked_matches.sort(key=lambda item: (-item[0], item[1]))
    return [source_item for _matches, _index, source_item in ranked_matches[:limit]]


def build_consumer_notes(animal_based: list[str]) -> list[str]:
    notes = [
        "These suggestions are inferred from menu language, so treat them as smart asks rather than guaranteed listed items.",
        "Mention the ingredients you saw on the menu when ordering. That makes an off-menu vegan ask feel much more realistic.",
    ]

    if animal_based:
        highlighted = human_join(animal_based[:4])
        notes.append(
            f"Watch for animal-based finishes or sauces elsewhere on the menu, especially items like {highlighted}."
        )
    else:
        notes.append(
            "Even if a menu looks plant-forward, it is still worth confirming butter, cheese, aioli, stock, and shared prep."
        )

    return notes


def ordered_present(available: list[str], options: set[str]) -> list[str]:
    return [item for item in available if item in options]


def first_present(available: list[str], options: set[str]) -> str | None:
    for item in available:
        if item in options:
            return item
    return None


def unique_preserve_order(values: list[str | None]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def limited_combinations(items: list[str], size: int, limit: int) -> list[tuple[str, ...]]:
    all_combos = list(combinations(items, size))
    if len(all_combos) <= limit:
        return all_combos

    selected: list[tuple[str, ...]] = []
    ingredient_use_count: dict[str, int] = {}

    indexed_combos = list(enumerate(all_combos))
    while indexed_combos and len(selected) < limit:
        if not selected:
            _index, combo = indexed_combos.pop(0)
            selected.append(combo)
            for ingredient in combo:
                ingredient_use_count[ingredient] = ingredient_use_count.get(ingredient, 0) + 1
            continue

        best_position = min(
            range(len(indexed_combos)),
            key=lambda position: combination_priority(indexed_combos[position][1], ingredient_use_count, indexed_combos[position][0]),
        )
        _index, combo = indexed_combos.pop(best_position)
        selected.append(combo)
        for ingredient in combo:
            ingredient_use_count[ingredient] = ingredient_use_count.get(ingredient, 0) + 1

    return selected


def looks_like_same_category_dish(candidate: CandidateDish, existing: CandidateDish) -> bool:
    if candidate.category != existing.category:
        return False

    candidate_ingredients = set(candidate.ingredients_used)
    existing_ingredients = set(existing.ingredients_used)
    union = candidate_ingredients | existing_ingredients
    if not union:
        return False

    overlap_ratio = len(candidate_ingredients & existing_ingredients) / len(union)
    return overlap_ratio >= 0.6


def combination_priority(
    combo: tuple[str, ...],
    ingredient_use_count: dict[str, int],
    original_index: int,
) -> tuple[int, int, int]:
    repeated_ingredients = sum(ingredient_use_count.get(ingredient, 0) for ingredient in combo)
    max_reuse = max((ingredient_use_count.get(ingredient, 0) for ingredient in combo), default=0)
    return repeated_ingredients, max_reuse, original_index


def ingredient_title(ingredient: str) -> str:
    return ingredient.title()


def ingredient_pair(ingredients: tuple[str, ...]) -> str:
    return " & ".join(ingredient_title(item) for item in ingredients)


def human_join(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def singularize(label: str) -> str:
    lowered = label.lower()
    if lowered.endswith("ies"):
        return lowered[:-3] + "y"
    if lowered.endswith("s"):
        return lowered[:-1]
    return lowered
