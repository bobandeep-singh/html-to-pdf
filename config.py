"""
Configuration settings for HTML to PDF converter
"""
import os
from pathlib import Path

class Config:
    """Configuration class for the HTML to PDF converter"""
    
    # Default settings
    DEFAULT_OUTPUT_DIR = "output"
    SUPPORTED_EXTENSIONS = ['.html', '.htm']
    
    @staticmethod
    def get_output_dir(base_path: str) -> Path:
        """Get the output directory path"""
        return Path(base_path) / Config.DEFAULT_OUTPUT_DIR
    
    @staticmethod
    def is_html_file(file_path: Path) -> bool:
        """Check if file is an HTML file"""
        return file_path.suffix.lower() in Config.SUPPORTED_EXTENSIONS