"""
Certificate Field Extraction Module
Handles OCR and intelligent field extraction from certificates with confidence scoring
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Tuple
import pytesseract
from PIL import Image
import pdfplumber
from pdf2image.pdf2image import convert_from_path
from docx import Document
import spacy

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("SpaCy model not found. Run: python -m spacy download en_core_web_sm")
    nlp = None


class FieldExtractor:
    """Extract fields from certificate text with confidence scoring"""
    
    def __init__(self):
        self.nlp = nlp
        
        # Regex patterns for field detection
        self.patterns = {
            'apaar_id': r'APAAR[-_]?([A-Z0-9-]{8,})',
            'cert_id': r'(?:Certificate|Cert)\s*(?:ID|No|Number)?\s*:?\s*([A-Z0-9-]{6,})',
            'gst': r'\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b',
            'cin': r'\b([LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6})\b',
            'hours': r'(\d+)\s*(?:hours?|hrs?)',
            'institution_code': r'(?:Institution|College|University)\s*Code\s*:?\s*([A-Z0-9-]{4,})',
            'email': r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
        }
        
        # Date patterns
        self.date_patterns = [
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})',  # dd/mm/yyyy or dd-mm-yyyy
            r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})',  # yyyy-mm-dd
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})',  # Month dd, yyyy
        ]
        
        # Context keywords for boosting confidence
        self.name_anchors = ['certify that', 'awarded to', 'presented to', 'this is to certify', 'student name']
        self.org_anchors = ['organization', 'company', 'at', 'with']
        self.title_anchors = ['internship title', 'position', 'role', 'as']
        
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract fields from certificate text with confidence scores
        
        Args:
            text: Certificate text content
            
        Returns:
            Dictionary of fields with values and confidence scores
        """
        if not text or not text.strip():
            return self._empty_result()
        
        text_lower = text.lower()
        result = {}
        
        # Extract using regex patterns
        result['apaar_id'] = self._extract_pattern(text, 'apaar_id')
        result['cert_id'] = self._extract_pattern(text, 'cert_id')
        result['gst'] = self._extract_pattern(text, 'gst')
        result['cin'] = self._extract_pattern(text, 'cin')
        result['hours'] = self._extract_hours(text)
        result['institution_code'] = self._extract_pattern(text, 'institution_code')
        
        # Extract dates
        dates = self._extract_dates(text)
        result['start_date'] = dates.get('start', {'value': '', 'conf': 0.0})
        result['end_date'] = dates.get('end', {'value': '', 'conf': 0.0})
        
        # Use spaCy NER if available
        if self.nlp:
            doc = self.nlp(text)
            
            # Extract person name (student name)
            result['name'] = self._extract_person_name(doc, text)
            
            # Extract organization
            result['organization'] = self._extract_organization(doc, text)
            
            # Extract internship title (from context)
            result['internship_title'] = self._extract_title(text, doc)
            
            # Extract signatory info
            result['signatory_name'] = self._extract_signatory(doc, text)
            result['signatory_email'] = self._extract_pattern(text, 'email')
        else:
            # Fallback without spaCy
            result['name'] = {'value': '', 'conf': 0.0}
            result['organization'] = {'value': '', 'conf': 0.0}
            result['internship_title'] = {'value': '', 'conf': 0.0}
            result['signatory_name'] = {'value': '', 'conf': 0.0}
            result['signatory_email'] = self._extract_pattern(text, 'email')
        
        return result
    
    def extract_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        Extract fields from certificate file (image, PDF, DOCX)
        
        Args:
            file_path: Path to certificate file
            
        Returns:
            Dictionary of fields with values and confidence scores
        """
        file_path_lower = file_path.lower()
        
        try:
            # Handle DOCX files
            if file_path_lower.endswith('.docx'):
                text = self._read_docx(file_path)
                return self.extract_from_text(text)
            
            # Handle PDF files
            elif file_path_lower.endswith('.pdf'):
                text = self._read_pdf(file_path)
                return self.extract_from_text(text)
            
            # Handle image files
            elif file_path_lower.endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
                text = self._read_image_ocr(file_path)
                return self.extract_from_text(text)
            
            # Handle text files
            elif file_path_lower.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    text = f.read()
                return self.extract_from_text(text)
            
            else:
                return self._empty_result()
                
        except Exception as e:
            print(f"Error extracting from file: {e}")
            return self._empty_result()
    
    def _read_docx(self, file_path: str) -> str:
        """Read text from DOCX file"""
        doc = Document(file_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    
    def _read_pdf(self, file_path: str) -> str:
        """Read text from PDF (searchable or scanned)"""
        text = ""
        
        # Try reading searchable PDF first
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"PDFPlumber error: {e}")
        
        # If no text extracted, try OCR
        if not text.strip():
            try:
                images = convert_from_path(file_path)
                for img in images:
                    text += pytesseract.image_to_string(img) + "\n"
            except Exception as e:
                print(f"OCR error: {e}")
        
        return text
    
    def _read_image_ocr(self, file_path: str) -> str:
        """Read text from image using OCR"""
        try:
            img = Image.open(file_path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception as e:
            print(f"OCR error: {e}")
            return ""
    
    def _extract_pattern(self, text: str, pattern_name: str) -> Dict[str, Any]:
        """Extract field using regex pattern"""
        if pattern_name not in self.patterns:
            return {'value': '', 'conf': 0.0}
        
        pattern = self.patterns[pattern_name]
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            value = match.group(1) if match.lastindex else match.group(0)
            # Higher confidence for structured patterns like GST, CIN
            conf = 0.9 if pattern_name in ['gst', 'cin'] else 0.8
            return {'value': value.strip(), 'conf': conf}
        
        return {'value': '', 'conf': 0.0}
    
    def _extract_hours(self, text: str) -> Dict[str, Any]:
        """Extract total hours from text"""
        pattern = self.patterns['hours']
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        if matches:
            # Take the largest number found
            hours = max([int(h) for h in matches])
            return {'value': str(hours), 'conf': 0.85}
        
        return {'value': '', 'conf': 0.0}
    
    def _extract_dates(self, text: str) -> Dict[str, Dict[str, Any]]:
        """Extract start and end dates"""
        dates_found = []
        
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = self._normalize_date(match)
                if normalized:
                    dates_found.append(normalized)
        
        result = {}
        
        if len(dates_found) >= 2:
            # Assume first date is start, second is end
            result['start'] = {'value': dates_found[0], 'conf': 0.8}
            result['end'] = {'value': dates_found[1], 'conf': 0.8}
        elif len(dates_found) == 1:
            result['start'] = {'value': dates_found[0], 'conf': 0.75}
            result['end'] = {'value': '', 'conf': 0.0}
        else:
            result['start'] = {'value': '', 'conf': 0.0}
            result['end'] = {'value': '', 'conf': 0.0}
        
        return result
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date to YYYY-MM-DD format"""
        date_formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%Y/%m/%d',
            '%B %d, %Y', '%b %d, %Y', '%B %d %Y', '%b %d %Y'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return ''
    
    def _extract_person_name(self, doc, text: str) -> Dict[str, Any]:
        """Extract student name using NER and context"""
        persons = [ent.text for ent in doc.ents if ent.label_ == 'PERSON']
        
        if not persons:
            return {'value': '', 'conf': 0.0}
        
        # Find person name near anchor phrases
        text_lower = text.lower()
        best_match = None
        best_score = 0.0
        
        for person in persons:
            score = 0.7  # Base score for NER detection
            person_pos = text_lower.find(person.lower())
            
            # Boost if near anchor phrases
            for anchor in self.name_anchors:
                anchor_pos = text_lower.find(anchor)
                if anchor_pos != -1 and abs(person_pos - anchor_pos) < 100:
                    score += 0.2
                    break
            
            if score > best_score:
                best_score = score
                best_match = person
        
        if best_match:
            return {'value': best_match, 'conf': min(best_score, 0.95)}
        
        # Fallback: return first person found
        return {'value': persons[0], 'conf': 0.7}
    
    def _extract_organization(self, doc, text: str) -> Dict[str, Any]:
        """Extract organization name using NER"""
        orgs = [ent.text for ent in doc.ents if ent.label_ == 'ORG']
        
        if not orgs:
            return {'value': '', 'conf': 0.0}
        
        # Prefer longer organization names (more specific)
        orgs_sorted = sorted(orgs, key=len, reverse=True)
        return {'value': orgs_sorted[0], 'conf': 0.8}
    
    def _extract_title(self, text: str, doc) -> Dict[str, Any]:
        """Extract internship title from context"""
        text_lower = text.lower()
        
        # Look for patterns like "internship in/as X" or "position: X"
        patterns = [
            r'internship\s+(?:in|as|for)\s+([A-Z][A-Za-z\s]{3,30})',
            r'position\s*:?\s*([A-Z][A-Za-z\s]{3,30})',
            r'role\s*:?\s*([A-Z][A-Za-z\s]{3,30})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                title = match.group(1).strip()
                # Clean up title
                title = re.sub(r'\s+', ' ', title)
                return {'value': title, 'conf': 0.75}
        
        return {'value': '', 'conf': 0.0}
    
    def _extract_signatory(self, doc, text: str) -> Dict[str, Any]:
        """Extract signatory name"""
        # Look for signatures at end of document
        lines = text.split('\n')
        last_50_lines = '\n'.join(lines[-50:])
        
        if self.nlp:
            doc_end = self.nlp(last_50_lines)
            persons = [ent.text for ent in doc_end.ents if ent.label_ == 'PERSON']
            
            if persons:
                # Return last person (likely signatory)
                return {'value': persons[-1], 'conf': 0.7}
        
        return {'value': '', 'conf': 0.0}
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty result structure"""
        return {
            'name': {'value': '', 'conf': 0.0},
            'apaar_id': {'value': '', 'conf': 0.0},
            'institution_code': {'value': '', 'conf': 0.0},
            'organization': {'value': '', 'conf': 0.0},
            'internship_title': {'value': '', 'conf': 0.0},
            'start_date': {'value': '', 'conf': 0.0},
            'end_date': {'value': '', 'conf': 0.0},
            'hours': {'value': '', 'conf': 0.0},
            'cert_id': {'value': '', 'conf': 0.0},
            'signatory_name': {'value': '', 'conf': 0.0},
            'signatory_email': {'value': '', 'conf': 0.0},
            'gst': {'value': '', 'conf': 0.0},
            'cin': {'value': '', 'conf': 0.0},
        }


# Convenience functions
def extract_from_text(text: str) -> Dict[str, Any]:
    """Extract fields from certificate text"""
    extractor = FieldExtractor()
    return extractor.extract_from_text(text)


def extract_from_file(file_path: str) -> Dict[str, Any]:
    """Extract fields from certificate file"""
    extractor = FieldExtractor()
    return extractor.extract_from_file(file_path)
