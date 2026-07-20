// api.js - one function per backend route, handles base url, auth token,
// json parsing, and turns backend errors into a readable message.
// full endpoint docs are in the README.
//
// login: api.login() returns { access_token }, save it with api.setToken().
// after that every call auto-sends the token. api.logout() clears it.

// wrapped in an iife so only `api` ends up global
(function () {
    // backend url, change here if port/host changes
    const BASE_URL = 'http://localhost:8000';

    // localStorage key for the jwt, same one sign_in_page.js uses
    const TOKEN_KEY = 'token';

    // --- session stuff -----------------------------------------------------

    function getToken() {
        return localStorage.getItem(TOKEN_KEY);
    }

    function setToken(token) {
        localStorage.setItem(TOKEN_KEY, token);
    }

    function clearToken() {
        localStorage.removeItem(TOKEN_KEY);
    }

    // true if we have a token saved, useful for gating logged in pages:
    //   if (!api.isLoggedIn()) window.location.href = '../html/sign_in_page.html';
    function isLoggedIn() {
        return getToken() !== null;
    }

    // clears the session, pass a url to redirect after logging out
    function logout(redirectTo) {
        clearToken();
        if (redirectTo) {
            window.location.href = redirectTo;
        }
    }

    // --- error handling ------------------------------------------------------

    // fastapi sends errors two ways:
    //   * normal HTTPExceptions (401/404/409/422 we raised) -> detail is a string
    //   * pydantic validation 422s -> detail is an array of { msg, loc, ... }
    // this flattens both into one string so we never show [object Object]
    function detailMessage(errorData) {
        const detail = errorData && errorData.detail;
        if (Array.isArray(detail)) {
            return (detail[0] && detail[0].msg) || 'Invalid input';
        }
        if (typeof detail === 'string') {
            return detail;
        }
        return 'Request failed';
    }

    // some skills have a slash in them (like "CI/CD"). the backend route is
    // fine with a literal slash so we keep it and encode everything else
    function encodeSkill(skill) {
        return String(skill).split('/').map(encodeURIComponent).join('/');
    }

    // --- the one function everything else calls -----------------------------

    async function request(method, path, body) {
        const headers = { 'Content-Type': 'application/json' };

        // attach the token if we have one, endpoints that don't need auth
        // just ignore it so it's fine to always send it
        const token = getToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const options = { method, headers };
        if (body !== undefined) {
            options.body = JSON.stringify(body);
        }

        const response = await fetch(`${BASE_URL}${path}`, options);

        // try to parse json, some responses might be empty
        let data = null;
        try {
            data = await response.json();
        } catch (_e) {
            data = null;
        }

        // not a 2xx? throw with the backend's message so callers can just
        // do catch (e) { showError(e.message); }
        if (!response.ok) {
            const err = new Error(detailMessage(data));
            err.status = response.status;
            err.data = data;
            throw err;
        }

        return data;
    }

    // basic verbs if you want to make your own call
    const get = (path) => request('GET', path);
    const post = (path, body) => request('POST', path, body);
    const patch = (path, body) => request('PATCH', path, body);

    // --- actual endpoints ----------------------------------------------------

    const api = {
        // session
        getToken, setToken, clearToken, isLoggedIn, logout,
        // escape hatches
        get, post, patch,

        // auth
        register: (body) => post('/auth/register', body),
        login: (username, password) => post('/auth/login', { username, password }),
        me: () => get('/auth/me'),

        // metadata
        getRoles: () => get('/roles'),

        // word cloud
        generateCloud: (body) => post('/wordcloud', body),

        // game
        getGameSkills: () => get('/game/skills'),
        getQuiz: (skill, difficulty) =>
            get(`/game/${encodeSkill(skill)}?difficulty=${encodeURIComponent(difficulty)}`),
        submitQuiz: (skill, body) => post(`/game/${encodeSkill(skill)}/submit`, body),

        // history
        getRecent: () => get('/me/recent'),

        // roadmap
        createRoadmap: (role_name) => post('/roadmap', { role_name }),
        getRoadmap: () => get('/roadmap'),
        updateStep: (stepId, status) => patch(`/roadmap/steps/${stepId}`, { status }),
    };

    // make it available as window.api and also as a commonjs export
    // so jest/jsdom tests can require('../js/api.js') the same file
    if (typeof window !== 'undefined') {
        window.api = api;
    }
    if (typeof module !== 'undefined' && module.exports) {
        module.exports = api;
    }
})();