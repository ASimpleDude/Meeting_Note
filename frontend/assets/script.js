let currentSession = null;

// ===============================
// Lấy danh sách session từ backend
// ===============================
async function renderSessionList() {
  const ul = document.getElementById("sessionList");
  ul.innerHTML = "";

  try {
    const res = await fetch("http://127.0.0.1:8000/api/sessions");
    const sessions = await res.json(); // [{id, name}, ...]
    sessions.forEach(session => {
      const li = document.createElement("li");
      li.style.display = "flex";
      li.style.justifyContent = "space-between";
      li.style.alignItems = "center";
      li.style.marginBottom = "5px";

      // Tên session
      const span = document.createElement("span");
      span.textContent = session.name;
      span.style.cursor = "pointer";
      span.onclick = () => switchSession(session.id);
      li.appendChild(span);

      // Icon xóa
      const deleteBtn = document.createElement("span");
      deleteBtn.innerHTML = "🗑"; // icon thùng rác
      deleteBtn.style.cursor = "pointer";
      deleteBtn.style.color = "red";
      deleteBtn.onclick = async (e) => {
        e.stopPropagation(); // tránh trigger switchSession
        if (!confirm("Bạn có chắc muốn xóa toàn bộ cuộc trò chuyện này?")) return;

        try {
          await fetch(`http://127.0.0.1:8000/api/chat/${session.id}`, { method: "DELETE" });
          // Nếu xóa session đang mở thì clear chat
          if (currentSession === session.id) {
            currentSession = null;
            document.getElementById("chat").innerHTML = "";
          }
          await renderSessionList(); // refresh danh sách
        } catch (error) {
          console.error("⚠️ Lỗi khi xóa session:", error);
        }
      };
      li.appendChild(deleteBtn);

      ul.appendChild(li);
    });
  } catch (error) {
    console.error("⚠️ Lỗi khi lấy danh sách session:", error);
  }
}

renderSessionList();

// ===============================
// Chuyển session
// ===============================
async function switchSession(session_id) {
  currentSession = session_id;
  await renderChat();
}

// ===============================
// Hiển thị chat của session hiện tại
// ===============================
async function renderChat() {
  const chatDiv = document.getElementById("chat");
  chatDiv.innerHTML = "";
  if (!currentSession) return;

  try {
    const res = await fetch(`http://127.0.0.1:8000/api/chat/${currentSession}`);
    const messages = await res.json(); // [{role, content, audio_path?}, ...]

    for (const msg of messages) {
      if (msg.role === "user") {
        // Tin nhắn user
        const userDiv = document.createElement("div");
        userDiv.className = "msg user";
        const pre = document.createElement("pre");
        pre.textContent = msg.content;
        userDiv.appendChild(pre);
        chatDiv.appendChild(userDiv);
      } else if (msg.role === "assistant") {
        // Tin nhắn AI
        const aiDiv = document.createElement("div");
        aiDiv.className = "msg ai";

        // Nội dung text
        const pre = document.createElement("pre");
        pre.textContent = msg.content;
        aiDiv.appendChild(pre);

        // Nếu có audio, thêm audio control ngay dưới
        if (msg.audio_path) {
          const audioDiv = document.createElement("div");
          audioDiv.style.marginTop = "10px";

          const audioEl = document.createElement("audio");
          audioEl.controls = true;
          audioEl.style.width = "100%";
          audioEl.style.maxWidth = "400px";

          const source = document.createElement("source");
          source.src = msg.audio_path;
          source.type = "audio/wav";
          audioEl.appendChild(source);

          audioDiv.appendChild(audioEl);
          aiDiv.appendChild(audioDiv);
        }

        chatDiv.appendChild(aiDiv);
      }
    }

    // Scroll xuống cuối chat
    chatDiv.scrollTop = chatDiv.scrollHeight;
  } catch (error) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "msg ai";
    errorDiv.style.color = "red";
    const pre = document.createElement("pre");
    pre.textContent = "⚠️ Lỗi khi load chat";
    errorDiv.appendChild(pre);
    chatDiv.appendChild(errorDiv);
  }
}


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
  if (!currentSession) {
    alert("Vui lòng chọn hoặc tạo session trước!");
    return;
  }

  const userInput = document.getElementById("userInput");
  const ttsInput = document.getElementById("tts");
  const chatDiv = document.getElementById("chat");
  const msg = userInput.value.trim();
  const tts = ttsInput.checked;
  if (!msg) return;

  // Append user message bằng createElement
  const userDiv = document.createElement("div");
  userDiv.className = "msg user";
  const preUser = document.createElement("pre");
  preUser.textContent = msg;
  userDiv.appendChild(preUser);
  chatDiv.appendChild(userDiv);
  chatDiv.scrollTop = chatDiv.scrollHeight;

  userInput.value = "";
  userInput.style.height = "auto";

  try {
    const response = await fetch("http://127.0.0.1:8000/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, session_id: currentSession, tts: tts })
    });
    const data = await response.json();
    const reply = data.reply;
    const audio_path = data.audio_path || null;

    // Append AI message chuẩn
    appendAiMessage(reply, audio_path);

    currentSession = data.session_id;
    renderSessionList(); // refresh danh sách session
  } catch (error) {
    const errorDiv = document.createElement("div");
    errorDiv.className = "msg ai";
    errorDiv.style.color = "red";
    const preError = document.createElement("pre");
    preError.textContent = "⚠️ Lỗi: Không kết nối được server";
    errorDiv.appendChild(preError);
    chatDiv.appendChild(errorDiv);
    chatDiv.scrollTop = chatDiv.scrollHeight;
  }
}

// Hàm append AI message chuẩn
function appendAiMessage(reply, audio_path=null) {
  const chatDiv = document.getElementById("chat");

  const aiDiv = document.createElement("div");
  aiDiv.className = "msg ai";

  const pre = document.createElement("pre");
  pre.textContent = reply;
  aiDiv.appendChild(pre);

  if (audio_path) {
    const audioDiv = document.createElement("div");
    audioDiv.style.marginTop = "10px";

    const audioEl = document.createElement("audio");
    audioEl.controls = true;
    audioEl.style.width = "100%";
    audioEl.style.maxWidth = "400px";

    const source = document.createElement("source");
    source.src = audio_path;
    source.type = "audio/wav";
    audioEl.appendChild(source);

    audioDiv.appendChild(audioEl);
    aiDiv.appendChild(audioDiv);
  }

  chatDiv.appendChild(aiDiv);
  chatDiv.scrollTop = chatDiv.scrollHeight;
}


// ===============================
// Tạo session mới
// ===============================
document.getElementById("newSessionBtn").onclick = () => {
  // Tạo session mới tạm thời trên frontend
  const newId = crypto.randomUUID();
  currentSession = newId;

  // Hiển thị tên session là thời gian hiện tại
  const sessionName = new Date().toLocaleString();

  // Thêm session vào danh sách HTML
  const ul = document.getElementById("sessionList");
  const li = document.createElement("li");
  li.textContent = sessionName;
  li.onclick = () => switchSession(newId);
  ul.appendChild(li);

  // Hiển thị chat trống
  const chatDiv = document.getElementById("chat");
  chatDiv.innerHTML = "";
};


// ===============================
// Nút xóa chat
// ===============================
document.getElementById("clearChatBtn").onclick = async () => {
  if (!currentSession) return;
  if (!confirm("Bạn có chắc muốn xóa toàn bộ cuộc trò chuyện này?")) return;

  try {
    await fetch(`http://127.0.0.1:8000/api/chat/${currentSession}`, { method: "DELETE" });
    await renderChat(); // load lại chat (trống)
    renderSessionList(); // cập nhật danh sách session
  } catch (error) {
    console.error("⚠️ Lỗi khi xóa chat:", error);
  }
};


// Append AI message
function appendAiMessage(reply, audio_path=null) {
  const chatDiv = document.getElementById("chat");

  // Wrapper cho mỗi message
  const msgWrapper = document.createElement("div");
  msgWrapper.className = "msg ai";

  // Nội dung text
  const pre = document.createElement("pre");
  pre.textContent = reply;
  msgWrapper.appendChild(pre);

  // Nếu có audio, thêm audio control ngay dưới
  if (audio_path) {
    const audioDiv = document.createElement("div");
    audioDiv.style.marginTop = "10px";
    const audioEl = document.createElement("audio");
    audioEl.controls = true;
    audioEl.style.width = "100%";
    audioEl.style.maxWidth = "400px";

    const source = document.createElement("source");
    source.src = audio_path;
    source.type = "audio/wav";
    audioEl.appendChild(source);

    audioDiv.appendChild(audioEl);
    msgWrapper.appendChild(audioDiv);
  }

  chatDiv.appendChild(msgWrapper);
  chatDiv.scrollTop = chatDiv.scrollHeight;
}
