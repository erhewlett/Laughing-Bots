document.addEventListener("DOMContentLoaded", () => {

    const API_BASE_URL = "http://localhost:8000";
    const MAX_POINTS = 10000;

    // Page elements
    const timeLeftInGame = document.querySelector(".time-left");
    // [CHANGED] ".difficulty-chosen" TO "#difficulty-chosen" (to match the HTML class)
    const playersChoice = document.querySelector("#difficulty-chosen");
    const pointsInGame = document.querySelector(".points-added");
    const totalPercentage = document.querySelector(".score-percentage");
    const questionText = document.querySelector("#question-text");
    const choicesContainer = document.querySelector("#choices-container");
    const submitAnswerBtn = document.querySelector("#submit-answer-btn");

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
     * Hard: 1 minute
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
     * The frontend starts at zero points.
     * The final score is calculated after the backend
     * grades the completed quiz.
     */

    updateScoreDisplay(0, totalQuestions);

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
     * Run submitCurrentAnswer() whenever the Submit
     * button is clicked.
     */
    submitAnswerBtn.addEventListener("click", submitCurrentAnswer);

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
     * Handles the player's answer when Submit is clicked.
     */
    function submitCurrentAnswer() {
        /*
         * Prevent answers after the game ends and
         * prevent double-click submissions.
         */
        if (gameFinished || submissionInProgress) {
            return;
        }

        /*
         * Find the selected radio input.
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
        submissionInProgress = true;
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
         */
        submittedAnswers.push(answer);

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
     * Sends all answers to the FastAPI backend.
     */
    async function submitCompletedQuiz() {
        /*
         * The backend requires one answer for every
         * question that was served.
         */
        if (submittedAnswers.length !== totalQuestions) {

            displayGameError(
                `All ${totalQuestions} questions must be answered before submission.`
            );

            submissionInProgress = false;

            return;
        }

        /*
         * Stop the timer while the quiz is submitted.
         */
        clearInterval(timerInterval);

        try {
            // save token
            const token = localStorage.getItem('token');
            const response = await fetch(
                `${API_BASE_URL}/game/${encodeURIComponent(chosenSkill)}/submit`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        Accept:
                            "application/json",
                        
                        Authorization:
                            `Bearer ${token}`
                    },

                    body: JSON.stringify({
                        quiz_id: quizId,

                        difficulty: selectedDifficulty,

                        answers: submittedAnswers
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
                error.message ||
                "The quiz could not be submitted."
            );

            /*
             * Allow the player to try submitting
             * the completed quiz again.
             */
            submissionInProgress = false;
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
        const finalScore =
            calculateTheScore(
                correctAnswers,
                backendTotal
            );

        const finalPercentage =
            calculateScorePercentage(
                finalScore
            );

        /*
         * Update the visible score.
         */
        updateScoreDisplay(
            correctAnswers,
            backendTotal
        );

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
     * Updates the points and percentage displayed
     * on the game page.
     */
    function updateScoreDisplay(correctAnswers, questionCount) {

        const score = calculateTheScore(correctAnswers, questionCount);

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
     */
    function handleTimeExpired() {
        clearInterval(timerInterval);

        gameFinished = true;

        submitAnswerBtn.disabled = true;

        setAnswerInputsDisabled(true);

        /*
         * The current backend requires exactly one
         * answer for every question served.
         *
         * An incomplete quiz cannot be submitted
         * because unanswered questions do not have
         * valid option IDs.
         */
        displayGameError(
            "Time expired. This incomplete quiz cannot be scored. Return to the dashboard to start a new quiz."
        );
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
     */
    function displayGameError(message) {
        let errorElement = document.querySelector("#game-display-error");

       
        errorElement.id = "game-display-error";

        errorElement.classList.add(
            "text-danger",
            "text-center",
            "mt-2"
        );

        errorElement.setAttribute(
            "role",
            "alert"
        );

        submitAnswerBtn.parentElement.insertAdjacentElement("afterend", errorElement);

        errorElement.textContent = message;
    }

    /**
     * Clears the current answer error.
     */
    function clearGameError() {
        const errorElement = document.querySelector("#game-display-error");

        if (errorElement) {
            errorElement.textContent = "";
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