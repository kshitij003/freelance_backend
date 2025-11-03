"""
CEESCM - Certificate Experience Education Skill Credit Matching
Tokenization module for internship descriptions
"""

import re
from typing import List, Set
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None


class CEESCMTokenizer:
    """Tokenize and normalize internship descriptions"""
    
    def __init__(self):
        self.nlp = nlp
        
        # Stop words to remove
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'been',
            'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
        
        # Technology and skill keywords (for boosting)
        self.tech_keywords = {
            'python', 'java', 'javascript', 'react', 'node', 'sql', 'database',
            'machine learning', 'ai', 'data science', 'web development', 'frontend',
            'backend', 'fullstack', 'mobile', 'android', 'ios', 'cloud', 'aws',
            'azure', 'gcp', 'docker', 'kubernetes', 'api', 'rest', 'graphql'
        }
    
    def tokenize(self, text: str) -> List[str]:
        """
        Tokenize and normalize text to CEESCM tokens
        
        Args:
            text: Input text (internship description, logs, etc.)
            
        Returns:
            List of normalized tokens
        """
        if not text:
            return []
        
        # Normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)  # Remove punctuation
        text = re.sub(r'\s+', ' ', text).strip()  # Normalize whitespace
        
        # Tokenize
        if self.nlp:
            doc = self.nlp(text)
            tokens = [token.lemma_ for token in doc if not token.is_stop and len(token.text) > 2]
        else:
            # Simple tokenization without spaCy
            words = text.split()
            tokens = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tokens = []
        for token in tokens:
            if token not in seen:
                seen.add(token)
                unique_tokens.append(token)
        
        return unique_tokens
    
    def extract_key_terms(self, text: str) -> List[str]:
        """
        Extract key technical terms and skills from text
        
        Args:
            text: Input text
            
        Returns:
            List of key terms
        """
        tokens = self.tokenize(text)
        
        # Filter for meaningful terms
        key_terms = []
        text_lower = text.lower()
        
        # Add tech keywords found in text
        for keyword in self.tech_keywords:
            if keyword in text_lower:
                key_terms.append(keyword.replace(' ', '_'))
        
        # Add noun chunks if spaCy available
        if self.nlp:
            doc = self.nlp(text)
            for chunk in doc.noun_chunks:
                if len(chunk.text.split()) <= 3:  # Max 3 words
                    normalized = chunk.text.lower().replace(' ', '_')
                    if normalized not in key_terms:
                        key_terms.append(normalized)
        
        return key_terms[:20]  # Limit to top 20 terms
    
    def get_token_vector(self, text: str) -> Set[str]:
        """Get token set for fast comparison"""
        return set(self.tokenize(text))


# Convenience function
def tokenize(text: str) -> List[str]:
    """Tokenize text to CEESCM tokens"""
    tokenizer = CEESCMTokenizer()
    return tokenizer.tokenize(text)


def get_sample_ceescm_tokens(internship_data: dict) -> List[str]:
    """
    Generate sample CEESCM tokens from internship data
    
    Args:
        internship_data: Dictionary with organization, title, etc.
        
    Returns:
        List of CEESCM tokens
    """
    tokenizer = CEESCMTokenizer()
    
    # Combine relevant fields
    text = ' '.join([
        internship_data.get('organization', ''),
        internship_data.get('internship_title', ''),
        internship_data.get('logs', ''),
    ])
    
    return tokenizer.tokenize(text)
