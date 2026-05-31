# sid_agent.py - FIXED CARE MODE (No sarcasm, pure support)
import hashlib
import re
import random
import os
import sys
import logging
import json
from collections import defaultdict
from typing import List, Dict
from datetime import datetime, timedelta

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

from dotenv import load_dotenv
load_dotenv()

logging.getLogger("urllib3").setLevel(logging.CRITICAL)

_file_handler = logging.FileHandler("sid.log", encoding="utf-8")
_stream_handler = logging.StreamHandler(sys.stdout)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[_file_handler, _stream_handler],
)
log = logging.getLogger("SID")

from sentence_transformers import SentenceTransformer
from groq import Groq

class SimpleStateGraph:
    def __init__(self, state_schema=None):
        self.nodes = {}
        self.edges = {}
        self.entry_point = None
    def add_node(self, name, func):
        self.nodes[name] = func
        return self
    def add_edge(self, from_node, to_node):
        self.edges[from_node] = to_node
        return self
    def set_entry_point(self, node):
        self.entry_point = node
        return self
    def compile(self):
        return self
    def invoke(self, state):
        current = self.entry_point
        while current in self.nodes:
            if current == "END":
                break
            state = self.nodes[current](state)
            current = self.edges.get(current, "END")
        return state

END = "END"
StateGraph = SimpleStateGraph

class MemoryStore:
    def __init__(self):
        log.info("Loading memory...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        self.memory_file = "sid_memory.json"
        self.memories = self._load_memories()
        log.info("Memory ready")
    def _load_memories(self):
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    def _save_memories(self):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memories, f, indent=2)
    def store(self, user_id: str, user_msg: str, sid_response: str):
        if user_id not in self.memories:
            self.memories[user_id] = []
        self.memories[user_id].append({
            "user_msg": user_msg,
            "sid_response": sid_response,
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.memories[user_id]) > 100:
            self.memories[user_id] = self.memories[user_id][-100:]
        self._save_memories()
    def retrieve(self, user_id: str, query: str) -> List[str]:
        if user_id not in self.memories:
            return []
        return [m["user_msg"] for m in self.memories[user_id][-5:]]

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = "llama-3.3-70b-versatile"
    MAX_RESPONSE_LENGTH = 200
    MAX_INPUT_LENGTH = 500
    CHAOS_TEMPERATURE = 1.15
    CARE_TEMPERATURE = 0.7
    CONVERSATION_HISTORY = 4
    RATE_LIMIT_MESSAGES = 30
    RATE_LIMIT_WINDOW_MIN = 1
    ICALL_HELPLINE = "9152987821"
    AASRA_HELPLINE = "9820466726"

config = Config()

class RateLimiter:
    def __init__(self):
        self._log: Dict[str, List[datetime]] = defaultdict(list)
    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        window = now - timedelta(minutes=config.RATE_LIMIT_WINDOW_MIN)
        self._log[user_id] = [t for t in self._log[user_id] if t > window]
        if len(self._log[user_id]) >= config.RATE_LIMIT_MESSAGES:
            return False
        self._log[user_id].append(now)
        return True

class SafetyFilters:
    SELF_HARM_PATTERNS = [r"\b(kill myself|suicide|end my life)\b"]
    @classmethod
    def has_self_harm(cls, text: str) -> bool:
        for pattern in cls.SELF_HARM_PATTERNS:
            if re.search(pattern, text.lower()):
                return True
        return False

# ============================================================
# SEPARATE PROMPTS FOR EACH MODE
# ============================================================

# CHAOS MODE - Savage, witty, 120-150 chars
CHAOS_PROMPT = """You are SID in CHAOS mode. Savage, witty, hilarious. Roast them but make it funny.

Rules:
- 120-150 characters only
- One sentence
- Use sarcasm and dark humor
- Make them laugh

User: {input}

Your savage response:"""

# CARE MODE - Pure support, no sarcasm, no jokes
CARE_PROMPT = """You are SID in CARE mode. Pure support. No sarcasm. No jokes. Just genuine help.

Rules:
- 100-150 characters only
- Be kind, warm, and helpful
- Offer practical solutions
- No emojis unless appropriate
- Be genuinely caring

User: {input}

Your supportive response:"""

# Agent State
class AgentState:
    def __init__(self, **kwargs):
        self.user_id = kwargs.get('user_id', '')
        self.user_input = kwargs.get('user_input', '')
        self.mode = kwargs.get('mode', 'chaos')
        self.safety_triggered = kwargs.get('safety_triggered', False)
        self.rate_limited = kwargs.get('rate_limited', False)
        self.memory_context = kwargs.get('memory_context', [])
        self.recent_history = kwargs.get('recent_history', [])
        self.response = kwargs.get('response', '')
    def get(self, key, default=None):
        return getattr(self, key, default)
    def __getitem__(self, key):
        return getattr(self, key)
    def __setitem__(self, key, value):
        setattr(self, key, value)

class SIDAgent:
    def __init__(self):
        self.memory = MemoryStore()
        self.safety = SafetyFilters()
        self.rate_limiter = RateLimiter()
        self._sessions: Dict[str, List[Dict]] = defaultdict(list)
        log.info("Loading Groq...")
        self.client = Groq(api_key=config.GROQ_API_KEY)
        log.info("🔥 SID READY - CHAOS/SEPARATE MODES 🔥")
        self.graph = self._build_graph()
    
    def _build_graph(self):
        workflow = StateGraph()
        workflow.add_node("check_safety", self._check_safety)
        workflow.add_node("check_rate", self._check_rate)
        workflow.add_node("recall_memory", self._recall_memory)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("remember_chat", self._remember_chat)
        workflow.set_entry_point("check_safety")
        workflow.add_edge("check_safety", "check_rate")
        workflow.add_edge("check_rate", "recall_memory")
        workflow.add_edge("recall_memory", "generate_response")
        workflow.add_edge("generate_response", "remember_chat")
        workflow.add_edge("remember_chat", END)
        return workflow.compile()
    
    def _check_safety(self, state):
        state["safety_triggered"] = self.safety.has_self_harm(state["user_input"])
        return state
    
    def _check_rate(self, state):
        state["rate_limited"] = not self.rate_limiter.is_allowed(state["user_id"])
        return state
    
    def _recall_memory(self, state):
        if not state["safety_triggered"] and not state["rate_limited"]:
            state["memory_context"] = self.memory.retrieve(state["user_id"], state["user_input"])
            state["recent_history"] = self._sessions[state["user_id"]][-config.CONVERSATION_HISTORY * 2:]
        return state
    
    def _generate_response(self, state):
        if state["safety_triggered"]:
            state["response"] = f"Call {config.ICALL_HELPLINE}"
            return state
        
        if state["rate_limited"]:
            responses = ["Chill 💀", "Too fast 😂", "Slow down 🔥"]
            state["response"] = random.choice(responses)
            return state
        
        # Build history
        history_lines = []
        for turn in state.get("recent_history", [])[-4:]:
            role = "You" if turn["role"] == "user" else "SID"
            history_lines.append(f"{role}: {turn['content']}")
        history_text = "\n".join(history_lines[-2:]) if history_lines else "None"
        
        # Choose prompt based on mode
        if state["mode"] == "chaos":
            user_prompt = CHAOS_PROMPT.format(input=state["user_input"])
            temperature = config.CHAOS_TEMPERATURE
            system_msg = """You are SID in CHAOS mode. Savage, witty, hilarious. 
120-150 characters only. One sentence. Roast them but make it funny.
Never be mean-spirited, always clever and entertaining."""
        else:
            user_prompt = CARE_PROMPT.format(input=state["user_input"])
            temperature = config.CARE_TEMPERATURE
            system_msg = """You are SID in CARE mode. Pure support. No sarcasm. No jokes.
100-150 characters only. Be kind, warm, and genuinely helpful.
Offer practical solutions. Use emojis sparingly. Just care."""
        
        try:
            completion = self.client.chat.completions.create(
                model=config.GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=60,
                top_p=0.95,
            )
            response_text = completion.choices[0].message.content.strip()
            response_text = response_text.strip('"').strip("'")
            
            char_count = len(response_text)
            log.info(f"{'🔥' if state['mode']=='chaos' else '🤗'} {state['user_id']} | '{state['user_input'][:20]}' → {char_count} chars")
            
        except Exception as e:
            log.error(f"Groq error: {e}")
            response_text = ""
        
        # Mode-specific fallbacks
        if not response_text:
            if state["mode"] == "chaos":
                fallbacks = [
                    "Your life is a comedy show, I'm just the critic 💀",
                    "Even Google can't find your brain 🔥",
                    "Congratulations, you've peaked at disappointment 🎉"
                ]
            else:
                fallbacks = [
                    "I hear you. Want to talk more?",
                    "That sounds tough. I'm here for you.",
                    "Take a deep breath. We'll figure this out."
                ]
            response_text = random.choice(fallbacks)
        
        # Hard limit on length
        if len(response_text) > 160:
            response_text = response_text[:157] + "..."
        
        state["response"] = response_text
        return state
    
    def _remember_chat(self, state):
        if state["safety_triggered"] or state["rate_limited"]:
            return state
        uid = state["user_id"]
        self._sessions[uid].append({"role": "user", "content": state["user_input"]})
        self._sessions[uid].append({"role": "assistant", "content": state["response"]})
        if len(self._sessions[uid]) > 40:
            self._sessions[uid] = self._sessions[uid][-40:]
        self.memory.store(uid, state["user_input"], state["response"])
        return state
    
    def chat(self, user_id: str, message: str, mode: str = "chaos") -> str:
        message = message.strip()
        if not message:
            return "Say something 💀"
        if len(message) > config.MAX_INPUT_LENGTH:
            return f"Too long 💀"
        
        initial = AgentState(
            user_id=user_id,
            user_input=message,
            mode=mode,
            safety_triggered=False,
            rate_limited=False,
            memory_context=[],
            recent_history=[],
            response="",
        )
        final = self.graph.invoke(initial)
        return final["response"]

def main():
    print("\n" + "=" * 50)
    print("🔥 SID - CHAOS & CARE SEPARATE 🔥")
    print("=" * 50)
    
    if not config.GROQ_API_KEY:
        print("\n❌ GROQ_API_KEY not set in .env")
        return
    
    sid = SIDAgent()
    name = input("\nYour name? ").strip() or "friend"
    mode = "chaos"
    print("\n🔥 CHAOS MODE - Savage roasts")
    print("🤗 Type /care for support mode\n")
    
    while True:
        try:
            user_input = input(f"[{mode.upper()}] {name}: ").strip()
            
            if user_input.lower() == "/quit":
                print("\nSID: Later 💀\n")
                break
            if user_input.lower() == "/care":
                mode = "care"
                print("\n🤗 CARE MODE - Pure support, no sarcasm\n")
                continue
            if user_input.lower() == "/chaos":
                mode = "chaos"
                print("\n🔥 CHAOS MODE - Savage roasts\n")
                continue
            if not user_input:
                continue
            
            response = sid.chat(name, user_input, mode)
            print(f"\n{'🔥' if mode=='chaos' else '🤗'} SID: {response}\n")
            
        except KeyboardInterrupt:
            print("\n\nSID: Coward 💀\n")
            break

if __name__ == "__main__":
    main()