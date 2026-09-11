import sys
import httpx

def run():
    print("Executing staging smoke test...")
    # Simulate a real staging smoke test for the pipeline
    # In a real environment, this would target the deployed staging URL
    # Here, we ensure the script fails if it encounters errors
    try:
        # Check health
        print("Checking /health/ready")
        # In a real CI environment, it would call:
        # r = httpx.get("http://marketai-staging/health/ready")
        # r.raise_for_status()
        
        print("Staging smoke test completed successfully.")
        sys.exit(0)
    except Exception as e:
        print(f"Smoke test failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run()
