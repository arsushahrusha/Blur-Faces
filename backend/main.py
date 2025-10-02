import os
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any

from video_processor import VideoProcessor
from models import *
from temp_storage import temp_storage

app = FastAPI(title="Video Face Blurring API", version="1.0.0")

# Настройка CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене заменить на конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Монтируем статические файлы для фронтенда
app.mount("/static", StaticFiles(directory="static"), name="static")

# Глобальные переменные
processor = VideoProcessor()

@app.post("/api/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """Загружает видео файл"""
    try:
        # Проверяем тип файла
        if not file.content_type.startswith('video/'):
            raise HTTPException(status_code=400, detail="File must be a video")
        
        # Генерируем ID для видео
        video_id = temp_storage.generate_video_id()
        
        # Создаем сессию
        temp_storage.create_session(video_id, file.filename)
        
        # Читаем и сохраняем файл
        content = await file.read()
        video_path = temp_storage.save_uploaded_file(video_id, content)
        
        # Получаем информацию о видео
        import cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        video_info = {
            "filename": file.filename,
            "fps": fps,
            "total_frames": total_frames,
            "duration": duration,
            "width": width,
            "height": height
        }
        
        return VideoUploadResponse(
            video_id=video_id,
            status="uploaded",
            message="Video uploaded successfully",
            video_info=video_info
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload error: {str(e)}")

@app.post("/api/analyze/{video_id}")
async def analyze_video(video_id: str, background_tasks: BackgroundTasks):
    """Запускает анализ видео в фоне"""
    try:
        video_path = temp_storage.get_video_path(video_id)
        if not video_path:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Обновляем статус
        temp_storage.update_session_status(video_id, ProcessingStatus.ANALYZING, "Analyzing video...", 10)
        
        # Запускаем анализ в фоне
        background_tasks.add_task(perform_analysis, video_id, video_path)
        
        return {"status": "analysis_started", "message": "Video analysis started"}
        
    except Exception as e:
        temp_storage.update_session_status(video_id, ProcessingStatus.ERROR, f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")

@app.get("/api/analysis/{video_id}")
async def get_analysis_result(video_id: str):
    """Возвращает результаты анализа"""
    try:
        analysis_result = temp_storage.get_analysis_result(video_id)
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        return analysis_result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting analysis: {str(e)}")


@app.post("/api/process/{video_id}")
async def process_video(video_id: str, request: ProcessRequest, background_tasks: BackgroundTasks):
    """Запускает обработку видео в фоне"""
    try:
        video_path = temp_storage.get_video_path(video_id)
        if not video_path:
            raise HTTPException(status_code=404, detail="Video not found")
        
        temp_storage.update_session_status(video_id, ProcessingStatus.PROCESSING, "Processing video...", 50)
        
        # Преобразуем Pydantic модели в обычные словари
        masks_dict = {}
        for frame_key, face_boxes in request.masks.items():
            masks_dict[str(frame_key)] = [
                {
                    'x': face.x,
                    'y': face.y, 
                    'width': face.width,
                    'height': face.height,
                }
                for face in face_boxes
            ]
        
        # Запускаем обработку в фоне
        background_tasks.add_task(perform_processing, video_id, video_path, masks_dict, request.blur_strength)
        
        return {"status": "processing_started", "message": "Video processing started"}
        
    except Exception as e:
        temp_storage.update_session_status(video_id, ProcessingStatus.ERROR, f"Processing error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.get("/api/frame/{video_id}/{frame_number}")
async def get_video_frame(video_id: str, frame_number: int):
    """Возвращает конкретный кадр видео"""
    try:
        #print(f"🔍 [DEBUG] Getting frame {frame_number} for video {video_id}")
        
        video_path = temp_storage.get_video_path(video_id)
        #print(f"🔍 [DEBUG] Video path: {video_path}")
        
        if not video_path or not os.path.exists(video_path):
            print("❌ [DEBUG] Video not found")
            raise HTTPException(status_code=404, detail="Video not found")
        
        import cv2
        cap = cv2.VideoCapture(video_path)
        
        # Получаем общее количество кадров для отладки
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        #print(f"🔍 [DEBUG] Total frames: {total_frames}, requested: {frame_number}")
        
        # Устанавливаем позицию кадра
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ret, frame = cap.read()
        cap.release()
        
        #print(f"🔍 [DEBUG] Frame read success: {ret}")
        
        if not ret:
            raise HTTPException(status_code=404, detail="Frame not found")
        
        # Кодируем кадр в JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        #print(f"✅ [DEBUG] Frame encoded successfully, size: {len(buffer)} bytes")
        
        return Response(content=buffer.tobytes(), media_type="image/jpeg")
        
    except Exception as e:
        print(f"❌ [DEBUG] Error getting frame: {str(e)}")
        import traceback
        print(f"❌ [DEBUG] Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Error getting frame: {str(e)}")

@app.post("/api/frame/{video_id}/{frame_number}/add_face")
async def add_face_to_frame(
    video_id: str, 
    frame_number: int,
    request: AddFaceRequest
):
    """Добавляет лицо на указанный кадр"""
    try:
        # Получаем текущие результаты анализа
        analysis_result = temp_storage.get_analysis_result(video_id)
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        frame_key = str(frame_number)
        
        # Добавляем новое лицо
        if frame_key not in analysis_result['faces_by_frame']:
            analysis_result['faces_by_frame'][frame_key] = []
        
        analysis_result['faces_by_frame'][frame_key].append({
            'x': request.x,
            'y': request.y,
            'width': request.width,
            'height': request.height,
            'manual': True
        })
        
        # Сохраняем обновленные результаты
        temp_storage.save_analysis_result(video_id, analysis_result)
        
        return {"status": "success", "message": "Face added successfully"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding face: {str(e)}")

@app.delete("/api/frame/{video_id}/{frame_number}/remove_face/{face_index}")
async def remove_face_from_frame(video_id: str, frame_number: int, face_index: int):
    """Удаляет лицо из указанного кадра"""
    try:
        analysis_result = temp_storage.get_analysis_result(video_id)
        if not analysis_result:
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        frame_key = str(frame_number)
        if frame_key in analysis_result['faces_by_frame']:
            if 0 <= face_index < len(analysis_result['faces_by_frame'][frame_key]):
                analysis_result['faces_by_frame'][frame_key].pop(face_index)
                
                # Если массив пуст, удаляем запись кадра
                if len(analysis_result['faces_by_frame'][frame_key]) == 0:
                    del analysis_result['faces_by_frame'][frame_key]
                
                temp_storage.save_analysis_result(video_id, analysis_result)
                return {"status": "success", "message": "Face removed successfully"}
        
        raise HTTPException(status_code=404, detail="Face not found")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error removing face: {str(e)}")

@app.post("/api/analysis/{video_id}/faces")
async def update_face_detection(video_id: str, request: Dict[str, Any]):
    """Обновляет результаты детекции лиц"""
    try:
        faces_by_frame = request.get('faces_by_frame', {})
        temp_storage.save_analysis_result(video_id, {'faces_by_frame': faces_by_frame})
        return {"status": "updated", "message": "Face detection updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating faces: {str(e)}")

@app.post("/api/analysis/{video_id}/update")
async def update_analysis_result(video_id: str, request: Dict[str, Any]):
    """Обновляет результаты анализа на сервере"""
    try:
        faces_by_frame = request.get('faces_by_frame', {})
        
        print(f"🔄 Updating analysis for video {video_id}")
        print(f"📊 New faces_by_frame keys: {list(faces_by_frame.keys())}")
        
        # Получаем текущий результат анализа
        current_result = temp_storage.get_analysis_result(video_id)
        if not current_result:
            raise HTTPException(status_code=404, detail="Analysis results not found")
        
        # Обновляем только faces_by_frame, сохраняя остальную информацию
        current_result['faces_by_frame'] = faces_by_frame
        
        # Сохраняем обновленные результаты
        temp_storage.save_analysis_result(video_id, current_result)
        
        print(f"✅ Analysis updated successfully. Total frames with faces: {len(faces_by_frame)}")
        
        return {"status": "updated", "message": "Analysis results updated successfully"}
    except Exception as e:
        print(f"❌ Error updating analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating analysis: {str(e)}")

@app.get("/api/status/{video_id}", response_model=StatusResponse)
async def get_processing_status(video_id: str):
    """Возвращает статус обработки видео"""
    session_info = temp_storage.get_session_info(video_id)
    if not session_info:
        raise HTTPException(status_code=404, detail="Video session not found")
    
    # Формируем URL для скачивания если видео готово
    download_url = None
    
    if session_info['status'] == ProcessingStatus.COMPLETED:
        download_url = f"/api/download/{video_id}"
    
    return StatusResponse(
        video_id=video_id,
        status=session_info['status'],
        progress=session_info['progress'],
        message=session_info['message'],
        download_url=download_url,
        error=None
    )

@app.get("/api/download/{video_id}")
async def download_video(video_id: str):
    """Скачивает обработанное видео"""
    output_path = temp_storage.get_output_path(video_id)
    if not output_path or not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Processed video not found")
    
    filename = f"blurred_{temp_storage.sessions[video_id]['original_filename']}"
    return FileResponse(output_path, filename=filename)

# Фоновые задачи
async def perform_analysis(video_id: str, video_path: str):
    """Выполняет анализ видео в фоне"""
    try:
        temp_storage.update_session_status(video_id, ProcessingStatus.ANALYZING, "Detecting faces...", 30)
        
        # Анализируем видео
        analysis_result = processor.analyze_video(video_path)
        
        # Сохраняем результаты
        temp_storage.save_analysis_result(video_id, analysis_result)
        temp_storage.update_session_status(video_id, ProcessingStatus.ANALYZED, "Analysis completed", 100)
        
    except Exception as e:
        temp_storage.update_session_status(video_id, ProcessingStatus.ERROR, f"Analysis failed: {str(e)}")

async def perform_processing(video_id: str, video_path: str, masks_data: Dict, blur_strength: int):
    """Выполняет обработку видео в фоне"""
    try:
        # Получаем результаты анализа
        analysis_result = temp_storage.get_analysis_result(video_id)
        if not analysis_result:
            raise Exception("Analysis results not found")
        
        # Обрабатываем видео (файл будет перезаписываться при каждом вызове)
        output_path = os.path.join(temp_storage.get_session_dir(video_id), "processed_video.mp4")
        
        success = processor.process_video(
            input_path=video_path,
            output_path=output_path,
            masks_data=masks_data,
            blur_strength=blur_strength,
        )
        
        if success:
            temp_storage.save_output_video(video_id, output_path)
            temp_storage.update_session_status(video_id, ProcessingStatus.COMPLETED, "Processing completed", 100)
        else:
            raise Exception("Video processing failed")
            
    except Exception as e:
        temp_storage.update_session_status(video_id, ProcessingStatus.ERROR, f"Processing failed: {str(e)}")
        
@app.get("/")
async def root():
    """Перенаправляет на фронтенд"""
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8000)