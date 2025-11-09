"""
Session Manager for Camera Image Analyzer
Handles session creation, storage, and conversation history
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import re


class SessionManager:
    """Manages analysis sessions with conversation history"""
    
    def __init__(self, sessions_dir: str = "sessions"):
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(exist_ok=True)
        self.current_session_id = None
        self.current_session = None
    
    def create_session(self, first_query: str = None) -> str:
        """
        Create a new session
        
        Args:
            first_query: Optional first query to name the session
            
        Returns:
            Session ID
        """
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = self.sessions_dir / session_id
        session_dir.mkdir(exist_ok=True)
        
        # Generate session title from first query or use default
        if first_query:
            title = self._generate_session_title(first_query)
        else:
            title = "New Analysis Session"
        
        session_info = {
            "session_id": session_id,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "title": title,
            "query_count": 0,
            "images_analyzed": 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        conversation = {
            "session_id": session_id,
            "queries": []
        }
        
        # Save session files
        self._save_json(session_dir / "session_info.json", session_info)
        self._save_json(session_dir / "conversation.json", conversation)
        
        self.current_session_id = session_id
        self.current_session = {
            "info": session_info,
            "conversation": conversation,
            "dir": session_dir
        }
        
        return session_id
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """
        Load an existing session
        
        Args:
            session_id: Session ID to load
            
        Returns:
            Session data or None if not found
        """
        session_dir = self.sessions_dir / session_id
        
        if not session_dir.exists():
            return None
        
        try:
            session_info = self._load_json(session_dir / "session_info.json")
            conversation = self._load_json(session_dir / "conversation.json")
            
            self.current_session_id = session_id
            self.current_session = {
                "info": session_info,
                "conversation": conversation,
                "dir": session_dir
            }
            
            return self.current_session
        except Exception as e:
            print(f"Error loading session {session_id}: {e}")
            return None
    
    def get_all_sessions(self) -> List[Dict]:
        """
        Get list of all sessions
        
        Returns:
            List of session info dictionaries
        """
        sessions = []
        
        for session_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            if session_dir.is_dir():
                try:
                    session_info = self._load_json(session_dir / "session_info.json")
                    sessions.append(session_info)
                except:
                    continue
        
        return sessions
    
    def add_query(self, user_query: str, results: Dict, context_used: List[int] = None) -> int:
        """
        Add a query and its results to the current session
        
        Args:
            user_query: User's query text
            results: Analysis results dictionary
            context_used: List of previous query numbers used as context
            
        Returns:
            Query number
        """
        if not self.current_session:
            raise ValueError("No active session. Create or load a session first.")
        
        conversation = self.current_session["conversation"]
        query_num = len(conversation["queries"]) + 1
        
        # Extract key information for summary
        total_images = results.get('total_images', 0)
        matches_found = results.get('matches_found', 0)
        
        # Create summary
        summary = f"Analyzed {total_images} images, found {matches_found} matches"
        
        # Extract key findings (locations with matches)
        key_findings = []
        for result in results.get('detailed_results', [])[:5]:  # Top 5
            if result.get('match'):
                key_findings.append({
                    'location': result.get('location_name', 'Unknown'),
                    'camera_ip': result.get('camera_ip', 'Unknown'),
                    'count': result.get('count', 'N/A')
                })
        
        query_entry = {
            "query_num": query_num,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_query": user_query,
            "context_used": context_used or [],
            "results": results,
            "summary": summary,
            "key_findings": key_findings
        }
        
        conversation["queries"].append(query_entry)
        
        # Update session info
        self.current_session["info"]["query_count"] = query_num
        self.current_session["info"]["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if query_num == 1:
            # Update title based on first query
            self.current_session["info"]["title"] = self._generate_session_title(user_query)
            self.current_session["info"]["images_analyzed"] = total_images
        
        # Save updated session
        self._save_json(
            self.current_session["dir"] / "session_info.json",
            self.current_session["info"]
        )
        self._save_json(
            self.current_session["dir"] / "conversation.json",
            conversation
        )
        
        return query_num
    
    def get_context_for_query(self, max_previous: int = 3) -> str:
        """
        Build context string from previous queries in session
        
        Args:
            max_previous: Maximum number of previous queries to include
            
        Returns:
            Context string
        """
        if not self.current_session:
            return ""
        
        queries = self.current_session["conversation"]["queries"]
        if not queries:
            return ""
        
        context_parts = ["PREVIOUS CONVERSATION CONTEXT:\n"]
        
        # Get last N queries
        recent_queries = queries[-max_previous:] if len(queries) > max_previous else queries
        
        for q in recent_queries:
            context_parts.append(f"\nQuery #{q['query_num']}: {q['user_query']}")
            context_parts.append(f"Summary: {q['summary']}")
            
            if q['key_findings']:
                context_parts.append("Key Locations Found:")
                for finding in q['key_findings']:
                    context_parts.append(
                        f"  - {finding['location']} (IP: {finding['camera_ip']}) - Count: {finding['count']}"
                    )
        
        context_parts.append("\n" + "="*80 + "\n")
        
        return "\n".join(context_parts)
    
    def analyze_query_type(self, query: str) -> Dict[str, Any]:
        """
        Analyze if query is a follow-up or new analysis
        
        Args:
            query: User's query
            
        Returns:
            Dictionary with query analysis
        """
        # Keywords that suggest follow-up queries
        follow_up_keywords = [
            'these', 'those', 'them', 'it', 'previous', 'above', 'earlier',
            'same', 'which of', 'from the', 'based on', 'using',
            'map', 'visualize', 'show me', 'list', 'filter', 'sort'
        ]
        
        query_lower = query.lower()
        
        # Check if it's a follow-up
        is_follow_up = any(keyword in query_lower for keyword in follow_up_keywords)
        
        # Additional check: if session has previous queries
        has_context = bool(
            self.current_session and 
            self.current_session["conversation"]["queries"]
        )
        
        return {
            "is_follow_up": is_follow_up and has_context,
            "requires_new_analysis": not is_follow_up or not has_context,
            "confidence": "high" if is_follow_up else "medium"
        }
    
    def get_previous_results(self, query_num: int = None) -> Optional[Dict]:
        """
        Get results from a previous query
        
        Args:
            query_num: Query number (None for most recent)
            
        Returns:
            Results dictionary or None
        """
        if not self.current_session:
            return None
        
        queries = self.current_session["conversation"]["queries"]
        if not queries:
            return None
        
        if query_num is None:
            return queries[-1]["results"]
        
        for q in queries:
            if q["query_num"] == query_num:
                return q["results"]
        
        return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if successful
        """
        session_dir = self.sessions_dir / session_id
        
        if not session_dir.exists():
            return False
        
        try:
            # Delete all files in session directory
            for file in session_dir.iterdir():
                file.unlink()
            session_dir.rmdir()
            
            # Clear current session if it was deleted
            if self.current_session_id == session_id:
                self.current_session_id = None
                self.current_session = None
            
            return True
        except Exception as e:
            print(f"Error deleting session {session_id}: {e}")
            return False
    
    def _generate_session_title(self, query: str, max_length: int = 40) -> str:
        """Generate a readable title from the first query"""
        # Remove special characters and extra spaces
        title = re.sub(r'[^\w\s]', ' ', query)
        title = ' '.join(title.split())
        
        # Capitalize first letter
        title = title.capitalize()
        
        # Truncate if too long
        if len(title) > max_length:
            title = title[:max_length] + "..."
        
        return title
    
    def _save_json(self, filepath: Path, data: Dict):
        """Save data to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _load_json(self, filepath: Path) -> Dict:
        """Load data from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def export_session(self, session_id: str, output_file: str) -> bool:
        """
        Export session to a single JSON file
        
        Args:
            session_id: Session ID to export
            output_file: Output file path
            
        Returns:
            True if successful
        """
        session = self.load_session(session_id)
        if not session:
            return False
        
        try:
            export_data = {
                "session_info": session["info"],
                "conversation": session["conversation"],
                "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"Error exporting session: {e}")
            return False


