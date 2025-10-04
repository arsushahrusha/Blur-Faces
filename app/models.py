from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from enum import Enum

class ProcessingStatus(str, Enum):
    UPLOADED = "uploaded"
    ANALYZING = "analyzing" 
    ANALYZED = "analyzed"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class FaceBoundingBox(BaseModel):
    x: int = Field(..., description="X координата левого верхнего угла")
    y: int = Field(..., description="Y координата левого верхнего угла")
    width: int = Field(..., description="Ширина прямоугольника")
    height: int = Field(..., description="Высота прямоугольника")

class VideoUploadResponse(BaseModel):
    video_id: str = Field(..., description="Уникальный идентификатор видео")
    status: str = Field(..., description="Статус обработки")
    message: str = Field(..., description="Сообщение для пользователя")
    video_info: Optional[Dict] = Field(None, description="Информация о видео")

class AnalysisResult(BaseModel):
    video_info: Dict[str, Any]
    faces_by_frame: Dict[str, List[FaceBoundingBox]]
    analysis_settings: Dict[str, Any]

class ProcessRequest(BaseModel):
    masks: Dict[str, List[FaceBoundingBox]] = Field(..., description="Маски для размытия")
    blur_strength: int = Field(15, ge=1, le=50, description="Сила размытия (1-50)")

class FrameRequest(BaseModel):
    frame_number: int = Field(..., ge=0, description="Номер кадра")
    width: Optional[int] = Field(None, description="Ширина изображения")
    height: Optional[int] = Field(None, description="Высота изображения")

class FaceUpdateRequest(BaseModel):
    frame_number: int = Field(..., ge=0, description="Номер кадра")
    faces: List[FaceBoundingBox] = Field(..., description="Список лиц для этого кадра")

class BatchFaceUpdateRequest(BaseModel):
    faces_by_frame: Dict[str, List[FaceBoundingBox]] = Field(..., description="Лица по кадрам")

class AddFaceRequest(BaseModel):
    x: int
    y: int
    width: int
    height: int

class EditorState(BaseModel):
    current_frame: int = Field(0, ge=0, description="Текущий кадр")
    total_frames: int = Field(..., ge=1, description="Всего кадров")
    faces_by_frame: Dict[str, List[FaceBoundingBox]] = Field(..., description="Лица по кадрам")
    is_modified: bool = Field(False, description="Были ли внесены изменения")

class StatusResponse(BaseModel):
    video_id: str
    status: ProcessingStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: str
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None
    video_id: Optional[str] = None