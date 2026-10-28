async function loadTeacherStudentManagement(force = false) {
    const container = document.getElementById('teacher-student-list');
    if (!container) return;

    container.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><div class="empty-msg">Loading students...</div></div>';

    const params = new URLSearchParams();
    const search = document.getElementById('teacher-student-search')?.value?.trim() || '';
    const department = document.getElementById('teacher-student-department')?.value || '';
    const semester = document.getElementById('teacher-student-semester')?.value || '';
    const section = document.getElementById('teacher-student-section')?.value || '';

    if (search) params.set('search', search);
    if (department) params.set('department', department);
    if (semester) params.set('semester', semester);
    if (section) params.set('section', section);

    try {
        const response = await fetch(`${API_BASE_URL}/teacher/students?${params.toString()}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load students');
        const data = await response.json();
        renderTeacherStudentList(data.students || []);
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load students right now.</div></div>';
    }
}

function renderTeacherStudentList(students) {
    const container = document.getElementById('teacher-student-list');
    if (!container) return;

    if (!students.length) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">🎓</div><div class="empty-msg">No students found for the selected filters.</div></div>';
        return;
    }

    container.innerHTML = `
        <div class="row g-3">
            ${students.map(student => `
                <div class="col-12 col-lg-6">
                    <div class="card h-100 shadow-sm">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start gap-3">
                                <div>
                                    <h5 class="mb-1">${student.full_name || 'Unknown Student'}</h5>
                                    <div class="text-muted small">${student.usn || '—'}</div>
                                </div>
                                <span class="badge bg-primary">${student.department || '—'}</span>
                            </div>
                            <div class="row mt-3 small text-muted">
                                <div class="col-6"><strong>Department:</strong> ${student.department || '—'}</div>
                                <div class="col-6"><strong>Semester:</strong> ${student.semester || '—'}</div>
                                <div class="col-6"><strong>Section:</strong> ${student.section || '—'}</div>
                                <div class="col-6"><strong>Attendance:</strong> ${student.attendance_percentage != null ? `${student.attendance_percentage}%` : '—'}</div>
                            </div>
                            <div class="mt-3">
                                <button class="btn btn-outline-primary btn-sm" onclick="openTeacherStudentProfile('${student._id}')">View Profile</button>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

async function openTeacherStudentProfile(studentId) {
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/students/${studentId}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load student profile');
        const data = await response.json();
        const body = document.getElementById('teacher-student-profile-body');
        if (!body) return;

        body.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6"><strong>Name:</strong> ${data.full_name || '—'}</div>
                <div class="col-md-6"><strong>USN:</strong> ${data.usn || '—'}</div>
                <div class="col-md-6"><strong>Email:</strong> ${data.email || '—'}</div>
                <div class="col-md-6"><strong>Phone:</strong> ${data.phone || '—'}</div>
                <div class="col-md-6"><strong>Department:</strong> ${data.department || '—'}</div>
                <div class="col-md-6"><strong>Semester:</strong> ${data.semester || '—'}</div>
                <div class="col-md-6"><strong>Section:</strong> ${data.section || '—'}</div>
                <div class="col-md-6"><strong>Attendance:</strong> ${data.attendance_percentage != null ? `${data.attendance_percentage}%` : '—'}</div>
                <div class="col-12"><strong>Gender:</strong> ${data.gender || '—'}</div>
            </div>
        `;

        const modal = new bootstrap.Modal(document.getElementById('teacherStudentProfileModal'));
        modal.show();
    } catch (err) {
        console.error(err);
        alert('Unable to load this student profile.');
    }
}

async function initTeacherStudentManagement() {
    await loadTeacherStudentManagement();
    await populateTeacherStudentFilters();
}

async function populateTeacherStudentFilters() {
    const departmentSelect = document.getElementById('teacher-student-department');
    if (!departmentSelect) return;

    try {
        const response = await fetch(`${API_BASE_URL}/teacher/students?limit=1`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) return;
        const data = await response.json();
        const departments = [...new Set((data.students || []).map(student => student.department).filter(Boolean))].sort();
        departmentSelect.innerHTML = '<option value="">All</option>' + departments.map(dept => `<option value="${dept}">${dept}</option>`).join('');
    } catch (err) {
        console.error(err);
    }
}

window.loadTeacherStudentManagement = loadTeacherStudentManagement;
window.openTeacherStudentProfile = openTeacherStudentProfile;
window.initTeacherStudentManagement = initTeacherStudentManagement;
