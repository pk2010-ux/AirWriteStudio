// AirWrite Studio Web Demo Version - app.js
// Handles UI interactions, MediaPipe Hands integration, and Canvas Drawing

document.addEventListener('DOMContentLoaded', () => {
    // ========== MODAL LOGIC ==========
    const modal = document.getElementById('startup-modal');
    const closeModalBtn = document.getElementById('close-modal-btn');
    closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // ========== UI ELEMENTS ==========
    const videoElement = document.getElementById('camera-feed');
    const cameraPlaceholder = document.getElementById('camera-placeholder');
    const cameraToggleBtn = document.getElementById('camera-toggle-btn');
    
    // Status UI
    const gestureDot = document.querySelector('.gesture-dot');
    const gestureIcon = document.querySelector('.gesture-icon');
    const gestureLabel = document.querySelector('.gesture-label');
    const gestureDesc = document.querySelector('.gesture-description');
    const handStatus = document.querySelector('.hand-status');
    const fpsLabel = document.querySelector('.fps-label');

    // Tools
    const colorSwatches = document.querySelectorAll('.color-swatch');
    const penSizeSlider = document.getElementById('pen-size');
    const eraserSizeSlider = document.getElementById('eraser-size');
    const clearCanvasBtn = document.querySelector('.danger-button'); // Clear Canvas

    // Canvas
    const canvasElement = document.getElementById('drawing-canvas');
    const canvasCtx = canvasElement.getContext('2d');
    const canvasPlaceholderUI = document.getElementById('canvas-placeholder');

    // Resize canvas to fill area
    function resizeCanvas() {
        const rect = canvasElement.parentElement.getBoundingClientRect();
        canvasElement.width = rect.width;
        canvasElement.height = rect.height;
    }
    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // ========== APP STATE ==========
    let isCameraRunning = false;
    let currentColor = '#FFFFFF';
    let penSize = 3.0;
    let eraserSize = 20.0;
    
    // Drawing state
    let isDrawing = false;
    let isErasing = false;
    let paths = []; // Array of drawn paths { color, size, points: [{x,y}] }
    let currentPath = null;
    let lastHandPosition = null;

    // Gestures
    const PINCH_THRESHOLD = 0.08; 
    const ERASE_THRESHOLD = 0.12;

    // ========== UI HANDLERS ==========
    
    colorSwatches.forEach(swatch => {
        swatch.addEventListener('click', (e) => {
            colorSwatches.forEach(s => s.classList.remove('selected'));
            swatch.classList.add('selected');
            currentColor = swatch.style.backgroundColor || swatch.getAttribute('title');
            // convert to hex or rgb string as is
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
        redrawCanvas();
    });

    function updateGestureStatus(mode, icon, color, description) {
        gestureDot.style.backgroundColor = color;
        gestureIcon.innerHTML = icon;
        gestureLabel.textContent = mode;
        gestureLabel.style.color = color;
        gestureDesc.textContent = description;
    }

    function updateHandStatus(recognized) {
        if (recognized) {
            handStatus.innerHTML = '<i class="fa-solid fa-face-smile"></i> Face recognised'; // Re-using for hand status for consistency with UI mockup
            handStatus.style.color = '#4ECDC4';
        } else {
            handStatus.innerHTML = '<i class="fa-solid fa-face-meh"></i> Face not recognised';
            handStatus.style.color = '#9898b0';
        }
    }

    // ========== DRAWING LOGIC ==========

    function drawLine(ctx, p1, p2, color, size) {
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.strokeStyle = color;
        ctx.lineWidth = size;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        ctx.stroke();
    }

    function redrawCanvas() {
        canvasCtx.clearRect(0, 0, canvasElement.width, canvasElement.height);
        
        // Hide placeholder if we have paths
        if (paths.length > 0) {
            canvasPlaceholderUI.style.display = 'none';
        } else {
            canvasPlaceholderUI.style.display = 'block';
        }

        paths.forEach(path => {
            if (path.points.length < 2) return;
            canvasCtx.beginPath();
            canvasCtx.moveTo(path.points[0].x, path.points[0].y);
            for (let i = 1; i < path.points.length; i++) {
                canvasCtx.lineTo(path.points[i].x, path.points[i].y);
            }
            canvasCtx.strokeStyle = path.color;
            canvasCtx.lineWidth = path.size;
            canvasCtx.lineCap = 'round';
            canvasCtx.lineJoin = 'round';
            canvasCtx.stroke();
        });
    }

    function eraseAt(x, y, radius) {
        // Simple spatial clearing: remove paths that have points near the eraser
        let pathsChanged = false;
        paths = paths.filter(path => {
            let keepPath = true;
            // Check if any point in path is within erase radius
            for (let pt of path.points) {
                let dx = pt.x - x;
                let dy = pt.y - y;
                if (Math.sqrt(dx*dx + dy*dy) < radius) {
                    keepPath = false;
                    pathsChanged = true;
                    break;
                }
            }
            return keepPath;
        });
        if (pathsChanged) {
            redrawCanvas();
        }
    }

    // ========== MEDIAPIPE HANDS ==========

    const hands = new Hands({locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
    }});

    hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.7,
        minTrackingConfidence: 0.5
    });

    let fpsFrames = 0;
    let lastFpsTime = performance.now();

    hands.onResults((results) => {
        fpsFrames++;
        let now = performance.now();
        if (now - lastFpsTime >= 1000) {
            fpsLabel.textContent = `FPS: ${fpsFrames}`;
            fpsFrames = 0;
            lastFpsTime = now;
        }

        if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
            updateHandStatus(true);
            const landmarks = results.multiHandLandmarks[0];
            
            // Map coordinates to canvas (Mirrored horizontally)
            // landmarks are 0..1
            // Use index finger tip (8) for drawing location
            let indexTip = landmarks[8];
            let thumbTip = landmarks[4];
            let middleTip = landmarks[12];
            let ringTip = landmarks[16];
            let pinkyTip = landmarks[20];

            let cx = (1.0 - indexTip.x) * canvasElement.width;
            let cy = indexTip.y * canvasElement.height;
            let currentPos = { x: cx, y: cy };

            // Gesture Math
            // Distance between thumb and index
            let pinchDist = Math.sqrt(Math.pow(thumbTip.x - indexTip.x, 2) + Math.pow(thumbTip.y - indexTip.y, 2));
            
            // Distance between middle/ring/pinky tips to wrist (to detect fist/eraser)
            let wrist = landmarks[0];
            let middleFold = Math.sqrt(Math.pow(middleTip.x - wrist.x, 2) + Math.pow(middleTip.y - wrist.y, 2));
            let ringFold = Math.sqrt(Math.pow(ringTip.x - wrist.x, 2) + Math.pow(ringTip.y - wrist.y, 2));
            let pinkyFold = Math.sqrt(Math.pow(pinkyTip.x - wrist.x, 2) + Math.pow(pinkyTip.y - wrist.y, 2));

            let isFist = (middleFold < ERASE_THRESHOLD && ringFold < ERASE_THRESHOLD && pinkyFold < ERASE_THRESHOLD);
            let isPinch = pinchDist < PINCH_THRESHOLD;

            if (isFist) {
                // ERASER MODE
                updateGestureStatus('Erasing', '<i class="fa-solid fa-eraser"></i>', '#E5484D', 'Closed fist — erase');
                
                // Use hand center for eraser
                let ex = (1.0 - landmarks[9].x) * canvasElement.width;
                let ey = landmarks[9].y * canvasElement.height;
                
                // Draw eraser cursor preview (temporarily directly on canvas context without saving to paths)
                redrawCanvas();
                canvasCtx.beginPath();
                canvasCtx.arc(ex, ey, eraserSize, 0, Math.PI * 2);
                canvasCtx.fillStyle = 'rgba(229, 72, 77, 0.4)';
                canvasCtx.fill();

                eraseAt(ex, ey, eraserSize);

                isDrawing = false;
                currentPath = null;
            } else if (isPinch) {
                // PEN MODE
                updateGestureStatus('Drawing', '<i class="fa-solid fa-pencil"></i>', '#4ECDC4', 'Thumb + Index pinch — draw');
                
                if (!isDrawing) {
                    isDrawing = true;
                    currentPath = { color: currentColor, size: penSize, points: [currentPos] };
                    paths.push(currentPath);
                } else {
                    currentPath.points.push(currentPos);
                    drawLine(canvasCtx, lastHandPosition, currentPos, currentColor, penSize);
                }
            } else {
                // NEUTRAL MODE
                updateGestureStatus('Neutral', '<i class="fa-solid fa-hand-paper"></i>', '#6C757D', 'Open palm — no action');
                isDrawing = false;
                currentPath = null;
                redrawCanvas(); // Clear any eraser cursor
                
                // Draw small cursor preview
                canvasCtx.beginPath();
                canvasCtx.arc(cx, cy, 3, 0, Math.PI * 2);
                canvasCtx.fillStyle = 'rgba(255, 255, 255, 0.5)';
                canvasCtx.fill();
            }

            lastHandPosition = currentPos;

        } else {
            updateHandStatus(false);
            isDrawing = false;
            currentPath = null;
        }
    });

    let camera = new Camera(videoElement, {
        onFrame: async () => {
            if (isCameraRunning) {
                await hands.send({image: videoElement});
            }
        },
        width: 1280,
        height: 720
    });

    // ========== CAMERA TOGGLE ==========

    cameraToggleBtn.addEventListener('click', async () => {
        if (isCameraRunning) {
            // STOP
            isCameraRunning = false;
            camera.stop();
            videoElement.style.display = 'none';
            cameraPlaceholder.style.display = 'flex';
            
            cameraToggleBtn.innerHTML = '<i class="fa-solid fa-video"></i> Start Camera';
            cameraToggleBtn.classList.remove('danger-button');
            cameraToggleBtn.classList.add('primary-button');
        } else {
            // START
            isCameraRunning = true;
            cameraPlaceholder.style.display = 'none';
            videoElement.style.display = 'block';
            
            cameraToggleBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Starting...';
            
            await camera.start();
            
            cameraToggleBtn.innerHTML = '<i class="fa-solid fa-stop"></i> Stop Camera';
            cameraToggleBtn.classList.remove('primary-button');
            cameraToggleBtn.classList.add('danger-button');
        }
    });

});
