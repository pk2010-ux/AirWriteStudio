// AirWrite Studio Web Demo - app.js
// All gesture detection runs on the Python backend via /api/process_frame
// This file handles: UI, camera, canvas drawing, and rendering backend results.

document.addEventListener('DOMContentLoaded', () => {
    // ========== MODAL ==========
    const modal = document.getElementById('startup-modal');
    document.getElementById('close-modal-btn').addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // ========== UI ELEMENTS ==========
    const videoElement = document.getElementById('camera-feed');
    const cameraPlaceholder = document.getElementById('camera-placeholder');
    const cameraToggleBtn = document.getElementById('camera-toggle-btn');

    const gestureDot = document.querySelector('.gesture-dot');
    const gestureIcon = document.querySelector('.gesture-icon');
    const gestureLabel = document.querySelector('.gesture-label');
    const gestureDesc = document.querySelector('.gesture-description');
    const handStatus = document.querySelector('.hand-status');
    const fpsLabel = document.querySelector('.fps-label');

    const colorSwatches = document.querySelectorAll('.color-swatch');
    const penSizeSlider = document.getElementById('pen-size');
    const eraserSizeSlider = document.getElementById('eraser-size');
    const clearCanvasBtn = document.querySelector('.danger-button');

    const canvasElement = document.getElementById('drawing-canvas');
    const canvasCtx = canvasElement.getContext('2d');
    const canvasPlaceholderUI = document.getElementById('canvas-placeholder');

    // ========== CANVAS SETUP ==========
    function resizeCanvas() {
        const rect = canvasElement.parentElement.getBoundingClientRect();
        // Save existing drawing
        const imageData = canvasCtx.getImageData(0, 0, canvasElement.width, canvasElement.height);
        canvasElement.width = rect.width;
        canvasElement.height = rect.height;
        canvasCtx.putImageData(imageData, 0, 0);
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // ========== STATE ==========
    let isCameraRunning = false;
    let cameraStream = null;
    let currentColor = '#FFFFFF';
    let penSize = 3.0;
    let eraserSize = 20.0;

    // Drawing
    let paths = [];       // { color, size, points: [{x,y}] }
    let currentPath = null;
    let isDrawing = false;
    let lastActionPoint = null;
    let currentGesture = 'neutral';

    // Gesture display config (matches your Python config.py)
    const GESTURE_INFO = {
        neutral:  { label: 'Neutral',  icon: 'fa-solid fa-hand',     color: '#555555', desc: 'Open palm — no action' },
        pen:      { label: 'Drawing',  icon: 'fa-solid fa-pencil',   color: '#0091FF', desc: 'Thumb + Index pinch — draw' },
        eraser:   { label: 'Erasing',  icon: 'fa-solid fa-eraser',   color: '#E5484D', desc: 'Thumb out, fingers curled — erase' },
        select:   { label: 'Select',   icon: 'fa-solid fa-arrow-pointer', color: '#AB6400', desc: 'Index finger point — select' },
        drag:     { label: 'Dragging', icon: 'fa-solid fa-up-down-left-right', color: '#AB6400', desc: 'Three fingers — drag selected' },
        zoom_in:  { label: 'Zoom In',  icon: 'fa-solid fa-magnifying-glass-plus', color: '#46A758', desc: 'Thumb + Middle — scale up' },
        zoom_out: { label: 'Zoom Out', icon: 'fa-solid fa-magnifying-glass-minus', color: '#46A758', desc: 'Thumb + Ring — scale down' },
    };

    // ========== UI HANDLERS ==========
    colorSwatches.forEach(swatch => {
        swatch.addEventListener('click', () => {
            colorSwatches.forEach(s => s.classList.remove('selected'));
            swatch.classList.add('selected');
            currentColor = swatch.style.backgroundColor || swatch.getAttribute('title');
        });
    });

    penSizeSlider.addEventListener('input', (e) => {
        penSize = e.target.value / 10;
        e.target.nextElementSibling.textContent = penSize.toFixed(1);
    });

    eraserSizeSlider.addEventListener('input', (e) => {
        eraserSize = parseInt(e.target.value);
        e.target.nextElementSibling.textContent = Math.round(eraserSize);
    });

    clearCanvasBtn.addEventListener('click', () => {
        paths = [];
        currentPath = null;
        isDrawing = false;
        redrawCanvas();
    });

    function updateGestureUI(gesture) {
        const info = GESTURE_INFO[gesture] || GESTURE_INFO.neutral;
        gestureDot.style.backgroundColor = info.color;
        gestureIcon.innerHTML = `<i class="${info.icon}"></i>`;
        gestureLabel.textContent = info.label;
        gestureLabel.style.color = info.color;
        gestureDesc.textContent = info.desc;
    }

    function updateHandStatus(detected) {
        if (detected) {
            handStatus.innerHTML = '<i class="fa-solid fa-hand"></i> Hand detected';
            handStatus.style.color = '#4ECDC4';
        } else {
            handStatus.innerHTML = '<i class="fa-solid fa-hand"></i> No hand detected';
            handStatus.style.color = '#9898b0';
        }
    }

    // ========== DRAWING ==========
    function redrawCanvas() {
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        canvasPlaceholderUI.style.display = paths.length > 0 ? 'none' : 'block';

        paths.forEach(path => {
            if (path.points.length < 2) return;
            canvasCtx.beginPath();
            canvasCtx.moveTo(path.points[0].x, path.points[0].y);
            for (let i = 1; i < path.points.length; i++) {
                // Use quadratic curves for smoothness
                const prev = path.points[i - 1];
                const curr = path.points[i];
                const mx = (prev.x + curr.x) / 2;
                const my = (prev.y + curr.y) / 2;
                canvasCtx.quadraticCurveTo(prev.x, prev.y, mx, my);
            }
            canvasCtx.strokeStyle = path.color;
            canvasCtx.lineWidth = path.size;
            canvasCtx.lineCap = 'round';
            canvasCtx.lineJoin = 'round';
            canvasCtx.stroke();
        });
    }

    function eraseAt(x, y, radius) {
        let changed = false;
        paths = paths.filter(path => {
            for (const pt of path.points) {
                if (Math.hypot(pt.x - x, pt.y - y) < radius) {
                    changed = true;
                    return false;
                }
            }
            return true;
        });
        if (changed) redrawCanvas();
    }

    // ========== BACKEND COMMUNICATION ==========
    let isProcessing = false;
    let fpsFrames = 0;
    let lastFpsTime = performance.now();

    async function processLoop() {
        if (!isCameraRunning || isProcessing) return;
        isProcessing = true;

        // Capture frame
        const captureCanvas = document.getElementById('capture-canvas');
        captureCanvas.width = videoElement.videoWidth || 320;
        captureCanvas.height = videoElement.videoHeight || 240;
        const ctx = captureCanvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, captureCanvas.width, captureCanvas.height);
        const frameData = captureCanvas.toDataURL('image/jpeg', 0.7);

        try {
            const resp = await fetch('/api/process_frame', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame: frameData })
            });

            if (resp.ok) {
                const data = await resp.json();
                handleResult(data);
            }
        } catch (err) {
            console.error('Backend error:', err);
        } finally {
            isProcessing = false;
            if (isCameraRunning) requestAnimationFrame(processLoop);
        }
    }

    function handleResult(data) {
        // FPS counter
        fpsFrames++;
        const now = performance.now();
        if (now - lastFpsTime >= 1000) {
            fpsLabel.textContent = `FPS: ${fpsFrames}`;
            fpsFrames = 0;
            lastFpsTime = now;
        }

        if (!data.hand_detected) {
            updateHandStatus(false);
            updateGestureUI('neutral');
            isDrawing = false;
            currentPath = null;
            return;
        }

        updateHandStatus(true);

        const gesture = data.gesture || 'neutral';
        const ap = data.action_point;
        currentGesture = gesture;
        updateGestureUI(gesture);

        if (!ap) return;

        // Convert normalized action_point (0..1) to canvas pixels (mirrored)
        const cx = (1.0 - ap.x) * canvasElement.width;
        const cy = ap.y * canvasElement.height;
        const pos = { x: cx, y: cy };

        // ─── Act on gesture ─────────────────────────────────────────
        if (gesture === 'pen') {
            canvasPlaceholderUI.style.display = 'none';
            if (!isDrawing) {
                isDrawing = true;
                currentPath = { color: currentColor, size: penSize, points: [pos] };
                paths.push(currentPath);
            } else {
                currentPath.points.push(pos);
                // Incremental draw for responsiveness
                if (lastActionPoint) {
                    canvasCtx.beginPath();
                    canvasCtx.moveTo(lastActionPoint.x, lastActionPoint.y);
                    canvasCtx.lineTo(pos.x, pos.y);
                    canvasCtx.strokeStyle = currentColor;
                    canvasCtx.lineWidth = penSize;
                    canvasCtx.lineCap = 'round';
                    canvasCtx.lineJoin = 'round';
                    canvasCtx.stroke();
                }
            }
        } else if (gesture === 'eraser') {
            isDrawing = false;
            currentPath = null;
            eraseAt(cx, cy, eraserSize);
            // Draw eraser cursor
            redrawCanvas();
            canvasCtx.beginPath();
            canvasCtx.arc(cx, cy, eraserSize, 0, Math.PI * 2);
            canvasCtx.fillStyle = 'rgba(229, 72, 77, 0.3)';
            canvasCtx.fill();
            canvasCtx.strokeStyle = 'rgba(229, 72, 77, 0.6)';
            canvasCtx.lineWidth = 1;
            canvasCtx.stroke();
        } else if (gesture === 'select') {
            isDrawing = false;
            currentPath = null;
            // Draw select cursor
            redrawCanvas();
            canvasCtx.beginPath();
            canvasCtx.arc(cx, cy, 5, 0, Math.PI * 2);
            canvasCtx.fillStyle = 'rgba(171, 100, 0, 0.6)';
            canvasCtx.fill();
        } else if (gesture === 'drag') {
            isDrawing = false;
            currentPath = null;
            // Draw drag indicator
            redrawCanvas();
            canvasCtx.beginPath();
            canvasCtx.arc(cx, cy, 8, 0, Math.PI * 2);
            canvasCtx.fillStyle = 'rgba(171, 100, 0, 0.4)';
            canvasCtx.fill();
            canvasCtx.strokeStyle = 'rgba(171, 100, 0, 0.7)';
            canvasCtx.lineWidth = 2;
            canvasCtx.stroke();
        } else if (gesture === 'zoom_in' || gesture === 'zoom_out') {
            isDrawing = false;
            currentPath = null;
            const zoomColor = 'rgba(70, 167, 88, 0.5)';
            redrawCanvas();
            canvasCtx.beginPath();
            canvasCtx.arc(cx, cy, 12, 0, Math.PI * 2);
            canvasCtx.fillStyle = zoomColor;
            canvasCtx.fill();
            // Draw +/- icon
            canvasCtx.strokeStyle = '#fff';
            canvasCtx.lineWidth = 2;
            canvasCtx.beginPath();
            canvasCtx.moveTo(cx - 6, cy);
            canvasCtx.lineTo(cx + 6, cy);
            canvasCtx.stroke();
            if (gesture === 'zoom_in') {
                canvasCtx.beginPath();
                canvasCtx.moveTo(cx, cy - 6);
                canvasCtx.lineTo(cx, cy + 6);
                canvasCtx.stroke();
            }
        } else {
            // neutral
            isDrawing = false;
            currentPath = null;
            redrawCanvas();
            // Small cursor dot
            canvasCtx.beginPath();
            canvasCtx.arc(cx, cy, 3, 0, Math.PI * 2);
            canvasCtx.fillStyle = 'rgba(255, 255, 255, 0.4)';
            canvasCtx.fill();
        }

        lastActionPoint = pos;
    }

    // ========== CAMERA TOGGLE ==========
    cameraToggleBtn.addEventListener('click', async () => {
        if (isCameraRunning) {
            isCameraRunning = false;
            if (cameraStream) cameraStream.getTracks().forEach(t => t.stop());
            videoElement.style.display = 'none';
            cameraPlaceholder.style.display = 'flex';
            cameraToggleBtn.innerHTML = '<i class="fa-solid fa-video"></i> Start Camera';
            cameraToggleBtn.classList.remove('danger-button');
            cameraToggleBtn.classList.add('primary-button');
            updateHandStatus(false);
            updateGestureUI('neutral');
        } else {
            try {
                cameraStream = await navigator.mediaDevices.getUserMedia({
                    video: { width: { ideal: 640 }, height: { ideal: 480 } },
                    audio: false
                });
                videoElement.srcObject = cameraStream;
                await videoElement.play();
                isCameraRunning = true;
                cameraPlaceholder.style.display = 'none';
                videoElement.style.display = 'block';
                cameraToggleBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Camera';
                cameraToggleBtn.classList.remove('primary-button');
                cameraToggleBtn.classList.add('danger-button');
                processLoop();
            } catch (err) {
                console.error('Camera error:', err);
                alert('Unable to access camera. Please check permissions.');
            }
        }
    });

});
