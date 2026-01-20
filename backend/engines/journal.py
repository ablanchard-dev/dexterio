"""Trade Journal & Performance Statistics"""
import logging
import os
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, Field
from models.trade import Trade
import uuid
from utils.path_resolver import data_path

logger = logging.getLogger(__name__)

class TradeJournalEntry(BaseModel):
    """Entry complète dans le journal (TJR)"""
    
    # Identification
    trade_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp_opened: datetime
    timestamp_closed: Optional[datetime] = None
    
    # Instrument
    symbol: str
    direction: str
    trade_type: str
    
    # Contexte Marché
    date: date
    session: str
    session_profile: int = 0
    bias_htf: str
    bias_confidence: float = 0.0
    daily_structure: str = ''
    h4_structure: str = ''
    h1_structure: str = ''
    market_conditions: str = ''
    
    # Setup
    playbook: str
    setup_quality: str
    setup_score: float
    confluences: Dict[str, bool] = {}
    confluences_count: int = 0
    ict_patterns: List[str] = []
    candlestick_patterns: List[str] = []
    
    # Risk & Sizing
    account_balance_at_entry: float
    risk_pct: float
    risk_amount: float
    position_size: float
    position_type: str = 'shares'
    
    # Prix
    entry_price: float
    stop_loss_initial: float
    stop_loss_final: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    exit_price: float
    
    # Résultat
    outcome: str
    pnl_dollars: float
    pnl_pct: float
    r_multiple: float
    duration_minutes: float
    exit_reason: str
    
    # Psychologie (TJR)
    emotions_before: str = ''
    emotions_during: str = ''
    emotions_after: str = ''
    discipline_respected: bool = True
    mistakes: str = ''
    lessons: str = ''
    tags: List[str] = []
    
    # Notes
    notes: str = ''
    screenshots: List[str] = []
    
    # Metadata
    trading_mode: str
    backtest_run_id: str | None = None

    version: str = '1.0'

class TradeJournal:
    """Gestion du journal de trades (Parquet)"""
    
    def __init__(self, journal_path: str = None):
        if journal_path is None:
            journal_path = str(data_path('trade_journal.parquet'))
        self.journal_path = journal_path
        self.entries = []
        
        # Créer dossier si nécessaire
        os.makedirs(os.path.dirname(journal_path), exist_ok=True)
        
        # Charger existant
        self.load()
        
        logger.info(f"TradeJournal initialized: {len(self.entries)} existing entries")
    
    def add_entry(self, trade: Trade, context: Dict[str, Any] = None):
        """
        Ajoute une entrée au journal
        
        Args:
            trade: Trade object complet
            context: Contexte additionnel (market_state, setup, etc.)
        """
        context = context or {}
        
        entry = TradeJournalEntry(
            trade_id=trade.id,
            timestamp_opened=trade.time_entry,
            timestamp_closed=trade.time_exit,
            
            symbol=trade.symbol,
            direction=trade.direction,
            trade_type=trade.trade_type,
            
            date=trade.date.date() if isinstance(trade.date, datetime) else trade.date,
            session=trade.session,
            session_profile=trade.session_profile,
            bias_htf=trade.bias_htf,
            market_conditions=trade.market_conditions,
            
            playbook=trade.playbook,
            setup_quality=trade.setup_quality,
            setup_score=trade.setup_score,
            confluences=trade.confluences,
            confluences_count=sum(1 for v in trade.confluences.values() if v),
            
            account_balance_at_entry=context.get('account_balance', 0),
            risk_pct=trade.risk_pct,
            risk_amount=trade.risk_amount,
            position_size=trade.position_size,
            
            entry_price=trade.entry_price,
            stop_loss_initial=trade.stop_loss,
            stop_loss_final=trade.stop_loss,
            take_profit_1=trade.take_profit_1,
            take_profit_2=trade.take_profit_2,
            exit_price=trade.exit_price,
            
            outcome=trade.outcome,
            pnl_dollars=trade.pnl_dollars,
            pnl_pct=trade.pnl_pct,
            r_multiple=trade.r_multiple,
            duration_minutes=trade.duration_minutes,
            exit_reason=trade.exit_reason,
            
            emotions_before=trade.emotions_entry if hasattr(trade, 'emotions_entry') else '',
            emotions_during=trade.emotions_during if hasattr(trade, 'emotions_during') else '',
            emotions_after=trade.emotions_exit if hasattr(trade, 'emotions_exit') else '',
            mistakes=trade.mistakes if hasattr(trade, 'mistakes') else '',
            lessons=trade.lessons if hasattr(trade, 'lessons') else '',
            
            backtest_run_id=context.get('backtest_run_id'),

            
            notes=trade.notes if hasattr(trade, 'notes') else '',
            
            trading_mode=context.get('trading_mode', 'SAFE')
        )
        
        self.entries.append(entry)
        self._save()
        
        logger.info(f"Trade journal entry added: {trade.id} ({trade.outcome})")
    
    def _save(self):
        """Sauvegarde en Parquet"""
        if not self.entries:
            return
        
        df = pd.DataFrame([e.model_dump() for e in self.entries])
        df.to_parquet(self.journal_path, index=False)
        logger.debug(f"Journal saved: {len(self.entries)} entries")
    
    def load(self):
        """Charge le journal"""
        if os.path.exists(self.journal_path):
            try:
                df = pd.read_parquet(self.journal_path)
                self.entries = [TradeJournalEntry(**row.to_dict()) for _, row in df.iterrows()]
                logger.info(f"Journal loaded: {len(self.entries)} entries")
            except Exception as e:
                logger.error(f"Error loading journal: {e}")
                self.entries = []
    
    def filter(self, **filters) -> List[TradeJournalEntry]:
        """
        Filtre les entrées
        
        Examples:
            journal.filter(outcome='win', trade_type='DAILY')
            journal.filter(playbook='NY_Open_Reversal')
        """
        filtered = self.entries
        for key, value in filters.items():
            filtered = [e for e in filtered if getattr(e, key, None) == value]
        return filtered
    
    def get_all(self) -> List[TradeJournalEntry]:
        """Retourne toutes les entrées"""
        return self.entries

class PerformanceStats:
    """Calcul des KPIs de trading"""
    
    def __init__(self, journal: TradeJournal):
        self.journal = journal
    
    def calculate_kpis(self, filters: Dict = None) -> Dict[str, Any]:
        """
        Calcule tous les KPIs
        
        Returns:
            Dict avec tous les indicateurs
        """
        entries = self.journal.filter(**filters) if filters else self.journal.entries
        
        if not entries:
            return {
                'total_trades': 0,
                'winrate': 0,
                'total_pnl_r': 0,
                'expectancy': 0
            }
        
        wins = [e for e in entries if e.outcome == 'win']
        losses = [e for e in entries if e.outcome == 'loss']
        
        return {
            # Basiques
            'total_trades': len(entries),
            'wins': len(wins),
            'losses': len(losses),
            'breakevens': len([e for e in entries if e.outcome == 'breakeven']),
            'winrate': len(wins) / len(entries) * 100 if entries else 0,
            
            # P&L
            'total_pnl_dollars': sum(e.pnl_dollars for e in entries),
            'total_pnl_r': sum(e.r_multiple for e in entries),
            'avg_pnl_r': sum(e.r_multiple for e in entries) / len(entries) if entries else 0,
            
            # R statistics
            'avg_win_r': sum(e.r_multiple for e in wins) / len(wins) if wins else 0,
            'avg_loss_r': sum(e.r_multiple for e in losses) / len(losses) if losses else 0,
            'largest_win_r': max((e.r_multiple for e in wins), default=0),
            'largest_loss_r': min((e.r_multiple for e in losses), default=0),
            
            # Expectancy
            'expectancy': self._calculate_expectancy(entries),
            
            # Profit Factor
            'profit_factor': self._calculate_profit_factor(entries),
            
            # Sharpe Ratio
            'sharpe_ratio': self._calculate_sharpe(entries),
            
            # Streaks
            'max_win_streak': self._max_streak(entries, 'win'),
            'max_loss_streak': self._max_streak(entries, 'loss'),
            
            # Par type
            'daily_trades': len([e for e in entries if e.trade_type == 'DAILY']),
            'scalp_trades': len([e for e in entries if e.trade_type == 'SCALP']),
            
            # Par playbook
            'by_playbook': self._stats_by_playbook(entries),
            
            # Par quality
            'by_quality': self._stats_by_quality(entries),
            
            # Drawdown
            'max_drawdown_r': self._calculate_max_dd(entries)
        }
    
    def _calculate_expectancy(self, entries: List[TradeJournalEntry]) -> float:
        """Expectancy = (Winrate × Avg Win) - (Lossrate × Avg Loss)"""
        if not entries:
            return 0
        
        wins = [e.r_multiple for e in entries if e.outcome == 'win']
        losses = [abs(e.r_multiple) for e in entries if e.outcome == 'loss']
        
        winrate = len(wins) / len(entries)
        lossrate = len(losses) / len(entries)
        
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        
        return (winrate * avg_win) - (lossrate * avg_loss)
    
    def _calculate_profit_factor(self, entries: List[TradeJournalEntry]) -> float:
        """Profit Factor = Gross Profit / Gross Loss"""
        gross_profit = sum(e.pnl_dollars for e in entries if e.pnl_dollars > 0)
        gross_loss = abs(sum(e.pnl_dollars for e in entries if e.pnl_dollars < 0))
        
        return gross_profit / gross_loss if gross_loss > 0 else 0
    
    def _calculate_sharpe(self, entries: List[TradeJournalEntry]) -> float:
        """Sharpe Ratio"""
        returns = [e.pnl_pct for e in entries]
        if len(returns) < 2:
            return 0
        
        mean_return = np.mean(returns)
        std_return = np.std(returns)
        risk_free = 0.01
        
        return (mean_return - risk_free) / std_return if std_return > 0 else 0
    
    def _max_streak(self, entries: List[TradeJournalEntry], outcome_type: str) -> int:
        """Calcule max streak"""
        max_streak = 0
        current_streak = 0
        
        for entry in entries:
            if entry.outcome == outcome_type:
                current_streak += 1
                max_streak = max(max_streak, current_streak)
            else:
                current_streak = 0
        
        return max_streak
    
    def _stats_by_playbook(self, entries: List[TradeJournalEntry]) -> Dict:
        """Statistiques par playbook"""
        playbooks = {}
        for entry in entries:
            pb = entry.playbook
            if pb not in playbooks:
                playbooks[pb] = {'trades': 0, 'wins': 0, 'total_r': 0}
            
            playbooks[pb]['trades'] += 1
            if entry.outcome == 'win':
                playbooks[pb]['wins'] += 1
            playbooks[pb]['total_r'] += entry.r_multiple
        
        for pb in playbooks:
            playbooks[pb]['winrate'] = playbooks[pb]['wins'] / playbooks[pb]['trades'] * 100
            playbooks[pb]['avg_r'] = playbooks[pb]['total_r'] / playbooks[pb]['trades']
        
        return playbooks
    
    def _stats_by_quality(self, entries: List[TradeJournalEntry]) -> Dict:
        """Stats par quality"""
        qualities = {}
        for entry in entries:
            q = entry.setup_quality
            if q not in qualities:
                qualities[q] = {'trades': 0, 'wins': 0, 'total_r': 0}
            
            qualities[q]['trades'] += 1
            if entry.outcome == 'win':
                qualities[q]['wins'] += 1
            qualities[q]['total_r'] += entry.r_multiple
        
        for q in qualities:
            qualities[q]['winrate'] = qualities[q]['wins'] / qualities[q]['trades'] * 100
            qualities[q]['avg_r'] = qualities[q]['total_r'] / qualities[q]['trades']
        
        return qualities
    
    def _calculate_max_dd(self, entries: List[TradeJournalEntry]) -> float:
        """Calcule max drawdown en R"""
        if not entries:
            return 0
        
        cumulative_r = 0
        peak_r = 0
        max_dd = 0
        
        for entry in entries:
            cumulative_r += entry.r_multiple
            peak_r = max(peak_r, cumulative_r)
            dd = peak_r - cumulative_r
            max_dd = max(max_dd, dd)
        
        return max_dd
