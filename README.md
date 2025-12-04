# AI-Assisted Knowledge Quiz 🧠

A fun quiz app that uses AI (Google Gemini) to create questions and give you feedback!

---

## 1. Project Setup & Demo

### How to Run

1. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Add your Gemini API key:**
   - Open `.env` file
   - Put your key: `GEMINI_API_KEY=your_key_here`
   - Get key from: https://aistudio.google.com/app/apikey

3. **Start the app:**
   ```bash
   python app.py
   ```

4. **Open in browser:**
   - Go to: http://localhost:5000

---

## 2. Problem Understanding

**Goal:** Make a quiz app where AI creates the questions.

**What it does:**
- Shows 6 fun topics to pick from
- AI makes 5 questions for your topic
- You answer and see your score
- AI gives you a nice message at the end

**Assumptions:**
- User has internet for AI calls
- User has a Gemini API key

---

## 3. AI Prompts

**For Questions:**
```
Create 5 multiple-choice questions about [topic].
Return as JSON with question, 4 options, and correct answer.
```

**For Feedback:**
```
Score: X/5 on [topic] quiz.
Write short encouraging sentences (max 50 words).
```

**API Calls per Quiz:** 2 requests (1 for questions, 1 for feedback)

---

## 4. Project Structure

```
ai-quiz/
├── app.py                 # Main Flask app (routes & logic)
├── requirements.txt       # Python packages needed
├── .env                   # Your API key (secret!)
│
├── services/
│   └── ai_service.py      # Talks to Gemini AI
│
├── templates/             # HTML pages
│   ├── base.html          # Common layout
│   ├── index.html         # Topic selection
│   ├── loading.html       # Loading screen
│   ├── quiz.html          # Quiz questions
│   ├── question.html      # Single question
│   ├── results.html       # Score & feedback
│   └── error.html         # Error page
│
└── static/
    └── styles.css         # All the pretty styling
```

**Tech Used:**
- Python Flask (backend)
- HTMX (smooth page updates)
- Google Gemini AI (questions & feedback)
- CSS (dark theme with animations)

---

## 5. Screenshots

### Home Screen
Pick from 6 topics: Wellness, Tech, Space, History, Science, Pop Culture

### Quiz Screen  
- See question with 4 options
- Click to select answer
- Navigate with Next/Previous buttons

### Results Screen
- Your score (e.g., 4/5 = 80%)
- See which answers were right/wrong
- Get AI feedback message

---

## 6. Known Issues

| Issue | How to Fix |
|-------|------------|
| AI sometimes slow | Fallback questions are used if AI fails |
| Need internet | Required for Gemini API |

**Future Improvements:**
- Add more topics
- Save high scores
- Add difficulty levels

---

## 7. Bonus Features ✨

- **Dark Mode:** Beautiful dark theme with purple accents
- **Animations:** Smooth transitions between screens
- **Loading Spinner:** Fun animation while AI thinks
- **Glassmorphism:** Modern frosted glass effects
- **Responsive:** Works on phone and computer

---

## Quick Commands

```bash
# Install
pip install -r requirements.txt

# Run
python app.py

# Open
http://localhost:5000
```

---

Made with ❤️ using Python, Flask, HTMX & Google Gemini AI
