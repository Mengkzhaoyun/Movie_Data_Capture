import json
import requests
import traceback
import config

def get_ai_client():
    conf = config.getInstance()
    if not conf.ai_enable() or not conf.ai_api_key():
        return None
    return {
        "api_key": conf.ai_api_key(),
        "api_base": conf.ai_api_base().rstrip('/'),
        "model": conf.ai_model()
    }

def ai_chat_completion(prompt, system_prompt="You are a helpful assistant.", temperature=0.7):
    client = get_ai_client()
    if not client:
        return None
        
    url = f"{client['api_base']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {client['api_key']}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": client['model'],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature
    }
    
    proxy_conf = config.getInstance().proxy()
    proxies = proxy_conf.proxies() if proxy_conf.enable else None
    
    try:
        response = requests.post(url, headers=headers, json=payload, proxies=proxies, timeout=30)
        response.raise_for_status()
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[-] AI API Error:", e)
        if config.getInstance().debug():
            traceback.print_exc()
            
    return None

def ai_translate_and_correct(text, field_type="text"):
    if not text:
        return text
        
    system_prompt = (
        "You are an expert translator and metadata correcter for Japanese adult videos. "
        "Your task is to correct OCR/scraping errors, properly translate Japanese into natural Simplified Chinese, "
        "and return ONLY the translated/corrected text without any extra explanation or conversational filler."
    )
    
    if field_type == "title":
        prompt = f"Correct and translate this video title into Simplified Chinese. Remove irrelevant website suffixes if they exist: '{text}'"
    elif field_type == "outline":
        prompt = f"Translate this video outline into natural Simplified Chinese: '{text}'"
    else:
        prompt = f"Correct and translate this into Simplified Chinese: '{text}'"
        
    result = ai_chat_completion(prompt, system_prompt, temperature=0.3)
    return result if result else text

def ai_process_tags(tag_list):
    if not tag_list or len(tag_list) == 0:
        return tag_list
        
    system_prompt = (
        "You are an expert metadata tagger for Japanese adult videos. "
        "I will give you a comma-separated list of raw tags. "
        "Please standardize them into concise Simplified Chinese tags. "
        "Remove meaningless tags, combine synonyms, fix OCR errors, and output exactly as a comma-separated list. "
        "No extra conversational text."
    )
    
    prompt = f"Raw tags: {','.join(tag_list)}"
    result = ai_chat_completion(prompt, system_prompt, temperature=0.2)
    
    if result:
        # cleanup if AI returns quotes or extra spaces, handle Chinese commas
        return [t.strip().strip("'").strip('"') for t in result.replace('，', ',').split(',') if t.strip()]
        
    return tag_list
