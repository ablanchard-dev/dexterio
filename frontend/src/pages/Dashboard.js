import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Activity, DollarSign, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const [marketState, setMarketState] = useState(null);
  const [riskState, setRiskState] = useState(null);
  const [performance, setPerformance] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(fetchDashboardData, 10000); // Update every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [marketRes, riskRes, perfRes] = await Promise.all([
        axios.get(`${API}/trading/market-state`),
        axios.get(`${API}/trading/risk-state`),
        axios.get(`${API}/trading/performance`)
      ]);

      setMarketState(marketRes.data);
      setRiskState(riskRes.data);
      setPerformance(perfRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading dashboard...</div>
      </div>
    );
  }

  const getStatusColor = () => {
    if (!riskState.trading_allowed) return 'text-red-500';
    if (riskState.daily_trade_count >= 3) return 'text-yellow-500';
    return 'text-green-500';
  };

  const getBiasColor = (bias) => {
    if (bias === 'bullish') return 'bg-green-500';
    if (bias === 'bearish') return 'bg-red-500';
    return 'bg-gray-500';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">DexterioBOT Dashboard</h1>
          <p className="text-gray-400 mt-1">Real-time trading overview</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline" className="text-lg px-4 py-2">
            {riskState.trading_mode}
          </Badge>
          <Badge variant="outline" className="text-lg px-4 py-2">
            PAPER TRADING
          </Badge>
        </div>
      </div>

      {/* Status Alert */}
      {!riskState.trading_allowed && (
        <Card className="bg-red-900/20 border-red-500">
          <CardContent className="flex items-center gap-2 py-4">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <span className="text-red-400 font-semibold">TRADING FROZEN: {riskState.freeze_reason}</span>
          </CardContent>
        </Card>
      )}

      {/* Main Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Account Balance */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Account Balance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${riskState.account_balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
            <p className="text-xs text-gray-400 mt-1">Peak: ${riskState.peak_balance.toLocaleString()}</p>
          </CardContent>
        </Card>

        {/* Daily P&L */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Daily P&L</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold flex items-center gap-2 ${riskState.daily_pnl_dollars >= 0 ? 'text-green-500' : 'text-red-500'}`}>
              {riskState.daily_pnl_dollars >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
              ${Math.abs(riskState.daily_pnl_dollars).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
            <p className="text-xs text-gray-400 mt-1">{riskState.daily_pnl_r >= 0 ? '+' : ''}{riskState.daily_pnl_r.toFixed(2)}R</p>
          </CardContent>
        </Card>

        {/* Current Risk */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Current Risk</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{(riskState.current_risk_pct * 100).toFixed(1)}%</div>
            <p className="text-xs text-gray-400 mt-1">
              {riskState.current_risk_pct === 0.02 ? 'Base risk' : 'Reduced (after loss)'}
            </p>
          </CardContent>
        </Card>

        {/* Trades Today */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Trades Today</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${getStatusColor()}`}>
              {riskState.daily_trade_count}
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Open: {riskState.open_positions_count}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Market State */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* SPY */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>SPY</span>
              <Badge className={getBiasColor(marketState?.htf_bias?.SPY)}>
                {marketState?.htf_bias?.SPY?.toUpperCase()}
              </Badge>
            </CardTitle>
            <CardDescription>S&P 500 ETF</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${marketState?.spy_price?.toFixed(2)}</div>
            <div className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Session:</span>
                <span className="font-medium">{marketState?.session}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Structure (Daily):</span>
                <span className="font-medium">{marketState?.structure?.SPY?.daily || 'N/A'}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* QQQ */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>QQQ</span>
              <Badge className={getBiasColor(marketState?.htf_bias?.QQQ)}>
                {marketState?.htf_bias?.QQQ?.toUpperCase()}
              </Badge>
            </CardTitle>
            <CardDescription>Nasdaq 100 ETF</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">${marketState?.qqq_price?.toFixed(2)}</div>
            <div className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Session:</span>
                <span className="font-medium">{marketState?.session}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Structure (Daily):</span>
                <span className="font-medium">{marketState?.structure?.QQQ?.daily || 'N/A'}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Performance Overview</CardTitle>
          <CardDescription>All-time statistics</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-400">Total Trades</div>
              <div className="text-2xl font-bold">{performance?.total_trades || 0}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Winrate</div>
              <div className="text-2xl font-bold text-green-500">{performance?.winrate?.toFixed(1) || 0}%</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Expectancy</div>
              <div className="text-2xl font-bold">{performance?.expectancy?.toFixed(2) || 0}R</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Profit Factor</div>
              <div className="text-2xl font-bold">{performance?.profit_factor?.toFixed(2) || 0}</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Dashboard;
