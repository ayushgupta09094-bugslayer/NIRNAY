# NIRNAY — PostgreSQL and Firebase setup

NIRNAY uses PostgreSQL for application data and Firebase for identity and cloud file storage. Firestore is not used by these backend routes.

## Architecture

- React + Vite is served by Vite locally and can be served by Firebase Hosting in production.
- Firebase Authentication handles email/password registration and login.
- Browser API requests include the Firebase ID token as `Authorization: Bearer ...`.
- FastAPI verifies tokens with Firebase Admin and scopes rows to the UID in the verified token.
- PostgreSQL stores user profiles, records, document metadata, and push-installation identifiers.
- Firebase Storage stores the actual private document bytes under `users/{uid}/documents/...`.
- Firebase Cloud Messaging is optional for browser notifications.
- Hosting rewrites `/api/**` to Cloud Run service `nirnay-api` in `asia-south1`.
- The demo tender endpoint remains sample data and is not yet persisted in PostgreSQL.

## 1. Create the PostgreSQL database

Install PostgreSQL for Windows from [postgresql.org](https://www.postgresql.org/download/windows/), start the service, and open pgAdmin. Connect as your database administrator. Run the first statement and execute it; then run the second statement separately and execute it:

```sql
CREATE USER nirnay_user WITH PASSWORD 'choose-a-strong-password';
```

```sql
CREATE DATABASE nirnay OWNER nirnay_user;
```

Edit `backend/.env` and set the connection URL to your actual credentials:

```dotenv
DATABASE_URL=postgresql+psycopg2://nirnay_user:choose-a-strong-password@127.0.0.1:5432/nirnay
```

URL-encode reserved characters in the password. The backend creates the `users`, `user_records`, `user_documents`, and `push_installations` tables automatically at startup if they do not exist. No Firestore database is required.

## 2. Configure Firebase Authentication

1. Create/select a project at https://console.firebase.google.com/.
2. Project settings → General → Your apps → register a Web App and copy its config.
3. Authentication → Sign-in method → enable **Email/Password**.
4. Authentication → Settings → Authorized domains → make sure `localhost` is allowed.
5. Copy `frontend/.env.example` to `frontend/.env.local` and fill in the public Web App values:
   - `VITE_FIREBASE_API_KEY`
   - `VITE_FIREBASE_AUTH_DOMAIN`
   - `VITE_FIREBASE_PROJECT_ID`
   - `VITE_FIREBASE_STORAGE_BUCKET`
   - `VITE_FIREBASE_MESSAGING_SENDER_ID`
   - `VITE_FIREBASE_APP_ID`
   - `VITE_FIREBASE_VAPID_KEY` (only for push notifications)

The public Web App config and VAPID public key can be in frontend env vars. Never put Firebase Admin private keys in frontend files or Git.

## 3. Enable Firebase Storage

1. Firebase Console → Build → Storage → **Get started**.
2. Create/enable the Storage bucket and copy its exact name.
3. Set `FIREBASE_PROJECT_ID` and `FIREBASE_STORAGE_BUCKET` in `backend/.env`.

The exact bucket name may be `PROJECT_ID.firebasestorage.app` or `PROJECT_ID.appspot.com`, depending on the project. The repository's Storage rules block direct browser access; authenticated FastAPI routes use Firebase Admin after validating the caller's ID token and checking the document's owner UID.

## 4. Configure Firebase Admin on the backend

For local development, Firebase Console → Project settings → Service accounts → generate a private key. Save it as `backend/service-account.json` and set the following in `backend/.env`:

```dotenv
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_STORAGE_BUCKET=your-actual-storage-bucket
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
ENABLE_TEST_NOTIFICATIONS=false
```

Run Uvicorn from `backend/` so the relative credential path resolves. Never commit or share the service-account JSON. For Cloud Run, use Application Default Credentials from the attached service identity rather than uploading a service-account key; configure `DATABASE_URL` as a Cloud Run secret/env var and make sure the service can reach your managed PostgreSQL instance.

## 5. Install and run locally

From the repository root in PowerShell, first configure both `backend/.env` and `frontend/.env.local` as above.

Backend terminal:

```powershell
cd backend
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks environment activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` and activate again.

Frontend terminal, from repository root:

```powershell
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

Open http://localhost:5173. Check the backend at http://127.0.0.1:8000/healthz and API docs at http://127.0.0.1:8000/docs. Vite proxies `/api` to the local backend.

## 6. Verify

- Register and sign in with a test user.
- Save a record and inspect `user_records` in PostgreSQL/pgAdmin.
- Inspect `users` for the signed-in Firebase UID.
- Upload/download/delete a small PDF or TXT file. Actual file bytes live in Firebase Storage; metadata and object path live in `user_documents`.
- Test that one user cannot access another user's records/documents.

If earlier testing wrote data to Firestore, this change does not automatically migrate it. Export and transform that data separately only if you need to keep it.

## 7. Optional push notifications

1. Firebase Console → Cloud Messaging → Web Push certificates; copy/generate the public VAPID key.
2. Set `VITE_FIREBASE_VAPID_KEY` in `frontend/.env.local` and restart Vite.
3. Sign in on localhost/HTTPS and click **Enable notifications**; grant browser permission.
4. For an explicit test only, set `ENABLE_TEST_NOTIFICATIONS=true` in `backend/.env`, restart the backend, and call authenticated `POST /api/v1/notifications/test`. Reset the flag to `false` afterwards.

Push notifications are optional; Authentication, PostgreSQL records, and Storage uploads can be tested separately.

## Production checklist

- Configure a reachable managed PostgreSQL database and keep `DATABASE_URL` out of source control.
- Use least-privilege service identities, enforce UID/tenant/role authorization, and apply schema migrations before production changes.
- Firebase Admin bypasses client Storage rules, so every file route must validate the verified UID and document ownership.
- Add content-signature validation, malware scanning, retention, and audit trails before storing real procurement documents.
- Keep test notifications disabled in production and verify hosting rewrites/CORS before go-live.
