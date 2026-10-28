async function loadAdminLeaves() {
    const container = document.getElementById('main-content');
    if (!container) return;

    container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center" style="min-height:300px">
            <div class="spinner-border text-secondary" role="status"></div>
        </div>
    `;

    try {
        const response = await fetch(`../views/admin_leaves.html`);
        if (!response.ok) throw new Error('View not found');
        const html = await response.text();
        container.innerHTML = html;
        await fetchAdminLeaves();
    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load leave review.</div></div>`;
    }
}

async function fetchAdminLeaves() {
    const list = document.getElementById('admin-leaves-list');
    if (!list) return;

    list.innerHTML = '<div class="text-center py-5">Loading leave requests...</div>';

    const status = document.getElementById('admin-leave-status')?.value || '';
    const search = document.getElementById('admin-leave-search')?.value || '';

    try {
        const params = new URLSearchParams();
        if (status) params.append('status', status);
        if (search) params.append('search', search);

        const response = await fetch(`${API_BASE_URL}/admin/leaves?${params.toString()}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load leave requests');
        const data = await response.json();

        const requests = data.requests || [];
        list.innerHTML = requests.length ? requests.map(request => `
            <div class="card shadow-sm p-3 mb-3">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6>${request.student_name || 'Unknown Student'}</h6>
                        <div class="small text-muted">${request.leave_type_name || 'Leave'} · ${request.status}</div>
                    </div>
                    <button class="btn btn-sm btn-outline-primary" onclick="openAdminLeaveDecision('${request.leave_id}')">Review</button>
                </div>
                <div class="mt-2 small text-muted">${request.from_date} to ${request.to_date} · ${request.total_days} days</div>
            </div>
        `).join('') : '<div class="empty-state"><div class="empty-icon">📭</div><div class="empty-msg">No leave requests found.</div></div>';
    } catch (err) {
        console.error(err);
        list.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load leave requests.</div></div>';
    }
}

function openAdminLeaveDecision(leaveId) {
    const modal = document.createElement('div');
    modal.className = 'admin-leave-modal';
    modal.innerHTML = `
        <div class="modal-backdrop"></div>
        <div class="modal-dialog">
            <div class="modal-content p-4">
                <h5>Leave Decision</h5>
                <p class="text-muted">Provide decision and optional remarks.</p>
                <div class="mb-3">
                    <label class="form-label">Remarks</label>
                    <textarea id="admin-leave-remarks" class="form-control" rows="3"></textarea>
                </div>
                <div class="d-flex gap-2 justify-content-end">
                    <button class="btn btn-outline-secondary" onclick="closeAdminLeaveModal()">Cancel</button>
                    <button class="btn btn-danger" onclick="submitAdminLeaveDecision('${leaveId}', 'Rejected')">Reject</button>
                    <button class="btn btn-success" onclick="submitAdminLeaveDecision('${leaveId}', 'Approved')">Approve</button>
                </div>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function closeAdminLeaveModal() {
    const modal = document.querySelector('.admin-leave-modal');
    if (modal) modal.remove();
}

async function submitAdminLeaveDecision(leaveId, status) {
    const remarks = document.getElementById('admin-leave-remarks')?.value || '';

    try {
        const response = await fetch(`${API_BASE_URL}/admin/leaves/${leaveId}`, {
            method: 'PUT',
            headers: {
                Authorization: `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status, remarks }),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Unable to update leave status');
        alert(data.message || 'Leave updated successfully');
        closeAdminLeaveModal();
        await fetchAdminLeaves();
    } catch (err) {
        console.error(err);
        alert(err.message || 'Error updating leave.');
    }
}

window.loadAdminLeaves = loadAdminLeaves;
