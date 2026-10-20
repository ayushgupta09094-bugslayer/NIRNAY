# NIRNAY — Firebase Authentication, Firestore, and Storage

NIRNAY uses Firebase Authentication for login, Cloud Firestore for user profiles and application records, FastAPI for protected API operations, and Firebase Storage for uploaded files when Storage is enabled on the Firebase project. PostgreSQL is no longer used by the backend in this branch.

## 1. Firebase Console setup

1. Select your Firebase project.
2. In Authentication → Sign-in method, enable Email/Password.
3. Create a Cloud Firestore database using Standard edition and Production mode.
4. Keep the repository's restrictive Firestore rules deployed.
5. Storage is optional for local Firestore testing. Firebase Storage setup for new projects may require the Blaze billing plan; if you stay on Spark, document upload/download will not work until you configure an alternative storage provider.

## 2. Configure frontend environment

Create the frontend environment file from PowerShell at the repository root:

    Copy-Item frontend/.env.example frontend/.env.local
    notepad frontend/.env.local

Fill the Firebase Web App values from Project settings → General → Your apps:

    VITE_FIREBASE_API_KEY=your-web-api-key
    VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
    VITE_FIREBASE_PROJECT_ID=your-project-id
    VITE_FIREBASE_STORAGE_BUCKET=your-actual-storage-bucket
    VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
    VITE_FIREBASE_APP_ID=your-web-app-id
    VITE_FIREBASE_VAPID_KEY=your-web-push-public-vapid-key
    VITE_API_BASE_URL=

The VAPID key is only needed for push notifications. Never put service-account credentials in a VITE variable.

## 3. Configure backend environment and credentials

In Firebase Console → Project settings → Service accounts, generate a private key for local development. Save it as backend/service-account.json. Do not commit or share this file.

Create the backend environment file:

    Copy-Item backend/.env.example backend/.env
    notepad backend/.env

Set these values:

    FIREBASE_PROJECT_ID=your-project-id
    FIREBASE_STORAGE_BUCKET=your-actual-storage-bucket
    GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
    FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
    ENABLE_TEST_NOTIFICATIONS=false

Use the exact project ID and bucket name from your Firebase Console. The Storage bucket is only required for file uploads and downloads.

The FastAPI backend verifies Firebase ID tokens and checks the authenticated UID before reading or changing user-owned Firestore records. Admin SDK calls bypass Firestore Security Rules, so server-side ownership checks are essential.

## 4. Firestore collections

The backend creates documents automatically when data is first saved. You do not need to create collections manually.

- users/{firebase_uid}: user profile.
- user_records/{record_id}: user records and associated data.
- user_documents/{document_id}: document metadata and Storage object path.
- push_installations/{installation_id}: push-notification registration metadata.

Existing PostgreSQL records are not automatically migrated.

## 5. Run the backend

Open PowerShell at the repository root:

    cd backend
    py -m venv venv
    .\venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

If PowerShell blocks activation, run the following in that terminal and activate again:

    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    .\venv\Scripts\Activate.ps1

If you already have a virtual environment, activate it instead of creating another one. Run commands from backend so the relative service-account path resolves.

## 6. Run the frontend

Open a second PowerShell terminal at the repository root:

    cd frontend
    npm install
    npm run lint
    npm run build
    npm run dev

Open http://localhost:5173. Backend health is available at http://127.0.0.1:8000/healthz and API documentation at http://127.0.0.1:8000/docs.

## 7. Test Firestore

1. Register and sign in at the local website.
2. Open Firebase Console → Firestore → Data.
3. Visit the app's profile endpoint or dashboard; the users collection should receive the profile when the frontend calls the authenticated /api/v1/auth/me endpoint.
4. Create a record; verify it appears in user_records.
5. Test upload/download only if Firebase Storage is enabled and configured.
6. Run npm run lint and npm run build in frontend before deploying.

Test with two separate accounts to ensure users cannot access each other's records. Do not deploy until you have tested authentication and ownership checks.

## 8. Optional push notifications

Configure Cloud Messaging and the public Web Push VAPID key, then set VITE_FIREBASE_VAPID_KEY in frontend/.env.local. Restart Vite after changing environment variables. To test backend notifications, temporarily set ENABLE_TEST_NOTIFICATIONS=true in backend/.env, restart the backend, and call the authenticated POST /api/v1/notifications/test endpoint. Set the flag back to false afterwards.
