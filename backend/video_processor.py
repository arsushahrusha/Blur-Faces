import cv2
import numpy as np
import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class FaceBoundingBox:
    x: int
    y: int
    width: int
    height: int

class VideoProcessor:
    def __init__(self):
        """Инициализация ТОЛЬКО с Haar cascade"""
        self.detector_type = 'haar'
        
        # Загружаем Haar cascade
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            raise RuntimeError("Failed to load Haar cascade detector")
        
        logger.info("✅ Haar cascade face detector initialized")

    def detect_faces(self, frame: np.ndarray) -> List[FaceBoundingBox]:
        """
        Детекция лиц с помощью Haar cascade
        """
        h, w = frame.shape[:2]
        faces = []
        
        try:
            # Конвертируем в grayscale (требование Haar cascade)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Детекция лиц с оптимальными параметрами
            detected_faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,      # Чувствительность к масштабу
                minNeighbors=4,       # Качество детекции
                minSize=(10, 10),     # Минимальный размер лица
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            # Обрабатываем найденные лица
            for (x, y, w, h) in detected_faces:
                # Добавляем margin вокруг лица
                margin_w = int(w * 0.2)
                margin_h = int(h * 0.25)
                
                faces.append(FaceBoundingBox(
                    x=max(0, x - margin_w),
                    y=max(0, y - margin_h),
                    width=min(frame.shape[1], w + 2 * margin_w),
                    height=min(frame.shape[0], h + 2 * margin_h),
                ))
                
            logger.debug(f"Detected {len(faces)} faces in frame")
            
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
        
        return faces

    def analyze_video(self, video_path: str, output_json_path: Optional[str] = None) -> Dict:
        """
        Анализ видео для обнаружения лиц
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        # Получаем информацию о видео
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"ANALYSIS: {total_frames} frames, {fps} FPS, {width}x{height}")
        
        # Настройки анализа
        frame_skip = 3          # Анализируем каждый 3-й кадр
        target_width = 640       # Разрешение для анализа
        
        faces_by_frame = {}
        previous_faces = []      # Для интерполяции между кадрами
        frame_number = 0
        
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_faces = []
            
            # Анализируем кадр с заданной частотой
            if frame_number % frame_skip == 0:
                # Уменьшаем разрешение для скорости
                analysis_frame = self._resize_frame(frame, target_width)
                current_faces = self.detect_faces(analysis_frame)
                
                # Масштабируем координаты обратно к исходному размеру
                if current_faces:
                    scale_w = width / analysis_frame.shape[1]
                    scale_h = height / analysis_frame.shape[0]
                    
                    scaled_faces = []
                    for face in current_faces:
                        scaled_faces.append(FaceBoundingBox(
                            x=int(face.x * scale_w),
                            y=int(face.y * scale_h),
                            width=int(face.width * scale_w),
                            height=int(face.height * scale_h),
                        ))
                    current_faces = scaled_faces
                
                previous_faces = current_faces
            else:
                # Используем лица из предыдущего кадра для плавности
                current_faces = previous_faces
            
            # Сохраняем результаты
            if current_faces:
                faces_by_frame[str(frame_number)] = [
                    {
                        'x': f.x, 
                        'y': f.y, 
                        'width': f.width, 
                        'height': f.height,
                    }
                    for f in current_faces
                ]
            
            # Логируем прогресс
            if frame_number % 100 == 0:
                elapsed = time.time() - start_time
                frames_per_sec = frame_number / elapsed if elapsed > 0 else 0
                logger.info(f"Frame {frame_number}/{total_frames} "
                           f"({frames_per_sec:.1f} FPS) - "
                           f"Found {len(faces_by_frame)} frames with faces")
            
            frame_number += 1
        
        cap.release()
        
        total_time = time.time() - start_time
        logger.info(f"✅ Analysis completed in {total_time:.1f} seconds")
        logger.info(f"📊 Results: {len(faces_by_frame)}/{total_frames} frames contain faces")
        
        # Формируем результат
        result = {
            'video_info': {
                'file_path': video_path,
                'fps': fps,
                'total_frames': total_frames,
                'duration': total_frames / fps if fps > 0 else 0,
                'width': width,
                'height': height
            },
            'faces_by_frame': faces_by_frame,
            'analysis_settings': {
                'frame_skip': frame_skip,
                'detector_type': self.detector_type,
                'processing_time': total_time
            }
        }
        
        # Сохраняем JSON если указан путь
        if output_json_path:
            self._save_to_json(result, output_json_path)
        
        return result

    def _resize_frame(self, frame: np.ndarray, target_width: int) -> np.ndarray:
        """Уменьшает кадр для быстрой обработки"""
        h, w = frame.shape[:2]
        if w > target_width:
            new_w = target_width
            new_h = int(h * target_width / w)
            return cv2.resize(frame, (new_w, new_h))
        return frame

    def _save_to_json(self, data: Dict, output_path: str):
        """Сохраняет данные в JSON файл"""
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Analysis results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")

    def process_video(self, input_path: str, output_path: str, 
                     masks_data: Dict, blur_strength: int = 25) -> bool:
        """
        Обрабатывает видео: применяет размытие к обнаруженным лицам
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open input video: {input_path}")
        
        # Параметры видео
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Создаем выходное видео
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            cap.release()
            raise ValueError(f"Cannot create output video: {output_path}")
        
        logger.info(f"PROCESSING: {total_frames} frames -> {output_path}")
        
        # Подготавливаем маски
        compiled_masks = {}
        for frame_key, masks in masks_data.items():
            try:
                frame_num = int(frame_key)
                compiled_masks[frame_num] = [
                    (mask['x'], mask['y'], mask['width'], mask['height'])
                    for mask in masks
                ]
            except (ValueError, KeyError):
                continue
        
        # Обработка кадров
        frame_number = 0
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Применяем размытие если есть маски для этого кадра
            if frame_number in compiled_masks:
                masks = compiled_masks[frame_number]
                frame = self._apply_blur(frame, masks, blur_strength)
            
            out.write(frame)
            frame_number += 1
            
            if frame_number % 60 == 0:  # Логируем каждую минуту
                elapsed = time.time() - start_time
                progress = (frame_number / total_frames) * 100
                logger.info(f"Processing: {progress:.1f}% complete")
        
        cap.release()
        out.release()
        
        total_time = time.time() - start_time
        logger.info(f"✅ Processing completed in {total_time:.1f} seconds")
        logger.info(f"💾 Output saved to: {output_path}")
        
        return True

    def _apply_blur(self, frame: np.ndarray, masks: list, blur_strength: int) -> np.ndarray:
        """Применяет размытие к областям с лицами"""
        if not masks:
            return frame
        
        result_frame = frame.copy()
        
        # Используем blur_strength для расчета размера ядра
        # Делаем ядро нечетным и зависимым от blur_strength
        kernel_size = max(3, blur_strength * 2 - 1)  # Минимальный размер 3, увеличиваем с blur_strength
        kernel_size = kernel_size + 1 if kernel_size % 2 == 0 else kernel_size  # Делаем нечетным
        
        for x, y, w, h in masks:
            # Проверяем границы
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
            
            if x2 > x1 and y2 > y1:
                roi = result_frame[y1:y2, x1:x2]
                if roi.size > 0:
                    blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
                    result_frame[y1:y2, x1:x2] = blurred_roi
        
        return result_frame

# Тестирование
if __name__ == "__main__":
    processor = VideoProcessor()
    
    # Тестируем на разных видео
    test_videos = [
        "C:/Users/Саныч/Desktop/videos/678558_University_College_1920x1080.mp4",
        "test_video1.mp4",
        "test_video2.mp4"
    ]
    
    for video_path in test_videos:
        if os.path.exists(video_path):
            print(f"\n=== Analyzing {video_path} ===")
            try:
                analysis = processor.analyze_video(video_path, "analysis.json")
                face_frames = len(analysis['faces_by_frame'])
                total_frames = analysis['video_info']['total_frames']
                print(f"Results: {face_frames}/{total_frames} frames have faces")
                
                if face_frames > 0:
                    output_path = video_path.replace('.mp4', '_blurred.mp4')
                    processor.process_video(video_path, output_path, analysis['faces_by_frame'])
                    print(f"Processed: {output_path}")
                else:
                    print("No faces found - skipping processing")
                    
            except Exception as e:
                print(f"Error processing {video_path}: {e}")