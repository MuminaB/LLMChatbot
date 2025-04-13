
document.addEventListener("DOMContentLoaded", function () {
    const chatMessages = document.getElementById("chat-messages");
    const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const newChatBtn = document.getElementById("new-chat");
  const clearHistoryBtn = document.getElementById("clear-history");
  const submitFeedbackBtn = document.getElementById("submit-feedback");
  const exportChatBtn = document.getElementById("export-chat"); // export button
  const historySidebarList = document.getElementById("chat-history-list");

  let chatHistory = JSON.parse(localStorage.getItem("chatHistory")) || [];

  //let sessionId = null;
  let sessionId = localStorage.getItem("sessionId") || null;
  console.log("sessionId:", sessionId);

  if (!sessionId) {
    startNewSession(); // Automatically starts a new session if none is found
  }


  function startNewSession() {
    fetch("/start-session", { method: "POST" })
      .then(res => res.json())
      .then(data => {
        sessionId = data.session_id;
        localStorage.setItem("sessionId", sessionId);
      });
  }
  

  function createTimestamp() {
    return new Date().toLocaleTimeString();
  }

  function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    const pair = document.createElement("div");
    pair.classList.add("message-pair");

    const userDiv = document.createElement("div");
    userDiv.classList.add("user-message");
    userDiv.textContent = message;

    const timeDiv = document.createElement("div");
    timeDiv.classList.add("timestamp");
    timeDiv.textContent = createTimestamp();

    userDiv.appendChild(timeDiv);
    pair.appendChild(userDiv);
    chatMessages.appendChild(pair);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: message,
        session_id: sessionId
      })
    })
    .then((res) => res.json())
    .then((data) => {
      const botDiv = document.createElement("div");
      botDiv.classList.add("bot-message");
      botDiv.textContent = "Typing...";
      pair.appendChild(botDiv);
      chatMessages.scrollTop = chatMessages.scrollHeight;
    
      setTimeout(() => {
        if (data.response) {
          botDiv.textContent = data.response;
        } else {
          botDiv.textContent = "⚠️ No reply from server.";
        }
        const botTime = document.createElement("div");
        botTime.classList.add("timestamp");
        botTime.textContent = createTimestamp();
        botDiv.appendChild(botTime);
      }, 700);
    
      if (chatHistory.length === 0) chatHistory.push([]);
      chatHistory[chatHistory.length - 1].push({
        user: message,
        bot: data.response,
      });
    
      localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
      updateHistory();
      userInput.value = "";
    })
    .catch((err) => {
      console.error("Fetch error:", err);
      const botDiv = document.createElement("div");
      botDiv.classList.add("bot-message");
      botDiv.textContent = "⚠️ Error contacting server.";
      pair.appendChild(botDiv);
    });
    
  }

  function updateHistory() {
    historySidebarList.innerHTML = "";
    chatHistory.forEach((chat, index) => {
      const li = document.createElement("li");
      li.innerHTML = `Chat ${index + 1}
        <span class="delete-icon" onclick="deleteChat(${index})">🗑️</span>`;
      li.onclick = () => loadChat(index);
      historySidebarList.appendChild(li);
    });
  }

  function loadChat(index) {
    chatMessages.innerHTML = "";
    chatHistory[index].forEach((pair) => {
      const pairDiv = document.createElement("div");
      pairDiv.classList.add("message-pair");

      const userDiv = document.createElement("div");
      userDiv.classList.add("user-message");
      userDiv.textContent = pair.user;

      const botDiv = document.createElement("div");
      botDiv.classList.add("bot-message");
      botDiv.textContent = pair.bot;

      pairDiv.appendChild(userDiv);
      pairDiv.appendChild(botDiv);
      chatMessages.appendChild(pairDiv);
    });
  }

  function deleteChat(index) {
    chatHistory.splice(index, 1);
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
    updateHistory();
    chatMessages.innerHTML = "";
  }

  function toggleSidebar() {
    const sidebar = document.getElementById("chat-sidebar");
    sidebar.style.display =
      sidebar.style.display === "block" ? "none" : "block";
  }

  window.toggleSidebar = toggleSidebar;

  sendBtn.addEventListener("click", sendMessage);
  userInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") sendMessage();
  });

  newChatBtn.addEventListener("click", () => {
    chatMessages.innerHTML = "";
    chatHistory.push([]);
    localStorage.setItem("chatHistory", JSON.stringify(chatHistory));
    updateHistory();
  
    startNewSession(); // ✅ This line starts a new session and stores sessionId
  });
  
  clearHistoryBtn.addEventListener("click", () => {
    fetch("/clear-history", { method: "POST" }).then(() => {
      chatMessages.innerHTML = "";
      chatHistory = [];
      localStorage.removeItem("chatHistory");
      updateHistory();
    });
  });

  submitFeedbackBtn.addEventListener("click", () => {
    const rating = document.getElementById("rating").value;
    const feedback = document.getElementById("feedback").value;

    fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, feedback }),
    })
    .then(() => alert("Feedback submitted!"))
    .catch((err) => console.error("Feedback error:", err));
  });

  exportChatBtn.addEventListener("click", () => {
    let text = "";
    chatHistory.forEach((session, i) => {
      text += `Chat ${i + 1}\n`;
      session.forEach((pair) => {
        text += "You: " + pair.user + "\n";
        text += "Bot: " + pair.bot + "\n\n";
      });
    });

    const blob = new Blob([text], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "chat_history.txt";
    link.click();
  });

  const latest = chatHistory[chatHistory.length - 1] || [];
  if (latest.length) loadChat(chatHistory.length - 1);
  updateHistory();
});


