"""
Property-based tests for PDF processing pipeline.

Feature: skill-stake-learning, Property 2: PDF Processing Round Trip
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch, AsyncMock
import tempfile
import os
from pathlib import Path
import uuid
from decimal import Decimal

from app.services.pdf_processor import PDFProcessorService
from app.services.quiz_generator import QuizGeneratorService
from app.schemas.pdf_upload import PDFUploadCreate, ProcessingStatus
from app.schemas.quiz import QuizQuestion, GeneratedQuiz
from app.crud.pdf_upload import pdf_upload_crud
from app.models.user import User


# Hypothesis strategies for generating test data
@st.composite
def valid_pdf_filename(draw):
    """Generate valid PDF filenames."""
    base_name = draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Pc', 'Pd'))))
    # Ensure it doesn't start with a dot or contain invalid characters
    base_name = base_name.strip('.-_')
    if not base_name:
        base_name = "document"
    return f"{base_name}.pdf"

@st.composite
def valid_file_size(draw):
    """Generate valid file sizes (1 byte to 50MB)."""
    return draw(st.integers(min_value=1, max_value=50*1024*1024))

@st.composite
def extracted_text_content(draw):
    """Generate realistic extracted text content."""
    # Generate meaningful text content that could come from a PDF
    paragraphs = draw(st.lists(
        st.text(min_size=50, max_size=500, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Po', 'Zs'))),
        min_size=2, max_size=10
    ))
    return "\n\n".join(paragraphs)

@st.composite
def mock_quiz_questions(draw):
    """Generate valid quiz questions for mocking."""
    questions = []
    for i in range(10):
        question_text = draw(st.text(min_size=20, max_size=200))
        options = draw(st.lists(
            st.text(min_size=5, max_size=50), 
            min_size=4, max_size=4, unique=True
        ))
        correct_answer = draw(st.integers(min_value=0, max_value=3))
        
        questions.append(QuizQuestion(
            question_id=f"q_{i+1}",
            question_text=question_text,
            options=options,
            correct_answer=correct_answer
        ))
    return questions


class TestPDFProcessingProperty:
    """Property-based tests for PDF processing pipeline."""

    @given(valid_pdf_filename(), valid_file_size())
    @settings(max_examples=100)
    def test_pdf_upload_validation_consistency(self, filename, file_size):
        """
        Property 2: PDF Processing Round Trip
        For any valid PDF filename and file size, upload validation should be consistent.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        # Test that valid inputs always pass validation
        upload_data = PDFUploadCreate(
            filename=filename,
            file_size=file_size
        )
        
        # Should not raise validation errors
        assert upload_data.filename == filename
        assert upload_data.file_size == file_size
        assert upload_data.filename.endswith('.pdf')

    @given(st.text(min_size=1, max_size=100), valid_file_size())
    @settings(max_examples=50)
    def test_non_pdf_files_rejected(self, base_filename, file_size):
        """
        Property 2: PDF Processing Round Trip
        For any non-PDF filename, validation should consistently reject the file.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        assume(not base_filename.lower().endswith('.pdf'))
        
        # Non-PDF files should be rejected
        with pytest.raises(ValueError, match="File must be a PDF"):
            PDFUploadCreate(
                filename=base_filename,
                file_size=file_size
            )

    @given(valid_pdf_filename())
    @settings(max_examples=50)
    def test_oversized_files_rejected(self, filename):
        """
        Property 2: PDF Processing Round Trip
        For any file size exceeding limits, validation should consistently reject.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        oversized = 51 * 1024 * 1024  # 51MB (over the 50MB limit)
        
        with pytest.raises(ValueError, match="File size .* exceeds maximum"):
            PDFUploadCreate(
                filename=filename,
                file_size=oversized
            )

    @given(extracted_text_content())
    @settings(max_examples=50)
    @patch('app.services.pdf_processor.genai')
    async def test_text_extraction_consistency(self, extracted_text, mock_genai):
        """
        Property 2: PDF Processing Round Trip
        For any valid extracted text, the processing pipeline should handle it consistently.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        # Mock Gemini API response
        mock_response = Mock()
        mock_response.text = extracted_text
        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = Mock()
        
        # Create temporary PDF file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b'%PDF-1.4 fake pdf content')
            temp_path = Path(temp_file.name)
        
        try:
            processor = PDFProcessorService()
            
            # Extract text should return the mocked content
            result = await processor.extract_text_from_pdf(temp_path)
            
            assert result == extracted_text.strip()
            assert len(result) >= 10  # Minimum length check
            
        finally:
            # Clean up
            if temp_path.exists():
                os.unlink(temp_path)

    @given(extracted_text_content(), valid_pdf_filename(), mock_quiz_questions())
    @settings(max_examples=30)
    @patch('app.services.quiz_generator.genai')
    async def test_quiz_generation_consistency(self, extracted_text, filename, mock_questions):
        """
        Property 2: PDF Processing Round Trip
        For any valid extracted text, quiz generation should produce consistent results.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        # Mock Gemini API response for quiz generation
        quiz_json = {
            "questions": [
                {
                    "question_text": q.question_text,
                    "options": q.options,
                    "correct_answer": q.correct_answer
                }
                for q in mock_questions
            ]
        }
        
        import json
        mock_response = Mock()
        mock_response.text = json.dumps(quiz_json)
        mock_model = Mock()
        mock_model.generate_content = Mock(return_value=mock_response)
        mock_genai.GenerativeModel.return_value = mock_model
        mock_genai.configure = Mock()
        
        generator = QuizGeneratorService()
        
        # Generate quiz from text
        result = await generator.generate_quiz_from_text(extracted_text, filename)
        
        # Verify consistency properties
        assert isinstance(result, GeneratedQuiz)
        assert len(result.questions) == 10
        assert result.source_material == filename
        
        # Verify each question structure
        for i, question in enumerate(result.questions):
            assert question.question_id == f"q_{i+1}"
            assert len(question.options) == 4
            assert 0 <= question.correct_answer <= 3
            assert len(question.question_text) >= 10

    @given(extracted_text_content())
    @settings(max_examples=50)
    def test_text_validation_consistency(self, extracted_text):
        """
        Property 2: PDF Processing Round Trip
        For any text content, validation should be consistent with content quality.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        processor = PDFProcessorService()
        
        # Test content validation
        is_valid = await processor.validate_pdf_content(extracted_text)
        
        # Validation should be consistent with content properties
        word_count = len(extracted_text.split())
        unique_words = len(set(extracted_text.lower().split()))
        
        if len(extracted_text.strip()) >= 100 and word_count >= 50 and unique_words >= 20:
            assert is_valid, f"Content should be valid: {len(extracted_text)} chars, {word_count} words, {unique_words} unique"
        else:
            assert not is_valid, f"Content should be invalid: {len(extracted_text)} chars, {word_count} words, {unique_words} unique"

    @given(extracted_text_content())
    @settings(max_examples=50)
    def test_text_statistics_consistency(self, extracted_text):
        """
        Property 2: PDF Processing Round Trip
        For any text content, statistics should be mathematically consistent.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        processor = PDFProcessorService()
        
        stats = processor.get_text_statistics(extracted_text)
        
        # Verify mathematical consistency
        assert stats['character_count'] == len(extracted_text)
        
        words = extracted_text.split()
        assert stats['word_count'] == len(words)
        
        # Reading time should be reasonable (based on 200 words per minute)
        expected_reading_time = max(1, len(words) / 200)
        assert abs(stats['estimated_reading_time_minutes'] - expected_reading_time) < 0.1
        
        # Unique words should be <= total words
        assert stats['unique_words'] <= stats['word_count']

    @given(valid_pdf_filename(), valid_file_size(), extracted_text_content())
    @settings(max_examples=30)
    def test_upload_record_creation_consistency(self, db_session, filename, file_size, extracted_text):
        """
        Property 2: PDF Processing Round Trip
        For any valid upload data, database record creation should be consistent.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        # Create a test user
        user = User(
            clerk_id=f"test_user_{uuid.uuid4()}",
            email=f"test_{uuid.uuid4()}@example.com"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        # Create upload record
        upload_data = PDFUploadCreate(
            filename=filename,
            file_size=file_size
        )
        
        upload_record = pdf_upload_crud.create_upload(
            db=db_session,
            upload_in=upload_data,
            user_id=str(user.user_id)
        )
        
        # Verify consistency
        assert upload_record.filename == filename
        assert upload_record.file_size == file_size
        assert upload_record.user_id == user.user_id
        assert upload_record.processing_status == ProcessingStatus.UPLOADED
        assert upload_record.upload_id is not None
        assert upload_record.created_at is not None
        
        # Test status update consistency
        updated_record = pdf_upload_crud.update_processing_status(
            db=db_session,
            upload_id=str(upload_record.upload_id),
            status=ProcessingStatus.COMPLETED,
            extracted_text=extracted_text
        )
        
        assert updated_record.processing_status == ProcessingStatus.COMPLETED
        assert updated_record.extracted_text == extracted_text

    @given(st.integers(min_value=0, max_value=100))
    @settings(max_examples=50)
    def test_empty_content_handling(self, padding_length):
        """
        Property 2: PDF Processing Round Trip
        For any empty or minimal content, the system should handle it consistently.
        Validates: Requirements 2.1, 2.2, 2.3, 2.5
        """
        # Generate minimal content (empty or very short)
        minimal_content = " " * padding_length
        
        processor = PDFProcessorService()
        
        # Empty content should always be invalid
        is_valid = await processor.validate_pdf_content(minimal_content)
        assert not is_valid
        
        # Statistics should handle empty content gracefully
        stats = processor.get_text_statistics(minimal_content)
        assert stats['character_count'] == len(minimal_content)
        assert stats['word_count'] == 0 if not minimal_content.strip() else len(minimal_content.split())
        assert stats['unique_words'] >= 0
        assert stats['estimated_reading_time_minutes'] >= 0