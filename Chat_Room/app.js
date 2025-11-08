let ws;
const joinScreen = document.getElementById("join-screen");
const chatScreen = document.getElementById("chat-screen");
const usernameInput = document.getElementById("username");
const roomInput = document.getElementById("room");
const messagesDiv = document.getElementById("messages");
const messageInput = document.getElementById("messageInput");
const roomTitle = document.getElementById("room-name");

document.getElementById("joinBtn").addEventListener("click", () => {
  const username = usernameInput.value.trim();
  const room = roomInput.value.trim();
  if (!username || !room) return alert("Please enter both username and room name!");

  ws = new WebSocket("ws://localhost:2025");

  ws.onopen = () => {
    ws.send(JSON.stringify({ type: "join", username, room }));
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "join_success") {
      joinScreen.classList.add("hidden");
      chatScreen.classList.remove("hidden");
      roomTitle.textContent = `Room: ${room}`;
      data.history.forEach(msg => addMessage(msg, "system"));
    } else if (data.type === "message") {
      const msg = `[${data.timestamp}] ${data.username}: ${data.message}`;
      addMessage(msg, data.username === username ? "self" : "other");
    } else if (data.type === "error") {
      alert(data.message);
    }
  };
});

document.getElementById("sendBtn").addEventListener("click", () => {
  const message = messageInput.value.trim();
  if (message && ws) {
    ws.send(JSON.stringify({ type: "message", message }));
    messageInput.value = "";
  }
});

document.getElementById("leaveBtn").addEventListener("click", () => {
  if (ws) ws.close();
  window.location.reload();
});

function addMessage(text, type = "other") {
  const div = document.createElement("div");
  div.classList.add("message");
  if (type === "system") div.classList.add("system");
  if (type === "self") div.classList.add("self");
  div.textContent = text;
  messagesDiv.appendChild(div);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}
