/**
 * @jest-environment jsdom
 */

/*
 * These require the shipped rules from js/game_flow.js rather than restating
 * them, so a regression in the file the quiz page actually loads fails here.
 *
 * The bug being pinned down: when the final submission failed, the page
 * re-enabled the Submit button "to allow another go at submitting", but the
 * button's only handler graded an answer. So the retry re-entered the answer
 * flow, re-recorded the last answer (a disabled radio is still :checked), and
 * left submittedAnswers one longer than the quiz - after which every attempt
 * failed the length check and the attempt could never be submitted at all.
 */

const flow = require("../js/game_flow.js");

const { PHASE } = flow;

describe("what pressing Submit means", () => {
    test("grades the answer on screen while answering", () => {
        expect(flow.submitClickAction(PHASE.ANSWERING, false)).toBe("grade-answer");
    });

    test("retries the submission after one failed", () => {
        // the whole point: this must NOT be "grade-answer"
        expect(flow.submitClickAction(PHASE.SUBMIT_FAILED, false)).toBe(
            "retry-submit"
        );
    });

    test("is ignored while an answer is being graded", () => {
        expect(flow.submitClickAction(PHASE.GRADING, false)).toBe("ignore");
    });

    test("is ignored while the quiz is being submitted", () => {
        expect(flow.submitClickAction(PHASE.SUBMITTING, false)).toBe("ignore");
    });

    test("is ignored once the quiz is graded", () => {
        expect(flow.submitClickAction(PHASE.FINISHED, false)).toBe("ignore");
    });

    test("is ignored while feedback is on screen, whatever the phase", () => {
        Object.values(PHASE).forEach((phase) => {
            expect(flow.submitClickAction(phase, true)).toBe("ignore");
        });
    });

    test("an unknown phase is ignored rather than guessed at", () => {
        expect(flow.submitClickAction("something-else", false)).toBe("ignore");
    });
});

describe("selecting an answer", () => {
    test("re-enables Submit while answering", () => {
        expect(flow.acceptsAnswerSelection(PHASE.ANSWERING, false)).toBe(true);
    });

    test("does nothing once the clock has run out and the quiz went in", () => {
        expect(flow.acceptsAnswerSelection(PHASE.SUBMITTING, false)).toBe(false);
        expect(flow.acceptsAnswerSelection(PHASE.FINISHED, false)).toBe(false);
    });

    test("does nothing while feedback is showing", () => {
        expect(flow.acceptsAnswerSelection(PHASE.ANSWERING, true)).toBe(false);
    });

    test("does not let a failed submission be turned back into answering", () => {
        expect(flow.acceptsAnswerSelection(PHASE.SUBMIT_FAILED, false)).toBe(false);
    });
});

describe("the countdown", () => {
    test("runs while the player is answering", () => {
        expect(flow.clockRuns(PHASE.ANSWERING, false)).toBe(true);
    });

    test("keeps running while one answer is graded - that is their time", () => {
        expect(flow.clockRuns(PHASE.GRADING, false)).toBe(true);
    });

    test("freezes while the correct answer is being read", () => {
        expect(flow.clockRuns(PHASE.ANSWERING, true)).toBe(false);
        expect(flow.clockRuns(PHASE.GRADING, true)).toBe(false);
    });

    test("stops once the quiz is on its way or graded", () => {
        expect(flow.clockRuns(PHASE.SUBMITTING, false)).toBe(false);
        expect(flow.clockRuns(PHASE.SUBMIT_FAILED, false)).toBe(false);
        expect(flow.clockRuns(PHASE.FINISHED, false)).toBe(false);
    });
});

describe("the clock running out", () => {
    test("submits what was answered", () => {
        expect(flow.expiryShouldSubmit(PHASE.ANSWERING)).toBe(true);
    });

    test("still submits when it runs out mid-grade", () => {
        // sharing one flag with per-answer grading meant the expiry skipped
        // submitting and the grade returned to a finished game, so the
        // attempt was never sent at all
        expect(flow.expiryShouldSubmit(PHASE.GRADING)).toBe(true);
    });

    test("does not submit a second time over one already in flight", () => {
        expect(flow.expiryShouldSubmit(PHASE.SUBMITTING)).toBe(false);
    });

    test("does not resubmit an already graded quiz", () => {
        expect(flow.expiryShouldSubmit(PHASE.FINISHED)).toBe(false);
    });
});

describe("recording answers", () => {
    test("records a new answer", () => {
        const answers = [];
        expect(flow.recordAnswer(answers, { question_id: 1, option_id: 10 })).toBe(
            true
        );
        expect(answers).toHaveLength(1);
    });

    test("refuses a second answer for the same question", () => {
        // the backend rejects a duplicate question_id with "A question was
        // answered more than once", and a list longer than the quiz fails the
        // page's own length check, so recording one strands the attempt
        const answers = [{ question_id: 1, option_id: 10 }];

        expect(flow.recordAnswer(answers, { question_id: 1, option_id: 11 })).toBe(
            false
        );
        expect(answers).toHaveLength(1);
    });

    test("keeps the first pick, matching what the backend locked", () => {
        const answers = [{ question_id: 1, option_id: 10 }];

        flow.recordAnswer(answers, { question_id: 1, option_id: 11 });

        expect(answers[0].option_id).toBe(10);
    });

    test("a ten question quiz records exactly ten answers", () => {
        const answers = [];

        for (let i = 1; i <= 10; i++) {
            flow.recordAnswer(answers, { question_id: i, option_id: i * 10 });
        }
        // and a stray repeat of the last one cannot push it to eleven
        flow.recordAnswer(answers, { question_id: 10, option_id: 999 });

        expect(answers).toHaveLength(10);
    });
});

describe("the sequence that used to strand a quiz", () => {
    /*
     * Walks the actual failure: ten answers in, the final submission fails,
     * the player presses Submit again. It must retry the submission with the
     * answer list untouched.
     */
    test("a failed submission retries instead of re-answering", () => {
        const answers = [];
        for (let i = 1; i <= 10; i++) {
            flow.recordAnswer(answers, { question_id: i, option_id: i * 10 });
        }

        let phase = PHASE.SUBMITTING;
        phase = PHASE.SUBMIT_FAILED; // the request came back an error

        const action = flow.submitClickAction(phase, false);

        expect(action).toBe("retry-submit");

        // the retry sends the same ten answers; nothing was appended
        expect(answers).toHaveLength(10);
    });

    test("a timed out submission that fails retries as timed out", () => {
        // re-sending a partial quiz without timed_out is rejected with
        // "Submit exactly the questions served for this quiz", so the page
        // has to remember which kind of submission it was retrying
        const pendingTimedOut = true;
        const phase = PHASE.SUBMIT_FAILED;

        expect(flow.submitClickAction(phase, false)).toBe("retry-submit");
        expect(pendingTimedOut).toBe(true);
    });
});
