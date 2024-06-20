const socket = io({ autoConnect: false }); // creates new Socket.IO client instance with autoConnect as false --> doesn't automatically connect to the server 

document.getElementById("join-btn").addEventListener("click", function () { // event listener for the join button
    let username = document.getElementById("username").value; //  gets value of username 
    socket.connect(); // connects Socket.IO client to the server

    document.cre 

    socket.on("connect", function () { // event listener for the connect event --> triggered when client successfully connects to the server 
        socket.emit("user_join", username); // emits 'user_join' event to the server with the username as the payload 
    })
})


document.getElementById("btn-train").addEventListener("click", function () { // event listener for the train button 
    socket.emit("train"); // emits 'train' event to the server 
})

socket.on("snake_data", function (data) { // listens for snake_data event from the server 
    let ul = document.getElementById("ul-snake-data"); // selects unordered list element with the id ul-snake-data
    let li = document.createElement("li") // creates new list item element 
    li.appendChild(document.createTextNode(data["data"]["snake"][0]["x"])); // adds x coordinate of the first segment of the snake to the list item as text 
    ul.appendChild(li) // appends new list item to the unordered list 
    ul.scrollTop = ul.scrollHeight; // scrolls the unordered list to the bottom to show the latest data 
})
