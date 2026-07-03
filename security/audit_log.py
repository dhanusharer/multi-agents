import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

class AuditLogger:
    """Append-only structured audit logger for Kisan Saathi."""

    def __init__(self, log_path: Optional[str] = None):
        if log_path:
            self.log_file = Path(log_path)
        else:
            self.log_file = Path(__file__).parent / "audit_log.json"
        
        # Ensure parent directories exist
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        # Create empty file if not exists
        if not self.log_file.exists():
            with open(self.log_file, "w", encoding="utf-8") as f:
                pass

    def _hash_dict(self, d: Dict[str, Any]) -> str:
        """Helper to generate a stable SHA-256 hash of a dictionary."""
        try:
            serialized = json.dumps(d, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        except Exception:
            return "hash_failed"

    def _write_entry(self, entry: Dict[str, Any]) -> None:
        """Write single entry to the audit log."""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"Audit log write failed: {e}")

    def log_tool_call(
        self,
        session_id: str,
        agent_name: str,
        tool_name: str,
        input_dict: Dict[str, Any],
        output_dict: Dict[str, Any],
        success: bool,
        latency_ms: float
    ) -> None:
        """Log a tool execution event using hashes to protect privacy."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "event_type": "tool_call",
            "agent": agent_name,
            "tool": tool_name,
            "input_hash": self._hash_dict(input_dict),
            "output_hash": self._hash_dict(output_dict),
            "success": success,
            "latency_ms": latency_ms,
            "language": input_dict.get("language", "unknown")
        }
        self._write_entry(entry)

    def log_query(self, session_id: str, agent_name: str, query: str, language: str, intent: str) -> None:
        """Log an incoming user query."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "event_type": "user_query",
            "agent": agent_name,
            "query_hash": hashlib.sha256(query.encode("utf-8")).hexdigest(),
            "language": language,
            "intent": intent
        }
        self._write_entry(entry)

    def log_response(self, session_id: str, agent_name: str, response_length: int, latency_ms: float, language: str) -> None:
        """Log an outgoing response event."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "event_type": "agent_response",
            "agent": agent_name,
            "response_length": response_length,
            "latency_ms": latency_ms,
            "language": language
        }
        self._write_entry(entry)

    def log_security_event(self, session_id: str, event_type: str, details: str, blocked: bool) -> None:
        """Log security occurrences like blocked prompt injections or output violations."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "event_type": f"security_{event_type}",
            "details": details,
            "blocked": blocked
        }
        self._write_entry(entry)

    def get_stats(self) -> Dict[str, Any]:
        """Read log and generate statistics for dashboard or evaluations."""
        stats = {
            "total_queries": 0,
            "total_tool_calls": 0,
            "failed_tool_calls": 0,
            "security_blocks": 0,
            "by_language": {},
            "by_intent": {}
        }
        if not self.log_file.exists():
            return stats

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    ev_type = entry.get("event_type", "")
                    
                    if ev_type == "user_query":
                        stats["total_queries"] += 1
                        lang = entry.get("language", "unknown")
                        intent = entry.get("intent", "unknown")
                        stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1
                        stats["by_intent"][intent] = stats["by_intent"].get(intent, 0) + 1
                    
                    elif ev_type == "tool_call":
                        stats["total_tool_calls"] += 1
                        if not entry.get("success", True):
                            stats["failed_tool_calls"] += 1
                    
                    elif ev_type.startswith("security_"):
                        if entry.get("blocked", True):
                            stats["security_blocks"] += 1
        except Exception as e:
            print(f"Error reading stats: {e}")
        
        return stats

    def contains_tool_call(self, tool_name: str) -> bool:
        """Verify if a specific tool was ever called (useful for evals)."""
        if not self.log_file.exists():
            return False
        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    entry = json.loads(line)
                    if entry.get("event_type") == "tool_call" and entry.get("tool") == tool_name:
                        return True
        except Exception:
            pass
        return False
