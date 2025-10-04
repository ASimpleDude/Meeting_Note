// ===============================
// ✅ Tự động thay đổi chiều cao của ô nhập (auto-resize)
// ===============================
function autoResize(textarea) {
  textarea.style.height = "auto"; // Reset chiều cao
  textarea.style.height = textarea.scrollHeight + "px"; // Mở rộng theo nội dung thực tế
}

// ===============================
// ✅ Xử lý khi người dùng nhấn phím Enter
// ===============================
function handleKey(event) {
  // Shift + Enter để xuống dòng
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault(); // Không xuống dòng
    sendMessage(); // Gửi tin nhắn
  }
}

// ===============================
// ✅ Hàm gửi tin nhắn tới server FastAPI
// ===============================
async function sendMessage() {
  // Lấy phần tử HTML của ô input và khung chat
  const userInput = document.getElementById("userInput");
  const chatDiv = document.getElementById("chat");

  // Lấy nội dung người dùng nhập vào và loại bỏ khoảng trắng thừa
  const msg = userInput.value.trim();

  // Nếu ô trống thì không làm gì cả
  if (!msg) return;

  // ===============================
  // 🧍 Hiển thị tin nhắn của người dùng lên giao diện
  // ===============================
  chatDiv.innerHTML += `<div class="msg user"><pre>${msg}</pre></div>`;
  chatDiv.scrollTop = chatDiv.scrollHeight; // Tự động cuộn xuống cuối
  userInput.value = ""; // Xóa nội dung sau khi gửi
  userInput.style.height = "auto"; // Thu nhỏ lại chiều cao ban đầu

  try {
    // ===============================
    // 🌐 Gửi yêu cầu POST đến API backend (FastAPI)
    // ===============================
    const response = await fetch("http://127.0.0.1:8000/chat", {
      method: "POST", // Gửi dạng POST
      headers: { "Content-Type": "application/json" }, // Dữ liệu gửi đi ở dạng JSON
      body: JSON.stringify({ message: msg }), // Chuyển message thành chuỗi JSON
    });

    // Chuyển phản hồi từ server (JSON) thành object JS
    const data = await response.json();

    // ===============================
    // 🤖 Hiển thị phản hồi của AI lên giao diện
    // ===============================
    chatDiv.innerHTML += `<div class="msg ai"><pre>${data.reply}</pre></div>`;
    chatDiv.scrollTop = chatDiv.scrollHeight; // Cuộn xuống dòng cuối cùng
  } catch (error) {
    // ===============================
    // ⚠️ Xử lý lỗi nếu không kết nối được đến server
    // ===============================
    chatDiv.innerHTML += `<div class="msg ai" style="color:red;"><pre>⚠️ Lỗi: Không kết nối được server</pre></div>`;
  }
}
