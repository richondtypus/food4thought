from app.services.generator import (
    CandidateDish,
    MenuContext,
    build_analysis,
    dedupe_candidates,
    limited_combinations,
)


def test_build_analysis_generates_dishes() -> None:
    context = MenuContext(
        filename="sunrise-bistro.pdf",
        raw_text="""
        Sunrise Bistro
        Avocado Toast with tomato, basil, olive oil
        Roasted Veggie Pasta with marinara, zucchini, mushroom, garlic
        Grilled Taco Plate with bell pepper, onion, cilantro and lime rice
        Market Salad with arugula, cucumber, white balsamic
        """,
    )

    result = build_analysis(context)

    assert result.restaurant_name == "Sunrise Bistro"
    assert result.vegan_dishes
    assert "animal_based" in result.ingredients.model_dump()
    assert any(item in result.ingredients.available for item in ("avocado", "pasta", "cilantro"))
    assert result.ingredients.likely_missing == []
    assert result.notes
    assert len(result.vegan_dishes) >= 5

    available_set = set(result.ingredients.available)
    for dish in result.vegan_dishes:
        assert dish.consumer_confidence
        assert dish.ordering_tip.startswith('Ask: "')
        assert dish.evidence_lines
        assert dish.ingredients_needed == []
        assert set(dish.ingredients_used).issubset(available_set)


def test_limited_combinations_prefers_variety() -> None:
    combos = limited_combinations(
        ["butternut squash", "eggplant", "tomato", "avocado"],
        size=2,
        limit=2,
    )

    assert combos == [
        ("butternut squash", "eggplant"),
        ("tomato", "avocado"),
    ]


def test_dedupe_candidates_collapses_near_duplicate_category_options() -> None:
    candidates = [
        CandidateDish(
            name="Butternut Squash & Avocado Fregola Bowl",
            category="Bowls",
            reasoning="",
            ingredients_used=("fregola", "butternut squash", "avocado", "herbs", "olive oil"),
            score=100,
        ),
        CandidateDish(
            name="Butternut Squash & Eggplant Fregola Bowl",
            category="Bowls",
            reasoning="",
            ingredients_used=("fregola", "butternut squash", "eggplant", "herbs", "olive oil"),
            score=98,
        ),
        CandidateDish(
            name="Butternut Squash & Avocado Insalata",
            category="Salads",
            reasoning="",
            ingredients_used=("arugula", "butternut squash", "avocado", "herbs", "olive oil"),
            score=95,
        ),
    ]

    deduped = dedupe_candidates(candidates)

    assert [dish.name for dish in deduped] == [
        "Butternut Squash & Avocado Fregola Bowl",
        "Butternut Squash & Avocado Insalata",
    ]
