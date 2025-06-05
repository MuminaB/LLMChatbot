let conversation = [];
let chatCounter = 1;

document.addEventListener("DOMContentLoaded", () => {
  const studentId = sessionStorage.getItem("student_id");
  const guestId = sessionStorage.getItem("guest_id");
  const storageKey = `unsaved_chat_${studentId || guestId || "anon"}`;

  // Load saved conversation (if exists)
  const savedChat = localStorage.getItem(storageKey);
  if (savedChat) {
    conversation = JSON.parse(savedChat);
    conversation.forEach(msg => {
      appendMessage(msg.content, msg.role);
    });
  }

  document.getElementById('send-btn').addEventListener('click', sendMessage);
  document.getElementById('user-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  document.getElementById("history-btn").addEventListener("click", toggleSidebar);

  document.getElementById("new-chat").addEventListener("click", async () => {
    if (conversation.length) {
      try {
        const res = await fetch("/save-session", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages: conversation })
        });
        const result = await res.json();
        alert(`${result.message}`);
        loadSessionList();
      } catch (err) {
        alert("⚠️ Failed to save chat.");
      }
    }

    try {
      const res = await fetch("/reset", { method: "POST" });
      if (res.status === 403) {
        showLimitModal();
        return;
      }
      document.getElementById("chat-messages").innerHTML = "";
      conversation = [];
      localStorage.removeItem(storageKey); // clear only this user's chat
    } catch (err) {
      alert("Something went wrong while resetting the chat.");
    }
  });

  document.getElementById("clear-history").addEventListener("click", () => {
    document.getElementById("chat-messages").innerHTML = "";
  });

  document.getElementById("export-chat").addEventListener("click", () => {
    if (!conversation.length) return;
    let exportText = "";
    conversation.forEach(msg => {
      const label = msg.role === "user" ? "You" : "Bot";
      exportText += `${label}: ${msg.content}\n`;
    });
    const blob = new Blob([exportText], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = "chat_history.txt";
    link.click();
  });

  document.getElementById('profile-btn').addEventListener('click', function (e) {
    e.preventDefault();
    const menu = document.getElementById('profile-menu');
    menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';
  });

  window.addEventListener('click', function (e) {
    const menu = document.getElementById('profile-menu');
    const profileBtn = document.getElementById('profile-btn');
    if (!menu.contains(e.target) && !profileBtn.contains(e.target)) {
      menu.style.display = 'none';
    }
  });

  // Hide sidebar by default on load
  document.getElementById("chat-sidebar").style.display = "none";

  // Feedback submission
  document.getElementById('submit-feedback').addEventListener('click', async () => {
    const rating = document.getElementById('rating').value;
    const comment = document.getElementById('feedback').value.trim();
    if (!rating) return alert('Please select a rating.');

    try {
      const res = await fetch('/submit-feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rating, comment })
      });
      if (res.ok) {
        alert('✅ Feedback submitted successfully!');
        document.getElementById('feedback').value = '';
        document.getElementById('rating').selectedIndex = 0;
      } else {
        alert('⚠️ Failed to submit feedback.');
      }
    } catch (err) {
      alert('❌ Error submitting feedback.');
    }
  });

  // Save storageKey to window for reuse in other functions
  window.currentStorageKey = storageKey;
});

function showLimitModal() {
  document.getElementById('limit-modal').style.display = 'flex';
}

function closeModal() {
  document.getElementById('limit-modal').style.display = 'none';
}

function linkify(text) {
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return text.replace(urlRegex, url => `<a href="${url}" target="_blank" style="color:#0047ab; text-decoration: underline;">${url}</a>`);
}

function appendMessage(content, role) {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = role === 'user' ? 'user-message' : 'bot-message';
  msg.innerHTML = linkify(content);
  container.appendChild(msg);
  scrollToBottom();
  conversation.push({ role, content });
  updateLocalChatStorage();
}

function typeBotResponse(content) {
  const container = document.getElementById('chat-messages');
  const msg = document.createElement('div');
  msg.className = 'bot-message';
  container.appendChild(msg);

  let index = 0;
  const delay = 10;

  function type() {
    if (index < content.length) {
      msg.innerHTML = linkify(content.slice(0, index + 1));
      index++;
      setTimeout(type, delay);
    } else {
      msg.innerHTML = linkify(content);
      conversation.push({ role: 'assistant', content });
      updateLocalChatStorage();
      scrollToBottom();
    }
  }

  type();
}

function updateLocalChatStorage() {
  if (window.currentStorageKey) {
    localStorage.setItem(window.currentStorageKey, JSON.stringify(conversation));
  }
}

function scrollToBottom() {
  const chatWindow = document.getElementById('chat-window');
  chatWindow.scrollTop = chatWindow.scrollHeight;
}



function toggleSidebar() {
  const sidebar = document.getElementById("chat-sidebar");
  const visible = sidebar.style.display === "block";
  sidebar.style.display = visible ? "none" : "block";
  if (!visible) loadSessionList();
}

async function loadSessionList() {
  const res = await fetch("/sessions");
  const sessions = await res.json();
  const list = document.getElementById("chat-history-list");
  list.innerHTML = "";

  sessions.forEach(session => {
    const li = document.createElement("li");
    li.innerHTML = `
      ${session.session_name}
      <button onclick="deleteSession(${session.id})" style="margin-left: 10px; background: red; color: white; border: none; padding: 2px 6px; border-radius: 4px; font-size: 12px;">🗑️</button>
    `;
    li.style.cursor = "pointer";
    li.onclick = () => loadSession(session.id);
    list.appendChild(li);
  });
}

async function deleteSession(id) {
  if (!confirm("Are you sure you want to delete this chat permanently?")) return;
  try {
    const res = await fetch(`/delete-session/${id}`, { method: "POST" });
    const data = await res.json();
    alert(data.message);
    loadSessionList();
  } catch (err) {
    alert("❌ Failed to delete chat.");
  }
}

async function loadSession(id) {
  try {
    const res = await fetch(`/load-session/${id}`);
    const messages = await res.json();
    const container = document.getElementById("chat-messages");
    container.innerHTML = "";
    conversation = [];

    messages.forEach(msg => {
      appendMessage(msg.content, msg.role);
    });

    scrollToBottom();
  } catch (err) {
    alert("Failed to load session.");
  }
}

async function sendMessage() {
  const input = document.getElementById('user-input');
  const message = input.value.trim();
  if (!message) return;

  appendMessage(message, 'user');
  input.value = '';

  const typingDiv = document.createElement('div');
  typingDiv.className = 'typing-indicator';
  typingDiv.innerText = 'Bot is typing...';
  document.getElementById('chat-messages').appendChild(typingDiv);
  scrollToBottom();

  try {
    const response = await fetch('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });

    const data = await response.json();
    typingDiv.remove();

    if (response.status === 403) {
      alert(data.message || "Guest limit reached. Please sign up to continue.");
      disableInput();
      window.location.href = "/signup";
      return;
    }

    typeBotResponse(data.response);
  } catch (error) {
    typingDiv.remove();
    appendMessage('Sorry, something went wrong.', 'bot');
  }
}

function disableInput() {
  document.getElementById('user-input').disabled = true;
  document.getElementById('send-btn').disabled = true;
  document.getElementById('new-chat').disabled = true;
}
