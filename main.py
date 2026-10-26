"""
Super Agent Node V4 - Web Terminal Edition
Secure web-based terminal with password protection
"""
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import subprocess
import secrets
import hashlib

app = FastAPI(title="Super Agent Node V4")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Password: "superagent123" (hashed)
WEB_PASSWORD = os.environ.get("WEB_PASSWORD", "superagent123")
PASSWORD_HASH = hashlib.sha256(WEB_PASSWORD.encode()).hexdigest()

# Session store (simple in-memory)
active_sessions = {}

def check_session(session_id: str) -> bool:
    return session_id in active_sessions

@app.get("/", response_class=HTMLResponse)
async def root():
    return """<!DOCTYPE html>
<html>
<head>
    <title>Terminal Access</title>
    <style>
        body { font-family: monospace; margin: 40px; background: #1e1e1e; color: #d4d4d4; }
        .container { max-width: 600px; margin: auto; padding: 30px; background: #252526; border-radius: 8px; }
        input[type="password"] { width: 100%; padding: 10px; font-size: 16px; margin: 10px 0; background: #3c3c3c; color: #d4d4d4; border: 1px solid #555; border-radius: 4px; }
        button { width: 100%; padding: 12px; font-size: 16px; background: #0e639c; color: white; border: none; border-radius: 4px; cursor: pointer; }
        button:hover { background: #1177bb; }
        .error { color: #f48771; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🔒 Terminal Access</h2>
        <p>Enter password to access terminal</p>
        <form method="POST" action="/login">
            <input type="password" name="password" placeholder="Password" required autofocus>
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>"""

@app.post("/login")
async def login(password: str = Form(...)):
    pwd_hash = hashlib.sha256(password.encode()).hexdigest()
    if pwd_hash == PASSWORD_HASH:
        session_id = secrets.token_urlsafe(32)
        active_sessions[session_id] = True
        response = RedirectResponse(url="/terminal", status_code=302)
        response.set_cookie(key="session", value=session_id, httponly=True, max_age=3600)
        return response
    else:
        return HTMLResponse(content="""<!DOCTYPE html>
<html>
<head><title>Login Failed</title></head>
<body style="font-family: monospace; background: #1e1e1e; color: #f48771; text-align: center; padding: 50px;">
<h2>❌ Invalid Password</h2>
<p><a href="/" style="color: #0e639c;">Try again</a></p>
</body>
</html>""", status_code=401)

@app.get("/terminal", response_class=HTMLResponse)
async def terminal(request: Request):
    session_id = request.cookies.get("session")
    if not check_session(session_id):
        return RedirectResponse(url="/")
    
    return """<!DOCTYPE html>
<html>
<head>
    <title>Web Terminal</title>
    <style>
        body { font-family: monospace; margin: 0; padding: 20px; background: #1e1e1e; color: #d4d4d4; }
        .terminal { max-width: 900px; margin: auto; background: #252526; padding: 20px; border-radius: 8px; }
        textarea { width: 100%; height: 400px; background: #1e1e1e; color: #d4d4d4; border: 1px solid #555; padding: 10px; font-family: monospace; font-size: 14px; }
        input[type="text"] { width: 70%; padding: 10px; font-family: monospace; background: #3c3c3c; color: #d4d4d4; border: 1px solid #555; border-radius: 4px; }
        button { padding: 10px 20px; background: #0e639c; color: white; border: none; border-radius: 4px; cursor: pointer; font-family: monospace; }
        button:hover { background: #1177bb; }
        .cmd-line { margin: 20px 0; }
    </style>
</head>
<body>
    <div class="terminal">
        <h2>🖥️ Web Terminal</h2>
        <p>Current working directory: <code id="pwd">/app</code></p>
        <div class="cmd-line">
            <input type="text" id="cmd" placeholder="Enter command..." autofocus>
            <button onclick="runCmd()">Execute</button>
            <button onclick="clearOutput()">Clear</button>
        </div>
        <textarea id="output" readonly>Welcome to Web Terminal\nType commands above and press Execute\n\n</textarea>
    </div>
    <script>
        let cmdInput = document.getElementById('cmd');
        let output = document.getElementById('output');
        
        cmdInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') runCmd();
        });
        
        async function runCmd() {
            const cmd = cmdInput.value.trim();
            if (!cmd) return;
            
            output.value += '$ ' + cmd + '\\n';
            cmdInput.value = '';
            
            try {
                const res = await fetch('/exec', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({cmd: cmd})
                });
                const data = await res.json();
                output.value += data.output + '\\n';
                if (data.pwd) document.getElementById('pwd').textContent = data.pwd;
            } catch (e) {
                output.value += 'Error: ' + e.message + '\\n';
            }
            
            output.scrollTop = output.scrollHeight;
        }
        
        function clearOutput() {
            output.value = '';
        }
    </script>
</body>
</html>"""

@app.post("/exec")
async def exec_command(request: Request):
    session_id = request.cookies.get("session")
    if not check_session(session_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    data = await request.json()
    cmd = data.get("cmd", "")
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30, cwd="/app")
        output = result.stdout + result.stderr
        pwd = subprocess.run("pwd", shell=True, capture_output=True, text=True, cwd="/app").stdout.strip()
        return {"output": output or "(no output)", "code": result.returncode, "pwd": pwd}
    except subprocess.TimeoutExpired:
        return {"output": "Command timeout (30s)", "code": -1, "pwd": "/app"}
    except Exception as e:
        return {"output": f"Error: {str(e)}", "code": -1, "pwd": "/app"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "super-agent-v4"}

if __name__ == "__main__":
    port = int(os.environ.get("SERVER_PORT", 8080))
    print(f"🚀 Super Agent Node V4 (Web Terminal)")
    print(f"🔒 Password: {WEB_PASSWORD}")
    uvicorn.run(app, host="0.0.0.0", port=port)
