// javascript for JobHopper sign in page

document.addEventListener('DOMContentLoaded', () => {

    // set variable loginForm for first <form> element
    const loginForm = document.querySelector('form');

    // set variable signInBtn for the sign in button (id = 'sign-in-btn') in the sign in page document
    const signInBtn = document.getElementById('sign-in-btn');

    // event listener for sign in button
    loginForm.addEventListener('submit', async (e) => {
        // prevent the default form submission behavior (which would reload the page)
        e.preventDefault();

        // get the values of the username and password input fields (from sign_in_page.html)
        // store in respective variables: username and password
        const username = document.getElementById('accountUsernameInput').value;
        const password = document.getElementById('accountPasswordInput').value;

        try {
            // 1. send a POST request to the backend server for authentication
            // fetch function takes the URL of the backend endpoint and a JavaScript object (configuration) as parameters
            const response = await fetch('http://localhost:8000/auth/login', {
                // method is POST, as we are sending data to the server
                method: 'POST',
                // set the headers to indicate that we are sending JSON data (content-type: application/json)
                headers: {
                    'Content-Type': 'application/json',
                },
                // send the username and password as JSON in the request body
                body: JSON.stringify({ username, password }),
            });

            // 2. if the response from the server is successful
            if (response.ok) {
                // convert response from the backend server to Javascript object (JSON format) and store in variable data
                const data = await response.json();

                // store the JWT token in localStorage for future authenticated requests, allowing other pages to verify that the user is logged in
                // access_token is the key defined in the backend (contains the JWT token returned by the backend server upon successful login)
                localStorage.setItem('token', data.access_token);

                // alert the user that the login was successful (for testing)
                // alert('Login successful!');

                // redirect the user to the user info view page after successful login
                window.location.href = '../html/user_info_view_page.html';
            // 3. if the response from the server is not successful (e.g., invalid credentials)
            // the server received the request, but the server did not approve the request (e.g., invalid credentials)
            } else {
                // convert response from the backend server to Javascript object (JSON format) and store in variable errorData
                const errorData = await response.json();

                // handle 422 error (FastAPI validation errors are arrays)
                if (Array.isArray(errorData.detail)) {
                    // grab the first error message from the array and show it in an alert
                    const firstError = errorData.detail[0].msg || "Invalid input";
                    alert(`Validation error: ${firstError}`);
                } else {

                // show error detail if it exists, otherwise show 'Invalid credentials' message
                alert(`Login failed: ${errorData.detail || 'Invalid credentials'}`);
                }
            }
        // catch any event in which the request could not make it to the backend server (e.g., server is down, network issues, etc.)
        // note: there is no response to parse in this case, as the request never made it to the backend server
        } catch (error) {
            console.error('Error during login:', error);
            alert('An error occurred during login. Please try again later.');
        }
    });
});
