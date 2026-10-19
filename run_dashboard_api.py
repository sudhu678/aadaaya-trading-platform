"""Start the public dashboard API with: python run_dashboard_api.py"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("dashboard.api.main:app", host="127.0.0.1", port=8000)
