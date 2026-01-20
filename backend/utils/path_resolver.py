"""
P2 Phase 1 - Portable Path Resolver

Module centralisé pour résoudre les chemins de façon portable (Windows/Linux).
Élimine les hardcodes /app/... et permet l'exécution locale.

Usage:
    from utils.path_resolver import get_repo_root, data_path, results_path
    
    # Get root directory
    root = get_repo_root()  # /app ou C:/Users/.../project
    
    # Get standard paths
    hist_data = data_path("historical/1m")
    results = results_path()
    backtest_results = data_path("backtest_results")
"""
import os
from pathlib import Path
from typing import Optional


# ============================================================================
# Auto-detection du repo root
# ============================================================================

def get_repo_root() -> Path:
    """
    Détecte automatiquement la racine du repository.
    
    Stratégie (P2-2.B hotfix Windows):
    1. Override manuel via DEXTERIO_REPO_ROOT (priorité absolue)
    2. Détection Docker forte (/.dockerenv existe)
    3. Calcul depuis ce fichier (Windows-safe)
    
    Returns:
        Path object du repo root
    """
    # Strategy 1: Manual override (Windows-safe)
    override = os.getenv("DEXTERIO_REPO_ROOT")
    if override:
        p = Path(override).resolve()
        if p.exists() and (p / "backend").exists():
            return p
    
    # Strategy 2: Real Docker detection (strong signal)
    if Path("/.dockerenv").exists():
        docker_root = Path("/app")
        if docker_root.exists() and (docker_root / "backend").exists():
            return docker_root
    
    # Strategy 3: Relative from this file (Windows default)
    # Ce fichier est dans backend/utils/path_resolver.py
    # Donc repo_root = ../../ depuis ici
    current_file = Path(__file__).resolve()
    backend_dir = current_file.parent.parent  # backend/
    repo_root = backend_dir.parent  # project root
    
    # Vérifier que c'est bien le repo root (doit contenir backend/)
    if (repo_root / "backend").exists():
        return repo_root
    
    # Strategy 4: Fallback to cwd
    cwd = Path.cwd()
    if (cwd / "backend").exists():
        return cwd
    
    # Strategy 5: Try parent of cwd (Windows: often repo root is parent of cwd if executed from backend/)
    cwd_parent = cwd.parent
    if (cwd_parent / "backend").exists():
        return cwd_parent
    
    # Last resort: return cwd (even if invalid, better than crashing)
    # In practice, Strategy 3 should always succeed if this file is in the repo
    return cwd


# Cache du repo root pour éviter recalculs
_REPO_ROOT: Optional[Path] = None


def repo_root() -> Path:
    """Returns cached repo root."""
    global _REPO_ROOT
    if _REPO_ROOT is None:
        _REPO_ROOT = get_repo_root()
    return _REPO_ROOT


# ============================================================================
# Standard paths helpers
# ============================================================================

def backend_path(*parts: str) -> Path:
    """
    Retourne un chemin dans backend/.
    
    Example:
        backend_path("results", "summary.json")
        -> /app/backend/results/summary.json (Docker)
        -> C:/Users/.../backend/results/summary.json (Windows)
    """
    return repo_root() / "backend" / Path(*parts)


def data_path(*parts: str) -> Path:
    """
    Retourne un chemin dans data/.
    
    Example:
        data_path("historical", "1m", "SPY.parquet")
        -> /app/data/historical/1m/SPY.parquet
    """
    return repo_root() / "data" / Path(*parts)


def results_path(*parts: str) -> Path:
    """
    Retourne un chemin dans backend/results/.
    
    Example:
        results_path("baseline_1d.json")
        -> /app/backend/results/baseline_1d.json
    """
    return backend_path("results", *parts)


def backtest_results_path(*parts: str) -> Path:
    """
    Retourne un chemin dans data/backtest_results/.
    
    Example:
        backtest_results_path("equity_baseline_1d.parquet")
        -> /app/data/backtest_results/equity_baseline_1d.parquet
    """
    return data_path("backtest_results", *parts)


def historical_data_path(timeframe: str = "1m", *parts: str) -> Path:
    """
    Retourne un chemin dans data/historical/{timeframe}/.
    
    Example:
        historical_data_path("1m", "SPY.parquet")
        -> /app/data/historical/1m/SPY.parquet
    """
    return data_path("historical", timeframe, *parts)


# ============================================================================
# Helpers pour découverte de fichiers
# ============================================================================

def discover_symbol_parquet(symbol: str, timeframe: str = "1m") -> Optional[Path]:
    """
    Découvre automatiquement le fichier Parquet pour un symbole.
    
    Cherche dans cet ordre:
    1. {symbol.upper()}.parquet
    2. {symbol.lower()}.parquet
    3. {symbol.lower()}_1m_*.parquet (legacy multi-file)
    
    Returns:
        Path du fichier si trouvé, None sinon
    """
    base = historical_data_path(timeframe)
    
    if not base.exists():
        return None
    
    # Try direct files
    direct_upper = base / f"{symbol.upper()}.parquet"
    if direct_upper.exists():
        return direct_upper
    
    direct_lower = base / f"{symbol.lower()}.parquet"
    if direct_lower.exists():
        return direct_lower
    
    # Try legacy pattern
    pattern = f"{symbol.lower()}_{timeframe}_*.parquet"
    matches = list(base.glob(pattern))
    if matches:
        return matches[0]  # Return first match
    
    return None


def ensure_dir(path: Path) -> Path:
    """
    Crée un répertoire s'il n'existe pas.
    
    Returns:
        Le path (pour chaînage)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


# ============================================================================
# Environment info (debugging)
# ============================================================================

def get_environment_info() -> dict:
    """
    Retourne des infos sur l'environnement d'exécution.
    Utile pour debugging / logs.
    """
    root = repo_root()
    return {
        "repo_root": str(root),
        "is_docker": (root == Path("/app")),
        "backend_exists": (root / "backend").exists(),
        "data_exists": (root / "data").exists(),
        "cwd": str(Path.cwd()),
        "platform": os.name,  # 'posix' ou 'nt' (Windows)
    }


# ============================================================================
# Self-test
# ============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("PATH RESOLVER - Self Test")
    print("=" * 80)
    
    env = get_environment_info()
    print("\n📂 Environment Info:")
    print(json.dumps(env, indent=2))
    
    print("\n📁 Standard Paths:")
    print(f"  repo_root():              {repo_root()}")
    print(f"  backend_path():           {backend_path()}")
    print(f"  data_path():              {data_path()}")
    print(f"  results_path():           {results_path()}")
    print(f"  backtest_results_path():  {backtest_results_path()}")
    print(f"  historical_data_path():   {historical_data_path()}")
    
    print("\n🔍 Symbol Discovery:")
    for sym in ["SPY", "QQQ"]:
        path = discover_symbol_parquet(sym)
        status = "✅ Found" if path else "❌ Not found"
        print(f"  {sym}: {status} → {path}")
    
    print("\n" + "=" * 80)
    print("✅ Path Resolver OK")
    print("=" * 80)
