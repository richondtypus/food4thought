from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import AnalysisResponse
from app.services.generator import MenuContext, build_analysis
from app.services.menu_parser import extract_pdf_text

app = FastAPI(title="Vegan Menu Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-menu", response_model=AnalysisResponse)
async def analyze_menu(file: UploadFile = File(...)) -> AnalysisResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="A file name is required.")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="The uploaded PDF was empty.")

    try:
        raw_text = extract_pdf_text(file_bytes)
    except Exception as exc:  # pragma: no cover - defensive response
        raise HTTPException(status_code=422, detail="Could not extract text from the PDF.") from exc

    if not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text was found in the PDF. OCR support would be the next step.",
        )

    return build_analysis(MenuContext(filename=file.filename, raw_text=raw_text))
