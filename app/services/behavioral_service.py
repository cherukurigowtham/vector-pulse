import json
import logging
import math
from typing import List, Dict, Any
from app.core.redis import r, rk

logger = logging.getLogger(__name__)

class BehavioralAnalyzer:
    """
    Cognitive Sequence Analyzer (Phase 13).
    Analyzes session clickstreams to detect anomalies using attention-inspired logic.
    """
    
    def __init__(self, merchant_id: str, session_id: str, device_hash: str | None = None):
        self.merchant_id = merchant_id
        self.session_id = session_id
        self.device_hash = device_hash
        self.stream_key = rk(f"behavior:stream:{merchant_id}:{session_id}")
        self.dna_key = rk(f"behavior:dna:{device_hash}") if device_hash else None

    async def get_signals(self) -> Dict[str, Any]:
        """
        Retrieves and analyzes the current session stream.
        Calculates entropy, velocity, and pattern deviations.
        """
        raw_events = await r.lrange(self.stream_key, 0, -1)
        if not raw_events:
            return {"score_impact": 0, "reason": "No behavioral signals yet"}

        events = [json.loads(e) for e in raw_events]
        
        # 1. Navigation Entropy (Randomness vs. Intent)
        # Bots typically follow linear or perfectly rhythmic patterns.
        # Humans have high entropy (random jitter, varying dwell times).
        # Suspiciously LOW entropy is a red flag for automation.
        entropy = self._calculate_navigation_entropy(events)
        
        # 2. Form Interaction Velocity (Bot Speed)
        form_velocity_penalty = self._analyze_form_velocity(events)
        
        # 3. Sequence Anomaly (Attention Mechanism)
        # Check for non-standard sequences (e.g., Focus -> Blur -> Click with 0ms dwell)
        sequence_penalty = self._detect_sequence_anomalies(events)
        
        # 4. Neural Transition Probability (Phase 10)
        # Uses a transition matrix to detect impossible automation sequences
        transition_penalty = self._calculate_transition_probability(events)
        
        # 5. DNA Persistence Check (Phase 11)
        # Compare current 'rhythm' with historical DNA for this device
        dna_anomaly = await self._check_dna_persistence(entropy, form_velocity_penalty)
        
        total_impact = min(80.0, float(entropy + form_velocity_penalty + sequence_penalty + transition_penalty + dna_anomaly))
        
        return {
            "score_impact": float(total_impact),
            "entropy": float(f"{float(entropy):.2f}"),
            "form_velocity_score": float(form_velocity_penalty),
            "sequence_anomaly": float(sequence_penalty),
            "transition_anomaly": float(transition_anomaly),
            "dna_anomaly": float(dna_anomaly),
            "event_count": len(events)
        }

    async def _check_dna_persistence(self, current_entropy: float, current_velocity: float) -> float:
        """
        Matches 'Interaction Rhythm' against previous sessions on this device.
        Bots have suspiciously identical DNA fingerprints across sessions.
        """
        if not self.dna_key:
            return 0.0

        # DNA Fingerprint = rounded tuple of entropy/velocity
        dna_fingerprint = f"{round(current_entropy, 1)}:{round(current_velocity, 1)}"
        
        # Check if this exact rhythm already exists for this device
        is_known = await r.sismember(self.dna_key, dna_fingerprint)
        if is_known:
            # If a high-penalty rhythm repeats, it's almost certainly a script.
            if current_entropy > 20 or current_velocity > 20:
                return 40.0 # Extreme Red Flag: Robotic Consistency
            return 15.0 # Low Red Flag: Pattern Re-use
        
        # Store for future sessions (TTL 30 days)
        await r.sadd(self.dna_key, dna_fingerprint)
        await r.expire(self.dna_key, 86400 * 30)
        return 0.0

    def _calculate_navigation_entropy(self, events: List[Dict]) -> float:
        """Calculates randomness in interaction timings."""
        if len(events) < 5: return 0
        
        deltas = []
        for i in range(1, len(events)):
            d = events[i]["timestamp"] - events[i-1]["timestamp"]
            deltas.append(max(0.001, d))
            
        # Standard deviation of log-deltas as a proxy for entropy
        avg = sum(deltas) / len(deltas)
        variance = sum((x - avg) ** 2 for x in deltas) / len(deltas)
        std_dev = math.sqrt(variance)
        
        # Low std_dev in interaction timing suggests a bot (rhythmic/constant speed)
        if std_dev < 0.05: # Extremely rhythmic
            return 25.0
        elif std_dev < 0.2:
            return 10.0
        return 0

    def _analyze_form_velocity(self, events: List[Dict]) -> float:
        """Detects suspiciously fast form fills."""
        blur_events = [e for e in events if e["event_type"] == "blur"]
        if not blur_events: return 0
        
        fast_fills = [e for e in blur_events if e.get("dwell_time_ms", 9999) < 100]
        if len(fast_fills) > 2:
            return 30.0
        return 0

    def _detect_sequence_anomalies(self, events: List[Dict]) -> float:
        """Checks for impossible human sequences."""
        # Example: Focus immediately followed by Click at same timestamp
        anomalies = 0.0
        for i in range(1, len(events)):
            if events[i].get("event_type") == "click" and events[i-1].get("event_type") == "focus":
                if events[i]["timestamp"] - events[i-1]["timestamp"] < 0.01:
                    anomalies += 1.0
        
        return min(20.0, float(anomalies * 10))

    def _calculate_transition_probability(self, events: List[Dict]) -> float:
        """
        Detects automation by analyzing the probability of event transitions.
        Standard Human Norms: focus -> input (0.8), input -> blur (0.7), focus -> click (0.3)
        Bot Anomaly: input -> click (0ms), blur -> focus (instant)
        """
        if len(events) < 3: return 0.0
        
        # Define unlikely/impossible transition penalties
        # Using strings for keys and float for values to appease lints
        PENALTIES = {
            "input_click": 15.0,  # Humans usually blur before clicking away or finishing input
            "blur_focus": 10.0,   # Immediate re-focus is rare for human jitter
            "keydown_click": 20.0 # Extreme automation signal
        }
        
        total_penalty = 0.0
        for i in range(1, len(events)):
            t1 = events[i-1].get("event_type", "unknown")
            t2 = events[i].get("event_type", "unknown")
            delta = events[i]["timestamp"] - events[i-1]["timestamp"]
            
            key = str(f"{t1}_{t2}")
            # Penalize the transition if it matches an anomaly pattern and is too fast
            if key in PENALTIES and delta < 0.05:
                total_penalty += float(PENALTIES[key])
                
        return min(30.0, float(total_penalty))

async def analyze_session_behavior(merchant_email: str, session_id: str, device_hash: str | None = None) -> Dict[str, Any]:
    analyzer = BehavioralAnalyzer(merchant_email, session_id, device_hash)
    return await analyzer.get_signals()
