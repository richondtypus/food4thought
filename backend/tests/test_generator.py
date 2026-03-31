from app.services.generator import MenuContext, build_analysis


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
