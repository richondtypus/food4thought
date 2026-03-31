# Vegan Menu Finder

A full-stack app that accepts a restaurant menu PDF, infers the ingredients and style already present in the kitchen, and uncovers realistic vegan-friendly dishes a diner could plausibly request from the existing pantry.

## Stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Poetry + Uvicorn
- AI-ready: OpenAI integration with a local heuristic fallback
- Data-ready: Supabase environment hooks for storage and persistence

## Project Structure

- `frontend/` - upload UI and consumer-facing vegan ordering guidance
- `backend/` - PDF parsing and pantry-native vegan suggestion API

## Local Development

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

## Environment Variables

### Frontend: `frontend/.env.local`

```bash
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

### Backend: `backend/.env`

```bash
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
```

The backend works without the OpenAI key by using deterministic heuristics. Supabase is optional in this scaffold.
