## Project Overview

This project is a web-based reading support system designed for users with reading difficulties, such as students with dyslexia.

The main goals of the system are:
Help users understand complex text more easily
Reduce reading stress
Provide a clearer and more controllable reading experience

The system supports:
Text input and display
Content summary
Reading assistance (chunking, structure)
Custom reading settings (font, colour)
Text-to-speech (TTS)

## Project Structure

This project uses a front-end and back-end separated architecture.

project-root/
│
├── frontend/     # Frontend (Vue 3 + Vite)
├── backend/      # Backend (FastAPI)
├── database/     # Database (not used yet)
├── docs/         # Documentation (optional)
├── docker/       # Deployment (future use)

Note: Both frontend and backend must run at the same time.

## Tech Stack
Frontend
Vue 3
Vite
JavaScript
Backend
Python 3.11
FastAPI
Uvicorn
Others
REST API
Environment variables (.env)

## Backend Structure
backend/
│
├── main.py           # Entry point
├── config.py         # Configuration
│
├── core/             # Core settings
│   └── database.py
│
├── routes/           # API layer
│   └── api.py
│
├── services/         # Business logic (core)
├── models/           # Data models
├── repositories/     # Database access
├── utils/            # Utilities
│
└── venv/             # Virtual environment (do not commit,this is already added to .gitignore.)

## Simple explanation:
routes: API endpoints
services: main logic
models: data structure
repositories: database operations

## Frontend Structure
frontend/
│
├── src/
│   ├── pages/        
│   ├── components/   
│   ├── services/     
│   ├── router/       
│   ├── assets/       
│   ├── App.vue       
│   └── main.js       
│
├── public/
├── node_modules/     # do not commit
└── vite.config.js

## Frontend & Backend
Frontend: http://localhost:5173
Backend: http://127.0.0.1:8000

# Example API:
http://127.0.0.1:8000/api/xxx

### First Setup

If this is your first time running the project, follow these steps.

1. Install Requirements

Make sure you have:

Python 3.11
Node.js 18 or above
Git

Check installation

Windows:
python --version
node -v
npm -v

macOS:
python3 --version
node -v
npm -v

2. Get Latest Code

Make sure you are on your branch:

git pull origin dev

Or use Git GUI to pull from dev.

3. Run Backend
a. Go to backend:
cd backend

b. Create virtual environment (only once)
Windows:
python -m venv venv

macOS:
python3 -m venv venv

###### c. Activate environment (every time) !!!!!!!
Windows:
venv\Scripts\activate

macOS:
source venv/bin/activate

d. You should see (venv) in terminal

e. Install dependencies:
pip install -r requirements.txt

f. Set environment variable
Create .env in backend folder:

GEMINI_API_KEY=your_api_key

g. Start backend
uvicorn main:app --reload

Open:
http://127.0.0.1:8000/docs

4. Run Frontend

⚠️Use a new terminal

a. cd frontend

b. Install:
npm install

c.Run:
npm run dev

Open:
http://localhost:5173

5. How It Works

You must run both:
Backend (FastAPI)
Frontend (Vue)

Flow:
Frontend → API request → Backend → Response → Display

## Common Issues

1. Backend not working

Check venv is activated
Check dependencies installed

2. Frontend cannot get data

Check backend is running
Check API URL

3. API key error
Check .env file
Development Rules
Python Environment

###### Always activate venv before coding !!!
# Do not install new packages without notice
# Update requirements.txt if new packages are added

# Git Branch Naming
Module	          Example
frontend	    feature/frontend-homepage
backend	        feature/backend-api
ai	            feature/ai-text
database	    feature/db-schema
deploy	        chore/deploy

# Sync with dev

Run in your branch:
git add .
git commit -m "save progress"
git pull origin dev

This will merge changes, not overwrite your code.

## Summary

To run the project:

Start backend
Start frontend
Open browser