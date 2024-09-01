// Fetch question suggestions based on user input
async function getSuggestions(input, suggestionList) {
    if (input.length < 3) {
        suggestionList.innerHTML = '';
        suggestionList.classList.add('hidden');
        return;
    }

    try {
        const response = await fetch(`/api/suggestions/suggest_questions?partial_input=${encodeURIComponent(input)}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        displaySuggestions(data.suggestions, suggestionList);
    } catch (error) {
        console.error('Error fetching suggestions:', error);
        suggestionList.innerHTML = '';
        suggestionList.classList.add('hidden');
    }
}

// Display fetched suggestions in the UI
function displaySuggestions(suggestions, suggestionList) {
    suggestionList.innerHTML = '';
    if (suggestions && suggestions.length > 0) {
        suggestions.forEach(suggestion => {
            const li = document.createElement('li');
            li.textContent = suggestion;
            li.className = 'suggestion-item';
            li.onclick = () => selectSuggestion(suggestion, suggestionList);
            suggestionList.appendChild(li);
        });
        suggestionList.classList.remove('hidden');
    } else {
        suggestionList.classList.add('hidden');
    }
}

// Handle selection of a suggestion
function selectSuggestion(suggestion, suggestionList) {
    const input = suggestionList.previousElementSibling;
    input.value = suggestion;
    suggestionList.classList.add('hidden');
}

// Debounce function to limit API calls
const debouncedGetSuggestions = debounce((input, suggestionList) => {
    getSuggestions(input, suggestionList);
}, 300);

// Set up event listeners for question inputs
document.addEventListener('DOMContentLoaded', function() {
    const questionInputs = document.querySelectorAll('.question-input');
    questionInputs.forEach(input => {
        input.addEventListener('input', function() {
            debouncedGetSuggestions(this.value, this.nextElementSibling);
        });
    });
});