from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import subprocess
import os
import asyncio
import json

app = FastAPI()

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files from the built UI
# We mount everything under / so it serves index.html at root
dist_path = os.path.join(os.getcwd(), "ui", "dist")

@app.get("/")
async def read_index():
    return FileResponse(os.path.join(dist_path, "index.html"))

# Mount assets and other static files
app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")

@app.post("/migrate")
async def migrate(request: Request):
    data = await request.json()
    
    # Build arguments for exportaiocli.py
    cmd = [
        "python3", "exportaiocli.py",
        "--admin-url", data.get("adminUrl"),
        "--username", data.get("username"),
        "--password", data.get("password")
    ]
    
    if data.get("rocketToken"):
        cmd.extend(["--rocket-token", data.get("rocketToken")])
    if data.get("rocketName"):
        cmd.extend(["--rocket-name", data.get("rocketName")])
    if data.get("rocketLocation"):
        cmd.extend(["--rocket-location", str(data.get("rocketLocation"))])
    if data.get("rocketLabel"):
        cmd.extend(["--rocket-label", data.get("rocketLabel")])
    
    # Optional flags
    if data.get("visual"):
        cmd.append("--visual")

    async def stream_logs():
        # Run the script and stream output
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=os.getcwd()
        )
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            # Yield as SSE data
            yield f"data: {line.decode().rstrip()}\n\n"
        
        await process.wait()
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream_logs(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
