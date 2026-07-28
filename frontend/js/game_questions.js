document.addEventListener("DOMContentLoaded", () => {

    const API_BASE_URL = "http://localhost:8000";
    const MAX_POINTS = 10000;

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
    // [CHANGED] ".difficulty-chosen" TO "#difficulty-chosen" (to match the HTML id)
    const playersChoice = document.querySelector("#difficulty-chosen");
    const pointsInGame = document.querySelector(".points-added");
    const totalPercentage = document.querySelector(".score-percentage");
    const questionText = document.querySelector("#question-text");
    const choicesContainer = document.querySelector("#choices-container");
    const submitAnswerBtn = document.querySelector("#submit-answer-btn");

    /*
    * The button that appears after the quiz has been completed to return users
    * back to the user view page
    */
    const returnPlayersBtn = document.createElement("button");

    returnPlayersBtn.type = "button";
    returnPlayersBtn.id = "user-view-btn";
    returnPlayersBtn.className = submitAnswerBtn.className;
    returnPlayersBtn.textContent = "Return to User View";
    returnPlayersBtn.hidden = true;

    submitAnswerBtn.insertAdjacentElement(
        "afterend",
        returnPlayersBtn
    );

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

    const answerLabels = choicesContainer.querySelectorAll("label");

    const answerInputs = choicesContainer.querySelectorAll("input[name='answerChoice']");

    /*
     * The game dashboard stores the response from:
     *
     * GET /game/{skill}?difficulty=easy
     *
     * inside sessionStorage under the key "current_quiz"d
     * which will read the quiz
     */

    const currentQuiz = JSON.parse(sessionStorage.getItem("current_quiz"));

    if (!currentQuiz || !Array.isArray(currentQuiz.questions)) {
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
    let gameFinished = false;
    let submissionInProgress = false;

    /*
     * True while the correct answer is on screen between questions.
     * Freezes the countdown (see FEEDBACK_DELAY_MS).
     */
    let feedbackShowing = false;

    /*
     * True once the completed quiz has been sent for grading.
     *
     * Kept apart from submissionInProgress, which is also raised while a
     * single answer is being graded. Sharing one flag meant a clock that ran
     * out mid-grade found it already set, skipped submitting, and then the
     * grading call returned to a finished game and stopped too, so the quiz
     * was never sent at all.
     */
    let finalSubmitStarted = false;

    /*
     * True when a completed quiz failed to send and Submit should try it
     * again rather than grade another answer.
     *
     * The button has one handler, submitCurrentAnswer. Re-enabling it after a
     * failed submission therefore put the player back in the answer flow: the
     * last question's radio is still checked (disabled radios still are), so
     * the same answer was recorded a second time, submittedAnswers ended up
     * one longer than the quiz, and every attempt after that failed the length
     * check below - the quiz could never be submitted at all.
     */
    let awaitingSubmitRetry = false;

    /*
     * Whether the submission being retried was a timed-out one. A partial
     * quiz re-sent without timed_out is rejected with "Submit exactly the
     * questions served for this quiz."
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
    answerInputs.forEach((input) => {
        input.addEventListener("change", () => {
            if (!gameFinished && !submissionInProgress) {
                submitAnswerBtn.disabled = false;

                clearGameError();
            }
        });
    });

    /*
     * Submit does one of two jobs depending on where the quiz is: grade the
     * answer on screen, or re-send a completed quiz whose submission failed.
     * It used to be wired straight to submitCurrentAnswer, so the retry path
     * re-entered the answer flow (see awaitingSubmitRetry above).
     */
    submitAnswerBtn.addEventListener("click", () => {
        if (awaitingSubmitRetry) {
            clearGameError();

            submitCompletedQuiz({ timedOut: pendingTimedOut });

            return;
        }

        submitCurrentAnswer();
    });

    /*
    * Redirect the player to the user-view page after
    * the completed quiz has been graded.
    */
    returnPlayersBtn.addEventListener("click", () => {

        window.location.href = "../html/user_info_view_page.html";
    });

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

            if (!currentLabel || !currentInput) {
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
         * The previous submission is complete, so
         * the next answer may now be selected.
         */
        submissionInProgress = false;
    }

    /**
     * Handles one submitted answer.
     */
    async function submitCurrentAnswer() {

        if (
            gameFinished ||
            submissionInProgress ||
            feedbackShowing
        ) {
            return;
        }

        const selectedAnswer = choicesContainer.querySelector(
            "input[name='answerChoice']:checked"
        );

        if (!selectedAnswer) {
            displayGameError(
                "Please select an answer before submitting."
            );

            submitAnswerBtn.disabled = true;

            return;
        }

        submissionInProgress = true;
        submitAnswerBtn.disabled = true;

        setAnswerInputsDisabled(true);

        clearGameError();

        const answer = {
            question_id: Number(
                selectedAnswer.dataset.questionId
            ),

            option_id: Number(
                selectedAnswer.dataset.optionId
            )
        };

        /*
        * Ask the backend to record and grade this answer.
        */
        const liveResult = await gradeAnswer(answer);

        /*
        * If the backend could not record the answer,
        * allow the player to try again.
        */
        if (!liveResult) {

            submissionInProgress = false;

            setAnswerInputsDisabled(false);

            submitAnswerBtn.disabled = false;

            return;
        }

        /*
        * Only store the answer locally after the backend
        * confirms it has been recorded.
        */
        if (
            !submittedAnswers.some(
                (submittedAnswer) =>
                    submittedAnswer.question_id === answer.question_id
            )
        ) {
            submittedAnswers.push(answer);
        }

        /*
        * The backend tells us how many questions have been
        * answered, so use that instead of our local count.
        */
        renderProgress(liveResult.answered_count);

        /*
        * The score has already been updated by gradeAnswer().
        */

        if (gameFinished) {
            return;
        }

        currentQuestionIndex++;

        if (currentQuestionIndex < totalQuestions) {

            displayQuestion();

            return;
        }

        /*
        * The backend tells us when every question has been
        * answered.
        */
        if (liveResult.quiz_complete) {

            submitCompletedQuiz();

            return;
        }

        /*
        * Fallback.
        */
        if (submittedAnswers.length === totalQuestions) {
            submitCompletedQuiz();
        }
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
     
    
    * Sends one answer to the live-answer endpoint.
    *
    * The backend records the answer, determines whether
    * it is correct, and returns the current normalized
    * score from 0 through 10,000.

    */

    async function gradeAnswer(answer) {

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

            const result = await response.json();

            if (!response.ok) {

                throw new Error(
                    
                    result.detail ||

                    `The answer could not be graded. Status: ${response.status}`

                );

            }

            /*

            * Use the backend's official running score

            */

            liveScore = Number(result.score_normalized ?? liveScore);

            /*

            * Update points and percentage immediately

            */

            renderScore(liveScore);

            /*

            * The backend also returns answered_count,

            * which is more authoritative than the local

            * array length.

            */

            renderProgress(Number(result.answered_count ?? submittedAnswers.length));

            /*

            * Display the Bootstrap validation feedback.

            */

            await showAnswerFeedback(result, answer.option_id);

            return result;

        } catch (error) {

            console.error("Answer grading failed:", error);

            displayGameError(

                error.message ||

                "The answer could not be graded. Please try again."

            );

            return null;

        }

    }
    /**
     * Marks the player's pick right or wrong, shows the correct
     * option, and holds it on screen long enough to read.
     */
    async function showAnswerFeedback(result, pickedOptionId) {

        const correctOptionId = Number(result.correct_option_id);

        answerInputs.forEach((input) => {

            const optionId = Number(input.dataset.optionId);

            if (Number.isNaN(optionId)) {

                return;

            }

            //The player selected the correct answer.

            if (result.is_correct && optionId === pickedOptionId) {

                input.classList.add("is-valid");

                input.setAttribute("aria-invalid", "false");

                return;

            }

            //The player selected an incorrect answer.

            if (!result.is_correct && optionId === pickedOptionId) {

                input.classList.add("is-invalid");

                input.setAttribute("aria-invalid", "true");

                return;

            }

            // Reveal the answer to the player if their answer ends up incorrect

            if (!result.is_correct && optionId === correctOptionId) {

                input.classList.add("is-valid");

                input.setAttribute("aria-invalid", "false");

            }

        });

        // This will prevent the timer from continuing its countdown during the delay

        feedbackShowing = true;

        await wait(FEEDBACK_DELAY_MS);

        feedbackShowing = false;

    }

    
    //Removes the right/wrong marks left by the previous question.
    
    function clearAnswerFeedback() {
        answerInputs.forEach((input) => {

            input.classList.remove("is-valid", "is-invalid");

            input.removeAttribute("aria-invalid");

        });
    }

    /**
     * Replaces the Submit button after the game is complete.
     */
    function returnPlayerBtn() {
        submitAnswerBtn.hidden = true;
        submitAnswerBtn.disabled = true;

        returnPlayersBtn.hidden = false;
        returnPlayersBtn.disabled = false;

        returnPlayersBtn.focus();
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

            submissionInProgress = false;

            return;
        }

        submissionInProgress = true;
        finalSubmitStarted = true;

        /*
         * Remembered so a retry re-sends the same kind of submission.
         */
        pendingTimedOut = timedOut;
        awaitingSubmitRetry = false;

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

            displayGameError(
                `${error.message || "The quiz could not be submitted."} ` +
                "Press Submit to try again."
            );

            submissionInProgress = false;

            /*
             * The send failed, so the quiz is not on its way after all.
             */
            finalSubmitStarted = false;

            /*
             * Allow another go at submitting. Safe to re-enable even after the
             * clock expired, because Submit now retries the submission rather
             * than letting the player carry on answering.
             */
            awaitingSubmitRetry = true;

            submitAnswerBtn.disabled = false;
        }
    }

        /**
     * Finishes the game after the backend returns
     * the graded quiz result.
     */
    function finishCompletedGame(result) {
        gameFinished = true;
        submissionInProgress = false;

        clearInterval(timerInterval);

        setAnswerInputsDisabled(true);

        submitAnswerBtn.disabled = true;

       
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

        returnPlayerBtn();
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
     * Updates the points and percentage displayed
     * on the game page.
     */
    function updateScoreDisplay(correctAnswers, questionCount) {

        renderScore(calculateTheScore(correctAnswers, questionCount));
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
             * The clock does not run while the player is being shown
             * the correct answer between questions.
             */
            if (feedbackShowing) {
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

        gameFinished = true;

        submitAnswerBtn.disabled = true;

        setAnswerInputsDisabled(true);

        /*
         * Only skip when the completed quiz is genuinely already on its
         * way. An answer being graded right now must not stop this, or a
         * clock running out mid-grade would leave the quiz unsubmitted.
         */
        if (finalSubmitStarted) {
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