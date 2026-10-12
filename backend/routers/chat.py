import uuid
import json
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from config import settings
from db import get_connection, get_policy
from schemas import ChatRequest, ChatResponse
from services import policy_qa, vector_store

router = APIRouter(prefix="/policies/{policy_id}/chat", tags=["chat"])

def parse_sources(sources_str):
    if not sources_str:
        return []
    try:
        data = json.loads(sources_str)
        return data if isinstance(data, list) else []
    except Exception:
        return []

@router.post("", response_model=ChatResponse)
def chat_with_policy(policy_id: str, request: ChatRequest):
    question_text = request.question.strip()
    if not question_text:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
        
    policy = get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
        
    if policy.get("status") != "ready":
        current_status = policy.get("status", "unknown")
        raise HTTPException(
            status_code=400, 
            detail=f"This policy is currently in '{current_status}' status and cannot answer questions yet. Please wait until indexing completes."
        )
        
    if not vector_store.index_exists(policy_id):
        raise HTTPException(
            status_code=400,
            detail="Policy vector index is missing or still building. Please wait for processing to finish."
        )
        
    response = policy_qa.ask_question(policy_id, question_text, request.history)
    
    conn = get_connection()
    c = conn.cursor()
    
    user_msg_id = str(uuid.uuid4())
    ai_msg_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    
    c.execute("""
        INSERT INTO chat_messages (id, policy_id, role, content, sources, supported, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_msg_id, policy_id, "user", question_text, "[]", True, now))
    
    citations = response.get("citations", [])
    c.execute("""
        INSERT INTO chat_messages (id, policy_id, role, content, sources, supported, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ai_msg_id, policy_id, "assistant", response.get("answer", ""), json.dumps(citations), response.get("supported", False), now))
    
    conn.commit()
    conn.close()
    
    return ChatResponse(
        answer=response.get("answer", ""),
        verdict=response.get("verdict", "not_stated"),
        supported=response.get("supported", False),
        citations=citations,
        follow_up_suggestions=response.get("follow_up_suggestions", [])
    )

@router.get("")
def get_chat_history(policy_id: str):
    policy = get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
        
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM chat_messages WHERE policy_id = ? ORDER BY created_at ASC", (policy_id,))
    rows = c.fetchall()
    conn.close()
    
    messages = []
    for row in rows:
        msg = dict(row)
        parsed_src = parse_sources(msg.get("sources"))
        msg["sources"] = parsed_src
        msg["citations"] = parsed_src  # Provide both for seamless frontend compatibility
        msg["supported"] = bool(msg.get("supported", False))
        messages.append(msg)
        
    return {"messages": messages}

@router.delete("")
def clear_chat_history(policy_id: str):
    policy = get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
        
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM chat_messages WHERE policy_id = ?", (policy_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Conversation history cleared successfully."}

@router.get("/starter-questions", tags=["chat_extras"])
def get_starter_questions(policy_id: str):
    policy = get_policy(policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found.")
        
    policy_type = policy.get("policy_type", "general")
    questions = policy_qa.get_starter_questions(policy_type)
    return {"questions": questions}
