const easyBtn = document.querySelector('.easyMode');
const mediumBtn = document.querySelector('.mediumMode');
const hardBtn = document.querySelector('.hardMode');
// Skill selected from the word cloud
const theSkill = localStorage.getItem("selected_skill");
const skillDisplay = document.querySelector("#skillDisplay");

const API_BASE_URL = "http://localhost:8000";

// Displays the skill on the dashboard

if (theSkill) {

    skillDisplay.textContent = theSkill;

    // Remove it so it won't be there after a refresh
    
} else {

    skillDisplay.textContent = "No skill selected";

}


easyBtn.addEventListener("click", () => {

    startGame("easy");
    console.log("easy difficulty selected");

});

mediumBtn.addEventListener("click", () => {

    startGame("medium");
    console.log("medium difficulty selected");

});

hardBtn.addEventListener("click", () => {

    startGame("hard");
    console.log("hard difficulty selected");

});

/**

 * Requests a new quiz from the backend.

 *

 * @param {"easy" | "medium" | "hard"} difficulty

 */

async function startGame(difficulty) {

    // False result
    if (!theSkill) {

        displayDashboardError(

            "No skill was selected. Please return to the word cloud and select a skill."

        );

        return;

    }

    setButtonsDisabled(true);

    try {

        const skillPath = encodeURIComponent(theSkill);
        const difficultyPath = encodeURIComponent(difficulty);

        const requestURL =

            `${API_BASE_URL}/game/${skillPath}` + `?difficulty=${difficultyPath}`;

        /*
         * The token has to go out on this request, not just on submit.
         *
         * The backend ties the quiz session it creates here to whoever
         * asked for it, and uses that to avoid repeating the questions
         * from the player's last quiz on the same skill and difficulty.
         * Without the header every session was created anonymous, so
         * that never happened and players saw the same questions again.
         */
        const headers = {

            Accept: "application/json"

        };

        const token = localStorage.getItem("token");

        if (token) {

            headers.Authorization = `Bearer ${token}`;

        }

        const response = await fetch(requestURL, {

            method: "GET",

            headers: headers

        });


        let responseData;
        
        try {

            responseData = await response.json();

        } catch {

            responseData = null;

        }

        if (!response.ok) {

            throw new Error(

                responseData?.detail ||

                `The quiz could not be loaded. Status: ${response.status}`

            );

        }

        if (!responseData?.quiz_id) {

            throw new Error(

                "The server returned an invalid quiz response."

            );

        }

        if (

            !Array.isArray(responseData.questions) ||

            responseData.questions.length === 0

        ) {

            throw new Error(

                `No ${difficulty} questions were found for ${theSkill}.`

            );

        }

        /*

         * Expected backend response:

         *

         * {

         *   quiz_id: 25,

         *   skill: "JavaScript",

         *   difficulty: "easy",

         *   questions: [

         *     {

         *       question_id: 1,

         *       question_text: "...",

         *       options: [

         *         {

         *           option_id: 4,

         *           option_text: "..."

         *         }

         *       ]

         *     }

         *   ]

         * }

         */

        sessionStorage.setItem("current_quiz", JSON.stringify(responseData));

        sessionStorage.setItem("selected_difficulty", responseData.difficulty);

        sessionStorage.setItem("selected_skill", responseData.skill);

        //remove theSKill after the quiz has successfully loaded and has been 
        // copied into sessionStorage:
        localStorage.removeItem("selected_skill");


        window.location.href = "../html/game_question_page.html";

    } catch (error) {

        console.error("Unable to start the game:", error);

        displayDashboardError(

            error.message || "Unable to connect to the game server."

        );

        setButtonsDisabled(false);

    }

}

function setButtonsDisabled(disabled) {

    easyBtn.disabled = disabled;

    mediumBtn.disabled = disabled;

    hardBtn.disabled = disabled;

}

function displayDashboardError(message) {

    // Class game-error does not exist
    let errorElement = document.querySelector(".game-error");
    // since it does not this if statement will relay false
    if (!errorElement) {
        // we create a <p> tag 
        errorElement = document.createElement("p");
        // Class game-error is created
        errorElement.classList.add("game-error");

        errorElement.setAttribute("role", "alert");

        const gameSetup = document.querySelector(".game-set-up");
        // adds the newly created element below the current element on the page
        gameSetup?.insertAdjacentElement("afterend", errorElement);

    }

    errorElement.textContent = message;

}