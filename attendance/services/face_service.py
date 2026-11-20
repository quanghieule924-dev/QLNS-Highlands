
from pathlib import Path

import cv2
import numpy as np

from cryptography.fernet import Fernet
from django.conf import settings


MODEL_DIR = Path(__file__).resolve().parent.parent / "face_models"

DETECTOR_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
RECOGNIZER_PATH = MODEL_DIR / "face_recognition_sface_2021dec.onnx"

MODEL_VERSION = "opencv-sface-2021dec"


class FaceProcessingError(Exception):
    pass


def get_cipher():
    key = getattr(settings, "FACE_ENCRYPTION_KEY", None)

    if not key:
        raise FaceProcessingError(
            "Chưa cấu hình FACE_ENCRYPTION_KEY trong file .env."
        )

    try:
        return Fernet(key.encode() if isinstance(key, str) else key)
    except (ValueError, TypeError):
        raise FaceProcessingError(
            "Khóa mã hóa Face ID không hợp lệ."
        )


def create_face_embedding(image_bytes):
    """
    Nhận ảnh JPEG/PNG.
    Kiểm tra đúng một khuôn mặt.
    Trả về embedding kiểu numpy float32.
    """

    if not image_bytes:
        raise FaceProcessingError("Chưa nhận được ảnh khuôn mặt.")

    if len(image_bytes) > 2 * 1024 * 1024:
        raise FaceProcessingError(
            "Ảnh quá lớn. Dung lượng tối đa là 2 MB."
        )

    if not DETECTOR_PATH.is_file() or not RECOGNIZER_PATH.is_file():
        raise FaceProcessingError(
            "Chưa có đủ hai file mô hình ONNX trong face_models."
        )

    # Giải mã ảnh
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise FaceProcessingError(
            "Ảnh không hợp lệ. Vui lòng chụp lại."
        )

    height, width = image.shape[:2]

    if width < 320 or height < 320:
        raise FaceProcessingError(
            "Độ phân giải ảnh quá thấp."
        )

    if width * height > 8_000_000:
        raise FaceProcessingError(
            "Độ phân giải ảnh vượt giới hạn cho phép."
        )

    # Phát hiện khuôn mặt bằng YuNet
    detector = cv2.FaceDetectorYN.create(
        str(DETECTOR_PATH),
        "",
        (width, height),
        0.9,
        0.3,
        5000
    )

    _, faces = detector.detect(image)

    if faces is None or len(faces) == 0:
        raise FaceProcessingError(
            "Không tìm thấy khuôn mặt. Vui lòng chụp lại."
        )

    if len(faces) != 1:
        raise FaceProcessingError(
            "Ảnh phải có đúng một khuôn mặt."
        )

    face = faces[0]

    x, y, w, h = face[:4]

    if w < 100 or h < 100:
        raise FaceProcessingError(
            "Khuôn mặt quá nhỏ. Hãy đứng gần camera hơn."
        )

    # Cắt vùng mặt để kiểm tra độ rõ
    x1 = max(0, int(x))
    y1 = max(0, int(y))
    x2 = min(width, int(x + w))
    y2 = min(height, int(y + h))

    face_crop = image[y1:y2, x1:x2]

    if face_crop.size == 0:
        raise FaceProcessingError("Không thể xử lý vùng khuôn mặt.")

    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)

    sharpness = cv2.Laplacian(
        gray, cv2.CV_64F
    ).var()

    if sharpness < 40:
        raise FaceProcessingError(
            "Ảnh hơi mờ. Vui lòng giữ yên và chụp lại."
        )

    # Trích xuất đặc trưng bằng SFace
    recognizer = cv2.FaceRecognizerSF.create(
        str(RECOGNIZER_PATH),
        ""
    )

    aligned_face = recognizer.alignCrop(image, face)
    embedding = recognizer.feature(aligned_face)

    if embedding is None or embedding.size == 0:
        raise FaceProcessingError(
            "Không thể tạo dữ liệu nhận diện."
        )

    return embedding.astype(np.float32)


def encrypt_embedding(embedding):
    """
    Mã hóa embedding trước khi ghi vào BinaryField.
    """
    return get_cipher().encrypt(
        embedding.astype(np.float32).tobytes()
    )


# ============================================================
# GIẢI MÃ EMBEDDING VÀ SO KHỚP KHUÔN MẶT
# ============================================================

from cryptography.fernet import InvalidToken


# Ngưỡng thử nghiệm SFace, cần hiệu chỉnh trước khi sử dụng thật
FACE_MATCH_THRESHOLD = 0.40


def decrypt_embedding(encrypted_data):

    try:
        raw_data = get_cipher().decrypt(
            bytes(encrypted_data)
        )
    except InvalidToken:
        raise FaceProcessingError(
            "Không thể giải mã Face ID. Kiểm tra khóa mã hóa."
        )

    # SFace 2021dec tạo vector 128 số float32
    if len(raw_data) != 128 * 4:
        raise FaceProcessingError(
            "Kích thước mẫu Face ID không hợp lệ."
        )

    embedding = np.frombuffer(
        raw_data, dtype=np.float32
    ).copy().reshape(1, 128)

    if not np.isfinite(embedding).all():
        raise FaceProcessingError(
            "Dữ liệu đặc trưng khuôn mặt không hợp lệ."
        )

    return embedding


def verify_face(image_bytes, encrypted_data):

    # 1. Tạo embedding khuôn mặt hiện tại
    current_embedding = create_face_embedding(
        image_bytes
    )

    # 2. Giải mã embedding đã đăng ký
    saved_embedding = decrypt_embedding(
        encrypted_data
    )

    # 3. So khớp bằng OpenCV SFace
    recognizer = cv2.FaceRecognizerSF.create(
        str(RECOGNIZER_PATH),
        ""
    )

    similarity = recognizer.match(
        saved_embedding,
        current_embedding,
        cv2.FaceRecognizerSF_FR_COSINE
    )

    if not np.isfinite(similarity):
        raise FaceProcessingError(
            "Không tính được độ tương đồng khuôn mặt."
        )

    return {
        "matched": bool(similarity >= FACE_MATCH_THRESHOLD),
        "similarity": float(similarity),
    }
