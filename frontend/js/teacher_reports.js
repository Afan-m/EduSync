async function loadTeacherReports() {
    const container = document.getElementById('teacher-reports-content');
    if (!container) return;

    container.innerHTML = '<div class="col-12"><div class="empty-state"><div class="empty-icon">⏳</div><div class="empty-msg">Loading reports...</div></div></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/teacher/reports`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load reports');
        const data = await response.json();
        renderTeacherReports(data);
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="col-12"><div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load reports.</div></div></div>';
    }
}

function renderTeacherReports(data) {
    const container = document.getElementById('teacher-reports-content');
    if (!container) return;

    const attendance = data.attendance_summary || {};
    const leave = data.leave_summary || {};
    const studentStats = data.student_statistics || {};
    const subjectStats = data.subject_statistics || [];

    container.innerHTML = `
        <div class="col-12 col-md-6 col-xl-3">
            <div class="card h-100 shadow-sm">
                <div class="card-body">
                    <h6 class="text-muted">Attendance Summary</h6>
                    <div class="mt-3"><strong>Total Sessions:</strong> ${attendance.total_sessions ?? 0}</div>
                    <div><strong>Average Attendance %:</strong> ${attendance.average_attendance_percentage ?? 0}%</div>
                    <div><strong>Present:</strong> ${attendance.present_count ?? 0}</div>
                    <div><strong>Absent:</strong> ${attendance.absent_count ?? 0}</div>
                </div>
            </div>
        </div>
        <div class="col-12 col-md-6 col-xl-3">
            <div class="card h-100 shadow-sm">
                <div class="card-body">
                    <h6 class="text-muted">Leave Summary</h6>
                    <div class="mt-3"><strong>Pending:</strong> ${leave.pending ?? 0}</div>
                    <div><strong>Approved:</strong> ${leave.approved ?? 0}</div>
                    <div><strong>Rejected:</strong> ${leave.rejected ?? 0}</div>
                </div>
            </div>
        </div>
        <div class="col-12 col-xl-6">
            <div class="card h-100 shadow-sm">
                <div class="card-body">
                    <h6 class="text-muted">Student Statistics</h6>
                    <div class="row mt-3">
                        <div class="col-md-6">
                            <h6>Department-wise</h6>
                            <ul class="mb-0 ps-3">
                                ${(studentStats.department_wise || []).map(item => `<li>${item.department}: ${item.count}</li>`).join('') || '<li>No data</li>'}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h6>Semester-wise</h6>
                            <ul class="mb-0 ps-3">
                                ${(studentStats.semester_wise || []).map(item => `<li>Sem ${item.semester}: ${item.count}</li>`).join('') || '<li>No data</li>'}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-12">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h6 class="text-muted">Subject Statistics</h6>
                    <div class="table-responsive mt-3">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Subject</th><th>Code</th><th>Sessions</th><th>Attendance %</th></tr>
                            </thead>
                            <tbody>
                                ${subjectStats.map(subject => `
                                    <tr>
                                        <td>${subject.subject_name || '—'}</td>
                                        <td>${subject.subject_code || '—'}</td>
                                        <td>${subject.sessions_conducted ?? 0}</td>
                                        <td>${subject.attendance_percentage ?? 0}%</td>
                                    </tr>
                                `).join('') || '<tr><td colspan="4" class="text-muted">No subject data.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    `;
}

window.loadTeacherReports = loadTeacherReports;
