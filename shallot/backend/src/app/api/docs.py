"""Documentation API endpoints."""
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, PlainTextResponse

# Get the path to the docs directory
DOCS_DIR = Path("/docs")  # Use absolute path for Docker compatibility

logger = logging.getLogger(__name__)
router = APIRouter()

logger.info("Initializing documentation router with base path: %s", DOCS_DIR)

@router.get("/{path:path}", description="Get documentation file content")
async def get_doc(path: str):
    """Get documentation file content."""
    try:
        logger.info("Documentation request received for path: %s", path)
        print(f"[DEBUG] Base docs dir: {DOCS_DIR}")
        
        # Add appropriate extension if not present
        if not (path.endswith('.md') or path.endswith('.html')):
            # Try HTML first, fall back to MD
            html_path = f"{path}.html"
            if (DOCS_DIR / html_path).exists():
                path = html_path
            else:
                path = f"{path}.md"
        file_path = DOCS_DIR / path
        print(f"[DEBUG] Full file path: {file_path}")
        print(f"[DEBUG] File exists: {file_path.exists()}")
        
        # Ensure the file exists and is within the docs directory
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(status_code=404, detail="Documentation not found")
        
        # Ensure the file is within the docs directory (prevent directory traversal)
        if not file_path.resolve().is_relative_to(DOCS_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
            
        # Read the file content
        content = file_path.read_text()
        
        # Return with appropriate response type based on file extension
        if file_path.suffix == '.html':
            return HTMLResponse(content=content)
        else:
            return PlainTextResponse(content=content)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
