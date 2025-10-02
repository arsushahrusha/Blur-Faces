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
    """Модель ограничивающего прямоугольника лица"""
    x: int = Field(..., description="X координата левого верхнего угла")
    y: int = Field(..., description="Y координата левого верхнего угла")
    width: int = Field(..., description="Ширина прямоугольника")
    height: int = Field(..., description="Высота прямоугольника")

class VideoUploadResponse(BaseModel):
    """Ответ на загрузку видео"""
    video_id: str = Field(..., description="Уникальный идентификатор видео")
    status: str = Field(..., description="Статус обработки")
    message: str = Field(..., description="Сообщение для пользователя")
    video_info: Optional[Dict] = Field(None, description="Информация о видео")

class AnalysisResult(BaseModel):
    """Результаты анализа видео"""
    video_info: Dict[str, Any]
    faces_by_frame: Dict[str, List[FaceBoundingBox]]
    analysis_settings: Dict[str, Any]

# class PreviewRequest(BaseModel):
#     """Запрос на генерацию превью"""
#     masks: Dict[str, List[FaceBoundingBox]] = Field(..., description="Маски для размытия")
#     blur_strength: int = Field(15, ge=1, le=50, description="Сила размытия (1-50)")
#     preview_duration: int = Field(10, ge=5, le=30, description="Длительность превью в секундах")

class ProcessRequest(BaseModel):
    """Запрос на обработку видео"""
    masks: Dict[str, List[FaceBoundingBox]] = Field(..., description="Маски для размытия")
    blur_strength: int = Field(15, ge=1, le=50, description="Сила размытия (1-50)")

class FrameRequest(BaseModel):
    """Запрос для получения кадра"""
    frame_number: int = Field(..., ge=0, description="Номер кадра")
    width: Optional[int] = Field(None, description="Ширина изображения")
    height: Optional[int] = Field(None, description="Высота изображения")

class FaceUpdateRequest(BaseModel):
    """Запрос на обновление данных о лицах"""
    frame_number: int = Field(..., ge=0, description="Номер кадра")
    faces: List[FaceBoundingBox] = Field(..., description="Список лиц для этого кадра")

class BatchFaceUpdateRequest(BaseModel):
    """Запрос на массовое обновление данных о лицах"""
    faces_by_frame: Dict[str, List[FaceBoundingBox]] = Field(..., description="Лица по кадрам")

class AddFaceRequest(BaseModel):
    x: int
    y: int
    width: int
    height: int

class EditorState(BaseModel):
    """Состояние редактора"""
    current_frame: int = Field(0, ge=0, description="Текущий кадр")
    total_frames: int = Field(..., ge=1, description="Всего кадров")
    faces_by_frame: Dict[str, List[FaceBoundingBox]] = Field(..., description="Лица по кадрам")
    is_modified: bool = Field(False, description="Были ли внесены изменения")

class StatusResponse(BaseModel):
    """Ответ со статусом обработки"""
    video_id: str
    status: ProcessingStatus
    progress: float = Field(0.0, ge=0.0, le=100.0)
    message: str
    download_url: Optional[str] = None
    preview_url: Optional[str] = None
    error: Optional[str] = None

class ErrorResponse(BaseModel):
    """Модель ошибки"""
    error: str
    details: Optional[str] = None
    video_id: Optional[str] = None