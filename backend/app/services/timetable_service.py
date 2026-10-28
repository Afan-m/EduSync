"""
app/services/timetable_service.py

Business logic for the Timetable Module.
"""
from typing import List, Dict
from datetime import datetime
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.timetable import TIMETABLE_COLLECTION, SUBJECT_COLLECTION
from app.models.student import STUDENT_COLLECTION

TEACHER_COLLECTION = "teachers"

async def _enrich_periods(periods: list, db: AsyncIOMotorDatabase) -> list:
    """Helper to fetch subject names and faculty names for the given periods."""
    enriched = []
    for p in periods:
        subject = await db[SUBJECT_COLLECTION].find_one({"subject_id": p.get("subject_id")})
        faculty = await db[TEACHER_COLLECTION].find_one({"_id": ObjectId(p.get("faculty_id"))}) if p.get("faculty_id") and len(p.get("faculty_id")) == 24 else None
        
        enriched_p = p.copy()
        enriched_p["subject_name"] = subject.get("subject_name") if subject else "Unknown Subject"
        enriched_p["subject_code"] = subject.get("subject_code") if subject else "---"
        enriched_p["faculty_name"] = faculty.get("full_name") or faculty.get("name") if faculty else "Unknown Faculty"
        enriched.append(enriched_p)
    return enriched

async def get_student_timetable(student_id: str, db: AsyncIOMotorDatabase) -> list:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department")
    sem = student.get("semester")
    sec = student.get("section")
    
    if not dept or not sem or not sec:
        return []
        
    cursor = db[TIMETABLE_COLLECTION].find({
        "department": dept,
        "semester": sem,
        "section": sec,
        "is_active": True
    })
    
    timetables = await cursor.to_list(length=10)
    
    # Enrich all periods
    for t in timetables:
        t["periods"] = await _enrich_periods(t.get("periods", []), db)
        # Convert _id to string for JSON serialization
        if "_id" in t:
            t["_id"] = str(t["_id"])
            
    return timetables

async def get_student_timetable_today(student_id: str, db: AsyncIOMotorDatabase) -> dict:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department")
    sem = student.get("semester")
    sec = student.get("section")
    
    if not dept or not sem or not sec:
        return {"periods": []}
        
    # Get current day of week as string (e.g. "Monday")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_str = days[datetime.today().weekday()]
    
    timetable = await db[TIMETABLE_COLLECTION].find_one({
        "department": dept,
        "semester": sem,
        "section": sec,
        "day_of_week": today_str,
        "is_active": True
    })
    
    if not timetable:
        return {"day_of_week": today_str, "periods": []}
        
    enriched_periods = await _enrich_periods(timetable.get("periods", []), db)
    
    # Sort periods by start time
    enriched_periods.sort(key=lambda x: x.get("start_time", "00:00"))
    
    return {
        "day_of_week": today_str,
        "periods": enriched_periods
    }

async def get_student_subjects(student_id: str, db: AsyncIOMotorDatabase) -> list:
    student = await db[STUDENT_COLLECTION].find_one({"_id": ObjectId(student_id)})
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    dept = student.get("department")
    sem = student.get("semester")
    
    if not dept or not sem:
        return []
        
    cursor = db[SUBJECT_COLLECTION].find({
        "department": dept,
        "semester": sem,
        "is_active": True
    })
    
    subjects = await cursor.to_list(length=50)
    for s in subjects:
        if "_id" in s:
            s["_id"] = str(s["_id"])
            
        faculty = await db[TEACHER_COLLECTION].find_one({"_id": ObjectId(s.get("faculty_id"))}) if s.get("faculty_id") and len(s.get("faculty_id")) == 24 else None
        s["faculty_name"] = faculty.get("full_name") or faculty.get("name") if faculty else "Unknown Faculty"
            
    return subjects


async def get_teacher_timetable(teacher_id: str, db: AsyncIOMotorDatabase) -> dict:
    teacher = await db[TEACHER_COLLECTION].find_one({"_id": ObjectId(teacher_id)}) if len(teacher_id) == 24 else None
    if not teacher:
        teacher = await db[TEACHER_COLLECTION].find_one({"_id": teacher_id})
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")

    department = teacher.get("department")
    if not department:
        return {"today": {"day_of_week": "", "periods": []}, "weekly": []}

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    today_str = days[datetime.today().weekday()]

    cursor = db[TIMETABLE_COLLECTION].find({"department": department, "is_active": True})
    timetables = await cursor.to_list(length=100)

    weekly = []
    today_periods = []

    for timetable in timetables:
        if "_id" in timetable:
            timetable["_id"] = str(timetable["_id"])

        matching_periods = []
        for period in timetable.get("periods", []):
            if str(period.get("faculty_id")) == str(teacher_id):
                matching_periods.append(period)

        if not matching_periods:
            continue

        enriched_periods = await _enrich_periods(matching_periods, db)
        enriched_periods.sort(key=lambda x: x.get("start_time", "00:00"))

        timetable_entry = {
            "timetable_id": timetable.get("timetable_id"),
            "department": timetable.get("department"),
            "semester": timetable.get("semester"),
            "section": timetable.get("section"),
            "day_of_week": timetable.get("day_of_week"),
            "periods": enriched_periods,
        }
        weekly.append(timetable_entry)

        if timetable.get("day_of_week") == today_str:
            today_periods = enriched_periods

    return {
        "today": {"day_of_week": today_str, "periods": today_periods},
        "weekly": weekly,
    }
