document.addEventListener("DOMContentLoaded", function() {
  const chatMessages = document.getElementById("chat-messages");
  const userInput = document.getElementById("user-input");
  const sendBtn = document.getElementById("send-btn");
  const newChatBtn = document.getElementById("new-chat");
  const clearHistoryBtn = document.getElementById("clear-history");
  const submitFeedbackBtn = document.getElementById("submit-feedback");
  
  function sendMessage() {
      const message = userInput.value.trim();
      if (!message) return;

      chatMessages.innerHTML += `<div class='user-message'>${message}</div>`;
      userInput.value = "";
      
      fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message })
      })
      .then(response => response.json())
      .then(data => {
          chatMessages.innerHTML += `<div class='bot-message'>${data.response}</div>`;
      })
      .catch(error => console.error("Error communicating with backend:", error));
  }

  sendBtn.addEventListener("click", sendMessage);
  userInput.addEventListener("keypress", function(event) {
      if (event.key === "Enter") sendMessage();
  });
  
  newChatBtn.addEventListener("click", function() {
      chatMessages.innerHTML = "";
  });
  
  clearHistoryBtn.addEventListener("click", function() {
      fetch("/clear-history", { method: "POST" })
      .then(() => { chatMessages.innerHTML = ""; });
  });
  
  submitFeedbackBtn.addEventListener("click", function() {
      const rating = document.getElementById("rating").value;
      const feedback = document.getElementById("feedback").value;
      
      fetch("/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rating, feedback })
      })
      .then(() => { alert("Feedback submitted!"); })
      .catch(error => console.error("Error submitting feedback:", error));
  });
});
