from fastapi import FastAPI
from pydantic import BaseModel
import uuid

app = FastAPI()

# ---------------- SESSION STORAGE ----------------
sessions = {}

# ---------------- REQUEST MODEL ----------------
class QueryRequest(BaseModel):
    session_id: str
    role: str
    message: str

# ---------------- TOOLS ----------------
def database_tool(payload):
    data = {"march_sales": 50000, "april_sales": 70000}
    query = payload.get("query", "").lower()

    if "march" in query:
        return {"sales": data["march_sales"]}
    return {"error": "Data not found"}

def email_tool(payload):
    to = payload.get("to")
    subject = payload.get("subject")
    content = payload.get("content")

    if not to:
        return {"error": "Recipient missing"}

    return {"status": "Email sent", "to": to}

def file_tool(payload):
    filename = payload.get("filename")

    try:
        with open(filename, "r") as f:
            return {"content": f.read()}
    except:
        return {"error": "File not found"}

# ---------------- ROUTER ----------------
def route_tool(message):
    message = message.lower()

    if "sales" in message:
        return "database.query"
    elif "email" in message:
        return "email.send"
    elif "file" in message:
        return "file.read"
    
    return "database.query"

# ---------------- CONNECTOR ----------------
def mcp_connector(tool, payload):
    if tool == "database.query":
        return database_tool(payload)
    elif tool == "email.send":
        return email_tool(payload)
    elif tool == "file.read":
        return file_tool(payload)
    
    return {"error": "Invalid tool"}

# ---------------- CONTEXT ----------------
def update_context(session_id, message):
    if session_id not in sessions:
        sessions[session_id] = []
    sessions[session_id].append(message)

# ---------------- RBAC ----------------
def check_access(role, tool):
    if role == "admin":
        return True
    if tool == "email.send":
        return False
    return True

# ---------------- SECURITY ----------------
def mask_sensitive(data):
    if isinstance(data, dict) and "to" in data:
        data["to"] = "***@***.com"
    return data

# ---------------- SAFE EXECUTION ----------------
def safe_execute(tool, payload):
    try:
        return mcp_connector(tool, payload)
    except Exception as e:
        return {"error": str(e)}

# ---------------- MULTI STEP ----------------
def multi_step_handler(message):
    if "sales and email" in message.lower():
        sales = database_tool({"query": "march sales"})
        
        email = email_tool({
            "to": "boss@company.com",
            "subject": "Sales Report",
            "content": str(sales)
        })

        return {
            "combined_result": {
                "sales": sales,
                "email": email
            }
        }
    return None

# ---------------- RESPONSE ----------------
def format_response(tool, result):
    if result is None:
        result = {"error": "No response"}

    result = mask_sensitive(result)

    return {
        "status": "success" if "error" not in result else "failure",
        "message": "Execution completed",
        "tool": tool,
        "result": result,
        "trace_id": str(uuid.uuid4())
    }

# ---------------- MAIN API ----------------
@app.post("/query")
def query(req: QueryRequest):

    # Context update
    update_context(req.session_id, req.message)

    # Multi-step check
    multi_result = multi_step_handler(req.message)
    if multi_result:
        return format_response("multi-step", multi_result)

    # Routing
    tool = route_tool(req.message)

    # RBAC check
    if not check_access(req.role, tool):
        return {
            "status": "failure",
            "message": "Access Denied",
            "tool": tool,
            "result": {},
            "trace_id": str(uuid.uuid4())
        }

    # MCP STRUCTURE (IMPORTANT)
    mcp_request = {
        "context": sessions.get(req.session_id, []),
        "tool": tool,
        "payload": {}
    }

    # Payload creation
    if tool == "database.query":
        mcp_request["payload"] = {"query": req.message}

    elif tool == "email.send":
        mcp_request["payload"] = {
            "to": "boss@company.com",
            "subject": "Report",
            "content": req.message
        }

    elif tool == "file.read":
        mcp_request["payload"] = {"filename": "test.txt"}

    # Safe execution
    result = safe_execute(tool, mcp_request["payload"])

    return format_response(tool, result)