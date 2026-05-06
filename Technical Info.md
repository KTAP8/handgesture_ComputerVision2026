# Technical Report — Hand Gesture Recognition System
### Computer Vision 2026

---

## 1. System Overview

This system performs real-time hand gesture recognition from a webcam feed and translates recognised gestures into OS-level keyboard events. The computer vision work is entirely contained in `server/hand_recognizer.py`. The pipeline combines classical image processing techniques (HSV segmentation, morphological filtering, Canny edge detection, Sobel gradients) with a deep learning model (MediaPipe GestureRecognizer) running in parallel. The classical techniques are used for visualisation and analysis; the neural model handles the actual classification.

```
Webcam frame
    │
    ├──► [Raw BGR frame] ──────────────────────────► MediaPipe GestureRecognizer
    │                                                       │
    │                                                  21 landmarks
    │                                                + gesture category
    │
    └──► [Grayscale + CLAHE] ──► HSV skin mask ──► Contour / Hull / Canny / Sobel
                                                         (visualisation only)
```

---

## 2. Frame Acquisition

Frames are captured via OpenCV's `VideoCapture` in a dedicated daemon thread. Each frame is horizontally flipped (`cv2.flip(frame, 1)`) before processing. This mirror transformation makes the display feel natural — the user's right hand appears on the right side of the screen, matching everyday mirror behaviour. Without this, left/right gestures would appear reversed from the user's perspective.

The capture loop runs as fast as the camera hardware allows. The output MJPEG stream is separately rate-limited to approximately 30 fps to avoid flooding the HTTP connection.

---

## 3. Image Preprocessing

### 3.1 CLAHE (Contrast Limited Adaptive Histogram Equalisation)

CLAHE is applied to the grayscale version of each frame:

```python
gray     = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
enhanced = self._clahe.apply(gray)   # clipLimit=2.0, tileGridSize=(8,8)
```

Standard histogram equalisation spreads intensity values globally across the whole image. CLAHE divides the image into small tiles (8×8 here) and equalises each tile independently, then bilinearly interpolates across tile borders to avoid hard edges. The `clipLimit=2.0` cap prevents over-amplification of noise — without it, CLAHE would boost noise in uniform regions (e.g. a blank wall) as aggressively as it boosts genuine structure.

**Important design note:** CLAHE is used exclusively for the visualisation overlays (skin mask, Canny, Sobel). The raw colour frame is fed to MediaPipe, not the CLAHE-processed one. MediaPipe's gesture model was trained on natural colour images; converting to grayscale then back to BGR strips the colour information the model relies on and measurably degrades detection accuracy.

### 3.2 Colour Space Conversion

The pipeline works across three colour spaces for different purposes:

| Space | Usage | Why |
|-------|-------|-----|
| BGR | Raw capture, output annotation | OpenCV's native format |
| RGB | MediaPipe input | MediaPipe expects RGB |
| Grayscale | CLAHE, Canny, Sobel | Single-channel operations |
| HSV | Skin segmentation | Hue isolates colour from brightness |

---

## 4. Skin Segmentation

### 4.1 HSV Thresholding

Human skin colour occupies a narrow, consistent band in HSV space. The hue channel encodes the actual colour independent of how bright or dark the lighting is, making it far more robust for skin detection than working in BGR where the same skin colour produces very different values under different lighting conditions.

```python
_SKIN_LOWER = np.array([0,  20,  70])   # H, S, V lower bound
_SKIN_UPPER = np.array([20, 255, 255])  # H, S, V upper bound
```

- **Hue 0–20** spans red through orange-yellow in HSV, which covers most skin tones. The range can be widened to hue ≈ 25 for darker skin tones or warm-lit environments.
- **Saturation ≥ 20** excludes near-grey pixels (white walls, grey clothing) that would otherwise fall into the hue range.
- **Value ≥ 70** excludes very dark pixels where skin detection is unreliable.

The result is a binary mask where white pixels (255) indicate likely skin and black pixels (0) indicate everything else.

### 4.2 Morphological Filtering

Raw HSV thresholding produces noisy results — small isolated blobs from similarly-coloured objects, and holes inside the hand region from specular highlights on knuckles (which desaturate the skin tone and fall below the saturation floor).

```python
# Remove noise blobs smaller than the structuring element
skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, self._morph_kernel)

# Fill holes left by specular highlights on knuckles
skin_mask = cv2.dilate(skin_mask, self._morph_kernel, iterations=1)
```

**MORPH_OPEN** is an erosion followed by a dilation using the same structuring element. It destroys any connected region smaller than the kernel — effective at removing stray blobs from background objects that accidentally pass the HSV test. The structuring element is an ellipse of size 7×7, chosen because a circular/elliptical kernel matches the roughly round shape of skin blobs better than a square one.

**Dilation** expands the surviving regions outward. A single dilation pass re-fills the small holes left by the opening and joins regions that were separated by a thin line of desaturated pixels (e.g. a crease or shadow line across the palm).

---

## 5. Contour and Convex Hull Analysis

### 5.1 Contour Detection

```python
contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
```

`RETR_EXTERNAL` retrieves only the outermost contours — the boundaries of the white regions in the mask — and ignores any contours nested inside them (holes). `CHAIN_APPROX_SIMPLE` compresses horizontal, vertical, and diagonal line segments, storing only their endpoints rather than every pixel, which reduces memory use and speeds up downstream operations.

The largest contour by area is taken as the hand region. A minimum area threshold of 2000 pixels² is applied to discard small false positives (a patch of similarly-coloured skin on a face or arm in the background, for example).

### 5.2 Convex Hull

```python
hull = cv2.convexHull(largest)
cv2.drawContours(frame, [hull], -1, (255, 0, 200), 2)  # magenta
```

The convex hull is the smallest convex polygon that encloses the contour — equivalently, the shape you would get by stretching a rubber band around the outermost points of the hand region. The gaps between the hull and the actual contour (where the fingers separate) are called **convexity defects**. These defects are a classical feature for finger counting: each valley between two raised fingers produces one defect. While this system does not currently use convexity defects for classification (MediaPipe handles that), they are visualised on screen and could be used for a custom rule-based classifier in future work.

---

## 6. Edge Detection

### 6.1 Canny Edge Detection

```python
skin_gray = cv2.bitwise_and(enhanced, enhanced, mask=skin_mask)
edges     = cv2.Canny(skin_gray, 40, 120)
```

Canny is applied to the CLAHE-enhanced grayscale image masked to the skin region. Masking before edge detection is important: without it, Canny would find every edge in the frame — furniture edges, clothing texture, background detail — making the output noisy and hard to interpret. Restricting the input to the skin mask means only edges within the hand region are detected.

Canny runs in four stages internally:

1. **Gaussian blur** — smooths the image to reduce false edges from sensor noise
2. **Sobel gradient** — computes image gradient magnitude and direction at every pixel
3. **Non-maximum suppression** — thins edges to single-pixel width by suppressing pixels that are not local maxima along the gradient direction
4. **Double thresholding + hysteresis** — pixels above the upper threshold (120) are definite edges; pixels below the lower threshold (40) are discarded; pixels in between are kept only if they connect to a definite edge

The thresholds 40/120 were chosen empirically. Reducing the lower threshold connects more edge fragments at the cost of including more noise.

### 6.2 Sobel Gradient Magnitude (Inset Visualisation)

```python
sx        = cv2.Sobel(enhanced, cv2.CV_64F, 1, 0, ksize=3)   # dI/dx
sy        = cv2.Sobel(enhanced, cv2.CV_64F, 0, 1, ksize=3)   # dI/dy
sobel_mag = cv2.convertScaleAbs(cv2.magnitude(sx, sy))
```

The Sobel operator approximates the image gradient by convolving the image with two 3×3 kernels — one sensitive to horizontal edges (∂I/∂x) and one to vertical edges (∂I/∂y). The gradient magnitude at each pixel is:

$$M = \sqrt{(\partial I / \partial x)^2 + (\partial I / \partial y)^2}$$

This produces a float64 array of edge strengths regardless of edge direction, which is then scaled back to uint8 with `convertScaleAbs`. Unlike Canny, Sobel does not threshold or thin edges — it is a raw gradient image. It is shown as a small inset in the top-right corner of the live feed as a diagnostic view of the overall edge structure in the frame.

---

## 7. Hand Landmark Detection and Gesture Classification

### 7.1 MediaPipe GestureRecognizer

Classification is handled by MediaPipe's `GestureRecognizer` model from the Tasks API. The model is a multi-stage pipeline:

1. **Palm detector** — a lightweight single-shot detector (BlazePalm) that locates the bounding box of each hand in the frame. It operates at low resolution for speed.
2. **Hand landmark model** — a regression network that takes the cropped hand region and outputs 21 3D landmarks (x, y, z) normalised to the hand bounding box. The 21 points cover each finger joint (4 joints per finger + the tip) plus the wrist.
3. **Gesture classifier** — a fully connected network operating on the landmark coordinates that outputs one of the supported gesture categories.

The model is run in `RunningMode.VIDEO` mode:

```python
options = mp_vision.GestureRecognizerOptions(
    base_options=mp_python.BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=mp_vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
```

`RunningMode.VIDEO` is critical for stability. In `IMAGE` mode (the default), each frame is treated as an independent detection — the palm detector runs from scratch every frame, and any frame where detection confidence dips slightly below threshold causes the gesture to disappear. In `VIDEO` mode, MediaPipe uses temporal filtering: once the hand is detected, a Kalman-filter-based tracker continues to predict hand position between frames and initialises the landmark model from the tracked region rather than re-running the palm detector. This dramatically reduces flickering.

### 7.2 Supported Gesture Classes

The model recognises 7 non-null gesture classes:

| MediaPipe Category | Mapped Label | Active |
|--------------------|--------------|--------|
| `Thumb_Up`         | `thumbs_up`  | Yes |
| `Thumb_Down`       | `thumbs_down`| Yes |
| `Open_Palm`        | `open_hand`  | Yes |
| `Pointing_Up`      | `point_up`   | Yes |
| `ILoveYou`         | `ok`         | Yes |
| `Victory`          | `peace`      | No (disabled) |
| `Closed_Fist`      | `fist`       | No (disabled) |
| `None`             | —            | — |

Note: the model does **not** have an `Ok` (ring + thumb) gesture class despite historical confusion in the codebase. `ILoveYou` (thumb, index, and pinky extended) is what the model classifies as its closest analogue.

### 7.3 Landmark Visualisation

The 21 landmarks are drawn on the frame as a skeleton:

```python
# 21 connections covering thumb, index, middle, ring, pinky
for a, b in _HAND_CONNECTIONS:
    cv2.line(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)   # green lines
for point in lm:
    cv2.circle(frame, (cx, cy), 4, (0, 255, 0), -1)         # green dots
```

Landmark coordinates are returned as normalised fractions (0.0–1.0) of the image dimensions, so they scale automatically to any camera resolution.

---

## 8. Gesture-to-Action Dispatch

### 8.1 Leading-Edge Detection (Operator)

Raw gesture polling produces repeated identical values — if the user holds a thumbs-up for two seconds, `current_gesture()` returns `"thumbs_up"` on every poll. Sending a keystroke on every poll would fire the action dozens of times. The `Operator` class solves this with a baseline comparison:

```python
if current != self._baseline:
    if current is not None:
        key = self._bindings.get(current)
        if key:
            pyautogui.press(key)
    self._baseline = current
```

A key fires only on the **transition** from one gesture to another. The baseline advances on every change including to `None`, which means the same gesture can re-fire after the hand disappears and comes back — the `None` state acts as a reset. This is a leading-edge trigger analogous to a rising-edge interrupt in digital electronics.

The tracker polls at 50 ms intervals (20 Hz), which gives a practical response latency of 0–50 ms from gesture change to keypress.

### 8.2 OS-Level Key Injection

`pyautogui.press()` synthesises platform-native input events — on macOS it uses CoreGraphics `CGEventPost`, on Windows it uses the `SendInput` Win32 API. This makes the keystroke indistinguishable from physical keyboard input from the perspective of the receiving application.

---

## 9. Threading Architecture

The system uses three threads:

| Thread | Role |
|--------|------|
| Main (Flask) | Serves HTTP requests, handles `/stream`, `/gesture`, `/dispatch` |
| `HandRecognizer._loop` | Runs the full CV pipeline per frame, writes `_gesture` and `_frame` |
| `Operator._tracker` | Polls `current_gesture()`, fires keypresses on transitions |

`_gesture` and `_frame` are shared between the Flask thread and the recogniser thread. Both are protected by a single `threading.Lock`. Reads and writes to these values are always wrapped in `with self._lock`, preventing torn reads (reading a partially-written value).

---

## 10. Design Decisions

**Why use MediaPipe for classification instead of a custom model?**
MediaPipe's landmark-based gesture classifier works across diverse lighting conditions, skin tones, and hand sizes because it operates on normalised 3D landmark geometry, not raw pixel values. A pixel-based custom classifier would require a much larger training dataset to achieve comparable robustness.

**Why keep classical CV techniques (HSV, Canny, Sobel) if MediaPipe handles classification?**
Two reasons. First, they provide diagnostic overlays that make the system's perception visible — you can see exactly which region the system considers "hand" and whether the edge structure is clean. This is valuable during development and for a CV course demonstration. Second, they represent independent signal sources: the convexity defects from the contour analysis or the Canny edge map could feed an alternative or supplementary classifier in future work without requiring any new infrastructure.

**Why feed raw frames to MediaPipe and not the CLAHE-processed frames?**
The GestureRecognizer was trained on natural colour images. CLAHE first converts to grayscale (losing colour information entirely) then converts back to a fake BGR image where all three channels are identical. The model's convolutional layers are sensitive to colour information — the palm detector in particular uses colour to distinguish hands from background — so this conversion degrades detection. CLAHE is kept only for the visualisation pipeline where it genuinely helps (it improves Canny edge quality and skin mask quality in dim or uneven lighting).

**Why VIDEO mode over LIVE_STREAM mode?**
`LIVE_STREAM` mode is asynchronous — results are returned via a callback, which requires the caller to manage synchronisation between the callback thread and the display thread. `VIDEO` mode is synchronous: `recognize_for_video()` returns a result immediately and can be called from any thread, making integration with the existing threading model straightforward.

---

## 11. Limitations and Future Work

**HSV skin range is fixed.** The thresholds H:[0–20], S:[20–255], V:[70–255] work well for medium skin tones in neutral lighting but may miss darker skin tones (which fall outside the hue range) or produce false positives in warm-coloured environments (wooden desks, orange walls). A per-session calibration step that samples the user's skin colour and sets the range dynamically would improve robustness.

**Single-hand only.** `num_hands=1` is set in the recogniser options. Multi-hand gestures (e.g. clapping, two-handed shapes) are not possible without changing this and updating the downstream mapping logic.

**No temporal smoothing on the gesture output.** A gesture that flickers between `thumbs_up` and `None` for one frame will fire the key once for each positive frame. A short debounce window — requiring the gesture to be stable for N consecutive frames before accepting it — would improve reliability at the cost of added latency.

**Convexity defects are computed but unused.** The convex hull is drawn but the `cv2.convexityDefects()` function is never called. Defect count is a simple and effective proxy for finger count, which could supplement the MediaPipe classifier or provide a fallback when the model is unavailable.

**No custom gesture support.** The system is limited to MediaPipe's 7 built-in gesture classes. Extending it to custom gestures would require either fine-tuning the MediaPipe model on custom data, or building a separate classifier that operates on the 21 landmark coordinates (a small MLP or SVM over the normalised landmark geometry would be sufficient for new static gestures).
