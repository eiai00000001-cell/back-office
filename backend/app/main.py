from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR
from app.database import Base, engine
from app.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.routers import clients, company_profile, expenses, health, home, invoices, payments, quotes

app = FastAPI(title="EIAI TEC 事務管理システム")

Base.metadata.create_all(bind=engine)

app.include_router(health.router)
app.include_router(clients.router)
app.include_router(company_profile.router)
app.include_router(invoices.router)
app.include_router(quotes.router)
app.include_router(expenses.router)
app.include_router(payments.router)
app.include_router(home.router)


@app.exception_handler(ValidationFailedError)
async def handle_validation_error(request: Request, exc: ValidationFailedError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def handle_not_found_error(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def handle_conflict_error(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "処理に失敗しました。しばらくしてから再度お試しください"},
    )


# 実運用時(EIAI TEC本人の日常利用)は、npm run buildの生成物をここで配信する(詳細設計書4.7.5)。
# 開発時はVite開発サーバーを使うため、静的ディレクトリが存在しない場合は何もしない。
# React Router(クライアントサイドルーティング)のブラウザ直接アクセス・リロードに対応するため、
# /assets配下は実ファイルを、それ以外のパス(/api/*を除く)はindex.htmlを返すSPAフォールバックとする。
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(STATIC_DIR / "assets")), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = STATIC_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")
