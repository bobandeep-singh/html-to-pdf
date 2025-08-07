// HTML to PDF Converter - Main JavaScript Application

class HTMLToPDFConverter {
    constructor() {
        this.currentState = {
            folderPath: '',
            htmlFiles: [],
            conversions: [],
            outputDir: ''
        };
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadCurrentState();
    }

    bindEvents() {
        // Create hidden file input for folder selection
        this.createFolderInput();
        
        // Folder selection
        document.getElementById('browseBtn').addEventListener('click', () => this.browseFolder());
        document.getElementById('scanBtn').addEventListener('click', () => this.scanFolder());
        
        // Conversion
        document.getElementById('convertBtn').addEventListener('click', () => this.convertFiles());
        
        // Download All button
        document.getElementById('downloadAllBtn').addEventListener('click', () => this.downloadAllPDFs());
        
        // Clear Session button
        document.getElementById('clearSessionBtn').addEventListener('click', () => this.clearSession());
        
        // Enter key support for folder input
        document.getElementById('folderPath').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.scanFolder();
            }
        });
    }

    createFolderInput() {
        // Create a hidden file input with webkitdirectory attribute
        this.folderInput = document.createElement('input');
        this.folderInput.type = 'file';
        this.folderInput.webkitdirectory = true;
        this.folderInput.multiple = true;
        this.folderInput.style.display = 'none';
        document.body.appendChild(this.folderInput);
        
        // Handle folder selection
        this.folderInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                // Get the folder path from the first file
                const firstFile = e.target.files[0];
                const pathParts = firstFile.webkitRelativePath.split('/');
                const folderName = pathParts[0];
                
                // For security reasons, we can't get the full absolute path
                // But we can work with the selected files directly
                this.handleFolderSelection(e.target.files, folderName);
            }
        });
    }

    browseFolder() {
        // Trigger the hidden file input
        this.folderInput.click();
    }

    handleFolderSelection(files, folderName) {
        // Filter HTML files from the selected files
        const htmlFiles = Array.from(files).filter(file => {
            const extension = file.name.toLowerCase().split('.').pop();
            return ['html', 'htm'].includes(extension);
        });

        if (htmlFiles.length === 0) {
            this.showToast('warning', 'No HTML files found in the selected folder.');
            return;
        }

        // Convert FileList to our format
        const fileList = htmlFiles.map(file => {
            const relativePath = file.webkitRelativePath;
            return {
                file_object: file,
                relative_path: relativePath,
                filename: file.name,
                size: file.size,
                folder_name: folderName
            };
        });

        // Update the folder path input
        document.getElementById('folderPath').value = `Selected folder: ${folderName}`;

        // Update current state
        this.currentState.folderPath = folderName;
        this.currentState.htmlFiles = fileList;
        this.currentState.outputDir = `${folderName}_output`;

        // Show results
        this.showBrowserScanResults({
            folder_path: folderName,
            html_files: fileList,
            output_dir: this.currentState.outputDir,
            total_files: fileList.length
        });

        this.activateStep(2);
        this.showToast('success', `Found ${fileList.length} HTML files in ${folderName}`);
    }

    async scanFolder() {
        const folderPath = document.getElementById('folderPath').value.trim();
        
        if (!folderPath) {
            this.showToast('error', 'Please enter a folder path');
            return;
        }

        this.showLoading('Scanning folder for HTML files...');

        try {
            const response = await fetch('/api/scan-folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ folder_path: folderPath })
            });

            const data = await response.json();

            if (data.success) {
                this.currentState.folderPath = data.folder_path;
                this.currentState.htmlFiles = data.html_files;
                this.currentState.outputDir = data.output_dir;
                
                this.showScanResults(data);
                this.activateStep(2);
                this.showToast('success', `Found ${data.total_files} HTML files`);
            } else {
                this.showToast('error', data.error || 'Failed to scan folder');
            }
        } catch (error) {
            this.showToast('error', 'Network error: ' + error.message);
        }

        this.hideLoading();
    }

    async convertFiles() {
        if (this.currentState.htmlFiles.length === 0) {
            this.showToast('error', 'No HTML files to convert');
            return;
        }

        this.showLoading('Converting HTML files to PDF...');

        try {
            // Check if we have browser-selected files or server path files
            const hasBrowserFiles = this.currentState.htmlFiles.some(file => file.file_object);
            
            if (hasBrowserFiles) {
                await this.convertBrowserFiles();
            } else {
                await this.convertServerFiles();
            }
        } catch (error) {
            this.showToast('error', 'Network error: ' + error.message);
        }

        this.hideLoading();
    }

    async convertServerFiles() {
        const response = await fetch('/api/convert', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        const data = await response.json();

        if (data.success) {
            this.currentState.conversions = data.conversions;
            this.showConversionResults(data);
            this.activateStep(3);
            this.showToast('success', `Conversion completed! ${data.statistics.successful} of ${data.statistics.total} files converted successfully`);
        } else {
            this.showToast('error', data.error || 'Conversion failed');
        }
    }

    async convertBrowserFiles() {
        const formData = new FormData();
        
        // Add files to form data
        this.currentState.htmlFiles.forEach((file, index) => {
            if (file.file_object) {
                formData.append('files', file.file_object);
                formData.append(`path_${file.file_object.name}`, file.relative_path);
            }
        });

        const response = await fetch('/api/upload-and-convert', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.success) {
            this.currentState.conversions = data.conversions;
            this.showBrowserConversionResults(data);
            this.activateStep(3);
            this.showToast('success', `Conversion completed! ${data.statistics.successful} of ${data.statistics.total} files converted successfully`);
        } else {
            this.showToast('error', data.error || 'Conversion failed');
        }
    }

    showScanResults(data) {
        const resultsContainer = document.getElementById('scanResults');
        
        if (data.html_files.length === 0) {
            resultsContainer.innerHTML = `
                <div class="text-center p-3">
                    <i class="fas fa-search fa-3x text-secondary mb-3"></i>
                    <h3>No HTML files found</h3>
                    <p class="text-secondary">No HTML files were found in the specified folder.</p>
                </div>
            `;
            return;
        }

        const statsHtml = `
            <div class="stats-grid mb-3">
                <div class="stat-item">
                    <div class="stat-value info">${data.total_files}</div>
                    <div class="stat-label">HTML Files Found</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value info">${data.folder_path.split('/').pop()}</div>
                    <div class="stat-label">Root Folder</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value info">${data.output_dir.split('/').pop()}</div>
                    <div class="stat-label">Output Folder</div>
                </div>
            </div>
        `;

        const fileListHtml = data.html_files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <i class="fas fa-file-code file-icon"></i>
                    <div class="file-details">
                        <h4>${file.filename}</h4>
                        <p>${file.relative_path}</p>
                    </div>
                </div>
                <div class="file-size">${this.formatFileSize(file.size)}</div>
            </div>
        `).join('');

        resultsContainer.innerHTML = `
            ${statsHtml}
            <div class="file-list">
                ${fileListHtml}
            </div>
        `;
    }

    showBrowserScanResults(data) {
        // Similar to showScanResults but for browser-selected files
        this.showScanResults(data);
        
        // Enable convert button since we have files selected
        document.getElementById('convertBtn').disabled = false;
    }

    showConversionResults(data) {
        const statsContainer = document.getElementById('conversionStats');
        const resultsContainer = document.getElementById('resultsContainer');
        const downloadAllSection = document.getElementById('downloadAllSection');

        // Show statistics
        const stats = data.statistics;
        statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value info">${stats.total}</div>
                    <div class="stat-label">Total Files</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value success">${stats.successful}</div>
                    <div class="stat-label">Successful</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value error">${stats.failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value info">${stats.success_rate}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
            </div>
        `;

        // Show download all button for server-based conversions
        if (stats.successful > 0) {
            downloadAllSection.style.display = 'block';
        }

        // Show conversion results with collapsible previews
        const conversionsHtml = data.conversions.map((conversion, index) => {
            const statusClass = conversion.success ? 'success' : 'error';
            const statusIcon = conversion.success ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
            const statusText = conversion.success ? 'Converted Successfully' : 'Conversion Failed';

            return `
                <div class="conversion-item" id="conversion-${index}">
                    <div class="conversion-header ${statusClass}" onclick="app.toggleConversion(${index})">
                        <div class="conversion-title">
                            <i class="${statusIcon}"></i>
                            <span>${conversion.html_file.filename}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm">${statusText}</span>
                            <i class="fas fa-chevron-down" id="chevron-${index}"></i>
                        </div>
                    </div>
                    <div class="conversion-content" id="content-${index}">
                        ${conversion.success ? this.createPreviewContent(conversion, index) : `
                            <div class="text-center p-3">
                                <i class="fas fa-exclamation-triangle fa-2x text-error mb-2"></i>
                                <p class="text-error">${conversion.error}</p>
                            </div>
                        `}
                    </div>
                </div>
            `;
        }).join('');

        resultsContainer.innerHTML = conversionsHtml;
    }

    showBrowserConversionResults(data) {
        const statsContainer = document.getElementById('conversionStats');
        const resultsContainer = document.getElementById('resultsContainer');
        const downloadAllSection = document.getElementById('downloadAllSection');

        // Show statistics
        const stats = data.statistics;
        statsContainer.innerHTML = `
            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-value info">${stats.total}</div>
                    <div class="stat-label">Total Files</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value success">${stats.successful}</div>
                    <div class="stat-label">Successful</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value error">${stats.failed}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value info">${stats.success_rate}%</div>
                    <div class="stat-label">Success Rate</div>
                </div>
            </div>
        `;

        // Show download all button for successful conversions (both browser uploads and server scanning)
        if (stats.successful > 0) {
            downloadAllSection.style.display = 'block';
        }

        // Show conversion results with collapsible previews for browser files
        const conversionsHtml = data.conversions.map((conversion, index) => {
            const statusClass = conversion.success ? 'success' : 'error';
            const statusIcon = conversion.success ? 'fas fa-check-circle' : 'fas fa-exclamation-circle';
            const statusText = conversion.success ? 'Converted Successfully' : 'Conversion Failed';

            return `
                <div class="conversion-item" id="conversion-${index}">
                    <div class="conversion-header ${statusClass}" onclick="app.toggleConversion(${index})">
                        <div class="conversion-title">
                            <i class="${statusIcon}"></i>
                            <span>${conversion.html_file.filename}</span>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-sm">${statusText}</span>
                            <i class="fas fa-chevron-down" id="chevron-${index}"></i>
                        </div>
                    </div>
                    <div class="conversion-content" id="content-${index}">
                        ${conversion.success ? this.createBrowserPreviewContent(conversion, index) : `
                            <div class="text-center p-3">
                                <i class="fas fa-exclamation-triangle fa-2x text-error mb-2"></i>
                                <p class="text-error">${conversion.error}</p>
                            </div>
                        `}
                    </div>
                </div>
            `;
        }).join('');

        resultsContainer.innerHTML = conversionsHtml;
    }

    createPreviewContent(conversion, index) {
        return `
            <div class="preview-container">
                <div class="preview-panel">
                    <div class="preview-header">
                        <i class="fas fa-code"></i>
                        HTML Preview
                    </div>
                    <div class="preview-content">
                        <iframe class="html-preview" id="html-${index}" src="/api/serve-html/${encodeURIComponent(conversion.html_file.absolute_path)}"></iframe>
                    </div>
                </div>
                <div class="preview-panel">
                    <div class="preview-header">
                        <i class="fas fa-file-pdf"></i>
                        PDF Preview
                    </div>
                    <div class="preview-content">
                        <iframe class="pdf-preview" id="pdf-${index}" src="/api/serve-pdf/${encodeURIComponent(conversion.pdf_path)}"></iframe>
                    </div>
                </div>
            </div>
            <div class="mt-3 text-center">
                <div class="flex items-center justify-between">
                    <div>
                        <strong>Original:</strong> ${conversion.html_file.relative_path}
                    </div>
                    <div>
                        <strong>PDF Output:</strong> ${conversion.relative_pdf_path}
                    </div>
                </div>
            </div>
        `;
    }

    createBrowserPreviewContent(conversion, index) {
        return `
            <div class="preview-container">
                <div class="preview-panel">
                    <div class="preview-header">
                        <i class="fas fa-code"></i>
                        HTML Preview
                    </div>
                    <div class="preview-content">
                        <iframe class="html-preview" id="html-${index}"></iframe>
                    </div>
                </div>
                <div class="preview-panel">
                    <div class="preview-header">
                        <i class="fas fa-file-pdf"></i>
                        PDF Preview
                    </div>
                    <div class="preview-content">
                        <iframe class="pdf-preview" id="pdf-${index}"></iframe>
                    </div>
                </div>
            </div>
            <div class="mt-3 text-center">
                <div class="flex items-center justify-between">
                    <div>
                        <strong>Original:</strong> ${conversion.html_file.relative_path}
                    </div>
                    <div>
                        <strong>PDF Output:</strong> ${conversion.relative_pdf_path || 'Generated PDF'}
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-primary" onclick="app.downloadPDF(${index})">
                        <i class="fas fa-download"></i> Download PDF
                    </button>
                </div>
            </div>
        `;
    }

    downloadPDF(index) {
        const conversion = this.currentState.conversions[index];
        if (conversion && conversion.success && conversion.pdf_data) {
            // Convert base64 to blob and download
            const byteCharacters = atob(conversion.pdf_data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const blob = new Blob([byteArray], { type: 'application/pdf' });
            
            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${conversion.html_file.filename.replace('.html', '.htm', '')}.pdf`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    }

    async downloadAllPDFs() {
        if (!this.currentState.conversions || this.currentState.conversions.length === 0) {
            this.showToast('error', 'No conversions available for download');
            return;
        }

        // Check if there are any successful conversions
        const successfulConversions = this.currentState.conversions.filter(c => c.success);
        if (successfulConversions.length === 0) {
            this.showToast('error', 'No successful conversions available for download');
            return;
        }

        this.showLoading('Creating ZIP file with all PDFs...');

        try {
            const response = await fetch('/api/download-all-pdfs');
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to download ZIP file');
            }

            // Get the filename from the Content-Disposition header or use a default
            const contentDisposition = response.headers.get('content-disposition');
            let filename = 'converted_pdfs.zip';
            if (contentDisposition) {
                const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
                if (filenameMatch) {
                    filename = filenameMatch[1].replace(/['"]/g, '');
                }
            }

            // Download the ZIP file
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            this.showToast('success', `Downloaded ${successfulConversions.length} PDFs as ZIP file with original folder structure`);

        } catch (error) {
            this.showToast('error', `Failed to download ZIP file: ${error.message}`);
        }

        this.hideLoading();
    }

    async clearSession() {
        if (!confirm('Are you sure you want to start fresh? This will clear all current data and conversions.')) {
            return;
        }

        this.showLoading('Clearing session...');

        try {
            const response = await fetch('/api/clear-session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();

            if (data.success) {
                // Reset client state
                this.currentState = {
                    folderPath: '',
                    htmlFiles: [],
                    conversions: [],
                    outputDir: ''
                };

                // Reset UI
                this.resetUI();
                this.showToast('success', 'Session cleared successfully. You can start fresh now.');
            } else {
                this.showToast('error', data.error || 'Failed to clear session');
            }
        } catch (error) {
            this.showToast('error', `Network error: ${error.message}`);
        }

        this.hideLoading();
    }

    resetUI() {
        // Clear form inputs
        document.getElementById('folderPath').value = '';
        
        // Clear results containers
        document.getElementById('scanResults').innerHTML = '';
        document.getElementById('conversionStats').innerHTML = '';
        document.getElementById('resultsContainer').innerHTML = '';
        
        // Hide download all section
        document.getElementById('downloadAllSection').style.display = 'none';
        
        // Reset steps to initial state
        this.activateStep(1);
        
        // Reset step cards
        document.querySelectorAll('.step-card').forEach(card => {
            card.classList.remove('active', 'completed');
        });
        document.getElementById('step1').classList.add('active');
        
        // Enable/disable buttons
        document.getElementById('convertBtn').disabled = false;
    }

    toggleConversion(index) {
        const content = document.getElementById(`content-${index}`);
        const chevron = document.getElementById(`chevron-${index}`);
        
        if (content.classList.contains('active')) {
            content.classList.remove('active');
            chevron.style.transform = 'rotate(0deg)';
        } else {
            // Close all other open conversions
            document.querySelectorAll('.conversion-content.active').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelectorAll('.conversion-header i.fa-chevron-down').forEach(el => {
                el.style.transform = 'rotate(0deg)';
            });
            
            // Open current conversion
            content.classList.add('active');
            chevron.style.transform = 'rotate(180deg)';
            
            // Load previews when opened for the first time
            if (!content.dataset.loaded) {
                this.loadPreviews(index);
                content.dataset.loaded = 'true';
            }
        }
    }

    async loadPreviews(index) {
        const conversion = this.currentState.conversions[index];
        if (!conversion.success) return;

        const htmlIframe = document.getElementById(`html-${index}`);
        const pdfIframe = document.getElementById(`pdf-${index}`);

        // Check if this is a browser-uploaded file (has pdf_data) or server file
        if (conversion.pdf_data) {
            // Browser-uploaded file - load from original file object and PDF data
            // Try to find by exact filename match first
            let originalFile = this.currentState.htmlFiles.find(f => f.filename === conversion.html_file.filename);
            
            // If not found, try to find by relative path
            if (!originalFile) {
                originalFile = this.currentState.htmlFiles.find(f => f.relative_path === conversion.html_file.relative_path);
            }
            
            // If still not found, try by the original file name (last part of path)
            if (!originalFile) {
                const htmlFileName = conversion.html_file.filename.split('/').pop();
                originalFile = this.currentState.htmlFiles.find(f => f.filename === htmlFileName);
            }
            
            if (originalFile && originalFile.file_object) {
                // Load HTML from original file object
                const htmlUrl = URL.createObjectURL(originalFile.file_object);
                htmlIframe.src = htmlUrl;
            } else {
                htmlIframe.src = 'data:text/html;charset=utf-8,<html><body><h3>HTML Preview Not Available</h3><p>Could not load original HTML file for preview.</p></body></html>';
            }

            // Load PDF from base64 data
            const byteCharacters = atob(conversion.pdf_data);
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const byteArray = new Uint8Array(byteNumbers);
            const pdfBlob = new Blob([byteArray], { type: 'application/pdf' });
            const pdfUrl = URL.createObjectURL(pdfBlob);
            pdfIframe.src = pdfUrl;
            
        } else {
            // Server file - load via API endpoints
            try {
                // Load HTML via server endpoint
                htmlIframe.src = `/api/serve-html/${encodeURIComponent(conversion.html_file.absolute_path)}`;

                // Load PDF via server endpoint
                if (pdfIframe) {
                    pdfIframe.src = `/api/serve-pdf/${encodeURIComponent(conversion.pdf_path)}`;
                }
            } catch (error) {
                console.error('Error setting up HTML preview:', error);
            }
        }
    }

    activateStep(stepNumber) {
        // Remove active class from all steps
        document.querySelectorAll('.step-card').forEach(card => {
            card.classList.remove('active');
        });

        // Mark previous steps as completed
        for (let i = 1; i < stepNumber; i++) {
            document.getElementById(`step${i}`).classList.add('completed');
        }

        // Activate current step
        document.getElementById(`step${stepNumber}`).classList.add('active');
    }

    showLoading(message = 'Processing...') {
        const modal = document.getElementById('loadingModal');
        const messageEl = document.getElementById('loadingMessage');
        messageEl.textContent = message;
        modal.classList.add('active');
    }

    hideLoading() {
        const modal = document.getElementById('loadingModal');
        modal.classList.remove('active');
    }

    showToast(type, message) {
        const toastContainer = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const iconMap = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        };

        toast.innerHTML = `
            <i class="${iconMap[type]}"></i>
            <span>${message}</span>
        `;

        toastContainer.appendChild(toast);

        // Remove toast after 5 seconds
        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async loadCurrentState() {
        try {
            const response = await fetch('/api/current-state');
            const state = await response.json();
            
            if (state.base_path) {
                document.getElementById('folderPath').value = state.base_path;
                this.currentState = state;
                
                if (state.html_files && state.html_files.length > 0) {
                    this.showScanResults({
                        folder_path: state.base_path,
                        html_files: state.html_files,
                        output_dir: state.output_dir,
                        total_files: state.html_files.length
                    });
                    this.activateStep(2);
                }
                
                if (state.conversions && state.conversions.length > 0) {
                    const stats = {
                        total: state.conversions.length,
                        successful: state.conversions.filter(c => c.success).length,
                        failed: state.conversions.filter(c => !c.success).length
                    };
                    stats.success_rate = ((stats.successful / stats.total) * 100).toFixed(1);
                    
                    this.showConversionResults({
                        conversions: state.conversions,
                        statistics: stats
                    });
                    this.activateStep(3);
                }
            }
        } catch (error) {
            console.log('No previous state found');
        }
    }
}

// Initialize the application
const app = new HTMLToPDFConverter();

// Make app globally available for event handlers
window.app = app;