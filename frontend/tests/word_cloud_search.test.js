/**
 * @jest-environment jsdom
 */

/*
 * These used to restate the search rules inside this file, because the page
 * that ran them was an ES module reaching for a live backend. A restated rule
 * cannot catch a regression in the shipped file, which is the whole point of
 * pinning it down - so the rules now live in js/word_cloud_search.js and this
 * requires that file directly. Every page that starts a search uses it too.
 */

const search = require("../js/word_cloud_search.js");

const { PARAMETERS, RESULTS, PENDING } = search.KEYS;

const CLOUD = { words: [{ skill: "Python", weight: 100, playable: true }] };

beforeEach(() => {
    localStorage.clear();
});

describe("deciding whether to run a search or redraw", () => {
    /*
     * The backend records a Search row on every POST /wordcloud and the profile
     * page keeps only the five most recent, so posting on every page load meant
     * a few refreshes quietly erased the user's real search history.
     */
    test("a staged search runs", () => {
        localStorage.setItem(PENDING, "1");
        expect(search.shouldRunSearch()).toBe(true);
    });

    test("a staged search runs even when an older cloud is cached", () => {
        localStorage.setItem(RESULTS, JSON.stringify(CLOUD));
        localStorage.setItem(PENDING, "1");
        expect(search.shouldRunSearch()).toBe(true);
    });

    test("a plain reload redraws instead of recording another search", () => {
        localStorage.setItem(RESULTS, JSON.stringify(CLOUD));
        expect(search.shouldRunSearch()).toBe(false);
    });

    test("nothing cached still runs a search", () => {
        expect(search.shouldRunSearch()).toBe(true);
    });

    test("unreadable cached results fall back to searching", () => {
        localStorage.setItem(RESULTS, "{not json");
        expect(search.shouldRunSearch()).toBe(true);
    });

    test("a cached value without a words array is not treated as a cloud", () => {
        localStorage.setItem(RESULTS, JSON.stringify({ role: "Data Analyst" }));
        expect(search.shouldRunSearch()).toBe(true);
    });

    test("repeated reloads never run more than the one real search", () => {
        search.stageSearch({ job_title: "Data Analyst" });
        expect(search.shouldRunSearch()).toBe(true);

        search.beginSearch();
        search.storeResults(CLOUD);

        for (let reload = 0; reload < 5; reload++) {
            expect(search.shouldRunSearch()).toBe(false);
        }
    });

    test("a failed search does not leave the previous cloud on screen", () => {
        // cloud from search A is cached, then search B is staged and fails.
        // reloading must not draw A under B's title.
        localStorage.setItem(RESULTS, JSON.stringify(CLOUD));
        search.stageSearch({ job_title: "Software Engineer" });

        expect(search.shouldRunSearch()).toBe(true);
        search.beginSearch(); // the request goes out, and fails

        expect(localStorage.getItem(RESULTS)).toBeNull();
        expect(search.shouldRunSearch()).toBe(true); // a reload retries
    });
});

describe("staging a search", () => {
    test("stores the parameters, flags it, and drops the stale cloud", () => {
        localStorage.setItem(RESULTS, JSON.stringify(CLOUD));

        search.stageSearch({ job_title: "Data Analyst", shape: "star" });

        expect(search.readStoredParameters().job_title).toBe("Data Analyst");
        expect(localStorage.getItem(PENDING)).toBe("1");
        expect(localStorage.getItem(RESULTS)).toBeNull();
    });

    test("clearSession forgets all three keys", () => {
        search.stageSearch({ job_title: "Data Analyst" });
        search.storeResults(CLOUD);

        search.clearSession();

        expect(localStorage.getItem(PARAMETERS)).toBeNull();
        expect(localStorage.getItem(RESULTS)).toBeNull();
        expect(localStorage.getItem(PENDING)).toBeNull();
    });
});

describe("stored search parameters", () => {
    test("missing parameters return null rather than throwing", () => {
        // reading .job_title straight off JSON.parse(null) threw a TypeError
        // above the page's try block, so it hung on "generating..." forever
        expect(search.readStoredParameters()).toBeNull();
    });

    test("unreadable parameters return null rather than throwing", () => {
        localStorage.setItem(PARAMETERS, "{not json");
        expect(search.readStoredParameters()).toBeNull();
    });

    test("a stored string is not accepted as parameters", () => {
        localStorage.setItem(PARAMETERS, JSON.stringify("nope"));
        expect(search.readStoredParameters()).toBeNull();
    });
});

describe("building the request body", () => {
    /*
     * Forms hand over strings, and a field nobody filled in hands over "".
     * Passing those through turned an unselected dropdown into a validation
     * error instead of a search.
     */
    test("numbers come through as numbers", () => {
        const body = search.requestBodyFrom({
            job_title: "Data Analyst",
            min_salary: "90000",
            word_count: "20",
        });

        expect(body.min_salary).toBe(90000);
        expect(body.word_count).toBe(20);
    });

    test("an empty word count falls back to the documented default", () => {
        const body = search.requestBodyFrom({ job_title: "Data Analyst", word_count: "" });

        expect(body.word_count).toBe(search.DEFAULT_WORD_COUNT);
    });

    test("an empty shape falls back to the documented default", () => {
        // the backend requires shape to match ^[A-Za-z0-9_-]+$, so "" is a 422
        const body = search.requestBodyFrom({ job_title: "Data Analyst", shape: "" });

        expect(body.shape).toBe(search.DEFAULT_SHAPE);
    });

    test("an empty minimum salary is null, not zero", () => {
        const body = search.requestBodyFrom({ job_title: "Data Analyst", min_salary: "" });

        expect(body.min_salary).toBeNull();
    });

    test("a deliberate zero minimum salary survives", () => {
        const body = search.requestBodyFrom({ job_title: "Data Analyst", min_salary: 0 });

        expect(body.min_salary).toBe(0);
    });

    test("a non-numeric salary becomes null rather than NaN", () => {
        const body = search.requestBodyFrom({ job_title: "Data Analyst", min_salary: "lots" });

        expect(body.min_salary).toBeNull();
    });

    test("industry is passed through, not blanked", () => {
        // the profile page hardcoded industry:"" while passing job_title
        // through, so an industry-only saved search re-ran as neither and was
        // rejected every single time
        const body = search.requestBodyFrom({ job_title: null, industry: "Marketing" });

        expect(body.industry).toBe("Marketing");
    });

    test("whitespace-only fields are treated as absent", () => {
        const body = search.requestBodyFrom({ job_title: "   ", industry: "Marketing" });

        expect(body.job_title).toBe("");
    });

    test("missing parameters do not throw", () => {
        expect(() => search.requestBodyFrom(null)).not.toThrow();
        expect(() => search.requestBodyFrom(undefined)).not.toThrow();
    });
});

describe("knowing a search is missing its one required field", () => {
    test("a job title is enough", () => {
        expect(search.isSearchable({ job_title: "Data Analyst", industry: "" })).toBe(true);
    });

    test("an industry alone is enough", () => {
        expect(search.isSearchable({ job_title: "", industry: "Marketing" })).toBe(true);
    });

    test("neither is not", () => {
        expect(search.isSearchable({ job_title: "", industry: "" })).toBe(false);
    });

    test("an industry-only saved search is re-runnable end to end", () => {
        // the exact row that could never be re-run before
        const saved = { job_title: null, industry: "Marketing", location: "Alexandria, Virginia" };

        search.stageSearch(saved);
        const body = search.requestBodyFrom(search.readStoredParameters());

        expect(search.isSearchable(body)).toBe(true);
        expect(body.industry).toBe("Marketing");
    });
});

describe("which words can start a quiz", () => {
    /*
     * Taken from the flag on the /wordcloud response. The page used to fetch
     * GET /game/skills for this, above its own error handling, so a backend
     * that was down left it saying "generating word cloud..." forever.
     */
    test("only the playable ones", () => {
        const playable = search.playableSkills({
            words: [
                { skill: "Python", playable: true },
                { skill: "Excel", playable: false },
                { skill: "SQL", playable: true },
            ],
        });

        expect([...playable].sort()).toEqual(["Python", "SQL"]);
    });

    test("a cloud with no playable words yields an empty set", () => {
        const playable = search.playableSkills({ words: [{ skill: "Excel" }] });

        expect(playable.size).toBe(0);
    });

    test("a missing or malformed cloud does not throw", () => {
        expect(search.playableSkills(null).size).toBe(0);
        expect(search.playableSkills({}).size).toBe(0);
    });
});
