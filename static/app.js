class VideoProcessorApp {
    constructor() {
        this.videoId = null;
        this.analysisResult = null;
        this.isProcessing = false;
        this.processVersion = 0;

        this.currentFrame = 0;
        this.isAddingFace = false;
        this.isRemovingFace = false;
        this.draggingFace = null;

        this.isDrawing = false;
        this.startX = 0;
        this.startY = 0;
        this.currentX = 0;
        this.currentY = 0;
        this.tempRect = null;

        this.videoScaleX = 1;
        this.videoScaleY = 1;
        this.canvasWidth = 800;
        this.canvasHeight = 450;

        this.initializeEventListeners();
    }
    calculateScaleFactors(videoWidth, videoHeight) {
        this.videoScaleX = this.canvasWidth / videoWidth;
        this.videoScaleY = this.canvasHeight / videoHeight;
    }

    videoToCanvas(x, y, width, height) {
        return {
            x: x * this.videoScaleX,
            y: y * this.videoScaleY,
            width: width * this.videoScaleX,
            height: height * this.videoScaleY
        };
    }

    canvasToVideo(x, y, width, height) {
        return {
            x: x / this.videoScaleX,
            y: y / this.videoScaleY,
            width: width / this.videoScaleX,
            height: height / this.videoScaleY
        };
    }

    initializeEventListeners() {
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const addFaceBtn = document.getElementById('addFaceBtn');
        const removeFaceBtn = document.getElementById('removeFaceBtn');
        const clearAllBtn = document.getElementById('clearAllBtn');
        const prevFrameBtn = document.getElementById('prevFrameBtn');
        const nextFrameBtn = document.getElementById('nextFrameBtn');
        const saveEditsBtn = document.getElementById('saveEditsBtn');
        const backToUploadBtn = document.getElementById('backToUploadBtn');

        if (addFaceBtn) addFaceBtn.addEventListener('click', () => this.toggleAddFaceMode());
        if (removeFaceBtn) removeFaceBtn.addEventListener('click', () => this.toggleRemoveFaceMode());
        if (clearAllBtn) clearAllBtn.addEventListener('click', () => this.clearCurrentFrameFaces());
        if (prevFrameBtn) prevFrameBtn.addEventListener('click', () => this.previousFrame());
        if (nextFrameBtn) nextFrameBtn.addEventListener('click', () => this.nextFrame());
        if (saveEditsBtn) saveEditsBtn.addEventListener('click', () => this.saveEdits());
        if (backToUploadBtn) backToUploadBtn.addEventListener('click', () => this.showStep('upload'));



        if (uploadArea && fileInput) {
            uploadArea.addEventListener('click', () => fileInput.click());
            uploadArea.addEventListener('dragover', (e) => {
                e.preventDefault();
                uploadArea.classList.add('dragover');
            });
            uploadArea.addEventListener('dragleave', () => {
                uploadArea.classList.remove('dragover');
            });
            uploadArea.addEventListener('drop', (e) => {
                e.preventDefault();
                uploadArea.classList.remove('dragover');
                const files = e.dataTransfer.files;
                if (files.length > 0) {
                    this.handleFileSelect(files[0]);
                }
            });

            fileInput.addEventListener('change', (e) => {
                if (e.target.files.length > 0) {
                    this.handleFileSelect(e.target.files[0]);
                }
            });
        } else {
            console.error('Upload elements not found');
        }

        // Analysis button
        const analyzeBtn = document.getElementById('analyzeBtn');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => {
                this.startAnalysis();
            });
        }

        // Blur strength slider
        const blurStrength = document.getElementById('blurStrength');
        if (blurStrength) {
            blurStrength.addEventListener('input', (e) => {
                document.getElementById('blurValue').textContent = e.target.value;
            });
        }

        // Process button
        const processBtn = document.getElementById('processBtn');
        if (processBtn) {
            processBtn.addEventListener('click', () => {
                this.processVideo();
            });
        }

        // Download button
        const downloadBtn = document.getElementById('downloadBtn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                this.downloadVideo();
            });
        }

        // New video button
        const newVideoBtn = document.getElementById('newVideoBtn');
        if (newVideoBtn) {
            newVideoBtn.addEventListener('click', () => {
                this.resetApp();
            });
        }
        const canvas = document.getElementById('faceCanvas');
        if (canvas) {
            canvas.addEventListener('click', (e) => this.handleCanvasClick(e));
            canvas.addEventListener('mousedown', (e) => this.handleCanvasMouseDown(e));
            canvas.addEventListener('mousemove', (e) => this.handleCanvasMouseMove(e));
            canvas.addEventListener('mouseup', (e) => this.handleCanvasMouseUp(e));
        }

        const skipEditingBtn = document.getElementById('skipEditingBtn');
        if (skipEditingBtn) {
            skipEditingBtn.addEventListener('click', () => {
                this.showStep('process');
            });
        }

        console.log('Event listeners initialized successfully');
    }

    async handleFileSelect(file) {
        console.log('File selected:', file.name);

        if (!file.type.startsWith('video/')) {
            this.showStatus('error', 'Please select a video file');
            return;
        }

        if (file.size > 500 * 1024 * 1024) {
            this.showStatus('error', 'File size must be less than 500MB');
            return;
        }

        this.showStatus('info', 'Uploading video...');

        try {
            const formData = new FormData();
            formData.append('file', file);

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Upload failed:', response.status, errorText);
                throw new Error(`Upload failed: ${response.status} ${response.statusText}`);
            }

            const result = await response.json();
            console.log('Upload response:', result);

            this.videoId = result.video_id;

            // ИНИЦИАЛИЗАЦИЯ МАСШТАБИРОВАНИЯ - ДОБАВЛЕНО
            if (result.video_info) {
                this.calculateScaleFactors(
                    result.video_info.width,
                    result.video_info.height
                );
                console.log(`🎯 Scale initialized: ${this.videoScaleX}x${this.videoScaleY} for video ${result.video_info.width}x${result.video_info.height}`);
            }

            // Show file info
            const fileInfo = document.getElementById('fileInfo');
            if (fileInfo) {
                fileInfo.innerHTML = `
                    <div class="file-info-content">
                        <strong>File:</strong> ${file.name}<br>
                        <strong>Size:</strong> ${this.formatFileSize(file.size)}<br>
                        <strong>Duration:</strong> ${result.video_info.duration.toFixed(1)}s<br>
                        <strong>Resolution:</strong> ${result.video_info.width}x${result.video_info.height}
                    </div>
                `;
                fileInfo.classList.remove('hidden');
            }

            // Setup original video
            const originalVideo = document.getElementById('originalVideo');
            if (originalVideo) {
                const videoUrl = URL.createObjectURL(file);
                originalVideo.src = videoUrl;
            }

            // Move to next step
            this.showStep('analyze');
            this.showStatus('success', 'Video uploaded successfully! Click "Start Analysis" to detect faces.');

        } catch (error) {
            console.error('Upload error:', error);
            this.showStatus('error', `Upload failed: ${error.message}`);
        }
    }

    async startAnalysis() {
        console.log('Starting analysis for video:', this.videoId);

        const analyzeBtn = document.getElementById('analyzeBtn');
        const progressContainer = document.getElementById('analyzeProgress');
        const statusDiv = document.getElementById('analyzeStatus');

        if (analyzeBtn) analyzeBtn.disabled = true;
        if (progressContainer) progressContainer.classList.remove('hidden');
        this.showStatus('info', 'Starting face detection...', statusDiv);

        try {
            const response = await fetch(`/api/analyze/${this.videoId}`, {
                method: 'POST'
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Analysis start failed:', response.status, errorText);
                throw new Error(`Analysis start failed: ${response.statusText}`);
            }

            console.log('Analysis started successfully');

            // Poll for status
            this.pollAnalysisStatus();

        } catch (error) {
            console.error('Analysis error:', error);
            if (analyzeBtn) analyzeBtn.disabled = false;
            this.showStatus('error', `Analysis failed: ${error.message}`, statusDiv);
        }
    }

    async pollAnalysisStatus() {
        const statusDiv = document.getElementById('analyzeStatus');
        const progressFill = document.getElementById('analyzeProgressFill');
        const progressText = document.getElementById('analyzeProgressText');

        const checkStatus = async () => {
            try {
                console.log('Checking status for video:', this.videoId);

                const response = await fetch(`/api/status/${this.videoId}`);
                if (!response.ok) {
                    console.error('Status check failed:', response.status);
                    return false;
                }

                const status = await response.json();
                console.log('Status response:', status);

                // Update progress
                if (progressFill) progressFill.style.width = `${status.progress}%`;
                if (progressText) progressText.textContent = `${Math.round(status.progress)}% - ${status.message}`;

                if (status.status === 'analyzed') {
                    this.showStatus('success', 'Analysis completed! Faces detected successfully.', statusDiv);
                    this.analysisResult = await this.getAnalysisResult();
                    if (analyzeBtn) analyzeBtn.disabled = false;
                    // ИСПРАВЛЕНИЕ: Переходим на шаг редактирования, а не сразу на обработку
                    this.showStep('edit'); // Было: this.showStep('process');

                    return true;
                } else if (status.status === 'error') {
                    this.showStatus('error', `Analysis failed: ${status.message || status.error}`, statusDiv);
                    const analyzeBtn = document.getElementById('analyzeBtn');
                    if (analyzeBtn) analyzeBtn.disabled = false;
                    return true;
                }

                // Continue polling
                setTimeout(checkStatus, 1000);
                return false;

            } catch (error) {
                console.error('Status check error:', error);
                this.showStatus('error', `Status check failed: ${error.message}`, statusDiv);
                const analyzeBtn = document.getElementById('analyzeBtn');
                if (analyzeBtn) analyzeBtn.disabled = false;
                return true;
            }
        };

        checkStatus();
    }

    async getAnalysisResult() {
        try {
            const response = await fetch(`/api/analysis/${this.videoId}`);
            if (!response.ok) {
                throw new Error(`Failed to get analysis results: ${response.status}`);
            }
            const result = await response.json();
            console.log('Analysis result frames:', Object.keys(result.faces_by_frame).length);
            return result;
        } catch (error) {
            console.error('Error getting analysis result:', error);
            throw error;
        }
    }

    async processVideo() {
        // Если уже идет обработка, выходим
        if (this.isProcessing) {
            console.log('Processing already in progress');
            return;
        }

        console.log('Starting video processing');

        const processBtn = document.getElementById('processBtn');
        const progressContainer = document.getElementById('processProgress');
        const statusDiv = document.getElementById('processStatus');

        this.isProcessing = true;
        if (processBtn) processBtn.disabled = true;
        if (progressContainer) progressContainer.classList.remove('hidden');

        const blurStrength = parseInt(document.getElementById('blurStrength').value);
        this.showStatus('info', `Starting video processing with blur strength: ${blurStrength}...`, statusDiv);

        try {
            const response = await fetch(`/api/process/${this.videoId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    masks: this.analysisResult.faces_by_frame,
                    blur_strength: blurStrength
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error('Processing start failed:', response.status, errorText);
                throw new Error(`Processing start failed: ${response.statusText}`);
            }

            console.log('Processing started successfully with blur strength:', blurStrength);

            // Poll for processing status
            this.pollProcessingStatus();

        } catch (error) {
            console.error('Processing error:', error);
            this.showStatus('error', `Processing failed: ${error.message}`, statusDiv);
            this.isProcessing = false;
            if (processBtn) processBtn.disabled = false;
        }
    }

    async pollProcessingStatus() {
        const statusDiv = document.getElementById('processStatus');
        const progressFill = document.getElementById('processProgressFill');
        const progressText = document.getElementById('processProgressText');
        const processBtn = document.getElementById('processBtn');

        const checkStatus = async () => {
            try {
                const response = await fetch(`/api/status/${this.videoId}`);
                if (!response.ok) return false;

                const status = await response.json();
                console.log('Processing status:', status);

                // Update progress
                if (progressFill) progressFill.style.width = `${status.progress}%`;
                if (progressText) progressText.textContent = `${Math.round(status.progress)}% - ${status.message}`;

                if (status.status === 'completed') {
                    const blurStrength = parseInt(document.getElementById('blurStrength').value);
                    this.processVersion++; // Увеличиваем версию при каждой обработке

                    this.showStatus('success', `Video processing completed with blur strength: ${blurStrength}! You can adjust blur strength and process again.`, statusDiv);

                    // Load processed video into player с уникальным URL
                    const processedVideo = document.getElementById('processedVideo');
                    if (processedVideo) {
                        const downloadUrl = `/api/download/${this.videoId}?v=${this.processVersion}&t=${new Date().getTime()}`;
                        processedVideo.src = downloadUrl;
                        console.log('Processed video URL:', downloadUrl, 'Blur strength:', blurStrength);

                        // Принудительно перезагружаем видео
                        processedVideo.load();
                    }

                    // Разблокируем кнопку для повторной обработки
                    this.isProcessing = false;
                    if (processBtn) processBtn.disabled = false;

                    return true;
                } else if (status.status === 'error') {
                    this.showStatus('error', `Processing failed: ${status.message || status.error}`, statusDiv);
                    this.isProcessing = false;
                    if (processBtn) processBtn.disabled = false;
                    return true;
                }

                // Continue polling
                setTimeout(checkStatus, 1000);
                return false;

            } catch (error) {
                console.error('Processing status check error:', error);
                this.showStatus('error', `Status check failed: ${error.message}`, statusDiv);
                this.isProcessing = false;
                if (processBtn) processBtn.disabled = false;
                return true;
            }
        };

        checkStatus();
    }

    downloadVideo() {
        if (this.videoId) {
            const downloadUrl = `/api/download/${this.videoId}`;
            console.log('Downloading from:', downloadUrl);
            window.open(downloadUrl, '_blank');
        } else {
            console.error('No video ID for download');
        }
    }

    resetApp() {
        console.log('Resetting app');

        // Reset all state
        this.videoId = null;
        this.analysisResult = null;
        this.isProcessing = false;
        this.processVersion = 0;

        // Reset UI
        this.showStep('upload');

        // Clear file input
        const fileInput = document.getElementById('fileInput');
        if (fileInput) fileInput.value = '';

        const fileInfo = document.getElementById('fileInfo');
        if (fileInfo) {
            fileInfo.classList.add('hidden');
            fileInfo.innerHTML = '';
        }

        // Clear videos
        const originalVideo = document.getElementById('originalVideo');
        if (originalVideo) originalVideo.src = '';

        const processedVideo = document.getElementById('processedVideo');
        if (processedVideo) processedVideo.src = '';

        // Clear status messages
        const analyzeStatus = document.getElementById('analyzeStatus');
        if (analyzeStatus) analyzeStatus.innerHTML = '';

        const processStatus = document.getElementById('processStatus');
        if (processStatus) processStatus.innerHTML = '';

        // Reset buttons
        const analyzeBtn = document.getElementById('analyzeBtn');
        if (analyzeBtn) analyzeBtn.disabled = false;

        const processBtn = document.getElementById('processBtn');
        if (processBtn) processBtn.disabled = false;

        // Reset progress bars
        const analyzeProgressFill = document.getElementById('analyzeProgressFill');
        if (analyzeProgressFill) analyzeProgressFill.style.width = '0%';

        const analyzeProgressText = document.getElementById('analyzeProgressText');
        if (analyzeProgressText) analyzeProgressText.textContent = '0%';

        const processProgressFill = document.getElementById('processProgressFill');
        if (processProgressFill) processProgressFill.style.width = '0%';

        const processProgressText = document.getElementById('processProgressText');
        if (processProgressText) processProgressText.textContent = '0%';

        // Reset blur strength
        const blurStrength = document.getElementById('blurStrength');
        const blurValue = document.getElementById('blurValue');
        if (blurStrength && blurValue) {
            blurStrength.value = 20;
            blurValue.textContent = '20';
        }
    }

    showStep(stepName) {
        console.log('Showing step:', stepName);

        // Hide all steps
        const steps = ['upload', 'analyze', 'edit', 'process'];
        steps.forEach(step => {
            const element = document.getElementById(`step-${step}`);
            if (element) {
                element.classList.add('hidden');
            }
        });

        // Show selected step
        const currentStep = document.getElementById(`step-${stepName}`);
        if (currentStep) {
            currentStep.classList.remove('hidden');

            // Если показываем редактор, инициализируем его
            if (stepName === 'edit') {
                this.initializeEditor();
            }

            console.log('Step displayed:', stepName);
        } else {
            console.error('Step element not found:', `step-${stepName}`);
        }
    }

    initializeEditor() {
        if (!this.analysisResult) return;

        const totalFrames = this.analysisResult.video_info.total_frames;
        document.getElementById('totalFrames').textContent = totalFrames;
        this.currentFrame = 0;
        this.loadFrame(this.currentFrame);
    }

    async loadFrame(frameNumber) {
        if (!this.videoId || !this.analysisResult) return;

        try {
            console.log(`🔄 [DEBUG] Loading frame ${frameNumber} for video ${this.videoId}`);

            const response = await fetch(`/api/frame/${this.videoId}/${frameNumber}`);
            console.log(`🔍 [DEBUG] Response status: ${response.status}`);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ [DEBUG] Frame load failed: ${response.status} - ${errorText}`);
                throw new Error(`Frame load failed: ${response.statusText}`);
            }

            const blob = await response.blob();
            console.log(`✅ [DEBUG] Frame blob received, size: ${blob.size} bytes`);

            const imageUrl = URL.createObjectURL(blob);

            const canvas = document.getElementById('faceCanvas');
            const ctx = canvas.getContext('2d');
            const img = new Image();

            img.onload = () => {
                console.log(`🖼️ [DEBUG] Image loaded, dimensions: ${img.width}x${img.height}`);

                // 1. Сначала рисуем изображение
                ctx.clearRect(0, 0, canvas.width, canvas.height);
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                // 2. Затем рисуем лица поверх изображения
                this.drawFacesForFrame(frameNumber);

                // 3. Сохраняем состояние для временного рисования
                this.originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);

                URL.revokeObjectURL(imageUrl);
                console.log(`✅ [DEBUG] Frame ${frameNumber} displayed successfully`);
            };

            img.onerror = (e) => {
                console.error(`❌ [DEBUG] Image load error:`, e);
                URL.revokeObjectURL(imageUrl);
            };

            img.src = imageUrl;

            // Update UI
            document.getElementById('currentFrame').textContent = frameNumber;
            document.getElementById('frameNumber').textContent = frameNumber;
            this.updateFacesList(frameNumber);

        } catch (error) {
            console.error('❌ Error loading frame:', error);
            this.showStatus('error', `Failed to load frame ${frameNumber}: ${error.message}`, document.getElementById('editStatus'));
        }
    }

    drawFacesForFrame(frameNumber) {
        const canvas = document.getElementById('faceCanvas');
        const ctx = canvas.getContext('2d');
        const frameKey = frameNumber.toString();

        // НЕ очищаем canvas здесь! Изображение уже нарисовано

        // Временно: рисуем красную рамку вокруг canvas для отладки
        ctx.strokeStyle = 'red';
        ctx.lineWidth = 2;
        ctx.strokeRect(0, 0, canvas.width, canvas.height);

        if (this.analysisResult.faces_by_frame[frameKey]) {
            this.analysisResult.faces_by_frame[frameKey].forEach((face, index) => {
                // МАСШТАБИРУЕМ КООРДИНАТЫ
                const scaledFace = this.videoToCanvas(face.x, face.y, face.width, face.height);

                console.log(`🎯 Face ${index}: original(${face.x},${face.y},${face.width},${face.height}) -> scaled(${scaledFace.x},${scaledFace.y},${scaledFace.width},${scaledFace.height})`);

                // Разный цвет для автоматических и ручных масок
                const isManual = face.manual;
                ctx.strokeStyle = isManual ? '#ff9900' : '#00ff00'; // Оранжевый для ручных, зеленый для авто
                ctx.lineWidth = 2;
                ctx.strokeRect(scaledFace.x, scaledFace.y, scaledFace.width, scaledFace.height);

                // Подпись с указанием типа
                ctx.fillStyle = isManual ? '#ff9900' : '#00ff00';
                ctx.font = '14px Arial';
                const label = isManual ? `Manual Face ${index + 1}` : `Face ${index + 1}`;
                ctx.fillText(label, scaledFace.x, scaledFace.y - 5);

                // Рисуем точку в центре для отладки
                ctx.fillStyle = 'blue';
                ctx.fillRect(
                    scaledFace.x + scaledFace.width / 2 - 2,
                    scaledFace.y + scaledFace.height / 2 - 2,
                    4, 4
                );
            });
        } else {
            console.log(`ℹ️ No faces detected in frame ${frameNumber}`);
        }
    }

    updateFacesList(frameNumber) {
        const facesList = document.getElementById('facesList');
        const frameKey = frameNumber.toString();

        if (!this.analysisResult.faces_by_frame[frameKey] ||
            this.analysisResult.faces_by_frame[frameKey].length === 0) {
            facesList.innerHTML = '<p>No faces detected in this frame</p>';
            return;
        }

        facesList.innerHTML = this.analysisResult.faces_by_frame[frameKey]
            .map((face, index) => `
                <div class="face-item" data-index="${index}">
                    <span>Face ${index + 1}</span>
                    <button class="btn-small" onclick="app.removeFace(${frameNumber}, ${index})">Remove</button>
                </div>
            `).join('');
    }

    toggleAddFaceMode() {
        this.isAddingFace = !this.isAddingFace;
        this.isRemovingFace = false;

        // Сбрасываем состояние рисования при выходе из режима
        if (!this.isAddingFace) {
            this.cancelDrawing();
        }

        const addFaceBtn = document.getElementById('addFaceBtn');
        if (addFaceBtn) {
            addFaceBtn.style.background = this.isAddingFace ? '#ff9900' : '';
        }

        const canvas = document.getElementById('faceCanvas');
        if (canvas) {
            canvas.style.cursor = this.isAddingFace ? 'crosshair' : 'default';
        }

        console.log(`🎨 Add face mode: ${this.isAddingFace}`);
    }

    toggleRemoveFaceMode() {
        this.isRemovingFace = !this.isRemovingFace;
        this.isAddingFace = false;

        const removeFaceBtn = document.getElementById('removeFaceBtn');
        if (removeFaceBtn) {
            removeFaceBtn.style.background = this.isRemovingFace ? '#ff4444' : '';
        }

        const canvas = document.getElementById('faceCanvas');
        if (canvas) {
            canvas.style.cursor = this.isRemovingFace ? 'not-allowed' : 'default';
        }
    }

    handleCanvasMouseDown(e) {
        if (!this.isAddingFace) return;

        const canvas = document.getElementById('faceCanvas');

        // Рассчитываем масштаб между CSS и реальными размерами
        const scaleX = canvas.width / canvas.offsetWidth;
        const scaleY = canvas.height / canvas.offsetHeight;

        this.isDrawing = true;
        this.startX = e.offsetX * scaleX;
        this.startY = e.offsetY * scaleY;
        this.currentX = this.startX;
        this.currentY = this.startY;

        console.log(`🎨 Start drawing at: (${this.startX}, ${this.startY}) scale: ${scaleX}x${scaleY}`);
    }

    handleCanvasMouseMove(e) {
        if (!this.isDrawing || !this.isAddingFace) return;

        const canvas = document.getElementById('faceCanvas');
        const scaleX = canvas.width / canvas.offsetWidth;
        const scaleY = canvas.height / canvas.offsetHeight;

        this.currentX = e.offsetX * scaleX;
        this.currentY = e.offsetY * scaleY;

        this.redrawCanvasWithTempRect();
    }

    handleCanvasMouseUp(e) {
        if (!this.isDrawing || !this.isAddingFace) return;

        const canvas = document.getElementById('faceCanvas');
        const scaleX = canvas.width / canvas.offsetWidth;
        const scaleY = canvas.height / canvas.offsetHeight;

        this.currentX = e.offsetX * scaleX;
        this.currentY = e.offsetY * scaleY;

        this.finishDrawing();
    }

    handleCanvasClick(e) {
        // Теперь клик используется только для отмены режима добавления
        if (this.isAddingFace && !this.isDrawing) {
            // Отменяем режим добавления при клике без рисования
            this.toggleAddFaceMode();
        }
    }

    async finishDrawing() {
        if (!this.isDrawing) return;

        // Вычисляем координаты и размер прямоугольника
        const x = Math.min(this.startX, this.currentX);
        const y = Math.min(this.startY, this.currentY);
        const width = Math.abs(this.currentX - this.startX);
        const height = Math.abs(this.currentY - this.startY);

        console.log(`🎨 Finished drawing canvas: (${x}, ${y}, ${width}, ${height})`);

        // Проверяем минимальный размер
        if (width < 20 || height < 20) {
            console.log('❌ Rectangle too small, ignoring');
            this.cancelDrawing();
            return;
        }

        // Преобразуем в координаты видео
        const videoCoords = this.canvasToVideo(x, y, width, height);
        console.log(`🎯 Video coords: (${videoCoords.x}, ${videoCoords.y}, ${videoCoords.width}, ${videoCoords.height})`);

        try {
            // Отправляем запрос на сервер для добавления лица
            const response = await fetch(`/api/frame/${this.videoId}/${this.currentFrame}/add_face`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    x: Math.round(videoCoords.x),
                    y: Math.round(videoCoords.y),
                    width: Math.round(videoCoords.width),
                    height: Math.round(videoCoords.height)
                })
            });

            if (!response.ok) {
                throw new Error(`Failed to add face: ${response.statusText}`);
            }

            const result = await response.json();
            console.log('✅ Face added successfully:', result);

            // Обновляем локальные данные
            this.analysisResult = await this.getAnalysisResult();

        } catch (error) {
            console.error('❌ Error adding face:', error);
            this.showStatus('error', `Failed to add face: ${error.message}`, document.getElementById('editStatus'));
        }

        // Сбрасываем состояние рисования
        this.cancelDrawing();
    }

    cancelDrawing() {
        this.isDrawing = false;
        this.tempRect = null;
        this.originalImageData = null; // Сбрасываем сохраненное изображение

        // Перерисовываем canvas
        this.loadFrame(this.currentFrame);
    }

    redrawCanvasWithTempRect() {
        const canvas = document.getElementById('faceCanvas');
        const ctx = canvas.getContext('2d');

        // Сохраняем оригинальное изображение
        if (!this.originalImageData) {
            this.originalImageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        }

        // Восстанавливаем оригинальное изображение
        ctx.putImageData(this.originalImageData, 0, 0);

        // Рисуем временный прямоугольник поверх
        if (this.isDrawing) {
            const x = Math.min(this.startX, this.currentX);
            const y = Math.min(this.startY, this.currentY);
            const width = Math.abs(this.currentX - this.startX);
            const height = Math.abs(this.currentY - this.startY);

            console.log(`🎨 Drawing temp rect: (${x}, ${y}, ${width}, ${height})`);

            // Рисуем полупрозрачный прямоугольник
            ctx.strokeStyle = '#ff9900';
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, width, height);

            // Заливка с прозрачностью
            ctx.fillStyle = 'rgba(255, 153, 0, 0.2)';
            ctx.fillRect(x, y, width, height);
        }
    }


    // addFace(frameNumber, x, y, width, height) {
    //     const frameKey = frameNumber.toString();

    //     if (!this.analysisResult.faces_by_frame[frameKey]) {
    //         this.analysisResult.faces_by_frame[frameKey] = [];
    //     }

    //     this.analysisResult.faces_by_frame[frameKey].push({
    //         x: Math.max(0, x),
    //         y: Math.max(0, y),
    //         width: width,
    //         height: height,
    //         confidence: 0.5, // Manual addition has lower confidence
    //         manual: true // Mark as manually added
    //     });

    //     this.loadFrame(frameNumber); // Reload to show new face
    // }

    async removeFace(frameNumber, faceIndex) {
        try {
            const response = await fetch(`/api/frame/${this.videoId}/${frameNumber}/remove_face/${faceIndex}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Failed to remove face');
            }

            // Всегда получаем свежие данные с сервера
            this.analysisResult = await this.getAnalysisResult();
            this.loadFrame(frameNumber);

        } catch (error) {
            console.error('❌ Error removing face:', error);
        }
    }

    async syncAnalysisResultWithServer() {
        try {
            console.log('🔄 Syncing analysis result with server...');

            const response = await fetch(`/api/analysis/${this.videoId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    faces_by_frame: this.analysisResult.faces_by_frame
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server returned ${response.status}: ${errorText}`);
            }

            const result = await response.json();
            console.log('✅ Analysis result synced with server:', result);

            return true;
        } catch (error) {
            console.error('❌ Error syncing with server:', error);
            this.showStatus('error', `Sync failed: ${error.message}`, document.getElementById('editStatus'));
            return false;
        }
    }

    async clearCurrentFrameFaces() {
        const frameKey = this.currentFrame.toString();
        delete this.analysisResult.faces_by_frame[frameKey];
        await this.syncAnalysisResultWithServer();
        this.loadFrame(this.currentFrame);
    }

    previousFrame() {
        if (this.currentFrame > 0) {
            this.currentFrame--;
            this.loadFrame(this.currentFrame);
        }
    }

    nextFrame() {
        const totalFrames = this.analysisResult.video_info.total_frames;
        if (this.currentFrame < totalFrames - 1) {
            this.currentFrame++;
            this.loadFrame(this.currentFrame);
        }
    }

    saveEdits() {
        // Analysis result already updated in memory
        this.showStep('process');
        this.showStatus('success', 'Face edits saved successfully!');
    }

    showStatus(type, message, element = null) {
        const statusElement = element || document.getElementById('analyzeStatus');
        if (statusElement) {
            statusElement.innerHTML = `
                <div class="status ${type}">
                    ${message}
                </div>
            `;
            console.log('Status:', type, message);
        }
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
}

// Initialize app when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing VideoProcessorApp...');
    try {
        // Сделать app глобальной переменной
        window.app = new VideoProcessorApp();
        console.log('VideoProcessorApp initialized successfully');
    } catch (error) {
        console.error('Failed to initialize VideoProcessorApp:', error);
    }
});