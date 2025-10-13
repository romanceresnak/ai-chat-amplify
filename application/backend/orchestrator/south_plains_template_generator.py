"""
South Plains Template-Based PowerPoint Generator for AWS Lambda

This module generates presentations by using the South Plains template as a base,
preserving all formatting while dynamically replacing content based on prompts.
"""

import os
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
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

class SouthPlainsGenerator:
    """
    Generates PowerPoint presentations using South Plains template,
    optimized for AWS Lambda environment.
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
        logger.info(f"SouthPlainsGenerator initialized with bucket: {self.template_bucket}, key: {self.template_key}")
        
    def generate_from_prompt(self, prompt: str, slide_type: str) -> str:
        """
        Generate a presentation based on prompt and slide type.
        
        Args:
            prompt: Natural language prompt describing the content
            slide_type: Type of slide (e.g., 'loan_portfolio', 'noninterest_income')
            
        Returns:
            S3 URL of generated presentation
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
            
            # Update slides based on content
            self._update_slides(extract_dir, content_data)
            
            # Repackage PowerPoint
            output_path = work_dir / f'generated_{slide_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pptx'
            self._create_pptx(extract_dir, output_path)
            
            # Upload to S3
            s3_url = self._upload_to_s3(output_path, slide_type)
            
            return s3_url
            
        finally:
            # Cleanup
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
    
    def _download_template(self, local_path: Path):
        """Download template from S3."""
        try:
            logger.info(f"Attempting to download template from S3: {self.template_bucket}/{self.template_key}")
            self.s3_client.download_file(
                self.template_bucket,
                self.template_key,
                str(local_path)
            )
            logger.info(f"Template downloaded successfully from S3: {self.template_bucket}/{self.template_key}")
        except Exception as e:
            logger.error(f"S3 download failed for {self.template_bucket}/{self.template_key}: {str(e)}")
            # Try alternative local templates
            local_alternatives = [
                Path(__file__).parent / 'working_reference.pptx',
                Path(__file__).parent / 'south_plains_template.pptx',
                Path(__file__).parent / 'PUBLIC IP South Plains (1).pptx'
            ]
            
            for local_template in local_alternatives:
                if local_template.exists():
                    logger.info(f"Using local template fallback: {local_template}")
                    shutil.copy(local_template, local_path)
                    return
            
            raise Exception(f"No template available. Tried S3: {self.template_bucket}/{self.template_key} and local alternatives")
    
    def _parse_prompt(self, prompt: str, slide_type: str) -> Dict:
        """Parse natural language prompt into structured data."""
        content_data = {
            'slide_type': slide_type,
            'prompt': prompt,
            'timestamp': datetime.now().isoformat()
        }
        
        # Extract key information based on slide type
        if slide_type == 'loan_portfolio':
            content_data.update(self._parse_loan_portfolio_prompt(prompt))
        elif slide_type == 'noninterest_income':
            content_data.update(self._parse_noninterest_income_prompt(prompt))
        elif slide_type == 'financial_summary':
            content_data.update(self._parse_financial_summary_prompt(prompt))
        else:
            content_data.update(self._parse_generic_prompt(prompt))
        
        return content_data
    
    def _parse_loan_portfolio_prompt(self, prompt: str) -> Dict:
        """Extract loan portfolio data from prompt."""
        data = {
            'title': 'Loan Portfolio',
            'subtitle': 'Total Loans Held for Investment ($ in Millions)',
            'slide_number': 26  # Based on template analysis
        }
        
        # Extract quarters and values using regex
        quarters_pattern = r'(\d[Q]\d{2})'
        values_pattern = r'\$(\d+(?:\.\d+)?)[M\s]*(?:million)?'
        
        quarters = re.findall(quarters_pattern, prompt)
        raw_values = re.findall(values_pattern, prompt)
        values = []
        for v in raw_values:
            try:
                values.append(float(v.replace(',', '')))
            except ValueError:
                continue
        
        if quarters and values:
            data['chart_data'] = {
                'categories': quarters[:5],  # Max 5 quarters
                'series': [{
                    'name': 'Total Loans',
                    'values': values[:5]
                }]
            }
        
        # Extract highlights
        if 'highlight' in prompt.lower():
            highlights = prompt.split('highlight')[-1].split('.')
            data['highlights'] = [h.strip() for h in highlights if h.strip()][:3]
        else:
            # Generate default highlights
            if values and len(values) >= 2:
                growth = values[-1] - values[-2]
                data['highlights'] = [
                    f'2Q\'20 Highlights',
                    f'Loan growth of ${growth:.0f} million in Q2',
                    'Strong performance across all segments'
                ]
        
        return data
    
    def _parse_noninterest_income_prompt(self, prompt: str) -> Dict:
        """Extract noninterest income data from prompt."""
        data = {
            'title': 'Noninterest Income',
            'subtitle': '$ In Millions',
            'slide_number': 26
        }
        
        # Extract data similar to loan portfolio
        quarters_pattern = r'(\d[Q]\d{2})'
        values_pattern = r'\$(\d+(?:\.\d+)?)[M\s]*(?:million)?'
        percentage_pattern = r'(\d+)%'
        
        quarters = re.findall(quarters_pattern, prompt)
        raw_values = re.findall(values_pattern, prompt)
        values = []
        for v in raw_values:
            try:
                values.append(float(v.replace(',', '')))
            except ValueError:
                continue
        percentages = [int(p) for p in re.findall(percentage_pattern, prompt)]
        
        if quarters and values:
            series_data = [{
                'name': 'Noninterest Income',
                'values': values[:5]
            }]
            
            if percentages:
                series_data.append({
                    'name': '% of Revenue',
                    'values': percentages[:5]
                })
            
            data['chart_data'] = {
                'categories': quarters[:5],
                'series': series_data
            }
        
        # Extract key insights
        if values and len(values) >= 2:
            current = values[-1]
            previous = values[-2]
            data['highlights'] = [
                f'2Q\'20 Highlights',
                f'Noninterest income is ${current} million, compared to ${previous} million in 1Q\'20',
                'The increase in 2Q\'20 compared to 1Q\'20 due to:',
                'An increase in mortgage banking activities revenue',
                'Fee income driven by mortgage operations and bank services'
            ]
        
        return data
    
    def _parse_financial_summary_prompt(self, prompt: str) -> Dict:
        """Extract financial summary data from prompt."""
        return {
            'title': 'Financial Summary',
            'slide_number': 5,
            'content': prompt
        }
    
    def _parse_generic_prompt(self, prompt: str) -> Dict:
        """Parse generic prompt for any slide type."""
        return {
            'title': prompt.split('.')[0][:50],  # First sentence as title
            'content': prompt,
            'slide_number': 1
        }
    
    def _update_slides(self, extract_dir: Path, content_data: Dict):
        """Update slide content based on parsed data."""
        slide_num = content_data.get('slide_number', 26)
        slide_path = extract_dir / 'ppt' / 'slides' / f'slide{slide_num}.xml'
        
        if not slide_path.exists():
            logger.warning(f"Slide {slide_num} not found, using slide 1")
            slide_path = extract_dir / 'ppt' / 'slides' / 'slide1.xml'
        
        # Parse slide XML
        tree = ET.parse(slide_path)
        root = tree.getroot()
        
        # Ensure South Plains branding elements are present
        self._ensure_branding_elements(root)
        
        # Update title
        if 'title' in content_data:
            self._update_slide_title(root, content_data['title'])
        
        # Update subtitle
        if 'subtitle' in content_data:
            self._update_slide_subtitle(root, content_data['subtitle'])
        
        # Update chart if present
        if 'chart_data' in content_data:
            self._update_slide_chart(root, extract_dir, slide_num, content_data['chart_data'])
        
        # Update highlights/content
        if 'highlights' in content_data:
            self._update_slide_highlights(root, content_data['highlights'])
        elif 'content' in content_data:
            self._update_slide_content(root, content_data['content'])
        
        # Save updated XML
        tree.write(slide_path, encoding='UTF-8', xml_declaration=True)
    
    def _update_slide_title(self, root: ET.Element, title: str):
        """Update slide title preserving formatting."""
        # Find title shape (usually first text shape)
        for shape in root.findall('.//p:sp', NAMESPACES):
            text_body = shape.find('.//a:p', NAMESPACES)
            if text_body is not None:
                # Check if this is likely the title (larger font size)
                run = text_body.find('.//a:r', NAMESPACES)
                if run is not None:
                    rPr = run.find('a:rPr', NAMESPACES)
                    if rPr is not None and rPr.get('sz'):
                        size = int(rPr.get('sz', '0'))
                        if size >= 3000:  # 30pt or larger
                            # Update title text
                            text_elem = run.find('a:t', NAMESPACES)
                            if text_elem is not None:
                                text_elem.text = title
                                return
    
    def _update_slide_subtitle(self, root: ET.Element, subtitle: str):
        """Update slide subtitle."""
        # Find subtitle (second text shape with reasonable size)
        title_found = False
        for shape in root.findall('.//p:sp', NAMESPACES):
            paragraphs = shape.findall('.//a:p', NAMESPACES)
            for para in paragraphs:
                run = para.find('.//a:r', NAMESPACES)
                if run is not None:
                    rPr = run.find('a:rPr', NAMESPACES)
                    if rPr is not None and rPr.get('sz'):
                        size = int(rPr.get('sz', '0'))
                        if size >= 3000 and not title_found:
                            title_found = True
                        elif title_found and 1000 <= size < 3000:
                            text_elem = run.find('a:t', NAMESPACES)
                            if text_elem is not None:
                                text_elem.text = subtitle
                                return
    
    def _update_slide_chart(self, root: ET.Element, extract_dir: Path, slide_num: int, chart_data: Dict):
        """Update chart data in slide."""
        # Find chart reference
        for graphic_frame in root.findall('.//p:graphicFrame', NAMESPACES):
            chart_elem = graphic_frame.find('.//c:chart', NAMESPACES)
            if chart_elem is not None:
                rel_id = chart_elem.get('{' + NAMESPACES['r'] + '}id')
                if rel_id:
                    # Update the chart file
                    self._update_chart_file(extract_dir, slide_num, rel_id, chart_data)
                    return
    
    def _update_chart_file(self, extract_dir: Path, slide_num: int, rel_id: str, chart_data: Dict):
        """Update the actual chart XML file."""
        # Get chart path from relationships
        rels_path = extract_dir / 'ppt' / 'slides' / '_rels' / f'slide{slide_num}.xml.rels'
        if rels_path.exists():
            rels_tree = ET.parse(rels_path)
            for rel in rels_tree.findall('.//{http://schemas.openxmlformats.org/package/2006/relationships}Relationship'):
                if rel.get('Id') == rel_id:
                    chart_path = rel.get('Target')
                    if chart_path.startswith('../'):
                        chart_path = chart_path[3:]
                    
                    full_chart_path = extract_dir / 'ppt' / chart_path
                    if full_chart_path.exists():
                        self._modify_chart_data(full_chart_path, chart_data)
    
    def _modify_chart_data(self, chart_path: Path, chart_data: Dict):
        """Modify chart data values."""
        tree = ET.parse(chart_path)
        root = tree.getroot()
        
        # Update categories
        if 'categories' in chart_data:
            cat_cache = root.find('.//c:cat//c:strRef//c:strCache', NAMESPACES)
            if cat_cache is not None:
                # Clear existing categories
                for pt in cat_cache.findall('c:pt', NAMESPACES):
                    cat_cache.remove(pt)
                
                # Add new categories
                for idx, cat in enumerate(chart_data['categories']):
                    pt_elem = ET.SubElement(cat_cache, '{' + NAMESPACES['c'] + '}pt')
                    pt_elem.set('idx', str(idx))
                    v_elem = ET.SubElement(pt_elem, '{' + NAMESPACES['c'] + '}v')
                    v_elem.text = cat
        
        # Update series values
        if 'series' in chart_data:
            all_series = root.findall('.//c:ser', NAMESPACES)
            for ser_idx, series_data in enumerate(chart_data['series']):
                if ser_idx < len(all_series):
                    ser_elem = all_series[ser_idx]
                    
                    # Update series name if provided
                    if 'name' in series_data:
                        tx_elem = ser_elem.find('.//c:tx//c:v', NAMESPACES)
                        if tx_elem is not None:
                            tx_elem.text = series_data['name']
                    
                    # Update values
                    val_cache = ser_elem.find('.//c:val//c:numRef//c:numCache', NAMESPACES)
                    if val_cache is not None:
                        # Clear existing values
                        for pt in val_cache.findall('c:pt', NAMESPACES):
                            val_cache.remove(pt)
                        
                        # Add new values
                        for idx, value in enumerate(series_data['values']):
                            pt_elem = ET.SubElement(val_cache, '{' + NAMESPACES['c'] + '}pt')
                            pt_elem.set('idx', str(idx))
                            v_elem = ET.SubElement(pt_elem, '{' + NAMESPACES['c'] + '}v')
                            v_elem.text = str(value)
        
        # Save updated chart
        tree.write(chart_path, encoding='UTF-8', xml_declaration=True)
    
    def _update_slide_highlights(self, root: ET.Element, highlights: List[str]):
        """Update highlights section in slide."""
        # Find text box containing "Highlights"
        for shape in root.findall('.//p:sp', NAMESPACES):
            text_body = shape.find('.//p:txBody', NAMESPACES)
            if text_body is not None:
                # Check if this contains "Highlights"
                first_para = text_body.find('.//a:p', NAMESPACES)
                if first_para is not None:
                    text = ''.join(first_para.itertext())
                    if 'highlight' in text.lower():
                        # Clear existing paragraphs except title
                        paragraphs = text_body.findall('a:p', NAMESPACES)
                        for i, para in enumerate(paragraphs):
                            if i > 0:  # Keep title paragraph
                                text_body.remove(para)
                        
                        # Add new highlights
                        for highlight in highlights[1:]:  # Skip first as it's the title
                            new_para = ET.SubElement(text_body, '{' + NAMESPACES['a'] + '}p')
                            
                            # Add bullet properties
                            pPr = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}pPr')
                            pPr.set('lvl', '0')
                            buChar = ET.SubElement(pPr, '{' + NAMESPACES['a'] + '}buChar')
                            buChar.set('char', '•')
                            
                            # Add text run
                            run = ET.SubElement(new_para, '{' + NAMESPACES['a'] + '}r')
                            text_elem = ET.SubElement(run, '{' + NAMESPACES['a'] + '}t')
                            text_elem.text = highlight
                        
                        return
    
    def _update_slide_content(self, root: ET.Element, content: str):
        """Update generic slide content."""
        # Find main content text box
        for shape in root.findall('.//p:sp', NAMESPACES):
            text_body = shape.find('.//p:txBody', NAMESPACES)
            if text_body is not None:
                # Clear existing content
                for para in text_body.findall('a:p', NAMESPACES):
                    text_body.remove(para)
                
                # Add new content as paragraphs
                for line in content.split('\n'):
                    if line.strip():
                        para = ET.SubElement(text_body, '{' + NAMESPACES['a'] + '}p')
                        run = ET.SubElement(para, '{' + NAMESPACES['a'] + '}r')
                        text_elem = ET.SubElement(run, '{' + NAMESPACES['a'] + '}t')
                        text_elem.text = line.strip()
    
    def _create_pptx(self, extract_dir: Path, output_path: Path):
        """Create PowerPoint file from extracted directory."""
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = str(file_path.relative_to(extract_dir))
                    zipf.write(file_path, arcname)
    
    def _upload_to_s3(self, file_path: Path, slide_type: str) -> str:
        """Upload generated file to S3 and return URL."""
        output_bucket = os.environ.get('OUTPUT_BUCKET', 'scribbe-ai-dev-output')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        s3_key = f'generated/{slide_type}_{timestamp}.pptx'
        
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
            ExpiresIn=3600  # 1 hour
        )
        
        return url
    
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
            self._add_page_number(sp_tree, '26')  # Default page number
            
        # Add black divider line under title if missing
        self._add_title_divider(sp_tree)
    
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

def lambda_handler(event, context):
    """AWS Lambda handler function."""
    try:
        body = json.loads(event.get('body', '{}'))
        prompt = body.get('prompt', '')
        slide_type = body.get('slide_type', 'generic')
        
        if not prompt:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Prompt is required'})
            }
        
        # Generate presentation
        generator = SouthPlainsGenerator()
        s3_url = generator.generate_from_prompt(prompt, slide_type)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': True,
                'download_url': s3_url,
                'slide_type': slide_type
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
    generator = SouthPlainsGenerator()
    
    # Test loan portfolio
    loan_prompt = "Create a loan portfolio slide showing quarters 2Q19 through 2Q20 with values $137, $141, $167, $189, $249 million. Highlight the growth in Q2."
    result = generator.generate_from_prompt(loan_prompt, 'loan_portfolio')
    print(f"Generated loan portfolio: {result}")
    
    # Test noninterest income
    income_prompt = "Generate noninterest income slide for 2Q19 to 2Q20 showing $13.7, $14.1, $16.7, $18.9, $24.9 million with percentages 36%, 35%, 37%, 38%, 45%"
    result = generator.generate_from_prompt(income_prompt, 'noninterest_income')
    print(f"Generated noninterest income: {result}")