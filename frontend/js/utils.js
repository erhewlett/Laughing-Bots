// get username

export async function getUsername() {
    // check for username in local cache
    const token = localStorage.getItem('token');

    // if there is no token, user is not logged in
    if (!token) {
        return null;
    }

    try {
        // request user information from backend API 
        const response = await fetch('http://localhost:8000/auth/me', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });

        // if API response is successful, parse user data, and return username
        if (response.ok) {
            const userData = await response.json();
            return userData.username;
        } else {
            // in the case of an invalid/expired token
            console.warn('Authentication token is invalid or expired.');
            localStorage.removeItem('token');
            return null;
        }
    } catch (error) {
        // catch network/server 
        console.error('Network/Server error.');
        return null;
    }
}