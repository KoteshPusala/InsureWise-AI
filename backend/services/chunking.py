import uuid
import re

def chunk_document(pages: list[dict]) -> list[dict]:
    chunks = []
    current_chunk_text = ""
    current_chunk_start_page = None
    current_section = None
    
    # Target chunk size: 600-900 characters with ~100 char overlap
    TARGET_MIN = 600
    TARGET_MAX = 900
    OVERLAP = 100
    
    # Heading patterns
    heading_patterns = [
        r"^[A-Z\s]{5,}$",  # All caps
        r"^(SECTION|PART|ARTICLE)\s+.*",
        r"^([1-9]\.|[A-Z]\)).*"
    ]
    
    def is_heading(line: str) -> bool:
        line = line.strip()
        for pattern in heading_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return True
        return False
        
    for page_data in pages:
        page_num = page_data["page_number"]
        text = page_data["text"]
        
        paragraphs = re.split(r'\n\s*\n', text)
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            lines = para.split('\n')
            for line in lines:
                if is_heading(line):
                    current_section = line.strip()
                    
            sentences = re.split(r'(?<=\. )', para)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue
                    
                if current_chunk_start_page is None:
                    current_chunk_start_page = page_num
                    
                if len(current_chunk_text) + len(sentence) > TARGET_MAX and len(current_chunk_text) >= TARGET_MIN:
                    chunks.append({
                        "chunk_id": str(uuid.uuid4()),
                        "text": current_chunk_text.strip(),
                        "page_start": current_chunk_start_page,
                        "page_end": page_num,
                        "section_heading": current_section
                    })
                    # Overlap
                    overlap_text = current_chunk_text[-OVERLAP:] if len(current_chunk_text) > OVERLAP else current_chunk_text
                    # Find first space in overlap to not break words
                    space_idx = overlap_text.find(' ')
                    if space_idx != -1:
                        overlap_text = overlap_text[space_idx+1:]
                    current_chunk_text = overlap_text + " " + sentence
                    current_chunk_start_page = page_num
                else:
                    if current_chunk_text:
                        current_chunk_text += " " + sentence
                    else:
                        current_chunk_text = sentence
                        
    if current_chunk_text:
        chunks.append({
            "chunk_id": str(uuid.uuid4()),
            "text": current_chunk_text.strip(),
            "page_start": current_chunk_start_page,
            "page_end": pages[-1]["page_number"] if pages else 1,
            "section_heading": current_section
        })
        
    return chunks
