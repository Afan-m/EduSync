async function loadAdminUsers() {
    const list = document.getElementById('admin-users-list');
    if (!list) return;

    list.innerHTML = '<div class="col-12"><div class="empty-state"><div class="empty-icon">⏳</div><div class="empty-msg">Loading users...</div></div></div>';

    const role = document.getElementById('admin-user-role')?.value || '';
    const search = document.getElementById('admin-user-search')?.value || '';
    const dept = document.getElementById('admin-user-dept')?.value || '';

    try {
        const response = await fetch(`${API_BASE_URL}/admin/users?role=${encodeURIComponent(role)}&search=${encodeURIComponent(search)}&department=${encodeURIComponent(dept)}`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load users');
        const data = await response.json();
        renderAdminUsers(data.users || []);
    } catch (err) {
        console.error(err);
        list.innerHTML = '<div class="col-12"><div class="empty-state"><div class="empty-icon">⚠️</div><div class="empty-msg">Unable to load users.</div></div></div>';
    }
}

function renderAdminUsers(users) {
    const list = document.getElementById('admin-users-list');
    if (!list) return;

    if (!users.length) {
        list.innerHTML = '<div class="col-12"><div class="empty-state"><div class="empty-icon">👥</div><div class="empty-msg">No users found.</div></div></div>';
        return;
    }

    list.innerHTML = users.map(user => `
        <div class="col-12 col-lg-6">
            <div class="card shadow-sm h-100">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <h6 class="mb-1">${user.full_name || 'Unnamed'}</h6>
                            <div class="text-muted small">${user.role === 'teacher' ? 'Teacher' : 'Student'}</div>
                        </div>
                        <span class="badge bg-light text-dark">${user.role || 'user'}</span>
                    </div>
                    <div class="mt-3 small">
                        <div><strong>Email:</strong> ${user.email || '—'}</div>
                        <div><strong>Department:</strong> ${user.department || '—'}</div>
                        <div><strong>${user.role === 'teacher' ? 'Employee ID' : 'USN'}:</strong> ${user.role === 'teacher' ? (user.employee_id || '—') : (user.usn || '—')}</div>
                        <div><strong>Status:</strong> ${user.is_active === false ? 'Inactive' : 'Active'}</div>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

window.loadAdminUsers = loadAdminUsers;

function showCreateTeacherModal() {
    const modal = document.getElementById('createTeacherModal');
    if (!modal) return;
    modal.style.display = 'block';
}

function hideCreateTeacherModal() {
    const modal = document.getElementById('createTeacherModal');
    if (!modal) return;
    modal.style.display = 'none';
    const alert = document.getElementById('ct-alert');
    if (alert) { alert.style.display = 'none'; alert.className = 'alert'; alert.textContent = ''; }
}

async function submitCreateTeacher() {
    const full_name = document.getElementById('ct-full_name')?.value || '';
    const email = document.getElementById('ct-email')?.value || '';
    const password = document.getElementById('ct-password')?.value || '';
    const department = document.getElementById('ct-department')?.value || '';
    const designation = document.getElementById('ct-designation')?.value || '';
    const phone = document.getElementById('ct-phone')?.value || '';
    const alert = document.getElementById('ct-alert');

    if (!full_name || !email || !password) {
        if (alert) { alert.style.display = 'block'; alert.className = 'alert alert-danger'; alert.textContent = 'Full name, email and password are required.'; }
        return;
    }

    try {
        const resp = await fetch(`${API_BASE_URL}/admin/users/teachers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('access_token')}` },
            body: JSON.stringify({ full_name, email, password, department, designation, phone })
        });
        const data = await resp.json();
        if (!resp.ok) {
            if (alert) { alert.style.display = 'block'; alert.className = 'alert alert-danger'; alert.textContent = data.detail || data.message || 'Failed to create teacher.'; }
            return;
        }
        if (alert) { alert.style.display = 'block'; alert.className = 'alert alert-success'; alert.textContent = 'Teacher created successfully.'; }
        // Refresh list
        await loadAdminUsers();
        setTimeout(() => hideCreateTeacherModal(), 800);
    } catch (err) {
        console.error(err);
        if (alert) { alert.style.display = 'block'; alert.className = 'alert alert-danger'; alert.textContent = 'Network error.'; }
    }
}
