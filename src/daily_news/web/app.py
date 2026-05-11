from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from daily_news.config import AppConfig
from daily_news.storage.sqlite_store import SqliteArticleStore


TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parent / "templates"))


def create_app(config: AppConfig) -> FastAPI:
    app = FastAPI(title="daily-news admin")
    app.state.config = config

    @app.get("/", response_class=HTMLResponse)
    @app.get("/articles", response_class=HTMLResponse)
    def article_list(request: Request):
        with _store_context(config) as store:
            rows = store.list_for_admin()
        articles = [_row_to_view_model(request, row) for row in rows]
        return TEMPLATES.TemplateResponse(
            request=request,
            name="articles.html",
            context={
                "articles": articles,
                "request": request,
            },
        )

    @app.get("/articles/{external_id}", response_class=HTMLResponse)
    def article_detail(request: Request, external_id: str):
        with _store_context(config) as store:
            row = store.get_for_admin(external_id)
        if row is None:
            raise HTTPException(status_code=404, detail="Article not found")
        article = _row_to_view_model(request, row, include_full_content=True)
        return TEMPLATES.TemplateResponse(
            request=request,
            name="article_detail.html",
            context={
                "article": article,
                "request": request,
            },
        )

    @app.get("/artifacts/{external_id}/video")
    def article_video(external_id: str):
        with _store_context(config) as store:
            row = store.get_for_admin(external_id)
        if row is None or not row["video_path"]:
            raise HTTPException(status_code=404, detail="Video artifact not found")
        video_path = Path(row["video_path"])
        if not video_path.exists():
            raise HTTPException(status_code=404, detail="Video artifact missing on disk")
        return FileResponse(video_path, media_type="video/mp4", filename=video_path.name)

    @app.get("/artifacts/{external_id}/cover")
    def article_cover(external_id: str):
        with _store_context(config) as store:
            row = store.get_for_admin(external_id)
        if row is None or not row["cover_path"]:
            raise HTTPException(status_code=404, detail="Cover artifact not found")
        cover_path = Path(row["cover_path"])
        if not cover_path.exists():
            raise HTTPException(status_code=404, detail="Cover artifact missing on disk")
        return FileResponse(cover_path, media_type="image/png", filename=cover_path.name)

    return app


class _store_context:
    def __init__(self, config: AppConfig):
        self._config = config
        self._store: SqliteArticleStore | None = None

    def __enter__(self) -> SqliteArticleStore:
        self._store = SqliteArticleStore(self._config.database_file)
        return self._store

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._store is not None:
            self._store.close()


def _row_to_view_model(request: Request, row, include_full_content: bool = False) -> dict:
    summary = _parse_summary(row["summary_json"])
    local_video_url = None
    cover_url = None
    if row["video_path"]:
        local_video_url = str(request.url_for("article_video", external_id=row["external_id"]))
    if row["cover_path"]:
        cover_url = str(request.url_for("article_cover", external_id=row["external_id"]))
    return {
        "external_id": row["external_id"],
        "title": row["title"],
        "source_name": row["source_name"],
        "original_url": row["url"],
        "published_at": _optional_row_value(row, "published_at"),
        "author": _optional_row_value(row, "author"),
        "status": row["status"],
        "is_published": row["status"] == "published",
        "summary": summary.get("summary"),
        "headline": summary.get("headline"),
        "key_points": summary.get("key_points", []),
        "script": summary.get("script"),
        "content_text": _optional_row_value(row, "content_text") if include_full_content else None,
        "publish_output": _optional_row_value(row, "publish_output"),
        "published_video_id": _optional_row_value(row, "published_video_id"),
        "published_video_url": row["published_video_url"],
        "local_video_url": local_video_url,
        "cover_url": cover_url,
        "last_error_stage": row["last_error_stage"],
        "last_error": row["last_error"],
        "updated_at": row["updated_at"],
        "created_at": row["created_at"],
    }


def _parse_summary(summary_json: str | None) -> dict:
    if not summary_json:
        return {}
    try:
        payload = json.loads(summary_json)
    except json.JSONDecodeError:
        return {"summary": summary_json}
    return {
        "headline": payload.get("headline"),
        "summary": payload.get("summary"),
        "key_points": payload.get("key_points") or [],
        "script": payload.get("script"),
    }


def _optional_row_value(row, key: str):
    if key in row.keys():
        return row[key]
    return None
