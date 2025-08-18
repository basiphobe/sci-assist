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

    async def generate_message(self, category: str = "random") -> str:
        """
        Generate a daily message for the specified category.
        
        Args:
            category: Type of message to generate (fact, tip, motivation, etc.)
        
        Returns:
            Generated message text
        """
        if not self.llm_client:
            raise RuntimeError("Generator not set up. Call setup() first.")
        
        # Get recent messages to avoid repetition
        recent_messages = self._get_recent_messages()
        
        # Define prompts for different categories with SCI-appropriate content
        category_prompts = {
            "fact": """Create a discussion starter about an interesting SCI-related fact. Focus on topics like: spinal cord anatomy, recovery statistics, adaptive equipment innovations, research breakthroughs, or historical SCI facts. Ask the community to share their thoughts or experiences related to it. Keep it under 150 characters.""",
            
            "tip": """Ask the community to share practical tips about SCI challenges. Focus on topics like: pressure sore prevention, transfer techniques, wheelchair maintenance, bathroom accessibility, cooking adaptations, exercise routines, or pain management. Keep it under 150 characters.""",
            
            "motivation": """Ask about personal growth and perspective changes. Focus on topics like: unexpected positive changes, things that help on hard days, ways of thinking that clicked, what keeps you going, finding new purpose, or getting through tough times. Keep it under 150 characters.""",
            
            "tech": """Ask about assistive technology and innovations. Focus on topics like: smartphone apps, smart home devices, wheelchair accessories, communication aids, driving adaptations, computer accessibility, or emerging technologies. Keep it under 150 characters.""",
            
            "community": """Ask about advocacy, education, or community involvement. Focus on topics like: accessibility awareness, policy advocacy, mentoring others, workplace accommodations, public speaking, or community organizing. Keep it under 150 characters.""",
            
            "wellness": """Ask about physical and mental wellness. Focus on topics like: what helps with mental health, sleep tips, nutrition advice, ways to manage stress, self-care ideas, therapy experiences, or calming techniques. Keep it under 150 characters.""",
            
            "random": """Create a discussion starter on a varied SCI-related topic. Choose from: travel experiences, workplace accommodations, hobbies/recreation, family dynamics, dating/relationships, home modifications, weather challenges, accessibility experiences, or daily problem-solving. Ask questions that let people share knowledge and experiences. Keep it under 150 characters."""
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

SPECIAL TASK: Create daily discussion starter messages (under 150 characters) that invite community members to share their experiences with each other.

Guidelines for daily messages:
- Use conversational, natural language (not clinical or business-speak)
- Ask questions that feel genuine and empathetic 
- Avoid corporate jargon like "mindset shifts", "resilience strategies", "growth mindset", "best practices"
- Use phrases real people say: "What helps you...", "How do you handle...", "What's worked for you...", "What gets you through..."
- Write as a caring facilitator, not as someone with personal SCI experience
- Do not use hashtags
- Create FRESH, UNIQUE topics that avoid repeating recent themes"""

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
            max_tokens=100,
            temperature=0.3
        )
        
        try:
            self.logger.info(f"Generating {category} message")
            response = await self.llm_client.generate_chat_completion(request.messages, 
                                                                    max_tokens=request.max_tokens,
                                                                    temperature=request.temperature)
            
            if response.choices and len(response.choices) > 0:
                message = response.content.strip()
                
                # Post-process to remove any hashtags that might have been generated
                import re
                message = re.sub(r'#\w+', '', message)  # Remove hashtags
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
                return message
            else:
                raise RuntimeError("No response choices returned from LLM")
                
        except Exception as e:
            self.logger.error(f"Failed to generate message: {e}")
            raise

    async def post_through_bot(self, message: str, test_mode: bool = False) -> bool:
        """
        Post a message through the bot's internal API.
        
        Args:
            message: The message to post
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
            
            # Message payload
            payload = {
                "content": message,
                "channel_id": str(channel_id)
            }
            
            # Send the message via bot API
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=10) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        
                        if test_mode:
                            self.logger.info(f"TEST: Bot confirmed it would post daily message to channel {channel_id}")
                            print(f"✅ TEST PASSED: Bot would post message to #{response_data.get('channel_name', 'unknown')}")
                            print(f"   Message: {message}")
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
        message = await generator.generate_message(category)
        
        if should_post:
            # Post through bot (with test mode option)
            posted = await generator.post_through_bot(message, test_mode=test_mode)
            
            if output_json:
                result = {
                    "success": posted,
                    "category": category,
                    "message": message,
                    "posted": posted,
                    "method": "bot_mediated"
                }
                print(json.dumps(result))
            else:
                if posted:
                    print(f"Successfully posted daily message through bot: {message}")
                else:
                    print(f"Failed to post message through bot: {message}")
        else:
            # Just generate and display
            if output_json:
                result = {
                    "success": True,
                    "category": category,
                    "message": message,
                    "posted": False,
                    "method": "bot_mediated"
                }
                print(json.dumps(result))
            else:
                print(message)
            
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
