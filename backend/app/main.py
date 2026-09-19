import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import STATIC_DIR
from app.schemas.common import ID_ERROR_MESSAGE
from app.schemas.field_labels import resolve_label
from app.exceptions import ConflictError, NotFoundError, UnprocessableError, ValidationFailedError
from app.routers import (
    clients,
    company_profile,
    dashboard,
    deadlines,
    expenses,
    health,
    home,
    invoices,
    notifications,
    payments,
    projects,
    quotes,
    reports,
)

logger = logging.getLogger("app")

app = FastAPI(title="EIAI TEC 事務管理システム")

# スキーマ作成はAlembicマイグレーション(起動時自動適用: app/migrate.py)のみで行う。import時にDBへ接続しない。

app.include_router(health.router)
app.include_router(clients.router)
app.include_router(company_profile.router)
app.include_router(invoices.router)
app.include_router(quotes.router)
app.include_router(expenses.router)
app.include_router(payments.router)
app.include_router(home.router)
app.include_router(dashboard.router)
app.include_router(projects.router)
app.include_router(notifications.router)
app.include_router(deadlines.router)
app.include_router(reports.router)


@app.exception_handler(ValidationFailedError)
async def handle_validation_error(request: Request, exc: ValidationFailedError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(UnprocessableError)
async def handle_unprocessable_error(request: Request, exc: UnprocessableError):
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def handle_not_found_error(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ConflictError)
async def handle_conflict_error(request: Request, exc: ConflictError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


# ID項目に数値以外が渡された場合にPydanticが返す型エラー(英語メッセージ)。日本語の統一文言へ置き換える。
_ID_TYPE_ERRORS = {"int_parsing", "int_type", "int_from_float", "int_parsing_size"}


def _is_id_type_error(error: dict) -> bool:
    loc = [part for part in error.get("loc", ()) if isinstance(part, str)]
    field = loc[-1] if loc else ""
    return error.get("type") in _ID_TYPE_ERRORS and (field == "id" or field.endswith("_id"))


def _localize_standard_error(error: dict, path: str) -> str | None:
    """必須欠落(missing)・文字数超過(string_too_long)を日本語化する。対象外や項目名未定義はNone。"""
    loc = [part for part in error.get("loc", ()) if isinstance(part, str)]
    field = loc[-1] if loc else ""
    label = resolve_label(path, field) if field != "body" else None
    if label is None:
        return None
    if error.get("type") == "missing":
        return f"{label}は必須です"
    if error.get("type") == "string_too_long":
        max_length = (error.get("ctx") or {}).get("max_length")
        if max_length is not None:
            return f"{label}は{max_length}文字以内で入力してください"
    return None


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    # FastAPI/Pydantic v2は標準では{"detail": [{"type":..., "loc":..., "msg":...}, ...]}という
    # 配列形式で返すが、フロントエンドは detail: string を前提としているため単一の文字列に変換する
    # (レビュー指摘1対応)。各スキーマのフィールドバリデータが raise ValueError(日本語メッセージ) した場合、
    # Pydanticはmsgを"Value error, <メッセージ>"の形に整形するため、そのプレフィックスは取り除く。
    message = "入力内容を確認してください"
    errors = exc.errors()
    if errors:
        raw_message = str(errors[0].get("msg", ""))
        prefix = "Value error, "
        message = raw_message[len(prefix):] if raw_message.startswith(prefix) else raw_message
        if _is_id_type_error(errors[0]):
            message = ID_ERROR_MESSAGE
        localized = _localize_standard_error(errors[0], request.url.path)
        if localized:
            message = localized
        if not message or message == "Field required":
            message = "入力内容を確認してください"
    return JSONResponse(status_code=422, content={"detail": message})


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    # 障害調査ができるよう、Uvicornの標準エラーログ(logs/uvicorn.log)へトレースバックを記録する
    # (レビュー指摘3対応)。
    logger.exception(
        "Unhandled exception while processing %s %s", request.method, request.url.path, exc_info=exc
    )
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
