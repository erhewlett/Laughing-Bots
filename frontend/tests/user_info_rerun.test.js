/**
 * @jest-environment jsdom
 */

/*
 * Search Again on the profile page.
 *
 * It used to POST /wordcloud itself with industry hardcoded to "" while
 * passing job_title straight through. A search saved from the industry field
 * has no job_title, so re-running one sent neither field, the backend rejected
 * it as missing its one required field, and the button could never do anything
 * but say "please try again". The fetch also had no error handling, so a
 * backend that was down made the button do nothing at all.
 *
 * It now stages the search and lets the view page run it, so this checks the
 * wiring: what the button hands over, with the industry intact.
 */

require("../js/word_cloud_search.js");
require("../js/user_info_view_page.js");

const search = window.wordCloudSearch;

/*
 * Both paths under test end in a redirect, and jsdom implements no navigation,
 * so each click also prints a "Not implemented: navigation" notice. That is
 * jsdom telling us it did not follow the link, not a failure - what is being
 * checked here is the state the page staged before redirecting. window.location
 * cannot be redefined in this jsdom version, so the notice is left as is.
 */

const ROWS = [1, 2, 3]
    .map(
        (n) => `
        <tr id="recent-word-cloud-row-${n}">
            <td id="recent-word-cloud-role-${n}">N/A</td>
            <td><button id="rerun-word-cloud-btn-${n}">Search Again</button></td>
        </tr>`
    )
    .join("");

/** The two calls initDashboard makes, in the order Promise.all resolves them. */
function mockDashboard(recentSearches) {
    global.fetch = jest.fn((url) => {
        const body = String(url).includes("/me/recent")
            ? { last_game: null, recent_searches: recentSearches }
            : { username: "tester1" };

        return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve(body) });
    });
}

async function loadPage(recentSearches) {
    document.body.innerHTML = `
        <div id="user-welcome-message"></div>
        <div id="user-info-error-message" style="display: none;">
            <span id="user-info-error-text"></span>
        </div>
        <td id="recent-game-keyword"></td>
        <td id="recent-game-score"></td>
        <table><tbody>${ROWS}</tbody></table>
        <button id="generate-new-word-cloud-btn"></button>
        <a id="sign-out-link" href="#"></a>
    `;

    localStorage.clear();
    localStorage.setItem("token", "a-token");

    mockDashboard(recentSearches);

    document.dispatchEvent(new Event("DOMContentLoaded"));

    // let the two fetches and the render settle
    await new Promise(process.nextTick);
    await new Promise(process.nextTick);
}

describe("Search Again", () => {
    test("re-runs an industry-only saved search", async () => {
        await loadPage([
            {
                search_id: 1,
                job_title: null,
                industry: "Marketing",
                location: "Alexandria, Virginia",
                min_salary: null,
                word_count: 20,
                shape: "star",
            },
        ]);

        document.getElementById("rerun-word-cloud-btn-1").click();

        const staged = search.readStoredParameters();

        // the industry has to survive; this is the field that used to be blanked
        expect(staged.industry).toBe("Marketing");

        // and the staged search must be one the backend will accept
        expect(search.isSearchable(search.requestBodyFrom(staged))).toBe(true);
        expect(localStorage.getItem(search.KEYS.PENDING)).toBe("1");
    });

    test("re-runs a job-title saved search", async () => {
        await loadPage([
            {
                search_id: 2,
                job_title: "Data Analyst",
                industry: null,
                location: "",
                min_salary: 90000,
                word_count: 30,
                shape: "circle",
            },
        ]);

        document.getElementById("rerun-word-cloud-btn-1").click();

        const body = search.requestBodyFrom(search.readStoredParameters());

        expect(body.job_title).toBe("Data Analyst");
        expect(body.min_salary).toBe(90000);
        expect(search.isSearchable(body)).toBe(true);
    });

    test("staging drops the previous cloud so the old one cannot be redrawn", async () => {
        await loadPage([{ search_id: 3, job_title: "Data Analyst", industry: null }]);

        search.storeResults({ words: [{ skill: "Stale", weight: 100 }] });

        document.getElementById("rerun-word-cloud-btn-1").click();

        expect(localStorage.getItem(search.KEYS.RESULTS)).toBeNull();
        expect(search.shouldRunSearch()).toBe(true);
    });

    test("an industry-only row is labelled by its industry, not left blank", async () => {
        await loadPage([{ search_id: 4, job_title: null, industry: "Marketing" }]);

        expect(document.getElementById("recent-word-cloud-role-1").innerText).toBe(
            "Marketing"
        );
    });

    test("rows without a saved search stay hidden", async () => {
        await loadPage([{ search_id: 5, job_title: "Data Analyst", industry: null }]);

        expect(document.getElementById("recent-word-cloud-row-1").style.display).toBe(
            "table-row"
        );
        expect(document.getElementById("recent-word-cloud-row-2").style.display).toBe(
            "none"
        );
    });
});

describe("signing out", () => {
    test("leaves none of the search keys behind", async () => {
        await loadPage([]);

        search.stageSearch({ job_title: "Data Analyst" });
        search.storeResults({ words: [{ skill: "Python" }] });

        document.getElementById("sign-out-link").click();

        expect(localStorage.getItem("token")).toBeNull();
        expect(localStorage.getItem(search.KEYS.PARAMETERS)).toBeNull();
        expect(localStorage.getItem(search.KEYS.RESULTS)).toBeNull();
        expect(localStorage.getItem(search.KEYS.PENDING)).toBeNull();
    });
});
