"""
app/services/face_service.py

Business logic for student face registration.
"""

from datetime import datetime
import os

import cv2
import numpy as np
from fastapi import HTTPException
from insightface.app import FaceAnalysis
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.student import STUDENT_COLLECTION
from app.models.face import FACE_COLLECTION, FaceRegistrationDocument, face_registration_to_dict

async def get_face_status(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    """
    Returns the current face registration status for a student.
    """
    doc = await db[FACE_COLLECTION].find_one({"student_id": student_id})
    if not doc:
        return {
            "status": "Not Registered",
            "images_captured": 0,
            "version": None,
            "registration_date": None,
            "is_registered": False
        }
        
    return {
        "status": "Registered" if doc.get("status") == "active" else "Reset Requested",
        "images_captured": len(doc.get("image_paths", [])),
        "version": doc.get("face_version", 1),
        "registration_date": doc.get("registration_date"),
        "is_registered": True
    }


def _load_insightface_analyzer() -> FaceAnalysis:
    """Lazy-load and cache the InsightFace analyzer instance."""
    if not hasattr(_load_insightface_analyzer, "analyzer"):
        analyzer = FaceAnalysis(name="buffalo_l", providers=["cpu"])
        analyzer.prepare(ctx_id=0, det_size=(640, 640))
        _load_insightface_analyzer.analyzer = analyzer
    return _load_insightface_analyzer.analyzer


def _extract_face_embedding(image_path: str) -> list[float]:
    """
    Load an image from disk and return a single face embedding.
    Raises HTTPException on missing or multiple faces.
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError("OpenCV failed to load the image.")
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to read face image '{os.path.basename(image_path)}': {exc}"
        )

    analyzer = _load_insightface_analyzer()
    faces = analyzer.get(image)
    if len(faces) == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No face detected in image '{os.path.basename(image_path)}'. "
                "Please upload a clear image showing one face."
            )
        )
    if len(faces) > 1:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Multiple faces detected in image '{os.path.basename(image_path)}'. "
                "Please submit one face per image."
            )
        )

    embedding = faces[0].embedding
    if embedding is None or len(embedding) == 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract face embedding from '{os.path.basename(image_path)}'."
        )

    return embedding.astype(float).tolist()


def _cleanup_face_images(image_paths: list[str]) -> None:
    """Delete face image files that were saved during a failed registration."""
    for path in image_paths:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


async def register_face(student_id: str, image_paths: list[str], db: AsyncIOMotorDatabase) -> dict:
    """
    Registers a new face for the student.
    - Validates face images by extracting embeddings.
    - Creates or replaces the face registration document.
    - Updates the student's face_registered flag.
    """
    # Validate and extract embeddings for every saved face image.
    try:
        embeddings = [_extract_face_embedding(path) for path in image_paths]
    except HTTPException:
        _cleanup_face_images(image_paths)
        raise

    if len(embeddings) == 0:
        _cleanup_face_images(image_paths)
        raise HTTPException(
            status_code=400,
            detail="Face registration images must contain at least one valid face encoding."
        )

    # Average embeddings to create a stable registration descriptor.
    face_embedding = np.mean(np.vstack(embeddings), axis=0).astype(float).tolist()
    embedding_model = "insightface"

    # Check if a registration already exists
    existing = await db[FACE_COLLECTION].find_one({"student_id": student_id})
    new_version = 1
    if existing:
        new_version = existing.get("face_version", 0) + 1

    face_doc = FaceRegistrationDocument(
        student_id=student_id,
        image_paths=image_paths,
        face_embedding=face_embedding,
        embedding_model=embedding_model,
        face_version=new_version,
        status="active"
    )

    doc_dict = face_registration_to_dict(face_doc)

    # Upsert the face registration document
    await db[FACE_COLLECTION].update_one(
        {"student_id": student_id},
        {"$set": doc_dict},
        upsert=True
    )
    
    # Update the student document
    result = await db[STUDENT_COLLECTION].update_one(
        {"_id": ObjectId(student_id)},
        {"$set": {"face_registered": True}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Student not found.")
        
    return {
        "message": "Face registration successful.",
        "version": new_version,
        "registration_date": doc_dict["registration_date"]
    }


async def request_face_reset(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    """
    Flags the student's face registration with status 'reset_requested'.
    The admin will perform the actual deletion later.
    """
    existing = await db[FACE_COLLECTION].find_one({"student_id": student_id})
    if not existing:
        raise HTTPException(status_code=404, detail="No face registration found to reset.")
        
    if existing.get("status") == "reset_requested":
        raise HTTPException(status_code=400, detail="A reset request is already pending.")
        
    await db[FACE_COLLECTION].update_one(
        {"student_id": student_id},
        {"$set": {
            "status": "reset_requested",
            "updated_at": datetime.utcnow()
        }}
    )
    
    return {"message": "Face registration reset requested. Please contact the administrator."}
