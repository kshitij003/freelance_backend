"""
PDF Report Generator for Internship Credits
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from datetime import datetime


def generate_pdf_report(record, output_path):
    """
    Generate PDF report for internship credit evaluation
    
    Args:
        record: Internship record dictionary
        output_path: Path to save PDF
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1a73e8'),
        spaceAfter=30,
        alignment=1  # Center
    )
    
    story.append(Paragraph("UGC Internship Credit Evaluation Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Internship ID and timestamp
    story.append(Paragraph(f"<b>Report ID:</b> {record.get('internship_id', 'N/A')}", styles['Normal']))
    story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 0.3*inch))
    
    # Student Information
    story.append(Paragraph("<b>Student Information</b>", styles['Heading2']))
    form_data = record.get('form_data', {})
    
    student_data = [
        ['Name:', form_data.get('name', 'N/A')],
        ['APAAR ID:', form_data.get('apaar_id', 'N/A')],
        ['Institution Code:', form_data.get('institution_code', 'N/A')],
    ]
    
    student_table = Table(student_data, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(student_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Internship Details
    story.append(Paragraph("<b>Internship Details</b>", styles['Heading2']))
    
    internship_data = [
        ['Organization:', form_data.get('organization', 'N/A')],
        ['Title:', form_data.get('internship_title', 'N/A')],
        ['Start Date:', form_data.get('start_date', 'N/A')],
        ['End Date:', form_data.get('end_date', 'N/A')],
        ['Total Hours:', form_data.get('hours', 'N/A')],
        ['Level:', form_data.get('level', 'N/A')],
    ]
    
    internship_table = Table(internship_data, colWidths=[2*inch, 4*inch])
    internship_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    
    story.append(internship_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Credit Evaluation
    story.append(Paragraph("<b>Credit Evaluation</b>", styles['Heading2']))
    
    decision = record.get('decision', 'N/A')
    decision_color = colors.green if decision == 'Equivalent' else (colors.orange if decision == 'Partially Equivalent' else colors.red)
    
    eval_data = [
        ['Decision:', decision],
        ['WMD Composite Score:', str(record.get('wmd_composite', 'N/A'))],
        ['Credits Awarded:', str(record.get('credits', 'N/A'))],
        ['Eligible:', 'Yes' if record.get('eligible', False) else 'No'],
    ]
    
    eval_table = Table(eval_data, colWidths=[2*inch, 4*inch])
    eval_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('TEXTCOLOR', (1, 0), (1, 0), decision_color),
    ]))
    
    story.append(eval_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Matched Courses
    matches = record.get('wmd_matches', [])
    if matches:
        story.append(Paragraph("<b>Matched Curriculum Courses</b>", styles['Heading2']))
        
        match_data = [['Course ID', 'Course Title', 'Similarity']]
        for match in matches[:5]:  # Top 5 matches
            match_data.append([
                match['course_id'],
                match['course_title'],
                f"{match['similarity']:.2f}"
            ])
        
        match_table = Table(match_data, colWidths=[1.5*inch, 3*inch, 1.5*inch])
        match_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(match_table)
        story.append(Spacer(1, 0.3*inch))
    
    # ABC Status
    abc_token = record.get('abc_token')
    if abc_token:
        story.append(Paragraph("<b>ABC Registration</b>", styles['Heading2']))
        story.append(Paragraph(f"ABC Token: {abc_token}", styles['Normal']))
        story.append(Paragraph(f"Status: {record.get('abc_status', 'N/A')}", styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
    
    # Footer
    story.append(Spacer(1, 0.5*inch))
    story.append(Paragraph(
        "<i>This is a computer-generated report from the UGC Internship Credit Portal (Demo)</i>",
        styles['Normal']
    ))
    
    # Build PDF
    doc.build(story)
