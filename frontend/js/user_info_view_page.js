// javascript for JobHopper user info view page

// initialization
async function initDashboard() {
    // get token from sign in and store in token variable
    const token = localStorage.getItem('token');

    // if token is missing, send user to sign in page
    if (!token) {
        window.location.href = '../html/sign_in_page.html';
        return;
    }

    // logic for "Generate New Word Cloud!" button
    const generateBtn = document.getElementById('generate-new-word-cloud-btn');
    if (generateBtn) {
        generateBtn.onclick = () => {
            // send user to word cloud creation page
            window.location.href = '../html/word_cloud_creation_page.html';
        };
    }

    try {
        const [userResponse, historyResponse] = await Promise.all([
            // fetch user information
            fetch('http://localhost:8000/auth/me', {
                headers: {'Authorization': `Bearer ${token}`}
            }),

            // fetch user's recent history
            fetch('http://localhost:8000/me/recent', {
                headers: {'Authorization': `Bearer ${token}`}
            })
        ]);

        if (userResponse.ok && historyResponse.ok) {
            const userData = await userResponse.json();
            const historyData = await historyResponse.json();

            // UI functions go here
            updateWelcomeMessage(userData);
            renderGameHistory(historyData.last_game);
            renderWordCloudHistory(historyData.recent_searches);
        } else if (userResponse.status === 401 || historyResponse.status === 401) {
            // session expired
            localStorage.removeItem('token');
            showErrorMessage("Session Expired. Please sign out and sign back in.")

            // automatically redirect to sign in page after 7 seconds
            setTimeout(() => {
                window.location.href = '../html/sign_in_page.html';
            }, 7000);
        }
        else {
            console.error("Failed to fetch dashboard data");
            showErrorMessage("Error: Failed to fetch dashboard data");
        }
    } catch (error) {
        console.error("Initialization error:", error);
        showErrorMessage(`Initialization error: ${error}`);
    }
}

// UI functions

// handle sign out logic
function handleSignOut() {
    // clear session data. The search keys are cleared by the module that owns
    // them, so signing out cannot leave one of the three behind.
    localStorage.removeItem('token');
    window.wordCloudSearch.clearSession();

    // replace and redirect to landing page
    window.location.replace('../html/main.html');
}

// error message handling
function showErrorMessage(message) {
    const errorDiv = document.getElementById('user-info-error-message');
    const errorText = document.getElementById('user-info-error-text');

    if (errorDiv && errorText) {
        errorText.innerText = message;
        errorDiv.style.display = 'block';

    }
}

// add username data to user welcome message (for personalization)
function updateWelcomeMessage(user) {
    const welcomeDiv = document.getElementById('user-welcome-message');
    if (welcomeDiv) {
        welcomeDiv.innerText = `Welcome, ${user.username}!`;
    }
}

// render game history data into table
function renderGameHistory(game) {
    const keywordCell = document.getElementById('recent-game-keyword');
    const scoreCell = document.getElementById('recent-game-score');

    if (game && keywordCell && scoreCell) {
        keywordCell.innerText = game.skill;
        scoreCell.innerText = `${game.score} / ${game.max_score}`;
    }
}

function renderWordCloudHistory(searches) {
    // loop through rows defined in user_info_view_page.html
    for (let i=0; i<3; i++) {
        // store current iteration's row in variable, row
        const row = document.getElementById(`recent-word-cloud-row-${i+1}`);

        // store current iteration's date cell in variable, dateCell
        const roleCell = document.getElementById(`recent-word-cloud-role-${i+1}`);

        // store current iteration's button in variable, btn
        const btn = document.getElementById(`rerun-word-cloud-btn-${i+1}`);

        // a page missing one of these rows should show the others, not throw
        if (!row || !roleCell || !btn) {
            continue;
        }

        // check that data exists for current index in the array
        if (searches && searches[i]) {
            row.style.display = 'table-row';
            // a search saved from the industry field has no job_title, which
            // rendered as an empty cell
            roleCell.innerText = searches[i].job_title || searches[i].industry || 'Saved search';
            // TODO: implement word cloud regeneration (with word_cloud_view_page)
            btn.onclick = () => handleRerunSearch(searches[i]);
        } else {
            row.style.display = 'none';
        }

    }
}

/* Re-run a saved search by staging it and letting the view page run it.
 *
 * This used to POST /wordcloud itself and store the result. Two things were
 * wrong with that. It hardcoded industry:"" while passing job_title straight
 * through, so a search saved from the industry field (which has no job_title -
 * see renderWordCloudHistory above) sent neither, was rejected by the backend
 * every time, and could never be re-run at all. And the fetch had no error
 * handling, so a backend that was down made the button do nothing whatsoever.
 *
 * Staging it instead means one page owns running a search, with the error
 * handling that page already has, and the industry comes along with it.
 */
function handleRerunSearch(searchData) {
    window.wordCloudSearch.stageSearch({
        job_title: searchData.job_title,
        industry: searchData.industry,
        location: searchData.location,
        min_salary: searchData.min_salary,
        word_count: searchData.word_count,
        shape: searchData.shape
    });

    // redirect user to word cloud view page, which runs the staged search
    window.location.href = '../html/word_cloud_view_page.html';
}

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();

    const signOutLink = document.getElementById('sign-out-link');
    if (signOutLink) {
        signOutLink.onclick = (e) => {
            e.preventDefault();
            handleSignOut();
        };
    }
});