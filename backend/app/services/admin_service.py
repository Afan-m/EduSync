import logging
import uuid
from datetime import datetime
from typing import Any

from bson import ObjectId
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.security import hash_password, verify_password
from app.models.academic import (
    ACADEMIC_CONFIG_COLLECTION,
    DEPARTMENTS_COLLECTION,
    AcademicConfigDocument,
    DepartmentDocument,
    academic_config_to_dict,
    department_to_dict,
)
from app.models.attendance import ATTENDANCE_RECORD_COLLECTION, ATTENDANCE_SESSION_COLLECTION
from app.models.leave import LEAVE_REQUEST_COLLECTION
from app.models.timetable import (
    SUBJECT_COLLECTION,
    TIMETABLE_COLLECTION,
    SubjectDocument,
    TimetableDocument,
    subject_to_dict,
    timetable_to_dict,
)

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_NAME = "Afan"
DEFAULT_ADMIN_EMAIL = "afan@admin.in"
DEFAULT_ADMIN_PASSWORD = "Admin@123"
VALID_SECTIONS = ["A", "B", "C", "D"]


def _serialize(doc: dict | None) -> dict | None:
    if not doc:
        return None
    if "_id" in doc:
        doc = dict(doc)
        doc["_id"] = str(doc["_id"])
    return doc


async def authenticate_admin(request: Any, db: AsyncIOMotorDatabase) -> dict:
    collection = db["admins"]
    admin = await collection.find_one({"email": request.email})

    if not admin:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if admin.get("role") != "admin":
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not verify_password(request.password, admin.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if admin.get("is_active") is False:
        raise HTTPException(status_code=403, detail="Your account is inactive. Please contact the administrator.")

    if admin.get("account_status") in {"blocked", "inactive"}:
        raise HTTPException(status_code=403, detail="Your account is inactive or blocked. Please contact the administrator.")

    logger.info(f"Admin authentication successful for {request.email}")
    return admin


async def seed_admin_account(db: AsyncIOMotorDatabase) -> None:
    """Ensure exactly one admin account exists and that it is the seeded permanent admin."""
    admin_collection = db["admins"]
    admins = await admin_collection.find({}).to_list(length=None)

    if not admins:
        admin_doc = {
            "full_name": DEFAULT_ADMIN_NAME,
            "email": DEFAULT_ADMIN_EMAIL,
            "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
            "role": "admin",
            "is_active": True,
            "account_status": "active",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await admin_collection.insert_one(admin_doc)
        return

    primary_admin = None
    for admin in admins:
        if admin.get("email") == DEFAULT_ADMIN_EMAIL:
            primary_admin = admin
            break
    if primary_admin is None:
        for admin in admins:
            if admin.get("email") == "admin@edusync.com":
                primary_admin = admin
                break
    if primary_admin is None:
        primary_admin = admins[0]

    await admin_collection.update_one(
        {"_id": primary_admin["_id"]},
        {
            "$set": {
                "full_name": DEFAULT_ADMIN_NAME,
                "email": DEFAULT_ADMIN_EMAIL,
                "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
                "role": "admin",
                "is_active": True,
                "account_status": "active",
                "updated_at": datetime.utcnow(),
            }
        },
    )

    duplicate_ids = [admin["_id"] for admin in admins if admin["_id"] != primary_admin["_id"]]
    if duplicate_ids:
        await admin_collection.delete_many({"_id": {"$in": duplicate_ids}})


async def get_admin_dashboard_summary(db: AsyncIOMotorDatabase) -> dict:
    students = await db["students"].find({"role": "student"}).to_list(length=1000)
    teachers = await db["teachers"].find({"role": "teacher"}).to_list(length=1000)
    leave_requests = await db[LEAVE_REQUEST_COLLECTION].find({}).to_list(length=1000)
    attendance_sessions = await db[ATTENDANCE_SESSION_COLLECTION].find({"status": {"$in": ["active", "paused"]}}).to_list(length=1000)

    departments = sorted({s.get("department") for s in students if s.get("department")})
    departments.extend(sorted({t.get("department") for t in teachers if t.get("department")}))
    departments = sorted(set(departments))

    recent_activity = []
    for item in sorted(leave_requests, key=lambda x: x.get("applied_at", datetime.utcnow()), reverse=True)[:5]:
        recent_activity.append({
            "title": f"Leave request {item.get('status', 'Pending')}",
            "message": f"{item.get('student_id', 'Student')} requested leave",
            "time": item.get("applied_at"),
        })

    for item in sorted(attendance_sessions, key=lambda x: x.get("start_time", datetime.utcnow()), reverse=True)[:3]:
        recent_activity.append({
            "title": "Active attendance session",
            "message": f"{item.get('subject', 'Class')} in {item.get('department', 'Dept')}",
            "time": item.get("start_time"),
        })

    recent_activity = sorted(recent_activity, key=lambda x: x.get("time", datetime.utcnow()), reverse=True)[:6]

    return {
        "total_students": len(students),
        "total_teachers": len(teachers),
        "total_departments": len(departments),
        "pending_leave_requests": sum(1 for item in leave_requests if item.get("status") == "Pending"),
        "active_attendance_sessions": len(attendance_sessions),
        "recent_activity": recent_activity,
        "quick_actions": [
            {"label": "Manage users", "view": "admin_users"},
            {"label": "Academic setup", "view": "admin_academics"},
            {"label": "Leave review", "view": "admin_leaves"},
        ],
    }


async def list_departments(db: AsyncIOMotorDatabase) -> list[dict]:
    cursor = db[DEPARTMENTS_COLLECTION].find({}).sort("name", 1)
    items = await cursor.to_list(length=200)
    return [_serialize(item) for item in items]


async def create_department(payload: dict, db: AsyncIOMotorDatabase) -> dict:
    name = (payload.get("name") or "").strip()
    code = (payload.get("code") or "").strip().upper()
    total_semesters = int(payload.get("total_semesters") or 4)
    if not name or not code:
        raise HTTPException(status_code=400, detail="Department name and code are required.")
    existing = await db[DEPARTMENTS_COLLECTION].find_one({"$or": [{"name": {"$regex": f"^{name}$", "$options": "i"}}, {"code": code}]})
    if existing:
        raise HTTPException(status_code=409, detail="Department already exists.")
    doc = DepartmentDocument(name=name, code=code, total_semesters=total_semesters, active=bool(payload.get("active", True)))
    await db[DEPARTMENTS_COLLECTION].insert_one(department_to_dict(doc))
    return {"message": "Department created."}


async def update_department(department_id: str, payload: dict, db: AsyncIOMotorDatabase) -> dict:
    try:
        obj_id = ObjectId(department_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid department id.")
    update = {}
    if payload.get("name"):
        update["name"] = payload.get("name").strip()
    if payload.get("code"):
        update["code"] = payload.get("code").strip().upper()
    if payload.get("total_semesters") is not None:
        update["total_semesters"] = int(payload.get("total_semesters"))
    if payload.get("active") is not None:
        update["active"] = bool(payload.get("active"))
    await db[DEPARTMENTS_COLLECTION].update_one({"_id": obj_id}, {"$set": update})
    return {"message": "Department updated."}


async def delete_department(department_id: str, db: AsyncIOMotorDatabase) -> dict:
    try:
        obj_id = ObjectId(department_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid department id.")
    await db[DEPARTMENTS_COLLECTION].delete_one({"_id": obj_id})
    return {"message": "Department deleted."}


async def list_subjects(db: AsyncIOMotorDatabase) -> list[dict]:
    cursor = db[SUBJECT_COLLECTION].find({}).sort("subject_name", 1)
    items = await cursor.to_list(length=400)
    return [_serialize(item) for item in items]


async def create_subject(payload: dict, db: AsyncIOMotorDatabase) -> dict:
    required = ["subject_code", "subject_name", "department", "semester", "credits", "faculty_id"]
    for field in required:
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required.")
    doc = SubjectDocument(
        subject_id=str(uuid.uuid4()),
        subject_code=str(payload["subject_code"]).strip().upper(),
        subject_name=str(payload["subject_name"]).strip(),
        department=str(payload["department"]).strip(),
        semester=int(payload["semester"]),
        credits=int(payload["credits"]),
        faculty_id=str(payload["faculty_id"]).strip(),
        is_active=bool(payload.get("is_active", True)),
    )
    await db[SUBJECT_COLLECTION].insert_one(subject_to_dict(doc))
    return {"message": "Subject created."}


async def update_subject(subject_id: str, payload: dict, db: AsyncIOMotorDatabase) -> dict:
    try:
        obj_id = ObjectId(subject_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid subject id.")
    update = {}
    for key in ["subject_code", "subject_name", "department", "semester", "credits", "faculty_id", "is_active"]:
        if key in payload:
            value = payload[key]
            if key in {"semester", "credits"}:
                value = int(value)
            if key == "is_active":
                value = bool(value)
            update[key] = value
    await db[SUBJECT_COLLECTION].update_one({"_id": obj_id}, {"$set": update})
    return {"message": "Subject updated."}


async def delete_subject(subject_id: str, db: AsyncIOMotorDatabase) -> dict:
    try:
        obj_id = ObjectId(subject_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid subject id.")
    await db[SUBJECT_COLLECTION].delete_one({"_id": obj_id})
    return {"message": "Subject deleted."}


async def list_timetables(db: AsyncIOMotorDatabase) -> list[dict]:
    cursor = db[TIMETABLE_COLLECTION].find({}).sort("department", 1)
    items = await cursor.to_list(length=400)
    return [_serialize(item) for item in items]


async def create_timetable(payload: dict, db: AsyncIOMotorDatabase) -> dict:
    required = ["department", "semester", "section", "day_of_week"]
    for field in required:
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required.")
    doc = TimetableDocument(
        timetable_id=str(uuid.uuid4()),
        department=str(payload["department"]).strip(),
        semester=int(payload["semester"]),
        section=str(payload["section"]).strip().upper(),
        day_of_week=str(payload["day_of_week"]).strip(),
        periods=payload.get("periods", []),
        is_active=bool(payload.get("is_active", True)),
    )
    await db[TIMETABLE_COLLECTION].insert_one(timetable_to_dict(doc))
    return {"message": "Timetable created."}


async def create_teacher(payload: dict, db: AsyncIOMotorDatabase) -> dict:
    """Create a teacher account. Validates unique email and hashes password."""
    full_name = (payload.get("full_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""
    department = (payload.get("department") or "").strip()
    designation = (payload.get("designation") or "").strip()
    phone = (payload.get("phone") or "").strip()

    if not full_name or not email or not password:
        raise HTTPException(status_code=400, detail="full_name, email and password are required.")

    # Check uniqueness
    existing = await db["teachers"].find_one({"email": email})
    if existing:
        raise HTTPException(status_code=409, detail="A teacher with this email already exists.")

    teacher_doc = {
        "full_name": full_name,
        "email": email,
        "password_hash": hash_password(password),
        "department": department,
        "designation": designation or None,
        "phone": phone or None,
        "role": "teacher",
        "is_active": True,
        "account_status": "active",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }

    result = await db["teachers"].insert_one(teacher_doc)
    return {"message": "Teacher created.", "teacher_id": str(result.inserted_id)}


async def update_timetable(timetable_id: str, payload: dict, db: AsyncIOMotorDatabase) -> dict:
    try:
        obj_id = ObjectId(timetable_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timetable id.")
    update = {}
    for key in ["department", "semester", "section", "day_of_week", "periods", "is_active"]:
        if key in payload:
            value = payload[key]
            if key == "semester":
                value = int(value)
            if key == "section":
                value = str(value).strip().upper()
            if key == "is_active":
                value = bool(value)
            update[key] = value
    await db[TIMETABLE_COLLECTION].update_one({"_id": obj_id}, {"$set": update})
    return {"message": "Timetable updated."}


async def delete_timetable(timetable_id: str, db: AsyncIOMotorDatabase) -> dict:
    try:
        obj_id = ObjectId(timetable_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timetable id.")
    await db[TIMETABLE_COLLECTION].delete_one({"_id": obj_id})
    return {"message": "Timetable deleted."}


async def get_academic_config(db: AsyncIOMotorDatabase) -> dict:
    doc = await db[ACADEMIC_CONFIG_COLLECTION].find_one({"key": "sections"})
    sections = doc.get("value", VALID_SECTIONS) if doc else VALID_SECTIONS
    return {"sections": sections, "departments": await list_departments(db)}


async def update_sections(payload: dict, db: AsyncIOMotorDatabase) -> dict:
    sections = payload.get("sections") or []
    if not isinstance(sections, list) or not sections:
        raise HTTPException(status_code=400, detail="At least one section is required.")
    await db[ACADEMIC_CONFIG_COLLECTION].update_one(
        {"key": "sections"},
        {"$set": {"value": [str(item).strip().upper() for item in sections], "updated_at": datetime.utcnow()}},
        upsert=True,
    )
    return {"message": "Sections updated."}


async def get_admin_attendance_summary(db: AsyncIOMotorDatabase, status: str | None = None, search: str | None = None, department: str | None = None, date: str | None = None) -> dict:
    query: dict = {}
    if status:
        query["status"] = status
    if department:
        query["department"] = department
    if search:
        term = search.strip()
        query["$or"] = [
            {"subject": {"$regex": term, "$options": "i"}},
            {"department": {"$regex": term, "$options": "i"}},
            {"section": {"$regex": term, "$options": "i"}},
        ]
    if date:
        try:
            start = datetime.strptime(date, "%Y-%m-%d")
            end = start.replace(hour=23, minute=59, second=59, microsecond=999999)
            query["start_time"] = {"$gte": start, "$lt": end}
        except ValueError:
            pass

    sessions = await db[ATTENDANCE_SESSION_COLLECTION].find(query).sort("start_time", -1).to_list(length=500)
    for session in sessions:
        session["present_count"] = await db[ATTENDANCE_RECORD_COLLECTION].count_documents({"session_id": session.get("session_id"), "attendance_status": "Present"})
        session["absent_count"] = await db[ATTENDANCE_RECORD_COLLECTION].count_documents({"session_id": session.get("session_id"), "attendance_status": {"$in": ["Absent", "Late", "Excused"]}})
        session["total_count"] = session["present_count"] + session["absent_count"]
        if "_id" in session:
            session["_id"] = str(session["_id"])

    summary = {
        "total_sessions": await db[ATTENDANCE_SESSION_COLLECTION].count_documents({}),
        "active_sessions": await db[ATTENDANCE_SESSION_COLLECTION].count_documents({"status": {"$in": ["active", "paused"]}}),
        "completed_sessions": await db[ATTENDANCE_SESSION_COLLECTION].count_documents({"status": "ended"}),
        "total_records": await db[ATTENDANCE_RECORD_COLLECTION].count_documents({}),
        "present_records": await db[ATTENDANCE_RECORD_COLLECTION].count_documents({"attendance_status": "Present"}),
        "absent_records": await db[ATTENDANCE_RECORD_COLLECTION].count_documents({"attendance_status": {"$in": ["Absent", "Late", "Excused"]}}),
    }
    return {"summary": summary, "sessions": sessions}


async def list_admin_leaves(db: AsyncIOMotorDatabase, status: str | None = None, search: str | None = None) -> list[dict]:
    query: dict = {}
    if status:
        query["status"] = status
    if search:
        term = search.strip()
        query["$or"] = [
            {"reason": {"$regex": term, "$options": "i"}},
            {"leave_id": {"$regex": term, "$options": "i"}},
        ]
    cursor = db[LEAVE_REQUEST_COLLECTION].find(query).sort("applied_at", -1)
    requests = await cursor.to_list(length=500)
    for request in requests:
        request["_id"] = str(request["_id"])
        student = await db["students"].find_one({"_id": ObjectId(request.get("student_id"))}) if request.get("student_id") else None
        if student:
            request["student_name"] = student.get("full_name", "Unknown")
            request["student_email"] = student.get("email")
            request["student_usn"] = student.get("usn")
        else:
            request["student_name"] = "Unknown"
            request["student_email"] = None
            request["student_usn"] = None
    return requests


async def override_leave_decision(leave_id: str, payload: dict, admin_id: str, db: AsyncIOMotorDatabase) -> dict:
    request = await db[LEAVE_REQUEST_COLLECTION].find_one({"leave_id": leave_id})
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found.")
    status_value = (payload.get("status") or "Approved").strip()
    if status_value not in {"Approved", "Rejected", "Pending", "Cancelled"}:
        raise HTTPException(status_code=400, detail="Invalid leave status.")
    update = {
        "status": status_value,
        "admin_id": admin_id,
        "admin_remarks": (payload.get("remarks") or "").strip() or None,
        "updated_at": datetime.utcnow(),
    }
    if status_value == "Approved":
        update["approved_at"] = datetime.utcnow()
    if status_value == "Rejected":
        update["rejected_at"] = datetime.utcnow()
    if status_value == "Cancelled":
        update["cancelled_at"] = datetime.utcnow()
    await db[LEAVE_REQUEST_COLLECTION].update_one({"leave_id": leave_id}, {"$set": update})
    return {"message": "Leave decision updated."}


async def get_admin_reports(db: AsyncIOMotorDatabase) -> dict:
    students = await db["students"].find({"role": "student"}).to_list(length=1000)
    teachers = await db["teachers"].find({"role": "teacher"}).to_list(length=1000)
    departments = await list_departments(db)
    subjects = await db[SUBJECT_COLLECTION].find({"is_active": True}).to_list(length=500)
    leave_requests = await db[LEAVE_REQUEST_COLLECTION].find({}).to_list(length=1000)
    attendance_records = await db[ATTENDANCE_RECORD_COLLECTION].find({}).to_list(length=5000)

    department_summary = []
    for department in departments:
        department_summary.append({
            "department": department.get("name"),
            "students": sum(1 for student in students if student.get("department") == department.get("name")),
            "subjects": sum(1 for subject in subjects if subject.get("department") == department.get("name")),
        })

    subject_summary = []
    for subject in subjects:
        subject_summary.append({
            "subject_name": subject.get("subject_name"),
            "subject_code": subject.get("subject_code"),
            "department": subject.get("department"),
            "semester": subject.get("semester"),
        })

    return {
        "total_students": len(students),
        "total_teachers": len(teachers),
        "attendance_summary": {
            "total_records": len(attendance_records),
            "present": sum(1 for record in attendance_records if record.get("attendance_status") == "Present"),
            "absent": sum(1 for record in attendance_records if record.get("attendance_status") in {"Absent", "Late", "Excused"}),
        },
        "leave_summary": {
            "pending": sum(1 for item in leave_requests if item.get("status") == "Pending"),
            "approved": sum(1 for item in leave_requests if item.get("status") == "Approved"),
            "rejected": sum(1 for item in leave_requests if item.get("status") == "Rejected"),
            "cancelled": sum(1 for item in leave_requests if item.get("status") == "Cancelled"),
        },
        "department_summary": department_summary,
        "subject_summary": subject_summary,
    }
