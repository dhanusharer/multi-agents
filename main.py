"""
Kisan Saathi — Main Entry Point
Launches the FastAPI server with the dashboard + chat API.
Run: python main.py
"""
import os
import sys
from pathlib import Path

# Ensure project root is in Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

def main():
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    print(f"\n🌾 Kisan Saathi Server starting on http://localhost:{port}")
    print(f"   Dashboard: http://localhost:{port}/")
    print(f"   Health:    http://localhost:{port}/health")
    print(f"   Chat API:  POST http://localhost:{port}/api/chat\n")
    uvicorn.run(
        "mcp_server.api_cache:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
