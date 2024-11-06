import json
import os
from datetime import datetime
from typing import Dict, Any
from pathlib import Path
import logging
from dataclasses import asdict

class AnalysisLogger:
    def __init__(self, base_dir: str = "analysis_logs"):
        """Initialize the analysis logger with base directory"""
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dated directory for today's logs
        self.today_dir = self.base_dir / datetime.now().strftime("%Y-%m-%d")
        self.today_dir.mkdir(exist_ok=True)
        
        # Initialize analysis file for today
        self.analysis_file = self.today_dir / "analysis.jsonl"
        
        # Setup logging for debugging
        self.logger = logging.getLogger(__name__)
        
    def _format_timestamp(self) -> str:
        """Format current timestamp for logging"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
    def _sanitize_for_json(self, obj: Any) -> Any:
        """Sanitize objects for JSON serialization"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return obj
        
    def log_analysis(self, 
                    chat_id: int,
                    message_obj: Any,
                    sentiment_analysis: Dict,
                    decision_info: Dict,
                    bot_response: str = None,
                    context_summary: Dict = None) -> None:
        """Log complete analysis of a message and bot's response"""
        try:
            analysis_entry = {
                "timestamp": self._format_timestamp(),
                "chat_id": chat_id,
                "message": {
                    "id": message_obj.id,
                    "content": message_obj.content,
                    "user_id": message_obj.user_id,
                    "keywords": message_obj.keywords,
                },
                "sentiment_analysis": sentiment_analysis,
                "decision_engine": {
                    "should_respond": decision_info.get('should_respond', False),
                    "decision_reason": decision_info.get('decision_reason', 'Unknown'),
                    "debug_info": decision_info
                },
                "context": context_summary,
                "bot_response": bot_response
            }
            
            # Sanitize the entry for JSON serialization
            sanitized_entry = json.loads(
                json.dumps(analysis_entry, default=self._sanitize_for_json)
            )
            
            # Append to today's analysis file
            with open(self.analysis_file, 'a', encoding='utf-8') as f:
                json.dump(sanitized_entry, f, ensure_ascii=False)
                f.write('\n')
                
            self.logger.info(f"Logged analysis for message {message_obj.id}")
            
        except Exception as e:
            self.logger.error(f"Error logging analysis: {str(e)}")
            
    def log_aggregate_stats(self, stats: Dict) -> None:
        """Log aggregate statistics for the day"""
        try:
            stats_file = self.today_dir / "daily_stats.json"
            
            # Update existing stats if file exists
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    existing_stats = json.load(f)
                stats = {**existing_stats, **stats}
            
            with open(stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
                
            self.logger.info("Updated daily statistics")
            
        except Exception as e:
            self.logger.error(f"Error logging daily stats: {str(e)}")
            
    def generate_daily_summary(self) -> Dict:
        """Generate summary of today's analysis"""
        try:
            if not self.analysis_file.exists():
                return {"error": "No analysis file found for today"}
                
            summary = {
                "total_messages": 0,
                "responses_sent": 0,
                "sentiment_distribution": {
                    "positive": 0,
                    "neutral": 0,
                    "negative": 0
                },
                "decision_reasons": {},
                "most_common_keywords": {},
            }
            
            with open(self.analysis_file, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    summary["total_messages"] += 1
                    
                    if entry.get("bot_response"):
                        summary["responses_sent"] += 1
                    
                    # Categorize sentiment
                    sentiment = entry["sentiment_analysis"]["polarity"]
                    if sentiment > 0.1:
                        summary["sentiment_distribution"]["positive"] += 1
                    elif sentiment < -0.1:
                        summary["sentiment_distribution"]["negative"] += 1
                    else:
                        summary["sentiment_distribution"]["neutral"] += 1
                    
                    # Track decision reasons
                    reason = entry["decision_engine"]["decision_reason"]
                    summary["decision_reasons"][reason] = summary["decision_reasons"].get(reason, 0) + 1
                    
                    # Track keywords
                    for keyword in entry["message"]["keywords"]:
                        summary["most_common_keywords"][keyword] = summary["most_common_keywords"].get(keyword, 0) + 1
            
            # Save summary
            with open(self.today_dir / "daily_summary.json", 'w') as f:
                json.dump(summary, f, indent=2)
                
            return summary
            
        except Exception as e:
            self.logger.error(f"Error generating daily summary: {str(e)}")
            return {"error": str(e)}
