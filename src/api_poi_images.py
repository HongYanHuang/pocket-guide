"""
POI Image Management API

Handles image upload, serving, and deletion for POIs.
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form, Depends
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime
from PIL import Image
import io

from api_models import (
    POIImageUploadResponse,
    POIImagesResponse,
    ImageMetadata,
    SuccessResponse
)
from auth.dependencies import require_backstage_admin
from utils import poi_name_to_id

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/pois",
    tags=["poi-images"]
)

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_IMAGES_PER_POI = 5
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
POI_IMAGES_DIR = Path("poi_images")


def validate_image(file: UploadFile) -> None:
    """Validate image file format and size"""
    # Check file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = file.file.read()
    file.file.seek(0)  # Reset file pointer

    # Check file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    # Verify it's a valid image
    try:
        img = Image.open(io.BytesIO(content))
        img.verify()
        if img.format not in ALLOWED_FORMATS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image format. Allowed: {', '.join(ALLOWED_FORMATS)}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid image file: {str(e)}"
        )


def compress_image(image_bytes: bytes, max_quality: int = 85) -> bytes:
    """Compress image while maintaining aspect ratio"""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert RGBA to RGB if necessary
    if img.mode == 'RGBA':
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])  # Use alpha channel as mask
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # Compress
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=max_quality, optimize=True)

    return output.getvalue()


def get_poi_image_dir(city: str, poi_id: str) -> Path:
    """Get image directory for a POI"""
    return POI_IMAGES_DIR / city / poi_id


def get_metadata_path(city: str, poi_id: str) -> Path:
    """Get metadata.json path for a POI"""
    return get_poi_image_dir(city, poi_id) / "metadata.json"


def load_image_metadata(city: str, poi_id: str) -> dict:
    """Load image metadata for a POI"""
    metadata_path = get_metadata_path(city, poi_id)

    if not metadata_path.exists():
        return {
            "poi_id": poi_id,
            "city": city,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            "images": []
        }

    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_image_metadata(city: str, poi_id: str, metadata: dict) -> None:
    """Save image metadata for a POI"""
    metadata["updated_at"] = datetime.utcnow().isoformat() + "Z"

    metadata_path = get_metadata_path(city, poi_id)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def get_next_image_filename(city: str, poi_id: str) -> str:
    """Get next available image filename"""
    metadata = load_image_metadata(city, poi_id)
    existing_count = len(metadata["images"])
    return f"image_{existing_count + 1:03d}.jpg"


@router.post(
    "/{city}/{poi_id}/images",
    response_model=POIImageUploadResponse,
    dependencies=[Depends(require_backstage_admin)],
    tags=["backstage"]
)
async def upload_poi_image(
    city: str,
    poi_id: str,
    image: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, max 5MB)"),
    caption: Optional[str] = Form(None, description="Image caption"),
    is_cover: bool = Form(False, description="Set as cover image"),
    order: int = Form(0, description="Display order"),
    user_info: dict = Depends(require_backstage_admin)
):
    """
    Upload image for a POI (backstage admin only)

    - Maximum 5 images per POI
    - File size limit: 5MB
    - Formats: JPEG, PNG, WebP
    - Images are compressed automatically
    """
    # Validate image
    validate_image(image)

    # Load current metadata
    metadata = load_image_metadata(city, poi_id)

    # Check image limit
    if len(metadata["images"]) >= MAX_IMAGES_PER_POI:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_IMAGES_PER_POI} images per POI. Delete an existing image first."
        )

    # Read and compress image
    image_bytes = await image.read()
    compressed_bytes = compress_image(image_bytes)

    # Generate filename
    filename = get_next_image_filename(city, poi_id)

    # Save image file
    image_dir = get_poi_image_dir(city, poi_id)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / filename

    with open(image_path, 'wb') as f:
        f.write(compressed_bytes)

    # If this is set as cover, unset other covers
    if is_cover:
        for img in metadata["images"]:
            img["is_cover"] = False

    # Add to metadata
    image_metadata = {
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "uploaded_by": user_info.get("email", "unknown"),
        "caption": caption,
        "is_cover": is_cover,
        "order": order
    }
    metadata["images"].append(image_metadata)

    # Save metadata
    save_image_metadata(city, poi_id, metadata)

    logger.info(f"Uploaded image {filename} for POI {poi_id} in {city} by {user_info.get('email')}")

    return POIImageUploadResponse(
        success=True,
        filename=filename,
        url=f"/pois/{city}/{poi_id}/images/{filename}",
        message="Image uploaded successfully"
    )


@router.get(
    "/{city}/{poi_id}/images",
    response_model=POIImagesResponse
)
async def get_poi_images(city: str, poi_id: str):
    """
    Get list of images for a POI (public access)
    """
    metadata = load_image_metadata(city, poi_id)

    images = [
        ImageMetadata(
            filename=img["filename"],
            url=f"/pois/{city}/{poi_id}/images/{img['filename']}",
            caption=img.get("caption"),
            uploaded_at=img["uploaded_at"],
            uploaded_by=img["uploaded_by"],
            order=img.get("order", 0),
            is_cover=img.get("is_cover", False)
        )
        for img in metadata["images"]
    ]

    # Sort by order
    images.sort(key=lambda x: x.order)

    return POIImagesResponse(
        poi_id=poi_id,
        city=city,
        images=images
    )


@router.get(
    "/{city}/{poi_id}/images/{filename}",
    response_class=FileResponse
)
async def serve_poi_image(city: str, poi_id: str, filename: str):
    """
    Serve POI image file (public access)
    """
    image_path = get_poi_image_dir(city, poi_id) / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(
        path=image_path,
        media_type="image/jpeg",
        filename=filename
    )


@router.delete(
    "/{city}/{poi_id}/images/{filename}",
    response_model=SuccessResponse,
    dependencies=[Depends(require_backstage_admin)],
    tags=["backstage"]
)
async def delete_poi_image(
    city: str,
    poi_id: str,
    filename: str,
    user_info: dict = Depends(require_backstage_admin)
):
    """
    Delete POI image (backstage admin only)
    """
    # Load metadata
    metadata = load_image_metadata(city, poi_id)

    # Find image in metadata
    image_index = None
    for i, img in enumerate(metadata["images"]):
        if img["filename"] == filename:
            image_index = i
            break

    if image_index is None:
        raise HTTPException(status_code=404, detail="Image not found in metadata")

    # Delete file
    image_path = get_poi_image_dir(city, poi_id) / filename
    if image_path.exists():
        image_path.unlink()

    # Remove from metadata
    metadata["images"].pop(image_index)
    save_image_metadata(city, poi_id, metadata)

    logger.info(f"Deleted image {filename} for POI {poi_id} in {city} by {user_info.get('email')}")

    return SuccessResponse(
        message="Image deleted successfully",
        data={"filename": filename}
    )
