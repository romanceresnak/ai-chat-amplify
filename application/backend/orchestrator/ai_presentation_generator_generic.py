"""
AI-Powered Generic Presentation Generator
Generates presentations dynamically based on instructions for any slide number
"""

import json
import boto3
from typing import Dict, List, Any, Optional, Tuple
import logging
import io
import re
import os
import base64

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3 = boto3.client('s3')

# Global variables for python-pptx availability
PPTX_AVAILABLE = False
Presentation = None
Inches = None
Pt = None
RGBColor = None
PP_ALIGN = None
ChartData = None
CategoryChartData = None
XL_CHART_TYPE = None
XL_LEGEND_POSITION = None
XL_LABEL_POSITION = None
XL_TICK_MARK = None
MSO_THEME_COLOR = None
MSO_SHAPE = None

class GenericPresentationGenerator:
    def __init__(self):
        self.bedrock_runtime = boto3.client('bedrock-runtime', region_name='eu-west-1')
        self.model_id = 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0'
        self.documents_bucket = os.environ.get('DOCUMENTS_BUCKET', 'scribbe-ai-dev-documents')
        self._initialize_pptx()
    
    def _initialize_pptx(self):
        """Initialize python-pptx imports on demand"""
        global PPTX_AVAILABLE, Presentation, Inches, Pt, RGBColor, PP_ALIGN
        global ChartData, CategoryChartData, XL_CHART_TYPE, XL_LEGEND_POSITION
        global XL_LABEL_POSITION, XL_TICK_MARK, MSO_THEME_COLOR, MSO_SHAPE
        
        if PPTX_AVAILABLE:
            return
        
        try:
            import sys
            import os
            
            # Add Lambda layer to path
            layer_paths = [
                "/opt/python/lib/python3.11/site-packages",
                "/opt/python",
                "/var/runtime"
            ]
            
            for path in layer_paths:
                if os.path.exists(path) and path not in sys.path:
                    sys.path.insert(0, path)
                    logger.info(f"Added {path} to sys.path")
            
            # Try importing python-pptx
            logger.info("Attempting to import python-pptx...")
            
            from pptx import Presentation as _Presentation
            from pptx.util import Inches as _Inches, Pt as _Pt
            from pptx.dml.color import RGBColor as _RGBColor
            from pptx.enum.text import PP_ALIGN as _PP_ALIGN
            from pptx.chart.data import ChartData as _ChartData
            from pptx.chart.data import CategoryChartData as _CategoryChartData
            from pptx.enum.chart import XL_CHART_TYPE as _XL_CHART_TYPE
            from pptx.enum.chart import XL_LEGEND_POSITION as _XL_LEGEND_POSITION
            from pptx.enum.chart import XL_LABEL_POSITION as _XL_LABEL_POSITION
            from pptx.enum.chart import XL_TICK_MARK as _XL_TICK_MARK
            from pptx.enum.dml import MSO_THEME_COLOR as _MSO_THEME_COLOR
            from pptx.enum.shapes import MSO_SHAPE as _MSO_SHAPE
            
            # Set global variables
            Presentation = _Presentation
            Inches = _Inches
            Pt = _Pt
            RGBColor = _RGBColor
            PP_ALIGN = _PP_ALIGN
            ChartData = _ChartData
            CategoryChartData = _CategoryChartData
            XL_CHART_TYPE = _XL_CHART_TYPE
            XL_LEGEND_POSITION = _XL_LEGEND_POSITION
            XL_LABEL_POSITION = _XL_LABEL_POSITION
            XL_TICK_MARK = _XL_TICK_MARK
            MSO_THEME_COLOR = _MSO_THEME_COLOR
            MSO_SHAPE = _MSO_SHAPE
            
            PPTX_AVAILABLE = True
            logger.info("✅ python-pptx initialized successfully")
            
        except ImportError as e:
            logger.error(f"❌ python-pptx not available: {e}")
            PPTX_AVAILABLE = False
    
    def generate_presentation(self, instructions: str) -> bytes:
        """Generate presentation based on natural language instructions"""
        
        logger.info(f"Generating presentation for: {instructions[:100]}...")
        
        # Parse the instructions to extract slide information
        slide_info = self._parse_slide_instructions(instructions)
        logger.info(f"Parsed slide info: {slide_info}")
        
        try:
            if PPTX_AVAILABLE:
                logger.info("Using python-pptx for generation")
                return self._generate_with_pptx(slide_info, instructions)
            else:
                logger.info("Falling back to XML generation")
                return self._generate_with_xml(slide_info, instructions)
        except Exception as e:
            logger.error(f"Error generating presentation: {e}")
            return self._generate_fallback_presentation(instructions)
    
    def _parse_slide_instructions(self, instructions: str) -> Dict[str, Any]:
        """Parse instructions to extract slide number and requirements"""
        
        # Extract slide number
        slide_number_match = re.search(r'(?:slide|Slide)\s*(\d+)', instructions, re.IGNORECASE)
        slide_number = int(slide_number_match.group(1)) if slide_number_match else None
        
        # Extract chart type mentions
        chart_types = []
        if re.search(r'bar\s*(?:and\s*)?line|combo\s*chart', instructions, re.IGNORECASE):
            chart_types.append('combo')
        elif re.search(r'donut|doughnut', instructions, re.IGNORECASE):
            chart_types.append('donut')
        elif re.search(r'bar\s*chart', instructions, re.IGNORECASE):
            chart_types.append('bar')
        elif re.search(r'line\s*chart', instructions, re.IGNORECASE):
            chart_types.append('line')
        elif re.search(r'pie\s*chart', instructions, re.IGNORECASE):
            chart_types.append('pie')
        
        # Extract title
        title_match = re.search(r'title[:\s]+([^\.]+)', instructions, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else f"Slide {slide_number}" if slide_number else "Presentation"
        
        # Use AI to understand the full content requirements
        ai_analysis = self._analyze_with_ai(instructions)
        
        return {
            'slide_number': slide_number,
            'title': title,
            'chart_types': chart_types,
            'instructions': instructions,
            'ai_analysis': ai_analysis
        }
    
    def _analyze_with_ai(self, instructions: str) -> Dict[str, Any]:
        """Use Claude to analyze and structure the slide requirements"""
        
        prompt = f"""
        Analyze the following slide instructions and extract structured information:
        
        Instructions: {instructions}
        
        Please provide a JSON response with:
        1. title: The main title of the slide
        2. subtitle: Any subtitle if mentioned
        3. data_series: Array of objects with label and value for chart data
        4. chart_config: Object with chart type, colors, etc if charts are mentioned
        5. center_text: Text to display in center of donut/pie charts
        6. text_content: Array of bullet points or text content
        7. highlights_section: Object with title and items for highlights/breakdown sections
        8. footer_text: Footer text if mentioned
        9. logo_position: Where to place logo if mentioned
        10. color_scheme: Suggested colors based on context
        11. instructions: The original instructions for reference
        
        For data_series, format as: [{{"label": "Category Name", "value": 28}}, ...]
        For highlights_section: {{"title": "2Q'20 Highlights", "items": ["item1", "item2", ...]}}
        
        Return only valid JSON without markdown formatting.
        """
        
        try:
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'messages': [{
                        'role': 'user',
                        'content': prompt
                    }],
                    'max_tokens': 2000,
                    'temperature': 0
                })
            )
            
            response_body = json.loads(response['body'].read())
            content = response_body['content'][0]['text']
            
            # Parse JSON from response
            return json.loads(content)
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {e}")
            return self._parse_manually(instructions)
    
    def _parse_manually(self, instructions: str) -> Dict[str, Any]:
        """Manual parsing when AI is not available"""
        
        # Extract main donut chart data
        donut_match = re.search(r'composition\s*\(([^)]+)\)', instructions)
        data_series = []
        if donut_match:
            data_text = donut_match.group(1)
            # Parse each item in format "Category X%"
            items = re.split(r',\s*', data_text)
            for item in items:
                match = re.match(r'(.+?)\s+(\d+)%', item)
                if match:
                    data_series.append({
                        'label': match.group(1).strip(),
                        'value': int(match.group(2))
                    })
        
        # Extract center text more accurately
        center_match = re.search(r'center text[^:]*reading\s+([^,]+)', instructions, re.IGNORECASE)
        center_text = center_match.group(1).strip() if center_match else ''
        center_text = center_text.replace(':', ':\n')  # Add line break after colon
        
        # Extract highlights with better parsing
        highlights_items = []
        highlights_match = re.search(r'Highlights["\s]+listing(.+?)(?:,\s*with|,\s*and)', instructions, re.IGNORECASE | re.DOTALL)
        if highlights_match:
            text = highlights_match.group(1)
            # Parse breakdown patterns: "Category (item1 X%, item2 Y%)"
            pattern = r'([^(]+?)\s*\(([^)]+)\)'
            for match in re.finditer(pattern, text):
                category = match.group(1).strip().rstrip(' for')
                items_text = match.group(2)
                # Parse items within parentheses
                items = []
                item_pattern = r'([^0-9]+?)\s+(\d+)%'
                for item_match in re.finditer(item_pattern, items_text):
                    items.append(f"{item_match.group(1).strip()} {item_match.group(2)}%")
                
                if items:
                    highlights_items.append({
                        'category': category,
                        'items': items
                    })
        
        # Extract footer more precisely
        footer_match = re.search(r'footer\s+(?:bar\s+)?with\s+([^,]+)', instructions, re.IGNORECASE)
        footer_text = footer_match.group(1).strip() if footer_match else 'Generated Presentation'
        
        # Extract title
        title_match = re.search(r'titled?\s+"([^"]+)"', instructions, re.IGNORECASE)
        title = title_match.group(1) if title_match else 'Loan Portfolio'
        
        return {
            'title': title,
            'data_series': data_series,
            'center_text': center_text,
            'highlights_section': {
                'title': "2Q'20 Highlights",
                'items': highlights_items
            } if highlights_items else None,
            'footer_text': footer_text,
            'logo_position': 'top right' if 'logo in top right' in instructions.lower() else None,
            'instructions': instructions
        }
    
    def _generate_with_pptx(self, slide_info: Dict, instructions: str) -> bytes:
        """Generate presentation using python-pptx"""
        
        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)
        
        # Create slide
        slide = self._create_dynamic_slide(prs, slide_info)
        
        # Save to bytes
        output = io.BytesIO()
        prs.save(output)
        output.seek(0)
        
        return output.read()
    
    def _create_dynamic_slide(self, prs, slide_info: Dict):
        """Create a slide dynamically based on parsed information"""
        
        # Use blank layout for maximum flexibility
        slide_layout = prs.slide_layouts[6] if len(prs.slide_layouts) > 6 else prs.slide_layouts[-1]
        slide = prs.slides.add_slide(slide_layout)
        
        ai_analysis = slide_info.get('ai_analysis', {})
        
        # Add title
        if ai_analysis.get('title') or slide_info.get('title'):
            title_text = ai_analysis.get('title', slide_info.get('title', ''))
            title_shape = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(0.8))
            title_frame = title_shape.text_frame
            title_frame.text = title_text
            title_para = title_frame.paragraphs[0]
            title_para.font.size = Pt(32)
            title_para.font.bold = True
            title_para.font.color.rgb = RGBColor(31, 73, 125)
        
        # Add subtitle
        if ai_analysis.get('subtitle'):
            subtitle_shape = slide.shapes.add_textbox(Inches(0.5), Inches(1.0), Inches(12), Inches(0.5))
            subtitle_frame = subtitle_shape.text_frame
            subtitle_frame.text = ai_analysis['subtitle']
            subtitle_para = subtitle_frame.paragraphs[0]
            subtitle_para.font.size = Pt(18)
            subtitle_para.font.color.rgb = RGBColor(89, 89, 89)
        
        # Current Y position tracker
        current_y = Inches(1.8)
        
        # Add charts if specified
        chart_type = None
        if slide_info.get('chart_types') and ai_analysis.get('data_series'):
            chart_type = slide_info['chart_types'][0]
            current_y = self._add_dynamic_chart(slide, chart_type, ai_analysis, current_y)
        
        # Add text content or highlights section
        if ai_analysis.get('highlights_section'):
            # Add highlights in right column for donut charts
            if chart_type == 'donut':
                highlights_x = Inches(7)
                highlights_y = Inches(1.8)
            else:
                highlights_x = Inches(0.5)
                highlights_y = current_y
            
            self._add_highlights_section(slide, ai_analysis['highlights_section'], highlights_x, highlights_y)
        elif ai_analysis.get('text_content'):
            self._add_text_content(slide, ai_analysis['text_content'], Inches(0.5), current_y)
        
        # Add logo if specified
        if ai_analysis.get('logo_position') == 'top right':
            self._add_logo_placeholder(slide)
        
        # Add footer with custom text
        footer_text = ai_analysis.get('footer_text', 'Generated Presentation')
        self._add_footer(slide, footer_text)
        
        return slide
    
    def _add_dynamic_chart(self, slide, chart_type: str, ai_analysis: Dict, y_position: float) -> float:
        """Add a chart dynamically based on type and data"""
        
        data_series = ai_analysis.get('data_series', [])
        if not data_series:
            return y_position
        
        # Prepare chart data
        chart_data = CategoryChartData()
        
        # Extract categories and values
        if isinstance(data_series[0], dict):
            categories = [item.get('label', f'Item {i+1}') for i, item in enumerate(data_series)]
            values = [item.get('value', 0) for item in data_series]
        else:
            # Fallback for simple data
            categories = [f'Item {i+1}' for i in range(len(data_series))]
            values = data_series
        
        chart_data.categories = categories
        chart_data.add_series('Portfolio', values)
        
        # Map chart type to XL_CHART_TYPE
        chart_type_map = {
            'bar': XL_CHART_TYPE.COLUMN_CLUSTERED,
            'line': XL_CHART_TYPE.LINE,
            'pie': XL_CHART_TYPE.PIE,
            'donut': XL_CHART_TYPE.DOUGHNUT,
            'combo': XL_CHART_TYPE.COLUMN_CLUSTERED  # Will modify later
        }
        
        xl_chart_type = chart_type_map.get(chart_type, XL_CHART_TYPE.COLUMN_CLUSTERED)
        
        # Adjust positioning for donut charts to leave room for highlights
        if chart_type == 'donut':
            x, y, cx, cy = Inches(0.5), y_position, Inches(6), Inches(4.5)
        else:
            x, y, cx, cy = Inches(0.5), y_position, Inches(7), Inches(4)
            
        chart = slide.shapes.add_chart(xl_chart_type, x, y, cx, cy, chart_data).chart
        
        # Style chart
        chart.has_title = False
        chart.has_legend = True
        chart.legend.position = XL_LEGEND_POSITION.BOTTOM
        chart.legend.font.size = Pt(10)
        
        # Special handling for donut charts
        if chart_type == 'donut':
            # Add center text if specified
            center_text = ai_analysis.get('center_text', '')
            if center_text:
                # Calculate center position
                center_x = x + cx/2 - Inches(1.5)
                center_y = y + cy/2 - Inches(0.5)
                
                center_shape = slide.shapes.add_textbox(center_x, center_y, Inches(3), Inches(1))
                center_frame = center_shape.text_frame
                center_frame.clear()
                
                for i, line in enumerate(center_text.split('\n')):
                    if i == 0:
                        p = center_frame.paragraphs[0]
                    else:
                        p = center_frame.add_paragraph()
                    p.text = line
                    p.alignment = PP_ALIGN.CENTER
                    p.font.bold = True
                    p.font.size = Pt(14) if i == 0 else Pt(16)
                    p.font.color.rgb = RGBColor(31, 73, 125)
        
        # Apply colors - use red accents if mentioned
        if 'red' in ai_analysis.get('instructions', '').lower():
            # Red color palette for South Plains Financial
            red_colors = [
                RGBColor(192, 80, 77),   # Primary red
                RGBColor(217, 83, 79),   # Lighter red
                RGBColor(172, 60, 57),   # Darker red
                RGBColor(237, 103, 99),  # Light red
                RGBColor(152, 40, 37),   # Deep red
                RGBColor(255, 123, 119), # Pale red
                RGBColor(132, 20, 17),   # Very dark red
            ]
            
            for i, series in enumerate(chart.series):
                if i < len(red_colors):
                    fill = series.format.fill
                    fill.solid()
                    fill.fore_color.rgb = red_colors[i]
        
        return y_position + cy + Inches(0.5)
    
    def _add_text_content(self, slide, text_content: List[str], x: float, y: float):
        """Add text content to slide"""
        
        text_shape = slide.shapes.add_textbox(x, y, Inches(12), Inches(5))
        text_frame = text_shape.text_frame
        text_frame.word_wrap = True
        
        for i, text in enumerate(text_content):
            if i == 0:
                p = text_frame.paragraphs[0]
            else:
                p = text_frame.add_paragraph()
            
            # Add bullet if it doesn't start with one
            if not text.strip().startswith('•'):
                p.text = f"• {text}"
            else:
                p.text = text
            
            p.font.size = Pt(12)
            p.font.color.rgb = RGBColor(55, 65, 81)
            p.space_after = Pt(6)
    
    def _add_footer(self, slide, footer_text="Generated Presentation"):
        """Add footer to slide with gray bar"""
        
        footer_y = Inches(6.8)
        
        # Add gray footer bar
        footer_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), footer_y,
            Inches(13.333), Inches(0.7)
        )
        footer_bar.fill.solid()
        footer_bar.fill.fore_color.rgb = RGBColor(240, 240, 240)
        footer_bar.line.fill.background()
        
        # Send to back
        slide.shapes._spTree.remove(footer_bar.element)
        slide.shapes._spTree.insert(2, footer_bar.element)
        
        # Add footer text
        footer_shape = slide.shapes.add_textbox(Inches(0), footer_y + Inches(0.1), Inches(13.333), Inches(0.5))
        footer_frame = footer_shape.text_frame
        footer_frame.text = footer_text
        footer_para = footer_frame.paragraphs[0]
        footer_para.alignment = PP_ALIGN.CENTER
        footer_para.font.size = Pt(11)
        footer_para.font.color.rgb = RGBColor(100, 100, 100)
    
    def _add_logo_placeholder(self, slide):
        """Add logo placeholder in top right"""
        
        logo_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(11.3), Inches(0.3),
            Inches(1.7), Inches(0.9)
        )
        logo_shape.fill.solid()
        logo_shape.fill.fore_color.rgb = RGBColor(250, 250, 250)
        logo_shape.line.color.rgb = RGBColor(217, 217, 217)
        logo_shape.line.width = Pt(0.5)
        
        logo_text_frame = logo_shape.text_frame
        logo_text_frame.clear()
        logo_text_frame.margin_all = Inches(0.1)
        
        logo_p = logo_text_frame.add_paragraph()
        logo_p.text = "[LOGO]"
        logo_p.alignment = PP_ALIGN.CENTER
        logo_text_frame.vertical_anchor = 1  # Middle
        logo_p.font.size = Pt(12)
        logo_p.font.color.rgb = RGBColor(180, 180, 180)
    
    def _add_highlights_section(self, slide, highlights_data: Dict, x: float, y: float):
        """Add highlights section with title and breakdown items"""
        
        # Add background box
        bg_shape = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            x - Inches(0.1), y - Inches(0.1),
            Inches(5.5), Inches(4.5)
        )
        bg_shape.fill.solid()
        bg_shape.fill.fore_color.rgb = RGBColor(250, 250, 250)
        bg_shape.line.color.rgb = RGBColor(220, 220, 220)
        bg_shape.line.width = Pt(0.5)
        
        # Send to back
        slide.shapes._spTree.remove(bg_shape.element)
        slide.shapes._spTree.insert(2, bg_shape.element)
        
        # Add title
        title_shape = slide.shapes.add_textbox(x, y, Inches(5), Inches(0.5))
        title_frame = title_shape.text_frame
        title_frame.clear()
        
        title_p = title_frame.add_paragraph()
        title_p.text = highlights_data.get('title', 'Highlights')
        title_p.font.size = Pt(18)
        title_p.font.bold = True
        title_p.font.color.rgb = RGBColor(192, 80, 77)  # Red accent
        
        # Add items
        items = highlights_data.get('items', [])
        content_shape = slide.shapes.add_textbox(x, y + Inches(0.6), Inches(5), Inches(3.5))
        content_frame = content_shape.text_frame
        content_frame.clear()
        content_frame.word_wrap = True
        
        for i, item in enumerate(items):
            if i == 0:
                p = content_frame.paragraphs[0]
            else:
                p = content_frame.add_paragraph()
            
            # Check if item is a category with sub-items
            if isinstance(item, dict):
                # Category header
                p.text = item.get('category', '')
                p.font.size = Pt(12)
                p.font.bold = True
                p.font.color.rgb = RGBColor(31, 73, 125)
                p.space_after = Pt(3)
                
                # Sub-items
                for sub_item in item.get('items', []):
                    sub_p = content_frame.add_paragraph()
                    sub_p.text = f"  • {sub_item}"
                    sub_p.font.size = Pt(11)
                    sub_p.font.color.rgb = RGBColor(55, 65, 81)
                    sub_p.space_after = Pt(2)
            else:
                # Simple bullet point
                p.text = f"• {item}"
                p.font.size = Pt(11)
                p.font.color.rgb = RGBColor(55, 65, 81)
                p.space_after = Pt(6)
    
    def _generate_with_xml(self, slide_info: Dict, instructions: str) -> bytes:
        """Generate presentation using XML when python-pptx is not available"""
        
        # This is a simplified version - in production, you'd generate proper OpenXML
        logger.info("Generating presentation with XML fallback")
        
        # For now, return a minimal valid PPTX structure
        # In a real implementation, this would create proper OpenXML
        return self._generate_fallback_presentation(instructions)
    
    def _generate_fallback_presentation(self, instructions: str) -> bytes:
        """Generate a basic fallback presentation"""
        
        # Try to use a template from S3 if available
        try:
            template_key = "templates/blank_template.pptx"
            response = s3.get_object(Bucket=self.documents_bucket, Key=template_key)
            logger.info(f"Using blank template from S3")
            return response['Body'].read()
        except:
            # Return a minimal PPTX file
            logger.error("No template available, returning minimal PPTX")
            # This would contain minimal valid PPTX structure
            return b"PK..."  # Abbreviated for brevity