async function loadAdminReports() {
    const container = document.getElementById('main-content');
    if (!container) return;

    container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center" style="min-height:300px">
            <div class="spinner-border text-secondary" role="status"></div>
        </div>
    `;

    try {
        const response = await fetch(`../views/admin_reports.html`);
        if (!response.ok) throw new Error('View not found');
        const html = await response.text();
        container.innerHTML = html;
        await fetchAdminReports();
    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load admin reports.</div></div>`;
    }
}

async function fetchAdminReports() {
    const container = document.getElementById('admin-reports-content');
    if (!container) return;

    container.innerHTML = '<div class="text-center py-5">Loading reports...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/admin/reports`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load admin reports');
        const data = await response.json();

        const attendance = data.attendance_summary || {};
        const leaveSummary = data.leave_summary || {};
        const departmentSummary = data.department_summary || [];
        const subjectSummary = data.subject_summary || [];

        container.innerHTML = `
            <div class="col-12 col-md-6 col-xl-3">
                <div class="card h-100 shadow-sm p-3">
                    <h6 class="text-muted">Students</h6>
                    <h2>${data.total_students ?? 0}</h2>
                </div>
            </div>
            <div class="col-12 col-md-6 col-xl-3">
                <div class="card h-100 shadow-sm p-3">
                    <h6 class="text-muted">Teachers</h6>
                    <h2>${data.total_teachers ?? 0}</h2>
                </div>
            </div>
            <div class="col-12 col-md-6 col-xl-3">
                <div class="card h-100 shadow-sm p-3">
                    <h6 class="text-muted">Attendance Records</h6>
                    <div>Total: ${attendance.total_records ?? 0}</div>
                    <div>Present: ${attendance.present ?? 0}</div>
                    <div>Absent: ${attendance.absent ?? 0}</div>
                </div>
            </div>
            <div class="col-12 col-md-6 col-xl-3">
                <div class="card h-100 shadow-sm p-3">
                    <h6 class="text-muted">Leave Summary</h6>
                    <div>Pending: ${leaveSummary.pending ?? 0}</div>
                    <div>Approved: ${leaveSummary.approved ?? 0}</div>
                    <div>Rejected: ${leaveSummary.rejected ?? 0}</div>
                </div>
            </div>
            <div class="col-12 col-lg-6">
                <div class="card shadow-sm p-3">
                    <h6 class="text-muted">Department Summary</h6>
                    <div class="table-responsive mt-3">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Department</th><th>Students</th><th>Subjects</th></tr>
                            </thead>
                            <tbody>
                                ${departmentSummary.map(item => `
                                    <tr>
                                        <td>${item.department || '—'}</td>
                                        <td>${item.students ?? 0}</td>
                                        <td>${item.subjects ?? 0}</td>
                                    </tr>
                                `).join('') || '<tr><td colspan="3" class="text-muted">No department data.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="col-12 col-lg-6">
                <div class="card shadow-sm p-3">
                    <h6 class="text-muted">Subjects</h6>
                    <div class="table-responsive mt-3">
                        <table class="table table-sm">
                            <thead>
                                <tr><th>Subject</th><th>Code</th><th>Dept</th><th>Sem</th></tr>
                            </thead>
                            <tbody>
                                ${subjectSummary.map(item => `
                                    <tr>
                                        <td>${item.subject_name || '—'}</td>
                                        <td>${item.subject_code || '—'}</td>
                                        <td>${item.department || '—'}</td>
                                        <td>${item.semester ?? '—'}</td>
                                    </tr>
                                `).join('') || '<tr><td colspan="4" class="text-muted">No subject data.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        console.error(err);
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load reports.</div></div>';
    }
}

window.loadAdminReports = loadAdminReports;
