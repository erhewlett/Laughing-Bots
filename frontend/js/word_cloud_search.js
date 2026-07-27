// word_cloud_search.js - the one owner of a word cloud search.
//
// Three pages start a search (the creation form, the signup form, and Search
// Again on the profile page) and one page runs it. They each used to keep their
// own copy of the localStorage keys and their own hand-built request body, and
// every one of them was subtly different:
//
//   * The profile page hardcoded industry:"" and posted the request itself, so
//     Search Again on a search saved from the industry field sent neither a
//     job title nor an industry and was rejected every time, with nothing but
//     "please try again" to show for it.
//   * The signup form wrote its parameters, cleared the cached cloud and set
//     the pending flag before validating anything, so an abandoned signup wiped
//     the cloud of whoever was already logged in on that browser and left a
//     bogus search staged to fire on their next visit.
//   * word_count and min_salary were stored as raw strings straight off the
//     form, so a half-filled form staged a search the backend rejected as a
//     validation error rather than as an empty result.
//
// So the keys, the request body, and the "is this a real search or a reload"
// decision live here, once. Loaded as a plain script before the page scripts,
// and required directly by the tests.
(function () {
    const KEYS = {
        PARAMETERS: "word_cloud_parameters",
        RESULTS: "word_cloud_results",
        PENDING: "word_cloud_pending",
    };

    // Matches SearchRequest in backend/app/schemas.py.
    const DEFAULT_WORD_COUNT = 30;
    const DEFAULT_SHAPE = "circle";

    function readJson(key) {
        try {
            return JSON.parse(localStorage.getItem(key));
        } catch (error) {
            console.warn(`Stored ${key} could not be read.`);

            return null;
        }
    }

    /** The stored search parameters, or null when there is nothing usable. */
    function readStoredParameters() {
        const parsed = readJson(KEYS.PARAMETERS);

        return parsed && typeof parsed === "object" ? parsed : null;
    }

    /** The cloud from the last real search, or null when there isn't one. */
    function readStoredResults() {
        const parsed = readJson(KEYS.RESULTS);

        return parsed && Array.isArray(parsed.words) ? parsed : null;
    }

    function asText(value) {
        if (value === null || value === undefined) {
            return "";
        }

        return String(value).trim();
    }

    function asNumber(value) {
        const text = asText(value);

        if (text === "") {
            return null;
        }

        const parsed = Number(text);

        return Number.isFinite(parsed) ? parsed : null;
    }

    /**
     * The POST /wordcloud body for a set of stored parameters.
     *
     * Forms hand over strings, and a field nobody filled in hands over "".
     * Sending those through as-is turned an unselected dropdown into a
     * validation error, so the defaults the backend documents are applied
     * here instead. industry is passed through rather than blanked, which is
     * what makes an industry-only search re-runnable.
     */
    function requestBodyFrom(parameters) {
        const stored = parameters || {};
        const wordCount = asNumber(stored.word_count);

        return {
            job_title: asText(stored.job_title),
            industry: asText(stored.industry),
            location: asText(stored.location),
            min_salary: asNumber(stored.min_salary),
            word_count: wordCount === null ? DEFAULT_WORD_COUNT : wordCount,
            shape: asText(stored.shape) || DEFAULT_SHAPE,
        };
    }

    /**
     * True when a search is missing the one field the backend insists on.
     *
     * Checked before the request so the page can say which field to fill in,
     * rather than relaying a validation error about a field the form on
     * screen may not even have.
     */
    function isSearchable(body) {
        return Boolean(body && (body.job_title || body.industry));
    }

    /**
     * True when the view page should call the backend rather than redraw.
     *
     * The backend records a Search row on every POST and the profile page
     * keeps only the five most recent, so posting on each page load meant a
     * few refreshes quietly erased the user's real history. A search is a
     * deliberate act: whoever asks for one stages it, and a plain reload
     * finds nothing staged and redraws what is stored.
     */
    function shouldRunSearch() {
        if (localStorage.getItem(KEYS.PENDING)) {
            return true;
        }

        return readStoredResults() === null;
    }

    /**
     * Stage a search for the view page to run, from any page that starts one.
     *
     * Drops the previous cloud at the same time: keeping it meant a search
     * that failed left the old one in storage, so a reload took the cache
     * branch and drew it under the new search's title.
     *
     * Call this only once the search is real - after a form validates, after
     * a signup succeeds - because it overwrites whatever the current session
     * had stored.
     */
    function stageSearch(parameters) {
        localStorage.setItem(KEYS.PARAMETERS, JSON.stringify(parameters));
        localStorage.setItem(KEYS.PENDING, "1");
        localStorage.removeItem(KEYS.RESULTS);
    }

    /**
     * What the view page does just before it calls the backend: consume the
     * flag so the search runs once, and drop any stale cloud with it.
     */
    function beginSearch() {
        localStorage.removeItem(KEYS.PENDING);
        localStorage.removeItem(KEYS.RESULTS);
    }

    function storeResults(result) {
        localStorage.setItem(KEYS.RESULTS, JSON.stringify(result));
    }

    /**
     * Forget everything about the current session's searches.
     *
     * Signing in, signing out and registering all need this: nobody is
     * obliged to sign out, so without it the next person to use the browser
     * could be shown the cloud belonging to the last one.
     */
    function clearSession() {
        localStorage.removeItem(KEYS.PARAMETERS);
        localStorage.removeItem(KEYS.RESULTS);
        localStorage.removeItem(KEYS.PENDING);
    }

    /**
     * The skills in a cloud that can actually start a quiz.
     *
     * Taken from the `playable` flag the /wordcloud response carries per
     * word. The view page used to fetch GET /game/skills for this instead,
     * above its own error handling, so a backend that was down left the page
     * saying "generating word cloud..." forever with nothing reported.
     */
    function playableSkills(cloud) {
        const words = (cloud && cloud.words) || [];

        return new Set(
            words.filter((word) => word.playable === true).map((word) => word.skill)
        );
    }

    const wordCloudSearch = {
        KEYS,
        DEFAULT_WORD_COUNT,
        DEFAULT_SHAPE,
        readStoredParameters,
        readStoredResults,
        requestBodyFrom,
        isSearchable,
        shouldRunSearch,
        stageSearch,
        beginSearch,
        storeResults,
        clearSession,
        playableSkills,
    };

    // Same dual export as api.js: window for the pages, module.exports for jest.
    if (typeof window !== "undefined") {
        window.wordCloudSearch = wordCloudSearch;
    }
    if (typeof module !== "undefined" && module.exports) {
        module.exports = wordCloudSearch;
    }
})();
