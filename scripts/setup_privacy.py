#!/usr/bin/env python3
"""
Setup privacy management for SCI-Assist bot.

This script:
1. Exports existing conversation data for training
2. Sets up privacy management tables
3. Applies retention policies
4. Provides options for data cleanup
"""

import sqlite3
import json
import argparse
from pathlib import Path
import sys
import os

# Add the src directory to Python path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from discord_llm_bot.privacy.manager import PrivacyManager, RetentionPolicy


def setup_privacy_system(db_path: str, config: dict):
    """Set up the privacy management system."""
    print("🔧 Setting up privacy management system...")
    
    # Create privacy manager with configured policy
    policy = RetentionPolicy(
        operational_days=config.get("operational_days", 7),
        training_days=config.get("training_days", 30),
        user_consent_required=config.get("user_consent_required", True),
        auto_cleanup_enabled=config.get("auto_cleanup_enabled", True)
    )
    
    privacy_manager = PrivacyManager(db_path, policy)
    
    print("✅ Privacy tables created")
    print(f"📅 Operational retention: {policy.operational_days} days")
    print(f"🎓 Training retention: {policy.training_days} days")
    print(f"🔒 Consent required: {policy.user_consent_required}")
    
    return privacy_manager


def apply_retention_cleanup(privacy_manager: PrivacyManager, dry_run: bool = True):
    """Apply retention policies to existing data."""
    print(f"🧹 {'Simulating' if dry_run else 'Applying'} retention cleanup...")
    
    results = privacy_manager.apply_retention_policy(dry_run=dry_run)
    
    print(f"📊 Messages to be cleaned up: {results['messages_to_delete']}")
    print(f"📅 Cutoff date: {results['operational_cutoff']}")
    
    if results['actions_taken']:
        for action in results['actions_taken']:
            print(f"✅ {action}")
    elif dry_run:
        print("🔍 This was a dry run - no actual changes made")
    else:
        print("ℹ️ No cleanup needed")
    
    return results


def backup_database(db_path: str, backup_dir: str = "backups"):
    """Create a backup of the database before making changes."""
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_path / f"bot_conversations_backup_{timestamp}.db"
    
    print(f"💾 Creating database backup: {backup_file}")
    
    import shutil
    shutil.copy2(db_path, backup_file)
    
    print(f"✅ Backup created: {backup_file}")
    return str(backup_file)


def main():
    parser = argparse.ArgumentParser(description="Setup privacy management for SCI-Assist bot")
    parser.add_argument("--db-path", default="bot_conversations.db", help="Path to bot database")
    parser.add_argument("--action", 
                       choices=["setup", "cleanup", "status", "backup", "all"], 
                       default="status",
                       help="Action to perform")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what would be done without making changes")
    parser.add_argument("--config", default="privacy_config.json",
                       help="Privacy configuration file")
    parser.add_argument("--force", action="store_true",
                       help="Force actions without confirmation")
    
    args = parser.parse_args()
    
    # Load configuration
    config_path = Path(args.config)
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
    else:
        # Default configuration
        config = {
            "operational_days": 7,
            "training_days": 30,
            "user_consent_required": True,
            "auto_cleanup_enabled": True
        }
        
        # Save default config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"📝 Created default config: {config_path}")
    
    print(f"🔧 Privacy Setup for SCI-Assist Bot")
    print(f"📁 Database: {args.db_path}")
    print(f"⚙️  Configuration: {config}")
    print()
    
    # Check if database exists
    if not Path(args.db_path).exists():
        print(f"❌ Database not found: {args.db_path}")
        return 1
    
    # Create backup if making changes
    if args.action in ["setup", "cleanup", "all"] and not args.dry_run:
        if not args.force:
            response = input("❓ Create database backup before proceeding? (y/N): ")
            if response.lower().startswith('y'):
                backup_database(args.db_path)
        else:
            backup_database(args.db_path)
    
    if args.action in ["setup", "all"]:
        privacy_manager = setup_privacy_system(args.db_path, config)
    else:
        # Create privacy manager for other operations
        policy = RetentionPolicy(**{k: v for k, v in config.items() if k in [
            "operational_days", "training_days", "user_consent_required", "auto_cleanup_enabled"
        ]})
        privacy_manager = PrivacyManager(args.db_path, policy)
    
    if args.action in ["cleanup", "all"]:
        if not args.dry_run and not args.force:
            print("⚠️  Warning: This will permanently modify conversation data!")
            response = input("❓ Continue with cleanup? (y/N): ")
            if not response.lower().startswith('y'):
                print("❌ Cleanup cancelled")
                return 0
        
        apply_retention_cleanup(privacy_manager, dry_run=args.dry_run)
    
    if args.action in ["status", "all"]:
        # Show current database status
        conn = sqlite3.connect(args.db_path)
        
        # Check if privacy tables exist
        tables = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name IN ('user_consent', 'data_retention_log')
        """).fetchall()
        
        print(f"\n📊 Database Status:")
        print(f"Privacy tables: {len(tables)}/2 present")
        
        # Message counts
        message_count = conn.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = 0").fetchone()[0]
        deleted_count = conn.execute("SELECT COUNT(*) FROM messages WHERE is_deleted = 1").fetchone()[0]
        user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        
        print(f"Active messages: {message_count}")
        print(f"Deleted messages: {deleted_count}")
        print(f"Total users: {user_count}")
        
        # Consent status if tables exist
        if len(tables) == 2:
            consent_count = conn.execute("SELECT COUNT(*) FROM user_consent").fetchone()[0]
            consented_users = conn.execute("""
            SELECT COUNT(*) FROM user_consent 
            WHERE data_retention_consent = 1
            """).fetchone()[0]
            
            print(f"Users with consent records: {consent_count}")
            print(f"Users consented to retention: {consented_users}")
        
        conn.close()
    
    print("\n✅ Privacy setup completed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
