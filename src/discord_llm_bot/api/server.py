"""
Internal API server for bot operations.

This module provides a lightweight HTTP API server that allows external scripts
to communicate with the bot for internal operations. It's designed for security
through obscurity on localhost only.
"""

import asyncio
from typing import Optional, Dict, Any, TYPE_CHECKING
import json
import secrets
from pathlib import Path

from aiohttp import web, ClientSession
from aiohttp.web import Request, Response
import structlog

from discord_llm_bot.utils.logging import get_logger

if TYPE_CHECKING:
    from discord_llm_bot.bot.client import DiscordLLMBot


class InternalAPIServer:
    """
    Internal API server for bot communication.
    
    Provides endpoints for:
    - Health checks
    - Daily message posting
    - Bot status information
    
    Security: 
    - Localhost only
    - Random API key generated at startup
    - Simple bearer token authentication
    """
    
    def __init__(self, bot: "DiscordLLMBot", port: int = 8765):
        """
        Initialize the internal API server.
        
        Args:
            bot: The Discord bot instance
            port: Port to run the server on (default: 8765)
        """
        self.bot = bot
        self.port = port
        self.logger = get_logger(__name__)
        
        # Generate a random API key for this session
        self.api_key = secrets.token_urlsafe(32)
        self.logger.info("Generated API key for internal server", 
                        port=port, key_preview=self.api_key[:8] + "...")
        
        # Save API key to a file for daily scripts to use
        try:
            api_key_file = Path("/opt/sci-assist/.bot-api-key")
            api_key_file.write_text(self.api_key)
            api_key_file.chmod(0o600)  # Only readable by owner
            self.logger.info("Saved API key to file", file=str(api_key_file))
        except Exception as e:
            self.logger.warning("Failed to save API key to file", error=str(e))
        
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
    async def start(self) -> None:
        """Start the internal API server."""
        self.app = web.Application()
        
        # Set up routes
        self.app.router.add_get('/health', self._health_check)
        self.app.router.add_post('/daily-message', self._post_daily_message)
        self.app.router.add_post('/test-daily-message', self._test_daily_message)
        self.app.router.add_get('/status', self._bot_status)
        
        # Start the server
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        
        self.site = web.TCPSite(self.runner, 'localhost', self.port)
        await self.site.start()
        
        self.logger.info("Internal API server started", 
                        host="localhost", port=self.port,
                        api_key=self.api_key)
        
    async def stop(self) -> None:
        """Stop the internal API server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
            
        # Clean up API key file
        try:
            api_key_file = Path("/opt/sci-assist/.bot-api-key")
            if api_key_file.exists():
                api_key_file.unlink()
                self.logger.info("Cleaned up API key file")
        except Exception as e:
            self.logger.warning("Failed to clean up API key file", error=str(e))
            
        self.logger.info("Internal API server stopped")
        
    def _check_auth(self, request: Request) -> bool:
        """Check if the request has valid authentication."""
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return False
        token = auth_header[7:]  # Remove 'Bearer ' prefix
        return token == self.api_key
        
    async def _health_check(self, request: Request) -> Response:
        """Health check endpoint."""
        if not self._check_auth(request):
            return Response(status=401, text='Unauthorized')
            
        health_data = {
            'status': 'healthy',
            'bot_ready': self.bot.is_ready(),
            'bot_user': str(self.bot.user) if self.bot.user else None,
            'guild_count': len(self.bot.guilds) if self.bot.is_ready() else 0,
        }
        
        return Response(
            text=json.dumps(health_data, indent=2),
            content_type='application/json'
        )
        
    async def _bot_status(self, request: Request) -> Response:
        """Get detailed bot status."""
        if not self._check_auth(request):
            return Response(status=401, text='Unauthorized')
            
        status_data = {
            'ready': self.bot.is_ready(),
            'user': str(self.bot.user) if self.bot.user else None,
            'guild_count': len(self.bot.guilds) if self.bot.is_ready() else 0,
            'latency': round(self.bot.latency * 1000, 2),  # ms
            'setup_complete': getattr(self.bot, '_setup_complete', False),
        }
        
        return Response(
            text=json.dumps(status_data, indent=2),
            content_type='application/json'
        )
        
    async def _post_daily_message(self, request: Request) -> Response:
        """Post a daily message through the bot."""
        if not self._check_auth(request):
            return Response(status=401, text='Unauthorized')
            
        if not self.bot.is_ready():
            return Response(status=503, text='Bot not ready')
            
        try:
            # Parse request body
            body = await request.json()
            message_content = body.get('content')
            channel_id = body.get('channel_id')
            
            if not message_content or not channel_id:
                return Response(status=400, text='Missing content or channel_id')
                
            # Get the channel
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return Response(status=404, text='Channel not found')
                
            # Send the message through the bot
            message = await channel.send(message_content)
            
            # Store in conversation context (let the bot's normal message handler do this)
            # The on_message event will automatically handle storing this message
            
            response_data = {
                'success': True,
                'message_id': message.id,
                'channel_id': channel.id,
                'timestamp': message.created_at.isoformat(),
            }
            
            self.logger.info("Daily message posted successfully",
                           message_id=message.id,
                           channel_id=channel.id)
            
            return Response(
                text=json.dumps(response_data, indent=2),
                content_type='application/json'
            )
            
        except json.JSONDecodeError:
            return Response(status=400, text='Invalid JSON')
        except Exception as e:
            self.logger.error("Failed to post daily message", error=str(e))
            return Response(status=500, text=f'Internal error: {str(e)}')
            
    async def _test_daily_message(self, request: Request) -> Response:
        """Test daily message posting without actually posting to Discord."""
        if not self._check_auth(request):
            return Response(status=401, text='Unauthorized')
            
        if not self.bot.is_ready():
            return Response(status=503, text='Bot not ready')
            
        try:
            # Parse request body
            body = await request.json()
            message_content = body.get('content')
            channel_id = body.get('channel_id')
            
            if not message_content or not channel_id:
                return Response(status=400, text='Missing content or channel_id')
                
            # Get the channel (just to verify it exists)
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                return Response(status=404, text='Channel not found')
                
            # Simulate posting (don't actually send)
            response_data = {
                'success': True,
                'test_mode': True,
                'message_content': message_content,
                'channel_id': int(channel_id),
                'channel_name': getattr(channel, 'name', 'Unknown'),
                'would_post': True,
            }
            
            self.logger.info("TEST: Daily message would be posted",
                           channel_id=channel_id,
                           message_preview=message_content[:50] + "...")
            
            return Response(
                text=json.dumps(response_data, indent=2),
                content_type='application/json'
            )
            
        except json.JSONDecodeError:
            return Response(status=400, text='Invalid JSON')
        except Exception as e:
            self.logger.error("Failed to test daily message", error=str(e))
            return Response(status=500, text=f'Internal error: {str(e)}')
