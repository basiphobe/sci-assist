#!/usr/bin/env python3
"""
Generate daily engagement messages through the bot's internal API.

This script communicates with the running bot to post daily messages,
ensuring they only happen when the bot is healthy and running.
All messages go through the bot's normal message handling.
"""

import asyncio
import sys
import json
import aiohttp
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timedelta

# Add the src directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Add the RAG system to the Python path
RAG_SYSTEM_PATH = Path(__file__).parent.parent / "ajsgptrag"
sys.path.insert(0, str(RAG_SYSTEM_PATH))

from discord_llm_bot.config import load_config
from discord_llm_bot.llm.client import LLMClient
from discord_llm_bot.llm.models import ChatMessage, ChatRequest, MessageRole
from discord_llm_bot.utils.logging import setup_logging, get_logger

try:
    from src.rag_system import WikipediaRAG
except ImportError:
    WikipediaRAG = None


class BotMediatedDailyMessageGenerator:
    """Generate daily messages through the bot's internal API."""
    
    def __init__(self):
        """Initialize the generator."""
        self.config = None
        self.llm_client = None
        self.rag_system = None
        self.logger = None
        self.bot_api_key = None
        self.bot_api_port = 8765
    
    async def setup(self):
        """Set up the LLM client and get bot API key."""
        # Load configuration (same as main bot)
        self.config = load_config()
        
        # Set up minimal logging to avoid interfering with JSON output
        import logging
        logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
        self.logger = logging.getLogger(__name__)
        
        # Create LLM client for message generation only
        self.llm_client = LLMClient(self.config.llm)
        
        # Initialize RAG system for varied content retrieval
        if WikipediaRAG is not None:
            try:
                import os
                os.environ['CUDA_VISIBLE_DEVICES'] = '0'
                os.environ['RAG_DEVICE'] = 'cpu'
                self.rag_system = WikipediaRAG()
                self.logger.info("RAG system initialized for daily messages")
            except Exception as e:
                self.logger.warning(f"RAG system unavailable for daily messages: {e}")
                self.rag_system = None
        else:
            self.logger.info("RAG system not importable, generating without RAG context")
        
        # Get the bot's API key from the health check endpoint
        await self._get_bot_api_key()
        
    async def cleanup(self):
        """Clean up resources."""
        if self.llm_client:
            await self.llm_client.close()
    
    async def _get_bot_api_key(self):
        """Get the bot's API key from the project file."""
        api_key_file = Path("/opt/sci-assist/.bot-api-key")
        
        if not api_key_file.exists():
            raise RuntimeError("Bot API key file not found - is the bot running?")
        
        try:
            self.bot_api_key = api_key_file.read_text().strip()
            self.logger.info("Successfully loaded bot API key")
        except Exception as e:
            raise RuntimeError(f"Failed to read bot API key: {e}")
    
    async def check_bot_health(self) -> bool:
        """Check if the bot is running and healthy."""
        if not self.bot_api_key:
            return False
            
        try:
            headers = {'Authorization': f'Bearer {self.bot_api_key}'}
            async with aiohttp.ClientSession() as session:
                async with session.get(f'http://localhost:{self.bot_api_port}/health', 
                                     headers=headers, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('bot_ready', False)
                    return False
        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False
    
    def _get_recent_messages(self) -> List[str]:
        """Get recent daily messages to avoid repetition.
        
        Returns ALL messages from the history file (up to 30 entries) to
        give the LLM the widest possible view of what's already been posted.
        """
        history_file = Path(__file__).parent / "daily_message_history.json"
        
        if not history_file.exists():
            return []
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Return all messages in history (file already capped at 30 entries)
            return [entry['message'] for entry in history if entry.get('message')]
        except (json.JSONDecodeError, KeyError):
            return []
    
    def _get_rag_context(self, category: str) -> Optional[str]:
        """
        Query the RAG system for relevant content to seed message generation.
        
        Uses category-specific search queries to retrieve varied Wikipedia
        content about SCI, accessibility, and assistive technology.
        
        Returns:
            Formatted context string from RAG, or None if unavailable.
        """
        if self.rag_system is None:
            return None
        
        import random
        
        # Category-specific RAG queries to retrieve varied, relevant content
        rag_queries = {
            "fact": [
                "spinal cord injury anatomy and physiology",
                "history of wheelchair development and accessibility",
                "spinal cord injury statistics and epidemiology",
                "Americans with Disabilities Act accessibility milestones",
                "Paralympic sports history and achievements",
                "assistive technology history and development",
                "spinal cord injury levels and classification",
                "accessibility standards and universal design",
            ],
            "tip": [
                "pressure ulcer prevention spinal cord injury",
                "wheelchair transfer techniques safety",
                "wheelchair maintenance and repair tips",
                "accessible bathroom modifications",
                "adaptive cooking tools and techniques for disability",
                "exercise and fitness for wheelchair users",
                "autonomic dysreflexia management spinal cord injury",
                "bladder management spinal cord injury",
                "adaptive driving controls for disability",
            ],
            "motivation": [
                "disability rights movement achievements",
                "famous people with spinal cord injuries accomplishments",
                "adaptive sports achievements world records",
                "disability advocacy success stories",
                "independent living movement disability",
            ],
            "tech": [
                "assistive technology for spinal cord injury",
                "smart home accessibility devices wheelchair users",
                "voice control technology disability accessibility",
                "wheelchair power assist technology innovations",
                "eye tracking technology computer access disability",
                "adaptive gaming controllers disability",
                "environmental control units disability",
                "augmentative alternative communication devices",
                "robotic arm wheelchair mounted assistive",
                "accessible smartphone apps disability",
                "standing wheelchair technology",
                "pressure mapping wheelchair cushion technology",
            ],
            "community": [
                "spinal cord injury peer support groups",
                "wheelchair accessible travel tips spinal cord injury",
                "workplace accommodations spinal cord injury wheelchair",
                "adaptive sports spinal cord injury recreation",
                "spinal cord injury caregiver challenges",
                "wheelchair accessibility public transportation",
            ],
            "wellness": [
                "mental health spinal cord injury coping strategies",
                "sleep hygiene wheelchair users",
                "nutrition spinal cord injury health",
                "mindfulness meditation chronic pain disability",
                "peer support spinal cord injury mental health",
                "secondary health conditions spinal cord injury prevention",
            ],
            "random": [
                "wheelchair accessible travel spinal cord injury",
                "adaptive sports spinal cord injury athletes",
                "home modifications wheelchair accessibility ramps",
                "dating relationships spinal cord injury",
                "workplace accommodations wheelchair users",
                "outdoor recreation wheelchair accessible trails",
                "spinal cord injury daily living challenges solutions",
            ],
        }
        
        queries = rag_queries.get(category, rag_queries["random"])
        query = random.choice(queries)
        
        try:
            self.logger.info(f"Querying RAG for category '{category}': {query}")
            chunks, scores = self.rag_system.retrieve_context(query)
            
            if not chunks:
                self.logger.info("RAG returned no chunks")
                return None
            
            # Format the top chunks as context for the LLM
            context_parts = []
            for chunk, score in zip(chunks[:3], scores[:3]):  # Top 3 chunks
                if hasattr(chunk, 'text') and chunk.text:
                    context_parts.append(chunk.text.strip())
            
            if not context_parts:
                return None
            
            context = "\n\n".join(context_parts)
            # Limit context length to avoid overwhelming the prompt
            if len(context) > 2000:
                context = context[:2000]
            
            self.logger.info(f"RAG provided {len(context_parts)} chunks ({len(context)} chars)")
            return context
            
        except Exception as e:
            self.logger.warning(f"RAG query failed: {e}")
            return None

    def _is_repetitive(self, message: str, recent_messages: List[str]) -> bool:
        """
        Check if a generated message is too similar to previously posted messages.
        
        Uses word-overlap ratio and key-phrase matching to detect repeats.
        """
        if not recent_messages:
            return False
        
        message_lower = message.lower()
        # Extract significant words (drop short/common words)
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                     'could', 'should', 'may', 'might', 'can', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'or', 'and', 'not',
                     'but', 'if', 'it', 'its', 'this', 'that', 'your', 'you',
                     'what', 'which', 'who', 'how', 'after', 'since', 'about'}
        message_words = {w for w in message_lower.split() if w not in stopwords and len(w) > 2}
        
        # Extract key phrases (2-grams) for catching thematic repetition
        message_bigrams = set()
        words_list = [w for w in message_lower.split() if w not in stopwords and len(w) > 2]
        for i in range(len(words_list) - 1):
            message_bigrams.add(f"{words_list[i]} {words_list[i+1]}")
        
        for prev in recent_messages:
            prev_words = {w for w in prev.lower().split() if w not in stopwords and len(w) > 2}
            
            if not message_words or not prev_words:
                continue
            # Jaccard similarity on significant words only
            overlap = message_words & prev_words
            similarity = len(overlap) / len(message_words | prev_words)
            if similarity > 0.30:
                self.logger.info(f"Repetition detected (word overlap {similarity:.0%}): {prev[:60]}...")
                return True
            
            # Also check bigram overlap for thematic repetition
            prev_words_list = [w for w in prev.lower().split() if w not in stopwords and len(w) > 2]
            prev_bigrams = set()
            for i in range(len(prev_words_list) - 1):
                prev_bigrams.add(f"{prev_words_list[i]} {prev_words_list[i+1]}")
            if message_bigrams and prev_bigrams:
                bigram_overlap = message_bigrams & prev_bigrams
                if len(bigram_overlap) >= 3:
                    self.logger.info(f"Repetition detected (bigram overlap {bigram_overlap}): {prev[:60]}...")
                    return True
        
        return False

    def _save_message_to_history(self, message: str, category: str):
        """Save generated message to history."""
        history_file = Path(__file__).parent / "daily_message_history.json"
        
        # Load existing history
        history = []
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                history = []
        
        # Add new message
        history.append({
            'date': datetime.now().isoformat(),
            'category': category,
            'message': message
        })
        
        # Keep only last 60 entries
        history = history[-60:]
        
        # Save updated history
        try:
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            # If we can't save history, continue anyway
            pass

    def _parse_poll_response(self, raw_response: str, category: str) -> Optional[dict]:
        """
        Parse a poll JSON response from the LLM.
        
        Returns None if parsing fails (caller should retry or fall back).
        """
        import re
        
        # Try to extract JSON from the response (LLM may wrap it in markdown etc.)
        json_match = re.search(r'\{[^{}]*"question"[^{}]*"options"[^{}]*\[.*?\][^{}]*\}', raw_response, re.DOTALL)
        
        if json_match:
            try:
                poll_data = json.loads(json_match.group())
                question = poll_data.get("question", "").strip()
                options = poll_data.get("options", [])
                
                # Validate the poll data
                if question and isinstance(options, list) and 2 <= len(options) <= 4:
                    # Truncate to Discord limits
                    question = question[:300]
                    options = [opt[:55] for opt in options if isinstance(opt, str) and opt.strip()]
                    
                    if len(options) >= 2:
                        return {
                            "format": "poll",
                            "question": question,
                            "options": options,
                            "category": category,
                        }
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        # Parsing failed
        self.logger.warning(f"Poll JSON parsing failed. Raw: {raw_response[:100]}")
        return None

    async def generate_message(self, category: str = "random") -> dict:
        """
        Generate a daily message for the specified category.
        
        Args:
            category: Type of message to generate (fact, tip, motivation, etc.)
        
        Returns:
            Dict with keys:
              - "format": "text" or "poll"
              - "content": message text (for text format)
              - "question": poll question (for poll format)
              - "options": list of poll options (for poll format)
              - "category": the category used
        """
        if not self.llm_client:
            raise RuntimeError("Generator not set up. Call setup() first.")
        
        # Get recent messages to avoid repetition
        recent_messages = self._get_recent_messages()
        
        # Define prompts for different categories with SCI-appropriate content
        # CRITICAL: Every prompt MUST require an explicit SCI/disability connection.
        # Generic wellness/motivation advice is useless to this community.
        category_prompts = {
            "fact": """Share one interesting, well-established fact that is SPECIFICALLY about spinal cord injury or the SCI community. Examples of good topics: how different injury levels (C4 vs T10) affect function, the history of wheelchair basketball starting in VA hospitals in 1946, how autonomic dysreflexia works, the difference between complete and incomplete injuries, or accessibility legislation milestones. IMPORTANT: Only use medically accurate, well-established facts. Do NOT mention regeneration, cure research, or experimental treatments. Do NOT ask the reader to share anything. Just state the fact. Keep it under 2 sentences.""",
            
            "tip": """Write one specific, actionable practical tip that addresses a challenge UNIQUE to living with a spinal cord injury. The tip MUST involve something specific to SCI — not generic advice anyone could use. Good examples: how to do a proper pressure relief in a wheelchair, tips for managing neurogenic bowel routines, how to check skin in hard-to-see areas, catheter care tips, how to handle temperature regulation issues below injury level, or tricks for transfers. Do NOT give generic health advice like "drink water" or "eat healthy." State the tip directly — do NOT ask a question. Keep it under 2 sentences.""",
            
            "motivation": """Write a short motivational thought that resonates specifically with the SCI community. It MUST reference a real aspect of life with SCI — adapting to a new normal, mastering a new skill post-injury, navigating accessibility barriers, the strength it takes to advocate for yourself, or finding independence in new ways. Do NOT write generic motivation like "believe in yourself" or "every day is a new opportunity." Write it as a direct statement — do NOT ask a question. Keep it under 2 sentences.""",
            
            "tech": """Recommend one specific assistive technology tool, app, device, or accessibility feature that is particularly useful for people with spinal cord injuries. Name the actual product/app and briefly explain what it does and WHY it matters for someone with SCI specifically (e.g., limited hand function, wheelchair use, voice control needs). Good examples: switch-adapted gaming controllers, Tecla-e for smart home control with limited mobility, mouth-stick alternatives, power wheelchair programming apps, or pressure-mapping cushion systems. Do NOT recommend generic tech like "use a fitness tracker." Keep it under 2 sentences.""",
            
            "community": """Create a poll question for the SCI community with 2-4 answer options. The question MUST be about a specific aspect of living with SCI — not a generic preference question. Good examples: "What's your biggest wheelchair maintenance headache?" with options like "Flat tires", "Caster issues", "Cushion wear", "Frame adjustments". Or: "How do you handle temperature regulation below your level?" with options like "Layering clothes", "Cooling vests", "Just deal with it", "Avoiding heat". Respond ONLY with valid JSON: {"question": "your question here", "options": ["Option 1", "Option 2", "Option 3"]}.""",
            
            "wellness": """Write one specific wellness or self-care tip that addresses a challenge UNIQUE to people with spinal cord injuries. The tip MUST be about an SCI-specific wellness concern — NOT generic advice like "get good sleep" or "practice mindfulness." Good SCI-specific topics: managing neuropathic pain without over-relying on meds, dealing with shoulder overuse from wheeling, mental health strategies for adjusting to life post-injury, preventing UTIs with proper hydration and catheter care, skin checks and pressure injury prevention, managing spasticity, or coping with fatigue from the extra energy SCI daily living requires. Keep it under 2 sentences.""",
            
            "random": """Create a discussion question about a specific aspect of daily life with SCI. The question MUST be about something that is unique or notably different for people with spinal cord injuries. Good examples: "What's your go-to hack for getting dressed faster?", "How did you figure out your vehicle modification setup?", "What's the most overrated piece of adaptive equipment?", or "What do you wish you'd known in your first year post-injury?" Ask one genuine question that invites people to share SCI-specific knowledge and experiences. Keep it under 2 sentences."""
        }
        
        prompt = category_prompts.get(category, category_prompts["random"])
        
        # Add recent messages context to avoid repetition
        if recent_messages:
            recent_context = "Previously posted (avoid similar topics):\n" + "\n".join([f"- {msg}" for msg in recent_messages])
            prompt = f"{prompt}\n\n{recent_context}"
        
        # Use the same system prompt as the main bot for consistent tone
        main_system_prompt = self.config.llm.get_system_prompt()
        
        daily_system_prompt = f"""{main_system_prompt}

SPECIAL TASK: You are generating short daily messages for the SCI community Discord channel. Most messages should give value directly (tips, facts, recommendations) rather than asking questions.

CRITICAL OUTPUT RULES:
- Respond with ONLY the message text itself — 1-2 sentences max, under 280 characters
- Do NOT include any instructions, meta-commentary, character counts, or explanations
- Do NOT prefix your response with labels like "Here's a tip:" or "Fact:"
- Do NOT echo or repeat any part of these instructions in your output
- Do NOT include phrases like "keep it under X characters" or "here is a tip"

CRITICAL SCI-RELEVANCE RULE:
- Every message MUST be specifically about spinal cord injury, wheelchair use, or disability-specific challenges
- NEVER post generic health, wellness, or motivational advice that could apply to anyone
- If the advice would make sense on a general health blog, it is NOT specific enough
- Bad example: "Maintain a consistent sleep schedule" (generic, not SCI-specific)
- Good example: "If spasticity or neuropathic pain disrupts your sleep, talk to your doc about timing your meds so they peak at bedtime" (SCI-specific)

Guidelines for daily messages:
- Use conversational, natural language (not clinical or business-speak)
- Write as a caring facilitator, not as someone with personal SCI experience
- Do not use hashtags or emojis
- Create FRESH, UNIQUE topics that avoid repeating recent themes
- When the prompt says "do NOT ask a question", write a direct statement only
- When asked for a poll, respond ONLY with the requested JSON format"""

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=daily_system_prompt),
            ChatMessage(role=MessageRole.USER, content=prompt),
        ]
        
        request = ChatRequest(
            messages=messages,
            model=self.config.llm.model_name,
            max_tokens=200 if category == "community" else 80,
            temperature=0.7
        )
        
        max_attempts = 5
        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(f"Generating {category} message (attempt {attempt})")
                response = await self.llm_client.generate_chat_completion(
                    request.messages, max_tokens=request.max_tokens, temperature=request.temperature
                )
                
                if not (response.choices and len(response.choices) > 0):
                    raise RuntimeError("No response choices returned from LLM")
                
                message = response.content.strip()
                
                # Handle poll format
                if category == "community":
                    poll_result = self._parse_poll_response(message, category)
                    if poll_result:
                        # Check if this poll has been posted before
                        if self._is_repetitive(poll_result["question"], recent_messages):
                            self.logger.warning(f"Attempt {attempt}: Poll is repetitive, retrying")
                            request.temperature = min(1.0, request.temperature + 0.15)
                            continue
                        self._save_message_to_history(poll_result["question"], category)
                        self.logger.info(f"Generated poll: {poll_result['question']}")
                        return poll_result
                    # Poll parsing failed
                    self.logger.warning(f"Attempt {attempt}: Poll parsing failed, retrying")
                    request.temperature = min(1.0, request.temperature + 0.15)
                    continue
                
                # Post-process text messages
                import re
                message = re.sub(r'#\w+', '', message)  # Remove hashtags
                message = re.sub(r'\s+', ' ', message)  # Clean whitespace
                
                # Strip leaked prompt instructions / meta-commentary
                message = re.sub(
                    r'(?i)\s*keep\s+it\s+under\s+\d+\s+(?:characters?|words?)\s*[:.]?\s*',
                    '', message
                )
                message = re.sub(
                    r'(?i)^(?:here(?:\'s| is) (?:a |an |one |the )?(?:tip|fact|thought|insight|recommendation|question|message)\s*[:.]?\s*)',
                    '', message
                )
                message = re.sub(
                    r'(?i)^(?:sure[!,.]?\s*|okay[!,.]?\s*|absolutely[!,.]?\s*)',
                    '', message
                )
                # Remove character/word count notes the LLM sometimes appends
                message = re.sub(
                    r'(?i)\s*\(?\d+\s*(?:characters?|words?|chars?)\)?\s*$',
                    '', message
                )
                
                # Remove surrounding quotes
                if message.startswith('"') and message.endswith('"'):
                    message = message[1:-1]
                elif message.startswith("'") and message.endswith("'"):
                    message = message[1:-1]
                
                message = message.strip()
                
                # Truncate to last complete sentence if over 280 chars
                if len(message) > 280:
                    # Find the last sentence boundary within 280 chars
                    truncated = message[:280]
                    last_period = truncated.rfind('.')
                    last_question = truncated.rfind('?')
                    last_exclaim = truncated.rfind('!')
                    cut_point = max(last_period, last_question, last_exclaim)
                    if cut_point > 100:  # Only truncate if we keep a meaningful amount
                        message = message[:cut_point + 1]
                
                # Check text messages for repetition too
                if self._is_repetitive(message, recent_messages):
                    self.logger.warning(f"Attempt {attempt}: Message is repetitive, retrying")
                    request.temperature = min(1.0, request.temperature + 0.15)
                    continue
                
                # Save to history
                self._save_message_to_history(message, category)
                self.logger.info(f"Generated message: {message[:50]}...")
                
                return {
                    "format": "text",
                    "content": message,
                    "category": category,
                }
                    
            except Exception as e:
                self.logger.error(f"Attempt {attempt} failed: {e}")
                if attempt == max_attempts:
                    raise
        
        raise RuntimeError(f"Failed to generate non-repetitive {category} message after {max_attempts} attempts")

    async def post_through_bot(self, message_data: dict, test_mode: bool = False) -> bool:
        """
        Post a message through the bot's internal API.
        
        Args:
            message_data: Dict from generate_message() with format, content/poll data
            test_mode: If True, skip actual posting and just simulate
            
        Returns:
            True if posted successfully, False otherwise
        """
        if not self.config:
            raise RuntimeError("Generator not set up. Call setup() first.")
        
        if test_mode:
            self.logger.info("TEST MODE: Would post daily message through bot (not actually posting)")
            return True
        
        # First check if bot is healthy
        if not await self.check_bot_health():
            self.logger.error("Bot is not running or not healthy - cannot post daily message")
            return False
        
        try:
            # Get the shared context channel
            channel_id = self.config.conversation.shared_context_channel_id
            if not channel_id:
                self.logger.error("No shared context channel configured")
                return False
            
            # Bot API endpoint - use test endpoint in test mode
            if test_mode:
                url = f"http://localhost:{self.bot_api_port}/test-daily-message"
            else:
                url = f"http://localhost:{self.bot_api_port}/daily-message"
            
            # Headers for bot API
            headers = {
                "Authorization": f"Bearer {self.bot_api_key}",
                "Content-Type": "application/json"
            }
            
            # Build payload based on message format
            payload = {
                "channel_id": str(channel_id),
                "format": message_data.get("format", "text"),
            }
            
            if message_data["format"] == "poll":
                payload["question"] = message_data["question"]
                payload["options"] = message_data["options"]
            else:
                payload["content"] = message_data["content"]
            
            # Send the message via bot API
            display_text = message_data.get("content") or message_data.get("question", "")
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        if test_mode:
                            self.logger.info(f"TEST: Bot confirmed it would post daily message to channel {channel_id}")
                            print(f"✅ TEST PASSED: Bot would post message to #{response_data.get('channel_name', 'unknown')}")
                            print(f"   Message: {display_text}")
                        else:
                            message_id = response_data.get('message_id')
                            self.logger.info(f"Successfully posted daily message through bot to channel {channel_id}")
                        
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to post message through bot: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to post message through bot: {e}")
            return False


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python generate_daily_message_v2.py <category> [--json] [--post] [--test]")
        print("Categories: fact, tip, motivation, tech, community, wellness, random")
        print("Options:")
        print("  --json    Output in JSON format")
        print("  --post    Post message through bot (default: just generate)")
        print("  --test    Test mode - simulate posting without actually posting")
        print("")
        print("NOTE: Bot must be running for posting to work. This ensures messages")
        print("      only happen when the bot is healthy and available.")
        sys.exit(1)
    
    category = sys.argv[1]
    output_json = "--json" in sys.argv
    should_post = "--post" in sys.argv
    test_mode = "--test" in sys.argv
    
    generator = BotMediatedDailyMessageGenerator()
    
    try:
        await generator.setup()
        message_data = await generator.generate_message(category)
        
        # Build a display string for non-JSON output
        if message_data["format"] == "poll":
            display_text = f"[POLL] {message_data['question']} | Options: {', '.join(message_data['options'])}"
        else:
            display_text = message_data["content"]
        
        if should_post:
            # Post through bot (with test mode option)
            posted = await generator.post_through_bot(message_data, test_mode=test_mode)
            
            if output_json:
                result = {
                    "success": posted,
                    "category": category,
                    "posted": posted,
                    "method": "bot_mediated",
                    **message_data,
                }
                print(json.dumps(result))
            else:
                if posted:
                    print(f"Successfully posted daily message through bot: {display_text}")
                else:
                    print(f"Failed to post message through bot: {display_text}")
        else:
            # Just generate and display
            if output_json:
                result = {
                    "success": True,
                    "category": category,
                    "posted": False,
                    "method": "bot_mediated",
                    **message_data,
                }
                print(json.dumps(result))
            else:
                print(display_text)
            
    except Exception as e:
        if output_json:
            result = {
                "success": False,
                "error": str(e),
                "posted": False,
                "method": "bot_mediated"
            }
            print(json.dumps(result))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await generator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
