// javascript for JobHopper roadmap page
//
// The roadmap is the "what should I learn first" view. The backend picks the
// eight highest-demand skills for a role and remembers how far along the user
// is; this page renders that and writes progress back as it changes.

import { loadPostings } from "./postings_table.js";

const API_BASE = 'http://localhost:8000';

// Matches the status values the backend accepts (StepStatusUpdate).
const STATUS_LABELS = {
    not_started: 'Not started',
    in_progress: 'In progress',
    completed: 'Completed',
};

// Skills that have quiz questions, so the page only offers "Practise" on the
// ones that can actually start a game. Filled in during initRoadmap.
let playableSkills = new Set();


// initialization
async function initRoadmap() {
    // get token from sign in and store in token variable
    const token = localStorage.getItem('token');

    // if token is missing, send user to sign in page
    if (!token) {
        window.location.href = '../html/sign_in_page.html';
        return;
    }

    try {
        // The roles list and the quiz skills are needed either way. The
        // roadmap itself 404s until one has been built, which is the normal
        // first visit rather than an error, so it is handled separately below.
        const [rolesResponse, skillsResponse] = await Promise.all([
            fetch(`${API_BASE}/roles`, { headers: authHeader(token) }),
            fetch(`${API_BASE}/game/skills`, { headers: authHeader(token) }),
        ]);

        if (rolesResponse.status === 401 || skillsResponse.status === 401) {
            handleExpiredSession();
            return;
        }

        if (rolesResponse.ok) {
            populateRoleOptions(await rolesResponse.json());
        }

        if (skillsResponse.ok) {
            const skills = await skillsResponse.json();
            playableSkills = new Set(skills.map((item) => item.skill));
        }

        await loadExistingRoadmap(token);
    } catch (error) {
        console.error('Initialization error:', error);
        showErrorMessage('Could not reach the server. Please try again.');
    }
}


function authHeader(token) {
    return { 'Authorization': `Bearer ${token || localStorage.getItem('token')}` };
}


// Fetch the roadmap the user already has, if there is one.
async function loadExistingRoadmap(token) {
    const response = await fetch(`${API_BASE}/roadmap`, { headers: authHeader(token) });

    if (response.status === 404) {
        // No roadmap built yet. Leave the empty-state text in place.
        return;
    }

    if (response.status === 401) {
        handleExpiredSession();
        return;
    }

    if (!response.ok) {
        showErrorMessage('Could not load your roadmap. Please try again.');
        return;
    }

    renderRoadmap(await response.json());
}


// Build (or rebuild) the roadmap for the selected role.
async function handleBuildRoadmap(event) {
    event.preventDefault();

    const select = document.getElementById('roadmapRoleSelect');
    const button = document.getElementById('build-roadmap-btn');
    const roleName = select ? select.value : '';

    if (!roleName) {
        showErrorMessage('Choose a role first.');
        return;
    }

    hideErrorMessage();
    // Rebuilding replaces every step, so stop a double click doing it twice.
    if (button) {
        button.disabled = true;
    }

    try {
        const response = await fetch(`${API_BASE}/roadmap`, {
            method: 'POST',
            headers: {
                ...authHeader(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ role_name: roleName }),
        });

        const data = await response.json();

        if (response.status === 401) {
            handleExpiredSession();
            return;
        }

        if (!response.ok) {
            showErrorMessage(data.detail || 'Could not build a roadmap for that role.');
            return;
        }

        renderRoadmap(data);
    } catch (error) {
        console.error('Could not build the roadmap:', error);
        showErrorMessage('Could not reach the server. Please try again.');
    } finally {
        if (button) {
            button.disabled = false;
        }
    }
}


// Save one step's progress.
async function handleStatusChange(stepId, status, selectElement) {
    hideErrorMessage();

    try {
        const response = await fetch(`${API_BASE}/roadmap/steps/${stepId}`, {
            method: 'PATCH',
            headers: {
                ...authHeader(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status }),
        });

        if (response.status === 401) {
            handleExpiredSession();
            return;
        }

        if (!response.ok) {
            // Put the dropdown back where it was, so what is on screen keeps
            // matching what is in the database.
            if (selectElement) {
                selectElement.value = selectElement.dataset.lastStatus;
            }
            showErrorMessage('Could not save that change. Please try again.');
            return;
        }

        if (selectElement) {
            selectElement.dataset.lastStatus = status;
        }
        updateSummaryCount();
    } catch (error) {
        console.error('Could not update the step:', error);
        if (selectElement) {
            selectElement.value = selectElement.dataset.lastStatus;
        }
        showErrorMessage('Could not reach the server. Please try again.');
    }
}


// UI functions

function populateRoleOptions(roles) {
    const select = document.getElementById('roadmapRoleSelect');
    if (!select) return;

    roles.forEach((role) => {
        const option = document.createElement('option');
        option.value = role.role_name;
        option.textContent = role.role_name;
        select.appendChild(option);
    });

    // Default to whatever the user last searched for, so the obvious next
    // click is the right one.
    const lastSearch = readStoredParameters();
    if (lastSearch && lastSearch.job_title) {
        const match = Array.from(select.options).find(
            (option) => option.value === lastSearch.job_title
        );
        if (match) {
            select.value = match.value;
        }
    }
}


// the search parameters the word cloud pages left behind, or null
function readStoredParameters() {
    try {
        const parsed = JSON.parse(localStorage.getItem('word_cloud_parameters'));
        return parsed && typeof parsed === 'object' ? parsed : null;
    } catch (error) {
        return null;
    }
}


function renderRoadmap(roadmap) {
    const body = document.getElementById('roadmap-steps-body');
    const heading = document.getElementById('roadmap-heading');
    if (!body) return;

    if (heading) {
        heading.innerText = `Your Steps for ${roadmap.role}`;
    }

    // The listings these steps came from. Not awaited: the roadmap is the
    // point of the page, and a slow or failed postings call should not hold it
    // up or blank it out.
    loadPostings({ roleName: roadmap.role });

    body.replaceChildren();

    if (!roadmap.steps || roadmap.steps.length === 0) {
        body.appendChild(emptyRow('No available data yet'));
        return;
    }

    roadmap.steps.forEach((step) => {
        body.appendChild(buildStepRow(step));
    });

    updateSummaryCount();
}


function buildStepRow(step) {
    const row = document.createElement('tr');

    row.appendChild(textCell(step.step_order));
    row.appendChild(textCell(step.skill));

    // progress
    const statusCell = document.createElement('td');
    statusCell.className = 'p-3 text-center';
    statusCell.appendChild(buildStatusSelect(step));
    row.appendChild(statusCell);

    // practise
    const practiseCell = document.createElement('td');
    practiseCell.className = 'p-3 text-center';
    practiseCell.appendChild(buildPractiseControl(step));
    row.appendChild(practiseCell);

    return row;
}


function buildStatusSelect(step) {
    const select = document.createElement('select');
    select.className = 'form-select';
    select.setAttribute('aria-label', `Progress for ${step.skill}`);
    select.dataset.lastStatus = step.status;

    Object.entries(STATUS_LABELS).forEach(([value, label]) => {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = label;
        if (value === step.status) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    select.onchange = () => handleStatusChange(step.step_id, select.value, select);

    return select;
}


function buildPractiseControl(step) {
    // Only the skills with questions behind them can start a game. The rest
    // say so rather than offering a button that would dead-end on a 404.
    if (!playableSkills.has(step.skill)) {
        const note = document.createElement('span');
        note.className = 'text-muted';
        note.innerText = 'No quiz yet';
        return note;
    }

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-secondary fw-semibold text-dark rounded-4 px-4';
    button.innerText = 'Practise';
    button.onclick = () => {
        // Same handoff the word cloud uses to start a game.
        localStorage.setItem('selected_skill', step.skill);
        window.location.href = '../html/game_difficulty.html';
    };
    return button;
}


function textCell(value) {
    const cell = document.createElement('td');
    cell.className = 'p-3 text-center';
    cell.innerText = value;
    return cell;
}


function emptyRow(message) {
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.className = 'p-3 text-center';
    cell.colSpan = 4;
    cell.innerText = message;
    row.appendChild(cell);
    return row;
}


// "3 of 8 done" under the heading, recalculated from what is on screen so it
// stays right after a status change without refetching the roadmap.
function updateSummaryCount() {
    const summary = document.getElementById('roadmap-summary');
    const body = document.getElementById('roadmap-steps-body');
    if (!summary || !body) return;

    const selects = body.querySelectorAll('select');
    if (selects.length === 0) return;

    const done = Array.from(selects).filter((s) => s.value === 'completed').length;
    summary.innerText =
        `${done} of ${selects.length} done. Highest demand first, based on the postings we hold.`;
}


// error message handling
function showErrorMessage(message) {
    const errorDiv = document.getElementById('roadmap-error-message');
    const errorText = document.getElementById('roadmap-error-text');

    if (errorDiv && errorText) {
        errorText.innerText = message;
        errorDiv.style.display = 'block';
    }
}


function hideErrorMessage() {
    const errorDiv = document.getElementById('roadmap-error-message');
    if (errorDiv) {
        errorDiv.style.display = 'none';
    }
}


function handleExpiredSession() {
    localStorage.removeItem('token');
    showErrorMessage('Session Expired. Please sign out and sign back in.');
    setTimeout(() => {
        window.location.href = '../html/sign_in_page.html';
    }, 7000);
}


document.addEventListener('DOMContentLoaded', () => {
    initRoadmap();

    const form = document.getElementById('roadmapForm');
    if (form) {
        form.addEventListener('submit', handleBuildRoadmap);
    }

    const close = document.getElementById('roadmap-error-close');
    if (close) {
        close.onclick = hideErrorMessage;
    }
});
