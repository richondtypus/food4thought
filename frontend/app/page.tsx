"use client";

import { useState } from "react";

type IngredientGroup = {
  available: string[];
  animal_based: string[];
};

type DishSuggestion = {
  name: string;
  category: string;
  feasibility: string;
  consumer_confidence: string;
  reasoning: string;
  ordering_tip: string;
  evidence_lines: string[];
  ingredients_used: string[];
};

type AnalysisResponse = {
  restaurant_name: string;
  cuisine_signals: string[];
  source_items: string[];
  ingredients: IngredientGroup;
  vegan_dishes: DishSuggestion[];
  notes: string[];
};

type SuggestionSection = {
  confidence: string;
  label: string;
  heading: string;
  note: string;
};

type ParsedEvidenceLine = {
  title: string;
  details: string | null;
  price: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

const suggestionSections: SuggestionSection[] = [
  {
    confidence: "Likely available now",
    label: "Best Bets",
    heading: "Likely available now",
    note: "These look closest to asks the kitchen could probably handle with the least friction.",
  },
  {
    confidence: "Likely available if you ask",
    label: "Askable Options",
    heading: "Likely available if you ask",
    note: "These suggestions still feel pantry-native, but they may need a clearer vegan request or a small adjustment.",
  },
  {
    confidence: "Worth asking about",
    label: "Stretch Asks",
    heading: "Worth asking about",
    note: "These are still grounded in the menu, but they feel more off-menu and should be treated as polite asks rather than expectations.",
  },
];

function statusTone(consumerConfidence: string): string {
  if (consumerConfidence === "Likely available now") {
    return "status-pill status-ready";
  }

  if (consumerConfidence === "Likely available if you ask") {
    return "status-pill status-strong";
  }

  return "status-pill status-possible";
}

function parseEvidenceLine(line: string): ParsedEvidenceLine {
  const trimmed = line.trim();
  const priceMatch = trimmed.match(/\s(\$?\d+(?:\.\d{1,2})?)$/);
  const price = priceMatch ? formatEvidencePrice(priceMatch[1]) : null;
  const withoutPrice = priceMatch
    ? trimmed.slice(0, trimmed.length - priceMatch[0].length).trim()
    : trimmed;

  const tokens = withoutPrice.split(/\s+/);
  const detailStart = findEvidenceDetailStart(tokens);
  const titleTokens =
    detailStart < tokens.length ? tokens.slice(0, detailStart) : tokens;
  const detailTokens =
    detailStart < tokens.length ? tokens.slice(detailStart) : [];

  return {
    title: prettifyEvidenceTitle(titleTokens.join(" ")),
    details: detailTokens.length
      ? prettifyEvidenceDetails(detailTokens.join(" "))
      : null,
    price,
  };
}

function findEvidenceDetailStart(tokens: string[]): number {
  let uppercaseLeadingCount = 0;

  for (const token of tokens) {
    if (/[a-z]/.test(token)) {
      break;
    }
    uppercaseLeadingCount += 1;
  }

  if (uppercaseLeadingCount >= 2 && uppercaseLeadingCount < tokens.length) {
    return uppercaseLeadingCount;
  }

  return tokens.length;
}

function prettifyEvidenceTitle(value: string): string {
  if (!/[a-z]/.test(value) && /[A-Z]/.test(value)) {
    return value.toLowerCase().replace(/\b[a-z]/g, (letter) => letter.toUpperCase());
  }

  return value;
}

function prettifyEvidenceDetails(value: string): string {
  const normalized = value.replace(/\s+/g, " ").trim();
  if (!normalized) {
    return normalized;
  }

  return normalized[0].toUpperCase() + normalized.slice(1);
}

function formatEvidencePrice(value: string): string {
  const numeric = Number(value.replace("$", ""));
  if (Number.isNaN(numeric)) {
    return value.startsWith("$") ? value : `$${value}`;
  }

  if (Number.isInteger(numeric)) {
    return `$${numeric.toFixed(0)}`;
  }

  return `$${numeric.toFixed(2)}`;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function lineIncludesPhrase(line: string, phrase: string): boolean {
  const pattern = new RegExp(
    `\\b${phrase.split(/\s+/).map(escapeRegExp).join("\\s+")}\\b`,
    "i",
  );
  return pattern.test(line);
}

function findLineMatches(line: string, phrases: string[]): string[] {
  return phrases.filter((phrase) => lineIncludesPhrase(line, phrase));
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!file) {
      setError("Choose a PDF menu to analyze.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_BASE}/analyze-menu`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        throw new Error(payload?.detail ?? "The analysis request failed.");
      }

      const data = (await response.json()) as AnalysisResponse;
      setResult(data);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "Something went wrong while analyzing the menu.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  const likelyNowCount =
    result?.vegan_dishes.filter((dish) => dish.consumer_confidence === "Likely available now")
      .length ?? 0;
  const askableCount =
    result?.vegan_dishes.filter((dish) => dish.consumer_confidence !== "Likely available now")
      .length ?? 0;
  const watchoutCount = result?.ingredients.animal_based.length ?? 0;

  return (
    <main className="app-shell">
      <section className="hero-shell">
        <div className="hero-panel">
          <div className="hero-ribbon">Pantry-native vegan finder</div>
          <h1>See what a restaurant can likely make vegan for you.</h1>
          <p className="hero-lede">
            Upload a menu PDF and we uncover the vegan-friendly dishes hiding in
            the kitchen&apos;s current pantry. The goal is not to invent fantasy
            meals. It&apos;s to help vegans see what a restaurant can plausibly make
            from ingredients already on the menu.
          </p>

          <div className="hero-metrics">
            <article className="hero-metric">
              <strong>Hidden vegan menu</strong>
              <p>We surface dishes the kitchen can likely assemble even if they are not listed as vegan.</p>
            </article>
            <article className="hero-metric">
              <strong>Askable, not imaginary</strong>
              <p>Every suggestion stays anchored to ingredients already signaled by the menu.</p>
            </article>
            <article className="hero-metric">
              <strong>Built for diners</strong>
              <p>You get confidence signals, menu evidence, and language you can actually use when ordering.</p>
            </article>
          </div>
        </div>

        <form className="upload-panel" onSubmit={handleSubmit}>
          <div className="upload-top">
            <p className="section-label">Menu Check</p>
            <h2>Upload a menu and uncover vegan options hiding in plain sight</h2>
            <p>
              Best on text-based PDFs. We read the current menu, infer the
              ingredients already in play, and turn that into vegan-friendly
              ordering guidance.
            </p>
          </div>

          <label className="dropzone" htmlFor="menu-upload">
            <span className="dropzone-title">Drop in a restaurant menu PDF</span>
            <span className="dropzone-subtitle">
              PDF only • pantry-native suggestions • diner-first output
            </span>
            <strong>{file?.name ?? "No file selected yet"}</strong>
          </label>

          <input
            id="menu-upload"
            className="sr-only"
            accept=".pdf"
            type="file"
            onChange={(event) => {
              setFile(event.target.files?.[0] ?? null);
              setResult(null);
              setError(null);
            }}
          />

          <button className="primary-button" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Checking the menu..." : "Find vegan-friendly options"}
          </button>

          <div className="assumption-row">
            <span className="info-chip">Pantry-native suggestions</span>
            <span className="info-chip">Consumer-first guidance</span>
            <span className="info-chip">Built from actual menu ingredients</span>
          </div>

          {error ? <p className="error-banner">{error}</p> : null}
        </form>
      </section>

      {result ? (
        <section className="results-shell">
          <section className="briefing-card">
            <div className="briefing-copy">
              <p className="section-label">Hidden Vegan Menu</p>
              <h2>{result.restaurant_name}</h2>
              <p className="briefing-lede">
                Based on the ingredients already signaled on this menu, here are{" "}
                {result.vegan_dishes.length} vegan-friendly orders worth trying.
                Think of these as the restaurant&apos;s hidden vegan menu, not just a
                brainstorm.
              </p>
            </div>

            <div className="briefing-tags">
              <span className="info-chip info-chip-strong">Pantry-native suggestions</span>
              {result.cuisine_signals.map((signal) => (
                <span className="info-chip" key={signal}>
                  {signal}
                </span>
              ))}
            </div>
          </section>

          <div className="metrics-grid">
            <article className="metric-card">
              <span>Best bets</span>
              <strong>{likelyNowCount}</strong>
              <p>Suggestions that feel closest to a low-friction vegan ask right now.</p>
            </article>
            <article className="metric-card">
              <span>Ask-worthy options</span>
              <strong>{askableCount}</strong>
              <p>Ideas that may still work if you mention the ingredients already on the menu.</p>
            </article>
            <article className="metric-card">
              <span>Animal-based watchouts</span>
              <strong>{watchoutCount}</strong>
              <p>Ingredients on the menu that may show up in sauces, finishes, or substitutions.</p>
            </article>
          </div>

          <div className="support-grid">
            <section className="content-card compact-card">
              <div className="section-heading compact-heading">
                <div>
                  <p className="section-label">How To Use This</p>
                  <h3>Order like a vegan regular, not like you are improvising</h3>
                </div>
                <p className="section-note">
                  The strongest asks mention ingredients the restaurant already uses.
                </p>
              </div>

              <ul className="note-list">
                {result.notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </section>

            <section className="content-card compact-card">
              <div className="section-heading compact-heading">
                <div>
                  <p className="section-label">Watchouts</p>
                  <h3>Ingredients worth double-checking before you order</h3>
                </div>
                <p className="section-note">
                  Menus often hide non-vegan finishes in sauces, dressings, or prep.
                </p>
              </div>

              {result.ingredients.animal_based.length ? (
                <>
                  <div className="ingredient-stack">
                    {result.ingredients.animal_based.map((ingredient) => (
                      <span className="ingredient-pill ingredient-pill-strong" key={ingredient}>
                        {ingredient}
                      </span>
                    ))}
                  </div>
                  <p className="support-copy">
                    These ingredients appeared on the menu, so it is worth
                    checking whether they show up in sauces, aiolis, dressings,
                    shared prep, or default add-ons.
                  </p>
                </>
              ) : (
                <p className="support-copy">
                  No obvious animal-based ingredients were flagged in the parsed
                  text, but it is still smart to confirm butter, cheese, stock,
                  and shared prep before treating anything as fully vegan.
                </p>
              )}
            </section>
          </div>

          {suggestionSections.map((section) => {
            const dishes = result.vegan_dishes.filter(
              (dish) => dish.consumer_confidence === section.confidence,
            );

            if (!dishes.length) {
              return null;
            }

            return (
              <section className="content-card" key={section.confidence}>
                <div className="section-heading">
                  <div>
                    <p className="section-label">{section.label}</p>
                    <h3>{section.heading}</h3>
                  </div>
                  <p className="section-note">{section.note}</p>
                </div>

                <div className="dish-grid">
                  {dishes.map((dish, index) => (
                    <article className="dish-card" key={`${dish.name}-${index}`}>
                      <div className="dish-topline">
                        <span className="dish-category">{dish.category}</span>
                        <span className={statusTone(dish.consumer_confidence)}>
                          {dish.consumer_confidence}
                        </span>
                      </div>

                      <div className="dish-heading">
                        <h4>{dish.name}</h4>
                      </div>

                      <p className="dish-reasoning">{dish.reasoning}</p>

                      {dish.evidence_lines.length ? (
                        <div className="evidence-block">
                          <span className="evidence-label">Why we think this could work</span>
                          <ul className="evidence-list">
                            {dish.evidence_lines.map((line) => {
                              const parsed = parseEvidenceLine(line);
                              const matchedIngredients = findLineMatches(
                                line,
                                dish.ingredients_used,
                              );
                              const lineWatchouts = findLineMatches(
                                line,
                                result.ingredients.animal_based,
                              );

                              return (
                                <li className="evidence-item" key={`${dish.name}-${line}`}>
                                  <div className="evidence-item-top">
                                    <h5 className="evidence-title">{parsed.title}</h5>
                                    {parsed.price ? (
                                      <span className="evidence-price">{parsed.price}</span>
                                    ) : null}
                                  </div>

                                  {parsed.details ? (
                                    <p className="evidence-details">{parsed.details}</p>
                                  ) : null}

                                  {matchedIngredients.length || lineWatchouts.length ? (
                                    <div className="evidence-tags">
                                      {matchedIngredients.map((ingredient) => (
                                        <span
                                          className="evidence-chip evidence-chip-match"
                                          key={`${line}-${ingredient}`}
                                        >
                                          Supports {ingredient}
                                        </span>
                                      ))}

                                      {lineWatchouts.map((ingredient) => (
                                        <span
                                          className="evidence-chip evidence-chip-watchout"
                                          key={`${line}-watchout-${ingredient}`}
                                        >
                                          Watchout {ingredient}
                                        </span>
                                      ))}
                                    </div>
                                  ) : null}
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      ) : null}

                      <div className="ordering-callout">
                        <span className="ordering-label">What to ask for</span>
                        <p>{dish.ordering_tip}</p>
                      </div>

                      <div className="ingredient-stack">
                        {dish.ingredients_used.map((ingredient) => (
                          <span className="ingredient-pill" key={`${dish.name}-${ingredient}`}>
                            {ingredient}
                          </span>
                        ))}
                      </div>
                    </article>
                  ))}
                </div>
              </section>
            );
          })}
        </section>
      ) : (
        <section className="preview-shell">
          <article className="preview-card">
            <p className="section-label">What You Get</p>
            <h2>A vegan ordering guide built from the menu the restaurant already has.</h2>
            <div className="preview-grid">
              <div className="preview-panel">
                <strong>Likely available now</strong>
                <p>Best bets that feel closest to something the kitchen can already do for a vegan diner.</p>
              </div>
              <div className="preview-panel">
                <strong>Likely if you ask</strong>
                <p>Suggestions anchored to current ingredients, plus language you can use when ordering.</p>
              </div>
              <div className="preview-panel">
                <strong>Menu watchouts</strong>
                <p>Animal-based ingredients flagged from the menu so you know where extra caution matters.</p>
              </div>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
