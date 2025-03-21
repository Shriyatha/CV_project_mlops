"""Main module for indexing and searching images and videos."""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import ffmpeg
import inflect
import nltk
from loguru import logger
from moviepy.editor import VideoFileClip
from nltk.stem import WordNetLemmatizer
from PIL import Image
from PIL.ExifTags import TAGS
from transformers import BlipForConditionalGeneration, BlipProcessor
from whoosh import index
from whoosh.fields import DATETIME, ID, TEXT, Schema
from whoosh.qparser import OrGroup, QueryParser

# Configure logging
logger.add(
    "app.log", rotation="10MB", level="INFO",
    format="{time} | {level} | {name}:{function}:{line} - {message}",
)

# Ensure NLTK resources are downloaded
nltk.download("wordnet")
nltk.download("omw-1.4")

# Initialize lemmatizer and inflect engine
lemmatizer = WordNetLemmatizer()
inflect_engine = inflect.engine()

# Set paths
IMAGE_FOLDER = "static/images"
VIDEO_FOLDER = "static/videos"
INDEX_FOLDER = "index"
FRAME_SAMPLE_RATE = 3  # Extract every 3 seconds for video captions

# Ensure required directories exist
for folder in [IMAGE_FOLDER, VIDEO_FOLDER, INDEX_FOLDER]:
    Path(folder).mkdir(parents=True, exist_ok=True)

# Define schema
schema = Schema(
    file_path=ID(stored=True),
    description=TEXT(stored=True),
    date=DATETIME(stored=True),  # Add date field for temporal queries
)

# Create or open index
if not Path(INDEX_FOLDER).joinpath("MAIN_0.toc").exists():
    ix = index.create_in(INDEX_FOLDER, schema)
else:
    ix = index.open_dir(INDEX_FOLDER)

# Load BLIP model
logger.info("Loading BLIP image captioning model...")
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
model = BlipForConditionalGeneration.from_pretrained(
    "Salesforce/blip-image-captioning-base",
)
logger.info("BLIP model loaded successfully!")


def extract_timestamp_from_image(image_path: str) -> datetime | None:
    """Extract timestamp from image EXIF data."""
    try:
        image = Image.open(image_path)
        exif_data = image.getexif()
        if exif_data is not None:
            for tag, value in exif_data.items():
                if TAGS.get(tag) == "DateTime":
                    return datetime.strptime(
                        value, "%Y:%m:%d %H:%M:%S",
                    ).replace(tzinfo=timezone.utc)
    except (AttributeError, KeyError) as e:
        logger.error(f"Error extracting EXIF data from image {image_path}: {e}")
    return None

def extract_timestamp_from_video(video_path: str) -> str | None:
    """Extract timestamp from video metadata using ffmpeg-python."""
    try:
        # Ensure the video path is valid and exists
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            logger.error("Video file not found: %s", video_path)
            return None

        # Convert to absolute path
        video_path = str(video_path_obj.resolve())

        # Use ffmpeg.probe to extract metadata
        metadata = ffmpeg.probe(video_path)
        for stream in metadata.get("streams", []):
            creation_time = stream.get("tags", {}).get("creation_time")
            if creation_time:
                return creation_time

    except ffmpeg.Error:
        logger.error("FFmpeg error while extracting timestamp")
    except FileNotFoundError:
        logger.error("File disappeared before processing: %s", video_path)
    return None


def generate_caption(image_path: str) -> str:
    """Generate an image caption using the BLIP model."""
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(images=image, return_tensors="pt")
        output = model.generate(**inputs)
        caption = processor.decode(output[0], skip_special_tokens=True)
        logger.info(f"Generated caption for {image_path}: {caption}")
    except (AttributeError, KeyError) as e:
        logger.error(f"Error processing {image_path}: {e}")
        return "No description available."
    else:
        return caption


def extract_video_caption(video_path: str | Path) -> str:
    """Extract frames from a video and generate an overall description."""
    # Convert video_path to a string if it's a Path object
    video_path_str = str(video_path) if isinstance(video_path, Path) else video_path

    clip = VideoFileClip(video_path_str)  # Pass the string path to moviepy
    duration = int(clip.duration)
    descriptions = []
    try:
        for i in range(0, duration, FRAME_SAMPLE_RATE):
            frame = clip.get_frame(i)
            frame_path = f"temp_frame_{i}.jpg"
            Image.fromarray(frame).save(frame_path)
            caption = generate_caption(frame_path)
            descriptions.append(caption)
            Path(frame_path).unlink()
    except (OSError, subprocess.CalledProcessError) as e:
        logger.warning(f"Error processing frame at {i}s: {e}")
    return " ".join(descriptions) if descriptions else "No description available."


def index_data() -> None:
    """Index images and videos."""
    try:
        if Path(INDEX_FOLDER).exists():
            shutil.rmtree(INDEX_FOLDER)

        # Create the index folder
        Path(INDEX_FOLDER).mkdir(parents=True, exist_ok=True)

        # Create or open the index
        ix = index.create_in(INDEX_FOLDER, schema)
        writer = ix.writer()

        for img_file in os.listdir(IMAGE_FOLDER):
            img_path = Path(IMAGE_FOLDER) / img_file
            if img_file.lower().endswith((".png", ".jpg", ".jpeg")):
                caption = generate_caption(img_path)
                timestamp = extract_timestamp_from_image(img_path)
                writer.add_document(
                    file_path=str(img_path),  # Convert Path to string
                    description=caption,
                    date=timestamp or datetime.now(timezone.utc),
                )
                logger.info(f"Indexed image: {img_path}")

        for video_file in os.listdir(VIDEO_FOLDER):
            if video_file.lower().endswith((".mp4", ".avi", ".mov")):
                video_path = Path(VIDEO_FOLDER) / video_file
                video_caption = extract_video_caption(video_path)
                timestamp = extract_timestamp_from_video(video_path)
                if timestamp == "Unknown":
                    timestamp = datetime.now(timezone.utc)
                if isinstance(timestamp, str):
                    try:
                        timestamp = datetime.strptime(
                            timestamp, "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
                    except ValueError:
                        timestamp = datetime.now(timezone.utc)

                # Add the document to the index
                writer.add_document(
                    file_path=str(video_path),
                    description=video_caption,
                    date=timestamp,
                )
                logger.info(f"Indexed video: {video_path}")

        writer.commit()
        logger.info("Indexing complete!")
    except (subprocess.CalledProcessError, OSError) as e:
        logger.error(f"Error indexing data: {e}")
        return

def search_with_filters(
    query: str,
    file_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[dict]:
    """Search with optional filters for file type and date range."""
    search_results = []

    with ix.searcher() as searcher:
        # Handle NOT operator explicitly
        if " NOT " in query:
            main_query, exclude_term = query.split(" NOT ", 1)
            main_query = main_query.strip()
            exclude_term = exclude_term.strip().lower()  # Case-insensitive exclusion
        else:
            main_query = query
            exclude_term = None

        # Parse the main query
        qp = QueryParser("description", ix.schema, group=OrGroup)
        q = qp.parse(main_query)

        # Perform the search
        results = searcher.search(q, limit=10)

        # Filter results by date range and exclude_term
        filtered_results = []
        for hit in results:
            if exclude_term and exclude_term in hit["description"].lower():
                continue  # Skip documents containing the exclude_term
            if file_type and file_type not in hit["file_path"]:
                continue
            if start_date and hit["date"] < start_date:
                continue
            if end_date and hit["date"] > end_date:
                continue
            filtered_results.append((hit["file_path"], hit["description"], hit["date"]))

        search_results = [(img, desc) for img, desc, _ in filtered_results]

    logger.info(f"Search results for '{query}': {search_results}")
    return search_results


def run_advanced_search(
    query: str,
    file_type: str,
    start_date: datetime | None,
    end_date: datetime | None,
) -> list[dict]:
    """Search UI function for retrieving images and videos."""
    return search_with_filters(query, file_type, start_date, end_date)


# Run indexing before launching the UI
index_data()
