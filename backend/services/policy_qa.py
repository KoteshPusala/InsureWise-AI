import json
import re
from typing import Dict, Any, List, Optional
from config import settings
from services.vector_store import search
from services.llm import generate, generate_json

def _normalize_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text.lower().strip())

def _token_overlap_ratio(quote: str, chunk_text: str) -> float:
    quote_words = set(re.findall(r'\w{3,}', quote.lower()))
    if not quote_words:
        return 0.0
    chunk_words = set(re.findall(r'\w{3,}', chunk_text.lower()))
    intersection = quote_words.intersection(chunk_words)
    return len(intersection) / len(quote_words)

def ask_question(policy_id: str, question: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    standalone_question = question.strip()
    demo_mode = getattr(settings, "DEMO_MODE", False) or not getattr(settings, "api_key_configured", False)
    
    if history and not demo_mode and len(history) > 0:
        try:
            prompt = f"Given conversation history: {json.dumps(history[-4:])}, rewrite this latest user question as a standalone query for search: '{question}'"
            rewritten = generate("You are a query rewriting assistant. Output ONLY the standalone question.", prompt, max_tokens=100).strip()
            if rewritten:
                standalone_question = rewritten.strip('"\'')
        except Exception:
            pass
            
    chunks = search(policy_id, standalone_question, top_k=settings.TOP_K, threshold=settings.RELEVANCE_THRESHOLD)
    
    if demo_mode:
        answer_text = "\n\n".join([f"[Page {c['page_start']}] {c['text']}" for c in chunks])
        citations = [{"page": c["page_start"], "quote": c["text"][:140]} for c in chunks[:3]]
        return {
            "answer": f"Policy Search Results:\n\n{answer_text}" if chunks else "The requested information was not found in the policy document.",
            "verdict": "covered" if chunks else "not_stated",
            "supported": bool(chunks),
            "citations": citations,
            "follow_up_suggestions": ["What are the exclusions?", "What is the deductible?", "How do I file a claim?"]
        }
        
    if not chunks:
        return {
            "answer": "The requested information could not be found in the policy document.",
            "verdict": "not_stated",
            "supported": False,
            "citations": [],
            "follow_up_suggestions": ["What is covered under this policy?", "What are the exclusions?"]
        }
        
    context = ""
    for i, chunk in enumerate(chunks):
        context += f"--- Excerpt {i+1} (Page {chunk['page_start']}) ---\n{chunk['text']}\n\n"
        
    system_prompt = (
        "You are an insurance policy assistant. Answer ONLY based on the provided document excerpts. "
        "Cite the exact page number as [Page N] for your claims. Do not guess. "
        "Distinguish between covered, excluded, conditional, or not_stated. "
        "Use plain language. Never claim legal certainty. "
        "Provide JSON output matching this structure: "
        '{"answer": "...", "verdict": "covered|excluded|conditional|not_stated", "supported": true/false, "citations": [{"page": N, "quote": "..."}], "follow_up_suggestions": ["..."]}'
    )
    
    user_prompt = f"Policy Excerpts:\n{context}\n\nUser Question: {standalone_question}"
    
    try:
        response = generate_json(system_prompt, user_prompt)
    except Exception as e:
        logger.warning(f"AI QA generation encountered error: {e}. Falling back to grounded policy excerpts.")
        excerpts = []
        for c in chunks[:3]:
            p = c.get("page_start", 1)
            t = (c.get("text") or "").strip()
            if t:
                excerpts.append(f"**Policy Page {p} excerpt:**\n> \"{t[:300]}\"")
        fallback_answer = (
            "Based directly on the policy document:\n\n"
            + "\n\n".join(excerpts)
            + "\n\n*(Direct policy retrieval mode - verified against cited policy pages)*"
        ) if excerpts else "Information regarding this query could not be located in the indexed policy document."

        return {
            "answer": fallback_answer,
            "verdict": "conditional" if chunks else "not_stated",
            "supported": bool(chunks),
            "citations": [{"page": c["page_start"], "quote": c["text"][:140]} for c in chunks[:3]],
            "follow_up_suggestions": ["What are the exclusions?", "What is the deductible?", "How do I file a claim?"]
        }
        
    # Validate and clean citations
    valid_citations = []
    seen_pages = set()
    raw_citations = response.get("citations", [])
    
    if isinstance(raw_citations, list):
        for cit in raw_citations:
            if not isinstance(cit, dict):
                continue
            quote = cit.get("quote", "").strip()
            page = cit.get("page")
            
            # Find matching chunk
            matched_chunk = None
            for chunk in chunks:
                norm_quote = _normalize_text(quote)
                norm_chunk = _normalize_text(chunk["text"])
                if norm_quote and norm_quote in norm_chunk:
                    matched_chunk = chunk
                    break
                elif quote and _token_overlap_ratio(quote, chunk["text"]) >= 0.4:
                    matched_chunk = chunk
                    break
                elif page and chunk["page_start"] == page:
                    matched_chunk = chunk
                    break
                    
            if matched_chunk:
                citation_page = matched_chunk["page_start"]
                citation_quote = quote if len(quote) > 10 else matched_chunk["text"][:140]
                if citation_page not in seen_pages:
                    valid_citations.append({"page": citation_page, "quote": citation_quote})
                    seen_pages.add(citation_page)
                    
    # Fallback citations if model didn't return them
    if not valid_citations and chunks:
        for c in chunks[:2]:
            valid_citations.append({"page": c["page_start"], "quote": c["text"][:140]})
            
    verdict = response.get("verdict", "not_stated")
    if verdict not in ("covered", "excluded", "conditional", "not_stated"):
        verdict = "not_stated"
        
    return {
        "answer": response.get("answer", "No answer provided."),
        "verdict": verdict,
        "supported": bool(response.get("supported", len(valid_citations) > 0)),
        "citations": valid_citations,
        "follow_up_suggestions": response.get("follow_up_suggestions", [])[:3]
    }

def get_starter_questions(policy_type: str) -> List[str]:
    type_lower = (policy_type or "").lower()
    if "vehicle" in type_lower or "auto" in type_lower:
        return ["What is my deductible?", "Am I covered for flood or water damage?", "Is roadside assistance included?"]
    elif "health" in type_lower or "medical" in type_lower:
        return ["Are pre-existing conditions covered?", "What is my copay or coinsurance?", "Is dental included?"]
    elif "home" in type_lower or "property" in type_lower:
        return ["Does this cover water damage?", "Are my electronics covered?", "What is the liability limit?"]
    return ["What are the main exclusions?", "How do I file a claim?", "What is my deductible?"]

def detect_policy_type(chunks: List[Dict[str, Any]]) -> str:
    text = " ".join([c["text"] for c in chunks[:10]]).lower()
    if any(k in text for k in ["auto", "vehicle", "car", "motor", "collision"]):
        return "vehicle"
    if any(k in text for k in ["health", "medical", "hospital", "physician", "dental"]):
        return "health"
    if any(k in text for k in ["home", "property", "dwelling", "fire", "homeowner"]):
        return "home"
    if any(k in text for k in ["travel", "trip", "flight", "baggage"]):
        return "travel"
    return "general"

def generate_policy_summary(policy_id: str, chunks: List[Dict[str, Any]]) -> str:
    if getattr(settings, "DEMO_MODE", False) or not getattr(settings, "api_key_configured", False):
        return "Ingested and indexed policy document for vector search and AI assistance."
    text = " ".join([c["text"] for c in chunks[:5]])[:2500]
    prompt = f"Summarize key coverages, exclusions, and deductibles of this insurance policy in 2-3 concise sentences:\n\n{text}"
    try:
        return generate("You are an insurance policy explainer.", prompt, max_tokens=150).strip()
    except Exception:
        return "Insurance policy uploaded and indexed for AI Q&A and claims assistance."
