async function loadTeacherTimetable() {
    const todayContainer = document.getElementById('teacher-today-classes');
    const weeklyContainer = document.getElementById('teacher-weekly-timetable');
    if (!todayContainer || !weeklyContainer) return;

    todayContainer.innerHTML = '<div class="text-muted">Loading timetable...</div>';
    weeklyContainer.innerHTML = '<div class="text-muted">Loading timetable...</div>';

    try {
        const response = await fetch(`${API_BASE_URL}/teacher/timetable`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) throw new Error('Failed to load timetable');
        const data = await response.json();
        renderTeacherTodayClasses(data.today || { periods: [] });
        renderTeacherWeeklyTimetable(data.weekly || []);
    } catch (err) {
        console.error(err);
        todayContainer.innerHTML = '<div class="text-muted">Unable to load timetable.</div>';
        weeklyContainer.innerHTML = '<div class="text-muted">Unable to load timetable.</div>';
    }
}

function renderTeacherTodayClasses(todayData) {
    const container = document.getElementById('teacher-today-classes');
    if (!container) return;

    const periods = todayData.periods || [];
    if (!periods.length) {
        container.innerHTML = '<div class="text-muted">No classes scheduled for today.</div>';
        return;
    }

    container.innerHTML = `
        <div class="row g-3">
            ${periods.map(period => `
                <div class="col-12 col-md-6">
                    <div class="card border-primary">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-center">
                                <h6 class="mb-0">${period.subject_name || 'Class'}</h6>
                                <span class="badge bg-primary">${period.start_time || ''} - ${period.end_time || ''}</span>
                            </div>
                            <div class="small text-muted mt-2">${period.room || '—'} · ${period.section || '—'}</div>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderTeacherWeeklyTimetable(weekly) {
    const container = document.getElementById('teacher-weekly-timetable');
    if (!container) return;

    if (!weekly.length) {
        container.innerHTML = '<div class="text-muted">No weekly timetable available.</div>';
        return;
    }

    container.innerHTML = `
        <div class="row g-3">
            ${weekly.map(day => `
                <div class="col-12 col-lg-6">
                    <div class="card h-100">
                        <div class="card-body">
                            <h6 class="fw-bold">${day.day_of_week || 'Day'}</h6>
                            <div class="small text-muted">${day.department || '—'} · Sem ${day.semester || '—'} · Sec ${day.section || '—'}</div>
                            <div class="mt-3">
                                ${(day.periods || []).map(period => `
                                    <div class="border rounded p-2 mb-2">
                                        <div class="fw-semibold">${period.subject_name || 'Class'}</div>
                                        <div class="small text-muted">${period.start_time || ''} - ${period.end_time || ''} · ${period.room || '—'}</div>
                                    </div>
                                `).join('') || '<div class="text-muted">No classes</div>'}
                            </div>
                        </div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

window.loadTeacherTimetable = loadTeacherTimetable;
