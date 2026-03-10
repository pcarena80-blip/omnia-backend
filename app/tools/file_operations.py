"""
File Operations Tool
Download files, manage local filesystem, organize documents.
All operations are sandboxed to a safe downloads directory.
"""
import os
import logging
from pathlib import Path
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

# Safe download directory
DOWNLOADS_DIR = Path.home() / "OMNIA_Downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)


async def download_file(
    url: str,
    filename: Optional[str] = None,
) -> dict:
    """
    Download a file from the internet.

    Args:
        url: URL to download from
        filename: Optional filename (otherwise extracted from URL)

    Returns:
        dict with download result
    """
    try:
        if not filename:
            filename = url.split("/")[-1].split("?")[0] or "download"

        filepath = DOWNLOADS_DIR / filename

        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url, timeout=60.0)
            response.raise_for_status()

            with open(filepath, "wb") as f:
                f.write(response.content)

        size_mb = os.path.getsize(filepath) / (1024 * 1024)

        return {
            "success": True,
            "filename": filename,
            "path": str(filepath),
            "size_mb": round(size_mb, 2),
            "message": f"✅ Downloaded '{filename}' ({size_mb:.1f} MB) to {DOWNLOADS_DIR}",
        }

    except Exception as e:
        logger.error(f"Download error: {e}")
        return {"success": False, "error": str(e)}


async def list_downloads() -> dict:
    """List all files in the OMNIA downloads directory."""
    files = []
    for f in DOWNLOADS_DIR.iterdir():
        if f.is_file():
            size = f.stat().st_size / (1024 * 1024)
            files.append({
                "name": f.name,
                "size_mb": round(size, 2),
                "path": str(f),
            })
    return {"files": files, "directory": str(DOWNLOADS_DIR)}


async def read_text_file(filepath: str, max_chars: int = 10000) -> dict:
    """
    Read a text file's content (sandboxed to downloads dir).

    Args:
        filepath: Path to the file (must be in OMNIA_Downloads)
        max_chars: Maximum characters to read

    Returns:
        dict with file content
    """
    path = Path(filepath)

    # Security: only allow reading from downloads directory
    try:
        path.resolve().relative_to(DOWNLOADS_DIR.resolve())
    except ValueError:
        return {"error": "Access denied: can only read files from OMNIA_Downloads"}

    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    try:
        content = path.read_text(encoding="utf-8")[:max_chars]
        return {
            "filename": path.name,
            "content": content,
            "truncated": len(content) >= max_chars,
        }
    except Exception as e:
        return {"error": f"Cannot read file: {e}"}
