# EduSync — Smart Campus ERP

## Project Description
EduSync is a Smart Campus ERP system designed to streamline and manage administrative and academic operations within an educational institution. It provides dedicated modules for students, teachers, administrators, attendance tracking, and facial recognition-based registration.

## Purpose

Educational institutions often struggle with fragmented, paper-based, or siloed systems for managing their day-to-day operations — from tracking attendance and handling leave requests to maintaining student and staff records. **EduSync** was built to solve this problem.

### Why EduSync?

The goal of EduSync is to provide a **unified, digital platform** that brings together all core campus management functions under one roof, replacing manual processes with efficient, automated workflows. Specifically, it aims to:

- **Eliminate administrative overhead** by digitizing processes such as student enrollment, leave management, attendance recording, and profile management.
- **Empower educators and students** with self-service access to their academic data, schedules, and records through role-based dashboards.
- **Enhance security and accuracy** by incorporating facial recognition for identity verification during attendance and registration, reducing fraud and human error.
- **Enable data-driven decisions** by centralizing institutional data in a structured database, making it easier for administrators to generate reports and insights.
- **Scale with the institution** through a modular architecture that allows new features (e.g., notifications, grading, fee management) to be added without disrupting existing functionality.

### Who Is It For?

| Role | Benefit |
|------|---------|
| **Students** | View attendance, submit leave requests, manage their profile |
| **Teachers** | Mark and monitor attendance, manage class records |
| **Administrators** | Oversee all modules, manage users, and access institution-wide reports |

EduSync serves as the foundational layer for a **smart, connected campus** — making campus life more organized, transparent, and efficient for everyone involved.

## Technology Stack
- **Backend**: Python 3.12, FastAPI
- **Database**: MongoDB (motor)
- **Authentication**: JWT (JSON Web Tokens)
- **Frontend**: HTML, CSS, JavaScript (Vanilla)

## Folder Structure
```text
EduSync-ERP/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── middleware/
│   │   ├── dependencies/
│   │   ├── exceptions/
│   │   └── main.py
│   ├── uploads/
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   └── run.py
├── frontend/
│   ├── pages/
│   ├── css/
│   ├── js/
│   ├── assets/
│   └── components/
├── docs/
├── README.md
└── .gitignore
```

## Setup Instructions

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables:
   - Copy `.env.example` to `.env` and update the placeholder values.
5. Run the server:
   ```bash
   python run.py
   ```

## Development Roadmap
- **Phase 1**: Initial project scaffolding and directory structure setup.
- **Phase 2**: Backend core setup (Database connection, Security, JWT Auth).
- **Phase 3**: API endpoint implementation (Student, Teacher, Admin modules).
- **Phase 4**: Frontend integration and UI development.
- **Phase 5**: Advanced features (Facial recognition, Notifications).
- **Phase 6**: Testing, optimization, and production deployment.
