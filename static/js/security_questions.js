// Changes the current page
function changePage(page) {
    window.location.href = '/' + page;
}

// Returns the appropriate icon class based on file extension
function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    const iconMap = {
        pdf: 'far fa-file-pdf',
        xlsx: 'far fa-file-excel',
        xls: 'far fa-file-excel',
        docx: 'far fa-file-word',
        doc: 'far fa-file-word',
        msg: 'far fa-envelope',
        eml: 'far fa-envelope'
    };
    return iconMap[extension] || 'far fa-file';
}

// Fetches and displays anonymised files
async function loadAnonymisedFiles() {
    try {
        const response = await axios.get('/get_anonymized_files');
        const filesList = document.getElementById('anonymized-files-list');
        filesList.innerHTML = '';
        if (response.data.anonymized_files?.length) {
            response.data.anonymized_files.forEach(file => {
                const listItem = document.createElement('li');
                const icon = document.createElement('i');
                icon.className = `${getFileIcon(file)} file-icon`;
                listItem.appendChild(icon);
                listItem.appendChild(document.createTextNode(file));
                filesList.appendChild(listItem);
            });
        } else {
            filesList.innerHTML = '<li>No anonymised files found.</li>';
        }
    } catch (error) {
        console.error('Error loading anonymised files:', error);
        document.getElementById('anonymized-files-list').innerHTML = '<li>Error loading anonymised files.</li>';
    }
}

// Adds a single new question input to the form
function addNewQuestion() {
    console.log('addNewQuestion called'); // Debugging log
    const questionsContainer = document.getElementById('questions-container');
    const newQuestionItem = document.createElement('div');
    newQuestionItem.className = 'question-item';
    newQuestionItem.innerHTML = `
        <input type="text" class="question-input" placeholder="Enter new security question">
        <i class="fas fa-trash delete-btn"></i>
    `;
    questionsContainer.appendChild(newQuestionItem);

    // Add event listener to the new delete button
    newQuestionItem.querySelector('.delete-btn').addEventListener('click', function() {
        deleteQuestion(this);
    });
}

// Removes a question from the form
function deleteQuestion(deleteBtn) {
    deleteBtn.closest('.question-item').remove();
}

// Toggles visibility of model-specific inputs
function toggleModelInputs() {
    const aiModelSelect = document.getElementById('ai-model-select');
    const apiKeyInput = document.getElementById('api-key-input');
    const localModelSelect = document.getElementById('local-model-select');

    apiKeyInput.style.display = aiModelSelect.value === 'free' ? 'none' : 'inline-block';
    localModelSelect.style.display = aiModelSelect.value === 'free' ? 'inline-block' : 'none';
}

// Initiates the analysis process
function runAnalysis() {
    console.log('Starting analysis...');
    const aiModel = document.getElementById('ai-model-select').value;
    const apiKey = document.getElementById('api-key-input').value;
    const localModel = document.getElementById('local-model-select').value;
    const questions = Array.from(document.querySelectorAll('.question-input'))
        .map(input => input.value.trim())
        .filter(Boolean);

    if (!questions.length) {
        alert('Please enter at least one security question.');
        return;
    }

    if (aiModel !== 'free' && !apiKey.trim()) {
        alert('Please enter an API key for the selected AI model.');
        return;
    }

    const spinner = document.getElementById('analysis-spinner');
    const runAnalysisBtn = document.getElementById('run-analysis-btn');

    spinner.style.display = 'inline-block';
    runAnalysisBtn.disabled = true;
    runAnalysisBtn.textContent = 'Processing (this may take a while)...';

    const selectedModel = aiModel === 'free' ? localModel : aiModel;

    axios.post('/process_questions', {
        ai_model: selectedModel,
        api_key: apiKey,
        questions: questions
    })
    .then(response => {
        console.log('Process started:', response.data);
        checkProcessStatus();
    })
    .catch(error => {
        console.error('Error starting question processing:', error);
        alert('An error occurred while starting the analysis. Please check the console for more details.');
        resetAnalysisUI();
    });
}

// Checks the status of the analysis process
function checkProcessStatus() {
    axios.get('/process_status')
    .then(response => {
        console.log('Process status response:', response.data);
        if (response.data.status === 'complete') {
            localStorage.setItem('analysisResults', JSON.stringify(response.data.results));
            displayResults(response.data.results);
            resetAnalysisUI();
        } else if (response.data.status === 'error') {
            alert('An error occurred during analysis: ' + response.data.message);
            resetAnalysisUI();
        } else {
            setTimeout(checkProcessStatus, 10000);
        }
    })
    .catch(error => {
        console.error('Error checking process status:', error);
        alert('An error occurred while checking the analysis status. Please check the console for more details.');
        resetAnalysisUI();
    });
}

// Resets the UI after analysis completion or error
function resetAnalysisUI() {
    document.getElementById('analysis-spinner').style.display = 'none';
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    runAnalysisBtn.disabled = false;
    runAnalysisBtn.textContent = 'Run Analysis on Anonymised Data';
}

// Displays the analysis results
function displayResults(results) {
    console.log('Displaying results:', results);
    const resultsContainer = document.getElementById('results-container');
    if (!resultsContainer) {
        console.error('Results container not found');
        return;
    }
    resultsContainer.innerHTML = '<h2 class="text-xl font-bold mb-4">Analysis Results</h2>';
    resultsContainer.style.display = 'block';

    if (results?.length) {
        results.forEach((result, index) => {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'mb-4 p-4 bg-white rounded shadow';
            resultDiv.innerHTML = `
                <h3 class="text-lg font-semibold mb-2">Question ${index + 1}</h3>
                <p class="mb-2"><strong>Q:</strong> ${result.question}</p>
                <p class="mb-2"><strong>A:</strong> ${result.answer}</p>
                <p class="mb-2"><strong>Source:</strong> ${result.source}</p>
                <p class="mb-2"><strong>Citation:</strong> ${result.citation}</p>
            `;
            resultsContainer.appendChild(resultDiv);
        });
    } else {
        resultsContainer.innerHTML += '<p>No results available. Please try running the analysis again.</p>';
    }
}

// Initialises the page when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded event fired');
    document.getElementById('analysis-spinner').style.display = 'none';
    toggleModelInputs();
    invertFavicon();
    loadAnonymisedFiles();
    populateFreeAIModels(); // defined in free_ai_models.js

    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            deleteQuestion(this);
        });
    });

    document.getElementById('ai-model-select').addEventListener('change', toggleModelInputs);
    document.getElementById('run-analysis-btn').addEventListener('click', runAnalysis);

    // Ensure only one event listener is attached to the add question button
    const addQuestionBtn = document.getElementById('add-question-btn');
    addQuestionBtn.removeEventListener('click', addNewQuestion);
    addQuestionBtn.addEventListener('click', addNewQuestion);
    
    const storedResults = localStorage.getItem('analysisResults');
    if (storedResults) {
        try {
            displayResults(JSON.parse(storedResults));
        } catch (error) {
            console.error('Error parsing stored results:', error);
        }
    }
});