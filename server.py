import os
import glob
from typing import List
import datetime
import markdown2
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import chromadb
from bleach import clean


load_dotenv()

app = Flask(__name__)


client = Groq(
    api_key=os.getenv('jfk_rag'),
)

# chroma persistent
db_path = "./chroma_db"
chroma_client = chromadb.PersistentClient(path=db_path)


collection_name = "documents_collection"
try:
    collection = chroma_client.get_collection(name=collection_name)
    print(f"Using existing collection with {collection.count()} documents")
except:
    collection = chroma_client.create_collection(name=collection_name)
    print(f"Created new collection: {collection_name}")

def load_documents(directory: str) -> List[dict]:
    """Load all text files from the specified directory."""
    documents = []
    
    if not os.path.exists(directory):
        print(f"Error: Directory '{directory}' does not exist.")
        return documents
    
    
    file_paths = glob.glob(f"{directory}/*.txt")
    
   
    print(f"Found {len(file_paths)} text files in '{directory}'")
    
    for i, file_path in enumerate(file_paths):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
                
                for j in range(0, len(content), 1000):
                    chunk = content[j:j+1000]
                    if len(chunk) > 100: 
                        doc_id = f"doc_{i}_chunk_{j//1000}"
                        documents.append({
                            "id": doc_id,
                            "text": chunk,
                            "metadata": {"source": os.path.basename(file_path)}
                        })
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return documents

def query(user_question: str, num_results: int = 10, chat_history=""):
    """Query the collection and generate a response using Groq."""
    
    results = collection.query(
        query_texts=[user_question],
        n_results=num_results
    )
    
    
    documents = "\n\n".join(results["documents"][0])
    sources = [doc["source"] for doc in results["metadatas"][0]]
    
    
    today = datetime.datetime.now().strftime("%B %d, %Y")
    
    
    system_prompt = f"""You are JFK FILES AI, an AI who specializes in historical/political research about the JFK assassination. Based on the user's query, you will dynamically be given a set of documents to reference (out of a total of thousands of documents).
Background: newly declassified JFK assassination files will be released in the coming weeks by President Trump's executive order - the order was made on Jan 23rd 2025 and will be released on March 18th 2025 (today's date is {today})
CHAT HISTORY:
{chat_history}
RULES:
- Keep things relevant to the convo, use a formal tone and stay on topic
- Say "CLASSIFIED" for unknown info
- Respond in a *semi-structured nature* where you **highlight** the most important information using the symbols * and ** (don't go overboard, but use this to help the user understand the most important information)
- Use precise dates and document references (use document name to assist the user with further research)
- If relevant, make suggestions to keep the conversation going
- Most importantly, be EXTREMELY concise; respond with 4-5 sentences unless asked otherwise
- Remember to look at the question from all possible angles, suspects and organisations, state and quote documents while doing so.

QUERY: {user_question}
DOCUMENTS (containing previously declassified information):
{documents}
If the user's query is not relevant, simply ignore the documents provided and ask them to rephrase. Otherwise, analyze and respond with facts found in the documents."""
    
    # Generate response with Groq
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_question,
            }
        ],
        model="llama-3.3-70b-versatile",
    )
    
    response = chat_completion.choices[0].message.content
    
    return response, sources

# Flask routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def process_chat():
    try:
        user_message = request.form.get('message')
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
        user_message = request.form.get("message", "")
        sanitized_message = clean(user_message)
        # Call the query function
        response, sources = query(sanitized_message)
        
        # Format response for htmx
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        response = markdown2.markdown(f"{response}")

        html_response = f"""
        <div class="message user">
            <div class="message-header">
                <span>You</span>
                <span>{current_time}</span>
            </div>
            <div class="message-content">{sanitized_message}</div>
        </div>
        <div class="message ai">
            <div class="message-header">
                <span>JFK Files AI</span>
                <span>{current_time}</span>
            </div>
            <div class="message-content">{response}</div>
            <div class="source-citation">Sources: {', '.join(sources[:10])}{' and more' if len(sources) > 10 else ''}</div>
        </div>
        """
        
        return html_response
    
    except Exception as e:
        print(f"Error processing request: {e}")
        return jsonify({"error": "An error occurred processing your request"}), 500

@app.route('/documents')
def documents():
    return render_template('documents.html')

@app.route('/timeline')
def timeline():
    return render_template('timeline.html')

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    try:
        app.run(debug=False, host='0.0.0.0',port=5004)
    except Exception as e:
        print(f"Application error: {e}")