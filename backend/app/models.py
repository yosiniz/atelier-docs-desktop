from typing import Any

from pydantic import BaseModel, Field


class ApiError(BaseModel):
    code: str
    message: str
    detail: str | None = None


class ApiResponse(BaseModel):
    ok: bool = True
    data: dict | list | None = None
    error: ApiError | None = None


class TextStyle(BaseModel):
    font_size: float = Field(default=11, ge=4, le=144)
    font_family: str | None = Field(default=None, max_length=100)
    color: str = Field(default="#111827", pattern=r"^#[0-9a-fA-F]{6}$")
    align: str = Field(default="left", pattern=r"^(left|center|right|justify)$")
    bold: bool = False
    italic: bool = False
    underline: bool = False


class TextEditRequest(BaseModel):
    page: int = Field(ge=0)
    rect: tuple[float, float, float, float]
    target_rect: tuple[float, float, float, float] | None = None
    source_baseline: float | None = None
    text: str = Field(max_length=10000)
    original_text: str = Field(default="", max_length=10000)
    style: TextStyle = Field(default_factory=TextStyle)
    preserve_style: bool = False


class TextStyleProbeRequest(BaseModel):
    page: int = Field(ge=0)
    rect: tuple[float, float, float, float]
    original_text: str = Field(default="", max_length=10000)


class SearchReplaceRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    replacement: str = Field(default="", max_length=5000)
    case_sensitive: bool = False
    whole_word: bool = False
    pages: list[int] | None = None


class RotateRequest(BaseModel):
    pages: list[int]
    angle: int


class SplitRequest(BaseModel):
    ranges: list[str]


class CompressRequest(BaseModel):
    level: str = Field(default="balanced", pattern=r"^(quality|balanced|small)$")


class DeletePagesRequest(BaseModel):
    pages: list[int] = Field(min_length=1)


class ReorderPagesRequest(BaseModel):
    order: list[int] = Field(min_length=1)


class CropPageRequest(BaseModel):
    page: int = Field(ge=0)
    rect: tuple[float, float, float, float]


class BlankPageRequest(BaseModel):
    after_page: int = Field(default=-1, ge=-1)
    width: float | None = Field(default=None, ge=72, le=5000)
    height: float | None = Field(default=None, ge=72, le=5000)


class PageDecorationRequest(BaseModel):
    header: str = Field(default="", max_length=500)
    footer: str = Field(default="", max_length=500)
    page_numbers: bool = True
    start_number: int = Field(default=1, ge=0, le=1_000_000)
    pages: list[int] | None = None
    font_size: float = Field(default=9, ge=4, le=36)
    color: str = Field(default="#4b5563", pattern=r"^#[0-9a-fA-F]{6}$")
    margin: float = Field(default=28, ge=8, le=144)


class AddTextRequest(BaseModel):
    page: int = Field(ge=0)
    rect: tuple[float, float, float, float]
    text: str = Field(min_length=1, max_length=10000)
    style: TextStyle = Field(default_factory=TextStyle)


class ShapeRequest(BaseModel):
    page: int = Field(ge=0)
    kind: str = Field(pattern=r"^(rectangle|ellipse|line)$")
    rect: tuple[float, float, float, float]
    stroke_color: str = Field(default="#6d5dfc", pattern=r"^#[0-9a-fA-F]{6}$")
    fill_color: str | None = Field(default=None, pattern=r"^#[0-9a-fA-F]{6}$")
    width: float = Field(default=1.5, ge=0.25, le=20)


class RedactRequest(BaseModel):
    page: int = Field(ge=0)
    rects: list[tuple[float, float, float, float]] = Field(min_length=1, max_length=100)


class InkRequest(BaseModel):
    page: int = Field(ge=0)
    paths: list[list[tuple[float, float]]] = Field(min_length=1, max_length=100)
    color: str = Field(default="#172033", pattern=r"^#[0-9a-fA-F]{6}$")
    width: float = Field(default=2, ge=0.25, le=30)


class MoveImageRequest(BaseModel):
    page: int = Field(ge=0)
    xref: int = Field(ge=1)
    source_rect: tuple[float, float, float, float]
    target_rect: tuple[float, float, float, float]


class EncryptRequest(BaseModel):
    user_password: str = Field(min_length=4, max_length=128)
    owner_password: str | None = Field(default=None, min_length=4, max_length=128)
    allow_print: bool = True
    allow_copy: bool = False
    allow_annotate: bool = False


class UnlockRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class MetadataRequest(BaseModel):
    title: str = Field(default="", max_length=500)
    author: str = Field(default="", max_length=500)
    subject: str = Field(default="", max_length=1000)
    keywords: str = Field(default="", max_length=1000)


class OfficeSaveRequest(BaseModel):
    updates: list[dict[str, Any]] = Field(default_factory=list, max_length=5000)


class OcrRequest(BaseModel):
    language: str = Field(default="tur+eng", pattern=r"^[a-z]{3}(\+[a-z]{3})*$")
    dpi: int = Field(default=300, ge=120, le=400)
    force: bool = False
    layout: str = Field(default="auto", pattern=r"^(auto|document|table|sparse)$")
    enhance: bool = True
    deskew: bool = True
    pages: list[int] | None = Field(default=None, min_length=1, max_length=500)


class WatermarkRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    pages: list[int] | None = None
    font_size: float = Field(default=42, ge=8, le=144)
    color: str = Field(default="#9ca3af", pattern=r"^#[0-9a-fA-F]{6}$")
    opacity: float = Field(default=0.25, ge=0.05, le=1)
    rotation: int = Field(default=0)


class WatermarkRemoveRequest(BaseModel):
    pages: list[int] | None = None


class LinkRequest(BaseModel):
    page: int = Field(ge=0)
    rect: tuple[float, float, float, float]
    uri: str = Field(min_length=4, max_length=2000)
