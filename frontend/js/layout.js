/**
 * frontend/js/layout.js
 * EduSync — Smart Campus ERP | Shared Dashboard Architecture
 *
 * Responsibilities:
 * - Load sidebar, topbar, footer components
 * - Determine logged-in role
 * - Render role-specific sidebar menus
 * - Handle SPA view routing inside #main-content
 */

const ROLE_MENUS = {
    student: [
        { section: 'Main' },
        { id: 'dashboard', icon: '🏠', label: 'Dashboard' },
        { id: 'profile', icon: '👤', label: 'My Profile' },
        { section: 'Academics' },
        { id: 'face', icon: '📷', label: 'Face Registration' },
        { id: 'attendance', icon: '📅', label: 'Attendance' },
        { id: 'timetable', icon: '🗓', label: 'Timetable' },
        { section: 'Administration' },
        { id: 'leave', icon: '📝', label: 'Leave Requests' },
        { id: 'notifications', icon: '🔔', label: 'Notifications', hasBadge: true },
        { id: 'settings', icon: '⚙', label: 'Settings' }
    ],
    teacher: [
        { section: 'Main' },
        { id: 'dashboard', icon: '🏠', label: 'Dashboard' },
        { id: 'teacher_attendance', icon: '📅', label: 'Attendance Sessions' },
        { id: 'teacher_attendance_history', icon: '🗂️', label: 'Attendance History' },
        { id: 'teacher_timetable', icon: '🗓️', label: 'Timetable' },
        { id: 'teacher_students', icon: '🎓', label: 'Student Management' },
        { id: 'teacher_reports', icon: '📊', label: 'Reports' },
        { section: 'Communication' },
        { id: 'notifications', icon: '🔔', label: 'Notifications', hasBadge: true },
        { id: 'teacher_leave', icon: '📝', label: 'Leave Approval' },
        { section: 'Account' },
        { id: 'profile', icon: '👤', label: 'Profile' },
        { id: 'settings', icon: '⚙', label: 'Settings' }
    ],
    admin: [
        { section: 'Main' },
        { id: 'dashboard', icon: '🏠', label: 'Dashboard' },
        { id: 'admin_users', icon: '👥', label: 'User Management' },
        { id: 'admin_academics', icon: '🏫', label: 'Academics' },
        { id: 'admin_attendance', icon: '📊', label: 'Attendance Admin' },
        { id: 'admin_leaves', icon: '📝', label: 'Leave Review' },
        { id: 'admin_reports', icon: '📈', label: 'Reports' },
        { section: 'Administration' },
        { id: 'notifications', icon: '🔔', label: 'Notifications', hasBadge: true },
        { id: 'settings', icon: '⚙', label: 'Settings' }
    ]
};

// State
let currentRole = null;
let currentUser = null;

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Determine role (try explicit stored objects first)
    if (localStorage.getItem('student')) {
        currentRole = 'student';
        currentUser = JSON.parse(localStorage.getItem('student'));
    } else if (localStorage.getItem('teacher')) {
        currentRole = 'teacher';
        currentUser = JSON.parse(localStorage.getItem('teacher'));
    } else if (localStorage.getItem('admin')) {
        currentRole = 'admin';
        currentUser = JSON.parse(localStorage.getItem('admin'));
    } else {
        // Attempt to infer role from JWT if available (helps when page reloads without stored profile)
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
                const inferredRole = payload && payload.role;
                if (inferredRole === 'teacher') {
                    // Try to fetch fresh teacher profile and store it
                    try {
                        const resp = await fetch(`${API_BASE_URL}/teacher/me`, {
                            headers: { Authorization: `Bearer ${token}` }
                        });
                        if (resp.ok) {
                            const profile = await resp.json();
                            localStorage.setItem('teacher', JSON.stringify(profile));
                            currentRole = 'teacher';
                            currentUser = profile;
                        } else {
                            currentRole = 'teacher';
                            currentUser = { full_name: payload.email || 'Teacher' };
                        }
                    } catch (err) {
                        currentRole = 'teacher';
                        currentUser = { full_name: payload.email || 'Teacher' };
                    }
                } else if (inferredRole) {
                    currentRole = inferredRole;
                    currentUser = { full_name: payload.email || 'User' };
                } else {
                    // Not logged in
                    window.location.href = 'signin.html';
                    return;
                }
            } catch (e) {
                console.error('Failed to decode access token', e);
                window.location.href = 'signin.html';
                return;
            }
        } else {
            // Not logged in
            window.location.href = 'signin.html';
            return;
        }
    }

    // 2. Load Components
    await loadComponent('sidebar-container', '../components/layout/sidebar.html');
    await loadComponent('topbar-container', '../components/layout/topbar.html');
    await loadComponent('footer-container', '../components/layout/footer.html');

    // 3. Render Menus & Init layout
    renderSidebarMenu();
    updateUserStrip();

    // 4. Set current year in footer
    const yearEl = document.getElementById('current-year');
    if (yearEl) yearEl.textContent = new Date().getFullYear();

    // 5. Load default dashboard view based on role
    if (currentRole === 'student') {
        await loadView('student_dashboard');
    } else if (currentRole === 'teacher') {
        await loadView('teacher_dashboard');
    } else if (currentRole === 'admin') {
        await loadView('admin_dashboard');
    }

    if (typeof refreshNotificationBadge === 'function') {
        await refreshNotificationBadge();
    }
});

/** Loads an HTML component into a container */
async function loadComponent(containerId, url) {
    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const html = await response.text();
        document.getElementById(containerId).innerHTML = html;
    } catch (error) {
        console.error(`Failed to load component ${url}:`, error);
    }
}

/** Renders the sidebar menu based on the user's role */
function renderSidebarMenu() {
    const nav = document.getElementById('sidebar-nav');
    if (!nav) return;

    const menuItems = ROLE_MENUS[currentRole] || [];
    let html = '';

    menuItems.forEach(item => {
        if (item.section) {
            html += `<div class="nav-section-label">${item.section}</div>`;
        } else {
            const badge = item.hasBadge ? `<span class="nav-badge" id="notif-count" style="display:none">0</span>` : '';
            html += `
                <div class="nav-item" data-page="${item.id}" onclick="loadView('${item.id}')" id="nav-${item.id}">
                    <span class="nav-icon">${item.icon}</span>
                    <span class="nav-label">${item.label}</span>
                    ${badge}
                </div>
            `;
        }
    });

    nav.innerHTML = html;
}

/** Populates the sidebar user strip and topbar profile with the current user's info */
function updateUserStrip() {
    const nameStr = currentUser.full_name || currentUser.name || 'User';
    const initial = nameStr.charAt(0).toUpperCase();

    // Sidebar
    const sideName = document.getElementById('sidebar-name');
    const sideInitial = document.getElementById('sidebar-avatar-initial');
    const sideRole = document.getElementById('sidebar-role');
    
    if (sideName) sideName.textContent = nameStr;
    if (sideInitial) sideInitial.textContent = initial;
    if (sideRole) sideRole.textContent = currentRole.toUpperCase();

    // Topbar
    const topName = document.getElementById('topbar-name');
    const topInitial = document.getElementById('topbar-avatar-initial');
    if (topName) topName.textContent = nameStr;
    if (topInitial) topInitial.textContent = initial;
}

/** Handles view routing */
window.loadView = async function(viewId) {
    const container = document.getElementById('main-content');
    if (!container) return;

    // Map dashboard route to the current role's specific dashboard view
    if (viewId === 'dashboard') {
        viewId = `${currentRole}_dashboard`;
    }

    const activeNavId = ['student_dashboard', 'teacher_dashboard', 'admin_dashboard'].includes(viewId) ? 'dashboard' : viewId;

    // Show loading skeleton
    container.innerHTML = `
        <div class="d-flex align-items-center justify-content-center" style="min-height:300px">
            <div class="spinner-border text-secondary" role="status"></div>
        </div>
    `;

    // Highlight sidebar nav item
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    const activeItem = document.getElementById(`nav-${activeNavId}`);
    if (activeItem) {
        activeItem.classList.add('active');
        const label = activeItem.querySelector('.nav-label');
        const topbarTitle = document.getElementById('topbar-title');
        if (label && topbarTitle) {
            topbarTitle.textContent = label.textContent.trim();
        }
    }

    // Close mobile sidebar
    const sidebar = document.getElementById('sidebar-container').firstElementChild;
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar && overlay) {
        sidebar.classList.remove('open');
        overlay.classList.remove('visible');
    }

    try {
        // Fetch view HTML
        const response = await fetch(`../views/${viewId}.html`);
        if (response.ok) {
            const html = await response.text();
            container.innerHTML = html;
            
            // Execute view-specific logic based on role & view
            executeViewLogic(viewId);
        } else {
            // View doesn't exist yet, show coming soon
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">🚧</div>
                    <div class="empty-msg">This feature is currently under development.</div>
                </div>
            `;
        }
    } catch (error) {
        console.error(`Error loading view ${viewId}:`, error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">❌</div>
                <div class="empty-msg">Failed to load content. Please try again.</div>
            </div>
        `;
    }
};

/** Executes javascript functions required for a specific view */
function executeViewLogic(viewId) {
    if (currentRole === 'student') {
        if (viewId === 'student_dashboard') {
            const student = JSON.parse(localStorage.getItem('student'));
            if (typeof renderStudentInfo === 'function') renderStudentInfo(student);
            if (typeof renderTimetable === 'function') renderTimetable(student);
            if (typeof renderNotifications === 'function') renderNotifications();
            if (typeof renderAttendance === 'function') renderAttendance();
            if (typeof renderHolidays === 'function') renderHolidays();
            if (typeof renderFaceWidget === 'function') renderFaceWidget();
            if (typeof renderLeaveWidget === 'function') renderLeaveWidget();
        } else if (viewId === 'profile') {
            if (typeof loadProfilePage === 'function') loadProfilePage();
        } else if (viewId === 'face') {
            if (typeof loadFacePage === 'function') loadFacePage();
        } else if (viewId === 'attendance') {
            if (typeof loadAttendancePage === 'function') loadAttendancePage();
        } else if (viewId === 'timetable') {
            if (typeof loadTimetablePage === 'function') loadTimetablePage();
        } else if (viewId === 'leave') {
            if (typeof loadLeavePage === 'function') loadLeavePage();
        }
    } else if (currentRole === 'teacher') {
        if (viewId === 'teacher_dashboard') {
            if (typeof renderTeacherDashboard === 'function') renderTeacherDashboard();
        } else if (viewId === 'teacher_attendance') {
            if (typeof renderTeacherAttendance === 'function') renderTeacherAttendance();
        } else if (viewId === 'teacher_leave') {
            if (typeof initTeacherLeavePage === 'function') initTeacherLeavePage();
        } else if (viewId === 'teacher_students') {
            if (typeof initTeacherStudentManagement === 'function') initTeacherStudentManagement();
        } else if (viewId === 'teacher_attendance_history') {
            if (typeof loadTeacherAttendanceHistory === 'function') loadTeacherAttendanceHistory();
        } else if (viewId === 'teacher_timetable') {
            if (typeof loadTeacherTimetable === 'function') loadTeacherTimetable();
        } else if (viewId === 'teacher_reports') {
            if (typeof loadTeacherReports === 'function') loadTeacherReports();
        }
    } else if (currentRole === 'admin') {
        if (viewId === 'admin_dashboard') {
            if (typeof renderAdminDashboard === 'function') renderAdminDashboard();
        } else if (viewId === 'admin_users') {
            if (typeof loadAdminUsers === 'function') loadAdminUsers();
        } else if (viewId === 'admin_academics') {
            if (typeof loadAdminAcademics === 'function') loadAdminAcademics();
        } else if (viewId === 'admin_attendance') {
            if (typeof loadAdminAttendance === 'function') loadAdminAttendance();
        } else if (viewId === 'admin_leaves') {
            if (typeof loadAdminLeaves === 'function') loadAdminLeaves();
        } else if (viewId === 'admin_reports') {
            if (typeof loadAdminReports === 'function') loadAdminReports();
        }
    }

    if (viewId === 'settings') {
        if (typeof initSettingsPage === 'function') initSettingsPage();
    } else if (viewId === 'notifications') {
        if (typeof initNotificationsPage === 'function') initNotificationsPage();
    }

    if (typeof refreshNotificationBadge === 'function') {
        refreshNotificationBadge();
    }
    // Expand for admin when those views are built
}

/** Sidebar Mobile Toggle */
window.toggleSidebar = function() {
    // The sidebar element itself is inside the container
    const sidebar = document.getElementById('sidebar-container').firstElementChild;
    const overlay = document.getElementById('sidebar-overlay');
    if (sidebar && overlay) {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('visible');
    }
};

/** Shared Sign Out */
window.signOut = function() {
    localStorage.removeItem('student');
    localStorage.removeItem('teacher');
    localStorage.removeItem('admin');
    localStorage.removeItem('access_token');
    localStorage.removeItem('token_type');
    window.location.href = 'signin.html';
};
