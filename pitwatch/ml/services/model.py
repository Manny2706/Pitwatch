import threading
from numbers import Integral
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from django.conf import settings


class PredictionError(Exception):
    pass


class InvalidImageError(PredictionError):
    pass


_MODEL_LOCK = threading.Lock()
_MODEL_STATE = {
    "session": None,
    "input_name": None,
    "output_name": None,
    "input_shape": None,
}


def _model_path() -> Path:
    models_dir = Path(settings.BASE_DIR) / "models"
    preferred = models_dir / "pothole_model.onnx"
    fallback = models_dir / "best.onnx"
    if preferred.exists():
        return preferred
    return fallback


def _load_session_once() -> None:
    if _MODEL_STATE["session"] is not None:
        return

    with _MODEL_LOCK:
        if _MODEL_STATE["session"] is not None:
            return

        model_path = _model_path()
        if not model_path.exists():
            raise PredictionError(f"Model file not found: {model_path}")

        try:
            session = ort.InferenceSession(str(model_path))
            _MODEL_STATE["session"] = session
            _MODEL_STATE["input_name"] = session.get_inputs()[0].name
            _MODEL_STATE["output_name"] = session.get_outputs()[0].name
            _MODEL_STATE["input_shape"] = session.get_inputs()[0].shape
        except Exception as exc:
            raise PredictionError(f"Failed to load ONNX model: {exc}") from exc


def _target_size() -> tuple[int, int]:
    shape = _MODEL_STATE.get("input_shape")
    if not shape or len(shape) < 4:
        return (224, 224)

    def as_size(value):
        if isinstance(value, Integral):
            value = int(value)
            return value if value > 0 else None
        return None

    # Expected ONNX image layouts are typically NCHW or NHWC.
    h = as_size(shape[2])
    w = as_size(shape[3])
    if h is not None and w is not None:
        return (w, h)

    h = as_size(shape[1])
    w = as_size(shape[2])
    if h is not None and w is not None:
        return (w, h)

    return (224, 224)


def preprocess_image(image: np.ndarray) -> np.ndarray:
    target_w, target_h = _target_size()
    image = cv2.resize(image, (target_w, target_h))
    image = image / 255.0
    image = np.transpose(image, (2, 0, 1))
    image = np.expand_dims(image, axis=0).astype(np.float32)
    return image


def _extract_probability(output_tensor) -> float:
    arr = np.asarray(output_tensor)
    if arr.size == 0:
        raise PredictionError("Model output is empty")

    arr = np.squeeze(arr)

    # Scalar classification output.
    if arr.ndim == 0:
        value = float(arr)
        return float(np.clip(value, 0.0, 1.0))

    # YOLO-style output [channels, num_boxes] where channel index 4 is objectness.
    if arr.ndim == 2 and arr.shape[0] >= 5:
        conf = arr[4]
        return float(np.clip(np.max(conf), 0.0, 1.0))

    # Transposed YOLO-style output [num_boxes, channels].
    if arr.ndim == 2 and arr.shape[1] >= 5:
        conf = arr[:, 4]
        return float(np.clip(np.max(conf), 0.0, 1.0))

    # Generic fallback for unknown output shapes.
    flat = arr.astype(np.float32).ravel()
    value = float(np.max(flat))
    return float(np.clip(value, 0.0, 1.0))


def predict(image: np.ndarray) -> float:
    _load_session_once()

    try:
        input_tensor = preprocess_image(image)
        outputs = _MODEL_STATE["session"].run(
            [_MODEL_STATE["output_name"]],
            {_MODEL_STATE["input_name"]: input_tensor},
        )
        return _extract_probability(outputs[0])
    except PredictionError:
        raise
    except Exception as exc:
        raise PredictionError(f"Inference failed: {exc}") from exc


def predict_from_file(uploaded_file) -> float:
    try:
        file_bytes = np.asarray(bytearray(uploaded_file.read()), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except Exception as exc:
        raise InvalidImageError(f"Invalid image file: {exc}") from exc

    if image is None:
        raise InvalidImageError("Unable to decode uploaded image")

    return predict(image)


def predict_from_bytes(raw_bytes: bytes) -> float:
    try:
        file_bytes = np.asarray(bytearray(raw_bytes), dtype=np.uint8)
        image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    except Exception as exc:
        raise InvalidImageError(f"Invalid image bytes: {exc}") from exc

    if image is None:
        raise InvalidImageError("Unable to decode uploaded image")

    return predict(image)
