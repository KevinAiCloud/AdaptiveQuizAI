"""Flask routes for AdaptiveQuiz — all application endpoints."""
import json
import os
from datetime import datetime, timedelta, date

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, session, jsonify,
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import or_

from sqlalchemy.exc import OperationalError, DisconnectionError

from backend.models import User, Question, QuizResult, TopicMastery, MistakeBank, db
from backend.ai_engine import AIEngine
from backend.services import extract_text_from_pdf, extract_text_from_image, clean_text, generate_otp, send_otp_email

routes_bp = Blueprint("routes", __name__)


def safe_commit(max_retries=2):
    """Commit with automatic retry on dropped DB connections."""
    for attempt in range(max_retries + 1):
        try:
            db.session.commit()
            return
        except (OperationalError, DisconnectionError) as e:
            db.session.rollback()
            if attempt < max_retries:
                print(f"DB connection lost, retrying commit (attempt {attempt + 1})…")
                db.session.remove()          # dispose of the dead session
            else:
                raise

# Initialize AI engine (lazy — key resolved at first use)
ai = AIEngine()


def is_allowed():
    """Check if user is logged in or guest."""
    return current_user.is_authenticated or session.get("is_guest")


# ═══════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════

@routes_bp.route("/health")
def health_check():
    key = os.getenv("OPENROUTER_API_KEY", "")
    return jsonify({
        "status": "ok",
        "openrouter_key_set": bool(key),
        "openrouter_key_preview": f"...{key[-6:]}" if len(key) > 6 else "NOT SET",
        "ai_client_ready": ai.client is not None,
    })


# ═══════════════════════════════════════════════════════════════════
# LANDING & AUTH
# ═══════════════════════════════════════════════════════════════════

@routes_bp.route("/")
def index():
    return render_template("landing.html")


@routes_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("routes.dashboard"))

    if request.method == "POST":
        login_id = request.form.get("login_id", "").strip()
        password = request.form.get("password", "")

        user = User.query.filter(
            or_(User.email == login_id, User.username == login_id)
        ).first()

        if user and user.check_password(password):
            login_user(user)
            session["is_guest"] = False
            return redirect(url_for("routes.dashboard"))

        flash("Invalid credentials. Please try again.", "danger")
    return render_template("login.html")


@routes_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return redirect(url_for("routes.signup"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("routes.signup"))

        existing = User.query.filter(
            or_(User.email == email, User.username == username)
        ).first()
        if existing:
            flash("Username or email already taken!", "danger")
            return redirect(url_for("routes.signup"))

        # Generate and send OTP
        otp = generate_otp()
        sent = send_otp_email(email, otp)

        if not sent:
            flash("Could not send verification email. Please try again.", "danger")
            return redirect(url_for("routes.signup"))

        # Store pending signup in session
        session["pending_signup"] = {
            "username": username,
            "email": email,
            "password": password,
            "otp": otp,
            "created_at": datetime.utcnow().isoformat(),
        }

        flash(f"Verification code sent to {email}! Check your inbox.", "success")
        return redirect(url_for("routes.verify_otp"))

    return render_template("signup.html")


@routes_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    pending = session.get("pending_signup")
    if not pending:
        flash("No pending signup. Please sign up first.", "warning")
        return redirect(url_for("routes.signup"))

    if request.method == "POST":
        entered_otp = request.form.get("otp", "").strip()

        # Check OTP expiry (10 minutes)
        created_at = datetime.fromisoformat(pending["created_at"])
        if datetime.utcnow() - created_at > timedelta(minutes=10):
            session.pop("pending_signup", None)
            flash("OTP expired. Please sign up again.", "danger")
            return redirect(url_for("routes.signup"))

        if entered_otp == pending["otp"]:
            # OTP correct — create the user
            new_user = User(email=pending["email"], username=pending["username"])
            new_user.set_password(pending["password"])
            db.session.add(new_user)
            safe_commit()
            session.pop("pending_signup", None)

            flash("Email verified! Account created. Please log in.", "success")
            return redirect(url_for("routes.login"))
        else:
            flash("Invalid OTP. Please try again.", "danger")

    return render_template("verify_otp.html", email=pending.get("email", ""))


@routes_bp.route("/resend-otp", methods=["POST"])
def resend_otp():
    pending = session.get("pending_signup")
    if not pending:
        flash("No pending signup found.", "warning")
        return redirect(url_for("routes.signup"))

    otp = generate_otp()
    sent = send_otp_email(pending["email"], otp)

    if sent:
        pending["otp"] = otp
        pending["created_at"] = datetime.utcnow().isoformat()
        session["pending_signup"] = pending
        flash("New verification code sent!", "success")
    else:
        flash("Could not resend OTP. Please try again.", "danger")

    return redirect(url_for("routes.verify_otp"))


@routes_bp.route("/guest-login")
def guest_login():
    session.clear()
    session["is_guest"] = True
    session["username"] = "Guest Explorer"
    session["streak"] = 0
    flash("Welcome, Guest! Your progress won't be saved.", "info")
    return redirect(url_for("routes.dashboard"))


@routes_bp.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("routes.login"))


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@routes_bp.route("/dashboard")
def dashboard():
    if not is_allowed():
        return redirect(url_for("routes.login"))

    is_guest = session.get("is_guest", False)
    username = session.get("username", "Guest")
    correct_total = 0
    total_q = 0
    mistake_count = 0
    user_streak = 0
    mastery_data = []

    if not is_guest and current_user.is_authenticated:
        username = current_user.username
        results_list = QuizResult.query.filter_by(user_id=current_user.id).all()
        correct_total = sum(r.score for r in results_list)
        total_q = sum(r.total_questions for r in results_list)
        mistake_count = MistakeBank.query.filter_by(user_id=current_user.id).count()
        user_streak = current_user.streak or 0
        mastery_data = TopicMastery.query.filter_by(user_id=current_user.id).all()

    fun_fact = "Learning is a superpower — keep going! 🚀"

    return render_template(
        "dashboard.html",
        username=username,
        is_guest=is_guest,
        correct_total=correct_total,
        incorrect_total=max(0, total_q - correct_total),
        mistake_count=mistake_count,
        streak=user_streak,
        fun_fact=fun_fact,
        topic_mastery=mastery_data,
        total_quizzes=len(QuizResult.query.filter_by(
            user_id=current_user.id).all()) if not is_guest and current_user.is_authenticated else 0,
    )


# ═══════════════════════════════════════════════════════════════════
# QUIZ GENERATION & PLAY
# ═══════════════════════════════════════════════════════════════════

@routes_bp.route("/generate", methods=["POST", "GET"])
def handle_generation():
    if not is_allowed():
        return redirect(url_for("routes.login"))

    source_type = request.form.get("source_type") or request.args.get("source_type")
    count = int(request.form.get("count", 5))
    q_format = request.form.get("q_format", "mcq")
    difficulty = request.form.get("difficulty", "medium")
    mastery_label = "General"
    q_ids = []

    try:
        content = ""
        if source_type == "mistake":
            # Re-quiz from mistake bank
            if session.get("is_guest"):
                flash("Guest users don't have a Mistake Bank!", "warning")
                return redirect(url_for("routes.dashboard"))
            mistakes = MistakeBank.query.filter_by(user_id=current_user.id).limit(count).all()
            if not mistakes:
                flash("Your Mistake Bank is empty! 🎉", "info")
                return redirect(url_for("routes.dashboard"))
            for m in mistakes:
                new_q = Question(
                    question_text=m.question_text,
                    options_json=m.options_json,
                    correct_answer=m.correct_answer,
                    explanation=m.explanation,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    topic=m.topic,
                )
                db.session.add(new_q)
                db.session.flush()
                q_ids.append(new_q.id)
            safe_commit()
            mastery_label = "Mistake Review"
        else:
            if source_type == "pdf":
                f = request.files.get("pdf_file")
                if f and f.filename:
                    content = extract_text_from_pdf(f)
                    mastery_label = f"PDF: {f.filename}"
            elif source_type == "text":
                content = request.form.get("raw_text", "")
                mastery_label = "Custom Text"
            elif source_type == "topic":
                mastery_label = request.form.get("topic_name", "General")
                content = f"Generate questions about: {mastery_label}"
            elif source_type == "image":
                f = request.files.get("image_file")
                if f and f.filename:
                    content = extract_text_from_image(f)
                    mastery_label = f"Image: {f.filename}"

            content = clean_text(content)
            if not content:
                flash("No content to generate questions from!", "danger")
                return redirect(url_for("routes.dashboard"))

            # Check API key before attempting generation
            if not ai.client:
                flash("OPENROUTER_API_KEY is not configured. Please add your API key to the .env file.", "danger")
                return redirect(url_for("routes.dashboard"))

            questions = ai.generate_questions(content, count, q_format, difficulty)
            if not questions:
                flash("AI couldn't generate questions. Try different content or check your API key.", "danger")
                return redirect(url_for("routes.dashboard"))

            for q_data in questions:
                new_q = Question(
                    question_text=q_data.get("question", ""),
                    options_json=json.dumps(q_data.get("options", {})),
                    correct_answer=q_data.get("correct_answer", ""),
                    explanation=q_data.get("explanation", ""),
                    difficulty=difficulty,
                    q_type=q_format,
                    user_id=current_user.id if current_user.is_authenticated else None,
                    topic=mastery_label,
                )
                db.session.add(new_q)
                db.session.flush()
                q_ids.append(new_q.id)
            safe_commit()

        if not q_ids:
            flash("No questions generated.", "warning")
            return redirect(url_for("routes.dashboard"))

        # Store quiz session
        session.update({
            "active_questions": q_ids,
            "current_idx": 0,
            "score": 0,
            "quiz_topic": mastery_label,
            "quiz_difficulty": difficulty,
            "user_answers": [],
        })
        return redirect(url_for("routes.quiz_page", q_id=q_ids[0]))

    except Exception as e:
        db.session.rollback()
        print(f"Generation error: {e}")
        flash(f"Error generating quiz: {str(e)}", "danger")
        return redirect(url_for("routes.dashboard"))


@routes_bp.route("/quiz/<int:q_id>")
def quiz_page(q_id):
    if not is_allowed():
        return redirect(url_for("routes.login"))

    question = Question.query.get_or_404(q_id)
    options = json.loads(question.options_json) if question.options_json else {}
    q_list = session.get("active_questions", [])
    current = session.get("current_idx", 0)

    return render_template(
        "quiz.html",
        question=question,
        options=options,
        current=current + 1,
        total=len(q_list),
        topic=session.get("quiz_topic", "Quiz"),
    )


@routes_bp.route("/submit-answer", methods=["POST"])
def submit_answer():
    if not is_allowed():
        return redirect(url_for("routes.login"))

    q_id = int(request.form.get("question_id"))
    user_answer = request.form.get("answer", "")
    question = Question.query.get_or_404(q_id)

    is_correct = user_answer.strip().upper() == question.correct_answer.strip().upper()

    # Save answer
    ans_list = session.get("user_answers", [])
    ans_list.append({
        "question": question.question_text,
        "user_answer": user_answer,
        "correct_answer": question.correct_answer,
        "is_correct": is_correct,
        "explanation": question.explanation,
        "options": json.loads(question.options_json) if question.options_json else {},
    })
    session["user_answers"] = ans_list

    if is_correct:
        session["score"] = session.get("score", 0) + 1
    elif not session.get("is_guest") and current_user.is_authenticated:
        # Add to mistake bank
        mistake = MistakeBank(
            user_id=current_user.id,
            question_text=question.question_text,
            correct_answer=question.correct_answer,
            options_json=question.options_json,
            topic=session.get("quiz_topic", "General"),
            explanation=question.explanation,
        )
        db.session.add(mistake)
        safe_commit()

    # Next question or results
    session["current_idx"] = session.get("current_idx", 0) + 1
    q_list = session.get("active_questions", [])

    if session["current_idx"] < len(q_list):
        return redirect(url_for("routes.quiz_page", q_id=q_list[session["current_idx"]]))
    return redirect(url_for("routes.results"))


# ═══════════════════════════════════════════════════════════════════
# RESULTS
# ═══════════════════════════════════════════════════════════════════

@routes_bp.route("/results")
def results():
    score = session.get("score", 0)
    user_answers = session.get("user_answers", [])
    total = len(user_answers)
    topic = session.get("quiz_topic", "Quiz")
    difficulty = session.get("quiz_difficulty", "medium")
    accuracy = (score / total * 100) if total > 0 else 0

    history_labels = []
    history_scores = []
    is_guest = session.get("is_guest", False)
    ai_insight = ""

    try:
        if not is_guest and current_user.is_authenticated:
            # Save result
            new_res = QuizResult(
                user_id=current_user.id,
                score=score,
                total_questions=total,
                topic=topic,
                difficulty=difficulty,
                timestamp=datetime.utcnow(),
            )
            db.session.add(new_res)

            # Update streak
            today = date.today()
            if current_user.last_quiz_date:
                last = current_user.last_quiz_date
                if last == today:
                    pass  # same day
                elif last == today - timedelta(days=1):
                    current_user.streak += 1
                else:
                    current_user.streak = 1
            else:
                current_user.streak = 1
            current_user.last_quiz_date = today

            # Update topic mastery
            mastery = TopicMastery.query.filter_by(
                user_id=current_user.id, topic=topic
            ).first()
            if not mastery:
                mastery = TopicMastery(
                    user_id=current_user.id, topic=topic,
                    correct_count=0, total_count=0,
                )
                db.session.add(mastery)
            mastery.correct_count += score
            mastery.total_count += total
            safe_commit()

            # History for chart
            past = QuizResult.query.filter_by(
                user_id=current_user.id
            ).order_by(QuizResult.timestamp.asc()).all()
            for r in past[-7:]:
                history_labels.append(r.timestamp.strftime("%d %b"))
                history_scores.append(
                    int(r.score / r.total_questions * 100) if r.total_questions else 0
                )

            # AI insight on mistakes
            wrong = [a for a in user_answers if not a["is_correct"]]
            if wrong:
                ai_insight = ai.generate_performance_insight(wrong, topic)
        else:
            history_labels = ["Now"]
            history_scores = [int(accuracy)]

    except Exception as e:
        db.session.rollback()
        print(f"Results save error: {e}")

    return render_template(
        "results.html",
        score=score,
        total=total,
        accuracy=accuracy,
        user_answers=user_answers,
        is_guest=is_guest,
        topic=topic,
        history_labels=json.dumps(history_labels),
        history_scores=json.dumps(history_scores),
        ai_insight=ai_insight,
    )


# ═══════════════════════════════════════════════════════════════════
# LIBRARY & MISTAKES
# ═══════════════════════════════════════════════════════════════════

@routes_bp.route("/library")
@login_required
def library():
    if session.get("is_guest"):
        flash("Library is for registered users only!", "info")
        return redirect(url_for("routes.signup"))

    results = QuizResult.query.filter_by(
        user_id=current_user.id
    ).order_by(QuizResult.timestamp.desc()).all()
    return render_template("library.html", results=results)


@routes_bp.route("/review-mistakes")
@login_required
def review_mistakes():
    mistakes = MistakeBank.query.filter_by(user_id=current_user.id).all()
    processed = []
    for m in mistakes:
        processed.append({
            "id": m.id,
            "question": m.question_text,
            "correct_answer": m.correct_answer,
            "options": json.loads(m.options_json) if m.options_json else {},
            "topic": m.topic,
            "explanation": m.explanation,
        })
    return render_template("review.html", mistakes=processed)


@routes_bp.route("/delete-mistake/<int:m_id>", methods=["POST"])
@login_required
def delete_mistake(m_id):
    m = MistakeBank.query.get_or_404(m_id)
    if m.user_id == current_user.id:
        db.session.delete(m)
        safe_commit()
        flash("Mistake removed!", "success")
    return redirect(url_for("routes.review_mistakes"))
