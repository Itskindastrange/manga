from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
from huggingface_hub import InferenceClient
from PIL import Image
import os
import logging
import io
import base64
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configuration
HF_TOKEN = os.environ.get('HF_TOKEN')
MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '10485760'))
TIMEOUT_SECONDS = int(os.environ.get('TIMEOUT_SECONDS', '120'))

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required")

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Hugging Face client
hf_client = InferenceClient(token=HF_TOKEN, timeout=TIMEOUT_SECONDS)

# Create the main app
app = FastAPI(
    title="Colorify Manga API",
    description="AI-powered manga colorization service",
    version="1.0.0"
)

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class ColorizationCreate(BaseModel):
    original_image: str  # base64 encoded
    user_id: str
    model_id: Optional[str] = "TencentARC/ColorFlow"

class Colorization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    original_image: str
    colorized_image: str
    model_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserProfile(BaseModel):
    id: str
    email: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    colorization_count: int = 0

# Middleware for file size limit
class LimitUploadSizeMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_upload_size: int):
        super().__init__(app)
        self.max_upload_size = max_upload_size
    
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            if "content-length" in request.headers:
                content_length = int(request.headers["content-length"])
                if content_length > self.max_upload_size:
                    return Response(
                        content=f"File size exceeds maximum allowed size of {self.max_upload_size} bytes",
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
                    )
        
        return await call_next(request)

app.add_middleware(LimitUploadSizeMiddleware, max_upload_size=MAX_FILE_SIZE)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string"""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG", quality=95)
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

def base64_to_image(base64_str: str) -> Image.Image:
    """Convert base64 string to PIL Image"""
    if base64_str.startswith('data:image'):
        base64_str = base64_str.split(',')[1]
    image_data = base64.b64decode(base64_str)
    return Image.open(io.BytesIO(image_data))

def preprocess_image(image: Image.Image, max_dimension: int = 1024) -> Image.Image:
    """Resize large images to prevent memory issues"""
    width, height = image.size
    
    if max(width, height) <= max_dimension:
        return image
    
    # Calculate scaling factor
    scale = max_dimension / max(width, height)
    new_width = int(width * scale)
    new_height = int(height * scale)
    
    logger.info(f"Resizing from {width}x{height} to {new_width}x{new_height}")
    resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    return resized

# Routes
@api_router.get("/")
async def root():
    return {
        "message": "Colorify Manga API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health",
            "colorize": "/api/colorize",
            "history": "/api/colorizations/{user_id}"
        }
    }

@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Colorify Manga API",
        "version": "1.0.0"
    }

@api_router.post("/colorize", response_model=Colorization)
async def colorize_manga(
    file: UploadFile = File(..., description="Black and white manga image to colorize"),
    user_id: str = "anonymous",
    model_id: str = "hakurei/waifu-diffusion-v1-4"
):
    """
    Colorize a black and white manga page using Hugging Face Inference API with DDColor model.
    """
    logger.info(f"Received colorization request for file: {file.filename}")
    
    # Validate file format
    allowed_formats = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed_formats:
        logger.warning(f"Invalid file format: {file.content_type}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file format. Allowed formats: JPEG, PNG, WebP"
        )
    
    try:
        # Read uploaded file
        contents = await file.read()
        logger.info(f"Read {len(contents)} bytes from uploaded file")
        
        # Open image with PIL
        try:
            image = Image.open(io.BytesIO(contents))
            logger.info(f"Image loaded: {image.size}, mode: {image.mode}")
        except Exception as e:
            logger.error(f"Failed to load image: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or corrupted image file"
            )
        
        # Convert to RGB if necessary
        if image.mode != "RGB":
            logger.info(f"Converting image from {image.mode} to RGB")
            image = image.convert("RGB")
        
        # Preprocess image - DDColor works best with smaller images
        image = preprocess_image(image, max_dimension=512)
        
        # Convert original to base64 for storage
        original_base64 = image_to_base64(image)
        
        # Save image to bytes for API call
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        
        # Call Hugging Face Inference API with DDColor
        try:
            logger.info(f"Calling Inference API with model: {model_id}")
            colorized_image = hf_client.image_to_image(
                image=img_byte_arr.getvalue(),
                model=model_id
            )
            logger.info("Successfully received colorized image from API")
        except Exception as api_error:
            logger.error(f"Inference API error: {str(api_error)}")
            error_str = str(api_error).lower()
            
            if "rate limit" in error_str or "429" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="API rate limit exceeded. Please try again later."
                )
            elif "not found" in error_str or "404" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Model {model_id} not found or not available"
                )
            elif "model is currently loading" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Model is loading. Please try again in a few moments."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Colorization service error: {str(api_error)}"
                )
        
        # Convert colorized image to base64
        colorized_base64 = image_to_base64(colorized_image)
        
        # Create colorization record
        colorization = Colorization(
            user_id=user_id,
            original_image=original_base64,
            colorized_image=colorized_base64,
            model_id=model_id
        )
        
        # Save to database
        await db.colorizations.insert_one(colorization.dict())
        logger.info(f"Saved colorization {colorization.id} to database")
        
        # Update user's colorization count
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"colorization_count": 1}},
            upsert=True
        )
        
        return colorization
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during colorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during processing"
        )
    finally:
        await file.close()

@api_router.get("/colorizations/{user_id}", response_model=List[Colorization])
async def get_user_colorizations(user_id: str, limit: int = 50):
    """
    Get colorization history for a specific user.
    """
    try:
        colorizations = await db.colorizations.find(
            {"user_id": user_id}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return [Colorization(**c) for c in colorizations]
    except Exception as e:
        logger.error(f"Error fetching colorizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching colorization history"
        )

@api_router.delete("/colorizations/{colorization_id}")
async def delete_colorization(colorization_id: str):
    """
    Delete a specific colorization.
    """
    try:
        result = await db.colorizations.delete_one({"id": colorization_id})
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Colorization not found"
            )
        
        return {"message": "Colorization deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting colorization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting colorization"
        )

# Include router
app.include_router(api_router)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
