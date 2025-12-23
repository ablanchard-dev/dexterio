"""
Market State Cache - Cache le market state pour éviter les recalculs inutiles
"""
from typing import Dict, Optional, Tuple
from datetime import datetime
from models.market_data import MarketState


class MarketStateCache:
    """
    Cache le market state et ne le recalcule que sur événements (HTF close, session change).
    Clé de contexte = (symbol, session, last_1h_close_ts, last_4h_close_ts, last_1d_close_ts)
    """
    
    def __init__(self):
        # Cache: clé -> MarketState
        self.cache: Dict[Tuple, MarketState] = {}
        
        # Dernières clés connues par symbole
        self.last_key: Dict[str, Optional[Tuple]] = {}
        
        # Stats
        self.hits = 0
        self.misses = 0
    
    def get_cache_key(self, symbol: str, session: str, 
                     last_1h_close: Optional[datetime],
                     last_4h_close: Optional[datetime],
                     last_1d_close: Optional[datetime]) -> Tuple:
        """Génère une clé de cache basée sur le contexte"""
        return (
            symbol,
            session,
            last_1h_close.isoformat() if last_1h_close else None,
            last_4h_close.isoformat() if last_4h_close else None,
            last_1d_close.isoformat() if last_1d_close else None
        )
    
    def get(self, key: Tuple) -> Optional[MarketState]:
        """Récupère le market state depuis le cache"""
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def put(self, key: Tuple, market_state: MarketState):
        """Stocke le market state dans le cache"""
        self.cache[key] = market_state
        
        # Limiter la taille du cache (garder les 1000 dernières entrées)
        if len(self.cache) > 1000:
            # Supprimer les 100 plus anciennes
            keys_to_remove = list(self.cache.keys())[:100]
            for k in keys_to_remove:
                del self.cache[k]
    
    def should_recalculate(self, symbol: str, new_key: Tuple) -> bool:
        """Détermine si on doit recalculer le market state"""
        last_key = self.last_key.get(symbol)
        if last_key is None:
            # Première fois, on doit calculer
            self.last_key[symbol] = new_key
            return True
        
        if last_key != new_key:
            # Le contexte a changé, on doit recalculer
            self.last_key[symbol] = new_key
            return True
        
        # Contexte identique, pas besoin de recalculer
        return False
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de cache"""
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "cache_size": len(self.cache)
        }
