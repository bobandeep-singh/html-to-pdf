"""
HTML to PDF Converter
A utility to convert HTML files to PDF while maintaining directory structure
"""
import logging
import sys
from pathlib import Path
from typing import List, Tuple
import click
from colorama import Fore, Style

from config import Config
from html_finder import HTMLFileFinder
from pdf_converter import PDFConverter
from logger_setup import setup_logging

logger = logging.getLogger(__name__)

class HTMLToPDFConverter:
    """Main converter class that orchestrates the conversion process"""
    
    def __init__(self, base_path: str, output_dir: str = None, base_url: str = None):
        """
        Initialize the converter
        
        Args:
            base_path (str): Base directory to search for HTML files
            output_dir (str): Output directory (default: base_path/output)
            base_url (str): Base URL for resolving relative paths in HTML
        """
        self.base_path = Path(base_path)
        self.output_dir = Path(output_dir) if output_dir else Config.get_output_dir(base_path)
        
        # Initialize components
        self.html_finder = HTMLFileFinder(base_path)
        self.pdf_converter = PDFConverter(base_url)
        
        # Statistics
        self.total_files = 0
        self.successful_conversions = 0
        self.failed_conversions = 0
    
    def convert_all(self) -> Tuple[int, int]:
        """
        Convert all HTML files found in the base path to PDF
        
        Returns:
            Tuple[int, int]: (successful_conversions, failed_conversions)
        """
        logger.info(f"Starting HTML to PDF conversion")
        logger.info(f"Base path: {self.base_path}")
        logger.info(f"Output directory: {self.output_dir}")
        
        # Find all HTML files
        html_files = self.html_finder.get_html_files_list()
        self.total_files = len(html_files)
        
        if self.total_files == 0:
            logger.warning("No HTML files found in the specified directory")
            return 0, 0
        
        logger.info(f"Found {self.total_files} HTML files to convert")
        
        # Convert each file
        for html_file in html_files:
            self._convert_single_file(html_file)
        
        # Print summary
        self._print_summary()
        
        return self.successful_conversions, self.failed_conversions
    
    def _convert_single_file(self, html_file: Path) -> None:
        """
        Convert a single HTML file to PDF
        
        Args:
            html_file (Path): Path to the HTML file
        """
        try:
            # Get relative path to maintain directory structure
            relative_path = self.html_finder.get_relative_path(html_file)
            
            # Generate output PDF path
            pdf_path = self.pdf_converter.get_pdf_path(html_file, self.output_dir, relative_path)
            
            # Convert to PDF
            if self.pdf_converter.convert_html_to_pdf(html_file, pdf_path):
                self.successful_conversions += 1
            else:
                self.failed_conversions += 1
                
        except Exception as e:
            logger.error(f"Unexpected error converting {html_file}: {str(e)}")
            self.failed_conversions += 1
    
    def _print_summary(self) -> None:
        """Print conversion summary"""
        print(f"\n{Style.BRIGHT}=== Conversion Summary ==={Style.RESET_ALL}")
        print(f"Total HTML files found: {self.total_files}")
        print(f"{Fore.GREEN}Successful conversions: {self.successful_conversions}{Style.RESET_ALL}")
        
        if self.failed_conversions > 0:
            print(f"{Fore.RED}Failed conversions: {self.failed_conversions}{Style.RESET_ALL}")
        
        success_rate = (self.successful_conversions / self.total_files * 100) if self.total_files > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        print(f"Output directory: {self.output_dir}")

@click.command()
@click.argument('base_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory (default: base_path/output)')
@click.option('--base-url', type=str, help='Base URL for resolving relative paths in HTML files')
@click.option('--log-level', type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']), 
              default='INFO', help='Logging level')
@click.option('--dry-run', is_flag=True, help='Show what would be converted without actually converting')
def main(base_path: str, output: str, base_url: str, log_level: str, dry_run: bool):
    """
    Convert HTML files to PDF while maintaining directory structure.
    
    BASE_PATH: Directory containing HTML files to convert
    """
    # Setup logging
    setup_logging(log_level)
    
    try:
        if dry_run:
            logger.info("DRY RUN MODE - No files will be converted")
            finder = HTMLFileFinder(base_path)
            html_files = finder.get_html_files_list()
            
            print(f"\nFound {len(html_files)} HTML files:")
            for html_file in html_files:
                relative_path = finder.get_relative_path(html_file)
                print(f"  {relative_path}")
            
            output_dir = Path(output) if output else Config.get_output_dir(base_path)
            print(f"\nOutput directory would be: {output_dir}")
            return
        
        # Initialize and run converter
        converter = HTMLToPDFConverter(base_path, output, base_url)
        successful, failed = converter.convert_all()
        
        # Exit with error code if there were failures
        if failed > 0:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.warning("Conversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()