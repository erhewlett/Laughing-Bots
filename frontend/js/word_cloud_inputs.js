// js for word_cloud_creation_page.html

import { getUsername } from "./utils.js";

// store valid locations for location input validation
let availableLocations = []

document.addEventListener('DOMContentLoaded', async () => {
    const username = await getUsername();

    // update welcome message
    const welcomeDiv = document.getElementById('word-cloud-creation-welcome-message');

    if (username) {
        welcomeDiv.textContent = `Welcome, ${username}!`;
    } else {
        window.location.href = '../html/sign_in_page.html';
    }
    // fetch available locations and populate options in the selection menu
    await fetchLocations();

    // grab form element
    const form = document.getElementById('wordCloudForm');

    // listen for form submission
    form.addEventListener('submit', async (event) => {
        // stop page from refreshing
        event.preventDefault();

        // validate location input
        const locationInput = document.getElementById('locationInput').value.trim();
        if (locationInput != "" && !availableLocations.includes(locationInput)) {
            showErrorMessage("Please select from the available locations or skip the location field.");
            return; 
        }

        // collect form data
        const formData = {
            job_title: document.getElementById('jobTitleInput').value,
            location: locationInput,
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

// fetch and populate avaiable locations from the backend
async function fetchLocations() {
    const dataList = document.getElementById('locationOptions');

    try {
        const response = await fetch('http://localhost:8000/locations');

        if (response.ok) {
            const locations = await response.json(); // returns a list of dictionaries

            // clear existing options
            dataList.innerHTML = '';

            // loop through available locations and create an option element for each available location
            locations.forEach(item => {
                const option = document.createElement('option');
                option.value = item.location;
                dataList.appendChild(option);

                // add the location to the list of available locations
                availableLocations.push(item.location);
            });
        } else {
            console.error('Failed to fetch available locations.');
            showErrorMessage('Failed to fetch available locations.');
        }
    } catch {
        console.error('Error connecting to backend server.');
        showErrorMessage('Error connecting to backend server. Please try again later.');
    }
}


// error message handling
function showErrorMessage(message) {
    const errorDiv = document.getElementById('word-cloud-inputs-error-message');

    if (errorDiv) {
        errorDiv.innerText = message;
        errorDiv.style.display = 'block';
    }
}