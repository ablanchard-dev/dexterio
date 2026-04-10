import { useState, useEffect, useCallback } from 'react';
import api from '@/apiClient';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

/**
 * Pilotage de la boucle automatique — même UI en paper (validation) et au passage en live
 * (config serveur : EXECUTION_BACKEND, LIVE_TRADING_ENABLED). API : /trading/bot-status, /trading/control.
 */
export default function TradingLoopControls({ pollMs = 5000, compact = false }) {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await api.get('/trading/bot-status');
      setStatus(r.data);
    } catch (e) {
      console.error('bot-status', e);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, pollMs);
    return () => clearInterval(id);
  }, [load, pollMs]);

  const start = async () => {
    const msg = status?.live_trading_enabled
      ? 'Démarrer la boucle : le serveur est en mode LIVE — des ordres réels peuvent être envoyés. Continuer ?'
      : 'Démarrer la boucle automatique (paper / simulation selon la config) ?';
    if (!window.confirm(msg)) return;
    setBusy(true);
    try {
      await api.post('/trading/control', { action: 'start' });
      await load();
    } catch (e) {
      const d = e.response?.data?.detail;
      alert(typeof d === 'string' ? d : e.message || 'Erreur démarrage');
    } finally {
      setBusy(false);
    }
  };

  const stop = async () => {
    if (!window.confirm('Arrêter la boucle automatique ?')) return;
    setBusy(true);
    try {
      await api.post('/trading/control', { action: 'stop' });
      await load();
    } catch (e) {
      const d = e.response?.data?.detail;
      alert(typeof d === 'string' ? d : e.message || 'Erreur arrêt');
    } finally {
      setBusy(false);
    }
  };

  if (!status) {
    return (
      <div className={compact ? 'text-sm text-gray-500' : 'text-sm text-gray-400'}>
        Chargement état de la boucle…
      </div>
    );
  }

  const live = status.live_trading_enabled === true;

  return (
    <div className={compact ? 'space-y-2' : 'space-y-3'}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={status.running ? 'default' : 'secondary'} className="text-xs">
          {status.running ? 'Boucle active' : 'Boucle arrêtée'}
        </Badge>
        <span className="text-xs text-gray-500">
          {status.execution_backend || '—'} · tick {status.interval_sec ?? '?'}s
        </span>
        {live ? (
          <Badge variant="destructive" className="text-xs">
            Mode LIVE — capital réel
          </Badge>
        ) : (
          <Badge variant="outline" className="text-xs border-amber-700 text-amber-200">
            Mode PAPER — validation
          </Badge>
        )}
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" onClick={start} disabled={busy || status.running}>
          Démarrer la boucle
        </Button>
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={stop}
          disabled={busy || !status.running}
        >
          Arrêter la boucle
        </Button>
      </div>
      {!compact && (
        <p className="text-xs text-gray-500 leading-relaxed max-w-2xl">
          Finalité produit : valider la stratégie en paper, puis basculer vers le live via la configuration
          serveur — cette interface reste le poste de commande pour les deux phases.
        </p>
      )}
    </div>
  );
}
