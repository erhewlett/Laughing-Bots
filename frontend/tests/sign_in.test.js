// simulate a browser environment (jsdom) for testing for this file

/**
 * @jest-environment jsdom
 */

// word_cloud_search.js owns the search keys and puts itself on window, exactly
// as the plain <script> tag on sign_in_page.html does. Loaded first because
// signing in clears the previous session's search through it.
require('../js/word_cloud_search.js');

// load js file
require('../js/sign_in_page.js');

describe('Sign In Page', () => {
    beforeEach(() => {
        // each test starts from a clean session
        localStorage.clear();

        // set up HTML needed for testing
        document.body.innerHTML = `
            <form>
                <input id="accountUsernameInput" />
                <input id="accountPasswordInput" />
                <button id="sign-in-btn"></button>
            </form>
            <div id="error-message" style="display: none;"></div>
        `;
        // manually create DOMContentLoaded event for javascript to activate required listeners
        document.dispatchEvent(new Event('DOMContentLoaded'));
    });

    // define unit test
    test('should show error message when login fails', async () => {
        // replace browser network request to backend with jest.fn()
        global.fetch = jest.fn(() =>
            // simulate a 401 error response from backend server (invalid credentials)
            // wrap in Promise.resolve (fetch returns a Promise)
            Promise.resolve({
                ok: false,
                json: () => Promise.resolve({ detail: 'Invalid credentials' }),
            })
        );

        // store required elements in variables
        const form = document.querySelector('form');                        // form element
        const username = document.getElementById('accountUsernameInput');   // username
        const password = document.getElementById('accountPasswordInput');   // password
        const errorMessageDiv = document.getElementById('error-message');   // error message div HTML element

        // simulate user input
        username.value = 'testuser';
        password.value = 'incorrectpassword';

        // simulate submit event
        form.dispatchEvent(new Event('submit'));

        // pause to make time for JavaScript to finish pending background work
        await new Promise(process.nextTick);

        // verify that the UI updated as expected for the test
        expect(errorMessageDiv.style.display).toBe('block');
        expect(errorMessageDiv.textContent).toContain('Invalid credentials');

    });

    test('a successful login does not inherit the last user\'s word cloud', async () => {
        // nobody is obliged to sign out, so without this the next person to log
        // in on this browser is shown the cloud belonging to the previous one
        localStorage.setItem('word_cloud_results', JSON.stringify({ words: [{ skill: 'Python' }] }));
        localStorage.setItem('word_cloud_parameters', JSON.stringify({ job_title: 'Data Analyst' }));
        localStorage.setItem('word_cloud_pending', '1');

        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: true,
                json: () => Promise.resolve({ access_token: 'a-token' }),
            })
        );

        document.getElementById('accountUsernameInput').value = 'seconduser';
        document.getElementById('accountPasswordInput').value = 'password123';

        document.querySelector('form').dispatchEvent(new Event('submit'));

        await new Promise(process.nextTick);

        expect(localStorage.getItem('token')).toBe('a-token');
        expect(localStorage.getItem('word_cloud_results')).toBeNull();
        expect(localStorage.getItem('word_cloud_parameters')).toBeNull();
        expect(localStorage.getItem('word_cloud_pending')).toBeNull();
    });
});