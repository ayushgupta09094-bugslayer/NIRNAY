# NIRNAY — local development with PostgreSQL and Firebase

NIRNAY uses:
- **PostgreSQL** for application profiles, user records, document metadata, and push-installation metadata.
- **Firebase Authentication** for user registration and sign-in.
- **Firebase Storage** for private uploaded document files.
- **Firebase Cloud Messaging** for optional browser notifications.
- **FastAPI** to verify Firebase ID tokens and authorize each user's database/file operations.

Firestore is not used by this backend. PostgreSQL tables are created automatically when the backend starts for the first time.

## Requirements

- Git
- Node.js LTS with npm
- Python 3.11 or newer
- PostgreSQL 15+ installed and running locally
- A Firebase project

## 1. Get the code and install frontend packages

Run from PowerShell:

```powershell
git clone https://github.com/ayushgupta09094-bugslayer/NIRNAY.git
cd NIRNAY

cd frontend
npm install
cd ..
```

If you are already working from a clone, do not clone over it. Make a backup or use a separate folder before switching branches when you have uncommitted changes.

## 2. Firebase Authentication and Web App

1. Open the [Firebase Console](https://console.firebase.google.com/) and create/select your project.
2. Go to Project settings → General → Your apps, register a Web app, and copy its config.
3. Open Build → Authentication → Sign-in method and enable **Email/Password**.
4. In Authentication settings → Authorized domains, make sure `localhost` is allowed for local development.
5. Create the frontend env file:

   ```powershell
   Copy-Item frontend/.env.example frontend/.env.local
   notepad frontend/.env.local
   ```

6. Fill in the Web App values:

   ```dotenv
   VITE_FIREBASE_API_KEY=your-web-api-key
   VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=your-project-id
   VITE_FIREBASE_STORAGE_BUCKET=your-actual-storage-bucket
   VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
   VITE_FIREBASE_APP_ID=your-web-app-id
   VITE_FIREBASE_VAPID_KEY=your-web-push-public-vapid-key
   VITE_API_BASE_URL=
   ```

   Replace the example values with the actual values from your project. The VAPID key is only needed to enable push notifications.

Firebase Web App config and the Web Push VAPID public key are client-side values. Never place a Firebase Admin service-account JSON/private key in a `VITE_*` variable or in source control.

## 3. Install and create the PostgreSQL database

You do **not** need to create a Firestore database. Application data goes into PostgreSQL.

### A. Start PostgreSQL

Install PostgreSQL for Windows using the official installer from [postgresql.org](https://www.postgresql.org/download/windows/). Remember the password you choose for the PostgreSQL administrator (usually `postgres`) and keep the database service running.

### B. Create a database and app user

Open **pgAdmin**, connect to your local PostgreSQL server, right-click the server's database/query tools, and open the Query Tool while connected as the PostgreSQL administrator. Run this SQL once:

```sql
CREATE USER nirnay_user WITH PASSWORD 'choose-a-strong-password';
CREATE DATABASE nirnay OWNER nirnay_user;
```

Replace the sample password before running it. If you already created the user or database, do not re-run these statements blindly; keep the existing database and credentials.

Alternatively, if `psql` is on your PATH, run:

```powershell
psql -U postgres -h 127.0.0.1 -p 5432
```

Then enter the same SQL in the psql prompt. Exit psql with `\q`.

### C. Set the database connection URL

Create the backend environment file:

```powershell
Copy-Item backend/.env.example backend/.env
notepad backend/.env
```

Set `DATABASE_URL` to the username, password, host, port, and database you just created:

```dotenv
DATABASE_URL=postgresql+psycopg2://nirnay_user:choose-a-strong-password@127.0.0.1:5432/nirnay
```

If your password contains special URL characters (such as `@`, `:`, `/`, or `#`), URL-encode the password portion or choose a strong development password that avoids URL-reserved characters. Keep `DATABASE_URL` private and never commit `backend/.env`.

The backend uses SQLAlchemy and psycopg2 to connect to PostgreSQL. Its first startup creates these tables if they do not exist:

- `users`: Firebase UID and basic profile fields.
- `user_records`: user-owned structured records; `data` is stored as PostgreSQL JSON.
- `user_documents`: file metadata and Firebase Storage object path (file bytes are not stored in PostgreSQL).
- `push_installations`: notification installation identifiers associated with a Firebase UID.

## 4. Enable Firebase Storage (files only)

1. In Firebase Console, open Build → Storage and choose **Get started** to create/enable the Storage bucket.
2. Copy the exact bucket name shown in the console (newer projects often use `PROJECT_ID.firebasestorage.app`; some older ones use `PROJECT_ID.appspot.com`).
3. In `backend/.env`, set:

   ```dotenv
   FIREBASE_PROJECT_ID=your-project-id
   FIREBASE_STORAGE_BUCKET=your-actual-storage-bucket
   GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
   FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ENABLE_TEST_NOTIFICATIONS=false
   ```

The supplied `storage.rules` denies direct browser reads/writes. The backend uses Firebase Admin after validating the Firebase ID token, checks that document metadata belongs to the signed-in UID, and then accesses the file in Storage.

## 5. Configure Firebase Admin credentials for FastAPI

1. In Firebase Console → Project settings → Service accounts, generate a private key for a service account.
2. Save the downloaded JSON file locally as `backend/service-account.json`.
3. Confirm `GOOGLE_APPLICATION_CREDENTIALS=./service-account.json` is set in `backend/.env`.
4. Verify that your environment file has the same `FIREBASE_PROJECT_ID` as your Web App config and the correct Storage bucket name.

The service-account file is a private server credential. Never commit or share it. The repository's `.gitignore` excludes service-account JSON files and environment files.

## 6. Install and run the backend

Open PowerShell at the repository root:

```powershell
cd backend

py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks venv activation, run this in that terminal and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
```

If the backend does not start, check that PostgreSQL is running, that `DATABASE_URL` matches your database credentials, and that the current working directory is `backend/` so the service-account path resolves correctly.

## 7. Run and check the frontend

Open a second PowerShell terminal at the repository root:

```powershell
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

Open these URLs:

- Frontend: http://localhost:5173
- API health: http://127.0.0.1:8000/healthz
- Interactive API docs: http://127.0.0.1:8000/docs

The Vite development server proxies `/api` to the local backend at `http://127.0.0.1:8000`.

## 8. Test user data and file uploads

1. Open http://localhost:5173/register and create a test account.
2. Sign in and confirm the dashboard appears.
3. Save a test record. In pgAdmin, inspect the `users` and `user_records` tables in the `nirnay` database.
4. Upload a small PDF or TXT file. The file bytes should appear in Firebase Storage; its metadata should appear in PostgreSQL's `user_documents` table.
5. Download and delete the file to check both the API and Storage connection.
6. Run `npm run lint` and `npm run build` from `frontend/` after frontend changes.

Each database query is filtered by the UID in the verified Firebase ID token, so one authenticated user's records and document metadata are not returned for another UID. If you already saved data to Firestore during earlier testing, this migration does not automatically copy it to PostgreSQL; export/transform it separately only if you need to preserve it.

## 9. Optional: browser push notifications

1. In Firebase Console → Cloud Messaging, configure the Web Push certificate/public VAPID key.
2. Set `VITE_FIREBASE_VAPID_KEY` in `frontend/.env.local` and restart Vite.
3. Open the frontend over `http://localhost:5173` or HTTPS, sign in, and click **Enable notifications**.
4. Grant notification permission in the browser.
5. For a backend notification test only, set `ENABLE_TEST_NOTIFICATIONS=true` in `backend/.env`, restart the backend, and call the authenticated `POST /api/v1/notifications/test` endpoint. Set it back to `false` afterwards.

Push notifications are optional for testing authentication, PostgreSQL records, and document storage.
