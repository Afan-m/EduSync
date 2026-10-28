async function loadAdminAcademics() {
    const container = document.getElementById('main-content');
    if (!container) return;

    container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center" style="min-height:300px">
            <div class="spinner-border text-secondary" role="status"></div>
        </div>
    `;

    try {
        const response = await fetch(`../views/admin_academics.html`);
        if (!response.ok) throw new Error('View not found');
        const html = await response.text();
        container.innerHTML = html;
        await fetchAcademicConfig();
    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load academic administration.</div></div>`;
    }
}

async function fetchAcademicConfig() {
    const listDepartments = document.getElementById('admin-departments-list');
    const listSubjects = document.getElementById('admin-subjects-list');
    const listSections = document.getElementById('admin-sections-list');
    const listTimetables = document.getElementById('admin-timetables-list');

    if (listDepartments) listDepartments.innerHTML = 'Loading departments...';
    if (listSubjects) listSubjects.innerHTML = 'Loading subjects...';
    if (listSections) listSections.innerHTML = 'Loading sections...';
    if (listTimetables) listTimetables.innerHTML = 'Loading timetables...';

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/config`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load academic config');
        const data = await response.json();

        const departments = data.departments || [];
        const sections = data.sections || [];

        if (listDepartments) {
            listDepartments.innerHTML = departments.length ? departments.map(dept => `
                <div class="mb-2 p-2 border rounded">
                    <div class="d-flex justify-content-between align-items-center">
                        <div><strong>${dept.name}</strong> (${dept.code})</div>
                        <div>${dept.active ? 'Active' : 'Inactive'}</div>
                    </div>
                    <div class="small text-muted">Semesters: ${dept.total_semesters}</div>
                </div>
            `).join('') : '<div class="text-muted">No departments configured.</div>';
        }

        if (listSections) {
            listSections.innerHTML = sections.length ? sections.map(section => `
                <span class="badge bg-secondary me-1 mb-1">${section}</span>
            `).join('') : '<div class="text-muted">No sections configured.</div>';
        }

        await fetchAdminSubjects();
        await fetchAdminTimetables();
    } catch (err) {
        console.error(err);
        if (listDepartments) listDepartments.innerHTML = '<div class="text-danger">Unable to load departments.</div>';
        if (listSubjects) listSubjects.innerHTML = '<div class="text-danger">Unable to load subjects.</div>';
        if (listSections) listSections.innerHTML = '<div class="text-danger">Unable to load sections.</div>';
        if (listTimetables) listTimetables.innerHTML = '<div class="text-danger">Unable to load timetables.</div>';
    }
}

async function fetchAdminSubjects() {
    const listSubjects = document.getElementById('admin-subjects-list');
    if (!listSubjects) return;

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/subjects`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load subjects');
        const data = await response.json();
        const subjects = data.subjects || [];

        listSubjects.innerHTML = subjects.length ? subjects.map(subject => `
            <div class="mb-2 p-2 border rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div><strong>${subject.subject_name}</strong></div>
                    <div>${subject.is_active ? 'Active' : 'Inactive'}</div>
                </div>
                <div class="small text-muted">${subject.subject_code} · ${subject.department} · Sem ${subject.semester}</div>
            </div>
        `).join('') : '<div class="text-muted">No subjects configured.</div>';
    } catch (err) {
        console.error(err);
        listSubjects.innerHTML = '<div class="text-danger">Unable to load subjects.</div>';
    }
}

async function fetchAdminTimetables() {
    const listTimetables = document.getElementById('admin-timetables-list');
    if (!listTimetables) return;

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/timetables`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load timetables');
        const data = await response.json();
        const timetables = data.timetables || [];

        listTimetables.innerHTML = timetables.length ? timetables.map(tt => `
            <div class="mb-2 p-2 border rounded">
                <div class="d-flex justify-content-between align-items-center">
                    <div><strong>${tt.department} Sem ${tt.semester} ${tt.section}</strong></div>
                    <div>${tt.is_active ? 'Active' : 'Inactive'}</div>
                </div>
                <div class="small text-muted">${tt.day_of_week} · ${tt.periods.length || 0} periods</div>
            </div>
        `).join('') : '<div class="text-muted">No timetables configured.</div>';
    } catch (err) {
        console.error(err);
        listTimetables.innerHTML = '<div class="text-danger">Unable to load timetables.</div>';
    }
}

function showDepartmentForm() {
    const target = document.getElementById('admin-academic-forms');
    if (!target) return;
    target.innerHTML = `
        <div class="card shadow-sm p-4 mb-4">
            <h5>Add Department</h5>
            <div class="row g-3 mt-3">
                <div class="col-md-4"><input id="dept-name" class="form-control" placeholder="Name" /></div>
                <div class="col-md-4"><input id="dept-code" class="form-control" placeholder="Code" /></div>
                <div class="col-md-2"><input id="dept-semesters" type="number" min="1" class="form-control" placeholder="Semesters" /></div>
                <div class="col-md-2 d-grid"><button class="btn btn-primary" onclick="submitDepartment()">Create</button></div>
            </div>
        </div>
    `;
}

async function submitDepartment() {
    const name = document.getElementById('dept-name')?.value.trim();
    const code = document.getElementById('dept-code')?.value.trim();
    const total_semesters = document.getElementById('dept-semesters')?.value;

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/departments`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, code, total_semesters }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to create department');
        alert(data.message || 'Department created successfully');
        await fetchAcademicConfig();
    } catch (err) {
        console.error(err);
        alert(err.message || 'Error creating department.');
    }
}

function showSubjectForm() {
    const target = document.getElementById('admin-academic-forms');
    if (!target) return;
    target.innerHTML = `
        <div class="card shadow-sm p-4 mb-4">
            <h5>Add Subject</h5>
            <div class="row g-3 mt-3">
                <div class="col-md-3"><input id="subject-code" class="form-control" placeholder="Subject Code" /></div>
                <div class="col-md-3"><input id="subject-name" class="form-control" placeholder="Subject Name" /></div>
                <div class="col-md-2"><input id="subject-dept" class="form-control" placeholder="Department" /></div>
                <div class="col-md-1"><input id="subject-sem" type="number" min="1" class="form-control" placeholder="Sem" /></div>
                <div class="col-md-1"><input id="subject-credits" type="number" min="1" class="form-control" placeholder="Credits" /></div>
                <div class="col-md-2 d-grid"><button class="btn btn-primary" onclick="submitSubject()">Create</button></div>
            </div>
        </div>
    `;
}

async function submitSubject() {
    const subject_code = document.getElementById('subject-code')?.value.trim();
    const subject_name = document.getElementById('subject-name')?.value.trim();
    const department = document.getElementById('subject-dept')?.value.trim();
    const semester = document.getElementById('subject-sem')?.value;
    const credits = document.getElementById('subject-credits')?.value;

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/subjects`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ subject_code, subject_name, department, semester, credits, faculty_id: '' }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to create subject');
        alert(data.message || 'Subject created successfully');
        await fetchAcademicConfig();
    } catch (err) {
        console.error(err);
        alert(err.message || 'Error creating subject.');
    }
}

function showSectionsForm() {
    const target = document.getElementById('admin-academic-forms');
    if (!target) return;
    target.innerHTML = `
        <div class="card shadow-sm p-4 mb-4">
            <h5>Edit Sections</h5>
            <div class="row g-3 mt-3">
                <div class="col-12"><input id="section-list" class="form-control" placeholder="Comma-separated sections, e.g. A,B,C" /></div>
                <div class="col-md-2 d-grid"><button class="btn btn-primary" onclick="submitSections()">Save Sections</button></div>
            </div>
        </div>
    `;
}

async function submitSections() {
    const raw = document.getElementById('section-list')?.value;
    const sections = raw ? raw.split(',').map(item => item.trim()).filter(Boolean) : [];

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/sections`, {
            method: 'PUT',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ sections }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to update sections');
        alert(data.message || 'Sections updated successfully');
        await fetchAcademicConfig();
    } catch (err) {
        console.error(err);
        alert(err.message || 'Error updating sections.');
    }
}

function showTimetableForm() {
    const target = document.getElementById('admin-academic-forms');
    if (!target) return;
    target.innerHTML = `
        <div class="card shadow-sm p-4 mb-4">
            <h5>Add Timetable</h5>
            <div class="row g-3 mt-3">
                <div class="col-md-3"><input id="timetable-dept" class="form-control" placeholder="Department" /></div>
                <div class="col-md-1"><input id="timetable-sem" type="number" min="1" class="form-control" placeholder="Sem" /></div>
                <div class="col-md-1"><input id="timetable-section" class="form-control" placeholder="Section" /></div>
                <div class="col-md-2"><input id="timetable-day" class="form-control" placeholder="Day" /></div>
                <div class="col-md-2"><input id="timetable-periods" class="form-control" placeholder="Periods JSON" /></div>
                <div class="col-md-3 d-grid"><button class="btn btn-primary" onclick="submitTimetable()">Create</button></div>
            </div>
            <div class="form-text mt-2">Use JSON for periods: [{"period_no":1,"start_time":"09:00","end_time":"10:00","subject_id":"...","faculty_id":"...","room":"R101"}]</div>
        </div>
    `;
}

async function submitTimetable() {
    const department = document.getElementById('timetable-dept')?.value.trim();
    const semester = document.getElementById('timetable-sem')?.value;
    const section = document.getElementById('timetable-section')?.value.trim();
    const day_of_week = document.getElementById('timetable-day')?.value.trim();
    const periodsRaw = document.getElementById('timetable-periods')?.value;

    let periods = [];
    try {
        periods = periodsRaw ? JSON.parse(periodsRaw) : [];
    } catch (err) {
        alert('Periods must be valid JSON.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/admin/academics/timetables`, {
            method: 'POST',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ department, semester, section, day_of_week, periods }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to create timetable');
        alert(data.message || 'Timetable created successfully');
        await fetchAdminTimetables();
    } catch (err) {
        console.error(err);
        alert(err.message || 'Error creating timetable.');
    }
}

window.loadAdminAcademics = loadAdminAcademics;
