from pydantic import BaseModel, Field


class IngredientGroup(BaseModel):
    available: list[str] = Field(default_factory=list)
    animal_based: list[str] = Field(default_factory=list)
    likely_missing: list[str] = Field(default_factory=list)


class DishSuggestion(BaseModel):
    name: str
    category: str
    feasibility: str
    reasoning: str
    ingredients_used: list[str]
    ingredients_needed: list[str]


class AnalysisResponse(BaseModel):
    restaurant_name: str
    cuisine_signals: list[str]
    source_items: list[str]
    ingredients: IngredientGroup
    vegan_dishes: list[DishSuggestion]
    notes: list[str]
