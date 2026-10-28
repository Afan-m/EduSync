from collections import Counter
from typing import Optional

from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.attendance import ATTENDANCE_RECORD_COLLECTION, ATTENDANCE_SESSION_COLLECTION
from app.models.leave import LEAVE_REQUEST_COLLECTION
from app.models.student import STUDENT_COLLECTION
from app.models.timetable import SUBJECT_COLLECTION, TIMETABLE_COLLECTION


async def get_teacher_reports(teacher_id: str, db: AsyncIOMotorDatabase) -> dict:
    sessions = await db[ATTENDANCE_SESSION_COLLECTION].find({"teacher_id": teacher_id}).to_list(length=500)
    records = await db[ATTENDANCE_RECORD_COLLECTION].find({"session_id": {"$in": [s["session_id"] for s in sessions]}}).to_list(length=5000)
    leave_requests = await db[LEAVE_REQUEST_COLLECTION].find({}).to_list(length=500)
    students = await db[STUDENT_COLLECTION].find({"role": "student"}).to_list(length=500)
    subjects = await db[SUBJECT_COLLECTION].find({"is_active": True}).to_list(length=500)

    total_sessions = len(sessions)
    present_count = sum(1 for r in records if r.get("attendance_status") == "Present")
    absent_count = sum(1 for r in records if r.get("attendance_status") in {"Absent", "Late", "Excused"})
    average_attendance = round((present_count / len(records) * 100) if records else 0, 2)

    leave_summary = {
        "pending": sum(1 for r in leave_requests if r.get("status") == "Pending"),
        "approved": sum(1 for r in leave_requests if r.get("status") == "Approved"),
        "rejected": sum(1 for r in leave_requests if r.get("status") == "Rejected"),
    }

    department_counts = Counter(student.get("department") for student in students if student.get("department"))
    semester_counts = Counter(str(student.get("semester")) for student in students if student.get("semester") is not None)

    subject_stats = []
    for subject in subjects:
        subject_sessions = [s for s in sessions if s.get("subject") == subject.get("subject_name")]
        subject_records = [r for r in records if any(s["session_id"] == r.get("session_id") for s in subject_sessions)]
        if not subject_records:
            attendance_pct = 0
        else:
            present = sum(1 for r in subject_records if r.get("attendance_status") == "Present")
            attendance_pct = round((present / len(subject_records)) * 100, 2)
        subject_stats.append({
            "subject_name": subject.get("subject_name"),
            "subject_code": subject.get("subject_code"),
            "sessions_conducted": len(subject_sessions),
            "attendance_percentage": attendance_pct,
        })

    return {
        "attendance_summary": {
            "total_sessions": total_sessions,
            "average_attendance_percentage": average_attendance,
            "present_count": present_count,
            "absent_count": absent_count,
        },
        "leave_summary": leave_summary,
        "student_statistics": {
            "department_wise": [{"department": dept, "count": count} for dept, count in sorted(department_counts.items())],
            "semester_wise": [{"semester": sem, "count": count} for sem, count in sorted(semester_counts.items())],
        },
        "subject_statistics": subject_stats,
    }
