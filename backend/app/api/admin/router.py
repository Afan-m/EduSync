"""Admin authentication, dashboard, and user management routes."""

from fastapi import APIRouter, Body, Depends, status

from app.auth_dependencies import get_current_admin
from app.core.database import get_database
from app.core.security import create_access_token
from app.schemas.admin import AdminLoginRequest, AdminPublicProfile
from app.services.admin_service import (
    authenticate_admin,
    create_department,
    create_subject,
    create_timetable,
    delete_department,
    delete_subject,
    delete_timetable,
    get_academic_config,
    get_admin_attendance_summary,
    get_admin_dashboard_summary,
    get_admin_reports,
    list_admin_leaves,
    list_departments,
    list_subjects,
    list_timetables,
    override_leave_decision,
    update_department,
    update_sections,
    update_subject,
    update_timetable,
)
from app.services.admin_service import create_teacher

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/ping")
async def ping():
    return {"module": "admin", "status": "ready"}


@router.post("/login", status_code=status.HTTP_200_OK)
async def admin_login(request: AdminLoginRequest):
    db = get_database()
    admin = await authenticate_admin(request, db)
    token_payload = {"admin_id": str(admin["_id"]), "email": admin["email"], "role": admin["role"]}
    access_token = create_access_token(token_payload)
    return {
        "success": True,
        "message": "Login successful.",
        "access_token": access_token,
        "token_type": "bearer",
        "admin": AdminPublicProfile(id=str(admin["_id"]), full_name=admin.get("full_name"), email=admin["email"], role=admin["role"]).model_dump(),
    }


@router.get("/me")
async def admin_me(current_admin: dict = Depends(get_current_admin)):
    return {
        "id": str(current_admin["_id"]),
        "full_name": current_admin.get("full_name"),
        "email": current_admin.get("email"),
        "role": current_admin.get("role", "admin"),
    }


@router.post("/logout")
async def admin_logout():
    return {"success": True, "message": "Admin logout acknowledged."}


@router.get("/dashboard")
async def admin_dashboard(current_admin: dict = Depends(get_current_admin)):
    db = get_database()
    return await get_admin_dashboard_summary(db)


@router.get("/users")
async def admin_users(
    role: str | None = None,
    search: str | None = None,
    department: str | None = None,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    query: dict = {}

    if role in {"student", "teacher"}:
        query["role"] = role

    if search and search.strip():
        term = search.strip()
        query["$or"] = [
            {"full_name": {"$regex": term, "$options": "i"}},
            {"email": {"$regex": term, "$options": "i"}},
            {"usn": {"$regex": term, "$options": "i"}},
            {"employee_id": {"$regex": term, "$options": "i"}},
        ]

    if department and department.strip():
        query["department"] = department.strip()

    collection_name = "students" if role == "student" else "teachers" if role == "teacher" else None
    if collection_name:
        users = await db[collection_name].find(query).sort("full_name", 1).to_list(length=500)
    else:
        students = await db["students"].find({**query, "role": "student"}).sort("full_name", 1).to_list(length=500)
        teachers = await db["teachers"].find({**query, "role": "teacher"}).sort("full_name", 1).to_list(length=500)
        users = students + teachers

    for user in users:
        user["_id"] = str(user["_id"])
    return {"users": users}

@router.get("/academics/config")
async def admin_academic_config(current_admin: dict = Depends(get_current_admin)):
    db = get_database()
    return await get_academic_config(db)


@router.post("/academics/departments")
async def admin_create_department(
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await create_department(payload, db)


@router.put("/academics/departments/{department_id}")
async def admin_update_department(
    department_id: str,
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await update_department(department_id, payload, db)


@router.delete("/academics/departments/{department_id}")
async def admin_delete_department(
    department_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await delete_department(department_id, db)


@router.get("/academics/subjects")
async def admin_list_subjects(current_admin: dict = Depends(get_current_admin)):
    db = get_database()
    return {"subjects": await list_subjects(db)}


@router.post("/academics/subjects")
async def admin_create_subject(
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await create_subject(payload, db)


@router.put("/academics/subjects/{subject_id}")
async def admin_update_subject(
    subject_id: str,
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await update_subject(subject_id, payload, db)


@router.delete("/academics/subjects/{subject_id}")
async def admin_delete_subject(
    subject_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await delete_subject(subject_id, db)


@router.get("/academics/timetables")
async def admin_list_timetables(current_admin: dict = Depends(get_current_admin)):
    db = get_database()
    return {"timetables": await list_timetables(db)}


@router.post("/academics/timetables")
async def admin_create_timetable(
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await create_timetable(payload, db)


@router.put("/academics/timetables/{timetable_id}")
async def admin_update_timetable(
    timetable_id: str,
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await update_timetable(timetable_id, payload, db)


@router.delete("/academics/timetables/{timetable_id}")
async def admin_delete_timetable(
    timetable_id: str,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await delete_timetable(timetable_id, db)


@router.put("/academics/sections")
async def admin_update_sections(
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await update_sections(payload, db)


@router.get("/attendance")
async def admin_attendance_summary(
    status: str | None = None,
    search: str | None = None,
    department: str | None = None,
    date: str | None = None,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await get_admin_attendance_summary(db, status=status, search=search, department=department, date=date)


@router.get("/leaves")
async def admin_leaves(
    status: str | None = None,
    search: str | None = None,
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return {"requests": await list_admin_leaves(db, status=status, search=search)}


@router.put("/leaves/{leave_id}")
async def admin_override_leave(
    leave_id: str,
    payload: dict = Body(...),
    current_admin: dict = Depends(get_current_admin),
):
    db = get_database()
    return await override_leave_decision(leave_id, payload, str(current_admin["_id"]), db)


@router.get("/reports")
async def admin_reports(current_admin: dict = Depends(get_current_admin)):
    db = get_database()
    return await get_admin_reports(db)


@router.post("/users/teachers")
async def admin_create_teacher(payload: dict = Body(...), current_admin: dict = Depends(get_current_admin)):
    db = get_database()
    return await create_teacher(payload, db)