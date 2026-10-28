"""Teacher authentication and attendance routes."""

from fastapi import APIRouter, Body, Depends, status

from app.core.database import get_database
from app.core.security import create_access_token
from app.auth_dependencies import get_current_teacher
from app.schemas.teacher import TeacherLoginRequest, TeacherLoginResponse, TeacherPublicProfile
from app.services.attendance_service import (
    change_session_status,
    get_live_attendance,
    get_teacher_attendance_session_detail,
    get_teacher_attendance_sessions,
    rotate_qr,
    start_session,
)
from app.services.live_face_attendance import run_live_attendance
from app.core.database import get_database
import asyncio
from app.services.leave_service import (
    get_teacher_pending_leaves,
    get_teacher_leave_detail,
    update_teacher_leave_decision,
)
from app.services.student_service import get_teacher_students, get_teacher_student_detail
from app.services.teacher_service import authenticate_teacher
from app.services.timetable_service import get_teacher_timetable
from app.services.report_service import get_teacher_reports

router = APIRouter(prefix="/teacher", tags=["Teacher"])


@router.get("/ping")
async def ping():
    """Confirms the teacher module is registered."""
    return {"module": "teacher", "status": "ready"}


@router.post(
    "/login",
    response_model=TeacherLoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Teacher login",
)
async def teacher_login(request: TeacherLoginRequest):
    db = get_database()
    teacher = await authenticate_teacher(request, db)

    teacher_id = str(teacher["_id"])
    token_payload = {
        "teacher_id": teacher_id,
        "email": teacher["email"],
        "role": teacher["role"],
    }
    access_token = create_access_token(token_payload)

    public_profile = TeacherPublicProfile(
        id=teacher_id,
        employee_id=teacher.get("employee_id"),
        full_name=teacher.get("full_name", "Teacher"),
        email=teacher["email"],
        department=teacher.get("department"),
        designation=teacher.get("designation"),
        subjects=teacher.get("subjects", []),
        profile_photo=teacher.get("profile_photo"),
        phone=teacher.get("phone"),
        is_active=teacher.get("is_active", True),
    )

    return TeacherLoginResponse(
        success=True,
        message="Login successful.",
        access_token=access_token,
        token_type="bearer",
        teacher=public_profile,
    )


@router.get("/me", response_model=TeacherPublicProfile)
async def teacher_me(current_teacher: dict = Depends(get_current_teacher)):
    return TeacherPublicProfile(
        id=str(current_teacher["_id"]),
        employee_id=current_teacher.get("employee_id"),
        full_name=current_teacher.get("full_name", "Teacher"),
        email=current_teacher.get("email"),
        department=current_teacher.get("department"),
        designation=current_teacher.get("designation"),
        subjects=current_teacher.get("subjects", []),
        profile_photo=current_teacher.get("profile_photo"),
        phone=current_teacher.get("phone"),
        is_active=current_teacher.get("is_active", True),
    )


@router.post("/logout")
async def teacher_logout():
    return {"success": True, "message": "Teacher logout acknowledged."}


@router.post("/attendance/start", status_code=status.HTTP_201_CREATED)
async def teacher_start_attendance(
    payload: dict = Body(...),
    current_teacher: dict = Depends(get_current_teacher),
):
    db = get_database()
    return await start_session(str(current_teacher["_id"]), payload, db)


@router.post("/attendance/rotate")
async def teacher_rotate_qr(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await rotate_qr(str(current_teacher["_id"]), db)


@router.post("/attendance/pause")
async def teacher_pause_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await change_session_status(str(current_teacher["_id"]), "paused", db)


@router.post("/attendance/resume")
async def teacher_resume_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await change_session_status(str(current_teacher["_id"]), "active", db)


@router.post("/attendance/end")
async def teacher_end_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await change_session_status(str(current_teacher["_id"]), "ended", db)


@router.get("/attendance/live")
async def teacher_live_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    records = await get_live_attendance(str(current_teacher["_id"]), db)
    return {"records": records}


@router.post("/attendance/live/start")
async def teacher_start_live_attendance(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()

    # Find the teacher's active session
    session = await db["attendance_sessions"].find_one({
        "teacher_id": str(current_teacher["_id"]),
        "status": {"$in": ["active", "paused"]},
    })

    if not session:
        return {"started": False, "message": "No active attendance session found."}

    session_id = session["session_id"]

    # Launch live attendance as a background task so the HTTP request returns immediately.
    asyncio.create_task(run_live_attendance(session_id=session_id, db=db))

    return {"started": True, "message": "Live attendance started."}


@router.get("/attendance/sessions")
async def teacher_attendance_sessions(
    subject: str | None = None,
    department: str | None = None,
    semester: str | None = None,
    section: str | None = None,
    date: str | None = None,
    current_teacher: dict = Depends(get_current_teacher),
):
    db = get_database()
    return {
        "sessions": await get_teacher_attendance_sessions(
            str(current_teacher["_id"]),
            db,
            subject=subject,
            department=department,
            semester=semester,
            section=section,
            date=date,
        )
    }


@router.get("/attendance/sessions/{session_id}")
async def teacher_attendance_session_detail(session_id: str, current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await get_teacher_attendance_session_detail(session_id, str(current_teacher["_id"]), db)


@router.get("/timetable")
async def teacher_timetable(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await get_teacher_timetable(str(current_teacher["_id"]), db)


@router.get("/reports")
async def teacher_reports(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await get_teacher_reports(str(current_teacher["_id"]), db)


@router.get("/students")
async def teacher_students(
    search: str | None = None,
    department: str | None = None,
    semester: str | None = None,
    section: str | None = None,
    current_teacher: dict = Depends(get_current_teacher),
):
    db = get_database()
    return {"students": await get_teacher_students(
        db,
        search=search,
        department=department,
        semester=semester,
        section=section,
        teacher_department=current_teacher.get("department"),
    )}


@router.get("/students/{student_id}")
async def teacher_student_detail(student_id: str, current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await get_teacher_student_detail(student_id, db)


@router.get("/leave/pending")
async def teacher_pending_leaves(current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return {"requests": await get_teacher_pending_leaves(db)}


@router.get("/leave/{leave_id}")
async def teacher_leave_detail(leave_id: str, current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    return await get_teacher_leave_detail(leave_id, db)


@router.put("/leave/{leave_id}/approve")
async def teacher_approve_leave(leave_id: str, payload: dict = Body(default=None), current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    remarks = (payload or {}).get("remarks") if payload else None
    return await update_teacher_leave_decision(leave_id, "approve", remarks, str(current_teacher["_id"]), db)


@router.put("/leave/{leave_id}/reject")
async def teacher_reject_leave(leave_id: str, payload: dict = Body(default=None), current_teacher: dict = Depends(get_current_teacher)):
    db = get_database()
    remarks = (payload or {}).get("remarks") if payload else None
    return await update_teacher_leave_decision(leave_id, "reject", remarks, str(current_teacher["_id"]), db)
