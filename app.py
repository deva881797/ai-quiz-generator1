"""
AI-Assisted Knowledge Quiz Application
Flask backend with HTMX for seamless interactions.
Uses Google Gemini API for AI-powered quiz generation.
"""

import os
import secrets
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
from services.ai_service import get_ai_service

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))

# AI Service configuration - Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')

# Available quiz topics with metadata
TOPICS = [
    {
        "id": "wellness",
        "name": "Wellness",
        "icon": "🧘",
        "description": "Health, mindfulness & self-care",
        "gradient": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
    },
    {
        "id": "tech-trends",
        "name": "Tech Trends",
        "icon": "💻",
        "description": "AI, blockchain & emerging tech",
        "gradient": "linear-gradient(135deg, #f093fb 0%, #f5576c 100%)"
    },
    {
        "id": "space",
        "name": "Space Exploration",
        "icon": "🚀",
        "description": "Cosmos, planets & astronomy",
        "gradient": "linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)"
    },
    {
        "id": "history",
        "name": "World History",
        "icon": "📜",
        "description": "Ancient civilizations & events",
        "gradient": "linear-gradient(135deg, #fa709a 0%, #fee140 100%)"
    },
    {
        "id": "science",
        "name": "Science & Nature",
        "icon": "🔬",
        "description": "Biology, physics & chemistry",
        "gradient": "linear-gradient(135deg, #a8edea 0%, #fed6e3 100%)"
    },
    {
        "id": "pop-culture",
        "name": "Pop Culture",
        "icon": "🎬",
        "description": "Movies, music & entertainment",
        "gradient": "linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%)"
    }
]


def get_topic_by_id(topic_id: str) -> dict:
    """Get topic metadata by ID."""
    for topic in TOPICS:
        if topic["id"] == topic_id:
            return topic
    return TOPICS[0]


@app.route('/')
def index():
    """Screen 1: Topic selection page."""
    # Clear any existing quiz session
    session.pop('quiz_data', None)
    session.pop('current_question', None)
    session.pop('answers', None)
    
    return render_template('index.html', topics=TOPICS)


@app.route('/start-quiz', methods=['POST'])
def start_quiz():
    """Initialize quiz and show loading screen."""
    topic_id = request.form.get('topic', 'wellness')
    topic = get_topic_by_id(topic_id)
    
    # Store topic in session
    session['selected_topic'] = topic
    session['current_question'] = 0
    session['answers'] = [-1] * 5  # -1 means not answered
    
    return render_template('loading.html', topic=topic)


@app.route('/generate-quiz/<topic_id>')
def generate_quiz(topic_id: str):
    """Generate quiz questions using AI (called via HTMX)."""
    topic = get_topic_by_id(topic_id)
    
    try:
        # Get AI service and generate questions
        ai_service = get_ai_service(GEMINI_API_KEY, GEMINI_MODEL)
        questions = ai_service.generate_quiz(topic["name"])
        
        # Store questions in session
        session['quiz_data'] = {
            'topic': topic,
            'questions': questions
        }
        session['current_question'] = 0
        session['answers'] = [-1] * len(questions)
        
        # Redirect to quiz page
        return render_template('quiz.html', 
                             topic=topic,
                             questions=questions,
                             current_index=0,
                             answers=session['answers'])
        
    except ConnectionError as e:
        return render_template('error.html', 
                             error="Cannot connect to Gemini API",
                             message="Please check your GEMINI_API_KEY in the .env file.",
                             topic=topic)
    except Exception as e:
        return render_template('error.html',
                             error="Quiz Generation Failed",
                             message=str(e),
                             topic=topic)


@app.route('/navigate', methods=['POST'])
def navigate():
    """Handle question navigation and answer selection."""
    quiz_data = session.get('quiz_data')
    if not quiz_data:
        return redirect(url_for('index'))
    
    # Get form data
    direction = request.form.get('direction', 'next')
    current_index = int(request.form.get('current_index', 0))
    selected_answer = request.form.get('selected_answer')
    
    # Update answer if provided
    answers = session.get('answers', [-1] * 5)
    if selected_answer is not None and selected_answer != '':
        answers[current_index] = int(selected_answer)
        session['answers'] = answers
    
    # Calculate new index
    questions = quiz_data['questions']
    if direction == 'next':
        new_index = min(current_index + 1, len(questions) - 1)
    elif direction == 'prev':
        new_index = max(current_index - 1, 0)
    elif direction == 'submit':
        return redirect(url_for('results'))
    else:
        new_index = current_index
    
    session['current_question'] = new_index
    
    return render_template('quiz.html',
                         topic=quiz_data['topic'],
                         questions=questions,
                         current_index=new_index,
                         answers=answers)


@app.route('/select-answer', methods=['POST'])
def select_answer():
    """Handle answer selection via HTMX (partial update)."""
    quiz_data = session.get('quiz_data')
    if not quiz_data:
        return '', 204
    
    current_index = int(request.form.get('current_index', 0))
    selected_answer = request.form.get('selected_answer')
    
    # Update answer
    answers = session.get('answers', [-1] * 5)
    if selected_answer is not None:
        answers[current_index] = int(selected_answer)
        session['answers'] = answers
    
    questions = quiz_data['questions']
    
    return render_template('question.html',
                         question=questions[current_index],
                         question_index=current_index,
                         selected_answer=answers[current_index],
                         total_questions=len(questions))


@app.route('/results')
def results():
    """Screen 4: Show results with AI-generated feedback."""
    quiz_data = session.get('quiz_data')
    answers = session.get('answers', [])
    
    if not quiz_data:
        return redirect(url_for('index'))
    
    questions = quiz_data['questions']
    topic = quiz_data['topic']
    
    # Calculate score
    score = 0
    results_data = []
    
    for i, question in enumerate(questions):
        user_answer = answers[i] if i < len(answers) else -1
        is_correct = user_answer == question['correct_index']
        if is_correct:
            score += 1
        
        results_data.append({
            'question': question['question'],
            'options': question['options'],
            'user_answer': user_answer,
            'correct_index': question['correct_index'],
            'is_correct': is_correct
        })
    
    # Generate AI feedback
    try:
        ai_service = get_ai_service(GEMINI_API_KEY, GEMINI_MODEL)
        feedback = ai_service.generate_feedback(score, len(questions), topic['name'], questions, answers)
    except Exception:
        # Fallback feedback
        percentage = (score / len(questions)) * 100
        if percentage >= 80:
            feedback = f"Excellent work! You've shown outstanding knowledge of {topic['name']}."
        elif percentage >= 60:
            feedback = f"Good job! You have a solid understanding of {topic['name']}."
        elif percentage >= 40:
            feedback = f"Nice effort! Keep exploring {topic['name']} to improve."
        else:
            feedback = f"Thanks for trying! Every attempt helps you learn more about {topic['name']}."
    
    return render_template('results.html',
                         topic=topic,
                         score=score,
                         total=len(questions),
                         percentage=int((score / len(questions)) * 100),
                         results=results_data,
                         feedback=feedback)


@app.route('/api/health')
def health_check():
    """Health check endpoint."""
    gemini_status = "configured" if GEMINI_API_KEY else "missing api key"
    
    return jsonify({
        "status": "healthy",
        "gemini": gemini_status,
        "model": GEMINI_MODEL
    })


if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
