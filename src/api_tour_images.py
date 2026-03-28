"""
Tour Image Management API

Handles image upload, serving, and deletion for tours.
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
    TourImageUploadResponse,
    TourImagesResponse,
    ImageMetadata,
    SuccessResponse
)
from auth.dependencies import require_backstage_admin

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/tours",
    tags=["tour-images"]
)

# Constants
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_GALLERY_IMAGES = 10
ALLOWED_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
TOURS_DIR = Path("tours")


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


def find_tour_path(tour_id: str) -> Path:
    """Find tour directory by searching all cities"""
    for city_dir in TOURS_DIR.iterdir():
        if not city_dir.is_dir():
            continue

        tour_path = city_dir / tour_id
        if tour_path.exists():
            return tour_path

    raise HTTPException(status_code=404, detail=f"Tour {tour_id} not found")


def get_tour_image_dir(tour_id: str) -> Path:
    """Get image directory for a tour"""
    tour_path = find_tour_path(tour_id)
    return tour_path / "images"


def get_tour_metadata_path(tour_id: str) -> Path:
    """Get metadata.json path for tour"""
    tour_path = find_tour_path(tour_id)
    return tour_path / "metadata.json"


def load_tour_metadata(tour_id: str) -> dict:
    """Load tour metadata"""
    metadata_path = get_tour_metadata_path(tour_id)

    if not metadata_path.exists():
        raise HTTPException(status_code=404, detail="Tour metadata not found")

    with open(metadata_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tour_metadata(tour_id: str, metadata: dict) -> None:
    """Save tour metadata"""
    metadata["updated_at"] = datetime.utcnow().isoformat() + "Z"

    metadata_path = get_tour_metadata_path(tour_id)

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


@router.post(
    "/{tour_id}/images",
    response_model=TourImageUploadResponse,
    dependencies=[Depends(require_backstage_admin)],
    tags=["backstage"]
)
async def upload_tour_image(
    tour_id: str,
    image: UploadFile = File(..., description="Image file (JPEG, PNG, WebP, max 5MB)"),
    image_type: str = Form(..., description="Image type: 'cover' or 'gallery'"),
    caption: Optional[str] = Form(None, description="Image caption"),
    order: int = Form(0, description="Display order (for gallery images)"),
    user_info: dict = Depends(require_backstage_admin)
):
    """
    Upload image for a tour (backstage admin only)

    - 1 cover image + max 10 gallery images
    - File size limit: 5MB
    - Formats: JPEG, PNG, WebP
    - Images are compressed automatically
    """
    # Validate image type
    if image_type not in ['cover', 'gallery']:
        raise HTTPException(
            status_code=400,
            detail="image_type must be 'cover' or 'gallery'"
        )

    # Validate image
    validate_image(image)

    # Load tour metadata
    metadata = load_tour_metadata(tour_id)

    # Initialize images field if not present
    if "images" not in metadata:
        metadata["images"] = {
            "cover": None,
            "gallery": []
        }

    # Check gallery limit
    if image_type == 'gallery' and len(metadata["images"]["gallery"]) >= MAX_GALLERY_IMAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {MAX_GALLERY_IMAGES} gallery images per tour. Delete an existing image first."
        )

    # Read and compress image
    image_bytes = await image.read()
    compressed_bytes = compress_image(image_bytes)

    # Generate filename
    if image_type == 'cover':
        filename = "cover.jpg"
    else:
        # Find next available gallery number
        existing_nums = []
        for img in metadata["images"]["gallery"]:
            try:
                num = int(img["filename"].split("_")[1].split(".")[0])
                existing_nums.append(num)
            except:
                pass
        next_num = max(existing_nums) + 1 if existing_nums else 1
        filename = f"gallery_{next_num:03d}.jpg"

    # Save image file
    image_dir = get_tour_image_dir(tour_id)
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = image_dir / filename

    # If replacing cover, delete old cover
    if image_type == 'cover' and metadata["images"]["cover"]:
        old_cover_path = image_dir / metadata["images"]["cover"]["filename"]
        if old_cover_path.exists():
            old_cover_path.unlink()

    with open(image_path, 'wb') as f:
        f.write(compressed_bytes)

    # Update metadata
    image_metadata = {
        "filename": filename,
        "uploaded_at": datetime.utcnow().isoformat() + "Z",
        "uploaded_by": user_info.get("email", "unknown"),
        "caption": caption
    }

    if image_type == 'cover':
        metadata["images"]["cover"] = image_metadata
    else:
        image_metadata["order"] = order
        metadata["images"]["gallery"].append(image_metadata)

    # Save metadata
    save_tour_metadata(tour_id, metadata)

    logger.info(f"Uploaded {image_type} image {filename} for tour {tour_id} by {user_info.get('email')}")

    return TourImageUploadResponse(
        success=True,
        filename=filename,
        url=f"/tours/{tour_id}/images/{filename}",
        image_type=image_type,
        message=f"Tour {image_type} image uploaded successfully"
    )


@router.get(
    "/{tour_id}/images",
    response_model=TourImagesResponse
)
async def get_tour_images(tour_id: str):
    """
    Get images for a tour (public access)
    """
    metadata = load_tour_metadata(tour_id)

    # Check if images field exists
    if "images" not in metadata or not metadata["images"]:
        return TourImagesResponse(
            tour_id=tour_id,
            cover=None,
            gallery=[]
        )

    # Build cover image
    cover = None
    if metadata["images"].get("cover"):
        cover_data = metadata["images"]["cover"]
        cover = ImageMetadata(
            filename=cover_data["filename"],
            url=f"/tours/{tour_id}/images/{cover_data['filename']}",
            caption=cover_data.get("caption"),
            uploaded_at=cover_data["uploaded_at"],
            uploaded_by=cover_data["uploaded_by"],
            order=0,
            is_cover=True
        )

    # Build gallery images
    gallery = [
        ImageMetadata(
            filename=img["filename"],
            url=f"/tours/{tour_id}/images/{img['filename']}",
            caption=img.get("caption"),
            uploaded_at=img["uploaded_at"],
            uploaded_by=img["uploaded_by"],
            order=img.get("order", 0),
            is_cover=False
        )
        for img in metadata["images"].get("gallery", [])
    ]

    # Sort gallery by order
    gallery.sort(key=lambda x: x.order)

    return TourImagesResponse(
        tour_id=tour_id,
        cover=cover,
        gallery=gallery
    )


@router.get(
    "/{tour_id}/images/{filename}",
    response_class=FileResponse
)
async def serve_tour_image(tour_id: str, filename: str):
    """
    Serve tour image file (public access)
    """
    image_path = get_tour_image_dir(tour_id) / filename

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="Image not found")

    return FileResponse(
        path=image_path,
        media_type="image/jpeg",
        filename=filename
    )


@router.delete(
    "/{tour_id}/images/{filename}",
    response_model=SuccessResponse,
    dependencies=[Depends(require_backstage_admin)],
    tags=["backstage"]
)
async def delete_tour_image(
    tour_id: str,
    filename: str,
    user_info: dict = Depends(require_backstage_admin)
):
    """
    Delete tour image (backstage admin only)
    """
    # Load metadata
    metadata = load_tour_metadata(tour_id)

    if "images" not in metadata:
        raise HTTPException(status_code=404, detail="No images found for this tour")

    # Check if it's cover or gallery
    deleted = False

    if metadata["images"].get("cover") and metadata["images"]["cover"]["filename"] == filename:
        # Delete cover
        metadata["images"]["cover"] = None
        deleted = True
    else:
        # Try to delete from gallery
        for i, img in enumerate(metadata["images"].get("gallery", [])):
            if img["filename"] == filename:
                metadata["images"]["gallery"].pop(i)
                deleted = True
                break

    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found in tour metadata")

    # Delete file
    image_path = get_tour_image_dir(tour_id) / filename
    if image_path.exists():
        image_path.unlink()

    # Save metadata
    save_tour_metadata(tour_id, metadata)

    logger.info(f"Deleted image {filename} for tour {tour_id} by {user_info.get('email')}")

    return SuccessResponse(
        message="Image deleted successfully",
        data={"filename": filename}
    )
