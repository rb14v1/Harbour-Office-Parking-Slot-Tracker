# Office Parking Slot Tracker

A web application that shows which office parking slots are free, lets employees occupy and release a slot, and gives administrators occupancy monitoring, employee management and usage reports.

- **Frontend:** React 18, Vite, Bootstrap 5, custom CSS, React Router, Axios, Recharts, Bootstrap Icons
- **Backend:** Python 3.13, FastAPI, PyMongo, PyJWT, bcrypt
- **Database:** MongoDB 7 (local, MongoDB Atlas, or Docker)

> **Scope change:** the original brief asked for Django and Django REST Framework. The project folder layout was then specified with a FastAPI backend, so the backend is FastAPI. The MongoDB rules still apply: PyMongo only, no Django ORM, no SQLite.

---

## 1. Problem statement

Employees drive to the office without knowing whether a parking slot is free. Facilities staff have no live view of usage and track allocations by hand. This tracker shows live availability, enforces one slot per employee and one employee per slot, and records every session for reporting.

## 2. Objectives

- Show live slot availability, refreshed every 5 seconds.
- Let an employee occupy a free slot that matches their vehicle, and release it when leaving.
- Prevent double allocation, both for the same slot and for the same employee.
- Give administrators slot and employee management, live occupancy, history and daily reports.
- Calculate every figure from stored entry and exit records.

## 3. Main features

| Area | Employee | Administrator |
|---|---|---|
| Access | Name, email and vehicle entered once (saved in the browser, no password) | Administrator password on the admin sign-in page |
| Dashboard | Summary cards, visual slot overview, recent activity | Same, plus 7-day entry/exit chart |
| Parking Slots | Filter by floor, vehicle type, status; search slot ID; occupy a free slot | Read-only view |
| My Parking | Own details, current allocation, release, select and confirm a free slot | Not applicable |
| Parking History | Own sessions | All sessions; filter by employee and slot |
| Reports & Analytics | No access | Daily entries/exits, occupied hours, average duration, peak hours, most-used slots, occupancy |
| Administration | No access | Add, edit, deactivate slots; add, edit, activate/deactivate employees; live occupancy |

## 4. System architecture

```
Browser (React SPA)                 Backend (FastAPI)                  MongoDB
+-------------------------+   HTTP   +--------------------------+  PyMongo  +--------------------+
| Pages                   |  JSON    | api/routes/*  (HTTP)     |---------> | employees          |
| Axios service layer     |<-------> | services/*   (rules)     |           | parking_slots      |
| 5 s polling hooks       |  + JWT   | db/mongo.py  (connection)|           | parking_history    |
+-------------------------+          | migrations/* (indexes)   |           | schema_migrations  |
                                     +--------------------------+           +--------------------+
```

- **Routes** validate input (Pydantic) and call services. They do not touch collections directly.
- **Services** hold the business rules, including the allocation logic in `backend/app/services/parking_service.py`.
- **Access:** employees are identified by the email in the `X-Employee-Email` header (no password). Administrators sign in with `ADMIN_PASSWORD` and receive an HS256 JWT. Employee active status is re-read from MongoDB on every request.
- **Timestamps:** stored in UTC. Returned as ISO strings with the `+05:30` offset (Asia/Kolkata). Report days and the history date filters use IST boundaries.

### Allocation rules (how double booking is prevented)

1. Reject if the employee already has an active session (`status: active`).
2. Check the slot exists, is not Inactive, and matches the employee's vehicle type.
3. **Atomic claim:** `find_one_and_update` changes the slot from `Available` to `Occupied` only if it is still `Available`. Exactly one concurrent request can match.
4. Insert the history record with `status: active`. Two unique partial indexes block a second active session for the same employee (`one_active_per_employee`) or the same slot (`one_active_per_slot`).
5. If step 4 fails, roll the slot back to `Available` and return a 409.

Release sets the history record to `completed` (conditional on it still being `active`), then frees the slot only if it still belongs to that session. If the slot update does not match, the history change is reverted.

## 5. Database collections

### `employees`

| Field | Type | Notes |
|---|---|---|
| `employee_id` | string | Unique. Stored uppercase. |
| `employee_name` | string | |
| `email` | string | Unique. Stored lowercase. |
| `password_hash` | string | bcrypt. Never returned by the API. |
| `department` | string | |
| `role` | `employee` \| `admin` | |
| `vehicle_type` | `Car` \| `Bike` | |
| `vehicle_number` | string | Registration number, uppercase. |
| `is_active` | bool | Inactive accounts cannot log in or call the API. |
| `created_at` | datetime (UTC) | |

### `parking_slots`

| Field | Type | Notes |
|---|---|---|
| `slot_id` | string | Unique. Example `G-C01`. |
| `floor` | string | `G`, `1`, `2`... |
| `location` | string | |
| `vehicle_type` | `Car` \| `Bike` | |
| `status` | `Available` \| `Occupied` \| `Reserved` \| `Inactive` | |
| `occupied_by` | string \| null | `employee_id` of the current holder. |
| `occupied_at` | datetime \| null | |
| `updated_at` | datetime (UTC) | |

### `parking_history`

| Field | Type | Notes |
|---|---|---|
| `employee_id` | string | |
| `employee_name` | string | Copied at entry time. |
| `slot_id` | string | |
| `vehicle_number` | string | Copied at entry time. |
| `entry_time` | datetime (UTC) | |
| `exit_time` | datetime \| null | `null` while the session is active. |
| `duration_minutes` | number \| null | Set on release. |
| `status` | `active` \| `completed` | |

### `schema_migrations`

Records which migrations have run (`version`, `description`, `applied_at`).

### Indexes (from `backend/migrations/001_create_indexes.py`)

| Collection | Index | Purpose |
|---|---|---|
| employees | `employee_id` unique | Identity |
| employees | `email` unique | Identity |
| employees | `department` | Filtering |
| parking_slots | `slot_id` unique | Identity |
| parking_slots | `floor, vehicle_type, status` | Slot filters |
| parking_slots | `status` | Availability counts |
| parking_history | `employee_id, entry_time desc` | Employee history |
| parking_history | `slot_id, entry_time desc` | Slot history |
| parking_history | `entry_time desc` | Reports and date filters |
| parking_history | `employee_id` unique, partial `status: active` | One active session per employee |
| parking_history | `slot_id` unique, partial `status: active` | One active session per slot |

## 6. API endpoints

All endpoints are under `/api`. Success responses: `{ "success": true, "message": "...", "data": ... }`. Errors: `{ "success": false, "message": "...", "error": { "code": "...", "details": ... } }`.

Interactive documentation: `http://localhost:8010/docs`.

| Method | Path | Access | Purpose |
|---|---|---|---|
| GET | `/health` | Public | API and MongoDB health |
| POST | `/auth/admin/login` | Public | Administrator login with `ADMIN_PASSWORD` |
| POST | `/identity` | Public | Save or update name, email, vehicle type and vehicle number |
| GET | `/identity/me` | Identity header | Confirm the saved employee |
| GET | `/auth/admin/me` | Admin | Check the administrator session |
| GET | `/slots` | Logged in | All slots; filters `floor`, `vehicle_type`, `status`, `search` |
| GET | `/slots/available` | Logged in | Free slots; optional `vehicle_type` |
| GET | `/slots/occupied` | Logged in | Occupied slots |
| GET | `/slots/floors` | Logged in | Distinct floors |
| GET | `/slots/{slot_id}` | Logged in | One slot |
| POST | `/slots` | Admin | Add slot |
| PATCH | `/slots/{slot_id}` | Admin | Edit slot |
| POST | `/slots/{slot_id}/deactivate` | Admin | Deactivate slot |
| POST | `/parking/occupy` | Logged in | Occupy a slot. Body: `{ "slot_id" }` |
| POST | `/parking/release` | Logged in | Release own slot. Admin may release any slot by passing `slot_id`. |
| GET | `/parking/me` | Logged in | Current allocation or `null` |
| GET | `/parking/occupancy` | Admin | Occupied slots with holders |
| GET | `/parking/history` | Logged in | Paged history; employees see own records only. Params: `employee_id`, `slot_id`, `date_from`, `date_to`, `sort_by`, `sort_order`, `page`, `page_size` |
| GET | `/employees` | Admin | List; params `search`, `department`, `role` |
| POST | `/employees` | Admin | Add employee |
| GET | `/employees/{employee_id}` | Admin | One employee |
| PATCH | `/employees/{employee_id}` | Admin | Edit employee |
| POST | `/employees/{employee_id}/deactivate` | Admin | Deactivate (blocked while the employee holds a slot) |
| POST | `/employees/{employee_id}/activate` | Admin | Reactivate |
| GET | `/dashboard/stats` | Logged in | Slot counts, occupancy %, entries/exits today, recent activity |
| GET | `/reports/daily?date=YYYY-MM-DD` | Admin | Daily entries, exits, durations, hourly entries, top slots |
| GET | `/reports/trends?days=7` | Admin | Per-day entries and exits |
| GET | `/reports/peak-hours?days=30` | Admin | Entries by IST hour |
| GET | `/reports/most-used-slots?days=30&limit=5` | Admin | Slots ranked by sessions |
| GET | `/reports/summary?days=30` | Admin | Totals, averages, current occupancy |

## 7. Project structure

```
office-parking-slot-tracker/
├── .github/workflows/ci.yml      CI: backend tests (MongoDB service), frontend tests and build
├── backend/
│   ├── app/
│   │   ├── api/                  deps.py (auth guards), routes/ (one module per area)
│   │   ├── core/                 config, security, timezone, exceptions
│   │   ├── db/mongo.py           PyMongo client and collection access
│   │   ├── schemas/              Pydantic request models and response helpers
│   │   ├── services/             business rules (auth, slots, parking, employees, reports)
│   │   └── main.py               app factory, CORS, error handlers, routers
│   ├── migrations/               001_create_indexes.py and runner.py
│   ├── scripts/seed.py           development sample data
│   ├── tests/                    pytest suites (auth, slots, parking, reports, employees)
│   ├── requirements.txt
│   └── requirements-dev.txt
├── frontend/
│   ├── src/api/                  Axios client and service functions
│   ├── src/components/           layout, guards, dialogs, cards, admin forms
│   ├── src/context/              auth and toast providers
│   ├── src/hooks/usePolling.js   5-second refresh hook
│   ├── src/pages/                login, dashboard, slots, my parking, history, reports, admin
│   ├── src/styles/custom.css
│   └── src/utils/                formatting and tests
├── docs/                         placeholder documents
├── infra/
│   ├── docker/                   backend and frontend Dockerfiles
│   ├── nginx/nginx.conf          serves the SPA and proxies /api
│   └── deploy/README.md          deployment placeholder
├── .dockerignore  .env.example  .gitignore  docker-compose.yml  healthz.py  README.md
```

## 8. Prerequisites (Windows 11)

- **Python 3.13** (`python --version`)
- **Node.js 24 LTS** (`node --version`)
- **MongoDB Community Server 7.x**, with MongoDB Compass for inspection. Install from https://www.mongodb.com/try/download/community and keep the "Install MongoDB as a Service" option ticked. The service then starts automatically.
- Optional: Docker Desktop, for the containerised run.

## 9. MongoDB configuration

**Option A: local MongoDB (default).** After installing, check the service is running:

```powershell
Get-Service MongoDB
```

If it is stopped: `Start-Service MongoDB`. The default URI is `mongodb://localhost:27017`, which matches `.env.example`.

**Option B: MongoDB Atlas.** Create a free cluster, add your IP to the access list, create a database user, and copy the connection string. Put it in `.env` as `MONGO_URI`. Never commit it.

**Connect with Compass:** open MongoDB Compass, use `mongodb://localhost:27017` (or the Atlas string), then open the `parking_tracker` database. You will see `employees`, `parking_slots`, `parking_history` and `schema_migrations`.

## 10. Environment variables

Copy the template and edit it:

```powershell
Copy-Item .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` refuses to start with the default JWT secret |
| `MONGO_URI` | `mongodb://localhost:27017` | Local or Atlas connection string |
| `MONGO_DB_NAME` | `parking_tracker` | Database name |
| `JWT_SECRET_KEY` | `dev-only-change-me` | Signing key. Use a long random value outside development. |
| `JWT_ALGORITHM` | `HS256` | |
| `JWT_EXPIRE_MINUTES` | `480` | Token lifetime (8 hours) |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated frontend origins |
| `ADMIN_PASSWORD` | `Admin@12345` | Administrator password. Must be changed outside development. |

The frontend reads `frontend/.env` (copy `frontend/.env.example`). `VITE_API_PROXY_TARGET` points the dev server at the backend.

## 11. Backend setup

Run these in a PowerShell terminal in VS Code (`Terminal > New Terminal`):

```powershell
cd C:\Users\admin\office-parking-slot-tracker\backend

# Create and activate the virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks the activation script, run this once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Install dependencies and start the API:

```powershell
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8010
```

On startup the API applies pending migrations (indexes) to MongoDB. Check it in a second terminal from the project root:

```powershell
python healthz.py
```

Expected output: `OK: Service is healthy. (http://localhost:8010/api/health)`.

## 12. Frontend setup

Open a second, separate terminal:

```powershell
cd C:\Users\admin\office-parking-slot-tracker\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open http://localhost:5173. The Vite dev server forwards `/api` to the backend on port 8000.

## 13. Database seeding

With the backend virtual environment active, from `backend`:

```powershell
# Add sample data only if the database is empty
python -m scripts.seed

# Drop existing parking data and reseed
python -m scripts.seed --reset
```

Seed contents: 20 slots over floors G, 1 and 2 (car and bike, one Reserved, one Inactive, five currently occupied), 1 administrator, 10 employees across six departments, and about 14 days of completed sessions.

## 14. Running the full application

Two terminals, both running at the same time:

| Terminal | Folder | Command | URL |
|---|---|---|---|
| 1: backend | `backend` (venv active) | `uvicorn app.main:app --reload --port 8010` | http://localhost:8010/docs |
| 2: frontend | `frontend` | `npm run dev` | http://localhost:5173 |

## 15. Sample employees and administrator (development only)

Employees have no password. Enter the name and email in the app's **My Parking** or **My Bookings** page. The seeded employees are:

| Name | Email | Employee ID |
|---|---|---|
| Aarav Sharma | aarav.sharma@example.com | EMP001 |
| Rohan Mehta | rohan.mehta@example.com | EMP003 |
| Meera Nair | meera.nair@example.com | EMP006 |

Other seeded employees follow the same pattern (`firstname.lastname@example.com`, EMP002 to EMP010). Their vehicle type and number are in `scripts/seed.py`.

Administrator password: `ADMIN_PASSWORD` in `.env`. The development default is `Admin@12345`. Change it outside development.

## 16. Testing

### Backend (pytest, needs MongoDB running)

Tests use a separate database, `parking_tracker_test`, which is dropped at the start of each run. Dev data is not touched.

```powershell
cd C:\Users\admin\office-parking-slot-tracker\backend
.\.venv\Scripts\Activate.ps1
pytest -v
```

The suites cover login and token rules, slot filters and admin guards, the allocation rules, release ownership, history paging and sorting, reports, employee management, and concurrency:

- 10 employees race for one slot: exactly one succeeds.
- One employee races for 5 slots: exactly one allocation is recorded, and no slot is left claimed by a failed attempt.

### Frontend

```powershell
cd C:\Users\admin\office-parking-slot-tracker\frontend
npm test
npm run build
```

### Manual checks (not automated)

1. Two browsers: enter EMP003's details in one and EMP006's details in the other. Occupy a slot in one window; within about 5 seconds the other window shows it as occupied.
2. Refresh the page after occupying a slot: the allocation remains (persistence check in MongoDB Compass).
3. Open `/reports` without signing in as administrator: the app sends you to the administrator sign-in page. `GET /api/reports/daily` without the admin token returns 403.

### Docker (optional)

Requires Docker Desktop. Stop the local API and frontend first, because the containers use port 8010 and 8080.

```powershell
cd C:\Users\admin\office-parking-slot-tracker
copy .env.example .env   # optional; edit JWT_SECRET_KEY and ADMIN_PASSWORD
docker compose up --build
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8010/docs
- Health: `python healthz.py http://localhost:8010`
- Stop: `docker compose down` (add `-v` to also delete the MongoDB volume)

These containers have not yet been built or run on a machine with Docker installed.

## 17. Known limitations

- **Identity is not verified.** Anyone who types an employee's email can see, change or cancel that employee's bookings and parking. There is no password or email check. This is a deliberate trade-off for an internal tool.
- **Unidentified visitors** can see the dashboard but not slots, bookings or history.
- **No multi-document transactions.** Allocation uses single-document atomic updates plus compensating rollbacks. A crash between the slot claim and the history insert can leave a slot marked `Occupied` with no active session. The `occupied_by` value would then point at an employee with no active history. No automatic repair exists yet.
- **Standalone MongoDB.** Multi-document transactions need a replica set. This project does not require one.
- **Token storage.** The JWT is kept in `localStorage`, which JavaScript can read. Production should move it to an `HttpOnly` cookie with CSRF protection.
- **Logout is client-side.** Tokens are stateless, so a stolen token stays valid until it expires (8 hours by default). No revocation list exists.
- **No login rate limiting or account lockout.**
- **Polling, not push.** The UI refreshes every 5 seconds. Changes can take up to 5 seconds to appear. WebSockets are not implemented.
- **Admin force release.** An administrator can release any slot. Each release is not logged separately, though the history record is updated.
- **Time-zone handling.** Report days use IST boundaries. Duration of sessions still active is not included in averages.
- **Seed passwords are public** in the seed script defaults. They exist only for development.
- **Frontend bundle size.** The production build is about 690 kB before gzip, driven by Recharts. Code-splitting has not been applied.
- **Passwords** are limited to 72 bytes (bcrypt limit).

## 18. Future enhancements

- WebSocket or Server-Sent Events updates in place of polling.
- Automatic reconciliation job for orphaned allocations.
- Reservations (the `Reserved` status exists but no booking flow does).
- HttpOnly cookie authentication with refresh tokens.
- Visitor parking and multi-building support.
- CSV export of reports and history.
- Route-level code splitting for the reports page.

## 19. Documentation

Placeholder files in `docs/` are for content not yet written: `architecture.md`, `api.md`, `database.md`, `testing.md`, `known-limitations.md`. Deployment notes are in `infra/deploy/README.md`.
