"""
app/services/attendance_service.py

Business logic for the Attendance Module.
"""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.attendance import (
    ATTENDANCE_SESSION_COLLECTION,
    ATTENDANCE_RECORD_COLLECTION,
    AttendanceSessionDocument,
    AttendanceRecordDocument,
    session_to_dict,
    record_to_dict
)
from app.models.student import STUDENT_COLLECTION

def generate_secure_token() -> str:
    return secrets.token_urlsafe(32)

async def start_session(teacher_id: str, payload: dict, db: AsyncIOMotorDatabase) -> dict:
    session_id = str(uuid.uuid4())
    
    # Check if there is already an active session for this teacher
    existing = await db[ATTENDANCE_SESSION_COLLECTION].find_one({
        "teacher_id": teacher_id,
        "status": "active"
    })
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active session. End it before starting a new one."
        )

    doc = AttendanceSessionDocument(
        session_id=session_id,
        teacher_id=teacher_id,
        department=payload.get("department", ""),
        semester=payload.get("semester", 1),
        section=payload.get("section", ""),
        subject=payload.get("subject", ""),
        room=payload.get("room", ""),
        qr_token=generate_secure_token()
    )
    
    await db[ATTENDANCE_SESSION_COLLECTION].insert_one(session_to_dict(doc))
    return {"message": "Session started", "session_id": session_id, "qr_token": doc.qr_token, "qr_rotation_interval": doc.qr_rotation_interval}


async def rotate_qr(teacher_id: str, db: AsyncIOMotorDatabase) -> dict:
    session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({
        "teacher_id": teacher_id,
        "status": {"$in": ["active", "paused"]}
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="No active session found.")
        
    new_token = generate_secure_token()
    new_version = session.get("token_version", 1) + 1
    
    await db[ATTENDANCE_SESSION_COLLECTION].update_one(
        {"session_id": session["session_id"]},
        {"$set": {
            "qr_token": new_token,
            "token_version": new_version,
            "updated_at": datetime.utcnow()
        }}
    )
    
    return {"message": "QR rotated", "qr_token": new_token, "token_version": new_version}


async def change_session_status(teacher_id: str, new_status: str, db: AsyncIOMotorDatabase) -> dict:
    session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({
        "teacher_id": teacher_id,
        "status": {"$in": ["active", "paused"]}
    })
    
    if not session:
        raise HTTPException(status_code=404, detail="No ongoing session found.")
        
    update_data = {"status": new_status, "updated_at": datetime.utcnow()}
    if new_status == "ended":
        update_data["expiry_time"] = datetime.utcnow()
        
    await db[ATTENDANCE_SESSION_COLLECTION].update_one(
        {"session_id": session["session_id"]},
        {"$set": update_data}
    )
    
    return {"message": f"Session {new_status}"}


async def get_live_attendance(teacher_id: str, db: AsyncIOMotorDatabase) -> list:
    session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({
        "teacher_id": teacher_id,
        "status": {"$in": ["active", "paused"]}
    })
    
    if not session:
        return []
        
    records_cursor = db[ATTENDANCE_RECORD_COLLECTION].find({"session_id": session["session_id"]})
    records = await records_cursor.to_list(length=1000)
    
    # Enrich with student details (this is a simplified approach, usually requires aggregate)
    enriched_records = []
    for r in records:
        student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(r["student_id"])})
        enriched_records.append({
            "student_name": student.get("full_name") if student else "Unknown",
            "usn": student.get("usn", "N/A"),
            "status": r["attendance_status"],
            "timestamp": r["timestamp"]
        })
        
    return enriched_records


async def get_teacher_attendance_sessions(
    teacher_id: str,
    db: AsyncIOMotorDatabase,
    subject: Optional[str] = None,
    department: Optional[str] = None,
    semester: Optional[str] = None,
    section: Optional[str] = None,
    date: Optional[str] = None,
) -> list:
    query = {"teacher_id": teacher_id}

    if subject and subject.strip():
        query["subject"] = {"$regex": subject.strip(), "$options": "i"}
    if department and department.strip():
        query["department"] = department.strip()
    if semester and semester.strip():
        query["semester"] = int(semester)
    if section and section.strip():
        query["section"] = section.strip().upper()
    if date and date.strip():
        try:
            day_start = datetime.strptime(date.strip(), "%Y-%m-%d")
            day_end = day_start + timedelta(days=1)
            query["start_time"] = {"$gte": day_start, "$lt": day_end}
        except ValueError:
            pass

    cursor = db[ATTENDANCE_SESSION_COLLECTION].find(query).sort("start_time", -1)
    sessions = await cursor.to_list(length=200)

    for session in sessions:
        if "_id" in session:
            session["_id"] = str(session["_id"])
        session["present_count"] = await db[ATTENDANCE_RECORD_COLLECTION].count_documents({
            "session_id": session["session_id"],
            "attendance_status": "Present",
        })
        session["absent_count"] = await db[ATTENDANCE_RECORD_COLLECTION].count_documents({
            "session_id": session["session_id"],
            "attendance_status": {"$in": ["Absent", "Late", "Excused"]},
        })

    return sessions


async def get_teacher_attendance_session_detail(session_id: str, teacher_id: str, db: AsyncIOMotorDatabase) -> dict:
    session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({"session_id": session_id, "teacher_id": teacher_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")

    if "_id" in session:
        session["_id"] = str(session["_id"])

    records_cursor = db[ATTENDANCE_RECORD_COLLECTION].find({"session_id": session_id}).sort("timestamp", -1)
    records = await records_cursor.to_list(length=1000)

    for record in records:
        if "_id" in record:
            record["_id"] = str(record["_id"])
        student_id = record.get("student_id")
        student = None
        if student_id:
            try:
                student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
            except Exception:
                student = await db[STUDENT_COLLECTION].find_one({"_id": student_id})
        record["student_name"] = student.get("full_name") if student else "Unknown"
        record["student_usn"] = student.get("usn") if student else "N/A"

    return {"session": session, "records": records}


async def scan_qr(student: dict, qr_token: str, db: AsyncIOMotorDatabase) -> dict:
    # 1. Pre-checks on student
    if not student.get("profile_completed", False):
        raise HTTPException(status_code=403, detail="Profile incomplete.")
    
    if not student.get("face_registered", False):
        raise HTTPException(status_code=403, detail="Face registration required.")

    # 2. Find session by QR token
    session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({"qr_token": qr_token})
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired QR token.")
        
    if session["status"] != "active":
        raise HTTPException(status_code=400, detail="Session is not active.")
        
    # 3. Match department, semester, section
    if (session["department"] != student.get("department") or
        session["semester"] != student.get("semester") or
        session["section"] != student.get("section")):
        raise HTTPException(status_code=403, detail="You do not belong to this class session.")
        
    # 4. Duplicate check
    student_id = str(student["_id"])
    existing = await db[ATTENDANCE_RECORD_COLLECTION].find_one({
        "session_id": session["session_id"],
        "student_id": student_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="Attendance already marked.")
        
    # 5. Record attendance
    doc = AttendanceRecordDocument(
        attendance_id=str(uuid.uuid4()),
        session_id=session["session_id"],
        student_id=student_id,
        attendance_status="Present",
        qr_verified=True
    )
    
    await db[ATTENDANCE_RECORD_COLLECTION].insert_one(record_to_dict(doc))
    
    return {"message": "Attendance marked successfully."}


async def get_active_session_by_id(session_id: str, db: AsyncIOMotorDatabase) -> dict:
    session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({
        "session_id": session_id,
        "status": {"$in": ["active", "paused"]}
    })
    if not session:
        raise HTTPException(status_code=404, detail="Active attendance session not found.")
    return session


async def get_marked_student_ids(session_id: str, db: AsyncIOMotorDatabase) -> set:
    cursor = db[ATTENDANCE_RECORD_COLLECTION].find({"session_id": session_id})
    records = await cursor.to_list(length=10000)
    return {record["student_id"] for record in records if record.get("student_id")}


async def mark_face_attendance(
    session_id: str,
    student_id: str,
    similarity_score: float,
    db: AsyncIOMotorDatabase,
) -> dict:
    existing = await db[ATTENDANCE_RECORD_COLLECTION].find_one({
        "session_id": session_id,
        "student_id": student_id,
    })

    if existing:
        return {"marked": False, "reason": "already_marked"}

    doc = AttendanceRecordDocument(
        attendance_id=str(uuid.uuid4()),
        session_id=session_id,
        student_id=student_id,
        attendance_status="Present",
        qr_verified=False,
        face_verified=True,
        face_match_score=float(similarity_score),
    )

    await db[ATTENDANCE_RECORD_COLLECTION].insert_one(record_to_dict(doc))
    return {"marked": True, "attendance_id": doc.attendance_id}


async def get_student_history(student_id: str, db: AsyncIOMotorDatabase) -> list:
    cursor = db[ATTENDANCE_RECORD_COLLECTION].find({"student_id": student_id}).sort("timestamp", -1)
    records = await cursor.to_list(length=100)
    
    history = []
    for r in records:
        session = await db[ATTENDANCE_SESSION_COLLECTION].find_one({"session_id": r["session_id"]})
        history.append({
            "subject": session["subject"] if session else "Unknown",
            "status": r["attendance_status"],
            "timestamp": r["timestamp"]
        })
    return history

async def get_student_summary(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    count = await db[ATTENDANCE_RECORD_COLLECTION].count_documents({"student_id": student_id})
    return {
        "total_classes": count,
        "present": count,
        "percentage": 100 if count > 0 else 0
    }
