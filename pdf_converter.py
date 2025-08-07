"""
PDF conversion utilities using xhtml2pdf
"""
import logging
import re
from pathlib import Path
from typing import Optional
from xhtml2pdf import pisa
from io import BytesIO

logger = logging.getLogger(__name__)

class PDFConverter:
    """Utility class to convert HTML files to PDF using xhtml2pdf"""
    
    def __init__(self, base_url: Optional[str] = None):
        """
        Initialize the PDF converter
        
        Args:
            base_url (Optional[str]): Base URL for resolving relative paths in HTML
        """
        self.base_url = base_url
    
    def convert_html_to_pdf(self, html_file_path: Path, pdf_file_path: Path) -> bool:
        """
        Convert an HTML file to PDF using xhtml2pdf
        
        Args:
            html_file_path (Path): Path to the input HTML file
            pdf_file_path (Path): Path to the output PDF file
            
        Returns:
            bool: True if conversion successful, False otherwise
        """
        try:
            # Ensure output directory exists
            pdf_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Converting {html_file_path} to {pdf_file_path}")
            
            # Read HTML content
            with open(html_file_path, 'r', encoding='utf-8') as html_file:
                html_content = html_file.read()
            
            # Add additional CSS for better PDF formatting
            enhanced_html = self._enhance_html_for_pdf(html_content)
            
            # Convert HTML to PDF
            result_file = BytesIO()
            pisa_status = pisa.CreatePDF(
                enhanced_html,
                dest=result_file,
                encoding='utf-8'
            )
            
            if not pisa_status.err:
                # Write PDF to file
                with open(pdf_file_path, 'wb') as pdf_file:
                    pdf_file.write(result_file.getvalue())
                
                logger.info(f"Successfully converted: {html_file_path.name}")
                return True
            else:
                logger.error(f"PDF generation failed for {html_file_path}: {pisa_status.err}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to convert {html_file_path}: {str(e)}")
            return False
    
    def _enhance_html_for_pdf(self, html_content: str) -> str:
        """
        Enhance HTML content with additional CSS for better PDF formatting
        
        Args:
            html_content (str): Original HTML content
            
        Returns:
            str: Enhanced HTML content
        """
        # First, sanitize the existing HTML to remove problematic CSS
        sanitized_html = self._sanitize_css_for_pdf(html_content)
        
        # CSS styles for better PDF output
        pdf_css = """
        <style type="text/css">
        @page {
            size: A4;
            margin: 0.75in;
        }
        
        body {
            font-family: Arial, sans-serif;
            line-height: 1.4;
            color: #333;
            font-size: 12pt;
        }
        
        h1, h2, h3, h4, h5, h6 {
            page-break-after: avoid;
            margin-top: 1em;
            margin-bottom: 0.5em;
            color: #222;
        }
        
        h1 { font-size: 18pt; }
        h2 { font-size: 16pt; }
        h3 { font-size: 14pt; }
        h4 { font-size: 13pt; }
        h5 { font-size: 12pt; }
        h6 { font-size: 11pt; }
        
        p {
            margin-bottom: 0.8em;
            text-align: justify;
        }
        
        img {
            max-width: 100%;
            height: auto;
            page-break-inside: avoid;
        }
        
        table {
            page-break-inside: avoid;
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 1em;
        }
        
        table td, table th {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        
        table th {
            background-color: #f2f2f2;
            font-weight: bold;
        }
        
        pre, code {
            font-family: "Courier New", monospace;
            background-color: #f5f5f5;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-size: 11pt;
        }
        
        pre {
            padding: 1em;
            overflow: hidden;
            page-break-inside: avoid;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        
        blockquote {
            margin: 1em 2em;
            padding-left: 1em;
            border-left: 3px solid #ddd;
            font-style: italic;
            color: #666;
        }
        
        ul, ol {
            padding-left: 2em;
            margin-bottom: 1em;
        }
        
        li {
            margin-bottom: 0.3em;
        }
        
        a {
            color: #0066cc;
            text-decoration: underline;
        }
        
        .page-break {
            page-break-before: always;
        }
        </style>
        """
        
        # Insert the CSS into the HTML head
        if '<head>' in sanitized_html.lower():
            # Insert after opening head tag
            head_pos = sanitized_html.lower().find('<head>') + len('<head>')
            enhanced_html = sanitized_html[:head_pos] + pdf_css + sanitized_html[head_pos:]
        elif '<html>' in sanitized_html.lower():
            # Insert after opening html tag
            html_pos = sanitized_html.lower().find('<html>') + len('<html>')
            enhanced_html = sanitized_html[:html_pos] + '<head>' + pdf_css + '</head>' + sanitized_html[html_pos:]
        else:
            # Prepend to the entire content
            enhanced_html = '<html><head>' + pdf_css + '</head><body>' + sanitized_html + '</body></html>'
        
        return enhanced_html

    def _sanitize_css_for_pdf(self, html_content: str) -> str:
        """
        Sanitize CSS to remove problematic constructs that xhtml2pdf can't handle
        
        Args:
            html_content (str): Original HTML content
            
        Returns:
            str: HTML with sanitized CSS
        """
        try:
            # More aggressive approach: remove all existing CSS completely
            # This ensures xhtml2pdf compatibility by eliminating all potential parsing issues
            
            # Remove entire <style> blocks that might be problematic
            style_pattern = r'<style[^>]*>.*?</style>'
            html_content = re.sub(style_pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Remove inline style attributes that might cause issues
            inline_style_pattern = r'\sstyle\s*=\s*["\'][^"\']*["\']'
            html_content = re.sub(inline_style_pattern, '', html_content, flags=re.IGNORECASE)
            
            # Remove link tags to external stylesheets
            link_css_pattern = r'<link[^>]*rel\s*=\s*["\']stylesheet["\'][^>]*>'
            html_content = re.sub(link_css_pattern, '', html_content, flags=re.IGNORECASE)
            
            # Remove problematic CSS class attributes
            class_pattern = r'\sclass\s*=\s*["\'][^"\']*["\']'
            html_content = re.sub(class_pattern, '', html_content, flags=re.IGNORECASE)
            
            # Clean up any remaining CSS-related attributes that might cause issues
            css_attributes = ['id', 'data-.*', 'aria-.*', 'role']
            for attr in css_attributes:
                attr_pattern = rf'\s{attr}\s*=\s*["\'][^"\']*["\']'
                html_content = re.sub(attr_pattern, '', html_content, flags=re.IGNORECASE)
            
            # Remove JavaScript that might interfere
            script_pattern = r'<script[^>]*>.*?</script>'
            html_content = re.sub(script_pattern, '', html_content, flags=re.DOTALL | re.IGNORECASE)
            
            # Clean up malformed tags and extra whitespace
            html_content = re.sub(r'\s+', ' ', html_content)
            html_content = re.sub(r'>\s+<', '><', html_content)
            html_content = re.sub(r'<\s+', '<', html_content)
            html_content = re.sub(r'\s+>', '>', html_content)
            
            return html_content.strip()
            
        except Exception as e:
            logger.warning(f"CSS sanitization failed, using simplified fallback: {str(e)}")
            # Fallback: extract just the text content and wrap in basic HTML
            try:
                # Remove all tags except basic content tags
                basic_tags = ['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'span', 'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'br', 'strong', 'em', 'b', 'i']
                
                # Start with clean content
                clean_content = html_content
                
                # Remove all attributes from tags
                clean_content = re.sub(r'<(\w+)[^>]*>', r'<\1>', clean_content)
                
                # Keep only allowed tags
                all_tags = re.findall(r'</?(\w+)[^>]*>', clean_content)
                for tag in set(all_tags):
                    if tag.lower() not in basic_tags:
                        tag_pattern = rf'</?{re.escape(tag)}[^>]*>'
                        clean_content = re.sub(tag_pattern, '', clean_content, flags=re.IGNORECASE)
                
                return clean_content
            except:
                # Ultimate fallback: return basic HTML structure
                return '<html><body><p>Content processing failed - original content could not be parsed safely for PDF conversion.</p></body></html>'
    
    def get_pdf_path(self, html_file_path: Path, output_base_path: Path, relative_path: Path) -> Path:
        """
        Generate the output PDF path maintaining directory structure
        
        Args:
            html_file_path (Path): Original HTML file path
            output_base_path (Path): Base output directory
            relative_path (Path): Relative path from source base directory
            
        Returns:
            Path: Output PDF file path
        """
        # Change extension to .pdf
        pdf_filename = html_file_path.stem + '.pdf'
        
        # Maintain directory structure
        pdf_relative_dir = relative_path.parent
        pdf_path = output_base_path / pdf_relative_dir / pdf_filename
        
        return pdf_path