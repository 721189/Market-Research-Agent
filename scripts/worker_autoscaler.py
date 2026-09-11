#!/usr/bin/env python3
"""
Celery Queue-Specific Dynamic Autoscaler.
Monitors queue depth, queue age, and task latency to compute recommended worker replica counts.
Autoscales independently across:
- research.quick (Many burstable lightweight replicas, target latency 30-60s)
- research.deep (Controlled replicas, network/LLM intensive)
- analysis (Deterministic computation & sensitivity matrices)
- reports (PDF rendering workers)
"""

import time
import os
import logging
from typing import Dict, Any

logger = logging.getLogger("marketai.autoscaler")

QUEUE_AUTOSCALE_POLICIES = {
    "research.quick": {
        "min_replicas": 4,
        "max_replicas": 40,
        "scale_up_threshold_depth": 5,
        "scale_up_threshold_age_sec": 10,
        "scale_down_idle_sec": 60,
        "target_concurrency_per_worker": 4
    },
    "research.deep": {
        "min_replicas": 2,
        "max_replicas": 15,
        "scale_up_threshold_depth": 3,
        "scale_up_threshold_age_sec": 30,
        "scale_down_idle_sec": 120,
        "target_concurrency_per_worker": 2
    },
    "analysis": {
        "min_replicas": 2,
        "max_replicas": 20,
        "scale_up_threshold_depth": 4,
        "scale_up_threshold_age_sec": 15,
        "scale_down_idle_sec": 60,
        "target_concurrency_per_worker": 4
    },
    "reports": {
        "min_replicas": 1,
        "max_replicas": 10,
        "scale_up_threshold_depth": 5,
        "scale_up_threshold_age_sec": 20,
        "scale_down_idle_sec": 90,
        "target_concurrency_per_worker": 2
    }
}

class QueueAutoscaler:
    def __init__(self, redis_client=None):
        self.redis = redis_client

    def get_queue_depth(self, queue_name: str) -> int:
        if not self.redis:
            return 0
        try:
            return int(self.redis.llen(queue_name) or 0)
        except Exception:
            return 0

    def calculate_desired_replicas(self, queue_name: str, current_depth: int, oldest_task_age_sec: float = 0.0) -> int:
        policy = QUEUE_AUTOSCALE_POLICIES.get(queue_name, QUEUE_AUTOSCALE_POLICIES["research.quick"])
        min_rep = policy["min_replicas"]
        max_rep = policy["max_replicas"]
        concurrency = policy["target_concurrency_per_worker"]

        if current_depth == 0:
            return min_rep

        # Needed workers = ceil(current_depth / concurrency)
        needed = (current_depth + concurrency - 1) // concurrency

        # If queue age is high, boost scaling factor
        if oldest_task_age_sec > policy["scale_up_threshold_age_sec"]:
            needed = int(needed * 1.5) + 1

        return max(min_rep, min(max_rep, needed))

    def run_autoscaling_cycle(self) -> Dict[str, Any]:
        recommendations = {}
        for q_name in QUEUE_AUTOSCALE_POLICIES:
            depth = self.get_queue_depth(q_name)
            replicas = self.calculate_desired_replicas(q_name, depth)
            recommendations[q_name] = {
                "current_depth": depth,
                "recommended_replicas": replicas
            }
            logger.info(f"Autoscale recommendation for '{q_name}': Depth={depth} -> Replicas={replicas}")
        return recommendations

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    autoscaler = QueueAutoscaler()
    recs = autoscaler.run_autoscaling_cycle()
    print("Autoscaler recommendations:", recs)
