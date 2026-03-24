"""AI Engine — OpenRouter LLM integration for quiz generation & study aids."""
import json
import os
import time
from openai import OpenAI


class AIEngine:
    """Handles all AI operations via OpenRouter."""

    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self._client = None
        self.MODEL = "meta-llama/llama-3.3-70b-instruct"
        self.FAST_MODEL = "meta-llama/llama-3.1-8b-instruct"

    @property
    def client(self):
        """Lazy-init OpenRouter client (OpenAI-compatible) so env vars are loaded first."""
        if self._client is None:
            key = self.api_key or os.getenv("OPENROUTER_API_KEY", "")
            if key:
                self._client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=key,
                )
                print(f"[AIEngine] OpenRouter client initialized (key: ...{key[-6:]})")
            else:
                print("[AIEngine] WARNING: No OPENROUTER_API_KEY found!")
        return self._client

    def _request(self, func, *args, **kwargs):
        """Retry wrapper for API calls."""
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                print(f"AI attempt {attempt+1} failed: {e}")
                if attempt < 2:
                    time.sleep(1.5)
        return None

    @staticmethod
    def _extract_json(text):
        """Extract JSON from a response that might be wrapped in markdown code blocks."""
        import re
        # Try raw parse first
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Try extracting from ```json ... ``` blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
        # Try finding first { ... } block
        match = re.search(r'(\{[\s\S]*\})', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    # ── Quiz Generation ──────────────────────────────────────────────
    def generate_questions(self, content, count=5, q_format="mcq", difficulty="medium"):
        """Generate quiz questions from content via OpenRouter."""
        if not self.client:
            print("[AIEngine] No client — cannot generate questions")
            return []
        if not content:
            print("[AIEngine] No content provided")
            return []

        print(f"[AIEngine] Generating {count} {q_format} questions, difficulty={difficulty}")

        diff_guide = {
            "easy": "simple recall and basic understanding",
            "medium": "application and analysis level",
            "hard": "synthesis, evaluation, and critical thinking"
        }.get(difficulty, "application and analysis level")

        system_prompt = (
            "You are an expert academic examiner. Output ONLY valid JSON. "
            'Structure: {"questions": [{"question": "...", "options": '
            '{"A": "...", "B": "...", "C": "...", "D": "..."}, '
            '"correct_answer": "A", "explanation": "..."}]}'
        )

        if q_format == "tf":
            format_rule = (
                "Generate True/False questions. "
                "'options' must be {\"A\": \"True\", \"B\": \"False\"}. "
                "'correct_answer' must be 'A' or 'B'."
            )
        else:
            format_rule = (
                "Generate MCQs with 4 options (A, B, C, D). "
                "'correct_answer' must be the key letter (A, B, C, or D)."
            )

        user_prompt = (
            f"TASK: Generate exactly {count} {q_format.upper()} questions.\n"
            f"DIFFICULTY: {difficulty} — focus on {diff_guide}.\n"
            f"RULE: {format_rule}\n"
            f"CONTENT:\n{content[:4000]}"
        )

        try:
            completion = self._request(
                self.client.chat.completions.create,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.MODEL,
                temperature=0.3,
            )
            if completion:
                raw = completion.choices[0].message.content
                print(f"[AIEngine] Got response ({len(raw)} chars)")
                data = self._extract_json(raw)
                if not data:
                    print(f"[AIEngine] Failed to parse JSON from response")
                    return []
                questions = data.get("questions", [])
                print(f"[AIEngine] Parsed {len(questions)} questions")
                return questions
            else:
                print("[AIEngine] No completion returned after retries")
        except Exception as e:
            print(f"[AIEngine] Question generation error: {e}")
            import traceback
            traceback.print_exc()
        return []

    # ── Study Material Generation ────────────────────────────────────
    def generate_study_material(self, content):
        """Generate study aids: shorthand notes, mnemonics, ELI10, flashcards."""
        if not self.client:
            return self._fallback_study()

        prompt = (
            f"Analyze the following content and return a JSON object with:\n"
            f'- "shorthand_notes": list of concise bullet-point notes\n'
            f'- "eli10": a simple "Explain Like I\'m 10" paragraph\n'
            f'- "mnemonic_story": a creative memory story using key concepts\n'
            f'- "flashcards": list of {{"front": "term", "back": "definition"}}\n'
            f'- "key_concepts": list of 5 most important concepts\n\n'
            f"CONTENT:\n{content[:3500]}"
        )
        try:
            response = self._request(
                self.client.chat.completions.create,
                model=self.MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant. Output ONLY valid JSON."},
                    {"role": "user", "content": prompt},
                ],
            )
            if response:
                data = self._extract_json(response.choices[0].message.content)
                if data:
                    return data
        except Exception:
            pass
        return self._fallback_study()

    def _fallback_study(self):
        return {
            "shorthand_notes": ["AI study material unavailable."],
            "eli10": "Content analysis requires an AI key.",
            "mnemonic_story": "",
            "flashcards": [],
            "key_concepts": [],
        }

    # ── Performance Insight ──────────────────────────────────────────
    def generate_performance_insight(self, mistakes, topic):
        """AI-powered feedback on quiz mistakes."""
        if not self.client or not mistakes:
            return f"Great job on {topic}! Keep exploring related concepts."

        mistake_text = "\n".join(
            [f"- {m.get('question', '')}" for m in mistakes[:5]]
        )
        prompt = (
            f"A student took a quiz on '{topic}' and struggled with:\n"
            f"{mistake_text}\n\n"
            "Give 2-3 lines of constructive feedback:\n"
            "1. Identify the weak sub-topic\n"
            "2. Give an actionable study tip"
        )
        try:
            completion = self._request(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": prompt}],
                model=self.FAST_MODEL,
                temperature=0.7,
            )
            if completion:
                return completion.choices[0].message.content
        except Exception:
            pass
        return f"Review the key concepts of {topic} and try again!"

    # ── Fun Fact ─────────────────────────────────────────────────────
    def get_fun_fact(self):
        """Get a random tech/science fun fact."""
        if not self.client:
            return "AI can process data millions of times faster than the human brain! 🧠"
        try:
            completion = self._request(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": "Share one amazing, short tech or science fact in one sentence."}],
                model=self.FAST_MODEL,
            )
            if completion:
                return completion.choices[0].message.content
        except Exception:
            pass
        return "Neural networks are inspired by the structure of the human brain! 🧠"

    # ── Topic Detection ──────────────────────────────────────────────
    def detect_topic(self, content):
        """Identify the main topic of given content."""
        if not self.client:
            return "General Study"
        try:
            completion = self._request(
                self.client.chat.completions.create,
                messages=[{"role": "user", "content": f"Identify the main subject of this text. Return ONLY the topic name in 2-4 words:\n{content[:1000]}"}],
                model=self.FAST_MODEL,
            )
            if completion:
                return completion.choices[0].message.content.strip().replace('"', '')
        except Exception:
            pass
        return "General Study"
