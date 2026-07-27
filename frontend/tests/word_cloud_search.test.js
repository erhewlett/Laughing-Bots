/**
 * @jest-environment jsdom
 */

/*
 * The word cloud view page used to POST /wordcloud on every load. The backend
 * records a Search row on each POST and the profile page keeps only the five
 * most recent, so refreshing the page a few times quietly erased the user's
 * real search history.
 *
 * A search now only runs when someone actually asked for one: the creation
 * form sets word_cloud_pending, and the profile page's Search Again leaves
 * fresh results behind. A plain reload finds neither and redraws what is
 * stored.
 *
 * These cover that decision directly. word_cloud_render.js is an ES module
 * that runs on DOMContentLoaded and reaches for a live backend, so the rule is
 * restated here rather than imported.
 */

const RESULTS_KEY = "word_cloud_results";
const PENDING_KEY = "word_cloud_pending";

function readStoredResults() {
    try {
        const parsed = JSON.parse(localStorage.getItem(RESULTS_KEY));
        return parsed && Array.isArray(parsed.words) ? parsed : null;
    } catch (error) {
        return null;
    }
}

/** True when the page should call the backend rather than redraw. */
function shouldRunSearch() {
    if (!localStorage.getItem(PENDING_KEY)) {
        if (readStoredResults()) {
            return false;
        }
    }
    return true;
}

const CLOUD = { words: [{ skill: "Python", weight: 100 }] };

describe("word cloud search gating", () => {
    beforeEach(() => {
        localStorage.clear();
    });

    test("submitting the creation form runs a search", () => {
        localStorage.setItem(PENDING_KEY, "1");
        expect(shouldRunSearch()).toBe(true);
    });

    test("submitting runs a search even when an older cloud is cached", () => {
        localStorage.setItem(RESULTS_KEY, JSON.stringify(CLOUD));
        localStorage.setItem(PENDING_KEY, "1");
        expect(shouldRunSearch()).toBe(true);
    });

    test("a plain reload redraws instead of recording another search", () => {
        localStorage.setItem(RESULTS_KEY, JSON.stringify(CLOUD));
        expect(shouldRunSearch()).toBe(false);
    });

    test("Search Again redraws the results it already fetched", () => {
        // the profile page POSTs itself, then stores the cloud and redirects,
        // so the view page must not fetch a second time
        localStorage.setItem(RESULTS_KEY, JSON.stringify(CLOUD));
        expect(shouldRunSearch()).toBe(false);
    });

    test("nothing cached still runs a search", () => {
        expect(shouldRunSearch()).toBe(true);
    });

    test("unreadable cached results fall back to searching", () => {
        localStorage.setItem(RESULTS_KEY, "{not json");
        expect(shouldRunSearch()).toBe(true);
    });

    test("a cached value without a words array is not treated as a cloud", () => {
        localStorage.setItem(RESULTS_KEY, JSON.stringify({ role: "Data Analyst" }));
        expect(shouldRunSearch()).toBe(true);
    });

    test("repeated reloads never run more than the one real search", () => {
        localStorage.setItem(PENDING_KEY, "1");
        expect(shouldRunSearch()).toBe(true);

        // the page consumes the flag and stores what it fetched
        localStorage.removeItem(PENDING_KEY);
        localStorage.setItem(RESULTS_KEY, JSON.stringify(CLOUD));

        for (let reload = 0; reload < 5; reload++) {
            expect(shouldRunSearch()).toBe(false);
        }
    });
});

describe("stored search parameters", () => {
    function readStoredParameters() {
        try {
            const parsed = JSON.parse(localStorage.getItem("word_cloud_parameters"));
            return parsed && typeof parsed === "object" ? parsed : null;
        } catch (error) {
            return null;
        }
    }

    beforeEach(() => {
        localStorage.clear();
    });

    test("missing parameters return null rather than throwing", () => {
        // reading .job_title straight off JSON.parse(null) threw a TypeError
        // above the page's try block, so it hung on "generating..." forever
        expect(readStoredParameters()).toBeNull();
    });

    test("unreadable parameters return null rather than throwing", () => {
        localStorage.setItem("word_cloud_parameters", "{not json");
        expect(readStoredParameters()).toBeNull();
    });

    test("a stored string is not accepted as parameters", () => {
        localStorage.setItem("word_cloud_parameters", JSON.stringify("nope"));
        expect(readStoredParameters()).toBeNull();
    });

    test("real parameters come back", () => {
        localStorage.setItem(
            "word_cloud_parameters",
            JSON.stringify({ job_title: "Data Analyst", shape: "circle" })
        );
        expect(readStoredParameters().job_title).toBe("Data Analyst");
    });
});
