"""
AI-Powered Presentation Generator - First Slide with Content Modification
Returns only the first slide from template with modified content
"""

import json
import boto3
from typing import Dict, Any
import logging
import io
import os
import zipfile
import re
import xml.etree.ElementTree as ET

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3 = boto3.client('s3')

class AIPresentationGenerator:
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-1')
        self.model_id = 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0'
        self.documents_bucket = os.environ.get('DOCUMENTS_BUCKET', 'scribbe-ai-dev-documents')
        self.template_key = 'PUBLIC IP South Plains (1).pptx'
    
    def generate_presentation(self, instructions: str) -> bytes:
        """Generate presentation - return first slide only with loan portfolio content"""
        
        try:
            # Download template from S3
            logger.info(f"Downloading template: {self.template_key}")
            template_response = s3.get_object(Bucket=self.documents_bucket, Key=self.template_key)
            template_content = template_response['Body'].read()
            
            logger.info(f"Successfully downloaded template, size: {len(template_content)} bytes")
            
            # Process the template to keep only first slide and modify content
            modified_content = self._process_template(template_content, instructions)
            
            return modified_content
            
        except Exception as e:
            logger.error(f"Error processing template: {e}", exc_info=True)
            # Return original template as fallback
            return template_content
    
    def _process_template(self, template_bytes: bytes, instructions: str) -> bytes:
        """Keep only the first slide and modify its content"""
        
        input_buffer = io.BytesIO(template_bytes)
        output_buffer = io.BytesIO()
        
        try:
            with zipfile.ZipFile(input_buffer, 'r') as zip_in:
                # List all files
                file_list = zip_in.namelist()
                logger.info(f"Template contains {len(file_list)} files")
                
                with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                    for file_name in file_list:
                        # Skip slides other than slide1
                        if 'ppt/slides/slide' in file_name and file_name.endswith('.xml'):
                            if 'slide1.xml' not in file_name:
                                logger.info(f"Skipping slide: {file_name}")
                                continue
                        
                        # Skip slide relationships for other slides
                        if 'ppt/slides/_rels/slide' in file_name:
                            if 'slide1.xml.rels' not in file_name:
                                logger.info(f"Skipping slide rels: {file_name}")
                                continue
                        
                        # Read the file content
                        file_content = zip_in.read(file_name)
                        
                        # Modify presentation.xml to reference only slide1
                        if file_name == 'ppt/presentation.xml':
                            file_content = self._modify_presentation_xml_simple(file_content)
                        
                        # Modify slide1.xml content for loan portfolio
                        elif file_name == 'ppt/slides/slide1.xml':
                            file_content = self._modify_slide1_content(file_content, instructions)
                        
                        # Write to output
                        zip_out.writestr(file_name, file_content)
            
            output_buffer.seek(0)
            result = output_buffer.getvalue()
            logger.info(f"Generated presentation with modified first slide, size: {len(result)} bytes")
            return result
            
        except Exception as e:
            logger.error(f"Error processing template ZIP: {e}")
            return template_bytes
    
    def _modify_slide1_content(self, content: bytes, instructions: str) -> bytes:
        """Modify slide1.xml to add loan portfolio content"""
        try:
            # Parse XML
            root = ET.fromstring(content)
            
            # Register namespaces
            ns = {
                'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
                'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
                'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            }
            
            # Find all text elements
            text_elements = root.findall('.//a:t', ns)
            
            # Counter for text replacements
            replacement_count = 0
            
            for elem in text_elements:
                current_text = elem.text or ""
                logger.info(f"Found text element: {current_text[:50]}...")
                
                # First major text element - make it title
                if replacement_count == 0 and len(current_text) > 5:
                    elem.text = "Loan Portfolio"
                    replacement_count += 1
                    logger.info("Replaced title with 'Loan Portfolio'")
                
                # Second major text element - subtitle
                elif replacement_count == 1 and len(current_text) > 5:
                    elem.text = "Total Loans Held for Investment ($ in Millions)"
                    replacement_count += 2
                    logger.info("Replaced subtitle")
                
                # Look for sections we can replace with content
                elif "south plains" in current_text.lower() and "financial" in current_text.lower():
                    # Keep company name
                    continue
                
                # Replace any large text blocks with our content
                elif len(current_text) > 50 and replacement_count < 4:
                    if replacement_count == 2:
                        elem.text = "2Q'20 HIGHLIGHTS: • Total loan increase of $229.9M vs. 1Q'20 • Growth from $215.3M PPP loans and $34.7M seasonal agriculture loans • Over 2,000 PPP loans closed • 2Q'20 yield of 5.26%"
                        replacement_count += 1
                        logger.info("Added highlights content")
                    elif replacement_count == 3:
                        elem.text = "Loan Balances: $1,936M (2Q'19), $1,963M (3Q'19), $2,144M (4Q'19), $2,109M (1Q'20), $2,332M (2Q'20)"
                        replacement_count += 1
                        logger.info("Added loan balances")
            
            # If we didn't replace enough content, try to find empty text elements
            if replacement_count < 3:
                # Find shapes with text frames
                shapes = root.findall('.//p:sp', ns)
                for shape in shapes:
                    text_body = shape.find('.//p:txBody', ns)
                    if text_body is not None:
                        paragraphs = text_body.findall('.//a:p', ns)
                        for p in paragraphs[:1]:  # Only modify first paragraph
                            # Clear existing runs
                            for run in p.findall('.//a:r', ns):
                                p.remove(run)
                            
                            # Add new run with our content
                            if replacement_count == 0:
                                new_run = ET.SubElement(p, '{http://schemas.openxmlformats.org/drawingml/2006/main}r')
                                new_text = ET.SubElement(new_run, '{http://schemas.openxmlformats.org/drawingml/2006/main}t')
                                new_text.text = "Loan Portfolio"
                                replacement_count = 1
                                break
            
            # Convert back to bytes
            return ET.tostring(root, encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            logger.error(f"Error modifying slide1.xml: {e}")
            return content
    
    def _modify_presentation_xml_simple(self, content: bytes) -> bytes:
        """Simple regex-based modification of presentation.xml"""
        try:
            content_str = content.decode('utf-8')
            
            # Pattern to match slide ID list
            pattern = r'<p:sldIdLst>.*?</p:sldIdLst>'
            match = re.search(pattern, content_str, re.DOTALL)
            
            if match:
                slide_list = match.group(0)
                
                # Extract just the first slide ID
                first_slide_pattern = r'<p:sldId[^>]*?r:id="rId\d+"[^>]*?/>'
                first_slide_match = re.search(first_slide_pattern, slide_list)
                
                if first_slide_match:
                    # Replace the entire slide list with just the first slide
                    new_slide_list = f'<p:sldIdLst>{first_slide_match.group(0)}</p:sldIdLst>'
                    content_str = content_str.replace(match.group(0), new_slide_list)
                    logger.info("Modified presentation.xml to include only first slide")
            
            return content_str.encode('utf-8')
            
        except Exception as e:
            logger.error(f"Error modifying presentation.xml: {e}")
            return content

    def analyze_presentation_request(self, instructions: str) -> Dict[str, Any]:
        """Simple analysis - returns loan portfolio structure"""
        return {
            "presentation_type": "loan_portfolio",
            "title": "Loan Portfolio Analysis",
            "sections": []
        }
    
    def _get_loan_portfolio_structure(self) -> Dict[str, Any]:
        """Loan portfolio presentation structure"""
        return {
            "presentation_type": "loan_portfolio",
            "title": "Loan Portfolio Analysis",
            "sections": []
        }
    
    def _get_default_structure(self, instructions: str) -> Dict[str, Any]:
        """Default structure"""
        return self._get_loan_portfolio_structure()