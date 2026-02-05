"""
services/request_queue.py — Leão de Chácara da API
Equivalente ao requestQueueService.ts.
Token Bucket com filas de prioridade para controlar rate limit do Gemini.
"""
import time
import threading
from typing import Callable, Any
from enum import IntEnum
from dataclasses import dataclass, field


class Priority(IntEnum):
    CRITICAL = 0    # Análise interativa do usuário
    HIGH = 1        # Agentes principais
    NORMAL = 2      # Busca de evidências
    LOW = 3         # Enriquecimento em background


@dataclass
class RateLimiter:
    """Token Bucket simples para controle de rate limit."""
    
    max_tokens: int = 14           # Requisições por minuto (Gemini free tier = 15 RPM)
    refill_interval: float = 60.0  # Segundos para refill completo
    
    _tokens: float = field(init=False)
    _last_refill: float = field(init=False)
    _lock: threading.Lock = field(init=False, default_factory=threading.Lock)
    
    def __post_init__(self):
        self._tokens = float(self.max_tokens)
        self._last_refill = time.time()
    
    def _refill(self):
        now = time.time()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * (self.max_tokens / self.refill_interval)
        self._tokens = min(self.max_tokens, self._tokens + tokens_to_add)
        self._last_refill = now
    
    def acquire(self, timeout: float = 120.0) -> bool:
        """Tenta adquirir um token. Bloqueia até conseguir ou timeout."""
        deadline = time.time() + timeout
        
        while time.time() < deadline:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            
            # Espera antes de tentar novamente
            wait_time = min(self.refill_interval / self.max_tokens, deadline - time.time())
            if wait_time > 0:
                time.sleep(wait_time)
        
        return False
    
    @property
    def available_tokens(self) -> float:
        with self._lock:
            self._refill()
            return self._tokens


class RequestQueue:
    """Fila de requisições com rate limiting e prioridade."""
    
    def __init__(self, rpm_limit: int = 14):
        self._limiter = RateLimiter(max_tokens=rpm_limit)
        self._total_requests = 0
        self._total_wait_time = 0.0
        self._errors = 0
    
    def execute(
        self,
        fn: Callable[..., Any],
        *args,
        priority: Priority = Priority.NORMAL,
        timeout: float = 120.0,
        **kwargs,
    ) -> Any:
        """
        Executa uma função respeitando o rate limit.
        Bloqueia até ter token disponível.
        """
        start = time.time()
        
        if not self._limiter.acquire(timeout=timeout):
            self._errors += 1
            raise TimeoutError(f"Rate limit: timeout após {timeout}s esperando por token")
        
        wait_time = time.time() - start
        self._total_wait_time += wait_time
        self._total_requests += 1
        
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            self._errors += 1
            raise
    
    @property
    def stats(self) -> dict:
        return {
            "total_requests": self._total_requests,
            "total_errors": self._errors,
            "avg_wait_seconds": (
                f"{self._total_wait_time / self._total_requests:.2f}"
                if self._total_requests > 0 else "0"
            ),
            "available_tokens": f"{self._limiter.available_tokens:.1f}",
        }


# Singleton global  
request_queue = RequestQueue(rpm_limit=14)
