from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess

app = FastAPI()

# Enable CORS for frontend connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change "*" to "http://localhost:3000" if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/resolve")
def resolve(domain: str, protocol: str = "udp"):
    """
    Calls UserScript.py with the given domain & protocol, then returns the response.
    """
    try:
        command = ["python", "UserScript.py", "-d", domain, "--ip", "192.168.0.155", "--port", "9292", "--protocol", protocol]
        result = subprocess.run(command, capture_output=True, text=True)

        return {"domain": domain, "protocol": protocol, "response": result.stdout}
    except Exception as e:
        return {"error": str(e)}

# Run using: python -m uvicorn backend:app --host 0.0.0.0 --port 8000 --reload
