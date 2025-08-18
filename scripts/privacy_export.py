#!/usr/bin/env python3
"""
Privacy-compliant data export and anonymization script.

This script exports conversation data for training purposes while:
1. Anonymizing all personal identifiers
2. Preserving conversation flow and content quality
3. Creating separate datasets for different training purposes
4. Implementing configurable retention policies
"""

import sqlite3
import json
import hashlib
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse


class PrivacyDataExporter:
    def __init__(self, db_path: str, export_dir: str = "training_data"):
        self.db_path = db_path
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(exist_ok=True)
        
        # User ID to anonymous ID mapping
        self.user_anonymization = {}
        
    def _anonymize_user_id(self, user_id: int) -> str:
        """Convert user ID to consistent anonymous identifier."""
        if user_id not in self.user_anonymization:
            # Create deterministic but anonymous ID
            hash_input = f"user_{user_id}_salt_sci_assist"
            anonymous_id = f"user_{hashlib.sha256(hash_input.encode()).hexdigest()[:8]}"
            self.user_anonymization[user_id] = anonymous_id
        return self.user_anonymization[user_id]
    
    def _anonymize_content(self, content: str) -> str:
        """Remove/anonymize PII from message content."""
        # Remove Discord mentions (@user#1234)
        content = re.sub(r'@[a-zA-Z0-9_]+#\d{4}', '@anonymized_user', content)
        
        # Remove Discord user/channel IDs (<@!123456789> or <#123456789>)
        content = re.sub(r'<[@#!&][0-9]+>', '@anonymized_mention', content)
        
        # Remove potential email addresses
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 
                        '[email_redacted]', content)
        
        # Remove potential phone numbers (basic patterns)
        content = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[phone_redacted]', content)
        
        # Remove URLs but keep the fact that a URL was shared
        content = re.sub(r'https?://[^\s]+', '[url_shared]', content)
        
        return content
    
    def export_training_conversations(self, 
                                    min_messages: int = 3,
                                    days_back: int = 30) -> Dict[str, Any]:
        """Export conversation data suitable for training."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get conversations with sufficient messages for training
        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        query = """
        SELECT c.id as conv_id, c.user_id, c.channel_id, c.guild_id,
               COUNT(m.id) as message_count,
               MIN(m.created_at) as first_message,
               MAX(m.created_at) as last_message
        FROM conversations c
        JOIN messages m ON c.id = m.conversation_id
        WHERE c.created_at >= ? AND m.is_deleted = 0
        GROUP BY c.id
        HAVING COUNT(m.id) >= ?
        ORDER BY c.updated_at DESC
        """
        
        conversations = conn.execute(query, (cutoff_date.isoformat(), min_messages)).fetchall()
        
        training_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_conversations": len(conversations),
                "anonymization_applied": True,
                "retention_days": days_back,
                "min_messages_threshold": min_messages
            },
            "conversations": []
        }
        
        for conv in conversations:
            # Get messages for this conversation
            msg_query = """
            SELECT role, content, created_at, extra_data, user_id
            FROM messages
            WHERE conversation_id = ? AND is_deleted = 0
            ORDER BY created_at ASC
            """
            
            messages = conn.execute(msg_query, (conv['conv_id'],)).fetchall()
            
            anonymized_messages = []
            for msg in messages:
                # Parse extra_data if it exists
                extra_data = {}
                if msg['extra_data']:
                    try:
                        extra_data = json.loads(msg['extra_data']) if isinstance(msg['extra_data'], str) else msg['extra_data']
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                anonymized_msg = {
                    "role": msg['role'],
                    "content": self._anonymize_content(msg['content']),
                    "timestamp": msg['created_at'],
                    "anonymous_user": self._anonymize_user_id(msg['user_id']),
                    "has_attachments": extra_data.get('has_attachments', False) if extra_data else False,
                    "message_length": len(msg['content'])
                }
                anonymized_messages.append(anonymized_msg)
            
            conversation_data = {
                "id": f"conv_{hashlib.sha256(f'{conv['conv_id']}_salt'.encode()).hexdigest()[:12]}",
                "anonymous_channel": f"channel_{hashlib.sha256(f'{conv['channel_id']}_salt'.encode()).hexdigest()[:8]}",
                "message_count": conv['message_count'],
                "duration_hours": (
                    datetime.fromisoformat(conv['last_message']) - 
                    datetime.fromisoformat(conv['first_message'])
                ).total_seconds() / 3600,
                "messages": anonymized_messages
            }
            
            training_data["conversations"].append(conversation_data)
        
        conn.close()
        return training_data
    
    def export_response_quality_data(self) -> Dict[str, Any]:
        """Export data focused on response quality assessment."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get user-assistant message pairs
        query = """
        SELECT 
            m1.content as user_message,
            m2.content as assistant_response,
            m1.created_at as user_timestamp,
            m2.created_at as response_timestamp,
            m1.user_id,
            m1.conversation_id
        FROM messages m1
        JOIN messages m2 ON m1.conversation_id = m2.conversation_id
        WHERE m1.role = 'user' 
        AND m2.role = 'assistant'
        AND m2.created_at > m1.created_at
        AND m1.is_deleted = 0 
        AND m2.is_deleted = 0
        ORDER BY m1.conversation_id, m1.created_at
        """
        
        pairs = conn.execute(query).fetchall()
        
        quality_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_pairs": len(pairs),
                "purpose": "response_quality_training"
            },
            "message_pairs": []
        }
        
        for pair in pairs:
            response_time = (
                datetime.fromisoformat(pair['response_timestamp']) - 
                datetime.fromisoformat(pair['user_timestamp'])
            ).total_seconds()
            
            pair_data = {
                "user_input": self._anonymize_content(pair['user_message']),
                "assistant_output": self._anonymize_content(pair['assistant_response']),
                "response_time_seconds": response_time,
                "input_length": len(pair['user_message']),
                "output_length": len(pair['assistant_response']),
                "anonymous_user": self._anonymize_user_id(pair['user_id'])
            }
            
            quality_data["message_pairs"].append(pair_data)
        
        conn.close()
        return quality_data
    
    def create_retention_report(self) -> Dict[str, Any]:
        """Create a report on current data retention."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Data age analysis
        age_query = """
        SELECT 
            COUNT(*) as total_messages,
            MIN(created_at) as oldest_message,
            MAX(created_at) as newest_message,
            COUNT(DISTINCT user_id) as unique_users,
            COUNT(DISTINCT conversation_id) as total_conversations
        FROM messages 
        WHERE is_deleted = 0
        """
        
        stats = conn.execute(age_query).fetchone()
        
        # Messages by age buckets
        bucket_query = """
        SELECT 
            CASE 
                WHEN created_at >= datetime('now', '-1 day') THEN 'last_24h'
                WHEN created_at >= datetime('now', '-7 days') THEN 'last_week'
                WHEN created_at >= datetime('now', '-30 days') THEN 'last_month'
                WHEN created_at >= datetime('now', '-90 days') THEN 'last_3_months'
                ELSE 'older'
            END as age_bucket,
            COUNT(*) as message_count
        FROM messages 
        WHERE is_deleted = 0
        GROUP BY age_bucket
        """
        
        buckets = conn.execute(bucket_query).fetchall()
        
        conn.close()
        
        return {
            "report_date": datetime.now().isoformat(),
            "overall_stats": dict(stats),
            "age_distribution": {bucket['age_bucket']: bucket['message_count'] for bucket in buckets},
            "recommendations": [
                "Consider implementing 30-day retention for most conversations",
                "Keep anonymized training data separately from operational data",
                "Implement user consent for data retention beyond operational needs",
                "Regular automated cleanup of old conversations"
            ]
        }


def main():
    parser = argparse.ArgumentParser(description='Export and anonymize conversation data')
    parser.add_argument('--db-path', default='bot_conversations.db', help='Path to SQLite database')
    parser.add_argument('--export-dir', default='training_data', help='Export directory')
    parser.add_argument('--action', choices=['export', 'report', 'all'], default='all', 
                       help='Action to perform')
    
    args = parser.parse_args()
    
    exporter = PrivacyDataExporter(args.db_path, args.export_dir)
    
    if args.action in ['export', 'all']:
        print("Exporting training conversations...")
        training_data = exporter.export_training_conversations()
        
        with open(f"{args.export_dir}/training_conversations.json", 'w') as f:
            json.dump(training_data, f, indent=2)
        
        print("Exporting response quality data...")
        quality_data = exporter.export_response_quality_data()
        
        with open(f"{args.export_dir}/response_quality_pairs.json", 'w') as f:
            json.dump(quality_data, f, indent=2)
        
        print(f"Exported {training_data['metadata']['total_conversations']} conversations")
        print(f"Exported {len(quality_data['message_pairs'])} message pairs")
    
    if args.action in ['report', 'all']:
        print("Generating retention report...")
        report = exporter.create_retention_report()
        
        with open(f"{args.export_dir}/retention_report.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        print("\nData Retention Report:")
        print(f"Total messages: {report['overall_stats']['total_messages']}")
        print(f"Unique users: {report['overall_stats']['unique_users']}")
        print(f"Total conversations: {report['overall_stats']['total_conversations']}")
        print("\nAge distribution:")
        for bucket, count in report['age_distribution'].items():
            print(f"  {bucket}: {count} messages")


if __name__ == "__main__":
    main()
