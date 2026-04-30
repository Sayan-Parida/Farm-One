# 🔴 Red Lines in VS Code - How to Fix

## The Problem

VS Code is showing red underlines on imports because it's using **Python 3.13** (global) instead of **Python 3.11.9** (in venv where modules are installed).

## ✅ Solution - Follow These Steps EXACTLY

### Step 1: Click on Python Version in Bottom Right

Look at the **bottom right corner** of VS Code. You should see something like:
```
Python 3.13.x 64-bit
```

**Click on it!**

### Step 2: Select the Virtual Environment

A menu will appear at the top. Look for and select:
```
Python 3.11.9 64-bit ('venv': venv)
```

Or the full path:
```
.\backend\venv\Scripts\python.exe
```

### Step 3: Reload Window

1. Press `Ctrl + Shift + P`
2. Type: `Developer: Reload Window`
3. Press Enter

**The red lines should disappear!** ✅

## Alternative Method (If Above Doesn't Work)

### Close and Reopen VS Code from Terminal

1. **Close VS Code completely**
2. **Open PowerShell** in the backend folder
3. **Run these commands:**
   ```powershell
   cd C:\Users\Sayan\Downloads\Farmone-main\Farmone-main\backend
   .\venv\Scripts\Activate.ps1
   code ..
   ```

This opens VS Code with the venv already activated.

## Verify It Worked

After selecting the interpreter, check:

1. **Bottom right corner** should show: `Python 3.11.9 ('venv': venv)`
2. **Red lines should be gone**
3. **Hover over imports** - should show module info, not errors

## Still Not Working?

If red lines persist after trying both methods:

1. **Install Pylance extension** (if not installed)
2. **Restart VS Code completely**
3. **Check the Output panel:**
   - View → Output
   - Select "Python" from dropdown
   - Look for any errors

## Important Note

⚠️ **The red lines are ONLY a visual/linting issue**

Your code is **actually working fine**:
- ✅ Server is running
- ✅ All endpoints work
- ✅ Tests pass

The red lines don't affect functionality - they're just annoying! Once you select the correct interpreter, they'll disappear.
