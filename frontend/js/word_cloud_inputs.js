// js for word_cloud_creation_page.html

import { getUsername } from "./utils.js";

document.addEventListener('DOMContentLoaded', async () => {
    const username = await getUsername();

    // update welcome message
    const welcomeDiv = document.getElementById('word-cloud-creation-welcome-message');

    if (username) {
        welcomeDiv.textContent = `Welcome, ${username}!`;
    } else {
        window.location.href = '../html/sign_in_page.html';
    }

    // grab form element
    const form = document.getElementById('wordCloudForm');

    // listen for form submission
    form.addEventListener('submit', async (event) => {
        // stop page from refreshing
        event.preventDefault();

        // collect form data
        const formData = {
            job_title: document.getElementById('jobTitleInput').value,
            location: document.getElementById('locationInput').value,
            min_salary: document.getElementById('minimumSalaryInput').value,

            word_count: document.getElementById('wordCountSelect').value,
            shape: document.getElementById('wordCloudShapeSelect').value
        };

        // save to localStorage
        localStorage.setItem('word_cloud_parameters', JSON.stringify(formData));

        // redirect to word cloud view/render page
        window.location.href = '../html/word_cloud_view_page.html';
    });
});