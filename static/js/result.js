// Initialise page functionality when DOM is fully loaded
document.addEventListener('DOMContentLoaded', function() {
    setActiveSidebarItem();
    loadAndDisplayResults();
    setupClearResultsButton();
});

// Navigate to a different page
function changePage(page) {
    window.location.href = '/' + page;
}

// Highlight the current page in the sidebar
function setActiveSidebarItem() {
    const currentPage = window.location.pathname.split('/').pop() || 'index';
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    sidebarItems.forEach(item => {
        const itemPage = item.textContent.toLowerCase().replace(' ', '_');
        item.classList.toggle('active', itemPage === currentPage);
    });
}

// Load and display stored analysis results
function loadAndDisplayResults() {
    const storedResults = localStorage.getItem('analysisResults');
    if (storedResults) {
        try {
            const results = JSON.parse(storedResults);
            displayResults(results);
        } catch (error) {
            console.error('Error parsing stored results:', error);
            displayResults(null);
        }
    } else {
        displayResults(null);
    }
}

// Render analysis results or display a message if none exist
function displayResults(results) {
    const resultsContainer = document.getElementById('results-container');
    resultsContainer.innerHTML = '';

    if (results && results.length > 0) {
        const summaryDiv = createSummaryDiv(results.length);
        resultsContainer.appendChild(summaryDiv);

        results.forEach((result, index) => {
            const resultDiv = createResultDiv(result, index);
            resultsContainer.appendChild(resultDiv);
        });
    } else {
        resultsContainer.innerHTML = createNoResultsMessage();
    }
}

// Create a summary div for the results
function createSummaryDiv(totalQuestions) {
    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'mb-6 p-4 bg-blue-100 rounded-lg';
    summaryDiv.innerHTML = `
        <h2 class="text-xl font-semibold mb-2">Summary</h2>
        <p class="text-lg">Total questions analysed: ${totalQuestions}</p>
    `;
    return summaryDiv;
}

// Create a div for an individual result
function createResultDiv(result, index) {
    const resultDiv = document.createElement('div');
    resultDiv.className = 'result-item mb-6 bg-white p-6 rounded-lg shadow-md';
    resultDiv.innerHTML = `
        <h3 class="text-2xl font-semibold mb-4 text-blue-600">Question ${index + 1}</h3>
        <div class="mb-4">
            <p class="text-xl font-medium mb-2"><i class="fas fa-question-circle mr-2 text-blue-500"></i> ${result.question}</p>
        </div>
        <div class="bg-gray-100 p-4 rounded-md mb-4">
            <p class="text-lg"><i class="fas fa-comment-alt mr-2 text-green-500"></i><strong></strong> ${result.answer}</p>
        </div>
        <div class="text-sm text-gray-600">
            <p class="mb-2"><i class="fas fa-file-alt mr-2"></i><strong>Source:</strong> ${result.source}</p>
            <p class="italic"><i class="fas fa-quote-left mr-2"></i><strong>Citation:</strong> ${result.citation}</p>
        </div>
    `;
    return resultDiv;
}

// Create a message for when no results are found
function createNoResultsMessage() {
    return `
        <div class="bg-yellow-100 border-l-4 border-yellow-500 text-yellow-700 p-4 rounded-md" role="alert">
            <p class="font-bold mb-2">No Results Found</p>
            <p>No analysis results were found. Please run the analysis from the Security Questions page.</p>
        </div>
    `;
}

// Clear all stored results after user confirmation
function clearResults() {
    if (confirm('Are you sure you want to clear all results? This action cannot be undone.')) {
        localStorage.removeItem('analysisResults');
        displayResults(null);
    }
}

// Set up the clear results button
function setupClearResultsButton() {
    const clearResultsBtn = document.getElementById('clearResultsBtn');
    if (clearResultsBtn) {
        clearResultsBtn.addEventListener('click', clearResults);
    }
}

// Export functions for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        changePage,
        setActiveSidebarItem,
        loadAndDisplayResults,
        displayResults,
        clearResults
    };
}