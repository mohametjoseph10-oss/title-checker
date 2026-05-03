from sentence_transformers import SentenceTransformer, util
import string

model = SentenceTransformer('all-MiniLM-L6-v2')

def clean_text(text):
    text = text.lower()
    text = text.translate(str.maketrans('', '', string.punctuation))
    return text.strip()

def check_similarity(input_title, existing_titles):
    if not model:
        return None, 0.0, "Model loading failed"
        
    cleaned_input = clean_text(input_title)
    if not cleaned_input:
        return None, 0.0, "Empty input"
        
    cleaned_existing = [clean_text(t) for t in existing_titles]
    
    # Compute embeddings
    input_emb = model.encode(cleaned_input)
    existing_embs = model.encode(cleaned_existing)
    
    # Compute cosine similarities
    cos_scores = util.cos_sim(input_emb, existing_embs)[0]
    
    # Find the highest score
    best_idx = cos_scores.argmax().item()
    best_score = cos_scores[best_idx].item()
    
    return existing_titles[best_idx], best_score
