async function loadTeacherAttendanceHistory() {
    const container = document.getElementById('teacher-attendance-history-list');
    if (!container) return;

    container.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><div class="empty-msg">Loading attendance sessions...</div></div>';

    const params = new URLSearchParams();
    const subject = document.getElementById('teacher-attendance-subject')?.value?.trim() || '';
    const department = document.getElementById('teacher-attendance-department')?.value?.trim() || '';
    const semester = document.getElementById('teacher-attendance-semester')?.value || '';
    const section = document.getElementById('teacher-attendance-section')?.value?.trim() || '';
    const date = document.getElementById('teacher-attendance-date')?.value || '';

    if (subject) params.set('subject', subject);
    if (department) params.set('department', department);
    if (semester) params.set('semester', semester);
    if (section) params.set('section', section);
    if (date) params.set('date', date);

    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/sessions?${params.toString()}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load sessions');
        const data = await response.json();
        renderTeacherAttendanceSessions(data.sessions || []);
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load attendance history.</div></div>';
    }
}

function renderTeacherAttendanceSessions(sessions) {
    const container = document.getElementById('teacher-attendance-history-list');
    if (!container) return;

    if (!sessions.length) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">📅</div><div class="empty-msg">No attendance sessions found.</div></div>';
        return;
    }

    container.innerHTML = `
        <div class="table-responsive">
            <table class="table table-hover align-middle">
                <thead>
                    <tr>
                        <th>Session ID</th>
                        <th>Subject</th>
                        <th>Dept</th>
                        <th>Sem</th>
                        <th>Section</th>
                        <th>Status</th>
                        <th>Present</th>
                        <th>Absent</th>
                        <th>Start</th>
                        <th>End</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    ${sessions.map(session => `
                        <tr>
                            <td>${session.session_id || '—'}</td>
                            <td>${session.subject || '—'}</td>
                            <td>${session.department || '—'}</td>
                            <td>${session.semester || '—'}</td>
                            <td>${session.section || '—'}</td>
                            <td><span class="badge bg-secondary">${session.status || '—'}</span></td>
                            <td>${session.present_count ?? 0}</td>
                            <td>${session.absent_count ?? 0}</td>
                            <td>${session.start_time ? new Date(session.start_time).toLocaleString() : '—'}</td>
                            <td>${session.expiry_time ? new Date(session.expiry_time).toLocaleString() : '—'}</td>
                            <td><button class="btn btn-outline-primary btn-sm" onclick="openTeacherAttendanceDetail('${session.session_id}')">View</button></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

async function openTeacherAttendanceDetail(sessionId) {
    try {
        const response = await fetch(`${API_BASE_URL}/teacher/attendance/sessions/${sessionId}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load attendance details');
        const data = await response.json();
        const body = document.getElementById('teacher-attendance-detail-body');
        if (!body) return;

        body.innerHTML = `
            <div class="mb-3">
                <strong>Session:</strong> ${data.session?.session_id || '—'}<br>
                <strong>Subject:</strong> ${data.session?.subject || '—'}<br>
                <strong>Department:</strong> ${data.session?.department || '—'} · <strong>Semester:</strong> ${data.session?.semester || '—'} · <strong>Section:</strong> ${data.session?.section || '—'}
            </div>
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr><th>Student</th><th>USN</th><th>Status</th><th>Time</th></tr>
                    </thead>
                    <tbody>
                        ${data.records?.map(record => `
                            <tr>
                                <td>${record.student_name || 'Unknown'}</td>
                                <td>${record.student_usn || 'N/A'}</td>
                                <td>${record.attendance_status || '—'}</td>
                                <td>${record.timestamp ? new Date(record.timestamp).toLocaleString() : '—'}</td>
                            </tr>
                        `).join('') || '<tr><td colspan="4" class="text-muted">No attendance records.</td></tr>'}
                    </tbody>
                </table>
            </div>
        `;

        const modal = new bootstrap.Modal(document.getElementById('teacherAttendanceDetailModal'));
        modal.show();
    } catch (err) {
        console.error(err);
        alert('Unable to load session details.');
    }
}

window.loadTeacherAttendanceHistory = loadTeacherAttendanceHistory;
window.openTeacherAttendanceDetail = openTeacherAttendanceDetail;
