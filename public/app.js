let pdfIndex = [];
const searchInput = document.getElementById('search-input');
const exactMatchCheck = document.getElementById('exact-match');
const folderSelect = document.getElementById('folder-select');
const resultsContainer = document.getElementById('results-container');
const resultsMeta = document.getElementById('results-meta');
const loadingIndicator = document.getElementById('loading');

// Load the index on page load
async function loadIndex() {
    try {
        loadingIndicator.classList.remove('hidden');
        const response = await fetch('/search_index.json');
        if (!response.ok) throw new Error("Could not load index");
        pdfIndex = await response.json();
        loadingIndicator.classList.add('hidden');
        console.log(`Loaded index with ${pdfIndex.length} documents.`);
    } catch (e) {
        loadingIndicator.innerText = "Error loading search index. Please try again later.";
        console.error(e);
    }
}

// Perform search
function performSearch() {
    const query = searchInput.value.trim();
    if (!query) {
        resultsContainer.innerHTML = '';
        resultsMeta.classList.add('hidden');
        return;
    }

    const exactMatch = exactMatchCheck.checked;
    const selectedFolder = folderSelect.value;
    
    let searchTerms = [query.toLowerCase()];
    if (!exactMatch) {
        // Split by spaces, remove empty strings
        searchTerms = query.toLowerCase().split(/\s+/).filter(t => t.length > 0);
    }

    const results = [];

    // Search through the index
    for (const doc of pdfIndex) {
        if (selectedFolder !== 'all' && doc.folder !== selectedFolder) {
            continue;
        }

        const documentMatches = [];
        
        for (const page of doc.pages) {
            const pageTextLower = page.text.toLowerCase();
            let pageMatchesAll = true;

            // Check if page contains all required terms
            for (const term of searchTerms) {
                if (!pageTextLower.includes(term)) {
                    pageMatchesAll = false;
                    break;
                }
            }

            if (pageMatchesAll) {
                // Generate a snippet for the first found term
                const mainTerm = searchTerms[0];
                const termIdx = pageTextLower.indexOf(mainTerm);
                
                // Get roughly 60 chars before and 120 after
                const startIdx = Math.max(0, termIdx - 60);
                const endIdx = Math.min(page.text.length, termIdx + mainTerm.length + 120);
                
                let snippet = page.text.substring(startIdx, endIdx);
                if (startIdx > 0) snippet = "..." + snippet;
                if (endIdx < page.text.length) snippet = snippet + "...";

                // Highlight terms in the snippet
                for (const term of searchTerms) {
                    // Use regex for case-insensitive replacement
                    const regex = new RegExp(`(${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                    snippet = snippet.replace(regex, '<mark>$1</mark>');
                }

                documentMatches.push({
                    pageNumber: page.page_number,
                    snippet: snippet
                });
            }
        }

        if (documentMatches.length > 0) {
            results.push({
                doc: doc,
                matches: documentMatches
            });
        }
    }

    renderResults(query, results);
}

function renderResults(query, results) {
    resultsContainer.innerHTML = '';
    
    resultsMeta.classList.remove('hidden');
    resultsMeta.innerText = `Found ${results.length} document(s) matching "${query}"`;

    if (results.length === 0) {
        resultsContainer.innerHTML = '<p>No results found. Try using different keywords or turning off "Exact match".</p>';
        return;
    }

    results.forEach(result => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'result-item';
        
        // Header
        const firstMatchPage = result.matches[0].pageNumber;
        const pdfUrl = `${result.doc.path}#page=${firstMatchPage}`;
        
        let html = `
            <div class="result-header">
                <h3><a href="${pdfUrl}" target="_blank">${result.doc.filename}</a></h3>
                <span class="badge">Folder: ${result.doc.folder}</span>
                <span class="badge">${result.matches.length} page(s) match</span>
            </div>
            <div class="matches-container">
        `;

        // Only show up to 3 snippets per document to keep it clean
        const snippetsToShow = result.matches.slice(0, 3);
        
        snippetsToShow.forEach(match => {
            const pageUrl = `${result.doc.path}#page=${match.pageNumber}`;
            html += `
                <div class="match-snippet">
                    <div class="page-num">
                        <a href="${pageUrl}" target="_blank">Page ${match.pageNumber}</a>
                    </div>
                    <div class="snippet-text">${match.snippet}</div>
                </div>
            `;
        });

        if (result.matches.length > 3) {
            html += `<p><em>...and ${result.matches.length - 3} more matching pages.</em></p>`;
        }

        html += `</div>`;
        itemDiv.innerHTML = html;
        resultsContainer.appendChild(itemDiv);
    });
}

// Event Listeners
let debounceTimeout;
searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(performSearch, 300); // 300ms debounce
});

exactMatchCheck.addEventListener('change', performSearch);
folderSelect.addEventListener('change', performSearch);

// Initialize
loadIndex();