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
        self.detector_type = 'haar'
        
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            raise RuntimeError("Failed to load Haar cascade detector")
        
        logger.info("Haar cascade face detector initialized")

    def detect_faces(self, frame: np.ndarray) -> List[FaceBoundingBox]:
        h, w = frame.shape[:2]
        faces = []
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
            detected_faces = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,      
                minNeighbors=4,      
                minSize=(10, 10),    
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            
            for (x, y, w, h) in detected_faces:
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
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        logger.info(f"ANALYSIS: {total_frames} frames, {fps} FPS, {width}x{height}")
        
        frame_skip = 3        
        target_width = 640       
        
        faces_by_frame = {}
        previous_faces = []   
        frame_number = 0
        
        start_time = time.time()
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            current_faces = []
            
            if frame_number % frame_skip == 0:
                analysis_frame = self._resize_frame(frame, target_width)
                current_faces = self.detect_faces(analysis_frame)
                
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
                current_faces = previous_faces
            
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
            
            if frame_number % 100 == 0:
                elapsed = time.time() - start_time
                frames_per_sec = frame_number / elapsed if elapsed > 0 else 0
                logger.info(f"Frame {frame_number}/{total_frames} "
                           f"({frames_per_sec:.1f} FPS) - "
                           f"Found {len(faces_by_frame)} frames with faces")
            
            frame_number += 1
        
        cap.release()
        
        total_time = time.time() - start_time
        logger.info(f"Analysis completed in {total_time:.1f} seconds")
        logger.info(f"Results: {len(faces_by_frame)}/{total_frames} frames contain faces")
     
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
        
        if output_json_path:
            self._save_to_json(result, output_json_path)
        
        return result

    def _resize_frame(self, frame: np.ndarray, target_width: int) -> np.ndarray:
        h, w = frame.shape[:2]
        if w > target_width:
            new_w = target_width
            new_h = int(h * target_width / w)
            return cv2.resize(frame, (new_w, new_h))
        return frame

    def _save_to_json(self, data: Dict, output_path: str):
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
                
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis results saved to: {output_path}")
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")

    def process_video(self, input_path: str, output_path: str, 
                        masks_data: Dict, blur_strength: int = 25) -> bool:
        import subprocess
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input video not found: {input_path}")
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open input video: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        ffmpeg_cmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-pix_fmt', 'bgr24',
            '-s', f'{width}x{height}',
            '-r', str(fps),
            '-i', '-', 
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-f', 'mp4',
            output_path
        ]
        
        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
        
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
        
        frame_number = 0
        start_time = time.time()
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if frame_number in compiled_masks:
                    masks = compiled_masks[frame_number]
                    frame = self._apply_blur(frame, masks, blur_strength)
                
                ffmpeg_process.stdin.write(frame.tobytes())
                
                frame_number += 1
                
                if frame_number % 60 == 0:
                    elapsed = time.time() - start_time
                    progress = (frame_number / total_frames) * 100
                    logger.info(f"Processing: {progress:.1f}% complete")
                    
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            return False
        finally:
            cap.release()
            ffmpeg_process.stdin.close()
            ffmpeg_process.wait()
        
        total_time = time.time() - start_time
        logger.info(f"H.264 processing completed in {total_time:.1f} seconds")
        return True

    def _apply_blur(self, frame: np.ndarray, masks: list, blur_strength: int) -> np.ndarray:
        if not masks:
            return frame
        
        result_frame = frame.copy()
        kernel_size = max(3, blur_strength * 2 - 1)  
        kernel_size = kernel_size + 1 if kernel_size % 2 == 0 else kernel_size  
        
        for x, y, w, h in masks:
            x1, y1 = max(0, x), max(0, y)
            x2, y2 = min(frame.shape[1], x + w), min(frame.shape[0], y + h)
            
            if x2 > x1 and y2 > y1:
                roi = result_frame[y1:y2, x1:x2]
                if roi.size > 0:
                    blurred_roi = cv2.GaussianBlur(roi, (kernel_size, kernel_size), 0)
                    result_frame[y1:y2, x1:x2] = blurred_roi
        
        return result_frame