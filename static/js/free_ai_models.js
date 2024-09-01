// List of available free AI models
const freeAIModels = [
    { name: "MPNet", value: "mpnet" },
    { name: "BART", value: "bart" },
    { name: "T5", value: "t5" }
];

// Populate the select element with free AI model options
function populateFreeAIModels() {
    const select = document.getElementById('local-model-select');
    select.innerHTML = '';
    freeAIModels.forEach(model => {
        const option = document.createElement('option');
        option.value = model.value;
        option.textContent = model.name;
        select.appendChild(option);
    });
}

// Process questions using the selected free AI model
async function processWithFreeModel(modelName, anonymizedPdfs, questions) {
    console.log(`Processing with model: ${modelName}`);
    console.log(`Questions: ${questions.join(', ')}`);
    
    try {
        const response = await axios.post('/process_questions', {
            ai_model: modelName,
            api_key: '',
            questions: questions
        });
        return response.data.results;
    } catch (error) {
        console.error('Error processing with free model:', error);
        throw error;
    }
}

// Run analysis using the selected free AI model and display results
async function runFreeModelAnalysis(modelName, anonymizedPdfs, questions) {
    try {
        const results = await processWithFreeModel(modelName, anonymizedPdfs, questions);
        displayResults(results);
    } catch (error) {
        console.error('Error processing with free model:', error);
        alert('An error occurred while processing with the free model. Please try again.');
    }
}

// Initialise free AI model options when the DOM is loaded
document.addEventListener('DOMContentLoaded', (event) => {
    populateFreeAIModels();
});

// Export functions for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        populateFreeAIModels,
        processWithFreeModel,
        runFreeModelAnalysis
    };
}