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
  reasoning: string;
  ingredients_used: string[];
};

type AnalysisResponse = {
  restaurant_name: string;
  cuisine_signals: string[];
  source_items: string[];
  ingredients: IngredientGroup;
  vegan_dishes: DishSuggestion[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

function statusTone(feasibility: string): string {
  if (feasibility === "Ready now") {
    return "status-pill status-ready";
  }

  if (feasibility === "Strong pantry fit") {
    return "status-pill status-strong";
  }

  return "status-pill status-possible";
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

  return (
    <main className="app-shell">
      <section className="hero-shell">
        <div className="hero-panel">
          <div className="hero-ribbon">VC Demo • Pantry-native vegan menu engine</div>
          <h1>Show every vegan dish a restaurant can already make.</h1>
          <p className="hero-lede">
            Upload a menu PDF and we infer the pantry already in play, then
            generate the full vegan dish set the kitchen can plausibly run right
            now. No fantasy SKUs. No blocker lists. Just what the restaurant
            already has.
          </p>

          <div className="hero-metrics">
            <article className="hero-metric">
              <strong>Pantry-native</strong>
              <p>Generated from ingredients already signaled by the current menu.</p>
            </article>
            <article className="hero-metric">
              <strong>Exhaustive mode</strong>
              <p>We surface all viable vegan dishes our engine can infer, not just 2-3 ideas.</p>
            </article>
            <article className="hero-metric">
              <strong>Boardroom-ready</strong>
              <p>Structured for fast storytelling in founder meetings, demos, and conferences.</p>
            </article>
          </div>
        </div>

        <form className="upload-panel" onSubmit={handleSubmit}>
          <div className="upload-top">
            <p className="section-label">Menu Input</p>
            <h2>Run a restaurant menu through investor-demo mode</h2>
            <p>
              Best on text-based PDFs. We map the current menu, infer the pantry,
              and return all viable vegan dishes grounded in existing ingredients.
            </p>
          </div>

          <label className="dropzone" htmlFor="menu-upload">
            <span className="dropzone-title">Drop in a restaurant menu PDF</span>
            <span className="dropzone-subtitle">
              PDF only • current pantry inferred from menu language
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
            {isSubmitting ? "Generating vegan menu..." : "Generate vegan menu"}
          </button>

          <div className="assumption-row">
            <span className="info-chip">No new ingredients assumed</span>
            <span className="info-chip">Uses current menu language</span>
            <span className="info-chip">Returns all viable dish concepts</span>
          </div>

          {error ? <p className="error-banner">{error}</p> : null}
        </form>
      </section>

      {result ? (
        <section className="results-shell">
          <section className="briefing-card">
            <div className="briefing-copy">
              <p className="section-label">Pantry-native Output</p>
              <h2>{result.restaurant_name}</h2>
              <p className="briefing-lede">
                We found {result.vegan_dishes.length} vegan dishes this kitchen can
                plausibly run from ingredients already signaled on the menu.
              </p>
            </div>

            <div className="briefing-tags">
              <span className="info-chip info-chip-strong">No new ingredients assumed</span>
              {result.cuisine_signals.map((signal) => (
                <span className="info-chip" key={signal}>
                  {signal}
                </span>
              ))}
            </div>
          </section>

          <div className="metrics-grid">
            <article className="metric-card">
              <span>Potential vegan dishes</span>
              <strong>{result.vegan_dishes.length}</strong>
              <p>All viable concepts inferred from the current pantry model.</p>
            </article>
            <article className="metric-card">
              <span>Pantry ingredients detected</span>
              <strong>{result.ingredients.available.length}</strong>
              <p>Signals we believe are already in the kitchen or on the line.</p>
            </article>
            <article className="metric-card">
              <span>Menu lines analyzed</span>
              <strong>{result.source_items.length}</strong>
              <p>Dish lines and menu text pulled directly from the restaurant PDF.</p>
            </article>
          </div>

          <section className="content-card">
            <div className="section-heading">
              <div>
                <p className="section-label">Possible Vegan Menu</p>
                <h3>All viable dishes inferred from the restaurant&apos;s current pantry</h3>
              </div>
              <p className="section-note">
                Every card below is built from ingredients already detected on the
                menu. No gap-fillers, no made-up pantry.
              </p>
            </div>

            <div className="dish-grid">
              {result.vegan_dishes.map((dish, index) => (
                <article className="dish-card" key={`${dish.name}-${index}`}>
                  <div className="dish-topline">
                    <span className="dish-index">{String(index + 1).padStart(2, "0")}</span>
                    <span className={statusTone(dish.feasibility)}>{dish.feasibility}</span>
                  </div>

                  <div className="dish-heading">
                    <p className="dish-category">{dish.category}</p>
                    <h4>{dish.name}</h4>
                  </div>

                  <p className="dish-reasoning">{dish.reasoning}</p>

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

        </section>
      ) : (
        <section className="preview-shell">
          <article className="preview-card">
            <p className="section-label">What The Demo Returns</p>
            <h2>A launchable vegan menu map, not a generic brainstorm.</h2>
            <div className="preview-grid">
              <div className="preview-panel">
                <strong>Current pantry model</strong>
                <p>We infer ingredients already on the line from menu language and dish formats.</p>
              </div>
              <div className="preview-panel">
                <strong>All viable vegan dishes</strong>
                <p>We return the full set of vegan dishes the kitchen can plausibly execute right now.</p>
              </div>
              <div className="preview-panel">
                <strong>Clean operator story</strong>
                <p>The output is built for quick explanation in meetings, not just internal analysis.</p>
              </div>
            </div>
          </article>
        </section>
      )}
    </main>
  );
}
