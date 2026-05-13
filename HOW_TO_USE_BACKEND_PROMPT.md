# How to Use the Backend Implementation Prompt

## 🎯 Purpose
The `BACKEND_IMPLEMENTATION_PROMPT.md` file contains a complete, structured prompt that you can give to an AI assistant (like Claude, ChatGPT, or me) to automatically implement the entire backend for your disaster management workflow.

---

## 📋 Step-by-Step Instructions

### Step 1: Open Your Backend Repository
```powershell
cd F:\ClimasyncAI_backend
```

### Step 2: Copy the Prompt File
Copy `BACKEND_IMPLEMENTATION_PROMPT.md` from your frontend repository to your backend repository:

```powershell
# From frontend folder
Copy-Item "F:\ClimaSyncAI_frontend\BACKEND_IMPLEMENTATION_PROMPT.md" -Destination "F:\ClimasyncAI_backend\"
```

Or manually copy the file.

### Step 3: Open AI Assistant in Backend Folder

**Option A: Using Kiro (if available in backend)**
1. Open VS Code in `F:\ClimasyncAI_backend`
2. Open Kiro chat
3. Paste the entire content of `BACKEND_IMPLEMENTATION_PROMPT.md`
4. Say: "Please implement this"

**Option B: Using Claude/ChatGPT**
1. Open Claude or ChatGPT
2. Start a new conversation
3. Copy the entire content of `BACKEND_IMPLEMENTATION_PROMPT.md`
4. Paste it into the chat
5. Add: "I'm in the F:\ClimasyncAI_backend folder. Please implement this."

**Option C: Using Cursor/Windsurf**
1. Open `F:\ClimasyncAI_backend` in Cursor/Windsurf
2. Open the AI chat
3. Paste the prompt
4. Let it implement

### Step 4: What the AI Will Do

The AI will automatically:
1. ✅ Create `app/modules/admin_workflow/` folder
2. ✅ Create all 6 Python files with complete code:
   - `__init__.py`
   - `models.py` (SQLAlchemy models)
   - `schemas.py` (Pydantic schemas)
   - `agent_client.py` (HTTP client)
   - `services.py` (Business logic)
   - `routes.py` (API endpoints)
3. ✅ Create database migration file
4. ✅ Update `main.py` to register routes
5. ✅ Update `app/core/config.py` with agent URLs
6. ✅ Update `.env.local` with environment variables
7. ✅ Update CORS configuration

### Step 5: After Implementation

Run these commands:

```powershell
# 1. Run database migrations
alembic upgrade head

# 2. Start the backend server
uvicorn main:app --reload --port 8000

# 3. Test the API
curl http://localhost:8000/docs
```

### Step 6: Test with Frontend

1. Make sure backend is running on port 8000
2. Start your frontend: `cd F:\ClimaSyncAI_frontend && npm run dev`
3. Navigate to: `http://localhost:3000/admin/create-account`
4. Create an admin account
5. Test the complete workflow

---

## 🔧 What If Something Goes Wrong?

### Issue: AI doesn't understand the prompt
**Solution:** Break it down:
1. First ask: "Create the admin_workflow module structure"
2. Then: "Implement models.py with these specifications: [paste models section]"
3. Continue file by file

### Issue: Import errors
**Solution:** The AI might need to know your existing imports. Show it:
```python
# Show existing files
from app.core.database import Base, get_db
from app.core.auth import get_current_user, create_access_token
from app.core.config import settings
```

### Issue: Database connection errors
**Solution:** Make sure your `.env.local` has correct database URL:
```env
DATABASE_URL=postgresql://user:password@localhost:5432/climasync_db
```

---

## 📚 Reference Files

If the AI needs more details, point it to these files in your frontend repo:

1. **Complete API Specification:**
   - `BACKEND_API_IMPLEMENTATION.md`

2. **Detailed Code Examples:**
   - `BACKEND_IMPLEMENTATION_CODE.md`
   - `BACKEND_SERVICES_ROUTES.md`

3. **Testing Guide:**
   - `DEPLOYMENT_TESTING_GUIDE.md`

4. **Quick Reference:**
   - `QUICK_REFERENCE.md`

---

## ✅ Success Checklist

After implementation, verify:

- [ ] `app/modules/admin_workflow/` folder exists with 6 files
- [ ] Database migration created in `migrations/versions/`
- [ ] Routes registered in `main.py`
- [ ] Config updated in `app/core/config.py`
- [ ] Environment variables in `.env.local`
- [ ] `alembic upgrade head` runs successfully
- [ ] Backend starts without errors
- [ ] API docs accessible at `http://localhost:8000/docs`
- [ ] Can create admin account via API
- [ ] Frontend can connect and create admin account

---

## 🚀 Quick Start Command

If you want to do it all in one go, just copy this entire message to your AI:

```
I'm in F:\ClimasyncAI_backend. Please read and implement everything in BACKEND_IMPLEMENTATION_PROMPT.md. 

After implementation:
1. Show me what files were created
2. Show me what files were modified
3. Tell me what commands to run next

My existing project structure:
- FastAPI backend
- SQLAlchemy ORM
- Alembic migrations
- JWT authentication already implemented
- Database connection already configured
- Modules in app/modules/ (auth, admin, disasters, etc.)

Please follow the existing code patterns and use the existing utilities.
```

---

## 💡 Pro Tips

1. **Review Before Running:** Ask the AI to show you the code before creating files
2. **One Module at a Time:** If you prefer control, implement one file at a time
3. **Test Incrementally:** Test each endpoint as it's created
4. **Use Git:** Commit after each successful step
5. **Keep Frontend Running:** Test integration as you build

---

## 🆘 Need Help?

If you encounter issues:
1. Check the error message
2. Look at `DEPLOYMENT_TESTING_GUIDE.md` troubleshooting section
3. Verify your database is running
4. Check that all environment variables are set
5. Make sure ports 8000, 8002, 8003 are available

---

**You're all set! Just copy the prompt and let the AI do the work.** 🎉
