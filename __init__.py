"""
services/cache_service.py — Armazém Inteligente
Equivalente ao advancedCacheService.ts.
Cache de dois níveis: L1 (memória) + L2 (disco via diskcache).
"""
import hashlib
import json
import time
from typing import Any, Optional
from functools import lru_cache

try:
    import diskcache
    HAS_DISKCACHE = True
except ImportError:
    HAS_DISKCACHE = False


class CacheService:
    """Cache de dois níveis para resultados de API."""
    
    def __init__(self, cache_dir: str = ".scout_cache", default_ttl: int = 3600):
        # L1 — Memória (dict simples)
        self._l1: dict[str, dict] = {}
        self._default_ttl = default_ttl
        
        # L2 — Disco
        if HAS_DISKCACHE:
            self._l2 = diskcache.Cache(cache_dir, size_limit=500 * 1024 * 1024)  # 500MB
        else:
            self._l2 = None
        
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, namespace: str, params: dict) -> str:
        """Gera uma chave de cache determinística."""
        raw = f"{namespace}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:24]
    
    def get(self, namespace: str, params: dict) -> Optional[Any]:
        """Busca no cache L1 → L2."""
        key = self._make_key(namespace, params)
        
        # L1 check
        if key in self._l1:
            entry = self._l1[key]
            if entry['expires'] > time.time():
                self._hits += 1
                return entry['value']
            else:
                del self._l1[key]
        
        # L2 check
        if self._l2 is not None:
            try:
                entry = self._l2.get(key)
                if entry is not None and entry.get('expires', 0) > time.time():
                    # Promote to L1
                    self._l1[key] = entry
                    self._hits += 1
                    return entry['value']
            except Exception:
                pass
        
        self._misses += 1
        return None
    
    def set(self, namespace: str, params: dict, value: Any, ttl: Optional[int] = None):
        """Armazena em L1 + L2."""
        key = self._make_key(namespace, params)
        ttl = ttl or self._default_ttl
        entry = {
            'value': value,
            'expires': time.time() + ttl,
            'namespace': namespace,
        }
        
        # L1
        self._l1[key] = entry
        
        # L2
        if self._l2 is not None:
            try:
                self._l2.set(key, entry, expire=ttl)
            except Exception:
                pass
    
    def invalidate(self, namespace: str, params: dict):
        """Remove entrada específica."""
        key = self._make_key(namespace, params)
        self._l1.pop(key, None)
        if self._l2 is not None:
            try:
                self._l2.delete(key)
            except Exception:
                pass
    
    def clear_all(self):
        """Limpa todo o cache."""
        self._l1.clear()
        if self._l2 is not None:
            try:
                self._l2.clear()
            except Exception:
                pass
    
    @property
    def stats(self) -> dict:
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{(self._hits / total * 100):.1f}%" if total > 0 else "0%",
            "l1_size": len(self._l1),
            "l2_size": len(self._l2) if self._l2 else 0,
        }


# Singleton global
cache = CacheService()
