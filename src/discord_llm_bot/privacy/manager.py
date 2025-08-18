"""
Privacy management implementation for Discord bot.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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
    
    def should_store_message(self, user_id: int) -> bool:
        """Check if we should store messages for this user based on consent."""
        if not self.policy.user_consent_required:
            return True
            
        consent = self.get_user_consent(user_id)
        if not consent:
            # Default to minimal storage if no consent given
            return False
            
        return consent.data_retention_consent
    
    def apply_retention_policy(self, dry_run: bool = True) -> Dict[str, Any]:
        """Apply data retention policy according to configuration."""
        conn = sqlite3.connect(self.db_path)
        
        operational_cutoff = datetime.now() - timedelta(days=self.policy.operational_days)
        
        # Find messages to be affected
        operational_query = """
        SELECT COUNT(*) as count FROM messages 
        WHERE created_at < ? AND is_deleted = 0
        """
        
        operational_count = conn.execute(operational_query, (operational_cutoff.isoformat(),)).fetchone()[0]
        
        results = {
            "dry_run": dry_run,
            "operational_cutoff": operational_cutoff.isoformat(),
            "messages_to_delete": operational_count,
            "actions_taken": []
        }
        
        if not dry_run and self.policy.auto_cleanup_enabled and operational_count > 0:
            # Mark old messages as deleted
            conn.execute("""
            UPDATE messages SET is_deleted = 1, content = '[DELETED - RETENTION POLICY]'
            WHERE created_at < ? AND is_deleted = 0
            """, (operational_cutoff.isoformat(),))
            
            results["actions_taken"].append(f"Marked {operational_count} messages as deleted")
            
            # Log the retention action
            conn.execute("""
            INSERT INTO data_retention_log (action, affected_records, retention_reason, details)
            VALUES (?, ?, ?, ?)
            """, (
                "automatic_retention_cleanup",
                operational_count,
                f"Policy: {self.policy.operational_days}d operational retention",
                json.dumps(results)
            ))
            
            conn.commit()
        
        conn.close()
        return results
