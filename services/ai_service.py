"""
AI Service Module - Google Gemini API Integration
Handles quiz question generation and personalized feedback generation.
Uses the official google-generativeai library.
"""

import json
import re
import time
from typing import List, Dict, Optional

import google.generativeai as genai


class AIService:
    """Service class for interacting with Google Gemini API."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model
        self.max_retries = 3
        self.retry_delay = 2
        self.debug = True
        
        # Configure the API
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)
    
    def _log(self, message: str):
        """Simple debug logger."""
        if self.debug:
            print(f"[AI Service] {message}")
    
    def _make_request(self, prompt: str) -> Optional[str]:
        """Make a request to Gemini API with error handling."""
        try:
            self._log(f"Making request to Gemini ({self.model_name})...")
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2000
                )
            )
            
            if response.text:
                self._log(f"Received response ({len(response.text)} chars): {response.text[:200]}...")
                return response.text
            
            self._log("No valid response from Gemini")
            return None
            
        except Exception as e:
            self._log(f"Error: {e}")
            raise Exception(f"Error communicating with Gemini: {str(e)}")
    
    def _extract_json(self, text: str) -> Optional[Dict]:
        """Extract JSON from AI response with multiple parsing strategies."""
        self._log("Attempting to extract JSON from response...")
        
        def normalize_questions(questions_list):
            """Normalize question format to use correct_index."""
            normalized = []
            for i, q in enumerate(questions_list):
                if isinstance(q, dict):
                    nq = {
                        "id": q.get("id", i + 1),
                        "question": q.get("question", ""),
                        "options": q.get("options", []),
                        "correct_index": q.get("correct_index", q.get("correctIndex", 0))
                    }
                    normalized.append(nq)
            return normalized
        
        # Strategy 1: Direct JSON parse - handle both array and object format
        try:
            parsed = json.loads(text.strip())
            
            if isinstance(parsed, list) and len(parsed) > 0:
                self._log("Strategy 1 (direct array parse) succeeded!")
                return {"questions": normalize_questions(parsed)}
            
            if isinstance(parsed, dict) and "questions" in parsed:
                self._log("Strategy 1 (direct object parse) succeeded!")
                return {"questions": normalize_questions(parsed["questions"])}
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Find JSON in text (array or object format)
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # Match JSON in code blocks first
            r'```\s*([\s\S]*?)\s*```',  # Match any code block
            r'\[[\s\S]*\]',  # Match array format [...]
            r'\{[\s\S]*\}',  # Match object format {...}
        ]
        
        for i, pattern in enumerate(json_patterns):
            matches = re.findall(pattern, text)
            for match in matches:
                try:
                    clean_match = match.strip()
                    
                    # For array format
                    if clean_match.startswith('['):
                        last_bracket = clean_match.rfind(']')
                        if last_bracket != -1:
                            clean_match = clean_match[:last_bracket + 1]
                        parsed = json.loads(clean_match)
                        if isinstance(parsed, list) and len(parsed) > 0:
                            self._log(f"Strategy 2 (array pattern {i}) succeeded!")
                            return {"questions": normalize_questions(parsed)}
                    
                    # For object format
                    if not clean_match.startswith('['):
                        if not clean_match.startswith('{'):
                            json_start = clean_match.find('{')
                            if json_start != -1:
                                clean_match = clean_match[json_start:]
                        last_brace = clean_match.rfind('}')
                        if last_brace != -1:
                            clean_match = clean_match[:last_brace + 1]
                        parsed = json.loads(clean_match)
                        if isinstance(parsed, dict) and "questions" in parsed:
                            self._log(f"Strategy 2 (object pattern {i}) succeeded!")
                            return {"questions": normalize_questions(parsed["questions"])}
                except json.JSONDecodeError as e:
                    self._log(f"Pattern {i} failed: {e}")
                    continue
        
        self._log("All JSON extraction strategies failed!")
        return None
    
    def generate_quiz(self, topic: str) -> List[Dict]:
        """Generate 5 multiple choice questions about the given topic."""
        
        prompt = f"""You are a quiz generator. Create 5 multiple-choice questions about {topic}.

IMPORTANT RULES:
1. Check all spelling and grammar carefully
2. End questions with "?" not "."
3. Return ONLY valid JSON - no extra text before or after
4. Each question needs exactly 4 options
5. correctIndex must be 0, 1, 2, or 3

Return this exact JSON format:
[
  {{
    "question": "Your question here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correctIndex": 0
  }}
]

Generate 5 interesting and educational questions about {topic}:"""

        last_error = None
        
        for attempt in range(self.max_retries):
            self._log(f"Attempt {attempt + 1}/{self.max_retries} for topic: {topic}")
            
            try:
                response = self._make_request(prompt)
                
                if response:
                    parsed = self._extract_json(response)
                    
                    if parsed and "questions" in parsed:
                        questions = parsed["questions"]
                        
                        valid_questions = []
                        for q in questions[:5]:
                            if self._validate_question(q):
                                valid_questions.append(q)
                                self._log(f"Valid question: {q.get('question', '')[:50]}...")
                        
                        if len(valid_questions) >= 3:
                            while len(valid_questions) < 5:
                                valid_questions.append(self._generate_fallback_question(topic, len(valid_questions) + 1))
                            self._log(f"Success! Returning {len(valid_questions)} questions")
                            return valid_questions[:5]
                        else:
                            self._log(f"Only {len(valid_questions)} valid questions, need at least 3")
                
                last_error = "Could not parse valid questions from AI response"
                
            except Exception as e:
                last_error = str(e)
                self._log(f"Error on attempt {attempt + 1}: {last_error}")
            
            if attempt < self.max_retries - 1:
                self._log(f"Waiting {self.retry_delay}s before retry...")
                time.sleep(self.retry_delay)
        
        self._log(f"All attempts failed. Using fallback questions. Last error: {last_error}")
        return self._generate_fallback_questions(topic)
    
    def _validate_question(self, question: Dict) -> bool:
        """Validate a question dictionary has all required fields and quality."""
        if "question" not in question or not question["question"]:
            return False
        
        q_text = question["question"].strip()
        
        if len(q_text) < 15:
            self._log(f"Rejected: question too short - {q_text}")
            return False
        
        low_quality_patterns = [
            "abbreviation for", "acronym for", "what does the word",
            "spell ", "how do you spell", "define the word",
            "synonym for", "antonym for",
            "q1", "q2", "q3", "q4", "q5", "question text", "your question",
        ]
        q_lower = q_text.lower()
        for pattern in low_quality_patterns:
            if pattern in q_lower:
                self._log(f"Rejected: low quality pattern '{pattern}'")
                return False
        
        if "options" not in question:
            return False
        if not isinstance(question["options"], list) or len(question["options"]) != 4:
            return False
        
        options = question["options"]
        if all(len(str(opt).strip()) <= 2 for opt in options):
            self._log(f"Rejected: options too short")
            return False
        
        correct_idx = question.get("correct_index", question.get("correctIndex", None))
        if correct_idx is None:
            return False
        
        try:
            idx = int(correct_idx)
            if idx < 0 or idx > 3:
                return False
        except (ValueError, TypeError):
            return False
        
        return True
    
    def _generate_fallback_question(self, topic: str, question_id: int) -> Dict:
        """Generate a single fallback question."""
        fallback_questions = {
            "Wellness": [
                {"question": "Which of these is recommended for better sleep?", "options": ["Caffeine before bed", "Regular sleep schedule", "Screen time", "Heavy meals"], "correct_index": 1},
                {"question": "What is mindfulness?", "options": ["Sleeping more", "Present moment awareness", "Multitasking", "Speed reading"], "correct_index": 1},
                {"question": "How much water should adults drink daily?", "options": ["1 cup", "8 cups", "20 cups", "No water needed"], "correct_index": 1},
                {"question": "Which activity reduces stress?", "options": ["Meditation", "Overworking", "Skipping meals", "Isolation"], "correct_index": 0},
                {"question": "What's a benefit of regular exercise?", "options": ["Fatigue", "Better mood", "Weight gain", "Insomnia"], "correct_index": 1},
            ],
            "Tech Trends": [
                {"question": "What does AI stand for?", "options": ["Artificial Intelligence", "Automated Internet", "Advanced Integration", "Auto Interface"], "correct_index": 0},
                {"question": "What is cloud computing?", "options": ["Weather prediction", "Remote data storage and processing", "Airplane technology", "Photography"], "correct_index": 1},
                {"question": "What is blockchain?", "options": ["A game", "Distributed ledger technology", "Social media", "Email service"], "correct_index": 1},
                {"question": "What does IoT mean?", "options": ["Internet of Things", "Input of Text", "Internal Operations", "Image Optimization"], "correct_index": 0},
                {"question": "What is machine learning?", "options": ["Robot building", "AI learning from data", "Computer repair", "Typing practice"], "correct_index": 1},
            ],
            "Space Exploration": [
                {"question": "Which planet is known as the Red Planet?", "options": ["Venus", "Mars", "Jupiter", "Saturn"], "correct_index": 1},
                {"question": "What is the closest star to Earth?", "options": ["Polaris", "Sirius", "The Sun", "Alpha Centauri"], "correct_index": 2},
                {"question": "Who was the first human in space?", "options": ["Neil Armstrong", "Yuri Gagarin", "Buzz Aldrin", "John Glenn"], "correct_index": 1},
                {"question": "What is a light-year?", "options": ["Time unit", "Distance unit", "Speed unit", "Weight unit"], "correct_index": 1},
                {"question": "Which planet has the most moons?", "options": ["Earth", "Mars", "Saturn", "Mercury"], "correct_index": 2},
            ],
            "World History": [
                {"question": "In which year did World War II end?", "options": ["1943", "1945", "1947", "1950"], "correct_index": 1},
                {"question": "Who was the first President of the United States?", "options": ["Abraham Lincoln", "Thomas Jefferson", "George Washington", "John Adams"], "correct_index": 2},
                {"question": "Which ancient wonder was located in Egypt?", "options": ["Colossus of Rhodes", "Great Pyramid of Giza", "Hanging Gardens", "Temple of Artemis"], "correct_index": 1},
                {"question": "The Renaissance began in which country?", "options": ["France", "England", "Italy", "Spain"], "correct_index": 2},
                {"question": "Who discovered America in 1492?", "options": ["Vasco da Gama", "Ferdinand Magellan", "Christopher Columbus", "Amerigo Vespucci"], "correct_index": 2},
            ],
            "Science & Nature": [
                {"question": "What is the chemical symbol for water?", "options": ["O2", "H2O", "CO2", "NaCl"], "correct_index": 1},
                {"question": "What is the largest organ in the human body?", "options": ["Heart", "Liver", "Skin", "Brain"], "correct_index": 2},
                {"question": "What gas do plants absorb from the air?", "options": ["Oxygen", "Nitrogen", "Carbon Dioxide", "Hydrogen"], "correct_index": 2},
                {"question": "What is the hardest natural substance?", "options": ["Gold", "Iron", "Diamond", "Platinum"], "correct_index": 2},
                {"question": "How many bones are in the adult human body?", "options": ["106", "206", "306", "406"], "correct_index": 1},
            ],
            "Pop Culture": [
                {"question": "Which band performed 'Bohemian Rhapsody'?", "options": ["The Beatles", "Queen", "Led Zeppelin", "Pink Floyd"], "correct_index": 1},
                {"question": "What year was the first iPhone released?", "options": ["2005", "2007", "2009", "2010"], "correct_index": 1},
                {"question": "Who directed the movie 'Titanic'?", "options": ["Steven Spielberg", "James Cameron", "Christopher Nolan", "Martin Scorsese"], "correct_index": 1},
                {"question": "Which streaming platform produces 'Stranger Things'?", "options": ["Amazon Prime", "Hulu", "Netflix", "Disney+"], "correct_index": 2},
                {"question": "What social media app is known for short videos?", "options": ["Facebook", "Twitter", "TikTok", "LinkedIn"], "correct_index": 2},
            ],
        }
        
        default_questions = [
            {"question": f"What is a key aspect of {topic}?", "options": ["Knowledge", "Ignorance", "Confusion", "None"], "correct_index": 0},
            {"question": f"Why is {topic} important?", "options": ["Personal growth", "No reason", "Waste of time", "Harmful"], "correct_index": 0},
            {"question": f"How can one learn about {topic}?", "options": ["Reading and practice", "Sleeping", "Ignoring it", "Running away"], "correct_index": 0},
            {"question": f"What skill helps in {topic}?", "options": ["Critical thinking", "Laziness", "Procrastination", "Denial"], "correct_index": 0},
            {"question": f"Who can benefit from {topic}?", "options": ["Everyone", "No one", "Only experts", "Only children"], "correct_index": 0},
        ]
        
        topic_questions = fallback_questions.get(topic, default_questions)
        idx = (question_id - 1) % len(topic_questions)
        
        return {"id": question_id, **topic_questions[idx]}
    
    def _generate_fallback_questions(self, topic: str) -> List[Dict]:
        """Generate fallback questions when AI fails."""
        return [self._generate_fallback_question(topic, i) for i in range(1, 6)]
    
    def generate_feedback(self, score: int, total: int, topic: str, questions: List[Dict], answers: List[int]) -> str:
        """Generate SHORT personalized feedback based on quiz performance."""
        percentage = (score / total) * 100 if total > 0 else 0
        
        prompt = f"""Score: {score}/{total} on {topic} quiz.
Write short encouraging sentences (max 50 words). No emojis."""

        try:
            response = self._make_request(prompt)
            if response:
                feedback = response.strip().strip('"\'')
                
                # Split into words
                words = feedback.split()

                # Keep only first 50 words
                if len(words) > 50:
                    words = words[:50]

                # Rejoin
                feedback = " ".join(words)

                return feedback
        except Exception:
            pass

        
        if percentage >= 80:
            return f"Excellent! You really know your {topic}."
        elif percentage >= 60:
            return f"Good job! Solid understanding of {topic}."
        elif percentage >= 40:
            return f"Nice try! Keep learning about {topic}."
        else:
            return f"Keep going! {topic} takes practice."


# Singleton instance
_ai_service = None


def get_ai_service(api_key: str, model: str = "gemini-2.0-flash") -> AIService:
    """Get or create the AI service singleton."""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService(api_key, model)
    return _ai_service
