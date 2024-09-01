// Navigate to a different page
window.changePage = function(page) {
    window.location.href = '/' + page;
};

// Handle file uploads
window.handleFiles = function(files) {
    if (typeof uploadFile === 'function') {
        ([...files]).forEach(uploadFile);
    } else {
        console.error('uploadFile function is not defined');
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const dropArea = document.getElementById('drop-area');
    const fileList = document.getElementById('fileList');
    const fileElem = document.getElementById('fileElem');

    if (!dropArea || !fileList || !fileElem) {
        console.error('Required DOM elements not found');
        return;
    }

    fileElem.addEventListener('change', function() {
        handleFiles(this.files);
    });

    // Set active item in sidebar
    function setActiveSidebarItem() {
        const currentPage = window.location.pathname.split('/').pop() || 'index';
        const sidebarItems = document.querySelectorAll('.sidebar-item');
        sidebarItems.forEach(item => {
            item.classList.toggle('active', item.textContent.toLowerCase().replace(' ', '_') === currentPage);
        });
    }

    // Get appropriate icon for file type
    function getFileIcon(fileName) {
        const extension = fileName.split('.').pop().toLowerCase();
        const iconMap = {
            'pdf': '<i class="fas fa-file-pdf text-red-500 mr-2"></i>',
            'eml': '<i class="fas fa-envelope text-blue-500 mr-2"></i>',
            'msg': '<i class="fas fa-envelope-open-text text-green-500 mr-2"></i>'
        };
        return iconMap[extension] || '<i class="fas fa-file text-gray-500 mr-2"></i>';
    }

    // Add file to the displayed list
    function addFileToList(fileName) {
        if (document.querySelector(`.file-item[data-filename="${fileName}"]`)) {
            console.log('File already in list:', fileName);
            return;
        }
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item flex justify-between items-center p-3 bg-gray-50 rounded-lg mb-2';
        fileItem.setAttribute('data-filename', fileName);
        fileItem.innerHTML = `
            <div class="flex items-center">
                ${getFileIcon(fileName)}
                <span class="file-name">${fileName}</span>
            </div>
            <span class="remove-file text-red-500 cursor-pointer" onclick="removeFile(this, '${fileName}')">
                <i class="fas fa-trash"></i>
            </span>
        `;
        fileList.appendChild(fileItem);
    }

    // Prevent default drag and drop behaviour
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, e => {
            e.preventDefault();
            e.stopPropagation();
        }, false);
    });

    // Highlight drop area on drag
    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.add('highlight'), false);
    });

    // Remove highlight on drag leave or drop
    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, () => dropArea.classList.remove('highlight'), false);
    });

    // Handle file drop
    dropArea.addEventListener('drop', e => {
        handleFiles(e.dataTransfer.files);
    }, false);

    // Upload file to server
    window.uploadFile = async function(file) {
        if (file.type === 'application/pdf' || file.name.endsWith('.eml') || file.name.endsWith('.msg')) {
            if (document.querySelector(`.file-item[data-filename="${file.name}"]`)) {
                console.log('File already in list:', file.name);
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await axios.post('/upload_pdf', formData, {
                    headers: { 'Content-Type': 'multipart/form-data' }
                });

                if (response.status === 200) {
                    console.log('File uploaded successfully:', file.name);
                    addFileToList(file.name);
                } else {
                    console.error('Unexpected response status:', response.status);
                    alert('Unexpected response when uploading file: ' + file.name);
                }
            } catch (error) {
                console.error('Error uploading file:', error);
                alert('Error uploading file: ' + file.name + '. Please check the console for more details.');
            }
        } else {
            alert('Unsupported file type. Please upload PDF, EML, or MSG files only.');
        }
    };

    // Remove file from server and UI
    window.removeFile = async function(element, fileName) {
        try {
            const response = await axios.delete(`/remove_pdf/${fileName}`);
            if (response.status === 200) {
                alert('File successfully removed: ' + fileName);
                window.location.reload();
            } else {
                alert('Failed to remove file: ' + fileName);
            }
        } catch (error) {
            console.error('Error removing file:', error);
            alert('Error removing file: ' + fileName);
        }
    }

    // Load existing files from server
    async function loadExistingFiles() {
        try {
            const response = await axios.get('/get_uploaded_pdfs');
            if (response.status === 200 && response.data.uploaded_pdfs) {
                fileList.innerHTML = '';
                response.data.uploaded_pdfs.forEach(addFileToList);
            }
        } catch (error) {
            console.error('Error loading existing files:', error);
        }
    }

    setActiveSidebarItem();
    loadExistingFiles();
    
});