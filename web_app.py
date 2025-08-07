"""
Web-based HTML to PDF Converter
A Flask web application with elegant UI for converting HTML files to PDF
"""
import os
import json
import base64
import tempfile
import shutil
import zipfile
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS

from html_finder import HTMLFileFinder
from pdf_converter import PDFConverter
from config import Config

app = Flask(__name__)
app.secret_key = 'html-to-pdf-converter-secret-key-change-in-production'
CORS(app)

def get_current_conversion():
    """Get current conversion state from session"""
    if 'current_conversion' not in session:
        session['current_conversion'] = {
            'base_path': None,
            'html_files': [],
            'conversions': [],
            'output_dir': None
        }
    return session['current_conversion']

def update_current_conversion(updates):
    """Update current conversion state in session"""
    current = get_current_conversion()
    current.update(updates)
    session['current_conversion'] = current
    session.modified = True

@app.route('/')
def index():
    """Main page with folder selection and conversion interface"""
    return render_template('index.html')

@app.route('/api/scan-folder', methods=['POST'])
def scan_folder():
    """Scan selected folder for HTML files"""
    try:
        data = request.get_json()
        folder_path = data.get('folder_path', '')
        
        if not folder_path or not os.path.exists(folder_path):
            return jsonify({'error': 'Invalid folder path'}), 400
        
        # Initialize HTML finder
        html_finder = HTMLFileFinder(folder_path)
        html_files = html_finder.get_html_files_list()
        
        # Convert to relative paths for display
        file_list = []
        for html_file in html_files:
            relative_path = html_finder.get_relative_path(html_file)
            file_list.append({
                'absolute_path': str(html_file),
                'relative_path': str(relative_path),
                'filename': html_file.name,
                'size': html_file.stat().st_size if html_file.exists() else 0
            })
        
        # Update session state
        update_current_conversion({
            'base_path': folder_path,
            'html_files': file_list,
            'output_dir': str(Config.get_output_dir(folder_path))
        })
        current_conversion = get_current_conversion()
        
        return jsonify({
            'success': True,
            'folder_path': folder_path,
            'html_files': file_list,
            'output_dir': current_conversion['output_dir'],
            'total_files': len(file_list)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/convert', methods=['POST'])
def convert_files():
    """Convert all HTML files to PDF"""
    try:
        current_conversion = get_current_conversion()
        if not current_conversion['base_path'] or not current_conversion['html_files']:
            return jsonify({'error': 'No files to convert. Please scan a folder first.'}), 400
        
        # Initialize PDF converter
        pdf_converter = PDFConverter()
        conversions = []
        
        for file_info in current_conversion['html_files']:
            html_file_path = Path(file_info['absolute_path'])
            relative_path = Path(file_info['relative_path'])
            output_dir = Path(current_conversion['output_dir'])
            
            # Generate PDF path
            pdf_path = pdf_converter.get_pdf_path(html_file_path, output_dir, relative_path)
            
            # Convert to PDF
            success = pdf_converter.convert_html_to_pdf(html_file_path, pdf_path)
            
            conversion_result = {
                'html_file': file_info,
                'pdf_path': str(pdf_path) if success else None,
                'relative_pdf_path': str(pdf_path.relative_to(output_dir)) if success else None,
                'success': success,
                'error': None if success else 'Conversion failed'
            }
            
            conversions.append(conversion_result)
        
        # Update session state
        update_current_conversion({'conversions': conversions})
        
        # Calculate statistics
        successful = sum(1 for c in conversions if c['success'])
        failed = len(conversions) - successful
        success_rate = (successful / len(conversions) * 100) if conversions else 0
        
        return jsonify({
            'success': True,
            'conversions': conversions,
            'statistics': {
                'total': len(conversions),
                'successful': successful,
                'failed': failed,
                'success_rate': round(success_rate, 1)
            }
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get-file-content/<path:file_path>')
def get_file_content(file_path):
    """Get HTML file content for preview"""
    try:
        absolute_path = Path(file_path)
        if not absolute_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        with open(absolute_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'content': content,
            'filename': absolute_path.name
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/serve-pdf/<path:pdf_path>')
def serve_pdf(pdf_path):
    """Serve PDF file for preview"""
    try:
        absolute_path = Path(pdf_path)
        if not absolute_path.exists():
            return jsonify({'error': 'PDF file not found'}), 404
        
        return send_file(absolute_path, mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/upload-and-convert', methods=['POST'])
def upload_and_convert():
    """Handle file uploads from browser and convert them to PDF"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files selected'}), 400
        
        # Create session-specific directory for storing PDFs
        session_id = session.get('session_id', os.urandom(16).hex())
        session['session_id'] = session_id
        
        session_temp_dir = Path(tempfile.gettempdir()) / 'html_to_pdf_sessions' / session_id
        session_temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            output_dir = session_temp_dir / "pdfs"  # Store PDFs in session directory
            output_dir.mkdir(exist_ok=True)
            
            # Save uploaded files and extract root folder name
            html_files = []
            root_folder_name = None
            
            for file in files:
                if file.filename.lower().endswith(('.html', '.htm')):
                    # Maintain directory structure from webkitRelativePath
                    relative_path = request.form.get(f'path_{file.filename}', file.filename)
                    
                    # Extract root folder name from the first file if not already set
                    if root_folder_name is None and '/' in relative_path:
                        root_folder_name = relative_path.split('/')[0]
                    elif root_folder_name is None:
                        # Fallback for files in root directory
                        root_folder_name = "uploaded_files"
                    
                    file_path = temp_path / relative_path
                    
                    # Create directory if needed
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save file
                    file.save(file_path)
                    html_files.append({
                        'absolute_path': str(file_path),
                        'relative_path': relative_path,
                        'filename': file.filename,
                        'size': file_path.stat().st_size
                    })
            
            # Update session state with root folder information
            update_current_conversion({
                'base_path': root_folder_name or "uploaded_files",
                'session_temp_dir': str(session_temp_dir)
            })
            
            if not html_files:
                return jsonify({'error': 'No HTML files found in upload'}), 400
            
            # Convert files to PDF
            pdf_converter = PDFConverter()
            conversions = []
            
            for file_info in html_files:
                html_file_path = Path(file_info['absolute_path'])
                relative_path = Path(file_info['relative_path'])
                
                # Generate PDF path in session directory
                pdf_path = pdf_converter.get_pdf_path(html_file_path, output_dir, relative_path)
                
                # Convert to PDF
                success = pdf_converter.convert_html_to_pdf(html_file_path, pdf_path)
                
                conversion_result = {
                    'html_file': file_info,
                    'pdf_path': str(pdf_path) if success else None,
                    'relative_pdf_path': str(pdf_path.relative_to(output_dir)) if success else None,
                    'success': success,
                    'error': None if success else 'Conversion failed',
                    'pdf_data': None
                }
                
                # Read PDF data if successful for immediate download
                if success:
                    with open(pdf_path, 'rb') as pdf_file:
                        conversion_result['pdf_data'] = base64.b64encode(pdf_file.read()).decode('utf-8')
                
                conversions.append(conversion_result)
            
            # Store conversion info in session without the large PDF data but with PDF paths
            conversions_for_session = []
            for conv in conversions:
                session_conv = conv.copy()
                # Remove large base64 PDF data from session storage but keep the PDF path
                if 'pdf_data' in session_conv:
                    del session_conv['pdf_data']
                conversions_for_session.append(session_conv)
            
            update_current_conversion({'conversions': conversions_for_session})
            
            # Calculate statistics
            successful = sum(1 for c in conversions if c['success'])
            failed = len(conversions) - successful
            success_rate = (successful / len(conversions) * 100) if conversions else 0
            
            return jsonify({
                'success': True,
                'conversions': conversions,
                'is_browser_upload': True,  # Flag to indicate browser upload
                'statistics': {
                    'total': len(conversions),
                    'successful': successful,
                    'failed': failed,
                    'success_rate': round(success_rate, 1)
                }
            })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/download-all-pdfs')
def download_all_pdfs():
    """Create and download a ZIP file containing all converted PDFs with folder structure"""
    try:
        current_conversion = get_current_conversion()
        print(f"Debug: current_conversion state: {current_conversion}")
        print(f"Debug: conversions count: {len(current_conversion.get('conversions', []))}")
        if not current_conversion.get('conversions') or len(current_conversion['conversions']) == 0:
            return jsonify({'error': 'No conversions available for download'}), 400
        
        # Filter only successful conversions
        successful_conversions = [c for c in current_conversion['conversions'] if c['success']]
        
        if not successful_conversions:
            return jsonify({'error': 'No successful conversions available for download'}), 400
        
        # Create a temporary ZIP file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_zip:
            with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                for conversion in successful_conversions:
                    pdf_path = conversion.get('pdf_path')
                    zip_path = conversion['relative_pdf_path']
                    
                    # Check if PDF file exists (works for both server files and session-stored files)
                    if pdf_path and os.path.exists(pdf_path):
                        zipf.write(pdf_path, zip_path)
                    else:
                        # This should not happen anymore with the new session storage approach
                        print(f"Warning: PDF file not found: {pdf_path}")
                        continue
        
        # Determine the ZIP filename based on the base folder
        current_conversion = get_current_conversion()
        base_folder_name = current_conversion.get('base_path', 'converted_pdfs')
        if base_folder_name:
            zip_filename = f"{os.path.basename(base_folder_name)}_pdfs.zip"
        else:
            zip_filename = "converted_pdfs.zip"
        
        # Send the ZIP file and clean up
        def cleanup_temp_file():
            try:
                os.unlink(temp_zip.name)
            except:
                pass
        
        response = send_file(
            temp_zip.name,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
        
        # Schedule cleanup after response is sent
        response.call_on_close(cleanup_temp_file)
        
        return response
        
    except Exception as e:
        return jsonify({'error': f'Failed to create ZIP file: {str(e)}'}), 500

@app.route('/api/current-state')
def get_current_state():
    """Get current conversion state"""
    return jsonify(get_current_conversion())

@app.route('/api/clear-session', methods=['POST'])
def clear_session():
    """Clear current session and start fresh"""
    try:
        # Clean up session directory if it exists
        current_conversion = get_current_conversion()
        session_temp_dir = current_conversion.get('session_temp_dir')
        
        if session_temp_dir and os.path.exists(session_temp_dir):
            try:
                shutil.rmtree(session_temp_dir)
            except Exception as cleanup_error:
                print(f"Warning: Failed to clean up session directory {session_temp_dir}: {cleanup_error}")
        
        # Clear session data
        session.clear()
        return jsonify({'success': True, 'message': 'Session cleared successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)