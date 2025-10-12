from openai import AzureOpenAI
from tenacity import retry, stop_after_attempt, wait_random_exponential
from api.config import AZURE_OPENAI_API_KEY, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_VERSION

# Initialize Azure OpenAI client
client = AzureOpenAI(
    api_key=AZURE_OPENAI_API_KEY,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

@retry(wait=wait_random_exponential(min=1, max=30), stop=stop_after_attempt(5))
def chat_completion(messages, model="gpt-4o-mini", temperature=0.2):
    """Call Azure OpenAI Chat API with retry & error handling."""
    return client.chat.completions.create(model=model, messages=messages)

def moderate_text(text):
    """Moderate input text using OpenAI moderation endpoint."""
    return client.moderations.create(input=text)
