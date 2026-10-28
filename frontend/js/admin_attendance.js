async function loadAdminAttendance() {
    const container = document.getElementById('main-content');
    if (!container) return;

    container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center" style="min-height:300px">
            <div class="spinner-border text-secondary" role="status"></div>
        </div>
    `;

    try {
        const response = await fetch(`../views/admin_attendance.html`);
        if (!response.ok) throw new Error('View not found');
        const html = await response.text();
        container.innerHTML = html;
        await fetchAdminAttendance();
    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load attendance administration.</div></div>`;
    }
}

async function fetchAdminAttendance() {
    const list = document.getElementById('admin-attendance-list');
    if (!list) return;

    list.innerHTML = '<div class="text-center py-5">Loading sessions...</div>';

    const status = document.getElementById('admin-attendance-status')?.value || '';
    const search = document.getElementById('admin-attendance-search')?.value || '';
    const department = document.getElementById('admin-attendance-department')?.value || '';
    const date = document.getElementById('admin-attendance-date')?.value || '';

    try {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        if (search) params.append('search', search);
        if (department) params.append('department', department);
        if (date) params.append('date', date);

        const response = await fetch(`${API_BASE_URL}/admin/attendance?${params.toString()}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load attendance sessions');
        const data = await response.json();

        const sessions = data.sessions || [];
        list.innerHTML = sessions.length ? sessions.map(session => `
            <div class="card shadow-sm p-3 mb-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6>${session.subject || 'Untitled Class'}</h6>
                        <div class="small text-muted">${session.department || 'Dept'} · ${session.section || 'Section'} · ${session.semester || 'Sem'}</div>
                    </div>
                    <span class="badge bg-${session.status === 'active' ? 'success' : session.status === 'paused' ? 'warning' : 'secondary'}">${session.status}</span>
                </div>
                <div class="mt-2 small text-muted">Present: ${session.present_count ?? 0} · Absent: ${session.absent_count ?? 0}</div>
            </div>
        `).join('') : '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-msg">No attendance sessions found.</div></div>';
    } catch (err) {
        console.error(err);
        list.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load attendance sessions.</div></div>';
    }
}

window.loadAdminAttendance = loadAdminAttendance;
