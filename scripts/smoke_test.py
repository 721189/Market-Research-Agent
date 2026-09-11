import os
import sys
import time
import logging
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("smoke_test")

STAGING_BASE_URL = os.getenv("STAGING_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("SMOKE_TEST_API_KEY", "mk_live_smoke_test_key_12345")

def run_smoke_test():
    logger.info(f"Starting Fail-Closed Staging Smoke Test against {STAGING_BASE_URL}...")
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}

    with httpx.Client(base_url=STAGING_BASE_URL, timeout=30.0) as client:
        # Step 1: Health Readiness Probe
        logger.info("Step 1: Checking GET /health/ready...")
        try:
            r = client.get("/health/ready")
            if r.status_code != 200:
                logger.error(f"Readiness check failed with status {r.status_code}: {r.text}")
                sys.exit(1)
            logger.info("Health check passed.")
        except Exception as e:
            logger.error(f"Readiness probe connection failed: {e}")
            sys.exit(1)

        # Step 2: Create Authenticated Research Job
        logger.info("Step 2: Submitting test research job via POST /api/v1/research...")
        payload = {
            "product_idea": "AI-powered automated inventory forecasting for local bakeries",
            "mode": "quick",
            "idempotency_key": f"smoke_test_{int(time.time())}"
        }
        
        try:
            r = client.post("/api/v1/research", json=payload, headers=headers)
            if r.status_code not in (200, 202):
                logger.error(f"Failed to submit research job. Status: {r.status_code}, Body: {r.text}")
                sys.exit(1)
            
            data = r.json()
            task_id = data.get("task_id")
            if not task_id:
                logger.error("Response did not contain valid task_id")
                sys.exit(1)
            logger.info(f"Research job created successfully. Task ID: {task_id}")

            # Step 3 & 4: Poll Job Status until Completed
            logger.info(f"Step 3: Polling GET /api/v1/research/{task_id}...")
            max_attempts = 20
            completed = False
            for attempt in range(1, max_attempts + 1):
                res = client.get(f"/api/v1/research/{task_id}", headers=headers)
                if res.status_code == 200:
                    status_info = res.json()
                    job_status = status_info.get("status")
                    logger.info(f"Attempt {attempt}/{max_attempts}: Job Status = {job_status}")
                    if job_status in ("COMPLETED", "FINISHED"):
                        completed = True
                        break
                    elif job_status in ("FAILED", "CANCELLED"):
                        logger.error(f"Job failed during smoke test with status: {job_status}")
                        sys.exit(1)
                else:
                    logger.error(f"Polling failed with status {res.status_code}: {res.text}")
                    sys.exit(1)
                time.sleep(2)

            if not completed:
                logger.error("Job polling timed out before reaching COMPLETED state.")
                sys.exit(1)

            # Step 5: Verify PDF Generation Endpoint
            logger.info(f"Step 5: Verifying GET /api/v1/reports/{task_id}/pdf...")
            pdf_res = client.get(f"/api/v1/reports/{task_id}/pdf", headers=headers)
            if pdf_res.status_code not in (200, 202):
                logger.error(f"PDF Endpoint check failed with status {pdf_res.status_code}: {pdf_res.text}")
                sys.exit(1)

            logger.info("Fail-Closed Staging Smoke Test execution completed successfully!")

        except Exception as e:
            logger.error(f"Smoke test encountered unexpected exception: {e}")
            sys.exit(1)

if __name__ == "__main__":
    run_smoke_test()

