"""
Word Mover's Distance (WMD) Similarity Matching Module
Uses spaCy embeddings as fallback (no GoogleNews dependency)
"""

import numpy as np
from typing import List, Dict, Tuple
import spacy

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None


class WMDMatcher:
    """Word Mover's Distance based similarity matching"""
    
    def __init__(self):
        self.nlp = nlp
        
        # Reference curriculum database (sample data)
        self.curriculum_db = {
            'CS301': {
                'title': 'Web Development Fundamentals',
                'keywords': ['html', 'css', 'javascript', 'web', 'frontend', 'react', 'responsive'],
                'description': 'Introduction to web development including HTML, CSS, JavaScript, and modern frameworks like React'
            },
            'CS302': {
                'title': 'Database Management Systems',
                'keywords': ['database', 'sql', 'mysql', 'postgresql', 'queries', 'data', 'tables'],
                'description': 'Relational database concepts, SQL queries, database design and normalization'
            },
            'CS303': {
                'title': 'Machine Learning Basics',
                'keywords': ['machine learning', 'python', 'ai', 'models', 'data science', 'algorithms'],
                'description': 'Introduction to machine learning algorithms, data preprocessing, and model training'
            },
            'CS304': {
                'title': 'Mobile App Development',
                'keywords': ['mobile', 'android', 'ios', 'app', 'react native', 'flutter'],
                'description': 'Mobile application development for Android and iOS platforms'
            },
            'CS305': {
                'title': 'Cloud Computing',
                'keywords': ['cloud', 'aws', 'azure', 'gcp', 'devops', 'docker', 'kubernetes'],
                'description': 'Cloud platforms, containerization, and DevOps practices'
            },
            'CS306': {
                'title': 'Backend Development',
                'keywords': ['backend', 'api', 'rest', 'node', 'python', 'flask', 'django', 'server'],
                'description': 'Server-side development, API design, and backend frameworks'
            },
        }
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not self.nlp:
            # Fallback: simple word overlap
            return self._simple_similarity(text1, text2)
        
        # Use spaCy similarity
        doc1 = self.nlp(text1)
        doc2 = self.nlp(text2)
        
        # spaCy similarity ranges 0-1
        similarity = doc1.similarity(doc2)
        
        # Boost for exact keyword matches
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        overlap = len(words1 & words2) / max(len(words1 | words2), 1)
        
        # Weighted combination
        final_score = 0.7 * similarity + 0.3 * overlap
        
        return min(final_score, 1.0)
    
    def _simple_similarity(self, text1: str, text2: str) -> float:
        """Fallback similarity using word overlap"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def find_matches(self, internship_tokens: List[str], threshold: float = 0.3) -> List[Dict]:
        """
        Find matching curriculum courses for internship
        
        Args:
            internship_tokens: List of CEESCM tokens from internship
            threshold: Minimum similarity threshold
            
        Returns:
            List of matches with scores
        """
        internship_text = ' '.join(internship_tokens)
        matches = []
        
        for course_id, course_data in self.curriculum_db.items():
            # Combine course keywords and description
            course_text = ' '.join(course_data['keywords']) + ' ' + course_data['description']
            
            # Calculate similarity
            similarity = self.calculate_similarity(internship_text, course_text)
            
            if similarity >= threshold:
                matches.append({
                    'course_id': course_id,
                    'course_title': course_data['title'],
                    'similarity': round(similarity, 3),
                    'keywords_matched': self._get_matched_keywords(internship_text, course_data['keywords'])
                })
        
        # Sort by similarity descending
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return matches
    
    def _get_matched_keywords(self, internship_text: str, course_keywords: List[str]) -> List[str]:
        """Get keywords that appear in both texts"""
        internship_lower = internship_text.lower()
        matched = []
        
        for keyword in course_keywords:
            if keyword in internship_lower:
                matched.append(keyword)
        
        return matched
    
    def compute_composite_score(self, matches: List[Dict]) -> float:
        """
        Compute composite WMD score from matches
        
        Args:
            matches: List of course matches
            
        Returns:
            Composite score (0.0 to 1.0)
        """
        if not matches:
            return 0.0
        
        # Take average of top 3 matches
        top_matches = matches[:3]
        scores = [m['similarity'] for m in top_matches]
        
        return round(sum(scores) / len(scores), 3)
    
    def classify_match(self, composite_score: float) -> str:
        """
        Classify match quality
        
        Args:
            composite_score: WMD composite score
            
        Returns:
            Classification: 'Equivalent', 'Partially Equivalent', 'Not Equivalent'
        """
        if composite_score >= 0.7:
            return 'Equivalent'
        elif composite_score >= 0.4:
            return 'Partially Equivalent'
        else:
            return 'Not Equivalent'
    
    def add_custom_keywords(self, course_id: str, keywords: List[str]):
        """Add custom keywords to a course (mentor override)"""
        if course_id in self.curriculum_db:
            existing = set(self.curriculum_db[course_id]['keywords'])
            existing.update(keywords)
            self.curriculum_db[course_id]['keywords'] = list(existing)


# Convenience function
def match_internship(internship_tokens: List[str]) -> Tuple[List[Dict], float, str]:
    """
    Match internship against curriculum
    
    Returns:
        (matches, composite_score, decision)
    """
    matcher = WMDMatcher()
    matches = matcher.find_matches(internship_tokens)
    composite = matcher.compute_composite_score(matches)
    decision = matcher.classify_match(composite)
    
    return matches, composite, decision
