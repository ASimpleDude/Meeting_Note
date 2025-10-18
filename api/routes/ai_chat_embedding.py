# =========================================
# 💡 DEMO: User → Embedding → ChromaDB → Query → GPT
# =========================================
# Yêu cầu:
# pip install openai chromadb

from openai import OpenAI
import chromadb

# 1️⃣ Khởi tạo OpenAI client & ChromaDB
openai_client = OpenAI(api_key="YOUR_OPENAI_API_KEY")
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("knowledge_base")

# 2️⃣ Nhập dữ liệu nguồn (có thể từ file, tài liệu, web, v.v.)
documents = [
    "Hà Nội là thủ đô của Việt Nam.",
    "Thành phố Hồ Chí Minh là trung tâm kinh tế lớn nhất Việt Nam.",
    "Việt Nam nổi tiếng với món phở và cà phê.",
]

# 3️⃣ Tạo embedding cho từng đoạn
embeddings = [
    openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=doc
    ).data[0].embedding for doc in documents
]

# 4️⃣ Lưu vào ChromaDB
collection.add(
    ids=[str(i) for i in range(len(documents))],
    documents=documents,
    embeddings=embeddings
)
print("✅ Đã lưu dữ liệu vào ChromaDB.\n")

# =========================================
# 5️⃣ User đặt câu hỏi
# =========================================
user_query = input("❓ Nhập câu hỏi của bạn: ")

# Tạo embedding cho câu hỏi
query_emb = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=user_query
).data[0].embedding

# Truy vấn ChromaDB tìm các đoạn văn gần nhất
results = collection.query(
    query_embeddings=[query_emb],
    n_results=2
)

# Lấy văn bản liên quan nhất
context = "\n".join(results["documents"][0])
print(f"\n📚 Ngữ cảnh tìm được:\n{context}\n")

# =========================================
# 6️⃣ Gửi ngữ cảnh + câu hỏi vào GPT để trả lời
# =========================================
prompt = f"""
Dưới đây là một số thông tin liên quan:
{context}

Dựa trên thông tin trên, hãy trả lời câu hỏi sau:
{user_query}
"""

response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}]
)

print("🤖 Trả lời từ GPT:\n")
print(response.choices[0].message.content)
