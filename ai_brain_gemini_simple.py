"""
Gemini AI with Token Caching (Cost Reduction)
Supports: gemini-3.5-flash, gemini-3.1-flash-lite, gemini-3-flash-preview
"""

import requests
import json
import time
import hashlib
import os

class GeminiAISimple:
    def __init__(self, api_key, model="gemini-3.1-flash-lite"):
        self.api_key = api_key
        self.model = model
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        
        # Token cache (your "virtual RAM")
        self.cache_dir = "token_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'tokens_saved': 0,
            'cost_saved_usd': 0.0
        }
    
    def _get_cache_key(self, prompt):
        """Hash prompt for cache lookup"""
        return hashlib.sha256(prompt.encode()).hexdigest()[:16]
    
    def _check_cache(self, cache_key):
        """Check if response is cached"""
        cache_file = f"{self.cache_dir}/{cache_key}.json"
        
        if os.path.exists(cache_file):
            with open(cache_file) as f:
                data = json.load(f)
                
                # Check expiry (default 1 hour)
                if time.time() < data.get('expires_at', 0):
                    self.stats['cache_hits'] += 1
                    self.stats['tokens_saved'] += data.get('tokens', 0)
                    # Estimate cost saved: ~$0.00015 per 1K tokens
                    self.stats['cost_saved_usd'] += data.get('tokens', 0) * 0.00015 / 1000
                    return data['response']
                else:
                    os.remove(cache_file)  # Expired
        
        self.stats['cache_misses'] += 1
        return None
    
    def _save_cache(self, cache_key, response, ttl=3600):
        """Save response to cache"""
        cache_file = f"{self.cache_dir}/{cache_key}.json"
        
        with open(cache_file, 'w') as f:
            json.dump({
                'response': response,
                'tokens': len(response.split()),
                'cached_at': time.time(),
                'expires_at': time.time() + ttl,
                'model': self.model
            }, f)
    
    def chat(self, prompt, use_cache=True, ttl=3600):
        """Chat with Gemini (with token caching)"""
        self.stats['total_requests'] += 1
        
        # Check cache first
        if use_cache:
            cache_key = self._get_cache_key(prompt)
            cached = self._check_cache(cache_key)
            if cached:
                return {
                    'response': cached,
                    'from_cache': True,
                    'stats': self.stats.copy()
                }
        
        # Cache miss — call Gemini
        url = f"{self.base_url}?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            ai_response = data['candidates'][0]['content']['parts'][0]['text']
            
            # Save to cache
            if use_cache:
                self._save_cache(cache_key, ai_response, ttl)
            
            return {
                'response': ai_response,
                'from_cache': False,
                'stats': self.stats.copy()
            }
        
        except Exception as e:
            return {
                'response': f"AI error: {str(e)}",
                'from_cache': False,
                'error': str(e),
                'stats': self.stats.copy()
            }
    
    def get_stats(self):
        """Get cache statistics"""
        total = self.stats['total_requests']
        if total == 0:
            return self.stats
        
        hit_rate = (self.stats['cache_hits'] / total) * 100
        return {
            **self.stats,
            'cache_hit_rate_percent': round(hit_rate, 1),
            'cost_reduction_percent': round(hit_rate, 1)
        }

# Global instance
ai_brain = None

def init_gemini(api_key, model="gemini-3.1-flash-lite"):
    """
    Initialize Gemini AI
    Models:
    - gemini-3.5-flash: Most intelligent (higher cost)
    - gemini-3.1-flash-lite: Most cost-efficient (RECOMMENDED)
    - gemini-3-flash-preview: Speed + intelligence
    """
    global ai_brain
    ai_brain = GeminiAISimple(api_key=api_key, model=model)
    return ai_brain
