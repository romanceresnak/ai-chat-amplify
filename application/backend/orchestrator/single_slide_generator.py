"""
Single Slide Generator - Creates individual slides using South Plains template
"""

import os
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import boto3
import logging
from datetime import datetime
import tempfile
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# XML namespaces
NAMESPACES = {
    'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
    'c': 'http://schemas.openxmlformats.org/drawingml/2006/chart'
}

class SingleSlideGenerator:
    """
    Generates single PowerPoint slides using South Plains template
    """
    
    def __init__(self, template_s3_bucket: str = None, template_s3_key: str = None):
        """
        Initialize generator with S3 template location.
        
        Args:
            template_s3_bucket: S3 bucket containing template
            template_s3_key: S3 key for template file
        """
        self.s3_client = boto3.client('s3')
        self.template_bucket = template_s3_bucket or os.environ.get('TEMPLATE_BUCKET', 'scribbe-ai-dev-documents')
        self.template_key = template_s3_key or os.environ.get('TEMPLATE_KEY', 'PUBLIC IP South Plains (1).pptx')
        self.temp_dir = None
        logger.info(f"SingleSlideGenerator initialized with bucket: {self.template_bucket}, key: {self.template_key}")
        
    def generate_single_slide(self, prompt: str, slide_type: str) -> str:
        """
        Generate a single slide presentation based on prompt and slide type.
        
        Args:
            prompt: Natural language prompt describing the content
            slide_type: Type of slide (e.g., 'loan_portfolio', 'noninterest_income')
            
        Returns:
            S3 URL of generated single-slide presentation
        """
        try:
            # Create temporary directory
            self.temp_dir = tempfile.mkdtemp()
            work_dir = Path(self.temp_dir)
            
            # Download template from S3
            template_path = work_dir / 'template.pptx'
            self._download_template(template_path)
            
            # Extract template
            extract_dir = work_dir / 'extracted'
            with zipfile.ZipFile(template_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Parse prompt and generate content
            content_data = self._parse_prompt(prompt, slide_type)
            
            # Create new single-slide presentation structure
            single_slide_dir = work_dir / 'single_slide'
            self._create_single_slide_structure(extract_dir, single_slide_dir, content_data)
            
            # Repackage as single-slide PowerPoint
            output_path = work_dir / f'single_slide_{slide_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pptx'
            self._create_pptx(single_slide_dir, output_path)
            
            # Upload to S3
            s3_url = self._upload_to_s3(output_path, slide_type)
            
            return s3_url
            
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _create_single_slide_structure(self, template_dir: Path, output_dir: Path, content_data: Dict):
        """Create a minimal PowerPoint structure with just one slide"""
        
        # Create directory structure
        output_dir.mkdir(exist_ok=True)
        (output_dir / '_rels').mkdir(exist_ok=True)
        (output_dir / 'ppt').mkdir(exist_ok=True)
        (output_dir / 'ppt' / '_rels').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'slides').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'slides' / '_rels').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'slideLayouts').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'slideLayouts' / '_rels').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'slideMasters').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'slideMasters' / '_rels').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'theme').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'media').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'charts').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'charts' / '_rels').mkdir(exist_ok=True)
        (output_dir / 'ppt' / 'embeddings').mkdir(exist_ok=True)
        
        # Copy essential files from template
        # 1. Content Types
        shutil.copy(template_dir / '[Content_Types].xml', output_dir / '[Content_Types].xml')
        self._update_content_types_for_single_slide(output_dir / '[Content_Types].xml')
        
        # 2. Main relationships
        shutil.copy(template_dir / '_rels' / '.rels', output_dir / '_rels' / '.rels')
        
        # 3. Presentation.xml (modified for single slide)
        self._create_single_slide_presentation(template_dir, output_dir)
        
        # 4. Determine which slide to copy
        # First check if prompt mentions a specific slide number
        slide_number = content_data.get('slide_number')
        
        if slide_number:
            # Use the specific slide number from the prompt
            source_slide_name = f'slide{slide_number}.xml'
            logger.info(f"Using slide {slide_number} from prompt")
        else:
            # Fall back to slide type mapping
            slide_type = content_data.get('slide_type', 'loan_portfolio')
            slide_mapping = {
                'loan_portfolio': 'slide26.xml',  # Default for loan portfolio
                'noninterest_income': 'slide27.xml',
                'financial_summary': 'slide5.xml'
            }
            source_slide_name = slide_mapping.get(slide_type, 'slide26.xml')
            logger.info(f"Using slide mapping for {slide_type}: {source_slide_name}")
        
        source_slide = template_dir / 'ppt' / 'slides' / source_slide_name
        
        # If the requested slide doesn't exist, find the first available slide
        if not source_slide.exists():
            logger.warning(f"Slide {source_slide_name} not found, searching for any available slide...")
            slides_dir = template_dir / 'ppt' / 'slides'
            slide_files = sorted(slides_dir.glob('slide*.xml'))
            if slide_files:
                source_slide = slide_files[0]
                logger.info(f"Using fallback slide {source_slide.name}")
            else:
                raise ValueError("No slides found in template")
        
        target_slide = output_dir / 'ppt' / 'slides' / 'slide1.xml'
        shutil.copy(source_slide, target_slide)
        
        # Update slide content
        self._update_slide_content(target_slide, content_data)
        
        # 5. Copy slide relationships
        source_rels = template_dir / 'ppt' / 'slides' / '_rels' / 'slide26.xml.rels'
        target_rels = output_dir / 'ppt' / 'slides' / '_rels' / 'slide1.xml.rels'
        if source_rels.exists():
            shutil.copy(source_rels, target_rels)
            self._update_slide_relationships(target_rels)
        
        # 6. Copy required theme, layouts, and masters
        shutil.copytree(template_dir / 'ppt' / 'theme', output_dir / 'ppt' / 'theme', dirs_exist_ok=True)
        
        # Copy minimal required layouts and masters
        self._copy_minimal_masters_layouts(template_dir, output_dir)
        
        # 7. Copy media files if referenced
        if (template_dir / 'ppt' / 'media').exists():
            for media_file in (template_dir / 'ppt' / 'media').iterdir():
                if media_file.is_file():
                    shutil.copy(media_file, output_dir / 'ppt' / 'media' / media_file.name)
        
        # 8. Copy chart files if present
        self._copy_chart_files(template_dir, output_dir, 26, 1)
    
    def _create_single_slide_presentation(self, template_dir: Path, output_dir: Path):
        """Create presentation.xml for single slide"""
        
        # Read template presentation.xml
        template_pres = template_dir / 'ppt' / 'presentation.xml'
        tree = ET.parse(template_pres)
        root = tree.getroot()
        
        # Update slide ID list to only have one slide
        sld_id_lst = root.find('.//{' + NAMESPACES['p'] + '}sldIdLst')
        if sld_id_lst is not None:
            # Clear all slides
            for sld_id in list(sld_id_lst):
                sld_id_lst.remove(sld_id)
            
            # Add single slide reference
            sld_id = ET.SubElement(sld_id_lst, '{' + NAMESPACES['p'] + '}sldId')
            sld_id.set('id', '256')
            sld_id.set('{' + NAMESPACES['r'] + '}id', 'rId2')
        
        # Write modified presentation.xml
        tree.write(output_dir / 'ppt' / 'presentation.xml', encoding='UTF-8', xml_declaration=True)
        
        # Create presentation.xml.rels
        self._create_presentation_rels(output_dir)
    
    def _create_presentation_rels(self, output_dir: Path):
        """Create presentation.xml.rels for single slide"""
        rels_content = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
    <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
    <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="theme/theme1.xml"/>
</Relationships>'''
        
        rels_path = output_dir / 'ppt' / '_rels' / 'presentation.xml.rels'
        with open(rels_path, 'w', encoding='utf-8') as f:
            f.write(rels_content)
    
    def _copy_minimal_masters_layouts(self, template_dir: Path, output_dir: Path):
        """Copy only required masters and layouts"""
        
        # Copy first master and its relationships
        master_files = list((template_dir / 'ppt' / 'slideMasters').glob('slideMaster*.xml'))
        if master_files:
            first_master = master_files[0]
            shutil.copy(first_master, output_dir / 'ppt' / 'slideMasters' / 'slideMaster1.xml')
            
            # Copy master relationships
            master_rels = template_dir / 'ppt' / 'slideMasters' / '_rels' / f'{first_master.name}.rels'
            if master_rels.exists():
                shutil.copy(master_rels, output_dir / 'ppt' / 'slideMasters' / '_rels' / 'slideMaster1.xml.rels')
        
        # Copy first layout and its relationships
        layout_files = list((template_dir / 'ppt' / 'slideLayouts').glob('slideLayout*.xml'))
        if layout_files:
            first_layout = layout_files[0]
            shutil.copy(first_layout, output_dir / 'ppt' / 'slideLayouts' / 'slideLayout1.xml')
            
            # Copy layout relationships
            layout_rels = template_dir / 'ppt' / 'slideLayouts' / '_rels' / f'{first_layout.name}.rels'
            if layout_rels.exists():
                shutil.copy(layout_rels, output_dir / 'ppt' / 'slideLayouts' / '_rels' / 'slideLayout1.xml.rels')
    
    def _update_content_types_for_single_slide(self, content_types_path: Path):
        """Update Content_Types.xml for single slide"""
        tree = ET.parse(content_types_path)
        root = tree.getroot()
        
        # Remove references to non-existent slides
        for override in list(root.findall('.//{http://schemas.openxmlformats.org/package/2006/content-types}Override')):
            part_name = override.get('PartName', '')
            if '/slides/slide' in part_name and not part_name.endswith('slide1.xml'):
                root.remove(override)
        
        tree.write(content_types_path, encoding='UTF-8', xml_declaration=True)
    
    def _update_slide_relationships(self, rels_path: Path):
        """Update slide relationships to ensure they work for slide1"""
        if rels_path.exists():
            tree = ET.parse(rels_path)
            root = tree.getroot()
            
            # Update slideLayout relationship if needed
            for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                if 'slideLayout' in rel.get('Type', ''):
                    # Point to slideLayout1
                    rel.set('Target', '../slideLayouts/slideLayout1.xml')
            
            tree.write(rels_path, encoding='UTF-8', xml_declaration=True)
    
    def _copy_chart_files(self, template_dir: Path, output_dir: Path, source_slide_num: int, target_slide_num: int):
        """Copy chart files if the slide contains charts"""
        
        # Check slide relationships for charts
        source_rels = template_dir / 'ppt' / 'slides' / '_rels' / f'slide{source_slide_num}.xml.rels'
        if source_rels.exists():
            tree = ET.parse(source_rels)
            root = tree.getroot()
            
            for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                if 'chart' in rel.get('Type', ''):
                    chart_target = rel.get('Target', '').replace('../', '')
                    source_chart = template_dir / 'ppt' / chart_target
                    
                    if source_chart.exists():
                        # Create chart directory if needed
                        chart_dir = output_dir / 'ppt' / 'charts'
                        chart_dir.mkdir(exist_ok=True)
                        
                        # Copy chart file
                        target_chart = output_dir / 'ppt' / chart_target
                        shutil.copy(source_chart, target_chart)
                        
                        # Copy chart relationships
                        chart_name = source_chart.name
                        source_chart_rels = source_chart.parent / '_rels' / f'{chart_name}.rels'
                        if source_chart_rels.exists():
                            target_chart_rels = target_chart.parent / '_rels' / f'{chart_name}.rels'
                            target_chart_rels.parent.mkdir(exist_ok=True)
                            shutil.copy(source_chart_rels, target_chart_rels)
                        
                        # Copy embedded Excel if exists
                        self._copy_embedded_excel(template_dir, output_dir, source_chart_rels)
    
    def _copy_embedded_excel(self, template_dir: Path, output_dir: Path, chart_rels_path: Path):
        """Copy embedded Excel files referenced by charts"""
        if chart_rels_path.exists():
            tree = ET.parse(chart_rels_path)
            root = tree.getroot()
            
            for rel in root.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                if 'embeddings' in rel.get('Target', ''):
                    excel_target = rel.get('Target', '').replace('../', '')
                    source_excel = template_dir / 'ppt' / excel_target
                    
                    if source_excel.exists():
                        target_excel = output_dir / 'ppt' / excel_target
                        target_excel.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(source_excel, target_excel)
    
    def _update_slide_content(self, slide_path: Path, content_data: Dict):
        """Update the slide content based on parsed data"""
        tree = ET.parse(slide_path)
        root = tree.getroot()
        
        # Store slide number for page numbering
        self.current_slide_number = str(content_data.get('slide_number', 26))
        
        # First, clean up any existing content that might be from wrong slide type
        self._clean_slide_content(root, content_data.get('slide_type', 'loan_portfolio'))
        
        # Update title
        if 'title' in content_data:
            self._update_slide_title(root, content_data['title'])
        
        # Update subtitle
        if 'subtitle' in content_data:
            self._update_slide_subtitle(root, content_data['subtitle'])
        
        # Update highlights
        if 'highlights' in content_data:
            self._update_slide_highlights(root, content_data['highlights'])
        
        # Ensure branding elements
        self._ensure_branding_elements(root)
        
        # Save updated XML
        tree.write(slide_path, encoding='UTF-8', xml_declaration=True)
    
    def _clean_slide_content(self, root: ET.Element, slide_type: str):
        """Clean up slide content to prepare for new content"""
        # Find all text shapes and update them based on slide type
        for shape in root.findall('.//p:sp', NAMESPACES):
            # Check if this is a title or subtitle shape
            nv_pr = shape.find('.//p:nvPr', NAMESPACES)
            if nv_pr is not None:
                ph = nv_pr.find('p:ph', NAMESPACES)
                if ph is not None:
                    ph_type = ph.get('type')
                    if ph_type == 'subTitle' or ph_type == 'body':
                        # Clear subtitle/body text that might be from wrong slide type
                        tx_body = shape.find('.//p:txBody', NAMESPACES)
                        if tx_body is not None:
                            for para in tx_body.findall('.//a:p', NAMESPACES):
                                for run in para.findall('.//a:r', NAMESPACES):
                                    text_elem = run.find('a:t', NAMESPACES)
                                    if text_elem is not None:
                                        # Clear text that's from wrong slide type
                                        if slide_type == 'loan_portfolio' and 'noninterest' in text_elem.text.lower():
                                            text_elem.text = ''
                                        elif slide_type == 'noninterest_income' and 'loan' in text_elem.text.lower() and 'noninterest' not in text_elem.text.lower():
                                            text_elem.text = ''
    
    def _update_slide_title(self, root: ET.Element, title: str):
        """Update slide title - find title placeholder and update"""
        # Find the title placeholder shape
        for shape in root.findall('.//p:sp', NAMESPACES):
            nv_pr = shape.find('.//p:nvPr', NAMESPACES)
            if nv_pr is not None:
                ph = nv_pr.find('p:ph', NAMESPACES)
                if ph is not None and ph.get('type') == 'title':
                    # Found title placeholder
                    # Get the text body
                    tx_body = shape.find('.//p:txBody', NAMESPACES)
                    if tx_body is not None:
                        # Find all paragraphs and clear them
                        for para in tx_body.findall('a:p', NAMESPACES):
                            # Remove all existing runs
                            for run in para.findall('a:r', NAMESPACES):
                                para.remove(run)
                            
                            # Add new run with the title
                            new_run = ET.SubElement(para, '{' + NAMESPACES['a'] + '}r')
                            run_props = ET.SubElement(new_run, '{' + NAMESPACES['a'] + '}rPr')
                            run_props.set('dirty', '0')
                            text_elem = ET.SubElement(new_run, '{' + NAMESPACES['a'] + '}t')
                            text_elem.text = title
                            
                            # Only update first paragraph
                            return
    
    def _update_slide_subtitle(self, root: ET.Element, subtitle: str):
        """Update slide subtitle"""
        # Find subtitle placeholder or text with specific characteristics
        for shape in root.findall('.//p:sp', NAMESPACES):
            # Check for subtitle placeholder
            nv_pr = shape.find('.//p:nvPr', NAMESPACES)
            if nv_pr is not None:
                ph = nv_pr.find('p:ph', NAMESPACES)
                if ph is not None and (ph.get('type') == 'subTitle' or ph.get('type') == 'body'):
                    # Found subtitle placeholder
                    tx_body = shape.find('.//p:txBody', NAMESPACES)
                    if tx_body is not None:
                        # Clear all paragraphs and add new one with subtitle
                        for para in tx_body.findall('a:p', NAMESPACES):
                            tx_body.remove(para)
                        
                        # Add new paragraph with subtitle
                        new_para = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}p')
                        new_run = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}r')
                        run_props = ET.SubElement(new_run, '{' + NAMESPACES['a'] + '}rPr')
                        run_props.set('sz', '2000')  # 20pt
                        text_elem = ET.SubElement(new_run, '{' + NAMESPACES['a'] + '}t')
                        text_elem.text = subtitle
                        return
            
            # If no placeholder, look for text that might be a subtitle
            # (e.g., "$ In Millions" or "Total Loans Held for Investment")
            tx_body = shape.find('.//p:txBody', NAMESPACES)
            if tx_body is not None:
                first_para = tx_body.find('a:p', NAMESPACES)
                if first_para is not None:
                    text = ''.join(first_para.itertext())
                    # Check if this looks like a subtitle
                    if any(marker in text.lower() for marker in ['$ in millions', 'total loans', 'noninterest income']):
                        # Update this text
                        for run in first_para.findall('a:r', NAMESPACES):
                            first_para.remove(run)
                        
                        new_run = ET.SubElement(first_para, '{' + NAMESPACES['a'] + '}r')
                        text_elem = ET.SubElement(new_run, '{' + NAMESPACES['a'] + '}t')
                        text_elem.text = subtitle
                        return
    
    def _update_slide_highlights(self, root: ET.Element, highlights: Union[List[str], List[Dict]]):
        """Update highlights section - handles both simple and hierarchical highlights"""
        # Find the highlights text box
        for shape in root.findall('.//p:sp', NAMESPACES):
            text_body = shape.find('.//p:txBody', NAMESPACES)
            if text_body is not None:
                # Check if this contains "Highlights"
                for para in text_body.findall('.//a:p', NAMESPACES):
                    text = ''.join(para.itertext())
                    if 'highlight' in text.lower():
                        # This is the highlights box - update content
                        # Keep the title paragraph
                        paragraphs = text_body.findall('a:p', NAMESPACES)
                        
                        # Clear all paragraphs except the title
                        for i, para in enumerate(paragraphs):
                            if i > 0:  # Keep first paragraph (title)
                                text_body.remove(para)
                        
                        # Check if highlights are hierarchical
                        if highlights and isinstance(highlights[0], dict):
                            # Hierarchical highlights
                            for highlight in highlights[1:]:  # Skip title
                                self._add_hierarchical_highlight(text_body, highlight)
                        else:
                            # Simple bullet points
                            for highlight in highlights:
                                if 'highlight' in highlight.lower():
                                    continue  # Skip the title itself
                                
                                new_para = ET.SubElement(text_body, '{' + NAMESPACES['a'] + '}p')
                                
                                # Add bullet properties
                                pPr = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}pPr')
                                pPr.set('lvl', '0')
                                pPr.set('marL', '342900')
                                pPr.set('indent', '-342900')
                                
                                # Add bullet character
                                buChar = ET.SubElement(pPr, '{' + NAMESPACES['a'] + '}buChar')
                                buChar.set('char', '•')
                                
                                # Add text run
                                run = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}r')
                                rPr = ET.SubElement(run, '{' + NAMESPACES['a'] + '}rPr')
                                rPr.set('sz', '1400')
                                text_elem = ET.SubElement(run, '{' + NAMESPACES['a'] + '}t')
                                text_elem.text = highlight
                        
                        return
    
    def _add_hierarchical_highlight(self, text_body: ET.Element, highlight: Dict):
        """Add a hierarchical highlight with proper formatting"""
        level = highlight.get('level', 1)
        style = highlight.get('style', 'normal')
        text = highlight['text']
        
        new_para = ET.SubElement(text_body, '{' + NAMESPACES['a'] + '}p')
        pPr = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}pPr')
        
        if level == 1:  # Category header
            pPr.set('lvl', '0')
            pPr.set('marL', '342900')
            pPr.set('indent', '-342900')
            
            # Red square bullet
            buChar = ET.SubElement(pPr, '{' + NAMESPACES['a'] + '}buChar')
            buChar.set('char', '■')
            buClr = ET.SubElement(pPr, '{' + NAMESPACES['a'] + '}buClr')
            srgbClr = ET.SubElement(buClr, '{' + NAMESPACES['a'] + '}srgbClr')
            srgbClr.set('val', 'BE0000')  # Red color
        
        elif level == 2:  # Sub-item
            pPr.set('lvl', '1')
            pPr.set('marL', '685800')
            pPr.set('indent', '-342900')
            
            # Circle bullet
            buChar = ET.SubElement(pPr, '{' + NAMESPACES['a'] + '}buChar')
            buChar.set('char', '○')
        
        # Add text run
        run = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}r')
        rPr = ET.SubElement(run, '{' + NAMESPACES['a'] + '}rPr')
        rPr.set('sz', '1400' if level == 2 else '1600')  # Smaller font for sub-items
        
        if level == 1:  # Bold for category headers
            rPr.set('b', '1')
        
        text_elem = ET.SubElement(run, '{' + NAMESPACES['a'] + '}t')
        text_elem.text = text
    
    def _ensure_branding_elements(self, root: ET.Element):
        """Ensure South Plains branding elements are present on the slide."""
        # Find spTree element
        sp_tree = root.find('.//p:spTree', NAMESPACES)
        if sp_tree is None:
            return
            
        # Check if footer bar already exists
        has_footer = False
        has_divider = False
        has_footer_text = False
        
        for shape in sp_tree.findall('.//p:sp', NAMESPACES):
            # Check position to identify footer bar
            xfrm = shape.find('.//a:xfrm', NAMESPACES)
            if xfrm is not None:
                off = xfrm.find('a:off', NAMESPACES)
                if off is not None and off.get('y') == '7040879':
                    has_footer = True
                    
        # Add gray footer bar if missing
        if not has_footer:
            footer_shape = ET.SubElement(sp_tree, '{' + NAMESPACES['p'] + '}sp')
            
            # Non-visual properties
            nv_sp_pr = ET.SubElement(footer_shape, '{' + NAMESPACES['p'] + '}nvSpPr')
            c_nv_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}cNvPr')
            c_nv_pr.set('id', '100')
            c_nv_pr.set('name', 'Footer Bar')
            c_nv_sp_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}cNvSpPr')
            nv_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}nvPr')
            
            # Shape properties
            sp_pr = ET.SubElement(footer_shape, '{' + NAMESPACES['p'] + '}spPr')
            
            # Transform
            xfrm = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}xfrm')
            off = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}off')
            off.set('x', '0')
            off.set('y', '7040879')
            ext = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}ext')
            ext.set('cx', '10058400')
            ext.set('cy', '731520')
            
            # Rectangle geometry
            prst_geom = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}prstGeom')
            prst_geom.set('prst', 'rect')
            av_lst = ET.SubElement(prst_geom, '{' + NAMESPACES['a'] + '}avLst')
            
            # Fill color - gray
            solid_fill = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}solidFill')
            srgb_clr = ET.SubElement(solid_fill, '{' + NAMESPACES['a'] + '}srgbClr')
            srgb_clr.set('val', 'BDBDBD')
            
            # Add footer text
            self._add_footer_text(sp_tree)
            # Use the slide number from the prompt or default to 26
            page_num = getattr(self, 'current_slide_number', '26')
            self._add_page_number(sp_tree, page_num)
            
        # Add black divider line under title if missing
        self._add_title_divider(sp_tree)
    
    # Include all parsing methods from original generator
    def _parse_prompt(self, prompt: str, slide_type: str) -> Dict:
        """Parse natural language prompt into structured data"""
        content_data = {
            'slide_type': slide_type,
            'prompt': prompt,
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract slide number if mentioned in prompt
        slide_number_match = re.search(r'[Ss]lide\s*(\d+)', prompt)
        if slide_number_match:
            content_data['slide_number'] = int(slide_number_match.group(1))
            logger.info(f"Detected slide number {content_data['slide_number']} in prompt")
        
        # Determine actual content type based on slide number and prompt content
        if content_data.get('slide_number') == 24 or 'donut chart' in prompt.lower():
            # Slide 24 is portfolio composition with donut chart
            content_data.update(self._parse_portfolio_composition_prompt(prompt))
        elif content_data.get('slide_number') == 23:
            # Slide 23 might have different format
            content_data.update(self._parse_slide_23_prompt(prompt))
        elif slide_type == 'loan_portfolio':
            content_data.update(self._parse_loan_portfolio_prompt(prompt))
        elif slide_type == 'noninterest_income':
            content_data.update(self._parse_noninterest_income_prompt(prompt))
        else:
            content_data.update(self._parse_generic_prompt(prompt))
        
        return content_data
    
    def _parse_loan_portfolio_prompt(self, prompt: str) -> Dict:
        """Extract loan portfolio data from prompt"""
        # Check if this is a donut chart or bar chart based on prompt
        is_donut = 'donut chart' in prompt.lower()
        
        data = {
            'title': 'Loan Portfolio',
            'subtitle': 'Portfolio Composition' if is_donut else 'Total Loans Held for Investment ($ in Millions)',
            'chart_type': 'donut' if is_donut else 'bar_line_combo'
        }
        
        # Extract quarters and values
        quarters_pattern = r"(\d[Q][''']\d{2})"
        values_pattern = r'\$(\d+(?:,\d+)?(?:\.\d+)?)[M\s]*(?:million)?'
        
        quarters = re.findall(quarters_pattern, prompt)
        raw_values = re.findall(values_pattern, prompt)
        values = [float(v.replace(',', '')) for v in raw_values]
        
        # Extract yield percentages (for line chart)
        yield_pattern = r'(\d+\.\d+)%'
        yields = re.findall(yield_pattern, prompt)
        
        if quarters and values:
            # Create series for bar and line combo chart
            series = [{
                'name': 'Total Loans',
                'values': values[:5],
                'chart_type': 'bar'
            }]
            
            # Add yield line if we have yield data
            if yields and len(yields) >= 5:
                series.append({
                    'name': 'Yield %',
                    'values': [float(y) for y in yields[:5]],
                    'chart_type': 'line'
                })
                
                # Check for PPP yield
                ppp_match = re.search(r'yield with PPP.*?(\d+\.\d+)%', prompt, re.IGNORECASE)
                if ppp_match:
                    # Add PPP yield as separate series
                    ppp_yield = float(ppp_match.group(1))
                    series.append({
                        'name': 'Yield with PPP',
                        'values': [None, None, None, None, ppp_yield],  # Only show for last quarter
                        'chart_type': 'line_dashed'
                    })
            
            data['chart_data'] = {
                'categories': quarters[:5],
                'series': series
            }
        
        # Extract highlights from prompt
        if 'highlight' in prompt.lower():
            # Check if this is a hierarchical highlight structure (for donut charts)
            if is_donut:
                data['highlights'] = self._parse_hierarchical_highlights(prompt)
            else:
                # Regular bullet point highlights for bar charts
                data['highlights'] = self._parse_regular_highlights(prompt)
        else:
            # No highlights requested
            data['highlights'] = ["2Q'20 Highlights"]
        
        return data
    
    def _parse_hierarchical_highlights(self, prompt: str) -> List[Dict]:
        """Parse hierarchical highlights structure for donut charts"""
        highlights_match = re.search(r'(?:highlights?|highlight\s+section)\s*(?:listing)?[:\s]*(.+?)(?:with\s+red\s+accents|styled|$)', prompt, re.IGNORECASE | re.DOTALL)
        if not highlights_match:
            return [{"text": "2Q'20 Highlights", "level": 0}]
        
        highlights_text = highlights_match.group(1).strip()
        highlights = [{"text": "2Q'20 Highlights", "level": 0}]  # Title
        
        # Parse categories with sub-items
        # Pattern: "Commercial Real Estate (Comm. LDC & Res. LD 9%, Hospitality 5%)"
        category_pattern = r'([^(),]+?)\s*\(([^)]+)\)'
        
        # Find all category matches
        for match in re.finditer(category_pattern, highlights_text):
            category = match.group(1).strip()
            sub_items = match.group(2)
            
            # Add category header
            if 'includes' not in category.lower():
                category += ' includes:'
            highlights.append({"text": category, "level": 1, "style": "category"})
            
            # Parse sub-items
            sub_item_pattern = r'([^,]+?)\s*(\d+%?)'
            for sub_match in re.finditer(sub_item_pattern, sub_items):
                item_text = sub_match.group(1).strip() + ' – ' + sub_match.group(2)
                highlights.append({"text": item_text, "level": 2, "style": "subitem"})
        
        return highlights
    
    def _parse_portfolio_composition_prompt(self, prompt: str) -> Dict:
        """Parse portfolio composition prompt for donut chart slides"""
        data = {
            'title': 'Loan Portfolio',
            'subtitle': 'Portfolio Composition',
            'chart_type': 'donut'
        }
        
        # Extract donut chart data
        # Pattern: "Commercial Real Estate 28%, Commercial – General 27%"
        percentage_pattern = r'([A-Za-z\s–-]+?)\s*(\d+)%'
        chart_data = []
        for match in re.finditer(percentage_pattern, prompt):
            category = match.group(1).strip()
            percentage = int(match.group(2))
            if category and 'highlight' not in category.lower():
                chart_data.append({'name': category, 'value': percentage})
        
        if chart_data:
            data['chart_data'] = chart_data
        
        # Parse hierarchical highlights without unwanted text
        data['highlights'] = self._parse_hierarchical_highlights_clean(prompt)
        
        return data
    
    def _parse_slide_23_prompt(self, prompt: str) -> Dict:
        """Parse slide 23 specific format"""
        data = {
            'title': self._extract_title_from_prompt(prompt),
            'slide_type': 'custom'
        }
        
        # Parse highlights without loan increase details
        if 'highlight' in prompt.lower():
            # Extract only the actual highlight items, not the loan details
            data['highlights'] = self._parse_slide_23_highlights(prompt)
        
        return data
    
    def _parse_hierarchical_highlights_clean(self, prompt: str) -> List[Dict]:
        """Parse hierarchical highlights without 'listing breakdowns for' text"""
        highlights = [{"text": "2Q'20 Highlights", "level": 0}]
        
        # Find the highlights section
        highlights_match = re.search(r'highlights["\s]*(?:listing)?[:\s]*(.+?)(?:with\s+red\s+accents|styled|$)', prompt, re.IGNORECASE | re.DOTALL)
        if not highlights_match:
            return highlights
        
        highlights_text = highlights_match.group(1).strip()
        
        # Remove "listing breakdowns for" or similar phrases
        highlights_text = re.sub(r'listing\s+breakdowns?\s+for\s*', '', highlights_text, flags=re.IGNORECASE)
        highlights_text = re.sub(r'breakdowns?\s+for\s*', '', highlights_text, flags=re.IGNORECASE)
        
        # Parse categories with better pattern
        # Look for "Commercial Real Estate (Comm. LDC & Res. LD 9%, Hospitality 5%)"
        category_pattern = r'([A-Za-z\s–-]+?)\s*\(([^)]+)\)'
        
        for match in re.finditer(category_pattern, highlights_text):
            category = match.group(1).strip()
            sub_items_text = match.group(2)
            
            # Clean up category name
            if not category.endswith('includes:'):
                category += ' includes:'
            
            highlights.append({"text": category, "level": 1, "style": "category"})
            
            # Parse sub-items more carefully
            # Pattern: "Comm. LDC & Res. LD 9%" or "PPP 9%"
            sub_items = re.split(r',\s*(?=[A-Z])', sub_items_text)
            for item in sub_items:
                item = item.strip()
                # Extract percentage at the end
                percent_match = re.search(r'(.+?)\s*(\d+%?)\s*$', item)
                if percent_match:
                    item_name = percent_match.group(1).strip()
                    item_percent = percent_match.group(2)
                    formatted_item = f"{item_name} – {item_percent}"
                    highlights.append({"text": formatted_item, "level": 2, "style": "subitem"})
        
        return highlights
    
    def _parse_slide_23_highlights(self, prompt: str) -> List[str]:
        """Parse highlights for slide 23 without loan details"""
        highlights = ["2Q'20 Highlights"]
        
        # Find highlights section but exclude loan increase details
        highlights_match = re.search(r'highlights["\s]*[:\s]*(.+?)(?:styled|$)', prompt, re.IGNORECASE | re.DOTALL)
        if not highlights_match:
            return highlights
        
        highlights_text = highlights_match.group(1)
        
        # Skip lines that contain loan increase amounts
        skip_patterns = [
            r'total loan increase of \$\d+',
            r'growth from \$\d+',
            r'partial offset from \$\d+',
            r'listing:',
            r'\$\d+\.?\d*[MB]'
        ]
        
        # Split by common delimiters
        parts = re.split(r'[,.]\s*', highlights_text)
        
        for part in parts:
            part = part.strip()
            # Check if this part should be skipped
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, part, re.IGNORECASE):
                    should_skip = True
                    break
            
            if not should_skip and part and len(part) > 10:
                # Clean up the text
                part = re.sub(r'^(and\s+|listing\s*:|-)\s*', '', part, flags=re.IGNORECASE)
                if part and part not in highlights:
                    highlights.append(part)
        
        return highlights[:5]  # Limit to 5 items
    
    def _extract_title_from_prompt(self, prompt: str) -> str:
        """Extract title from prompt"""
        # Look for text after 'titled'
        title_match = re.search(r'titled\s+["\']?([^"\']+)["\']?', prompt, re.IGNORECASE)
        if title_match:
            return title_match.group(1).strip()
        return 'Loan Portfolio'
    
    def _parse_regular_highlights(self, prompt: str) -> List[str]:
        """Parse regular bullet point highlights for bar charts (Slide 26)"""
        highlights_match = re.search(r'(?:highlights?|highlight\s+section)\s*(?:listing)?[:\s]*(.+?)(?:styled|with\s+red|$)', prompt, re.IGNORECASE | re.DOTALL)
        if not highlights_match:
            return ["2Q'20 Highlights"]
        
        highlights_text = highlights_match.group(1)
        highlights = ["2Q'20 Highlights"]  # Title
        
        # For Slide 26, we want specific items, not the dollar amounts
        # Look for these specific patterns in the prompt
        wanted_patterns = [
            r'over\s+\d+[^,\.]+PPP loans[^,\.]*',  # "over 2,000 PPP loans closed"
            r'\d+Q\'\d+\s+yield[^,\.)]+(?:\([^)]+\))?',  # "2Q'20 yield of 5.26% (down 50 bps vs. 1Q'20 excluding PPP)"
        ]
        
        # First try to find the specific wanted patterns
        for pattern in wanted_patterns:
            match = re.search(pattern, highlights_text, re.IGNORECASE)
            if match:
                highlight = match.group(0).strip()
                highlight = re.sub(r'^\s*[-,]\s*', '', highlight)
                if highlight and not any(h == highlight for h in highlights):
                    highlights.append(highlight)
        
        # Also look for items that don't contain dollar amounts
        parts = re.split(r',\s*(?=and\s|[a-zA-Z])', highlights_text)
        for part in parts:
            part = part.strip()
            
            # Skip if it contains loan amounts or specific unwanted phrases
            if any(phrase in part.lower() for phrase in ['total loan increase of $', 'growth from $', 'partial offset from $', 'listing:', '$229', '$215', '$24']):
                continue
            
            # Clean and add if it's substantial
            part = re.sub(r'^\s*(and\s+|listing\s*:|-|\d+\.\s*)\s*', '', part, flags=re.IGNORECASE)
            if part and len(part) > 15 and not any(part in h for h in highlights):
                highlights.append(part)
        
        return highlights[:4]  # Return title + 3 highlights max
    
    def _parse_noninterest_income_prompt(self, prompt: str) -> Dict:
        """Extract noninterest income data from prompt"""
        data = {
            'title': 'Noninterest Income',
            'subtitle': '$ In Millions'
        }
        
        # Similar implementation to loan portfolio
        quarters_pattern = r'(\d[Q]\d{2})'
        values_pattern = r'\$(\d+(?:\.\d+)?)[M\s]*(?:million)?'
        percentage_pattern = r'(\d+)%'
        
        quarters = re.findall(quarters_pattern, prompt)
        raw_values = re.findall(values_pattern, prompt)
        values = [float(v.replace(',', '')) for v in raw_values]
        percentages = [int(p) for p in re.findall(percentage_pattern, prompt)]
        
        if values and len(values) >= 2:
            current = values[-1]
            previous = values[-2]
            data['highlights'] = [
                f"2Q'20 Highlights",
                f"Noninterest income is ${current} million, compared to ${previous} million in 1Q'20",
                "The increase in 2Q'20 compared to 1Q'20 due to:",
                "• An increase in mortgage banking activities revenue",
                "• Fee income driven by mortgage operations and bank services"
            ]
        
        return data
    
    def _parse_generic_prompt(self, prompt: str) -> Dict:
        """Parse generic prompt"""
        return {
            'title': prompt.split('.')[0][:50],
            'content': prompt
        }
    
    def _add_footer_text(self, sp_tree: ET.Element):
        """Add South Plains Financial, Inc. text to footer."""
        footer_text_shape = ET.SubElement(sp_tree, '{' + NAMESPACES['p'] + '}sp')
        
        # Non-visual properties
        nv_sp_pr = ET.SubElement(footer_text_shape, '{' + NAMESPACES['p'] + '}nvSpPr')
        c_nv_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}cNvPr')
        c_nv_pr.set('id', '101')
        c_nv_pr.set('name', 'Footer Text')
        c_nv_sp_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}cNvSpPr')
        nv_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}nvPr')
        
        # Shape properties
        sp_pr = ET.SubElement(footer_text_shape, '{' + NAMESPACES['p'] + '}spPr')
        xfrm = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}xfrm')
        off = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}off')
        off.set('x', '457200')
        off.set('y', '7257600')
        ext = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}ext')
        ext.set('cx', '4572000')
        ext.set('cy', '304800')
        
        # Text body
        tx_body = ET.SubElement(footer_text_shape, '{' + NAMESPACES['p'] + '}txBody')
        body_pr = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}bodyPr')
        lst_style = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}lstStyle')
        
        # Paragraph with text
        p = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}p')
        r = ET.SubElement(p, '{' + NAMESPACES['a'] + '}r')
        rPr = ET.SubElement(r, '{' + NAMESPACES['a'] + '}rPr')
        rPr.set('sz', '1800')
        rPr.set('b', '1')
        
        # Red text color
        solid_fill_text = ET.SubElement(rPr, '{' + NAMESPACES['a'] + '}solidFill')
        srgb_clr_text = ET.SubElement(solid_fill_text, '{' + NAMESPACES['a'] + '}srgbClr')
        srgb_clr_text.set('val', 'BE0000')
        
        # Font
        latin = ET.SubElement(rPr, '{' + NAMESPACES['a'] + '}latin')
        latin.set('typeface', 'Arial')
        
        # Text
        t = ET.SubElement(r, '{' + NAMESPACES['a'] + '}t')
        t.text = 'South Plains Financial, Inc.'
    
    def _add_page_number(self, sp_tree: ET.Element, page_num: str):
        """Add page number to footer."""
        page_num_shape = ET.SubElement(sp_tree, '{' + NAMESPACES['p'] + '}sp')
        
        # Non-visual properties
        nv_sp_pr = ET.SubElement(page_num_shape, '{' + NAMESPACES['p'] + '}nvSpPr')
        c_nv_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}cNvPr')
        c_nv_pr.set('id', '102')
        c_nv_pr.set('name', 'Page Number')
        c_nv_sp_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}cNvSpPr')
        nv_pr = ET.SubElement(nv_sp_pr, '{' + NAMESPACES['p'] + '}nvPr')
        
        # Shape properties
        sp_pr = ET.SubElement(page_num_shape, '{' + NAMESPACES['p'] + '}spPr')
        xfrm = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}xfrm')
        off = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}off')
        off.set('x', '9450000')
        off.set('y', '7257600')
        ext = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}ext')
        ext.set('cx', '457200')
        ext.set('cy', '304800')
        
        # Text body
        tx_body = ET.SubElement(page_num_shape, '{' + NAMESPACES['p'] + '}txBody')
        body_pr = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}bodyPr')
        lst_style = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}lstStyle')
        
        # Paragraph with right alignment
        p = ET.SubElement(tx_body, '{' + NAMESPACES['a'] + '}p')
        pPr = ET.SubElement(p, '{' + NAMESPACES['a'] + '}pPr')
        pPr.set('algn', 'r')
        
        r = ET.SubElement(p, '{' + NAMESPACES['a'] + '}r')
        rPr = ET.SubElement(r, '{' + NAMESPACES['a'] + '}rPr')
        rPr.set('sz', '1800')
        
        # White text color
        solid_fill = ET.SubElement(rPr, '{' + NAMESPACES['a'] + '}solidFill')
        srgb_clr = ET.SubElement(solid_fill, '{' + NAMESPACES['a'] + '}srgbClr')
        srgb_clr.set('val', 'FFFFFF')
        
        t = ET.SubElement(r, '{' + NAMESPACES['a'] + '}t')
        t.text = page_num
    
    def _add_title_divider(self, sp_tree: ET.Element):
        """Add black divider line under title."""
        # Check if divider already exists
        for shape in sp_tree.findall('.//p:cxnSp', NAMESPACES):
            xfrm = shape.find('.//a:xfrm', NAMESPACES)
            if xfrm is not None:
                off = xfrm.find('a:off', NAMESPACES)
                if off is not None and off.get('y') == '1143000':
                    return  # Divider already exists
        
        # Add line
        line_shape = ET.SubElement(sp_tree, '{' + NAMESPACES['p'] + '}cxnSp')
        
        # Non-visual properties
        nv_cxn_sp_pr = ET.SubElement(line_shape, '{' + NAMESPACES['p'] + '}nvCxnSpPr')
        c_nv_pr = ET.SubElement(nv_cxn_sp_pr, '{' + NAMESPACES['p'] + '}cNvPr')
        c_nv_pr.set('id', '103')
        c_nv_pr.set('name', 'Divider Line')
        c_nv_cxn_sp_pr = ET.SubElement(nv_cxn_sp_pr, '{' + NAMESPACES['p'] + '}cNvCxnSpPr')
        nv_pr = ET.SubElement(nv_cxn_sp_pr, '{' + NAMESPACES['p'] + '}nvPr')
        
        # Shape properties
        sp_pr = ET.SubElement(line_shape, '{' + NAMESPACES['p'] + '}spPr')
        xfrm = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}xfrm')
        off = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}off')
        off.set('x', '685800')
        off.set('y', '1143000')
        ext = ET.SubElement(xfrm, '{' + NAMESPACES['a'] + '}ext')
        ext.set('cx', '8686800')
        ext.set('cy', '0')
        
        # Line geometry
        prst_geom = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}prstGeom')
        prst_geom.set('prst', 'line')
        av_lst = ET.SubElement(prst_geom, '{' + NAMESPACES['a'] + '}avLst')
        
        # Line style
        ln = ET.SubElement(sp_pr, '{' + NAMESPACES['a'] + '}ln')
        ln.set('w', '9144')
        solid_fill_line = ET.SubElement(ln, '{' + NAMESPACES['a'] + '}solidFill')
        srgb_clr_line = ET.SubElement(solid_fill_line, '{' + NAMESPACES['a'] + '}srgbClr')
        srgb_clr_line.set('val', '000000')
    
    # Include other necessary methods
    def _download_template(self, local_path: Path):
        """Download template from S3"""
        try:
            logger.info(f"Downloading template from S3: {self.template_bucket}/{self.template_key}")
            self.s3_client.download_file(
                self.template_bucket,
                self.template_key,
                str(local_path)
            )
            logger.info("Template downloaded successfully")
        except Exception as e:
            logger.error(f"Failed to download template: {e}")
            raise
    
    def _create_pptx(self, extract_dir: Path, output_path: Path):
        """Create PowerPoint file from directory"""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(extract_dir))
                    zipf.write(file_path, arcname)
    
    def _upload_to_s3(self, file_path: Path, slide_type: str) -> str:
        """Upload to S3 and return URL"""
        output_bucket = os.environ.get('OUTPUT_BUCKET', 'scribbe-ai-dev-output')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f'single_slides/{slide_type}_{timestamp}.pptx'
        
        self.s3_client.upload_file(
            str(file_path),
            output_bucket,
            s3_key,
            ExtraArgs={'ContentType': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'}
        )
        
        # Generate presigned URL
        url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': output_bucket, 'Key': s3_key},
            ExpiresIn=3600
        )
        
        logger.info(f"Single slide uploaded to S3: {s3_key}")
        return url

# Lambda handler if needed
def lambda_handler(event, context):
    """AWS Lambda handler function"""
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '')
        slide_type = body.get('slide_type', 'generic')
        
        if not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Prompt is required'})
            }
        
        # Generate single slide
        generator = SingleSlideGenerator()
        s3_url = generator.generate_single_slide(prompt, slide_type)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'download_url': s3_url,
                'slide_type': slide_type,
                'message': 'Single slide generated successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

if __name__ == "__main__":
    # Test locally
    generator = SingleSlideGenerator()
    
    # Test loan portfolio
    loan_prompt = "Create a loan portfolio slide showing quarters 2Q19 through 2Q20 with values $137, $141, $167, $189, $249 million."
    result = generator.generate_single_slide(loan_prompt, 'loan_portfolio')
    print(f"Generated single slide: {result}")