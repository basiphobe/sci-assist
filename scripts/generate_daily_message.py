#!/usr/bin/env python3
"""
Generate daily engagement messages using the bot's LLM.

This script uses the same LLM configuration as the main bot to generate
fresh, contextually relevant daily messages for the SCI community.
"""

import asyncio
import sys
import json
import os
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
from discord_llm_bot.database.repositories import DatabaseManager
from discord_llm_bot.conversation.manager import ConversationManager


class DailyMessageGenerator:
    """Generate daily messages using the bot's LLM."""
    
    def __init__(self):
        """Initialize the generator."""
        self.config = None
        self.llm_client = None
        self.db_manager = None
        self.conversation_manager = None
        self.logger = None
    
    async def setup(self):
        """Set up the LLM client."""
        # Load configuration (same as main bot)
        self.config = load_config()
        
        # Set up minimal logging to avoid interfering with JSON output
        import logging
        logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
        self.logger = logging.getLogger(__name__)
        
        # Create LLM client
        self.llm_client = LLMClient(self.config.llm)
        
        # Initialize database and conversation manager for storing messages
        self.db_manager = DatabaseManager(self.config.database)
        await self.db_manager.initialize()
        
        self.conversation_manager = ConversationManager(
            self.config, 
            self.llm_client, 
            self.db_manager
        )
        
    async def cleanup(self):
        """Clean up resources."""
        if self.db_manager:
            await self.db_manager.close()
        if self.llm_client:
            await self.llm_client.close()
    
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
            "fact": """Create a discussion starter about an interesting SCI-related fact. Focus on topics like: spinal cord anatomy basics, injury level statistics, adaptive equipment innovations, accessibility history, or SCI community achievements. IMPORTANT: Only use well-established, medically accurate facts. Do NOT mention regeneration, cure research, or experimental treatments. Ask the community to share their thoughts or experiences related to it. Keep it under 150 characters.""",
            
            "tip": """Ask the community to share practical tips about SCI challenges. Focus on topics like: pressure sore prevention, transfer techniques, wheelchair maintenance, bathroom accessibility, cooking adaptations, exercise routines, or pain management. Keep it under 150 characters.""",
            
            "motivation": """Ask about personal growth and perspective changes. Focus on topics like: unexpected positive changes, mindset shifts, goal achievement, overcoming obstacles, finding purpose, or resilience strategies. Keep it under 150 characters.""",
            
            "tech": """Ask about assistive technology and innovations. Focus on topics like: smartphone apps, smart home devices, wheelchair accessories, communication aids, driving adaptations, computer accessibility, or emerging technologies. Keep it under 150 characters.""",
            
            "community": """Ask about advocacy, education, or community involvement. Focus on topics like: accessibility awareness, policy advocacy, mentoring others, workplace accommodations, public speaking, or community organizing. Keep it under 150 characters.""",
            
            "wellness": """Ask about physical and mental wellness strategies. Focus on topics like: mental health practices, sleep routines, nutrition, stress management, self-care rituals, therapy experiences, or mindfulness techniques. Keep it under 150 characters.""",
            
            "random": """Create a discussion starter on a varied SCI-related topic. Choose from: travel experiences, workplace accommodations, hobbies/recreation, family dynamics, dating/relationships, home modifications, weather challenges, accessibility experiences, or daily problem-solving. Ask questions that let people share knowledge and experiences. Keep it under 150 characters."""
        }
        
        prompt = category_prompts.get(category, category_prompts["random"])
        
        # Add recent messages context to avoid repetition
        if recent_messages:
            recent_context = "Recent daily messages posted (avoid similar topics):\\n" + "\\n".join([f"- {msg}" for msg in recent_messages])
            prompt = f"{prompt}\\n\\n{recent_context}"
        
        # Create the chat request with proper SCI-specialized system prompt
        daily_system_prompt = """You are a bot that facilitates discussions in a Discord chat for people with spinal cord injuries. Create discussion starters under 150 characters that invite community members to share their experiences with each other. 

You are NOT a person with SCI - you are a bot helping people connect. Ask questions that let community members share their knowledge and experiences. Do not use hashtags. Write from the perspective of a helpful facilitator, not as someone with personal SCI experience.

CRITICAL MEDICAL ACCURACY: Never mention spinal cord regeneration, cures, or experimental treatments. The spinal cord does not regenerate. Focus only on established, accurate medical information and practical topics.

IMPORTANT: Create FRESH, UNIQUE topics. Avoid repeating similar themes or questions from recent messages."""

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
            model=self.config.llm.model_name,  # Add required model field
            max_tokens=100,  # Keep responses concise
            temperature=0.3  # Lower temperature for more consistent adherence to instructions
        )
        
        try:
            self.logger.info(f"Generating {category} message")
            response = await self.llm_client.generate_chat_completion(request.messages, 
                                                                    max_tokens=request.max_tokens,
                                                                    temperature=request.temperature)
            
            if response.choices and len(response.choices) > 0:
                message = response.content.strip()
                
                # Post-process to remove any hashtags that might have been generated
                # Remove hashtags and clean up the message
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

    async def post_to_discord(self, message: str, test_mode: bool = False) -> bool:
        """
        Post a message to Discord using the Discord API.
        
        Args:
            message: The message to post
            test_mode: If True, skip actual posting and just simulate
            
        Returns:
            True if posted successfully, False otherwise
        """
        if not self.config:
            raise RuntimeError("Generator not set up. Call setup() first.")
        
        if test_mode:
            self.logger.info("TEST MODE: Would post daily message (not actually posting)")
            return True
        
        try:
            # Get the shared context channel
            channel_id = self.config.conversation.shared_context_channel_id
            if not channel_id:
                self.logger.error("No shared context channel configured")
                return False
            
            # Discord API endpoint
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            
            # Headers for Discord API
            headers = {
                "Authorization": f"Bot {self.config.discord.token}",
                "Content-Type": "application/json"
            }
            
            # Message payload
            payload = {
                "content": message
            }
            
            # Send the message via HTTP
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        message_id = response_data.get('id')
                        
                        self.logger.info(f"Successfully posted daily message to channel {channel_id}")
                        
                        # Also store the message in the conversation database for context
                        try:
                            conversation_id = await self.conversation_manager.get_or_create_conversation(
                                user_id=999999999999999999,  # Special bot user ID
                                channel_id=channel_id,
                                guild_id=self.config.discord.guild_id,
                            )
                            
                            await self.conversation_manager.add_message(
                                conversation_id=conversation_id,
                                content=message,
                                role="assistant",
                                extra_data={
                                    "discord_message_id": message_id,
                                    "discord_user_id": 0,  # Replace with your bot's user ID
                                    "discord_username": "sci-assist",
                                    "daily_message": True,
                                }
                            )
                            self.logger.info(f"Stored daily message in conversation database")
                            
                        except Exception as e:
                            self.logger.error(f"Failed to store daily message in database: {e}")
                            # Don't fail the whole operation if database storage fails
                        
                        return True
                    else:
                        error_text = await response.text()
                        self.logger.error(f"Failed to post message: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            self.logger.error(f"Failed to post message to Discord: {e}")
            return False


async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python generate_daily_message.py <category> [--json] [--post] [--test]")
        print("Categories: fact, tip, motivation, tech, community, wellness, random")
        print("Options:")
        print("  --json    Output in JSON format")
        print("  --post    Post message to Discord (default: just generate)")
        print("  --test    Test mode - simulate posting without actually posting")
        sys.exit(1)
    
    category = sys.argv[1]
    output_json = "--json" in sys.argv
    should_post = "--post" in sys.argv
    test_mode = "--test" in sys.argv
    
    generator = DailyMessageGenerator()
    
    try:
        await generator.setup()
        message = await generator.generate_message(category)
        
        if should_post:
            # Post to Discord (with test mode option)
            posted = await generator.post_to_discord(message, test_mode=test_mode)
            
            if output_json:
                result = {
                    "success": posted,
                    "category": category,
                    "message": message,
                    "posted": posted
                }
                print(json.dumps(result))
            else:
                if posted:
                    print(f"Successfully posted daily message: {message}")
                else:
                    print(f"Failed to post message: {message}")
        else:
            # Just generate and display
            if output_json:
                result = {
                    "success": True,
                    "category": category,
                    "message": message,
                    "posted": False
                }
                print(json.dumps(result))
            else:
                print(message)
            
    except Exception as e:
        if output_json:
            result = {
                "success": False,
                "error": str(e),
                "posted": False
            }
            print(json.dumps(result))
        else:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        await generator.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
