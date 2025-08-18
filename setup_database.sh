#!/bin/bash
# Database setup script for sci-assist-bot

echo "Setting up Alembic database configuration..."

# Update alembic.ini with correct database URL
sed -i 's|^sqlalchemy.url = .*|sqlalchemy.url = sqlite:///./bot_conversations.db|' alembic.ini

# Replace env.py with our template
cp alembic_env_template.py alembic/env.py

echo "Creating initial migration..."
alembic revision --autogenerate -m "Initial migration"

echo "Applying migrations..."
alembic upgrade head

echo "Database setup complete!"
