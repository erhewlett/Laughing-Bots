// js for word_cloud_view_page.html

import { getUsername } from "./utils.js";

document.addEventListener('DOMContentLoaded', async () => {
    const username = await getUsername()

    // get data from local storage
    const storedParameters = JSON.parse(localStorage.getItem('word_cloud_parameters'));
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

    // make a request to backend for word cloud
    try {
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
            return;
        }

        if (!response.ok) {
            const errorMessage = wordCloudResult.detail || `Error ${response.status}: Failed to generate word cloud.`;
            throw new Error(errorMessage);
        }

        // on success: hide loading text
        document.getElementById('generating-word-cloud-text').style.display = 'none';

        // prepare result data (from backend)
        const formattedResults = wordCloudResult.words.map(item => [item.skill, item.weight]);
        
        // RENDER WORD CLOUD
        console.log(wordCloudParameters.shape)
        renderWordCloud(formattedResults, wordCloudParameters.shape, playableSet);

    } catch (error) {
        console.error("Error:", error);
        showErrorMessage(error.message);
    }
});


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
                window.location.href = '../html/game_question_page.html' // TEMPORARY: TO BE UPDATED
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