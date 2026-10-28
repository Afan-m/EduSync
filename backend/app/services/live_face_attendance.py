"""
app/services/live_face_attendance.py

Live face recognition attendance logic for use by teachers.
"""

from __future__ import annotations

import math
import time
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.core.config import settings
from app.models.face import FACE_COLLECTION
from app.models.student import STUDENT_COLLECTION
from app.services.attendance_service import (
    get_active_session_by_id,
    get_marked_student_ids,
    mark_face_attendance,
)


def _load_insightface_analyzer() -> FaceAnalysis:
    if not hasattr(_load_insightface_analyzer, "analyzer"):
        analyzer = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        analyzer.prepare(ctx_id=0, det_size=(640, 640))
        _load_insightface_analyzer.analyzer = analyzer
    return _load_insightface_analyzer.analyzer


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


async def _load_registered_faces(db: AsyncIOMotorDatabase) -> dict[str, dict[str, Any]]:
    cursor = db[FACE_COLLECTION].find({"status": "active", "face_registered": True})
    documents = await cursor.to_list(length=10000)
    face_index: dict[str, dict[str, Any]] = {}

    for doc in documents:
        student_id = doc.get("student_id")
        if not student_id or not doc.get("face_embedding"):
            continue
        face_index[student_id] = {
            "embedding": np.array(doc["face_embedding"], dtype=np.float32),
            "document": doc,
        }

    return face_index


async def _load_student_names(db: AsyncIOMotorDatabase, student_ids: set[str]) -> dict[str, str]:
    names: dict[str, str] = {}
    if not student_ids:
        return names
    cursor = db[STUDENT_COLLECTION].find({"_id": {"$in": [ObjectId(sid) for sid in student_ids]}})
    async for student in cursor:
        if student and student.get("_id"):
            names[str(student["_id"])] = student.get("full_name", "Unknown")
    return names


def _draw_label(frame: np.ndarray, text: str, bbox: list[float]) -> None:
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 200, 0), 2)
    cv2.putText(frame, text, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)


async def run_live_attendance(
    session_id: str,
    db: AsyncIOMotorDatabase,
    max_frames: int | None = None,
    max_seconds: float | None = None,
) -> dict:
    session = await get_active_session_by_id(session_id, db)
    registered_faces = await _load_registered_faces(db)
    if not registered_faces:
        return {"success": False, "message": "No registered face embeddings available."}

    known_student_ids = set(registered_faces.keys())
    student_names = await _load_student_names(db, known_student_ids)
    marked_ids = await get_marked_student_ids(session_id, db)
    analyzer = _load_insightface_analyzer()
    threshold = float(settings.LIVE_ATTENDANCE_SIMILARITY_THRESHOLD)

    # Minimal logging only; excessive debug output removed per configuration.

    cap = cv2.VideoCapture(int(settings.LIVE_ATTENDANCE_CAMERA_INDEX))
    if not cap.isOpened():
        return {"success": False, "message": "Unable to open webcam."}


    frame_index = 0
    start_time = time.time()
    try:
        while True:
            if max_frames is not None and frame_index >= max_frames:
                print(f"[live_attendance] stopping after max_frames={max_frames}")
                break
            if max_seconds is not None and (time.time() - start_time) >= max_seconds:
                print(f"[live_attendance] stopping after max_seconds={max_seconds}")
                break

            ret, frame = cap.read()
            frame_index += 1
            if not ret:
                print(f"[live_attendance] frame {frame_index} read failed")
                break

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            faces = analyzer.get(rgb_frame)

            for face_index, face in enumerate(faces, start=1):
                embedding = np.array(face.embedding, dtype=np.float32)
                best_match_id = None
                best_score = -1.0

                for student_id, data in registered_faces.items():
                    if student_id in marked_ids:
                        continue
                    similarity = _cosine_similarity(embedding, data["embedding"])
                    if similarity > best_score:
                        best_score = similarity
                        best_match_id = student_id


                label = "Unknown"
                if best_match_id and best_score >= threshold:
                    name = student_names.get(best_match_id, "Student")
                    label = f"{name} ({best_score:.2f})"
                    await mark_face_attendance(
                        session_id=session_id,
                        student_id=best_match_id,
                        similarity_score=best_score,
                        db=db,
                    )
                    if attendance_result.get("marked"):
                        marked_ids.add(best_match_id)

                _draw_label(frame, label, face.bbox.tolist())

            cv2.imshow("EduSync Live Attendance", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break

            time.sleep(0.01)

    finally:
        cap.release()
        cv2.destroyAllWindows()

    return {"success": True, "message": "Live attendance session ended."}
