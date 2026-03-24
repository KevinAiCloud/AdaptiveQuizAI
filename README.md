<p align="center">
  <h1 align="center">🧠 AdaptiveQuiz</h1>
  <p align="center">
    <strong>AI-Powered Adaptive Quiz Platform</strong><br/>
    <em>Transform any content into personalised, intelligent assessments</em>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
    <img src="https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask"/>
    <img src="https://img.shields.io/badge/Llama_3.3-AI_Powered-6C5CE7?style=for-the-badge&logo=meta&logoColor=white" alt="AI"/>
    <img src="https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel"/>
  </p>
</p>

---

An intelligent quiz platform that leverages **Llama 3.3 70B** (via OpenRouter) to generate context-aware questions, track learning progress, and deliver AI-powered performance insights — all wrapped in a stunning **glassmorphic dark UI**.

---

## ✨ Features

<table>
  <tr>
    <td>🎯 <strong>AI Quiz Generation</strong></td>
    <td>Generate MCQ & True/False questions from topics, raw text, or PDF uploads</td>
  </tr>
  <tr>
    <td>📊 <strong>Adaptive Difficulty</strong></td>
    <td>Questions adapt based on your performance — Easy, Medium, or Hard</td>
  </tr>
  <tr>
    <td>📧 <strong>Email OTP Verification</strong></td>
    <td>Secure signup with 6-digit email verification codes</td>
  </tr>
  <tr>
    <td>🔥 <strong>Streak Tracking</strong></td>
    <td>Daily login streaks with gamification to keep you consistent</td>
  </tr>
  <tr>
    <td>🔍 <strong>Mistake Bank</strong></td>
    <td>Every wrong answer is saved — re-quiz yourself on weak areas</td>
  </tr>
  <tr>
    <td>📈 <strong>Smart Analytics</strong></td>
    <td>Score history charts, topic mastery bars, and AI-generated insights</td>
  </tr>
  <tr>
    <td>⚡ <strong>AI Study Hub</strong></td>
    <td>Auto-generated notes, mnemonics, ELI10 explanations, and flashcards</td>
  </tr>
  <tr>
    <td>👤 <strong>Guest Mode</strong></td>
    <td>Try the full experience without creating an account</td>
  </tr>
  <tr>
    <td>📄 <strong>Client-Side PDF</strong></td>
    <td>PDFs are parsed in-browser with pdf.js — no file size limits</td>
  </tr>
  <tr>
    <td>🎨 <strong>Glassmorphic UI</strong></td>
    <td>Modern dark-themed design with glass effects and gradient animations</td>
  </tr>
</table>

---

## 🛠️ Tech Stack

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND          Jinja2 · Vanilla CSS · pdf.js        │
│                    Chart.js · Inter Font                 │
├─────────────────────────────────────────────────────────┤
│  BACKEND           Flask 3.0 · Flask-Login              │
│                    Flask-SQLAlchemy · Werkzeug           │
├─────────────────────────────────────────────────────────┤
│  AI ENGINE         OpenRouter API · Llama 3.3 70B       │
│                    Llama 3.1 8B (fast tasks)            │
├─────────────────────────────────────────────────────────┤
│  DATABASE          PostgreSQL (prod) · SQLite (dev)     │
├─────────────────────────────────────────────────────────┤
│  SERVICES          Gmail SMTP (OTP) · pypdf             │
├─────────────────────────────────────────────────────────┤
│  DEPLOYMENT        Vercel (Python Serverless)           │
└─────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
AdaptiveQuiz/
│
├── main.py                      # Flask app factory & entry point
├── requirements.txt             # Python dependencies
├── vercel.json                  # Vercel serverless config
├── .env.example                 # Environment variables template
│
├── backend/
│   ├── __init__.py              # Package marker
│   ├── models.py                # SQLAlchemy models (User, Question, QuizResult, etc.)
│   ├── ai_engine.py             # OpenRouter LLM integration (Llama 3.3)
│   ├── services.py              # PDF extraction, OTP email, text processing
│   └── routes.py                # All Flask routes & API endpoints
│
└── frontend/
    ├── static/css/
    │   └── style.css            # Glassmorphic design system (589 lines)
    └── templates/
        ├── base.html            # Base layout — navbar, flash messages
        ├── landing.html         # Hero landing page
        ├── login.html           # Login form
        ├── signup.html          # Registration form
        ├── verify_otp.html      # OTP verification
        ├── dashboard.html       # Stats, mastery bars, quiz generator
        ├── quiz.html            # Active quiz — one question at a time
        ├── results.html         # Score card, charts, AI insight
        ├── library.html         # Quiz history table
        ├── review.html          # Mistake Bank review
        ├── study_hub.html       # AI Study Hub input
        └── study_hub_result.html # Study material output
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- An [OpenRouter API Key](https://openrouter.ai/keys) — free credits available
- A Gmail account with an [App Password](https://myaccount.google.com/apppasswords) — for OTP emails

### 1️⃣ Clone & Install

```bash
git clone <your-repo-url>
cd AdaptiveQuiz
python -m venv venv
```

```bash
# Activate virtual environment
venv\Scripts\activate          # Windows
source venv/bin/activate       # macOS / Linux
```

```bash
python -m pip install -r requirements.txt
```

### 2️⃣ Configure Environment

```bash
copy .env.example .env         # Windows
cp .env.example .env           # macOS / Linux
```

Open `.env` and fill in your keys :

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
SECRET_KEY=your-random-secret-key
SMTP_EMAIL=your_gmail@gmail.com
SMTP_PASSWORD=your-gmail-app-password
DATABASE_URL=                  # Leave empty for SQLite (local dev)
```

### 3️⃣ Run

```bash
python main.py
```

🎉 Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** and start quizzing!

---

## 🌐 Deploying to Vercel

1. Push your code to a GitHub repository
2. Import the repo on [vercel.com](https://vercel.com)
3. Add these **Environment Variables** in the Vercel dashboard:

   | Variable | Value |
   |---|---|
   | `OPENROUTER_API_KEY` | Your OpenRouter API key |
   | `SECRET_KEY` | A strong random string |
   | `SMTP_EMAIL` | Gmail address for OTP emails |
   | `SMTP_PASSWORD` | Gmail App Password |
   | `DATABASE_URL` | PostgreSQL connection string (e.g. from [neon.tech](https://neon.tech)) |

4. **Deploy!** 🚀

---

## 🧪 How It Works

```
📤 Upload Content          →    🧠 AI Processes           →    📝 Take Quiz
(Topic / Text / PDF)            (Llama 3.3 generates           (Answer adaptive
                                 questions & options)            questions)

                            →    🏆 Get Results
                                 (Score, charts, AI insights,
                                  mistakes saved for review)
```

### Quiz Flow
1. **Choose a source** — enter a topic, paste text, or upload a PDF
2. **Configure** — select question count (5–20), format (MCQ/True-False), difficulty
3. **AI generates** — Llama 3.3 creates contextual questions with explanations
4. **Answer & learn** — one question at a time with a progress bar
5. **Review results** — performance chart, AI learning insight, detailed answer review
6. **Improve** — revisit mistakes in the Mistake Bank, re-quiz on weak areas

---

## 🗄️ Database Models

| Model | Purpose |
|---|---|
| `User` | Authentication, streak tracking, preferences |
| `Question` | AI-generated questions with options, answers, explanations |
| `QuizResult` | Historical scores per quiz session |
| `TopicMastery` | Cumulative per-topic correct/total counts |
| `MistakeBank` | Wrong answers saved for targeted re-quizzing |

---

## 📸 Screenshots -

> *Coming soon — run the app locally to see the glassmorphic UI in action!*

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
