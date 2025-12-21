"""Card Parser: YAML Header + NL Body."""
from typing import Dict, Tuple

import yaml
from fastapi import HTTPException


def parse_card_text(text: str) -> Tuple[Dict, str]:
    """
    Parses a card text into (header_dict, body_text).
    Format must be:
    YAML content
    ---
    NL content
    
    OR
    
    ---
    YAML content
    ---
    NL content
    """
    # Normalize inputs
    text = text.strip()
    
    parts = text.split("---", 2)
    
    # Case 1: "YAML \n --- \n Body" -> parts=["YAML", "Body"] (split=1?)
    # But split("---", 2) might behave differently depending on leading dashes.
    
    # Let's robustly find the separating dashed line.
    
    # If starts with ---, we might have frontmatter style:
    # ---
    # yaml
    # ---
    # body
    
    if text.startswith("---"):
        # We expect 3 parts: empty, yaml, body
        parts = text.split("---", 2)
        if len(parts) < 3:
             raise HTTPException(status_code=422, detail="Invalid card format: Frontmatter style requires closing '---'")
        
        yaml_text = parts[1]
        body_text = parts[2]
    else:
        # We expect: yaml \n --- \n body
        parts = text.split("---", 1)
        if len(parts) < 2:
            raise HTTPException(status_code=422, detail="Invalid card format: Missing '---' separator")
        
        yaml_text = parts[0]
        body_text = parts[1]

    # Parse YAML
    try:
        header = yaml.safe_load(yaml_text)
        if not isinstance(header, dict):
             # Maybe empty or scalar
             header = {}
        if header is None:
            header = {}
    except yaml.YAMLError as e:
        raise HTTPException(status_code=422, detail=f"Invalid YAML header: {str(e)}")

    return header, body_text.strip()
