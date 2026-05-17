"""
MACT v2.0 - Learning Analytics Dashboard
Features: Progress Tracking, Knowledge Radar, Forecasting, Metrics
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import math


@dataclass
class StudySession:
    session_id: str
    user_id: str
    start_time: str
    end_time: str
    concepts_studied: List[str]
    quiz_scores: List[float]
    time_spent_minutes: int
    streak_count: int


@dataclass
class UserMetrics:
    total_study_time_minutes: int
    concepts_mastered: int
    concepts_in_progress: int
    total_concepts: int
    current_streak_days: int
    longest_streak_days: int
    average_quiz_score: float
    accuracy_trend: List[float]  # Last 10 quizzes
    study_heatmap: Dict[str, int]  # Day -> minutes studied
    mastery_by_topic: Dict[str, float]


@dataclass
class KnowledgeRadarPoint:
    topic: str
    strength: float  # 0.0-1.0
    subtopics: Dict[str, float]


@dataclass
class MasteryForecast:
    concept_id: str
    current_mastery: float
    predicted_mastery_date: str
    confidence: float
    recommended_study_minutes: int


class AnalyticsDashboard:
    def __init__(self, memory_client=None):
        self.memory = memory_client
        self.sessions: List[StudySession] = []
        self.metrics_cache: Optional[UserMetrics] = None
        
    def log_session(self, session: StudySession):
        """Log a study session"""
        self.sessions.append(session)
        
        if self.memory:
            self.memory.store(f"session_{session.session_id}", asdict(session))
        
        # Invalidate cache
        self.metrics_cache = None
    
    def calculate_metrics(self, user_id: str) -> UserMetrics:
        """Calculate comprehensive user metrics"""
        if self.metrics_cache:
            return self.metrics_cache
        
        if not self.sessions:
            # Return empty metrics
            return UserMetrics(
                total_study_time_minutes=0,
                concepts_mastered=0,
                concepts_in_progress=0,
                total_concepts=0,
                current_streak_days=0,
                longest_streak_days=0,
                average_quiz_score=0.0,
                accuracy_trend=[],
                study_heatmap={},
                mastery_by_topic={}
            )
        
        # Total study time
        total_time = sum(s.time_spent_minutes for s in self.sessions)
        
        # Concepts analysis
        all_concepts = set()
        concept_scores = {}
        
        for session in self.sessions:
            for concept in session.concepts_studied:
                all_concepts.add(concept)
                if concept not in concept_scores:
                    concept_scores[concept] = []
                concept_scores[concept].extend(session.quiz_scores)
        
        # Calculate mastery per concept
        mastery_by_topic = {}
        mastered_count = 0
        in_progress_count = 0
        
        for concept, scores in concept_scores.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            mastery_by_topic[concept] = avg_score
            
            if avg_score >= 0.8:
                mastered_count += 1
            elif avg_score > 0.3:
                in_progress_count += 1
        
        # Streak calculation
        session_dates = sorted(set(
            datetime.fromisoformat(s.start_time).date()
            for s in self.sessions
        ))
        
        current_streak = self._calculate_current_streak(session_dates)
        longest_streak = self._calculate_longest_streak(session_dates)
        
        # Average quiz score
        all_scores = [score for s in self.sessions for score in s.quiz_scores]
        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        
        # Accuracy trend (last 10 quizzes)
        accuracy_trend = all_scores[-10:] if len(all_scores) >= 10 else all_scores
        
        # Study heatmap (last 30 days)
        study_heatmap = self._generate_study_heatmap()
        
        self.metrics_cache = UserMetrics(
            total_study_time_minutes=total_time,
            concepts_mastered=mastered_count,
            concepts_in_progress=in_progress_count,
            total_concepts=len(all_concepts),
            current_streak_days=current_streak,
            longest_streak_days=longest_streak,
            average_quiz_score=avg_score,
            accuracy_trend=accuracy_trend,
            study_heatmap=study_heatmap,
            mastery_by_topic=mastery_by_topic
        )
        
        return self.metrics_cache
    
    def _calculate_current_streak(self, dates: List) -> int:
        """Calculate current study streak"""
        if not dates:
            return 0
        
        today = datetime.now().date()
        streak = 0
        
        # Check from today backwards
        current_date = today
        while current_date in dates:
            streak += 1
            current_date -= timedelta(days=1)
        
        # If didn't study today, check from yesterday
        if streak == 0 and (today - timedelta(days=1)) in dates:
            current_date = today - timedelta(days=1)
            while current_date in dates:
                streak += 1
                current_date -= timedelta(days=1)
        
        return streak
    
    def _calculate_longest_streak(self, dates: List) -> int:
        """Calculate longest study streak"""
        if not dates:
            return 0
        
        sorted_dates = sorted(dates)
        longest = 1
        current = 1
        
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                current += 1
                longest = max(longest, current)
            else:
                current = 1
        
        return longest
    
    def _generate_study_heatmap(self) -> Dict[str, int]:
        """Generate study heatmap for last 30 days"""
        heatmap = {}
        today = datetime.now().date()
        
        for i in range(30):
            date = today - timedelta(days=i)
            date_str = date.strftime("%Y-%m-%d")
            
            # Sum minutes studied on this date
            minutes = sum(
                s.time_spent_minutes
                for s in self.sessions
                if datetime.fromisoformat(s.start_time).date() == date
            )
            
            heatmap[date_str] = minutes
        
        return heatmap
    
    def generate_knowledge_radar(self, mastery_by_topic: Dict[str, float]) -> List[KnowledgeRadarPoint]:
        """Generate knowledge radar data for visualization"""
        radar_points = []
        
        # Group topics by category (simplified - in production use concept graph)
        categories = {
            "Foundations": [],
            "Intermediate": [],
            "Advanced": []
        }
        
        for topic, strength in mastery_by_topic.items():
            # Simple categorization based on topic name (replace with actual graph)
            if any(word in topic.lower() for word in ["basic", "intro", "fundamental"]):
                categories["Foundations"].append((topic, strength))
            elif any(word in topic.lower() for word in ["advanced", "complex", "optimization"]):
                categories["Advanced"].append((topic, strength))
            else:
                categories["Intermediate"].append((topic, strength))
        
        for category, topics in categories.items():
            if topics:
                avg_strength = sum(s for _, s in topics) / len(topics)
                subtopics = {t: s for t, s in topics}
                
                radar_points.append(KnowledgeRadarPoint(
                    topic=category,
                    strength=avg_strength,
                    subtopics=subtopics
                ))
        
        return radar_points
    
    def forecast_mastery(
        self, 
        concept_id: str, 
        current_mastery: float,
        study_rate: float  # mastery gain per hour
    ) -> MasteryForecast:
        """Predict when user will master a concept"""
        target_mastery = 0.8  # 80% = mastered
        
        if current_mastery >= target_mastery:
            return MasteryForecast(
                concept_id=concept_id,
                current_mastery=current_mastery,
                predicted_mastery_date=datetime.now().strftime("%Y-%m-%d"),
                confidence=1.0,
                recommended_study_minutes=0
            )
        
        remaining = target_mastery - current_mastery
        
        if study_rate <= 0:
            # No progress rate available
            return MasteryForecast(
                concept_id=concept_id,
                current_mastery=current_mastery,
                predicted_mastery_date="Unknown",
                confidence=0.0,
                recommended_study_minutes=60
            )
        
        hours_needed = remaining / study_rate
        days_needed = max(1, math.ceil(hours_needed / 2))  # Assume 2h study/day
        
        predicted_date = datetime.now() + timedelta(days=days_needed)
        
        # Confidence based on consistency of study
        confidence = min(0.95, 0.5 + (len(self.sessions) / 20))
        
        return MasteryForecast(
            concept_id=concept_id,
            current_mastery=current_mastery,
            predicted_mastery_date=predicted_date.strftime("%Y-%m-%d"),
            confidence=confidence,
            recommended_study_minutes=int(hours_needed * 60)
        )
    
    def get_dashboard_data(self, user_id: str) -> Dict:
        """Get complete dashboard data for frontend"""
        metrics = self.calculate_metrics(user_id)
        radar = self.generate_knowledge_radar(metrics.mastery_by_topic)
        
        # Generate forecasts for top 5 concepts in progress
        forecasts = []
        sorted_concepts = sorted(
            [(k, v) for k, v in metrics.mastery_by_topic.items() if v < 0.8],
            key=lambda x: x[1]
        )[:5]
        
        for concept_id, mastery in sorted_concepts:
            # Estimate study rate from historical data (simplified)
            study_rate = 0.05  # 5% mastery gain per hour (placeholder)
            forecast = self.forecast_mastery(concept_id, mastery, study_rate)
            forecasts.append(asdict(forecast))
        
        return {
            "metrics": asdict(metrics),
            "radar": [asdict(r) for r in radar],
            "forecasts": forecasts,
            "generated_at": datetime.now().isoformat()
        }


# Example usage
if __name__ == "__main__":
    dashboard = AnalyticsDashboard()
    
    # Simulate study sessions
    for i in range(10):
        session = StudySession(
            session_id=f"session_{i}",
            user_id="user_001",
            start_time=(datetime.now() - timedelta(days=9-i)).isoformat(),
            end_time=(datetime.now() - timedelta(days=9-i) + timedelta(hours=1)).isoformat(),
            concepts_studied=["neural_networks", "backpropagation"] if i % 2 == 0 else ["activation_functions", "optimization"],
            quiz_scores=[0.7 + (i * 0.03), 0.8 + (i * 0.02)],
            time_spent_minutes=45 + (i * 5),
            streak_count=i+1
        )
        dashboard.log_session(session)
    
    # Get dashboard data
    data = dashboard.get_dashboard_data("user_001")
    
    print("=== LEARNING ANALYTICS DASHBOARD ===\n")
    print(f"Total Study Time: {data['metrics']['total_study_time_minutes']} minutes")
    print(f"Concepts Mastered: {data['metrics']['concepts_mastered']}")
    print(f"Current Streak: {data['metrics']['current_streak_days']} days")
    print(f"Average Quiz Score: {data['metrics']['average_quiz_score']:.2%}")
    print(f"Longest Streak: {data['metrics']['longest_streak_days']} days")
    
    print("\n=== KNOWLEDGE RADAR ===")
    for point in data['radar']:
        print(f"  {point['topic']}: {point['strength']:.2%}")
    
    print("\n=== MASTERY FORECASTS ===")
    for forecast in data['forecasts']:
        print(f"  {forecast['concept_id']}: {forecast['current_mastery']:.2%} → Mastered by {forecast['predicted_mastery_date']}")
        print(f"    Confidence: {forecast['confidence']:.2%}, Recommended: {forecast['recommended_study_minutes']} min")
