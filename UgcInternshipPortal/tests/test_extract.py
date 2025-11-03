"""
Unit tests for certificate field extraction
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from extractor import extract_from_text, extract_from_file


def test_extract_from_sample_text():
    """Test extraction from sample certificate text"""
    
    # Read sample certificate (adjust path for test directory)
    sample_path = '../uploads/samples/sample_cert_text.txt'
    
    if not os.path.exists(sample_path):
        print(f"Sample file not found: {sample_path}")
        print("Creating sample file for testing...")
        return
    
    with open(sample_path, 'r') as f:
        text = f.read()
    
    # Extract fields
    fields = extract_from_text(text)
    
    print("=" * 60)
    print("TEST: Extract from Sample Certificate Text")
    print("=" * 60)
    
    for field_name, field_data in fields.items():
        value = field_data.get('value', '')
        conf = field_data.get('conf', 0.0)
        
        if value:
            print(f"\n{field_name}:")
            print(f"  Value: {value}")
            print(f"  Confidence: {conf:.2f} ({conf*100:.0f}%)")
            
            # Validate expected values
            if field_name == 'name' and 'Amit Kumar' in value:
                print("  ✓ PASS: Name correctly extracted")
            elif field_name == 'apaar_id' and 'APAAR-2024-MH-123456' in value:
                print("  ✓ PASS: APAAR ID correctly extracted")
            elif field_name == 'organization' and 'Tech Innovations' in value:
                print("  ✓ PASS: Organization correctly extracted")
            elif field_name == 'hours' and '320' in value:
                print("  ✓ PASS: Hours correctly extracted")
            elif field_name == 'start_date' and '2024-06-01' in value:
                print("  ✓ PASS: Start date correctly extracted")
            elif field_name == 'cert_id' and 'CERT-TI-2024-089' in value:
                print("  ✓ PASS: Certificate ID correctly extracted")
            elif field_name == 'gst' and '27AABCT1234E1Z5' in value:
                print("  ✓ PASS: GST correctly extracted")
    
    print("\n" + "=" * 60)
    print("Extraction test completed")
    print("=" * 60)


def test_extract_custom_certificate():
    """Test extraction with custom certificate text"""
    
    custom_text = """
    INTERNSHIP CERTIFICATE
    
    This certifies that Priya Sharma has completed an internship
    at DataScience Solutions from January 15, 2024 to March 30, 2024.
    
    Total working hours: 240 hrs
    Position: Data Analyst Intern
    
    Certificate Number: CERT-DS-2024-045
    
    Authorized by:
    Dr. Suresh Patel
    director@datasciencesolutions.com
    """
    
    fields = extract_from_text(custom_text)
    
    print("\n" + "=" * 60)
    print("TEST: Extract from Custom Certificate")
    print("=" * 60)
    
    for field_name, field_data in fields.items():
        value = field_data.get('value', '')
        conf = field_data.get('conf', 0.0)
        
        if value:
            print(f"\n{field_name}: {value} (conf: {conf:.2f})")
    
    print("\n" + "=" * 60)


def test_extract_from_file():
    """Test extraction from file"""
    
    sample_path = '../uploads/samples/sample_cert_text.txt'
    
    if not os.path.exists(sample_path):
        print(f"Sample file not found: {sample_path}")
        return
    
    # Extract from file
    fields = extract_from_file(sample_path)
    
    print("\n" + "=" * 60)
    print("TEST: Extract from File")
    print("=" * 60)
    
    mandatory_fields = ['name', 'start_date', 'end_date']
    for field in mandatory_fields:
        if field in fields and fields[field]['value']:
            print(f"✓ {field}: {fields[field]['value']} (conf: {fields[field]['conf']:.2f})")
        else:
            print(f"✗ {field}: NOT FOUND")
    
    print("=" * 60)


if __name__ == '__main__':
    print("\n" + "=" * 70)
    print(" Certificate Field Extraction Tests")
    print("=" * 70)
    
    test_extract_from_sample_text()
    test_extract_custom_certificate()
    test_extract_from_file()
    
    print("\n✓ All tests completed!\n")
