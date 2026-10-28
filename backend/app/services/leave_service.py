"""
app/services/leave_service.py

Business logic for the Leave Management Module.
"""
import os
import uuid
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, UploadFile, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.models.leave import (
    LEAVE_TYPE_COLLECTION,
    LEAVE_REQUEST_COLLECTION,
    LeaveRequestDocument,
    leave_request_to_dict
)

UPLOAD_DIR = "uploads/leave_documents"
MAX_FILE_SIZE = 5 * 1024 * 1024 # 5 MB
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}

async def get_leave_types(db: AsyncIOMotorDatabase) -> list:
    cursor = db[LEAVE_TYPE_COLLECTION].find({"is_active": True})
    types = await cursor.to_list(length=100)
    for t in types:
        if "_id" in t:
            t["_id"] = str(t["_id"])
    return types

async def apply_leave(
    student_id: str,
    leave_type_id: str,
    from_date_str: str,
    to_date_str: str,
    reason: str,
    attachment: Optional[UploadFile],
    db: AsyncIOMotorDatabase
) -> dict:
    # 1. Validation: Empty reason
    if not reason or not reason.strip():
        raise HTTPException(status_code=400, detail="Reason cannot be empty.")
        
    # 2. Validation: Dates
    try:
        from_date = datetime.strptime(from_date_str, "%Y-%m-%d")
        to_date = datetime.strptime(to_date_str, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
        
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    if from_date < today:
        raise HTTPException(status_code=400, detail="Cannot apply for past dates.")
        
    if to_date < from_date:
        raise HTTPException(status_code=400, detail="To Date cannot be earlier than From Date.")
        
    total_days = (to_date - from_date).days + 1

    # 3. Validation: Leave Type
    leave_type = await db[LEAVE_TYPE_COLLECTION].find_one({"leave_type_id": leave_type_id, "is_active": True})
    if not leave_type:
        raise HTTPException(status_code=400, detail="Invalid or inactive leave type.")
        
    if total_days > leave_type.get("max_days", 999):
        raise HTTPException(status_code=400, detail=f"Leave duration exceeds maximum allowed days ({leave_type.get('max_days')}) for this type.")

    # 4. Validation: Overlapping Leaves
    overlapping = await db[LEAVE_REQUEST_COLLECTION].find_one({
        "student_id": student_id,
        "status": {"$in": ["Pending", "Approved"]},
        "$or": [
            {"from_date": {"$lte": to_date_str}, "to_date": {"$gte": from_date_str}}
        ]
    })
    
    if overlapping:
        raise HTTPException(status_code=400, detail="You already have a Pending or Approved leave during this period.")

    # 5. Attachment Handling
    attachment_path = None
    if attachment:
        ext = os.path.splitext(attachment.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Invalid file type. Allowed: PDF, JPG, JPEG, PNG.")
            
        # Check size (read up to MAX_FILE_SIZE + 1)
        contents = await attachment.read(MAX_FILE_SIZE + 1)
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File size exceeds 5MB limit.")
        
        # Reset pointer for saving
        await attachment.seek(0)
        
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        unique_filename = f"{uuid.uuid4()}{ext}"
        full_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        with open(full_path, "wb") as buffer:
            shutil.copyfileobj(attachment.file, buffer)
            
        attachment_path = f"uploads/leave_documents/{unique_filename}"
    elif leave_type.get("requires_attachment"):
        raise HTTPException(status_code=400, detail="An attachment is required for this leave type.")

    # 6. Save Request
    leave_id = str(uuid.uuid4())
    doc = LeaveRequestDocument(
        leave_id=leave_id,
        student_id=student_id,
        leave_type_id=leave_type_id,
        from_date=from_date_str,
        to_date=to_date_str,
        total_days=total_days,
        reason=reason.strip(),
        attachment_path=attachment_path
    )
    
    await db[LEAVE_REQUEST_COLLECTION].insert_one(leave_request_to_dict(doc))
    return {"message": "Leave request submitted successfully.", "leave_id": leave_id}

async def get_student_leave_history(student_id: str, db: AsyncIOMotorDatabase) -> list:
    cursor = db[LEAVE_REQUEST_COLLECTION].find({"student_id": student_id}).sort("applied_at", -1)
    requests = await cursor.to_list(length=100)
    
    for r in requests:
        if "_id" in r:
            r["_id"] = str(r["_id"])
        
        # Hydrate leave type name
        lt = await db[LEAVE_TYPE_COLLECTION].find_one({"leave_type_id": r.get("leave_type_id")})
        r["leave_type_name"] = lt.get("name") if lt else "Unknown"
        
    return requests

async def cancel_leave(student_id: str, leave_id: str, db: AsyncIOMotorDatabase) -> dict:
    request = await db[LEAVE_REQUEST_COLLECTION].find_one({"leave_id": leave_id, "student_id": student_id})
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found.")
        
    if request.get("status") != "Pending":
        raise HTTPException(status_code=400, detail="Only Pending requests can be cancelled.")
        
    await db[LEAVE_REQUEST_COLLECTION].update_one(
        {"leave_id": leave_id},
        {"$set": {
            "status": "Cancelled",
            "cancelled_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }}
    )
    
    return {"message": "Leave request cancelled successfully."}


async def _get_student_for_leave_request(request: dict, db: AsyncIOMotorDatabase) -> dict:
    student_id = request.get("student_id")
    if not student_id:
        return {}

    candidate_ids = [student_id]
    if isinstance(student_id, str):
        try:
            candidate_ids.append(ObjectId(student_id))
        except Exception:
            pass

    for candidate_id in candidate_ids:
        student = await db["students"].find_one({"_id": candidate_id})
        if student:
            return student

    return {}


async def get_teacher_pending_leaves(db: AsyncIOMotorDatabase) -> list:
    cursor = db[LEAVE_REQUEST_COLLECTION].find({"status": "Pending"}).sort("applied_at", -1)
    requests = await cursor.to_list(length=100)

    for request in requests:
        if "_id" in request:
            request["_id"] = str(request["_id"])
        student = await _get_student_for_leave_request(request, db)
        if student:
            request["student_name"] = student.get("full_name", "Unknown")
            request["student_email"] = student.get("email")
            request["student_usn"] = student.get("usn")
        else:
            request["student_name"] = "Unknown"
            request["student_email"] = None
            request["student_usn"] = None

        leave_type = await db[LEAVE_TYPE_COLLECTION].find_one({"leave_type_id": request.get("leave_type_id")})
        request["leave_type_name"] = leave_type.get("name") if leave_type else "Unknown"

    return requests


async def get_teacher_leave_detail(leave_id: str, db: AsyncIOMotorDatabase) -> dict:
    request = await db[LEAVE_REQUEST_COLLECTION].find_one({"leave_id": leave_id})
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if "_id" in request:
        request["_id"] = str(request["_id"])

    student = await _get_student_for_leave_request(request, db)
    if student:
        request["student_name"] = student.get("full_name", "Unknown")
        request["student_email"] = student.get("email")
        request["student_usn"] = student.get("usn")
    else:
        request["student_name"] = "Unknown"
        request["student_email"] = None
        request["student_usn"] = None

    leave_type = await db[LEAVE_TYPE_COLLECTION].find_one({"leave_type_id": request.get("leave_type_id")})
    request["leave_type_name"] = leave_type.get("name") if leave_type else "Unknown"

    return request


async def update_teacher_leave_decision(leave_id: str, decision: str, remarks: Optional[str], teacher_id: str, db: AsyncIOMotorDatabase) -> dict:
    request = await db[LEAVE_REQUEST_COLLECTION].find_one({"leave_id": leave_id})
    if not request:
        raise HTTPException(status_code=404, detail="Leave request not found.")

    if request.get("status") != "Pending":
        raise HTTPException(status_code=400, detail="Only pending leave requests can be reviewed.")

    update_payload = {
        "status": "Approved" if decision == "approve" else "Rejected",
        "teacher_id": teacher_id,
        "teacher_remarks": remarks.strip() if remarks and remarks.strip() else None,
        "updated_at": datetime.utcnow(),
    }

    if decision == "approve":
        update_payload["approved_at"] = datetime.utcnow()
    else:
        update_payload["rejected_at"] = datetime.utcnow()

    await db[LEAVE_REQUEST_COLLECTION].update_one({"leave_id": leave_id}, {"$set": update_payload})
    return {"message": f"Leave request {decision}d successfully."}
