# Local Testing Guide for ClimaSync.AI Login Feature

This guide walks you through manually verifying the Authentication and Login APIs using FastAPI's built-in Swagger UI and your local Supabase Dashboard.

---

## Step 1: Start the Development Server

Open your terminal in the backend root directory (`f:\ClimasyncAI_backend`) and run the FastAPI server using `uv`:

```bash
uv run uvicorn app.main:create_app --reload --host 127.0.0.1 --port 8000
```
*Wait until you see the `Application startup complete` message.*

---

## Step 2: Open the Swagger UI Dashboard

FastAPI automatically generates an interactive API schema interface. 
1. Open your browser and navigate to: **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**
2. You will see both the `/api/v1/auth/login` and `/api/v1/auth/register` endpoints listed under the **Auth** section.

---

## Step 3: Register a New Test User

You first need a registered account before you can log in.

1. In the Swagger UI, click on the **`POST /api/v1/auth/register`** endpoint.
2. Click the **"Try it out"** button.
3. In the Request body, fill in the JSON data:
```json
{
  "email": "testuser1@example.com",
  "org_name": "Test NGO",
  "password": "StrongPassword123!"
}
```
4. Click **Execute**. You should receive an `HTTP 201 Created` response.

---

## Step 4: Verify the Email in Supabase Manually
Because the backend enforces an "Email Verification Required" security policy, you cannot log in yet. In a production flow, you would enter an OTP sent to your email. For this manual test, we'll verify it straight in the database.

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard/).
2. Select your ClimaSync.AI project and navigate to the **Table Editor**.
3. Open the **`auth_users`** table.
4. Find the row with `"testuser1@example.com"`.
5. Edit the `email_verified` column to be **`TRUE`**.
6. Set the `email_verified_at` column to the current timestamp (or any valid date).
7. Ensure the table saves securely.

---

## Step 5: Test the Login Flow

Now that the email is verified, let's capture our Access Tokens!

1. Go back to the Swagger UI at **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**.
2. Click on the **`POST /api/v1/auth/login`** endpoint.
3. Click **"Try it out"**.
4. In the Request body, fill in your matching credentials:
```json
{
  "email": "testuser1@example.com",
  "password": "StrongPassword123!"
}
```
5. Click **Execute**.

### Expected Responses 🎯
* **If Successful:** You will receive an `HTTP 200 OK` housing your `access_token`, `refresh_token`, and user profile data!
* **If Incorrect Password:** You will receive `HTTP 401 Unauthorized`.
* **If You Spin Request Super Fast (Brute Force):** On the 11th quick tap, the system will block you and return `HTTP 429 Too Many Requests`.

---

## 💡 Using Postman Instead?
If you strictly prefer Postman over Swagger UI:
1. Import a new Request and set the method to **POST**.
2. URL: `http://127.0.0.1:8000/api/v1/auth/login`
3. Under the **Body** tab, select **raw** and switch the format to **JSON**.
4. Paste the JSON payloads seen above and hit **Send**!
