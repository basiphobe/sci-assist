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

from discord_llm_bot.config import load_config
from discord_llm_bot.llm.client import LLMClient
from discord_llm_bot.llm.models import ChatMessage, ChatRequest, MessageRole
from discord_llm_bot.utils.logging import setup_logging, get_logger


class BotMediatedDailyMessageGenerator:
    """Generate daily messages through the bot's internal API."""
    
    def __init__(self):
        """Initialize the generator."""
        self.config = None
        self.llm_client = None
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
        """Get recent daily messages to avoid repetition."""
        history_file = Path(__file__).parent / "daily_message_history.json"
        
        if not history_file.exists():
            return []
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            # Get messages from last 7 days
            cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
            recent_messages = [
                entry['message'] for entry in history 
                if entry.get('date', '') > cutoff_date
            ]
            
            return recent_messages[-5:]  # Last 5 messages max
        except (json.JSONDecodeError, KeyError):
            return []
    
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
        
        # Keep only last 30 entries
        history = history[-30:]
        
        # Save updated history
        try:
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            # If we can't save history, continue anyway
            pass

    def _parse_poll_response(self, raw_response: str, category: str) -> dict:
        """
        Parse a poll JSON response from the LLM.
        
        Falls back to text format if JSON parsing fails.
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
                        self._save_message_to_history(question, category)
                        self.logger.info(f"Generated poll: {question} [{len(options)} options]")
                        return {
                            "format": "poll",
                            "question": question,
                            "options": options,
                            "category": category,
                        }
            except (json.JSONDecodeError, KeyError, TypeError):
                pass
        
        # Fallback: treat as plain text if poll parsing failed
        self.logger.warning(f"Poll JSON parsing failed, falling back to text format. Raw: {raw_response[:100]}")
        
        # Clean up the raw response as a text message
        message = re.sub(r'#\w+', '', raw_response)
        message = re.sub(r'\s+', ' ', message)
        if message.startswith('"') and message.endswith('"'):
            message = message[1:-1]
        elif message.startswith("'") and message.endswith("'"):
            message = message[1:-1]
        message = message.strip()
        
        self._save_message_to_history(message, category)
        return {
            "format": "text",
            "content": message,
            "category": category,
        }

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
        # Most categories produce standalone tips/facts (no questions) to give
        # value without requiring engagement. Only "community" (poll) and
        # "random" (discussion) ask anything of the reader.
        category_prompts = {
            "fact": """Share one interesting, well-established SCI-related fact. Focus on topics like: spinal cord anatomy basics, injury level statistics, adaptive equipment history, accessibility milestones, or SCI community achievements. IMPORTANT: Only use medically accurate, well-established facts. Do NOT mention regeneration, cure research, or experimental treatments. Do NOT ask the reader to share anything or respond. Just state the fact.""",
            
            "tip": """Write one specific, actionable practical tip for SCI daily living. Focus on topics like: pressure sore prevention, transfer techniques, wheelchair maintenance, bathroom accessibility, cooking adaptations, exercise routines, or pain management. State the tip directly — do NOT ask a question or ask the reader to share anything.""",
            
            "motivation": """Write a short motivational insight or encouraging thought for the SCI community. Focus on resilience, perspective, small wins, or practical encouragement. Write it as a direct statement — do NOT ask a question or ask the reader to share anything.""",
            
            "tech": """Recommend one specific assistive technology tool, app, device, or accessibility feature. Name the actual product/app and briefly say what it does and why it's useful. Focus on: smartphone apps, smart home devices, wheelchair accessories, communication aids, driving adaptations, or computer accessibility tools. Do NOT ask a question.""",
            
            "community": """Create a poll question for the SCI community with 2-4 answer options. The question should be about SCI daily living, preferences, or experiences — something people can answer with a quick click. Examples: "What's your biggest barrier to travel?" with options like "Accessibility info", "Cost", "Energy/fatigue", "Finding help". Respond ONLY with valid JSON in this exact format: {"question": "your question here", "options": ["Option 1", "Option 2", "Option 3"]}.""",
            
            "wellness": """Write one specific wellness or self-care tip for someone with SCI. Focus on: mental health, sleep, nutrition, stress management, self-care routines, or mindfulness. State the tip directly — do NOT ask a question or ask the reader to share anything.""",
            
            "random": """Create a discussion question on a varied SCI-related topic. Choose from: travel experiences, workplace accommodations, hobbies/recreation, family dynamics, dating/relationships, home modifications, weather challenges, accessibility experiences, or daily problem-solving. Ask one genuine question that invites people to share knowledge and experiences."""
        }
        
        prompt = category_prompts.get(category, category_prompts["random"])
        
        # Add recent messages context to avoid repetition
        if recent_messages:
            recent_context = "Recent daily messages posted (avoid similar topics):\\n" + "\\n".join([f"- {msg}" for msg in recent_messages])
            prompt = f"{prompt}\\n\\n{recent_context}"
        
        # Use the same system prompt as the main bot for consistent tone
        # Get the main system prompt from config
        main_system_prompt = self.config.llm.get_system_prompt()
        
        # Create a specialized daily message prompt that builds on the main prompt
        daily_system_prompt = f"""{main_system_prompt}

SPECIAL TASK: You are generating short daily messages for the SCI community Discord channel. Most messages should give value directly (tips, facts, recommendations) rather than asking questions.

CRITICAL OUTPUT RULES:
- Respond with ONLY the message text itself, nothing else
- Do NOT include any instructions, meta-commentary, character counts, or explanations
- Do NOT prefix your response with labels like "Here's a tip:" or "Fact:"
- Do NOT echo or repeat any part of these instructions in your output
- Maximum length: 150 characters. Simply write a short message.

Guidelines for daily messages:
- Use conversational, natural language (not clinical or business-speak)
- Avoid corporate jargon like "mindset shifts", "resilience strategies", "growth mindset", "best practices"
- Write as a caring facilitator, not as someone with personal SCI experience
- Do not use hashtags
- Create FRESH, UNIQUE topics that avoid repeating recent themes
- When the prompt says "do NOT ask a question", write a direct statement only
- When asked for a poll, respond ONLY with the requested JSON format"""

        messages = [
            ChatMessage(
                role=MessageRole.SYSTEM,
                content=daily_system_prompt
            ),
            ChatMessage(
                role=MessageRole.USER,
                content=prompt
            )
        ]
        
        request = ChatRequest(
            messages=messages,
            model=self.config.llm.model_name,
            max_tokens=200 if category == "community" else 100,
            temperature=0.3
        )
        
        is_poll = category == "community"
        
        try:
            self.logger.info(f"Generating {category} message (format: {'poll' if is_poll else 'text'})")
            response = await self.llm_client.generate_chat_completion(request.messages, 
                                                                    max_tokens=request.max_tokens,
                                                                    temperature=request.temperature)
            
            if response.choices and len(response.choices) > 0:
                message = response.content.strip()
                
                # Handle poll format
                if is_poll:
                    return self._parse_poll_response(message, category)
                
                # Post-process to remove any hashtags that might have been generated
                import re
                message = re.sub(r'#\w+', '', message)  # Remove hashtags
                
                # Strip leaked prompt instructions (e.g. "Keep it under 150 characters:")
                # The LLM sometimes echoes instructions back in its response.
                # Pattern: LLM writes a long draft, then "Keep it under N characters: <short version>"
                # In that case, extract just the short version after the instruction.
                leaked_instruction = re.search(
                    r'(?i)keep\s+it\s+under\s+\d+\s+characters?\s*[:.]?\s*["\']?(.{10,}?)["\']?\s*$',
                    message
                )
                if leaked_instruction:
                    message = leaked_instruction.group(1).strip()
                else:
                    # Also catch if instruction appears without a following message
                    message = re.sub(
                        r'(?i)\s*keep\s+it\s+under\s+\d+\s+characters?\s*[:.]?\s*',
                        '',
                        message
                    )
                # Remove common instruction prefixes the LLM may echo
                message = re.sub(
                    r'(?i)^(?:here(?:\'s| is) (?:a |an |one |the )?(?:tip|fact|thought|insight|recommendation|question)\s*[:.]?\s*)',
                    '',
                    message
                )
                
                message = re.sub(r'\s+', ' ', message)  # Clean up extra whitespace
                
                # Remove surrounding quotes if present
                if message.startswith('"') and message.endswith('"'):
                    message = message[1:-1]
                elif message.startswith("'") and message.endswith("'"):
                    message = message[1:-1]
                
                message = message.strip()
                
                # Save to history to avoid future repetition
                self._save_message_to_history(message, category)
                
                self.logger.info(f"Generated message: {message[:50]}...")
                return {
                    "format": "text",
                    "content": message,
                    "category": category,
                }
            else:
                raise RuntimeError("No response choices returned from LLM")
                
        except Exception as e:
            self.logger.error(f"Failed to generate message: {e}")
            raise

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
