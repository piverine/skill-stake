import google.generativeai as genai
from pathlib import Path
from typing import Optional
import asyncio
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

class PDFProcessorService:
    """Service for processing PDF files using Gemini 2.0 Flash API."""
    
    def __init__(self):
        """Initialize the PDF processor with Gemini API configuration."""
        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is required for PDF processing")
        
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    async def extract_text_from_pdf(self, file_path: Path) -> str:
        """
        Extract text content from a PDF file using Gemini 2.0 Flash multimodal capabilities.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content as string
            
        Raises:
            Exception: If PDF processing fails
        """
        try:
            if not file_path.exists():
                raise FileNotFoundError(f"PDF file not found: {file_path}")
            
            # Read PDF file
            with open(file_path, 'rb') as f:
                pdf_data = f.read()
            
            # Create a file object for Gemini API
            pdf_file = {
                'mime_type': 'application/pdf',
                'data': pdf_data
            }
            
            # Prompt for text extraction
            prompt = """
            Please extract all the text content from this PDF document. 
            Preserve the structure and formatting as much as possible.
            Include headings, paragraphs, lists, and any other textual content.
            Do not include any commentary or analysis, just the raw text content.
            """
            
            # Function to try generation with a specific model
            async def generate_with_model(model_name: str, retries: int = 3) -> str:
                current_model = genai.GenerativeModel(model_name)
                last_error = None
                
                for attempt in range(retries):
                    try:
                        logger.info(f"Attempting PDF processing with model {model_name} (attempt {attempt+1}/{retries})")
                        response = await asyncio.to_thread(
                            current_model.generate_content,
                            [prompt, pdf_file]
                        )
                        
                        if not response.text:
                            raise Exception("No text content extracted from PDF")
                            
                        return response.text
                        
                    except Exception as e:
                        last_error = e
                        error_str = str(e)
                        
                        # Check for quota exceeded or rate limit errors
                        if "429" in error_str or "quota" in error_str.lower():
                            wait_time = 2 ** (attempt + 1) + 1  # Exponential backoff
                            logger.warning(f"Rate limit hit for {model_name}, waiting {wait_time}s before retry")
                            await asyncio.sleep(wait_time)
                        else:
                            # For other errors, maybe don't retry as aggressively or re-raise
                            logger.warning(f"Error with {model_name}: {error_str}")
                
                raise last_error

            # Try primary model (gemini-3-flash-preview) first
            try:
                extracted_text = await generate_with_model('gemini-3-flash-preview')
            except Exception as e:
                logger.warning(f"Primary model failed: {str(e)}. Falling back to gemini-1.5-flash")
                try:
                    # Fallback to gemini-1.5-flash
                    extracted_text = await generate_with_model('gemini-1.5-flash')
                except Exception as fallback_error:
                    logger.error(f"Fallback model also failed: {str(fallback_error)}")
                    raise Exception(f"PDF processing failed with both models. Last error: {str(fallback_error)}")

            extracted_text = extracted_text.strip()
            
            # Validate extracted text
            if len(extracted_text) < 10:
                raise Exception("Extracted text is too short, PDF may be corrupted or contain no text")
            
            logger.info(f"Successfully extracted {len(extracted_text)} characters from PDF: {file_path.name}")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Failed to extract text from PDF {file_path}: {str(e)}")
            raise Exception(f"PDF text extraction failed: {str(e)}")
    
    async def validate_pdf_content(self, extracted_text: str) -> bool:
        """
        Validate that extracted text contains meaningful content for quiz generation.
        
        Args:
            extracted_text: The extracted text content
            
        Returns:
            True if content is suitable for quiz generation, False otherwise
        """
        if not extracted_text or len(extracted_text.strip()) < 100:
            return False
        
        # Check for minimum word count (at least 50 words for meaningful quiz generation)
        word_count = len(extracted_text.split())
        if word_count < 50:
            return False
        
        # Check that it's not just repetitive content
        unique_words = set(extracted_text.lower().split())
        if len(unique_words) < 20:  # At least 20 unique words
            return False
        
        return True
    
    def get_text_statistics(self, extracted_text: str) -> dict:
        """
        Get statistics about the extracted text.
        
        Args:
            extracted_text: The extracted text content
            
        Returns:
            Dictionary with text statistics
        """
        if not extracted_text:
            return {
                'character_count': 0,
                'word_count': 0,
                'unique_words': 0,
                'estimated_reading_time_minutes': 0
            }
        
        words = extracted_text.split()
        unique_words = set(word.lower().strip('.,!?;:"()[]{}') for word in words)
        
        # Estimate reading time (average 200 words per minute)
        reading_time = max(1, len(words) / 200)
        
        return {
            'character_count': len(extracted_text),
            'word_count': len(words),
            'unique_words': len(unique_words),
            'estimated_reading_time_minutes': round(reading_time, 1)
        }