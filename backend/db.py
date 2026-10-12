import sqlite3
import json
import uuid
import os
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import settings

def get_connection():
    os.makedirs(str(settings.STORAGE_DIR), exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS policies (
            id TEXT PRIMARY KEY,
            filename TEXT,
            display_name TEXT,
            uploaded_at TEXT,
            page_count INTEGER,
            chunk_count INTEGER,
            ocr_pages TEXT,
            status TEXT,
            progress_stage TEXT DEFAULT '',
            error_message TEXT,
            policy_type TEXT,
            summary TEXT
        )
    """)
    
    # In case policies table existed without progress_stage
    try:
        cursor.execute("ALTER TABLE policies ADD COLUMN progress_stage TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id TEXT PRIMARY KEY,
            policy_id TEXT,
            role TEXT,
            content TEXT,
            sources TEXT,
            supported BOOLEAN,
            created_at TEXT,
            FOREIGN KEY(policy_id) REFERENCES policies(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id TEXT PRIMARY KEY,
            policy_id TEXT,
            incident_description TEXT,
            incident_type TEXT,
            incident_date TEXT,
            created_at TEXT,
            status TEXT,
            checklist_items TEXT,
            documents TEXT,
            FOREIGN KEY(policy_id) REFERENCES policies(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_documents (
            id TEXT PRIMARY KEY,
            claim_id TEXT,
            filename TEXT,
            page_count INTEGER,
            extracted_text_preview TEXT,
            doc_type_guess TEXT,
            created_at TEXT,
            checklist_item_id TEXT DEFAULT '',
            file_size INTEGER DEFAULT 0,
            file_path TEXT DEFAULT '',
            version INTEGER DEFAULT 1,
            is_current INTEGER DEFAULT 1,
            status TEXT DEFAULT 'awaiting_upload',
            classification TEXT DEFAULT '{}',
            extracted_data TEXT DEFAULT '{}',
            verification_findings TEXT DEFAULT '{}',
            issues TEXT DEFAULT '[]',
            review_status TEXT DEFAULT 'pending',
            reviewer_name TEXT DEFAULT '',
            reviewer_notes TEXT DEFAULT '',
            reviewed_at TEXT DEFAULT '',
            FOREIGN KEY(claim_id) REFERENCES claims(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_physical_verifications (
            id TEXT PRIMARY KEY,
            claim_id TEXT UNIQUE,
            status TEXT DEFAULT 'pending',
            requested_by TEXT,
            requested_at TEXT,
            scheduled_date TEXT DEFAULT '',
            scheduled_location TEXT DEFAULT '',
            instructions TEXT DEFAULT '',
            assigned_inspector TEXT DEFAULT '',
            outcome_status TEXT DEFAULT '',
            outcome_notes TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY(claim_id) REFERENCES claims(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claim_audit_log (
            id TEXT PRIMARY KEY,
            claim_id TEXT,
            document_id TEXT DEFAULT '',
            event_type TEXT,
            actor_name TEXT,
            actor_role TEXT DEFAULT 'system',
            old_status TEXT DEFAULT '',
            new_status TEXT DEFAULT '',
            details TEXT DEFAULT '{}',
            created_at TEXT,
            FOREIGN KEY(claim_id) REFERENCES claims(id)
        )
    """)

    # Auto-migrate claims table columns if missing
    claim_cols = [
        ("claim_title", "TEXT DEFAULT ''"),
        ("claim_category", "TEXT DEFAULT ''"),
        ("incident_details", "TEXT DEFAULT '{}'"),
        ("readiness_score", "INTEGER DEFAULT 0"),
        ("report_version", "INTEGER DEFAULT 1"),
        ("report_stale", "INTEGER DEFAULT 0"),
        ("updated_at", "TEXT DEFAULT ''"),
        ("physical_verification_status", "TEXT DEFAULT 'none'"),
        ("physical_verification_id", "TEXT DEFAULT ''"),
    ]
    for col_name, col_def in claim_cols:
        try:
            cursor.execute(f"ALTER TABLE claims ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    # Auto-migrate claim_documents table columns if missing
    doc_cols = [
        ("checklist_item_id", "TEXT DEFAULT ''"),
        ("file_size", "INTEGER DEFAULT 0"),
        ("file_path", "TEXT DEFAULT ''"),
        ("version", "INTEGER DEFAULT 1"),
        ("is_current", "INTEGER DEFAULT 1"),
        ("status", "TEXT DEFAULT 'awaiting_upload'"),
        ("classification", "TEXT DEFAULT '{}'"),
        ("extracted_data", "TEXT DEFAULT '{}'"),
        ("verification_findings", "TEXT DEFAULT '{}'"),
        ("issues", "TEXT DEFAULT '[]'"),
        ("review_status", "TEXT DEFAULT 'pending'"),
        ("reviewer_name", "TEXT DEFAULT ''"),
        ("reviewer_notes", "TEXT DEFAULT ''"),
        ("reviewed_at", "TEXT DEFAULT ''"),
    ]
    for col_name, col_def in doc_cols:
        try:
            cursor.execute(f"ALTER TABLE claim_documents ADD COLUMN {col_name} {col_def}")
        except sqlite3.OperationalError:
            pass

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT,
            password_hash TEXT,
            created_at TEXT
        )
    """)

    # User scoping migrations
    try:
        cursor.execute("ALTER TABLE policies ADD COLUMN user_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE claims ADD COLUMN user_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


import hashlib
import secrets

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), 100000)
    return f"{salt}:{key.hex()}"

def verify_password(stored_password: str, provided_password: str) -> bool:
    try:
        if not stored_password or ":" not in stored_password:
            return False
        salt, key_hex = stored_password.split(":")
        new_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), bytes.fromhex(salt), 100000)
        return secrets.compare_digest(new_key.hex(), key_hex)
    except Exception:
        return False

def create_user(name: str, email: str, password: str) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    user_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    pw_hash = hash_password(password)
    c.execute("""
        INSERT INTO users (id, email, name, password_hash, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, email.lower().strip(), name.strip(), pw_hash, created_at))
    conn.commit()
    conn.close()
    return {"id": user_id, "email": email.lower().strip(), "name": name.strip(), "created_at": created_at}

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (email.lower().strip(),))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def create_policy(filename: str, display_name: str, page_count: int = 0, user_id: str = "") -> str:
    conn = get_connection()
    c = conn.cursor()
    policy_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()
    c.execute("""
        INSERT INTO policies (id, filename, display_name, uploaded_at, page_count, chunk_count, ocr_pages, status, progress_stage, error_message, policy_type, summary, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (policy_id, filename, display_name, uploaded_at, page_count, 0, "[]", "processing", "uploading", "", "", "", user_id))
    conn.commit()
    conn.close()
    return policy_id

def get_policy(policy_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM policies WHERE id = ?", (policy_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def list_policies(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    if user_id:
        # Show policies uploaded by this user + global template policies
        c.execute("SELECT * FROM policies WHERE user_id = ? OR user_id = '' OR user_id IS NULL ORDER BY uploaded_at DESC", (user_id,))
    else:
        c.execute("SELECT * FROM policies ORDER BY uploaded_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_policy(policy_id: str, **kwargs):
    if not kwargs:
        return
    conn = get_connection()
    c = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(policy_id)
    c.execute(f"UPDATE policies SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def create_claim(
    policy_id: str,
    incident_description: str,
    incident_type: str,
    incident_date: str,
    claim_title: str = "",
    claim_category: str = "",
    incident_details: Optional[Dict[str, Any]] = None,
    user_id: str = ""
) -> str:
    conn = get_connection()
    c = conn.cursor()
    claim_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    inc_details_json = json.dumps(incident_details or {})
    title = claim_title or f"{incident_type.replace('_', ' ').title()} Claim"
    category = claim_category or incident_type
    c.execute("""
        INSERT INTO claims (
            id, policy_id, incident_description, incident_type, incident_date, created_at, status, checklist_items, documents,
            claim_title, claim_category, incident_details, readiness_score, report_version, report_stale, updated_at, user_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        claim_id, policy_id, incident_description, incident_type, incident_date, created_at, "draft", "[]", "[]",
        title, category, inc_details_json, 0, 1, 0, created_at, user_id
    ))
    conn.commit()
    conn.close()
    log_audit_event(
        claim_id=claim_id,
        event_type="claim_created",
        actor_name="Claimant",
        actor_role="claimant",
        new_status="draft",
        details={"incident_type": incident_type, "incident_date": incident_date, "title": title}
    )
    return claim_id

def get_claim(claim_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM claims WHERE id = ?", (claim_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_claim(claim_id: str, **kwargs):
    if not kwargs:
        return
    conn = get_connection()
    c = conn.cursor()
    kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(claim_id)
    c.execute(f"UPDATE claims SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def mark_claim_report_stale(claim_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE claims SET report_stale = 1, updated_at = ? WHERE id = ?", (datetime.now(timezone.utc).isoformat(), claim_id))
    conn.commit()
    conn.close()

def log_audit_event(
    claim_id: str,
    event_type: str,
    actor_name: str = "System",
    actor_role: str = "system",
    document_id: str = "",
    old_status: str = "",
    new_status: str = "",
    details: Optional[Dict[str, Any]] = None
) -> str:
    conn = get_connection()
    c = conn.cursor()
    log_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    details_json = json.dumps(details or {})
    c.execute("""
        INSERT INTO claim_audit_log (
            id, claim_id, document_id, event_type, actor_name, actor_role, old_status, new_status, details, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (log_id, claim_id, document_id, event_type, actor_name, actor_role, old_status, new_status, details_json, created_at))
    conn.commit()
    conn.close()
    return log_id

def get_claim_audit_logs(claim_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM claim_audit_log WHERE claim_id = ? ORDER BY created_at ASC", (claim_id,))
    rows = c.fetchall()
    conn.close()
    results = []
    for r in rows:
        item = dict(r)
        if item.get("details"):
            try:
                item["details"] = json.loads(item["details"])
            except Exception:
                pass
        results.append(item)
    return results

def create_physical_verification_request(claim_id: str, requested_by: str, instructions: str = "") -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM claim_physical_verifications WHERE claim_id = ?", (claim_id,))
    row = c.fetchone()
    now_str = datetime.now(timezone.utc).isoformat()
    if row:
        pv_id = row["id"]
        c.execute("""
            UPDATE claim_physical_verifications
            SET status = 'pending', requested_by = ?, instructions = ?, requested_at = ?, updated_at = ?
            WHERE id = ?
        """, (requested_by, instructions, now_str, now_str, pv_id))
    else:
        pv_id = str(uuid.uuid4())
        c.execute("""
            INSERT INTO claim_physical_verifications (
                id, claim_id, status, requested_by, requested_at, instructions, created_at, updated_at
            ) VALUES (?, ?, 'pending', ?, ?, ?, ?, ?)
        """, (pv_id, claim_id, requested_by, now_str, instructions, now_str, now_str))

    c.execute("""
        UPDATE claims
        SET physical_verification_status = 'pending', physical_verification_id = ?, status = 'physical_verification_pending', updated_at = ?
        WHERE id = ?
    """, (pv_id, now_str, claim_id))
    conn.commit()
    conn.close()
    log_audit_event(
        claim_id=claim_id,
        event_type="physical_verification_requested",
        actor_name=requested_by,
        actor_role="reviewer",
        new_status="physical_verification_pending",
        details={"instructions": instructions}
    )
    return pv_id

def get_physical_verification(claim_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM claim_physical_verifications WHERE claim_id = ?", (claim_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_physical_verification(claim_id: str, **kwargs):
    if not kwargs:
        return
    conn = get_connection()
    c = conn.cursor()
    kwargs["updated_at"] = datetime.now(timezone.utc).isoformat()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(claim_id)
    c.execute(f"UPDATE claim_physical_verifications SET {set_clause} WHERE claim_id = ?", values)
    conn.commit()
    conn.close()

def create_claim_document(
    claim_id: str,
    filename: str,
    checklist_item_id: str = "",
    file_size: int = 0,
    page_count: int = 0,
    extracted_text_preview: str = "",
    doc_type_guess: str = "unknown",
    status: str = "uploaded"
) -> str:
    conn = get_connection()
    c = conn.cursor()
    doc_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()
    file_path = str(settings.UPLOADS_DIR / f"{doc_id}.pdf")
    
    # Calculate version and archive previous current document for this checklist requirement
    version = 1
    if checklist_item_id:
        c.execute("SELECT COUNT(*) FROM claim_documents WHERE claim_id = ? AND checklist_item_id = ?", (claim_id, checklist_item_id))
        count = c.fetchone()[0]
        version = count + 1
        # Archive any previous current document for this item so only one current document exists per item
        c.execute("UPDATE claim_documents SET is_current = 0 WHERE claim_id = ? AND checklist_item_id = ? AND is_current = 1", (claim_id, checklist_item_id))

    c.execute("""
        INSERT INTO claim_documents (
            id, claim_id, filename, page_count, extracted_text_preview, doc_type_guess, created_at,
            checklist_item_id, file_size, file_path, version, is_current, status,
            classification, extracted_data, verification_findings, issues, review_status, reviewer_name, reviewer_notes, reviewed_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        doc_id, claim_id, filename, page_count, extracted_text_preview, doc_type_guess, created_at,
        checklist_item_id, file_size, file_path, version, 1, status,
        "{}", "{}", "{}", "[]", "pending", "", "", ""
    ))
    conn.commit()
    conn.close()
    log_audit_event(
        claim_id=claim_id,
        document_id=doc_id,
        event_type="document_uploaded",
        actor_name="Claimant",
        actor_role="claimant",
        new_status=status,
        details={"filename": filename, "checklist_item_id": checklist_item_id, "file_size": file_size, "version": version}
    )
    mark_claim_report_stale(claim_id)
    return doc_id

def get_claim_documents(claim_id: str, is_current_only: bool = True) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    if is_current_only:
        c.execute("SELECT * FROM claim_documents WHERE claim_id = ? AND is_current = 1 ORDER BY created_at ASC", (claim_id,))
    else:
        c.execute("SELECT * FROM claim_documents WHERE claim_id = ? ORDER BY created_at ASC", (claim_id,))
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_claim_document(doc_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM claim_documents WHERE id = ?", (doc_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None

def update_claim_document(doc_id: str, **kwargs):
    if not kwargs:
        return
    conn = get_connection()
    c = conn.cursor()
    set_clause = ", ".join([f"{k} = ?" for k in kwargs.keys()])
    values = list(kwargs.values())
    values.append(doc_id)
    c.execute(f"UPDATE claim_documents SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()

def delete_claim_document(doc_id: str) -> bool:
    doc = get_claim_document(doc_id)
    if not doc:
        return False
    claim_id = doc["claim_id"]
    filename = doc.get("filename", "")
    file_path = settings.UPLOADS_DIR / f"{doc_id}.pdf"
    if file_path.exists():
        try:
            file_path.unlink()
        except OSError:
            pass
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM claim_documents WHERE id = ?", (doc_id,))
    conn.commit()
    conn.close()
    log_audit_event(
        claim_id=claim_id,
        document_id=doc_id,
        event_type="document_deleted",
        actor_name="Claimant",
        actor_role="claimant",
        details={"filename": filename}
    )
    mark_claim_report_stale(claim_id)
    return True

def reassign_claim_document(doc_id: str, new_checklist_item_id: str):
    doc = get_claim_document(doc_id)
    if not doc:
        return
    old_item_id = doc.get("checklist_item_id", "")
    update_claim_document(doc_id, checklist_item_id=new_checklist_item_id)
    log_audit_event(
        claim_id=doc["claim_id"],
        document_id=doc_id,
        event_type="document_reassigned",
        actor_name="Assessor",
        actor_role="reviewer",
        details={"old_checklist_item_id": old_item_id, "new_checklist_item_id": new_checklist_item_id}
    )
    mark_claim_report_stale(doc["claim_id"])

def record_document_review(doc_id: str, reviewer_name: str, review_status: str, reviewer_notes: str):
    doc = get_claim_document(doc_id)
    if not doc:
        return
    reviewed_at = datetime.now(timezone.utc).isoformat()
    norm_status = review_status.lower()
    # Canonicalize outcome
    if norm_status in ("accepted", "human_verified"):
        new_lifecycle_status = "reviewed"
    elif norm_status in ("info_required", "correction_required", "mismatch_confirmed", "human_rejected"):
        new_lifecycle_status = "needs_attention"
    else:
        new_lifecycle_status = "ready_for_review"

    update_claim_document(
        doc_id,
        review_status=review_status,
        reviewer_name=reviewer_name,
        reviewer_notes=reviewer_notes,
        reviewed_at=reviewed_at,
        status=new_lifecycle_status
    )
    log_audit_event(
        claim_id=doc["claim_id"],
        document_id=doc_id,
        event_type="document_reviewed",
        actor_name=reviewer_name,
        actor_role="reviewer",
        old_status=doc.get("status", ""),
        new_status=new_lifecycle_status,
        details={"review_status": review_status, "reviewer_notes": reviewer_notes}
    )
    mark_claim_report_stale(doc["claim_id"])

def recover_stuck_policies(timeout_seconds: Optional[int] = None) -> int:
    """Marks any policies stuck in intermediate processing states as failed.
    If timeout_seconds is given, only policies older than that threshold are marked failed.
    If timeout_seconds is None (e.g. at startup), all stuck policies from prior process runs are marked failed.
    """
    conn = get_connection()
    c = conn.cursor()
    
    stuck_statuses = ("processing", "uploading", "extracting_text", "chunking", "building_index", "analyzing")
    placeholders = ",".join("?" for _ in stuck_statuses)
    
    c.execute(f"SELECT * FROM policies WHERE status IN ({placeholders})", stuck_statuses)
    rows = c.fetchall()
    
    recovered = 0
    now = datetime.now(timezone.utc)
    
    for row in rows:
        policy = dict(row)
        should_fail = False
        
        if timeout_seconds is None:
            should_fail = True
        else:
            try:
                uploaded_at = datetime.fromisoformat(policy["uploaded_at"].replace("Z", "+00:00"))
                if uploaded_at.tzinfo is None:
                    uploaded_at = uploaded_at.replace(tzinfo=timezone.utc)
                age = (now - uploaded_at).total_seconds()
                if age >= timeout_seconds:
                    should_fail = True
            except Exception:
                should_fail = True
                
        if should_fail:
            c.execute("""
                UPDATE policies 
                SET status = 'failed', 
                    progress_stage = 'failed', 
                    error_message = 'Processing was interrupted or timed out. Please retry uploading this policy.'
                WHERE id = ?
            """, (policy["id"],))
            recovered += 1
            
    conn.commit()
    conn.close()
    return recovered

def delete_policy_cascade(policy_id: str) -> None:
    """Deletes policy, associated files, vector indexes, chat messages, claims, and claim documents."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Gather claims
    c.execute("SELECT id FROM claims WHERE policy_id = ?", (policy_id,))
    claim_rows = c.fetchall()
    claim_ids = [r["id"] for r in claim_rows]
    
    # 2. Gather claim documents for all associated claims
    for cid in claim_ids:
        c.execute("SELECT id FROM claim_documents WHERE claim_id = ?", (cid,))
        doc_rows = c.fetchall()
        for doc in doc_rows:
            doc_file = settings.UPLOADS_DIR / f"{doc['id']}.pdf"
            if doc_file.exists():
                try:
                    doc_file.unlink()
                except OSError:
                    pass
        # Remove report directory
        report_dir = settings.REPORTS_DIR / cid
        if report_dir.exists():
            shutil.rmtree(report_dir, ignore_errors=True)
            
        c.execute("DELETE FROM claim_documents WHERE claim_id = ?", (cid,))
        
    c.execute("DELETE FROM claims WHERE policy_id = ?", (policy_id,))
    c.execute("DELETE FROM chat_messages WHERE policy_id = ?", (policy_id,))
    c.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
    
    conn.commit()
    conn.close()
    
    # 3. Remove policy uploaded PDF
    pdf_file = settings.UPLOADS_DIR / f"{policy_id}.pdf"
    if pdf_file.exists():
        try:
            pdf_file.unlink()
        except OSError:
            pass
            
    # 4. Remove vector index directory
    index_dir = settings.INDEXES_DIR / policy_id
    if index_dir.exists():
        shutil.rmtree(index_dir, ignore_errors=True)
