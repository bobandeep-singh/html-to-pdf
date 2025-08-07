"""
HTML file discovery utilities
"""
import logging
from pathlib import Path
from typing import List, Generator
from config import Config

logger = logging.getLogger(__name__)

class HTMLFileFinder:
    """Utility class to find HTML files recursively"""
    
    def __init__(self, base_path: str):
        """
        Initialize the HTML file finder
        
        Args:
            base_path (str): Base path to search for HTML files
        """
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            raise FileNotFoundError(f"Base path does not exist: {base_path}")
        if not self.base_path.is_dir():
            raise NotADirectoryError(f"Base path is not a directory: {base_path}")
    
    def find_html_files(self) -> Generator[Path, None, None]:
        """
        Recursively find all HTML files in the base path
        
        Yields:
            Path: Path object for each HTML file found
        """
        logger.info(f"Searching for HTML files in: {self.base_path}")
        
        for file_path in self.base_path.rglob("*"):
            if file_path.is_file() and Config.is_html_file(file_path):
                logger.debug(f"Found HTML file: {file_path}")
                yield file_path
    
    def get_html_files_list(self) -> List[Path]:
        """
        Get a list of all HTML files found
        
        Returns:
            List[Path]: List of Path objects for HTML files
        """
        return list(self.find_html_files())
    
    def get_relative_path(self, file_path: Path) -> Path:
        """
        Get the relative path of a file with respect to the base path
        
        Args:
            file_path (Path): Absolute path of the file
            
        Returns:
            Path: Relative path from base_path
        """
        return file_path.relative_to(self.base_path)