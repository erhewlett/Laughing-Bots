document.addEventListener("DOMContentLoaded", () => {

    const API_BASE_URL = "http://localhost:8000";
    const MAX_POINTS = 10000;

    /*
     * The page's state rules, loaded as a plain script just before this one.
     * Kept in their own file so the tests exercise the same rules the page
     * runs rather than a restatement of them.
     */
    const flow = window.gameFlow;

    if (!flow) {
        console.error(
            "game_flow.js did not load, so the quiz page cannot run."
        );

        return;
    }

    /*
     * How long the correct answer stays on screen before the next
     * question loads.
     *
     * The countdown is paused for this stretch. The player is reading
     * feedback, not answering, so it would not be fair to charge them
     * for it, and on hard mode 10 of these would eat a sixth of the
     * clock.
     */
    const FEEDBACK_DELAY_MS = 1500;

    // Page elements
    const timeLeftInGame = document.querySelector(".time-left");
    // [CHANGED] ".difficulty-chosen" TO "#difficulty-chosen" (to match the HTML class)
    const playersChoice = document.querySelector("#difficulty-chosen");
    const pointsInGame = document.querySelector(".points-added");
    const totalPercentage = document.querySelector(".score-percentage");
    const questionText = document.querySelector("#question-text");
    const choicesContainer = document.querySelector("#choices-container");
    const submitAnswerBtn = document.querySelector("#submit-answer-btn");

    /*
     * The progress bar is optional. It is not in the required-element
     * check below, so a page without it still plays.
     */
    const progressTrack = document.querySelector(".progress[role='progressbar']");
    const progressBar = document.querySelector(".progress-bar");

    if (
        !timeLeftInGame ||
        !playersChoice ||
        !pointsInGame ||
        !totalPercentage ||
        !questionText ||
        !choicesContainer ||
        !submitAnswerBtn
    ) {
        console.error(
            "One or more required game-page elements could not be found."
        );

        return;
    }

    /*
     * The markup ships four answer rows. A question with more options than
     * that used to have the extras silently dropped, which on a question
     * whose correct option fell off the end made it unanswerable. Every
     * question in the bank has exactly four today, so instead of relying on
     * that staying true, the first row is kept as a template and more rows
     * are cloned from it when a question needs them.
     */
    const answerRowTemplate = choicesContainer.querySelector("label");

    if (!answerRowTemplate) {
        displayGameError("The answer choices could not be found on this page.");

        submitAnswerBtn.disabled = true;

        return;
    }

    let answerLabels = choicesContainer.querySelectorAll("label");

    let answerInputs = choicesContainer.querySelectorAll("input[name='answerChoice']");

    /**
     * Makes sure the page has at least `needed` answer rows, cloning the
     * template for any that are missing, then refreshes the cached lists.
     */
    function ensureAnswerRows(needed) {
        while (choicesContainer.querySelectorAll("label").length < needed) {
            const row = answerRowTemplate.cloneNode(true);

            const input = row.querySelector("input[name='answerChoice']");

            if (!input) {
                break;
            }

            input.checked = false;

            choicesContainer.appendChild(row);
        }

        answerLabels = choicesContainer.querySelectorAll("label");

        answerInputs = choicesContainer.querySelectorAll("input[name='answerChoice']");
    }

    /*
     * The game dashboard stores the response from:
     *
     * GET /game/{skill}?difficulty=easy
     *
     * inside sessionStorage under the key "current_quiz"d
     * which will read the quiz
     */

    /*
     * A malformed value here used to throw straight out of the listener,
     * which left the page on its placeholder question with nothing said
     * about why. Anything unreadable is treated as "no quiz".
     */
    const currentQuiz = readCurrentQuiz();

    if (
        !currentQuiz ||
        !Array.isArray(currentQuiz.questions) ||
        currentQuiz.questions.length === 0 ||
        typeof currentQuiz.difficulty !== "string"
    ) {
        displayGameError(
            "No active quiz was found. Return to the dashboard and select a difficulty."
        );

        submitAnswerBtn.disabled = true;

        return;
    }

    const quizId = currentQuiz.quiz_id;
    const chosenSkill = currentQuiz.skill;

    const selectedDifficulty = currentQuiz.difficulty.toLowerCase();

    const quizQuestions = currentQuiz.questions;
    const totalQuestions = quizQuestions.length;

    /*
     * The timer changes based on difficulty.
     *
     * Easy: 3 minutes
     * Medium: 2 minutes
     * Hard: 90 seconds
     *
     * Difficulty does not change the maximum score.
     * Every mode is normalized to 10,000 points.
     */
    const difficultySettings = {
        easy: {
            displayName: "Easy",
            timeInSeconds: 180
        },

        medium: {
            displayName: "Medium",
            timeInSeconds: 120
        },

        hard: {
            displayName: "Hard",
            timeInSeconds: 90
        }
    };

    const currentSettings = difficultySettings[selectedDifficulty];

    if (!currentSettings) {
        displayGameError(
            "The selected difficulty is invalid."
        );

        submitAnswerBtn.disabled = true;

        return;
    }

    let currentQuestionIndex = 0;
    let remainingTime = currentSettings.timeInSeconds;
    let timerInterval = null;

    /*
     * What the page is doing right now. One value at a time, so what a
     * Submit click means is never ambiguous. See js/game_flow.js for the
     * rules and for the bugs the old set of overlapping booleans caused.
     */
    let phase = flow.PHASE.ANSWERING;

    /*
     * True while the correct answer is on screen between questions.
     * Freezes the countdown (see FEEDBACK_DELAY_MS) and swallows clicks.
     * Not a phase: it can sit on top of grading.
     */
    let feedbackShowing = false;

    /*
     * Whether the submission currently in flight (or the one that just
     * failed) is a timed-out one. A retry has to send the same flag: a
     * partial quiz re-sent as a normal submission is rejected with
     * "Submit exactly the questions served for this quiz."
     */
    let pendingTimedOut = false;

    /*
     * The running 0-10,000 score, as graded by the backend one answer
     * at a time. The backend is the only thing that decides what is
     * correct, so this is read straight off its response rather than
     * being tallied here.
     */
    let liveScore = 0;

    /*
     * This array stores each answer submitted by the player.
     *
     * Example:
     *
     * [
     *     {
     *         question_id: 25,
     *         option_id: 101
     *     }
     * ]
     */
    const submittedAnswers = [];

    //Display the selected difficulty
    playersChoice.textContent = currentSettings.displayName;

    /*
     * The player starts at zero points. From here the score is
     * updated after every answer, using the running total the
     * backend sends back when it grades that answer.
     */

    renderScore(0);
    renderProgress(0);

    /*
     * Display the first question and start the timer.
     */
    displayQuestion();
    startTimer();

    /*
     * Enable the Submit button when the player selects
     * one of the answer choices.
     */
    /*
     * One delegated listener rather than one per radio, so answer rows
     * cloned for a question with more than four options are covered
     * without having to re-bind anything.
     */
    choicesContainer.addEventListener("change", (event) => {
        if (!event.target.matches("input[name='answerChoice']")) {
            return;
        }

        if (flow.acceptsAnswerSelection(phase, feedbackShowing)) {
            submitAnswerBtn.disabled = false;

            clearGameError();
        }
    });

    /*
     * The Submit button does one of two different jobs depending on where
     * the quiz is: grade the answer on screen, or re-send a completed quiz
     * whose submission failed. It used to be wired straight to
     * submitCurrentAnswer, so the retry path re-entered the answer flow and
     * left the quiz permanently unsubmittable (see js/game_flow.js).
     */
    submitAnswerBtn.addEventListener("click", handleSubmitClick);

    function handleSubmitClick() {
        const action = flow.submitClickAction(phase, feedbackShowing);

        if (action === "grade-answer") {
            submitCurrentAnswer();

            return;
        }

        if (action === "retry-submit") {
            clearGameError();

            submitCompletedQuiz({ timedOut: pendingTimedOut });
        }
    }

    /**
     * The quiz the difficulty page stored, or null if there isn't a
     * readable one.
     */
    function readCurrentQuiz() {
        try {
            return JSON.parse(sessionStorage.getItem("current_quiz"));
        } catch (error) {
            console.error("The stored quiz could not be read:", error);

            return null;
        }
    }

    /**
     * Displays the current question and answer choices.
     */
    function displayQuestion() {

        const question = quizQuestions[currentQuestionIndex];

        if (!question) {
            displayGameError("The next question could not be loaded.");

            return;
        }

        /*
         * Display the question text.
         */
        questionText.textContent = question.question_text;

        /*
         * Make sure there is a row for every option before any of them are
         * filled in, so none can be dropped for want of somewhere to go.
         */
        ensureAnswerRows(question.options.length);

        /*
         * Clear the previous radio-button selection.
         *
         * The data attributes are also removed before
         * the current question's values are added.
         */
        answerInputs.forEach((input) => {
            input.checked = false;
            input.disabled = false;

            input.removeAttribute("data-question-id");

            input.removeAttribute("data-option-id");
        });

        /*
         * Reset the labels in case the previous
         * question had fewer answer choices.
         */
        answerLabels.forEach((label) => {
            label.classList.remove("active");
            label.hidden = false;
        });

        /*
         * Drop the right/wrong marks from the previous question.
         */
        clearAnswerFeedback();

        /*
         * Fill the existing radio-button labels with
         * the answer options returned by the backend.
         */
        question.options.forEach((option, index) => {

            const currentLabel = answerLabels[index];

            const currentInput = answerInputs[index];

            /*
             * ensureAnswerRows() above guarantees a row per option, so this
             * only guards against a malformed cloned row.
             */
            if (!currentLabel || !currentInput) {
                console.error("An answer choice had nowhere to render.");

                return;
            }

            let choiceText = currentLabel.querySelector(".choice-text");

            /*
             *
             * This creates a span automatically if
             * one is not already present.
             */
            // [CHANGED] - added ! (only create a new span element if choiceText does not exist)
            if (!choiceText) {
                choiceText =
                    document.createElement("span");

                choiceText.classList.add(
                    "choice-text"
                );

                /*
                 * Remove placeholder text nodes such as:
                 *
                 * Choice 1
                 * Choice 2
                 */
                Array.from(currentLabel.childNodes).forEach((node) => {
                    if (
                        node.nodeType ===
                        Node.TEXT_NODE
                    ) {
                        node.remove();
                    }
                });

                currentLabel.appendChild(
                    choiceText
                );
            }

            /*
             * Display the answer text.
             */
            choiceText.textContent = option.option_text;

            /*
             * Store the question and option IDs
             * inside the radio input.
             */
            currentInput.dataset.questionId = String(question.question_id);

            currentInput.dataset.optionId = String(option.option_id);
        });

        /*
         * Hide unused labels if a question contains
         * fewer options than the HTML provides.
         */
        for (
            let index = question.options.length;
            index < answerLabels.length;
            index++
        ) {
            answerLabels[index].hidden = true;
            answerInputs[index].disabled = true;
        }

        /*
         * A new question begins without a selected
         * answer, so Submit remains disabled.
         */
        submitAnswerBtn.disabled = true;

        /*
         * The previous answer is graded and done with, so this question is
         * open for one.
         */
        phase = flow.PHASE.ANSWERING;
    }

    /**
     * Handles the player's answer when Submit is clicked.
     */
    async function submitCurrentAnswer() {
        /*
         * Find the selected radio input. handleSubmitClick has already
         * established that this is the right thing to be doing.
         */
        const selectedAnswer = choicesContainer.querySelector(
            "input[name='answerChoice']:checked"
        );

        /*
         * Prevent an empty answer from being submitted.
         */
        if (!selectedAnswer) {
            displayGameError("Please select an answer before submitting.");

            submitAnswerBtn.disabled = true;

            return;
        }

        /*
         * Immediately disable Submit and the answer
         * inputs so the user cannot double-click or
         * change the answer during submission.
         */
        phase = flow.PHASE.GRADING;
        submitAnswerBtn.disabled = true;

        setAnswerInputsDisabled(true);

        /*
         * Creating the answer object expected by
         * the backend.
         */
        const answer = {
            question_id: Number(selectedAnswer.dataset.questionId),

            option_id: Number(selectedAnswer.dataset.optionId)
        };

        /*
         * Storing the player's answer.
         *
         * The completed quiz is still submitted in full at the end.
         * Grading below is what moves the score during play; the
         * final submission is what records the attempt.
         *
         * recordAnswer refuses a second answer for a question already
         * answered. The backend rejects duplicates outright, so recording
         * one would make the whole quiz unsubmittable.
         */
        if (!flow.recordAnswer(submittedAnswers, answer)) {
            console.warn(
                "Ignoring a repeat answer for question",
                answer.question_id
            );
        }

        renderProgress(submittedAnswers.length);

        /*
         * Have the backend grade this one answer, then show the
         * player how they did before moving on.
         */
        await gradeAnswer(answer);

        /*
         * Grading is a round trip, so the clock can run out while it
         * is in flight. If it did, the expiry has already submitted what
         * was answered and moved the phase on, so stop here rather than
         * loading another question on top of the expiry message. The
         * countdown is frozen while feedback is on screen, so this only
         * covers the request itself.
         */
        if (phase !== flow.PHASE.GRADING) {
            return;
        }

        /*
         * Move the question index forward.
         */
        currentQuestionIndex++;

        /*
         * Display another question if questions remain.
         */
        if (currentQuestionIndex <totalQuestions) {

            displayQuestion();

            return;
        }

        /*
         * All questions have been answered, so send
         * the completed quiz to the backend.
         */
        submitCompletedQuiz();
    }

    /**
     * Sends one answer to the backend, shows whether it was right,
     * and moves the score.
     *
     * The backend records the answer before it tells us anything, so
     * the pick is locked in by the time the player learns whether it
     * was correct. That is what makes it safe to reveal the right
     * option here instead of holding everything back until the end.
     *
     * A failure here is not fatal. The answer is already in
     * submittedAnswers, so the completed quiz still grades correctly
     * at the end; the player just does not get feedback on this one.
     */
    async function gradeAnswer(answer) {
        let result = null;

        try {
            const response = await fetch(
                `${API_BASE_URL}/game/${encodeURIComponent(chosenSkill)}/answer`,
                {
                    method: "POST",

                    headers: buildRequestHeaders(),

                    body: JSON.stringify({
                        quiz_id: quizId,

                        question_id: answer.question_id,

                        option_id: answer.option_id
                    })
                }
            );

            result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail ||
                    `The answer could not be graded. Status: ${response.status}`
                );
            }
        } catch (error) {
            console.error("Answer grading failed:", error);

            /*
             * Keep playing. The score catches up when the completed
             * quiz is graded.
             */
            return;
        }

        /*
         * The running total is the backend's, not ours, so the number
         * the player watches climb is the number they finish on.
         */
        liveScore = Number(result.score_normalized ?? liveScore);

        renderScore(liveScore);

        await showAnswerFeedback(result, answer.option_id);
    }

    /**
     * Marks the player's pick right or wrong, shows the correct
     * option, and holds it on screen long enough to read.
     */
    async function showAnswerFeedback(result, pickedOptionId) {
        const correctOptionId = Number(result.correct_option_id);

        answerInputs.forEach((input) => {
            const optionId = Number(input.dataset.optionId);

            const label = input.closest("label");

            if (!label || Number.isNaN(optionId)) {
                return;
            }

            /*
             * The correct option is always marked. The player's pick
             * is marked wrong only when it was not the correct one,
             * so a right answer gets a single check rather than a
             * check and a cross on the same row.
             */
            if (optionId === correctOptionId) {
                label.classList.add("answer-correct");
            } else if (optionId === pickedOptionId) {
                label.classList.add("answer-wrong");
            }
        });

        /*
         * Freeze the countdown while the answer is on screen.
         */
        feedbackShowing = true;

        await wait(FEEDBACK_DELAY_MS);

        feedbackShowing = false;
    }

    /**
     * Removes the right/wrong marks left by the previous question.
     */
    function clearAnswerFeedback() {
        answerLabels.forEach((label) => {
            label.classList.remove("answer-correct", "answer-wrong");
        });
    }

    /**
     * Request headers for the game endpoints.
     *
     * The token is only attached when there is one. Sending
     * "Bearer null" while logged out reads as a malformed token.
     */
    function buildRequestHeaders() {
        const headers = {
            "Content-Type": "application/json",

            Accept: "application/json"
        };

        const token = localStorage.getItem("token");

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        return headers;
    }

    /**
     * Resolves after the given number of milliseconds.
     */
    function wait(milliseconds) {
        return new Promise((resolve) => {
            setTimeout(resolve, milliseconds);
        });
    }

    /**
     * Sends all answers to the FastAPI backend.
     *
     * @param {{timedOut?: boolean}} [options] timedOut submits a partial
     *        quiz after the clock runs out. The backend grades the
     *        unanswered questions wrong and keeps the maximum at the
     *        full quiz.
     */
    async function submitCompletedQuiz(options) {
        const timedOut = Boolean(options && options.timedOut);

        /*
         * Outside of a timeout the backend requires one answer for
         * every question that was served.
         */
        if (!timedOut && submittedAnswers.length !== totalQuestions) {

            displayGameError(
                `All ${totalQuestions} questions must be answered before submission.`
            );

            phase = flow.PHASE.ANSWERING;

            return;
        }

        /*
         * Remembered so a retry re-sends the same kind of submission. A
         * partial quiz re-sent without timed_out is rejected outright.
         */
        pendingTimedOut = timedOut;

        phase = flow.PHASE.SUBMITTING;

        /*
         * Stop the timer while the quiz is submitted.
         */
        clearInterval(timerInterval);

        try {
            const response = await fetch(
                `${API_BASE_URL}/game/${encodeURIComponent(chosenSkill)}/submit`,
                {
                    method: "POST",

                    headers: buildRequestHeaders(),

                    body: JSON.stringify({
                        quiz_id: quizId,

                        difficulty: selectedDifficulty,

                        answers: submittedAnswers,

                        /*
                         * Time actually spent on questions. The clock is
                         * frozen while feedback is on screen, so this does
                         * not bill the player for reading it.
                         */
                        elapsed_seconds: Math.max(
                            currentSettings.timeInSeconds - remainingTime,
                            0
                        ),

                        timed_out: timedOut
                    })
                }
            );

            const result =
                await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail ||
                    `The quiz could not be submitted. Status: ${response.status}`
                );
            }

            /*
             * The backend successfully graded
             * the completed quiz.
             */
            finishCompletedGame(result);
        } catch (error) {
            console.error(
                "Quiz submission failed:",
                error
            );

            /*
             * The send failed, so the quiz is not on its way after all. The
             * answers are all still here, so the player can re-send them:
             * the phase says the Submit button now retries the submission
             * instead of grading another answer. Getting that wrong is what
             * used to leave a quiz permanently unsubmittable.
             */
            phase = flow.PHASE.SUBMIT_FAILED;

            displayGameError(
                `${error.message || "The quiz could not be submitted."} ` +
                "Press Submit to try again."
            );

            submitAnswerBtn.disabled = false;
        }
    }

        /**
     * Finishes the game after the backend returns
     * the graded quiz result.
     */
    function finishCompletedGame(result) {
        phase = flow.PHASE.FINISHED;

        clearInterval(timerInterval);

        setAnswerInputsDisabled(true);

        submitAnswerBtn.disabled = true;

        /*
         * The exact property names depend on the
         * GameResult schema returned by your backend.
         *
         * These fallbacks support common names such as:
         *
         * correct_count
         * score
         * total_questions
         * max_score
         * 
         * class GameResult(BaseModel):
    skill: str
    difficulty: Difficulty
    score: int              # number correct
    max_score: int          # number of questions (10 for a full quiz)
    correct_count: int
    total_questions: int
    mastered: bool          # perfect score on a hard quiz
    results: list[QuestionResult]
         * 
         */
        const correctAnswers = Number(
            result.correct_count ??
            result.score ??
            0
        );

        const backendTotal = Number(
            result.total_questions ??
            result.max_score ??
            totalQuestions
        );

        /*
         * Point System:
         *
         * Every difficulty to a maximum
         * score of 10,000 points.
         *
         * With ten questions:
         *
         * 1 correct  = 1,000 points
         * 5 correct  = 5,000 points
         * 10 correct = 10,000 points
         */
        /*
         * The backend sends the same 0-10,000 figure it has been
         * returning after every answer, so the final number matches
         * the one the player watched climb. The local calculation is
         * kept as a fallback for a response that omits it.
         */
        const finalScore = Number(
            result.score_normalized ??
            calculateTheScore(correctAnswers, backendTotal)
        );

        const finalPercentage =
            calculateScorePercentage(
                finalScore
            );

        /*
         * Update the visible score.
         */
        renderScore(finalScore);

        /*
         * Store the complete game result.
         */
        const gameResults = {
            quizId: quizId,

            skill:
                result.skill ??
                chosenSkill,

            difficulty:
                result.difficulty ??
                selectedDifficulty,

            correctAnswers:
                correctAnswers,

            incorrectAnswers:
                Math.max(backendTotal - correctAnswers, 0),

            totalQuestions:
                backendTotal,

            pointsPerCorrectAnswer:
                MAX_POINTS / backendTotal,

            finalScore:
                finalScore,

            percentage:
                finalPercentage,

            mastered:
                Boolean(result.mastered),

            questionResults:
                result.results ?? [],

            remainingTime:
                remainingTime
        };

        /*
         * Save the results so a results page can
         * retrieve them later.
         */
        localStorage.setItem("latest_game_results", JSON.stringify(gameResults));

        console.log("Game results:", gameResults);

        displayGameResults(gameResults);
    }

    /**
     * Calculates a score normalized to 10,000 points.
     */
    function calculateTheScore(correctAnswers, questionCount) {

        if (questionCount <= 0) {
            return 0;
        }

        /*
         * Ten questions:
         *
         * 10,000 / 10 = 1,000 points each
         *
         */
        const pointsPerCorrectAnswer =
            MAX_POINTS / questionCount;

        return Math.min(Math.round(correctAnswers * pointsPerCorrectAnswer),

            MAX_POINTS
        );
    }

    /**
     * Converts the score to a percentage.
     */
    function calculateScorePercentage(score) {

        return Math.round((score / MAX_POINTS) * 100);

    }

    /**
     * Moves the progress bar to show how much of the quiz is done.
     *
     * The markup carried a bar that nothing ever updated, so it sat
     * at 0% for the whole game.
     */
    function renderProgress(answeredCount) {
        if (!progressBar || totalQuestions <= 0) {
            return;
        }

        const percentComplete = Math.min(
            Math.round((answeredCount / totalQuestions) * 100),
            100
        );

        progressBar.style.width = `${percentComplete}%`;

        if (progressTrack) {
            progressTrack.setAttribute("aria-valuenow", String(percentComplete));
        }
    }

    /**
     * Writes an already-calculated 0-10,000 score to the page.
     *
     * The percentage is that score out of the 10,000 maximum, so one
     * correct answer out of ten reads as 1,000 pts and 10%.
     */
    function renderScore(score) {

        const percentage = calculateScorePercentage(score);

        pointsInGame.textContent = `${score.toLocaleString("en-US")} pts`;

        totalPercentage.textContent = `${percentage}%`;
    }

    /**
     * Starts the difficulty-based countdown timer.
     */
    function startTimer() {
        updateTimerDisplay();

        timerInterval = setInterval(() => {
            /*
             * The clock does not run while the player is being shown the
             * correct answer between questions, nor once the quiz is on its
             * way to be graded. It does keep running while a single answer
             * is graded - that round trip is the player's time.
             */
            if (!flow.clockRuns(phase, feedbackShowing)) {
                return;
            }

            remainingTime--;

            if (remainingTime <= 0) {

                remainingTime = 0;

                updateTimerDisplay();

                handleTimeExpired();

                return;
            }

            updateTimerDisplay();
        }, 1000);
    }

    /**
     * Updates the timer text in minutes and seconds.
     */
    function updateTimerDisplay() {
        const minutes = Math.floor(remainingTime / 60);

        const seconds = remainingTime % 60;

        /*
         * padStart ensures nine seconds appears
         * as 09 instead of 9.
         *
         */
        timeLeftInGame.textContent = `${minutes}:${seconds.toString().padStart(2, "0")}`;
    }

    /**
     * Handles an expired timer.
     *
     * The answers given before the clock ran out are still worth
     * points, so the quiz is submitted rather than thrown away.
     * The backend grades whatever is missing as wrong and keeps the
     * maximum at the full ten questions, so stopping early is never
     * better than playing on.
     */
    function handleTimeExpired() {
        clearInterval(timerInterval);

        submitAnswerBtn.disabled = true;

        setAnswerInputsDisabled(true);

        /*
         * Only skip when the completed quiz is genuinely already on its
         * way, or already graded. An answer being graded right now must not
         * stop this, or a clock running out mid-grade would leave the quiz
         * unsubmitted.
         */
        if (!flow.expiryShouldSubmit(phase)) {
            return;
        }

        const answered = submittedAnswers.length;

        displayGameError(
            `Time expired. Scoring the ${answered} question${answered === 1 ? "" : "s"} you answered.`
        );

        submitCompletedQuiz({ timedOut: true });
    }

    /**
     * Enables or disables every radio answer.
     */
    function setAnswerInputsDisabled(disabled) {
        answerInputs.forEach((input) => {
            input.disabled = disabled;
        });
    }

    /**
     * Displays an error message below the Submit button.
     *
     * Styling and placement live in the HTML now. This used to add the
     * classes and re-insert the element on every call, which moved it
     * down the page each time an error was shown.
     */
    function displayGameError(message) {
        const errorElement = document.querySelector("#game-display-error");

        if (!errorElement) {
            console.error("Game error, with nowhere to show it:", message);

            return;
        }

        errorElement.textContent = message;

        errorElement.hidden = false;
    }

    /**
     * Clears the current answer error.
     */
    function clearGameError() {
        const errorElement = document.querySelector("#game-display-error");

        if (errorElement) {
            errorElement.textContent = "";

            errorElement.hidden = true;
        }
    }

    /**
     * Temporarily logs the game results.
     *
     * This can later redirect the player to a
     * dedicated results page.
     */
    function displayGameResults(results) {
        console.log(
            `Final score: ${results.finalScore}`
        );

        console.log(
            `Final percentage: ${results.percentage}%`
        );

        console.log(
            `Correct answers: ${results.correctAnswers}/${results.totalQuestions}`
        );

        /*
         * Add the results-page redirect when your
         * results page is ready.
         */
        // window.location.href =
        //     "../html/game_results.html";
    }
});