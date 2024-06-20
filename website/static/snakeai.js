const gameBoard = document.querySelector("#gameBoard"); // selects game board html canvas element 
const ctx = gameBoard.getContext("2d"); // gets drawing context 
const scoreText = document.querySelector("#score"); // html element for displaying the score 
const gamesText = document.querySelector("#games") // html element for displaying the number of game s
const hidemeDiv = document.getElementById("hideme") // html element for hidden div 
const highscoreText = document.querySelector("#highscore"); // html element for displaying high score 
const gameWidth = gameBoard.width; // gameboard width 
const gameHeight = gameBoard.height; // gameboard height 

const dangerAheadtText = document.querySelector("#dangerAhead");
const dangerRightText = document.querySelector("#dangerRight");
const dangerLeftText = document.querySelector("#dangerLeft");
const directionText = document.querySelector("#direction");
const foodLeftText = document.querySelector("#foodLeft");
const foodRightText = document.querySelector("#foodRight");
const foodAboveText = document.querySelector("#foodAbove");
const foodBelowText = document.querySelector("#foodBelow");



// colors for use
const boardBackground = "white";
const snakeColor = "lightgreen";
const snakeBorder = "black";
const foodColor = "red";

const unitSize = 20; // size of each unit/block

let foodX; // x coordinate of food 
let foodY; // y coordinate of food 
let score = 0; // current score 
let game_score = 0; // game score 
let snake = []; // represents the snake as array of objects of x,y coordinates 
let state = [];
let num_trainings = 0; // number of training sessions
let games = 0; // tracks number of games played
let running = false; // indicates whether game is running 

const socket = io(); // initializes Socket.IO connection

// for displaying initial message on the screen 
ctx.font = "35px Quicksand";
ctx.fillStyle = "black";
ctx.textAlign = "center";
ctx.fillText("training arena", gameWidth / 2, gameHeight / 2);

hidemeDiv.style.display = "none"; // hides the hidemeDiv element 

//triggers when train button is clicked, sends call to train event that begins training
document.getElementById("btn-train").addEventListener("click", function () {
    if (!running) { // if the game is not running
        running = true; // indicates the game is now running 
        let food = document.getElementById("food").value; // gets food reward argument
        let alive = document.getElementById("alive").value; // gets alive reward argument
        let die = document.getElementById("die").value; // gets die reward argument 
        if (food == "" || alive == "" || die == "") { // if any of the reward args were empty, sets running to false 
            running = false;
        }
        else { // reward args were valid 
            socket.emit("train", food, alive, die); // emits 'train' event via sociket with reward args 
            hidemeDiv.style.display = "block"; // displays the hidden div

        }
    }

})

document.getElementById("btn-off").addEventListener("click", function () { // adds event listener to off button
    running = false; // running is set to false when it's clicked 
})

function updateRunning() { 
    if (games > 98) { // if number of games plays exceeds 98
        running = false; // set running to false 
        
        // display training concluded to the canvas 
        ctx.font = "35px Quicksand";
        ctx.fillStyle = "black";
        ctx.textAlign = "center";
        ctx.fillText("training concluded", gameWidth / 2, gameHeight / 2);
    }
    else {
        running = true;
    }
}

//subscriber to training data
socket.on("snake_data", function (data, callback) { // when snake_data events are recieved from the server
    clearBoard(); // clear the board

    // updates food position, snake position, games played, score, and game score with the recieved data 
    foodX = data["data"]["apple"]["x"];
    foodY = data["data"]["apple"]["y"];
    snake = data["data"]["snake"];
    games = data["data"]["stats"]["games"];
    score = data["data"]["stats"]["score"];
    game_score = data["data"]["stats"]["record"];
    state = data["data"]["state"];

    // draws food, snake, and stats on the canvas 
    drawFood();
    drawSnake();
    drawStats();
    updateDangers();
    updateDirection();
    updateFood();

    console.log("running: " + running) // prints message to console that game is running 

    if (running) {
    }
    else { // game is not running 
        // stops the game and clears the board 
        games = 0 
        clearBoard();

        // displays training concluded message to canvas 
        ctx.font = "35px Quicksand";
        ctx.fillStyle = "black";
        ctx.textAlign = "center";
        ctx.fillText("training concluded", gameWidth / 2, gameHeight / 2);
        return callback(false) // calls the callback with false 
    }
    updateRunning(); // to check and update the running status 
})

function clearBoard() { /// fills board with bakground color to clear the prev contents  
    ctx.fillStyle = boardBackground;
    ctx.fillRect(0, 0, gameWidth, gameHeight);
};

function drawFood() { // draws food 
    ctx.fillStyle = foodColor;
    ctx.fillRect(foodX, foodY, unitSize, unitSize);
};

function drawSnake() { // draws snake 
    ctx.fillStyle = snakeColor;
    ctx.strokeStyle = snakeBorder;
    snake.forEach(snakePart => {
        ctx.fillRect(snakePart.x, snakePart.y, unitSize, unitSize);
        ctx.strokeRect(snakePart.x, snakePart.y, unitSize, unitSize);
    })
};

function drawStats() { // display score, high score, and number of games played to html elements 
    scoreText.textContent = score;
    highscoreText.textContent = game_score;
    if (games == 1000) {
        gamesText.textContent = "0/100"
    }
    else {
        gamesText.textContent = games + "/100"
    }
}

//const dangerAheadtText = document.querySelector("#dangerAhead");
//const dangerRightText = document.querySelector("#dangerRight");
//const dangerLeftText = document.querySelector("#dangerLeft");
//const directionText = document.querySelector("#direction");
//const foodLeftText = document.querySelector("#foodLeft");
//const foodRightText = document.querySelector("#foodRight");
//const foodAboveText = document.querySelector("#foodAbove");
//const foodBelowText = document.querySelector("#foodBelow");

function updateDangers() {
    const dangerAhead = state[0];
    const dangerRight = state[1];
    const dangerLeft = state[2];

    dangerAheadtText.textContent = numToWord(dangerAhead);
    dangerRightText.textContent = numToWord(dangerRight);
    dangerLeftText.textContent = numToWord(dangerLeft);

}

function updateDirection() {
    const left = state[3];
    const right = state[4];
    const up = state[5];
    const down = state[6];

    if (left == 1) {
        directionText.textContent = "Left";
    }
    else if (right == 1) {
        directionText.textContent = "Right";
    }
    else if (up == 1) {
        directionText.textContent = "Up";
    }
    else {
        directionText.textContent = "Down";
    }

}

function updateFood() {
    const left = state[7];
    const right = state[8];
    const up = state[9];
    const down = state[10];

    foodLeftText.textContent = numToWord(left);
    foodRightText.textContent = numToWord(right);
    foodAboveText.textContent = numToWord(up);
    foodBelowText.textContent = numToWord(down);
}

function numToWord(num) {
    if (num == 1) {
        return "Yes";
    }
    return "No";
}
