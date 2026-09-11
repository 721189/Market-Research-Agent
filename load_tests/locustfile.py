import uuid
import json
import time
from locust import HttpUser, task, between, events

class MarketAIStressUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        self.headers = {
            "Authorization": "Bearer mock_perf_test_token",
            "Content-Type": "application/json"
        }
        self.active_tasks = []

    @task(3)
    def fetch_user_profile(self):
        self.client.get("/api/v1/auth/me", headers=self.headers, name="/api/v1/auth/me")

    @task(5)
    def submit_research_job(self):
        job_payload = {
            "product_idea": f"Autonomous AI SDR Agent {uuid.uuid4().hex[:6]}",
            "mode": "quick",
            "idempotency_key": str(uuid.uuid4())
        }
        with self.client.post(
            "/api/v1/research",
            json=job_payload,
            headers=self.headers,
            catch_response=True,
            name="/api/v1/research [POST]"
        ) as response:
            if response.status_code in (200, 202):
                data = response.json()
                task_id = data.get("task_id")
                if task_id:
                    self.active_tasks.append(task_id)
                response.success()
            else:
                response.failure(f"Failed with status: {response.status_code}")

    @task(10)
    def poll_active_tasks(self):
        if not self.active_tasks:
            return
        task_id = self.active_tasks[-1]
        with self.client.get(
            f"/api/v1/research/{task_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/v1/research/{id} [GET]"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                if data.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
                    self.active_tasks.remove(task_id)
                response.success()
            else:
                response.failure(f"Poll failed: {response.status_code}")

    @task(2)
    def check_billing(self):
        self.client.get("/api/v1/billing/subscription", headers=self.headers, name="/api/v1/billing/subscription")
