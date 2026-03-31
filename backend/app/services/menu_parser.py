from __future__ import annotations

import io
import re

import pdfplumber

STOPWORDS = {
    "with",
    "and",
    "the",
    "our",
    "served",
    "fresh",
    "house",
    "style",
    "choice",
    "your",
    "menu",
    "daily",
    "special",
    "chef",
    "grilled",
    "crispy",
    "roasted",
    "braised",
    "perfect",
    "share",
    "plates",
    "boards",
    "salads",
    "pizza",
    "chef",
}

SECTION_HEADERS = {
    "small plates",
    "chef's boards",
    "chef’s boards",
    "salads",
    "pizza",
    "pasta",
    "dessert",
    "cocktails",
    "beer",
    "wine",
    "brunch",
    "lunch",
    "dinner",
}

NAME_BLACKLIST = SECTION_HEADERS | {
    "daily soup",
    "perfect to share",
}

CUISINE_KEYWORDS: dict[str, tuple[tuple[str, int], ...]] = {
    "Mexican": (
        ("taco", 3),
        ("quesadilla", 3),
        ("salsa", 2),
        ("burrito", 3),
        ("enchilada", 3),
        ("fajita", 3),
        ("cilantro", 1),
        ("lime", 1),
    ),
    "Italian": (
        ("marinara", 3),
        ("bruschetta", 3),
        ("prosciutto", 2),
        ("pecorino", 2),
        ("mozzarella", 2),
        ("ricotta", 2),
        ("fregola", 2),
        ("polenta", 2),
        ("grana padano", 2),
        ("calabrian", 2),
        ("parmesan", 2),
        ("vodka sauce", 2),
    ),
    "Mediterranean": (
        ("hummus", 3),
        ("falafel", 3),
        ("tabbouleh", 3),
        ("pita", 2),
        ("tahini", 2),
        ("sumac", 2),
    ),
    "Thai": (
        ("pad thai", 3),
        ("lemongrass", 2),
        ("thai basil", 2),
        ("coconut milk", 2),
        ("satay", 2),
        ("peanut", 1),
        ("curry", 2),
    ),
    "Indian": (
        ("masala", 3),
        ("dal", 2),
        ("tikka", 2),
        ("naan", 2),
        ("paneer", 2),
        ("chutney", 2),
        ("garam masala", 2),
    ),
    "American": (
        ("burger", 3),
        ("fries", 2),
        ("slaw", 2),
        ("bbq", 2),
        ("sandwich", 2),
        ("caesar", 1),
        ("chopped", 1),
    ),
}

VEGAN_INGREDIENT_HINTS = {
    "arugula",
    "asparagus",
    "avocado",
    "basil",
    "black beans",
    "beans",
    "bell pepper",
    "bread",
    "broccoli",
    "brussels sprouts",
    "bun",
    "butternut squash",
    "cabbage",
    "carrot",
    "cauliflower",
    "chickpea",
    "cilantro",
    "coconut milk",
    "corn",
    "cucumber",
    "curry",
    "date",
    "eggplant",
    "fregola",
    "flour tortilla",
    "fig",
    "garlic",
    "greens",
    "heirloom tomato",
    "herb oil",
    "herbs",
    "hummus",
    "jalapeno",
    "kale",
    "lemon",
    "lentils",
    "lime",
    "marinara",
    "mint",
    "mushroom",
    "olive oil",
    "onion",
    "oregano",
    "pasta",
    "peanut",
    "pickled onion",
    "pine nuts",
    "pita",
    "pistachio",
    "potato",
    "quinoa",
    "radicchio",
    "rice",
    "salsa",
    "salsa verde",
    "spinach",
    "sumac",
    "tahini",
    "thai basil",
    "tomato",
    "tofu",
    "white balsamic",
    "white beans",
    "zucchini",
}

ANIMAL_INGREDIENTS = {
    "aioli",
    "beef",
    "burrata",
    "butter",
    "calamari",
    "pork",
    "chicken",
    "cream",
    "egg",
    "goat cheese",
    "gorgonzola",
    "grana padano",
    "honey",
    "lamb",
    "meatball",
    "mozzarella",
    "paneer",
    "parmesan",
    "pecorino",
    "pepperoni",
    "shrimp",
    "prosciutto",
    "ricotta",
    "salmon",
    "sausage",
    "sopressatta",
    "stracciatella",
    "yogurt",
    "steak",
    "cheese",
    "bacon",
}

GENERIC_INGREDIENTS = {
    "italian",
    "spicy",
    "market",
    "seasonal",
    "little",
    "gem",
    "daily",
    "hot",
    "smoked",
    "rustic",
    "fresh",
}

FORMAT_SIGNAL_INGREDIENTS = {
    "bruschetta": "bread",
    "burger": "bun",
    "sandwich": "bread",
    "taco": "flour tortilla",
    "toast": "bread",
    "wrap": "flour tortilla",
}


def extract_pdf_text(file_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [page.extract_text() or "" for page in pdf.pages]
    return "\n".join(pages).strip()


def derive_restaurant_name(filename: str, raw_text: str) -> str:
    for line in raw_text.splitlines()[:8]:
        candidate = normalize_line(line)
        lowered = candidate.lower()
        if not candidate or lowered in NAME_BLACKLIST:
            continue
        if contains_price_or_calories(candidate):
            continue
        if looks_like_menu_item(candidate):
            continue
        if len(candidate.split()) <= 6 and not is_section_header(candidate):
            return candidate.title()

    cleaned_name = re.sub(r"[_-]+", " ", filename.rsplit(".", 1)[0]).strip()
    if cleaned_name and cleaned_name.lower() not in {"menu", "testmenu", "testmenu1", "uploaded"}:
        return cleaned_name.title()
    return "Uploaded Menu"


def extract_source_items(raw_text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for line in raw_text.splitlines():
        cleaned = normalize_line(line)
        if len(cleaned) < 5:
            continue
        if is_section_header(cleaned):
            continue
        if re.fullmatch(r"[$\d., ]+", cleaned):
            continue
        if not re.search(r"[a-zA-Z]", cleaned):
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        candidates.append(cleaned)
    return candidates[:60]


def infer_cuisine_signals(source_items: list[str]) -> list[str]:
    joined = " ".join(source_items).lower()
    scores: dict[str, int] = {}
    for label, keywords in CUISINE_KEYWORDS.items():
        score = sum(weight for phrase, weight in keywords if phrase_present(joined, phrase))
        if score:
            scores[label] = score

    if not scores:
        return ["Contemporary Casual"]

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_score = ranked[0][1]
    if top_score < 2:
        return ["Contemporary Casual"]

    selected = [label for label, score in ranked if score >= max(2, top_score - 1)]
    return selected[:2]


def infer_available_ingredients(source_items: list[str]) -> list[str]:
    joined = " ".join(source_items).lower()
    detected = detect_phrases(joined, VEGAN_INGREDIENT_HINTS)
    enriched = [item for item in detected if item not in GENERIC_INGREDIENTS]
    seen = set(enriched)

    for phrase, ingredient in FORMAT_SIGNAL_INGREDIENTS.items():
        if ingredient in seen:
            continue
        if phrase_present(joined, phrase):
            enriched.append(ingredient)
            seen.add(ingredient)

    return enriched[:28]


def infer_animal_ingredients(source_items: list[str]) -> list[str]:
    joined = " ".join(source_items).lower()
    return detect_phrases(joined, ANIMAL_INGREDIENTS)[:12]


def infer_missing_ingredients(available: list[str], cuisine_signals: list[str]) -> list[str]:
    suggestions_by_cuisine = {
        "Mexican": ["black beans", "chipotle", "salsa verde"],
        "Italian": ["cashew cream", "white beans", "oregano"],
        "Mediterranean": ["tahini", "mint", "sumac"],
        "Thai": ["tofu", "lemongrass", "thai basil"],
        "Indian": ["garam masala", "tofu", "coconut yogurt"],
        "American": ["vegan aioli", "pickled onion", "smoked paprika"],
        "Contemporary Casual": ["tofu", "herb oil", "pickled onion"],
    }
    recommended: list[str] = []
    available_set = set(available)
    for signal in cuisine_signals:
        for ingredient in suggestions_by_cuisine.get(signal, ()):
            if ingredient not in available_set:
                recommended.append(ingredient)
    return recommended[:6]


def normalize_line(line: str) -> str:
    cleaned = re.sub(r"\b\d{2,4}\s*cal\b", "", line, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -\t")
    return cleaned


def contains_price_or_calories(value: str) -> bool:
    return bool(re.search(r"\b\d+(?:\.\d+)?\b", value) or re.search(r"\bcal\b", value, re.IGNORECASE))


def is_section_header(value: str) -> bool:
    lowered = value.lower().strip("! ")
    if lowered.startswith("add chicken"):
        return True
    if "perfect to share" in lowered:
        return True
    normalized = lowered.rstrip(":").strip()
    return normalized in SECTION_HEADERS


def phrase_present(text: str, phrase: str) -> bool:
    pattern = r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b"
    return re.search(pattern, text) is not None


def detect_phrases(text: str, phrases: set[str]) -> list[str]:
    matches: list[tuple[int, str]] = []
    for phrase in phrases:
        pattern = r"\b" + r"\s+".join(re.escape(part) for part in phrase.split()) + r"\b"
        match = re.search(pattern, text)
        if match:
            matches.append((match.start(), phrase))

    matches.sort(key=lambda item: item[0])
    seen: set[str] = set()
    ordered: list[str] = []
    for _position, phrase in matches:
        if phrase in seen or phrase in STOPWORDS:
            continue
        seen.add(phrase)
        ordered.append(phrase)
    return ordered


def looks_like_menu_item(value: str) -> bool:
    lowered = value.lower()
    if value.isupper() and len(value.split()) >= 2:
        return True
    if detect_phrases(lowered, VEGAN_INGREDIENT_HINTS):
        return True
    if detect_phrases(lowered, ANIMAL_INGREDIENTS):
        return True
    return any(phrase_present(lowered, phrase) for phrase in ("bruschetta", "parmesan", "salad", "pizza"))
