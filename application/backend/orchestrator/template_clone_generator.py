"""
Template Clone PowerPoint Generator

This module creates presentations by copying an existing template and modifying only the text content,
preserving all visual elements, formatting, and layout exactly as in the original.
"""

import os
import copy
import re
import shutil
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# XML namespaces for PowerPoint
NAMESPACES = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'
}

class TemplateCloneGenerator:
    """
    Generates PowerPoint presentations by cloning a template and replacing only text content.
    Works at the XML level to ensure perfect preservation of formatting.
    """
    
    def __init__(self, template_path: str):
        """
        Initialize with a template PowerPoint file.
        
        Args:
            template_path: Path to the reference PowerPoint template
        """
        self.template_path = Path(template_path)
        self.temp_dir = Path("temp_pptx_work")
        
    def generate_presentation(self, content_map: Dict[str, Dict], output_path: str):
        """
        Generate a presentation by cloning the template and replacing content.
        
        Args:
            content_map: Dictionary mapping slide numbers to their new content
            output_path: Path where the generated presentation will be saved
        """
        try:
            # Create temporary working directory
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(exist_ok=True)
            
            # Extract template
            with zipfile.ZipFile(self.template_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            # Process each slide in content_map
            for slide_num, content in content_map.items():
                self._update_slide_content(slide_num, content)
            
            # Repackage the PowerPoint
            self._create_pptx(output_path)
            
            # Cleanup
            shutil.rmtree(self.temp_dir)
            
            logger.info(f"Presentation generated successfully: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating presentation: {e}")
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
            raise
    
    def _update_slide_content(self, slide_num: str, content: Dict):
        """Update content in a specific slide while preserving all formatting."""
        slide_path = self.temp_dir / 'ppt' / 'slides' / f'slide{slide_num}.xml'
        
        if not slide_path.exists():
            logger.warning(f"Slide {slide_num} not found")
            return
        
        # Parse slide XML
        tree = ET.parse(slide_path)
        root = tree.getroot()
        
        # Update text elements
        if 'texts' in content:
            self._update_text_elements(root, content['texts'])
        
        # Update chart data if present
        if 'chart_data' in content:
            self._update_chart_data(root, slide_num, content['chart_data'])
        
        # Save modified XML
        tree.write(slide_path, encoding='UTF-8', xml_declaration=True)
    
    def _update_text_elements(self, root: ET.Element, texts: List[Dict]):
        """Update text elements in the slide while preserving formatting."""
        # Find all text runs in the slide
        text_runs = root.findall('.//a:r', NAMESPACES)
        
        for text_info in texts:
            target_text = text_info.get('find', '')
            new_text = text_info.get('replace', '')
            partial_match = text_info.get('partial', False)
            
            for run in text_runs:
                text_elem = run.find('a:t', NAMESPACES)
                if text_elem is not None:
                    current_text = text_elem.text or ''
                    
                    if partial_match:
                        # Replace partial matches
                        if target_text in current_text:
                            text_elem.text = current_text.replace(target_text, new_text)
                    else:
                        # Replace exact matches
                        if current_text.strip() == target_text.strip():
                            text_elem.text = new_text
    
    def _update_chart_data(self, root: ET.Element, slide_num: str, chart_data: Dict):
        """Update chart data while preserving chart formatting."""
        # Find chart references in the slide
        chart_refs = root.findall('.//p:graphicFrame//a:graphic//a:graphicData//c:chart', 
                                  {'p': NAMESPACES['p'], 'a': NAMESPACES['a'], 
                                   'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'})
        
        if not chart_refs:
            logger.warning(f"No charts found in slide {slide_num}")
            return
        
        # For each chart, update its data
        for idx, chart_ref in enumerate(chart_refs):
            # Get chart relationship ID
            rel_id = chart_ref.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
            if rel_id:
                self._update_chart_xml(slide_num, rel_id, chart_data)
    
    def _update_chart_xml(self, slide_num: str, rel_id: str, chart_data: Dict):
        """Update the chart XML file with new data."""
        # Find the chart file from relationships
        rels_path = self.temp_dir / 'ppt' / 'slides' / '_rels' / f'slide{slide_num}.xml.rels'
        
        if not rels_path.exists():
            return
        
        rels_tree = ET.parse(rels_path)
        rels_root = rels_tree.getroot()
        
        # Find the chart file path
        for relationship in rels_root.findall('.//Relationship', 
                                            {'': 'http://schemas.openxmlformats.org/package/2006/relationships'}):
            if relationship.get('Id') == rel_id:
                chart_path = relationship.get('Target')
                if chart_path.startswith('../'):
                    chart_path = chart_path[3:]
                
                full_chart_path = self.temp_dir / 'ppt' / chart_path
                if full_chart_path.exists():
                    self._modify_chart_values(full_chart_path, chart_data)
                break
    
    def _modify_chart_values(self, chart_path: Path, chart_data: Dict):
        """Modify chart values in the chart XML."""
        tree = ET.parse(chart_path)
        root = tree.getroot()
        
        chart_ns = {'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'}
        
        # Update categories
        if 'categories' in chart_data:
            cat_elements = root.findall('.//c:cat//c:strRef//c:strCache//c:pt', chart_ns)
            for idx, cat_elem in enumerate(cat_elements):
                if idx < len(chart_data['categories']):
                    v_elem = cat_elem.find('c:v', chart_ns)
                    if v_elem is not None:
                        v_elem.text = chart_data['categories'][idx]
        
        # Update series values
        if 'series' in chart_data:
            for series_idx, series_data in enumerate(chart_data['series']):
                # Find the series values
                series_xpath = f'.//c:ser[{series_idx + 1}]//c:val//c:numCache//c:pt'
                val_elements = root.findall(series_xpath, chart_ns)
                
                values = series_data.get('values', [])
                for idx, val_elem in enumerate(val_elements):
                    if idx < len(values):
                        v_elem = val_elem.find('c:v', chart_ns)
                        if v_elem is not None:
                            v_elem.text = str(values[idx])
        
        # Save modified chart
        tree.write(chart_path, encoding='UTF-8', xml_declaration=True)
    
    def _create_pptx(self, output_path: str):
        """Create PowerPoint file from the modified XML files."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(self.temp_dir))
                    zipf.write(file_path, arcname)

def create_loan_portfolio_slide(generator: TemplateCloneGenerator, output_path: str):
    """Create a loan portfolio slide using the template."""
    content_map = {
        '26': {  # Slide 26 in the reference is loan portfolio
            'texts': [
                {'find': 'Loan Portfolio', 'replace': 'Loan Portfolio'},
                {'find': '2Q20 Highlights', 'replace': '2Q\'20 Highlights'},
                {'find': '$249', 'replace': '$249'},
                {'find': '$189', 'replace': '$189'},
                {'find': '$167', 'replace': '$167'},
                {'find': '$141', 'replace': '$141'},
                {'find': '$137', 'replace': '$137'}
            ],
            'chart_data': {
                'categories': ['2Q19', '3Q19', '4Q19', '1Q20', '2Q20'],
                'series': [
                    {
                        'name': 'Total Loans',
                        'values': [137, 141, 167, 189, 249]
                    }
                ]
            }
        }
    }
    
    return generator.generate_presentation(content_map, output_path)

def create_noninterest_income_slide(generator: TemplateCloneGenerator, output_path: str):
    """Create a noninterest income slide using the template."""
    content_map = {
        '26': {  # Using same slide number, but would be different in real scenario
            'texts': [
                {'find': 'Loan Portfolio', 'replace': 'Noninterest Income'},
                {'find': 'Total Loans Held for Investment ($ in Millions)', 
                 'replace': '$ In Millions'},
                {'find': '2Q20 Highlights', 'replace': '2Q\'20 Highlights'},
                # Update the highlights text
                {'find': 'Noninterest income is $24.9 million', 'replace': 'Noninterest income is $24.9 million, compared to $18.9 million in 1Q\'20', 'partial': True}
            ],
            'chart_data': {
                'categories': ['2Q19', '3Q19', '4Q19', '1Q20', '2Q20'],
                'series': [
                    {
                        'name': 'Noninterest Income',
                        'values': [13.7, 14.1, 16.7, 18.9, 24.9]
                    },
                    {
                        'name': '% of Revenue',
                        'values': [36, 35, 37, 38, 45]
                    }
                ]
            }
        }
    }
    
    return generator.generate_presentation(content_map, output_path)

# Example usage
if __name__ == "__main__":
    # Initialize generator with template
    template_path = "scribbe-ai-dev-documents/PUBLIC IP South Plains (1).pptx"
    generator = TemplateCloneGenerator(template_path)
    
    # Generate loan portfolio slide
    create_loan_portfolio_slide(generator, "loan_portfolio_from_template.pptx")
    
    # Generate noninterest income slide
    create_noninterest_income_slide(generator, "noninterest_income_from_template.pptx")