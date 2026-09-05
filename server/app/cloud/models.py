from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

AspectRatio = Literal["16:9", "9:16"]
VideoDuration = Literal[4, 6, 8]
VideoResolution = Literal["720p", "1080p"]
PersonGeneration = Literal["allow_adult", "disallow"]


class VeoGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4_000)
    aspect_ratio: AspectRatio = "9:16"
    duration_seconds: VideoDuration = 8
    resolution: VideoResolution = "1080p"
    sample_count: int = Field(default=1, ge=1, le=4)
    generate_audio: bool = True
    enhance_prompt: bool = True
    person_generation: PersonGeneration = "allow_adult"
    negative_prompt: str | None = Field(default=None, max_length=1_500)
    seed: int | None = Field(default=None, ge=0, le=4_294_967_295)
    image_gcs_uri: str | None = None
    image_mime_type: Literal["image/png", "image/jpeg", "image/webp"] = "image/png"
    last_frame_gcs_uri: str | None = None
    last_frame_mime_type: Literal["image/png", "image/jpeg", "image/webp"] = "image/png"

    @field_validator("image_gcs_uri", "last_frame_gcs_uri")
    @classmethod
    def validate_gcs_uri(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith("gs://") or ".." in value:
            raise ValueError("image inputs must be canonical gs:// URIs")
        return value

    @model_validator(mode="after")
    def validate_frames(self) -> "VeoGenerateRequest":
        if self.last_frame_gcs_uri and not self.image_gcs_uri:
            raise ValueError("last_frame_gcs_uri requires image_gcs_uri")
        return self


class VeoStatusRequest(BaseModel):
    operation_name: str = Field(min_length=20, max_length=1_000)


class DriveArchiveRequest(BaseModel):
    gcs_uri: str = Field(min_length=6, max_length=2_048)
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}$")

    @field_validator("gcs_uri")
    @classmethod
    def validate_gcs_uri(cls, value: str) -> str:
        if not value.startswith("gs://") or ".." in value:
            raise ValueError("gcs_uri must be a canonical gs:// URI")
        return value


class DriveJsonUploadRequest(BaseModel):
    name: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,119}\.json$")
    payload: dict[str, Any]
