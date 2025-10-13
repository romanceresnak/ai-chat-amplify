"""
Smart Template-Based Generator
Updates specific values in existing PowerPoint templates
"""

import boto3
import io
import re
import logging
from typing import Dict, List, Any, Optional
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
try:
    from .minimal_slide_extractor import extract_single_slide_minimal
except ImportError:
    from minimal_slide_extractor import extract_single_slide_minimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3
s3 = boto3.client('s3')

class SmartTemplateGenerator:
    def __init__(self):
        self.documents_bucket = 'scribbe-ai-dev-documents'
        self.template_key = 'PUBLIC IP South Plains (1).pptx'
        self.template_cache = None
    
    def generate_presentation(self, instructions: str) -> bytes:
        """Generate presentation by updating template values"""
        
        # Parse instructions
        slide_info = self._parse_instructions(instructions)
        slide_number = slide_info.get('slide_number')
        
        if not slide_number:
            raise ValueError("Please specify a slide number")
        
        logger.info(f"Generating slide {slide_number}")
        
        # Load template
        if not self.template_cache:
            logger.info("Loading template from S3...")
            response = s3.get_object(Bucket=self.documents_bucket, Key=self.template_key)
            self.template_cache = response['Body'].read()
        
        # Load presentation
        prs = Presentation(io.BytesIO(self.template_cache))
        
        # Get the target slide (0-indexed)
        slide_index = slide_number - 1
        if slide_index >= len(prs.slides):
            raise ValueError(f"Slide {slide_number} not found")
        
        target_slide = prs.slides[slide_index]
        
        # Update values based on slide type
        if slide_number == 23 or slide_number == 26:
            self._update_slide_23(target_slide, slide_info)
        elif slide_number == 24:
            self._update_slide_24(target_slide, slide_info)
        
        # Save the updated presentation to get updated bytes
        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        
        # Extract only the requested slide
        updated_bytes = output.getvalue()
        single_slide_bytes = extract_single_slide_minimal(updated_bytes, slide_number)
        
        return single_slide_bytes
    
    def _parse_instructions(self, instructions: str) -> Dict[str, Any]:
        """Parse slide instructions"""
        
        # Get slide number
        slide_match = re.search(r'(?:slide|Slide)\s*(\d+)', instructions)
        slide_number = int(slide_match.group(1)) if slide_match else None
        
        result = {'slide_number': slide_number}
        
        # Parse based on slide type
        if slide_number in [23, 26]:
            # Parse loan values and yields
            result['new_values'] = self._parse_slide_23_values(instructions)
        elif slide_number == 24:
            # Parse portfolio composition
            result['portfolio'] = self._parse_slide_24_values(instructions)
        
        return result
    
    def _parse_slide_23_values(self, instructions: str) -> Dict[str, Any]:
        """Parse values for Slide 23/26"""
        
        values = {
            'loans': {},
            'yields': {},
            'highlights': []
        }
        
        # Parse loan balances
        # Pattern: $X,XXXM Quarter
        loan_pattern = r'\$?([\d,]+)M?\s+([\dQ]+\'?\d{2})'
        for match in re.finditer(loan_pattern, instructions):
            amount = match.group(1).replace(',', '')
            quarter = match.group(2)
            
            # Normalize quarter format
            if not quarter.startswith(('1Q', '2Q', '3Q', '4Q')):
                continue
                
            values['loans'][quarter] = int(amount)
        
        # Parse yields
        # Pattern: X.XX% in sequence
        yield_section = re.search(r'yield[^:]*:\s*([^,\n]+)', instructions, re.IGNORECASE)
        if yield_section:
            yields = re.findall(r'([\d.]+)%', yield_section.group(1))
            quarters = ['2Q\'19', '3Q\'19', '4Q\'19', '1Q\'20', '2Q\'20']
            for i, y in enumerate(yields[:5]):
                if i < len(quarters):
                    values['yields'][quarters[i]] = float(y)
        
        # Parse highlights
        highlight_keywords = [
            'Total loan increase',
            'Growth from',
            'offset',
            'PPP loans closed',
            'yield of'
        ]
        
        for keyword in highlight_keywords:
            pattern = re.compile(f'([^.]*{keyword}[^.]*\\.)', re.IGNORECASE)
            match = pattern.search(instructions)
            if match:
                values['highlights'].append(match.group(1).strip())
        
        return values
    
    def _parse_slide_24_values(self, instructions: str) -> Dict[str, Any]:
        """Parse values for Slide 24"""
        
        portfolio = {}
        
        # Parse portfolio composition
        comp_match = re.search(r'composition\s*\(([^)]+)\)', instructions)
        if comp_match:
            items = comp_match.group(1).split(',')
            for item in items:
                match = re.match(r'(.+?)\s+(\d+)%', item.strip())
                if match:
                    category = match.group(1).strip()
                    percentage = int(match.group(2))
                    portfolio[category] = percentage
        
        return portfolio
    
    def _update_slide_23(self, slide, slide_info: Dict):
        """Update Slide 23 values"""
        
        new_values = slide_info.get('new_values', {})
        loans = new_values.get('loans', {})
        yields = new_values.get('yields', {})
        highlights = new_values.get('highlights', [])
        
        logger.info(f"Updating with loans: {loans}")
        logger.info(f"Updating with yields: {yields}")
        
        # Map of shape indices to quarters (based on the structure we found)
        loan_shape_map = {
            2: '2Q\'19',  # Shape 2: $1,936
            3: '3Q\'19',  # Shape 3: $1,963
            4: '4Q\'19',  # Shape 4: $2,144
            5: '1Q\'20',  # Shape 5: $2,109
            6: '2Q\'20'   # Shape 6: $2,332
        }
        
        yield_shape_map = {
            7: '2Q\'19',   # Shape 7: 5.90%
            8: '3Q\'19',   # Shape 8: 5.91%
            9: '4Q\'19',   # Shape 9: 5.79%
            10: '1Q\'20',  # Shape 10: 5.76%
            11: '2Q\'20'   # Shape 11: 5.26%
        }
        
        # Update loan values
        for shape_idx, quarter in loan_shape_map.items():
            if quarter in loans and shape_idx < len(slide.shapes):
                shape = slide.shapes[shape_idx]
                if hasattr(shape, 'text_frame') and shape.text_frame:
                    # Update the text
                    shape.text_frame.text = f"${loans[quarter]:,}"
                    # Preserve formatting of first paragraph
                    if shape.text_frame.paragraphs:
                        p = shape.text_frame.paragraphs[0]
                        p.font.bold = True
        
        # Update yield values
        for shape_idx, quarter in yield_shape_map.items():
            if quarter in yields and shape_idx < len(slide.shapes):
                shape = slide.shapes[shape_idx]
                if hasattr(shape, 'text_frame') and shape.text_frame:
                    shape.text_frame.text = f"{yields[quarter]}%"
                    # Preserve formatting
                    if shape.text_frame.paragraphs:
                        p = shape.text_frame.paragraphs[0]
                        p.font.bold = True
        
        # Update highlights if provided
        if highlights:
            highlight_shapes = [21, 22, 23, 24, 25]  # Based on structure analysis
            for i, (shape_idx, highlight) in enumerate(zip(highlight_shapes, highlights)):
                if shape_idx < len(slide.shapes):
                    shape = slide.shapes[shape_idx]
                    if hasattr(shape, 'text_frame') and shape.text_frame:
                        # Clean up the highlight text
                        clean_highlight = highlight.replace('•', '').strip()
                        shape.text_frame.text = clean_highlight
    
    def _update_slide_24(self, slide, slide_info: Dict):
        """Update Slide 24 values"""
        
        portfolio = slide_info.get('portfolio', {})
        
        if not portfolio:
            logger.warning("No portfolio data to update")
            return
        
        # For Slide 24, we'd need to update the chart data
        # This is more complex and requires chart manipulation
        logger.info(f"Would update portfolio with: {portfolio}")
        
        # Update text values that match portfolio categories
        for shape in slide.shapes:
            if hasattr(shape, 'text_frame') and shape.text_frame:
                text = shape.text_frame.text
                
                # Check if text contains any portfolio categories
                for category, percentage in portfolio.items():
                    if category in text:
                        # Update percentage
                        new_text = re.sub(r'\d+%', f'{percentage}%', text)
                        shape.text_frame.text = new_text
                        break


# For backward compatibility
GenericPresentationGenerator = SmartTemplateGenerator