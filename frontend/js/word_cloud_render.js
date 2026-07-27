// js for word_cloud_view_page.html

import { getUsername } from "./utils.js";

document.addEventListener('DOMContentLoaded', async () => {
    // this page needs a session, same guard the other logged-in pages use.
    // without it a signed-out visit fell through to the parse below and threw.
    //
    // this replaces the token console.log from rose-debugging-2: it checks the
    // same thing and acts on it, and printing a token to the console is worth
    // avoiding anyway.
    if (!localStorage.getItem('token')) {
        window.location.href = '../html/sign_in_page.html';
        return;
    }

    // get data from local storage. a bad/missing value used to throw here,
    // above the try below, so the page hung on "generating..." forever.
    const storedParameters = readStoredParameters();

    if (!storedParameters) {
        window.location.href = '../html/word_cloud_creation_page.html';
        return;
    }

    const username = await getUsername()

    const wordCloudParameters = {
        job_title: storedParameters.job_title || "",
        industry: "", // temp fix for backend
        location: storedParameters.location || "",
        min_salary: (storedParameters.min_salary === "" || storedParameters.min_salary === null)
            ? null
            : Number(storedParameters.min_salary),
        word_count: storedParameters.word_count,
        shape: storedParameters.shape
    };

    // update title
    populateTitle(username, wordCloudParameters);

    const skillResponse = await fetch('http://localhost:8000/game/skills', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    });

    const skillData = await skillResponse.json();
    const playableSet = new Set(skillData.map(item => item.skill));

    try {
        const wordCloudResult = await loadWordCloud(wordCloudParameters);

        if (!wordCloudResult) {
            return;
        }

        // on success: hide loading text
        document.getElementById('generating-word-cloud-text').style.display = 'none';

        // prepare result data (from backend)
        const formattedResults = wordCloudResult.words.map(item => [item.skill, item.weight]);

        // RENDER WORD CLOUD
        renderWordCloud(formattedResults, wordCloudParameters.shape, playableSet);

    } catch (error) {
        console.error("Error:", error);
        showErrorMessage(error.message);
    }
});


// read the search parameters the creation page (or a rerun) left for us,
// returning null when there is nothing usable to render
function readStoredParameters() {
    try {
        const parsed = JSON.parse(localStorage.getItem('word_cloud_parameters'));
        return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (error) {
        console.warn('Stored word cloud parameters could not be read.');
        return null;
    }
}


/* Returns the cloud to draw, or null when an error was already shown.
 *
 * The backend records a Search row on every POST /wordcloud, so posting on
 * each page load meant a refresh silently added another entry to the user's
 * history. Only five are kept, so refreshing a few times wiped the real ones.
 *
 * A search is a deliberate act now: whoever starts one sets word_cloud_pending
 * (the creation form) or leaves the results behind for us (Search Again on the
 * profile page). A plain reload finds neither and just redraws what is stored.
 */
async function loadWordCloud(wordCloudParameters) {
    const pending = localStorage.getItem('word_cloud_pending');

    if (!pending) {
        const cached = readStoredResults();
        if (cached) {
            return cached;
        }
    }

    // consume the flag first so a failed search does not re-run on reload
    localStorage.removeItem('word_cloud_pending');

    // make a wordcloud POST request to the backend
    const response = await fetch('http://localhost:8000/wordcloud', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(wordCloudParameters)
    });

    const wordCloudResult = await response.json();

    if (response.status === 422) {
        showErrorMessage(wordCloudResult.detail || "Not enough job information to generate a word cloud. Please try updating your seach parameters.")
        document.getElementById('generating-word-cloud-text').style.display = 'none';
        return null;
    }

    if (!response.ok) {
        const errorMessage = wordCloudResult.detail || `Error ${response.status}: Failed to generate word cloud.`;
        throw new Error(errorMessage);
    }

    localStorage.setItem('word_cloud_results', JSON.stringify(wordCloudResult));

    return wordCloudResult;
}


// the cloud from the last real search, or null if there isn't a usable one
function readStoredResults() {
    try {
        const parsed = JSON.parse(localStorage.getItem('word_cloud_results'));
        return parsed && Array.isArray(parsed.words) ? parsed : null;
    } catch (error) {
        console.warn('Stored word cloud results could not be read.');
        return null;
    }
}


// UI functions

// populate title
function populateTitle(username, wrdCloudParams) {
    const titleElement = document.getElementById('word-cloud-title');
    if (!titleElement) return;

    // populate username
    let title = `${username}'s word cloud`;

    // populate job title
    if (wrdCloudParams.job_title && wrdCloudParams.job_title !== "") {
        title += ` for ${wrdCloudParams.job_title}`;
    }

    //populate location
    if (wrdCloudParams.location && wrdCloudParams.location !== "") {
        title += ` in ${wrdCloudParams.location}`;
    }

    // populate min salary
    if (wrdCloudParams.min_salary && wrdCloudParams.min_salary !== "") {
        title += ` with a minimum salary of ${wrdCloudParams.min_salary}`;
    }

    titleElement.textContent = title;

}

// error message handling
function showErrorMessage(message) {
    const errorDiv = document.getElementById('word-cloud-view-error-message');
    const loadingText = document.getElementById('generating-word-cloud-text').style.display = 'none';

    if (errorDiv) {
        errorDiv.innerText = message;
        errorDiv.style.display = 'block';
    }
}

// render word cloud
function renderWordCloud(data, shape, playableSet) {
    const container = document.getElementById('word-cloud-box');
    const myColors = ['#8BA6E9', '#7E96C4', '#D7B7BC'];

    WordCloud(container, {
        list: data,
        shape: shape,
        gridSize: 12,
        weightFactor: 1,
        fontFamily: 'Cascadia Code',
        color: () => {
            return myColors[Math.floor(Math.random() * myColors.length)];
        },
        backgroundColor: '#ffffff',
        ellipticity: 1.0,
        origin: [600, 600],

        click: (item) => {
            const word = item[0];
            if (playableSet.has(word)) {
                localStorage.setItem('selected_skill', word);
                window.location.href = '../html/game_difficulty.html' // UPDATED
            }
        },

        hover: (item) => {
            if (item && playableSet.has(item[0])) {
                container.style.cursor = 'pointer';
            } else {
                container.style.cursor = 'default';
            }
        }
    });
}