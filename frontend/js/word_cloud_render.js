// js for word_cloud_view_page.html

import { getUsername } from "./utils.js";

/*
 * The search rules (which localStorage keys, what the request body is, whether
 * a load is a real search or a reload) live in js/word_cloud_search.js, which
 * loads as a plain script before this module and so is already on window. The
 * pages that stage a search and the tests use that same file.
 */
const search = window.wordCloudSearch;

document.addEventListener('DOMContentLoaded', async () => {
    /*
     * Everything is inside one try, including the network calls.
     *
     * The /game/skills call used to sit above the try that wrapped the rest,
     * so a backend that was down, a 401, or any response that wasn't an array
     * threw out of this listener and left the page on "generating word
     * cloud..." forever with nothing said about why. That call is gone now -
     * the /wordcloud response carries a `playable` flag per word for exactly
     * this - but the boundary stays, because the point is that nothing on this
     * page fails silently.
     */
    try {
        if (!search) {
            throw new Error("The page did not load correctly. Please refresh.");
        }

        // this page needs a session, same guard the other logged-in pages use.
        // without it a signed-out visit fell through to the parse below and threw.
        if (!localStorage.getItem('token')) {
            window.location.href = '../html/sign_in_page.html';
            return;
        }

        // get data from local storage. a bad/missing value used to throw here,
        // above the try, so the page hung on "generating..." forever.
        const storedParameters = search.readStoredParameters();

        if (!storedParameters) {
            window.location.href = '../html/word_cloud_creation_page.html';
            return;
        }

        const wordCloudParameters = search.requestBodyFrom(storedParameters);

        const username = await getUsername();

        // update title
        populateTitle(username, wordCloudParameters);

        const wordCloudResult = await loadWordCloud(wordCloudParameters);

        if (!wordCloudResult) {
            return;
        }

        // on success: hide loading text
        hideLoadingText();

        // prepare result data (from backend)
        const formattedResults = wordCloudResult.words.map(item => [item.skill, item.weight]);

        // which words can start a quiz, straight off the response
        const playableSet = search.playableSkills(wordCloudResult);

        // RENDER WORD CLOUD
        renderWordCloud(formattedResults, wordCloudParameters.shape, playableSet);
    } catch (error) {
        console.error("Error:", error);
        showErrorMessage(error.message || "The word cloud could not be generated.");
    }
});


/* Returns the cloud to draw, or null when an error was already shown.
 *
 * The backend records a Search row on every POST /wordcloud, so posting on
 * each page load meant a refresh silently added another entry to the user's
 * history. Only five are kept, so refreshing a few times wiped the real ones.
 *
 * A search is a deliberate act now: whoever starts one stages it (the creation
 * form, the signup form, or Search Again on the profile page). A plain reload
 * finds nothing staged and just redraws what is stored.
 */
async function loadWordCloud(wordCloudParameters) {
    if (!search.shouldRunSearch()) {
        const cached = search.readStoredResults();
        if (cached) {
            return cached;
        }
    }

    /*
     * Say which field is missing rather than relaying a validation error about
     * it. The creation form always sets a job title, but a search staged from
     * somewhere else need not have.
     */
    if (!search.isSearchable(wordCloudParameters)) {
        search.beginSearch();
        showErrorMessage("Please choose a job title or an industry to search for.");
        return null;
    }

    // consume the flag so this search runs once, and drop the previous cloud
    // with it. Keeping it meant a search that failed left the old cloud in
    // storage, so a reload took the cache branch and drew it under the new
    // search's title. Nothing is recorded when a search fails, so a reload
    // after one simply tries again rather than duplicating a history row.
    search.beginSearch();

    // make a wordcloud POST request to the backend
    const response = await fetch('http://localhost:8000/wordcloud', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(wordCloudParameters)
    });

    const wordCloudResult = await readJsonBody(response);

    if (response.status === 401) {
        // the token expired mid-session; there is nothing to draw signed out
        localStorage.removeItem('token');
        window.location.href = '../html/sign_in_page.html';
        return null;
    }

    if (response.status === 422) {
        showErrorMessage(
            detailMessage(wordCloudResult) ||
            "Not enough job information to generate a word cloud. Please try updating your search parameters."
        );
        return null;
    }

    if (!response.ok) {
        throw new Error(
            detailMessage(wordCloudResult) ||
            `Error ${response.status}: Failed to generate word cloud.`
        );
    }

    search.storeResults(wordCloudResult);

    return wordCloudResult;
}


/* Parse a JSON body without throwing on an empty or non-JSON response, which
 * is what a proxy error page or a dropped connection looks like. */
async function readJsonBody(response) {
    try {
        return await response.json();
    } catch (error) {
        return null;
    }
}


/* FastAPI reports errors two ways: a string `detail` for the ones we raise,
 * and an array of {msg, loc} for validation failures. Flattening both here is
 * what keeps "[object Object]" off the screen. */
function detailMessage(body) {
    const detail = body && body.detail;

    if (Array.isArray(detail)) {
        return (detail[0] && detail[0].msg) || "";
    }
    if (typeof detail === 'string') {
        return detail;
    }
    return "";
}


// UI functions

function hideLoadingText() {
    const loadingText = document.getElementById('generating-word-cloud-text');

    if (loadingText) {
        loadingText.style.display = 'none';
    }
}

// populate title
function populateTitle(username, wrdCloudParams) {
    const titleElement = document.getElementById('word-cloud-title');
    if (!titleElement) return;

    // populate username
    let title = `${username || 'Your'}'s word cloud`;

    // populate job title, or the industry when that is what was searched
    if (wrdCloudParams.job_title) {
        title += ` for ${wrdCloudParams.job_title}`;
    } else if (wrdCloudParams.industry) {
        title += ` in the ${wrdCloudParams.industry} industry`;
    }

    //populate location
    if (wrdCloudParams.location) {
        title += ` in ${wrdCloudParams.location}`;
    }

    // populate min salary. Compared against null rather than tested for
    // truthiness so a deliberate 0 is not dropped.
    if (wrdCloudParams.min_salary !== null && wrdCloudParams.min_salary !== undefined) {
        title += ` with a minimum salary of ${wrdCloudParams.min_salary}`;
    }

    titleElement.textContent = title;

}

// error message handling
function showErrorMessage(message) {
    const errorDiv = document.getElementById('word-cloud-view-error-message');

    hideLoadingText();

    if (errorDiv) {
        errorDiv.innerText = message;
        errorDiv.style.display = 'block';
    }
}

// render word cloud
function renderWordCloud(data, shape, playableSet) {
    const container = document.getElementById('word-cloud-box');
    const myColors = ['#8BA6E9', '#7E96C4', '#D7B7BC'];

    if (!container) {
        throw new Error("The word cloud has nowhere to render on this page.");
    }

    /* The library comes from a CDN. If that did not load, say so rather than
     * throwing "WordCloud is not defined" into the console. */
    if (typeof WordCloud !== 'function') {
        throw new Error("The word cloud library could not be loaded.");
    }

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
