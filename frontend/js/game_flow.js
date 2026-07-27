// game_flow.js - the quiz page's state rules, kept apart from its DOM wiring.
//
// The page used to track four overlapping booleans (gameFinished,
// submissionInProgress, feedbackShowing, finalSubmitStarted). Any two of them
// could describe the same moment, and the gaps between them were real bugs:
//
//   * A failed final submission re-enabled the Submit button "to allow another
//     go at submitting", but the button's only handler grades an answer. The
//     retry therefore re-entered the answer flow, re-recorded the last answer
//     (a disabled radio is still :checked), and left the list one longer than
//     the quiz - so every following attempt failed the length check and the
//     attempt could never be submitted at all.
//   * Retrying a submission that had timed out would have sent timed_out:false
//     the second time, which the backend rejects with "Submit exactly the
//     questions served for this quiz."
//
// So the page has one phase at a time, and what a Submit click means is a
// function of that phase rather than of whichever boolean was checked first.
// Feedback is deliberately NOT a phase: it is a short overlay that freezes the
// clock and swallows clicks, and it can sit on top of grading.
//
// Loaded as a plain script before game_questions.js, and required directly by
// the tests, so the rules the tests check are the ones the page runs.
(function () {
    const PHASE = {
        // Waiting for the player to pick an option and press Submit.
        ANSWERING: "answering",
        // An answer is being graded by POST /game/{skill}/answer.
        GRADING: "grading",
        // The completed quiz is on its way to POST /game/{skill}/submit.
        SUBMITTING: "submitting",
        // That submission failed. The quiz is intact and can be re-sent.
        SUBMIT_FAILED: "submit_failed",
        // Graded and recorded. Nothing more to send.
        FINISHED: "finished",
    };

    /**
     * What pressing Submit means right now.
     *
     * @returns {"grade-answer"|"retry-submit"|"ignore"}
     */
    function submitClickAction(phase, feedbackShowing) {
        if (feedbackShowing) {
            return "ignore";
        }
        if (phase === PHASE.ANSWERING) {
            return "grade-answer";
        }
        if (phase === PHASE.SUBMIT_FAILED) {
            return "retry-submit";
        }
        return "ignore";
    }

    /** True when picking a different option should re-enable Submit. */
    function acceptsAnswerSelection(phase, feedbackShowing) {
        return phase === PHASE.ANSWERING && !feedbackShowing;
    }

    /**
     * True when the countdown should tick.
     *
     * It keeps running while an answer is graded - that round trip is the
     * player's time - but stops for feedback (they are reading, not
     * answering) and once the quiz is on its way to be graded.
     */
    function clockRuns(phase, feedbackShowing) {
        if (feedbackShowing) {
            return false;
        }
        return phase === PHASE.ANSWERING || phase === PHASE.GRADING;
    }

    /**
     * True when the expiring clock should submit what has been answered.
     *
     * False once a submission is already on its way or the quiz is graded;
     * an answer merely being graded must NOT stop it, or a clock running out
     * mid-grade would leave the attempt unsent.
     */
    function expiryShouldSubmit(phase) {
        return phase !== PHASE.SUBMITTING && phase !== PHASE.FINISHED;
    }

    /**
     * Record one answer, refusing a second answer for the same question.
     *
     * The backend rejects a duplicate question_id outright ("A question was
     * answered more than once"), and a list longer than the quiz fails the
     * page's own length check, so a duplicate is unsubmittable either way.
     * Keeping the first pick also matches the backend, which locks an answer
     * when it grades it and will not let a submission swap it afterwards.
     *
     * @returns {boolean} true if it was recorded, false if already answered
     */
    function recordAnswer(answers, answer) {
        const already = answers.some(
            (existing) => existing.question_id === answer.question_id
        );
        if (already) {
            return false;
        }
        answers.push(answer);
        return true;
    }

    const gameFlow = {
        PHASE,
        submitClickAction,
        acceptsAnswerSelection,
        clockRuns,
        expiryShouldSubmit,
        recordAnswer,
    };

    // Same dual export as api.js: window for the page, module.exports for jest.
    if (typeof window !== "undefined") {
        window.gameFlow = gameFlow;
    }
    if (typeof module !== "undefined" && module.exports) {
        module.exports = gameFlow;
    }
})();
