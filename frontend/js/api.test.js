/**
 * @jest-environment jsdom
 */

// load the helper (works because api.js also does module.exports)
const api = require('../js/api.js');

describe('api.js helper', () => {
    beforeEach(() => {
        // start each test with a clean session and a fresh fetch mock
        localStorage.clear();
        global.fetch = undefined;
    });

    test('token helpers read/write/clear the same "token" key as sign in', () => {
        api.setToken('abc123');
        expect(localStorage.getItem('token')).toBe('abc123');
        expect(api.getToken()).toBe('abc123');
        api.clearToken();
        expect(api.getToken()).toBeNull();
    });

    test('attaches Authorization: Bearer <token> when logged in', async () => {
        api.setToken('abc123');
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({ ok: 1 }) })
        );

        await api.getRecent();

        const [, options] = global.fetch.mock.calls[0];
        expect(options.headers.Authorization).toBe('Bearer abc123');
    });

    test('omits Authorization header when not logged in', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
        );

        await api.getRoles();

        const [, options] = global.fetch.mock.calls[0];
        expect(options.headers.Authorization).toBeUndefined();
    });

    test('throws with the backend string detail on error', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                status: 401,
                json: () => Promise.resolve({ detail: 'Invalid username or password.' }),
            })
        );

        await expect(api.login('u', 'p')).rejects.toThrow('Invalid username or password.');
    });

    test('flattens a 422 array detail into the first message', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({
                ok: false,
                status: 422,
                json: () =>
                    Promise.resolve({ detail: [{ msg: 'Password is too long.', loc: ['body', 'password'] }] }),
            })
        );

        // should NOT throw "[object Object]"
        await expect(api.register({ username: 'x', password: 'y' })).rejects.toThrow('Password is too long.');
    });

    test('keeps a literal slash in skill names like CI/CD', async () => {
        global.fetch = jest.fn(() =>
            Promise.resolve({ ok: true, json: () => Promise.resolve({}) })
        );

        await api.getQuiz('CI/CD', 'easy');

        const [url] = global.fetch.mock.calls[0];
        expect(url).toContain('/game/CI/CD?difficulty=easy');
    });
});
