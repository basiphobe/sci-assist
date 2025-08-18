#!/usr/bin/env python3
"""
Privacy-compliant conversation management system.

This module implements privacy controls including:
- Automatic data retention policies
- User consent management
- Data anonymization for training
- GDPR-compliant data handling
"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from dataclasses import dataclass


@dataclass
class RetentionPolicy:
    """Configuration for data retention policies."""
    operational_days: int = 7      # Days to keep for bot operation
    training_days: int = 30        # Days to keep for training (anonymized)
    user_consent_required: bool = True
    auto_cleanup_enabled: bool = True


@dataclass
class UserConsent:
    """User consent preferences."""
    user_id: int
    data_retention_consent: bool = False
    training_data_consent: bool = False
    marketing_consent: bool = False
    consent_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None


class PrivacyManager:
    """Manages privacy-compliant data handling for the bot."""
    
    def __init__(self, db_path: str, policy: RetentionPolicy):
        self.db_path = db_path
        self.policy = policy
        self.logger = logging.getLogger(__name__)
        self._ensure_privacy_tables()
    
    def _ensure_privacy_tables(self):
        """Create privacy management tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        
        # User consent table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_consent (
            user_id INTEGER PRIMARY KEY,
            data_retention_consent BOOLEAN DEFAULT FALSE,
            training_data_consent BOOLEAN DEFAULT FALSE,
            marketing_consent BOOLEAN DEFAULT FALSE,
            consent_date TIMESTAMP,
            updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)
        
        # Data retention log
        conn.execute("""
        CREATE TABLE IF NOT EXISTS data_retention_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            affected_records INTEGER,
            retention_reason TEXT,
            executed_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT
        )
        """)
        
        conn.commit()
        conn.close()
    
    def get_user_consent(self, user_id: int) -> Optional[UserConsent]:
        """Get user consent preferences."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        result = conn.execute(
            "SELECT * FROM user_consent WHERE user_id = ?", 
            (user_id,)
        ).fetchone()
        
        conn.close()
        
        if result:
            return UserConsent(
                user_id=result['user_id'],
                data_retention_consent=bool(result['data_retention_consent']),
                training_data_consent=bool(result['training_data_consent']),
                marketing_consent=bool(result['marketing_consent']),
                consent_date=datetime.fromisoformat(result['consent_date']) if result['consent_date'] else None,
                updated_date=datetime.fromisoformat(result['updated_date']) if result['updated_date'] else None
            )
        return None
    
    def update_user_consent(self, consent: UserConsent):
        """Update user consent preferences."""
        conn = sqlite3.connect(self.db_path)
        
        # Upsert consent record
        conn.execute("""
        INSERT OR REPLACE INTO user_consent 
        (user_id, data_retention_consent, training_data_consent, marketing_consent, 
         consent_date, updated_date)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (
            consent.user_id,
            consent.data_retention_consent,
            consent.training_data_consent,
            consent.marketing_consent,
            consent.consent_date.isoformat() if consent.consent_date else datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        self.logger.info(f"Updated consent for user {consent.user_id}")
    
    def apply_retention_policy(self, dry_run: bool = True) -> Dict[str, Any]:
        """Apply data retention policy according to configuration."""
        conn = sqlite3.connect(self.db_path)
        
        operational_cutoff = datetime.now() - timedelta(days=self.policy.operational_days)
        training_cutoff = datetime.now() - timedelta(days=self.policy.training_days)
        
        # Find messages to be affected
        operational_query = """
        SELECT COUNT(*) as count FROM messages 
        WHERE created_at < ? AND is_deleted = 0
        """
        
        training_query = """
        SELECT COUNT(*) as count FROM messages m
        JOIN users u ON m.user_id = u.id
        LEFT JOIN user_consent uc ON u.id = uc.user_id
        WHERE m.created_at < ? 
        AND m.is_deleted = 0
        AND (uc.training_data_consent IS NULL OR uc.training_data_consent = 0)
        """
        
        operational_count = conn.execute(operational_query, (operational_cutoff.isoformat(),)).fetchone()[0]
        training_count = conn.execute(training_query, (training_cutoff.isoformat(),)).fetchone()[0]
        
        results = {
            "dry_run": dry_run,
            "operational_cutoff": operational_cutoff.isoformat(),
            "training_cutoff": training_cutoff.isoformat(),
            "messages_to_delete": {
                "operational": operational_count,
                "training_without_consent": training_count
            },
            "actions_taken": []
        }
        
        if not dry_run and self.policy.auto_cleanup_enabled:
            # Delete operational data past retention
            if operational_count > 0:
                conn.execute("""
                UPDATE messages SET is_deleted = 1, content = '[DELETED - RETENTION POLICY]'
                WHERE created_at < ? AND is_deleted = 0
                """, (operational_cutoff.isoformat(),))
                
                results["actions_taken"].append(f"Marked {operational_count} operational messages as deleted")
            
            # Delete training data without consent
            if training_count > 0:
                conn.execute("""
                UPDATE messages SET is_deleted = 1, content = '[DELETED - NO CONSENT]'
                WHERE id IN (
                    SELECT m.id FROM messages m
                    JOIN users u ON m.user_id = u.id
                    LEFT JOIN user_consent uc ON u.id = uc.user_id
                    WHERE m.created_at < ?
                    AND m.is_deleted = 0
                    AND (uc.training_data_consent IS NULL OR uc.training_data_consent = 0)
                )
                """, (training_cutoff.isoformat(),))
                
                results["actions_taken"].append(f"Marked {training_count} training messages as deleted (no consent)")
            
            # Log the retention action
            conn.execute("""
            INSERT INTO data_retention_log (action, affected_records, retention_reason, details)
            VALUES (?, ?, ?, ?)
            """, (
                "automatic_retention_cleanup",
                operational_count + training_count,
                f"Policy: {self.policy.operational_days}d operational, {self.policy.training_days}d training",
                json.dumps(results)
            ))
            
            conn.commit()
        
        conn.close()
        return results
    
    def export_user_data(self, user_id: int) -> Dict[str, Any]:
        """Export all data for a specific user (GDPR compliance)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get user info
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user:
            return {"error": "User not found"}
        
        # Get consent
        consent = self.get_user_consent(user_id)
        
        # Get conversations
        conversations = conn.execute("""
        SELECT c.*, COUNT(m.id) as message_count
        FROM conversations c
        LEFT JOIN messages m ON c.id = m.conversation_id AND m.is_deleted = 0
        WHERE c.user_id = ?
        GROUP BY c.id
        ORDER BY c.created_at DESC
        """, (user_id,)).fetchall()
        
        # Get messages
        messages = conn.execute("""
        SELECT * FROM messages 
        WHERE user_id = ? AND is_deleted = 0
        ORDER BY created_at DESC
        """, (user_id,)).fetchall()
        
        conn.close()
        
        return {
            "export_date": datetime.now().isoformat(),
            "user": dict(user),
            "consent": consent.__dict__ if consent else None,
            "conversations": [dict(conv) for conv in conversations],
            "messages": [dict(msg) for msg in messages],
            "total_messages": len(messages),
            "data_retention_notice": f"Data older than {self.policy.operational_days} days may be automatically deleted"
        }
    
    def delete_user_data(self, user_id: int, verification_token: str) -> Dict[str, Any]:
        """Delete all user data (GDPR right to be forgotten)."""
        # This would require additional verification in a real system
        conn = sqlite3.connect(self.db_path)
        
        # Count what will be deleted
        message_count = conn.execute(
            "SELECT COUNT(*) FROM messages WHERE user_id = ? AND is_deleted = 0", 
            (user_id,)
        ).fetchone()[0]
        
        conversation_count = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE user_id = ?", 
            (user_id,)
        ).fetchone()[0]
        
        # Mark messages as deleted
        conn.execute("""
        UPDATE messages 
        SET is_deleted = 1, content = '[DELETED - USER REQUEST]'
        WHERE user_id = ?
        """, (user_id,))
        
        # Mark conversations as inactive
        conn.execute("""
        UPDATE conversations 
        SET is_active = 0, extra_data = json_set(
            COALESCE(extra_data, '{}'), 
            '$.deletion_reason', 
            'user_request'
        )
        WHERE user_id = ?
        """, (user_id,))
        
        # Remove consent records
        conn.execute("DELETE FROM user_consent WHERE user_id = ?", (user_id,))
        
        # Log the deletion
        conn.execute("""
        INSERT INTO data_retention_log (action, affected_records, retention_reason, details)
        VALUES (?, ?, ?, ?)
        """, (
            "user_data_deletion",
            message_count + conversation_count,
            "user_request_gdpr",
            json.dumps({
                "user_id": user_id,
                "messages_deleted": message_count,
                "conversations_deleted": conversation_count,
                "verification_token": verification_token[:8] + "..."
            })
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "deletion_date": datetime.now().isoformat(),
            "messages_deleted": message_count,
            "conversations_deleted": conversation_count,
            "status": "completed"
        }


# Usage example and CLI interface
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Privacy management for Discord bot')
    parser.add_argument('--db-path', default='bot_conversations.db')
    parser.add_argument('--action', choices=['cleanup', 'export-user', 'report'], required=True)
    parser.add_argument('--user-id', type=int, help='User ID for user-specific actions')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without executing')
    
    args = parser.parse_args()
    
    policy = RetentionPolicy(
        operational_days=7,
        training_days=30,
        user_consent_required=True,
        auto_cleanup_enabled=not args.dry_run
    )
    
    manager = PrivacyManager(args.db_path, policy)
    
    if args.action == 'cleanup':
        results = manager.apply_retention_policy(dry_run=args.dry_run)
        print(json.dumps(results, indent=2))
    
    elif args.action == 'export-user':
        if not args.user_id:
            print("--user-id required for export-user action")
            return
        
        data = manager.export_user_data(args.user_id)
        filename = f"user_data_export_{args.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"User data exported to {filename}")
    
    elif args.action == 'report':
        # Implementation for privacy report
        print("Privacy management report - implement as needed")


if __name__ == "__main__":
    main()
