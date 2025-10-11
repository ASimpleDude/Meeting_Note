let session_id = localStorage.getItem("session_id");
let sessions = JSON.parse(localStorage.getItem("sessions")) || {}; // lưu lịch sử chat trên client
let currentSession = session_id || createNewSession();

// ===============================
// Tạo session mới
// ===============================
function createNewSession() {
  const id = crypto.randomUUID();
  localStorage.setItem("session_id", id);
  sessions[id] = [];
  saveSessionsToStorage();
  renderSessionList();
  return id;
}

function saveSessionsToStorage() {
  localStorage.setItem("sessions", JSON.stringify(sessions));
}

// ===============================
// Render danh sách session
// ===============================
function renderSessionList() {
  const ul = document.getElementById("sessionList");
  ul.innerHTML = "";
  for (const id in sessions) {
    const li = document.createElement("li");
    li.textContent = `Cuộc trò chuyện ${id.slice(0,6)}`;
    li.onclick = () => switchSession(id);
    ul.appendChild(li);
  }
}
renderSessionList();

function switchSession(id) {
  currentSession = id;
  localStorage.setItem("session_id", id);
  renderChat();
}

// ===============================
// Hiển thị chat của session hiện tại
// ===============================
function renderChat() {
  const chatDiv = document.getElementById("chat");
  chatDiv.innerHTML = "";
  const messages = sessions[currentSession] || [];
  for (const msg of messages) {
    const cls = msg.role === "user" ? "user" : "ai";
    chatDiv.innerHTML += `<div class="msg ${cls}"><pre>${msg.content}</pre></div>`;
  }
  chatDiv.scrollTop = chatDiv.scrollHeight;
}
renderChat();

// ===============================
// Auto-resize textarea
// ===============================
function autoResize(textarea) {
  textarea.style.height = "auto";
  textarea.style.height = textarea.scrollHeight + "px";
}

// ===============================
// Handle Enter key
// ===============================
function handleKey(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
}

// ===============================
// Gửi message lên backend
// ===============================
async function sendMessage() {
  const userInput = document.getElementById("userInput");
  const chatDiv = document.getElementById("chat");
  const msg = userInput.value.trim();
  if (!msg) return;

  // Append user message
  chatDiv.innerHTML += `<div class="msg user"><pre>${msg}</pre></div>`;
  chatDiv.scrollTop = chatDiv.scrollHeight;
  userInput.value = "";
  userInput.style.height = "auto";

  // Lưu trên client
  if (!sessions[currentSession]) sessions[currentSession] = [];
  sessions[currentSession].push({role: "user", content: msg});
  saveSessionsToStorage();

  // Gọi backend
  try {
    const response = await fetch("http://127.0.0.1:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, session_id: currentSession })
    });
    const data = await response.json();
    const reply = data.reply;

    // Append AI message
    chatDiv.innerHTML += `<div class="msg ai"><pre>${reply}</pre></div>`;
    chatDiv.scrollTop = chatDiv.scrollHeight;

    // Lưu AI message
    sessions[currentSession].push({role: "assistant", content: reply});
    saveSessionsToStorage();

    // Cập nhật session_id nếu backend trả session mới
    currentSession = data.session_id;
    localStorage.setItem("session_id", currentSession);
    renderSessionList();

  } catch (error) {
    chatDiv.innerHTML += `<div class="msg ai" style="color:red;"><pre>⚠️ Lỗi: Không kết nối được server</pre></div>`;
  }
}

// ===============================
// Nút tạo session mới
// ===============================
document.getElementById("newSessionBtn").onclick = () => {
  currentSession = createNewSession();
  renderChat();
};
