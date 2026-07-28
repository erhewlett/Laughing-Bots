// The job postings behind a search, as a table.
//
// Used by the roadmap page, where the listings explain why the steps are
// ordered the way they are. It was briefly on the word cloud page too, but a
// table of jobs under the cloud competed with the cloud itself and with the
// route into the game, which are what that page is for.
//
// Kept as its own module rather than folded into roadmap_page.js because the
// endpoint takes a whole search, not just a role, so this is reusable the day
// another page wants to show the same evidence.
//
// The markup it fills is a plain Bootstrap table with a summary line above it.

const API_BASE = 'http://localhost:8000';

// Enough to make the point on screen without turning the page into a job board.
export const POSTINGS_LIMIT = 10;


/* Load the postings for a search and render them.
 *
 * `search` takes the same fields as POST /wordcloud, so a stored word cloud
 * search can be handed straight over. `roleName` is the shortcut the roadmap
 * page uses, where the role is already known and there is no search to reuse.
 *
 * Failures are reported in the summary line and nowhere else. This is
 * supporting evidence on both pages, and it should never take down the thing
 * it is evidence for.
 */
export async function loadPostings({
    search = {},
    roleName = null,
    summaryId = 'postings-summary',
    bodyId = 'postings-body',
} = {}) {
    const summary = document.getElementById(summaryId);
    const body = document.getElementById(bodyId);
    if (!summary || !body) return;

    const query = new URLSearchParams({ limit: String(POSTINGS_LIMIT) });
    const jobTitle = roleName || search.job_title;
    if (jobTitle) query.set('job_title', jobTitle);
    if (search.industry) query.set('industry', search.industry);
    if (search.location) query.set('location', search.location);
    if (search.min_salary !== null && search.min_salary !== undefined && search.min_salary !== '') {
        query.set('min_salary', String(search.min_salary));
    }

    try {
        const response = await fetch(`${API_BASE}/postings?${query}`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });

        if (!response.ok) {
            summary.innerText = 'Could not load the postings for this search.';
            return;
        }

        render(await response.json(), summary, body);
    } catch (error) {
        console.error('Could not load postings:', error);
        summary.innerText = 'Could not load the postings for this search.';
    }
}


function render(data, summary, body) {
    if (!data.postings || data.postings.length === 0) {
        summary.innerText = 'No postings matched this search.';
        return;
    }

    const shown = data.postings.length;
    summary.innerText = shown < data.total
        ? `Showing ${shown} of ${data.total} ${data.role} postings from the last 30 days.`
        : `All ${data.total} ${data.role} postings from the last 30 days.`;

    body.replaceChildren();
    data.postings.forEach((posting) => body.appendChild(buildRow(posting)));
}


function buildRow(posting) {
    const row = document.createElement('tr');

    row.appendChild(cell(posting.title || 'Untitled role'));
    row.appendChild(cell(posting.company_name || 'Not listed'));
    row.appendChild(cell(posting.location || 'Not listed'));
    row.appendChild(cell(formatSalaryRange(posting.salary_min, posting.salary_max)));

    const posted = cell(formatPostedDate(posting.date_posted));
    posted.classList.add('text-center');
    row.appendChild(posted);

    const linkCell = document.createElement('td');
    linkCell.className = 'p-3 text-center';
    if (posting.source_url) {
        const link = document.createElement('a');
        link.href = posting.source_url;
        link.target = '_blank';
        // These URLs come from an external job feed, so don't hand the page
        // they open a reference back to this one.
        link.rel = 'noopener noreferrer';
        link.innerText = 'View';
        link.setAttribute('aria-label', `View the listing for ${posting.title || 'this role'}`);
        linkCell.appendChild(link);
    } else {
        linkCell.innerText = 'Not listed';
    }
    row.appendChild(linkCell);

    return row;
}


function cell(value) {
    const td = document.createElement('td');
    td.className = 'p-3';
    // innerText, not innerHTML: these strings come from a third-party feed.
    td.innerText = value;
    return td;
}


// Most scraped postings carry no salary at all, so say so plainly rather than
// leaving an empty cell or rendering a misleading "$0".
function formatSalaryRange(low, high) {
    if (low && high) return `${formatMoney(low)} - ${formatMoney(high)}`;
    if (low) return `${formatMoney(low)}+`;
    if (high) return `Up to ${formatMoney(high)}`;
    return 'Not listed';
}


export function formatMoney(value) {
    const amount = Number(value);
    if (!Number.isFinite(amount)) return value;
    return amount.toLocaleString('en-US', {
        style: 'currency',
        currency: 'USD',
        maximumFractionDigits: 0,
    });
}


function formatPostedDate(value) {
    if (!value) return 'Unknown';
    const when = new Date(value);
    if (Number.isNaN(when.getTime())) return 'Unknown';
    return when.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
