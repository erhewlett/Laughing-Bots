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
        } else {
            console.error("Failed to fetch dashboard data");
            alert("Failed to fetch dashboard data");
        }
    } catch (error) {
        console.error("Initialization error:", error);
        alert(`Initialization error: ${error}`);
    }
}

// UI functions

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

        // check that data exists for current index in the array
        if (searches && searches[i]) {
            row.style.display = 'table-row';
            roleCell.innerText = searches[i].job_title;
            // TODO: implement word cloud regeneration (with word_cloud_view_page)
            btn.onclick = () => handleRerunSearch(searches[i]);
        } else {
            row.style.display = 'none';
        }

    }
}

async function handleRerunSearch(searchData) {
    // save user's search history parameters
    const wordCloudParameters = {
        job_title: searchData.job_title,
        industry: searchData.industry,
        location: searchData.location,
        min_salary: searchData.min_salary,

        word_count: searchData.word_count,
        shape: searchData.shape
    };

    // make a wordcloud POST request to the backend
    const response = await fetch('http://localhost:8000/wordcloud', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(wordCloudParameters)
    });

    if (response.ok) {
        const resultData = await response.json();

        // save weighted keyword results and word cloud parameters to local storage
        localStorage.setItem('word_cloud_results', JSON.stringify(resultData));
        localStorage.setItem('word_cloud_parameters', JSON.stringify(wordCloudParameters));

        // redirect user to word cloud view page
        window.location.href = '../html/word_cloud_view_page.html';
    } else {
        alert("Failed to regenerate word cloud. Please try again.");
    }
}

document.addEventListener('DOMContentLoaded', initDashboard);