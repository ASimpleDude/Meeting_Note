# =========================================
# 🧠 Demo: ChromaDB QA không cần AI
# =========================================
# Cài trước các thư viện:
# pip install chromadb sentence-transformers

from chromadb import Client
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import re

# ========================
# 1️⃣ Khởi tạo database
# ========================
client = Client(Settings(persist_directory="./chroma_db"))
collection = client.get_or_create_collection("meeting_notes")

# ========================
# 2️⃣ Model embedding
# ========================
model = SentenceTransformer("keepitreal/vietnamese-sbert")

# ========================
# 3️⃣ Dữ liệu meeting
# ========================
meeting_text = """
Scrum Master: Chào mọi người, chúng ta bắt đầu daily nhé. An, hôm qua em làm gì và hôm nay kế hoạch ra sao?
An (Backend): Hôm qua em hoàn thiện API login, hôm nay sẽ làm phần xác thực token. Không có blocker.
Huy (Frontend): Em đang làm giao diện dashboard, còn vài lỗi hiển thị cần fix. Blocker là chưa có dữ liệu thật để test.
Lan (Tester): Bên QA mới test được phần đăng ký, đang chờ build mới để test phần login.
Scrum Master: Ok, Minh gửi dữ liệu cho Huy và build mới cho Lan nhé. Cảm ơn mọi người, kết thúc daily.
""".strip()

lines = [l.strip() for l in meeting_text.split("\n") if l.strip()]

# Xóa dữ liệu cũ (demo lại mỗi lần)
collection.delete(where={})

# Encode & nạp vào Chroma
embeddings = model.encode(lines).tolist()
collection.add(
    documents=lines,
    embeddings=embeddings,
    ids=[f"line_{i}" for i in range(len(lines))]
)

print("✅ Đã nạp dữ liệu meeting vào ChromaDB.\n")

# ========================
# 4️⃣ Hàm tìm & trả lời
# ========================
def find_answer(question: str):
    query_emb = model.encode([question]).tolist()
    results = collection.query(query_embeddings=query_emb, n_results=2)

    if not results["documents"]:
        return "❌ Không tìm thấy thông tin phù hợp."

    # Lấy đoạn văn gần nghĩa nhất
    doc = results["documents"][0][0]

    # Nếu có dạng "Tên (Role): ..." thì tách thông tin
    match = re.match(r"^([A-ZĐÂÊÔƠƯa-zđâêôơưÀ-ỹ\s]+)\s*\((.*?)\):\s*(.*)$", doc)
    if match:
        name, role, content = match.groups()
        name = name.strip()
        role = role.strip()
        return f"{name} là {role.lower()}, {content}"
    else:
        return doc

# ========================
# 5️⃣ Demo hỏi đáp
# ========================
sample_questions = [
    "An là ai?",
    "An hôm nay làm gì?",
    "Blocker của Huy là gì?",
    "Lan đang làm gì?",
]

for q in sample_questions:
    print(f"❓ {q}")
    print("➡️", find_answer(q))
    print()
