import time
import logging
from typing import List, Dict, Any, Optional
import threading

logger = logging.getLogger("marketai.telemetry.alerting")

class AlertSeverity:
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertRule:
    def __init__(self, name: str, description: str, severity: str, evaluate_fn):
        self.name = name
        self.description = description
        self.severity = severity
        self.evaluate_fn = evaluate_fn
        self.last_triggered: Optional[float] = None
        self.cooldown_seconds: float = 300.0  # 5 minute cooldown

    def check(self) -> Optional[Dict[str, Any]]:
        now = time.time()
        if self.last_triggered and (now - self.last_triggered) < self.cooldown_seconds:
            return None

        is_firing, details = self.evaluate_fn()
        if is_firing:
            self.last_triggered = now
            return {
                "alert": self.name,
                "description": self.description,
                "severity": self.severity,
                "timestamp": now,
                "details": details
            }
        return None

class AlertEngine:
    """
    Evaluates real-time operational thresholds and dispatches notifications
    on SLA violations, high error rates, security anomalies, and queue stagnation.
    """
    def __init__(self):
        self._rules: List[AlertRule] = []
        self._recent_errors: List[float] = []
        self._recent_requests: List[float] = []
        self._lock = threading.Lock()
        self._active_alerts: List[Dict[str, Any]] = []

    def record_request(self, is_error: bool = False) -> None:
        now = time.time()
        cutoff = now - 300.0 # 5-minute rolling window
        with self._lock:
            self._recent_requests = [t for t in self._recent_requests if t >= cutoff] + [now]
            if is_error:
                self._recent_errors = [t for t in self._recent_errors if t >= cutoff] + [now]

    def get_error_rate(self) -> float:
        with self._lock:
            total = len(self._recent_requests)
            if total == 0:
                return 0.0
            return len(self._recent_errors) / float(total)

    def register_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    def evaluate_all(self) -> List[Dict[str, Any]]:
        firing: List[Dict[str, Any]] = []
        for rule in self._rules:
            alert = rule.check()
            if alert:
                firing.append(alert)
                logger.warning(
                    f"ALERT FIRING [{alert['severity']}] {alert['alert']}: {alert['description']} "
                    f"Details: {alert['details']}"
                )
        return firing

alert_engine = AlertEngine()

# Initialize standard operational rules
alert_engine.register_rule(AlertRule(
    name="HighHttpErrorRate",
    description="HTTP 5xx error rate exceeded 5% threshold over the last 5 minutes",
    severity=AlertSeverity.CRITICAL,
    evaluate_fn=lambda: (
        alert_engine.get_error_rate() > 0.05,
        {"current_error_rate": f"{alert_engine.get_error_rate() * 100:.2f}%"}
    )
))
