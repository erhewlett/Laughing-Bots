// js for word_cloud_view_page.html

import { getUsername } from "./utils.js";
// Only the money formatter. The postings table itself belongs to the roadmap
// page; this page just needs to render a salary in the title.
import { formatMoney } from "./postings_table.js";

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

    try {
        // this used to sit above the try, so a backend that was down, a 401, or
        // any response that wasn't an array threw out of the listener and left
        // the page on "generating your word cloud..." for good, with nothing
        // said about why. Inside the try it is reported like anything else.
        const skillResponse = await fetch('http://localhost:8000/game/skills', {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        const skillData = await skillResponse.json();
        const playableSet = new Set(skillData.map(item => item.skill));

        const wordCloudResult = await loadWordCloud(wordCloudParameters);

        if (!wordCloudResult) {
            return;
        }

        // on success: hide loading text
        document.getElementById('generating-word-cloud-text').style.display = 'none';

        // prepare result data (from backend)
        const formattedResults = wordCloudResult.words.map(item => [item.skill, item.weight]);

        // RENDER WORD CLOUD
        await renderWordCloud(formattedResults, wordCloudParameters.shape, playableSet);

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

    // consume the flag so this search runs once, and drop the previous cloud
    // with it. Keeping it meant a search that failed left the old cloud in
    // storage, so a reload took the cache branch and drew it under the new
    // search's title. Nothing is recorded when a search fails, so a reload
    // after one simply tries again rather than duplicating a history row.
    localStorage.removeItem('word_cloud_pending');
    localStorage.removeItem('word_cloud_results');

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

    // populate min salary - as money, not as the raw number the field held
    if (wrdCloudParams.min_salary && wrdCloudParams.min_salary !== "") {
        title += ` with a minimum salary of ${formatMoney(wrdCloudParams.min_salary)}`;
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

// The box the cloud was drawn into back when its size was hard-coded. The
// type sizes below were picked against this, so they are scaled by however
// much smaller the real box turns out to be (see _wordCloudRender.scss).
const REFERENCE_BOX_PX = 1200;
const REFERENCE_GRID_PX = 12;

// The cloud font, which arrives from Google Fonts after the page does.
const CLOUD_FONT = 'Cascadia Code';

// wordcloud2 reserves space using the canvas text metrics, then paints the
// word as DOM text. The two disagree by a few pixels per word, and on the
// outermost words that difference lands past the edge of the box, where
// `overflow: hidden` shears the last letter off. Drawing a touch smaller than
// the space claimed absorbs the difference; it is not noticeable, and a
// clipped word on the demo screen is.
const CLOUD_FIT_MARGIN = 0.95;


/* Don't lay the cloud out until the font it is measured in has arrived.
 *
 * wordcloud2 measures every word on a canvas to decide where it fits. Ask it
 * before the webfont has loaded and it measures the fallback, lays the cloud
 * out to those widths, and then the real font paints wider than the space
 * reserved for it - so the words on the right ran past the edge of the box and
 * were cut off by `overflow: hidden`, and a couple were dropped as "not
 * fitting" when they would have fit.
 */
async function waitForCloudFont() {
    if (!document.fonts) return;              // older browser: render as before
    try {
        await document.fonts.load(`16px "${CLOUD_FONT}"`);
        await document.fonts.ready;
    } catch (error) {
        // A font that never loads is not a reason to skip the cloud; it just
        // renders in the fallback, which is what used to happen every time.
        console.warn('Cloud font did not load; rendering with the fallback.');
    }
}

// render word cloud
async function renderWordCloud(data, shape, playableSet) {
    const container = document.getElementById('word-cloud-box');
    const myColors = ['#8BA6E9', '#7E96C4', '#D7B7BC'];

    // The library is served from js/vendor, so this only trips if that file
    // failed to load. Say so, rather than throwing "WordCloud is not defined"
    // out of the caller and leaving the page on "generating...".
    if (typeof WordCloud !== 'function') {
        showErrorMessage(
            'The word cloud library did not load. Reload the page, and check that ' +
            'js/vendor/wordcloud2.js is being served.'
        );
        return;
    }

    await waitForCloudFont();

    // Scale the type to the box we actually got. Without this the words keep
    // their old sizes and a smaller box simply drops the ones that no longer
    // fit, which thins the cloud out on a laptop screen.
    const style = window.getComputedStyle(container);
    const usableWidth =
        container.clientWidth
        - parseFloat(style.paddingLeft)
        - parseFloat(style.paddingRight);
    const scale = usableWidth > 0 ? usableWidth / REFERENCE_BOX_PX : 1;

    WordCloud(container, {
        list: data,
        shape: shape,
        gridSize: Math.max(4, Math.round(REFERENCE_GRID_PX * scale)),
        weightFactor: scale * CLOUD_FIT_MARGIN,
        fontFamily: CLOUD_FONT,
        color: () => {
            return myColors[Math.floor(Math.random() * myColors.length)];
        },
        backgroundColor: '#ffffff',
        ellipticity: 1.0,
        // No origin: the default is the middle of the element. The old
        // [600, 600] was the middle of the old fixed box, which sat 32px right
        // of centre once the padding was taken off.

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