import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Shield, AlertTriangle, CheckCircle, TrendingUp, TrendingDown } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const RiskManagement = () => {
  const [riskState, setRiskState] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRiskState();
    const interval = setInterval(fetchRiskState, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchRiskState = async () => {
    try {
      const response = await axios.get(`${API}/trading/risk-state`);
      setRiskState(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching risk state:', error);
    }
  };

  const handleCloseAll = async () => {
    if (!window.confirm('Are you sure you want to close all open positions?')) return;

    try {
      await axios.post(`${API}/trading/control`, { action: 'close_all' });
      alert('All positions closed successfully');
      fetchRiskState();
    } catch (error) {
      alert(`Failed to close positions: ${error.response?.data?.detail || error.message}`);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading risk management...</div>
      </div>
    );
  }

  const riskPercentage = (riskState.current_risk_pct * 100).toFixed(1);
  const isReducedRisk = riskState.current_risk_pct === 0.01;
  const maxTradesPerDay = riskState.trading_mode === 'SAFE' ? 4 : 5;
  const tradeProgress = (riskState.daily_trade_count / maxTradesPerDay) * 100;

  // Calculate drawdown
  const drawdown = ((riskState.peak_balance - riskState.account_balance) / riskState.peak_balance) * 100;

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Risk Management</h1>
          <p className="text-gray-400 mt-1">Monitor and control trading risk</p>
        </div>
        <div className="flex gap-2">
          <Badge variant="outline" className="text-lg px-4 py-2">
            {riskState.trading_mode}
          </Badge>
          {riskState.open_positions_count > 0 && (
            <Button onClick={handleCloseAll} variant="destructive" size="sm">
              Close All Positions
            </Button>
          )}
        </div>
      </div>

      {/* Trading Status */}
      <Card className={`border-2 ${
        !riskState.trading_allowed ? 'border-red-500 bg-red-900/10' :
        riskState.daily_trade_count >= maxTradesPerDay * 0.75 ? 'border-yellow-500 bg-yellow-900/10' :
        'border-green-500 bg-green-900/10'
      }`}>
        <CardContent className="flex items-center gap-4 py-6">
          {!riskState.trading_allowed ? (
            <>
              <AlertTriangle className="h-8 w-8 text-red-500" />
              <div className="flex-1">
                <div className="font-bold text-lg text-red-400">TRADING FROZEN</div>
                <div className="text-sm text-red-300">{riskState.freeze_reason}</div>
              </div>
            </>
          ) : (
            <>
              <CheckCircle className="h-8 w-8 text-green-500" />
              <div className="flex-1">
                <div className="font-bold text-lg text-green-400">TRADING ACTIVE</div>
                <div className="text-sm text-green-300">All systems operational</div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Risk Rule: 2% → 1% → 2% */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Dynamic Risk Rule (2% → 1% → 2%)
          </CardTitle>
          <CardDescription>Risk adjusts automatically based on last trade outcome</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Current Risk */}
            <div className="flex items-center justify-between p-4 bg-gray-900 rounded-lg">
              <div>
                <div className="text-sm text-gray-400">Current Risk per Trade</div>
                <div className="text-3xl font-bold flex items-center gap-2">
                  {riskPercentage}%
                  {isReducedRisk ? (
                    <TrendingDown className="h-6 w-6 text-yellow-500" />
                  ) : (
                    <TrendingUp className="h-6 w-6 text-green-500" />
                  )}
                </div>
              </div>
              <Badge className={isReducedRisk ? 'bg-yellow-500' : 'bg-green-500'}>
                {isReducedRisk ? 'REDUCED (After Loss)' : 'BASE RISK'}
              </Badge>
            </div>

            {/* Rule Explanation */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-sm">
              <div className="p-3 border border-gray-800 rounded">
                <div className="font-medium text-green-500 mb-1">Base State (2%)</div>
                <div className="text-gray-400">Standard risk per trade when performing well</div>
              </div>
              <div className="p-3 border border-gray-800 rounded">
                <div className="font-medium text-yellow-500 mb-1">After Loss (1%)</div>
                <div className="text-gray-400">Risk reduced by half to preserve capital</div>
              </div>
              <div className="p-3 border border-gray-800 rounded">
                <div className="font-medium text-blue-500 mb-1">After Win (2%)</div>
                <div className="text-gray-400">Risk restored to base level</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Daily Limits */}
      <Card>
        <CardHeader>
          <CardTitle>Daily Trading Limits</CardTitle>
          <CardDescription>Track usage against maximum thresholds</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Trades Count */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Trades Today</span>
              <span className="font-medium">{riskState.daily_trade_count} / {maxTradesPerDay}</span>
            </div>
            <Progress value={tradeProgress} className="h-2" />
            {tradeProgress >= 75 && (
              <div className="text-xs text-yellow-500 mt-1">⚠ Approaching daily limit</div>
            )}
          </div>

          {/* Daily P&L (R) */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Daily P&L (R)</span>
              <span className={`font-medium ${
                riskState.daily_pnl_r >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                {riskState.daily_pnl_r >= 0 ? '+' : ''}{riskState.daily_pnl_r.toFixed(2)}R
              </span>
            </div>
            <div className="text-xs text-gray-400">
              Max loss: {riskState.trading_mode === 'SAFE' ? '-3.0R' : '-4.0R'}
            </div>
          </div>

          {/* Daily P&L ($) */}
          <div>
            <div className="flex justify-between text-sm mb-2">
              <span className="text-gray-400">Daily P&L ($)</span>
              <span className={`font-medium ${
                riskState.daily_pnl_dollars >= 0 ? 'text-green-500' : 'text-red-500'
              }`}>
                ${riskState.daily_pnl_dollars.toFixed(2)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Account Status */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Balance */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Account Balance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              ${riskState.account_balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              Peak: ${riskState.peak_balance.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        {/* Drawdown */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Current Drawdown</CardTitle>
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${
              drawdown >= 8 ? 'text-red-500' : drawdown >= 5 ? 'text-yellow-500' : 'text-green-500'
            }`}>
              {drawdown.toFixed(2)}%
            </div>
            <div className="text-xs text-gray-400 mt-1">
              Max allowed: 10%
            </div>
          </CardContent>
        </Card>

        {/* Open Positions */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400">Open Positions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {riskState.open_positions_count}
            </div>
            <div className="text-xs text-gray-400 mt-1">
              Active trades
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Risk Configuration</CardTitle>
          <CardDescription>Current risk management settings</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-gray-400">Trading Mode</div>
              <div className="font-bold">{riskState.trading_mode}</div>
            </div>
            <div>
              <div className="text-gray-400">Base Risk</div>
              <div className="font-bold">2.0%</div>
            </div>
            <div>
              <div className="text-gray-400">Reduced Risk</div>
              <div className="font-bold">1.0%</div>
            </div>
            <div>
              <div className="text-gray-400">Max Daily Loss</div>
              <div className="font-bold">3.0%</div>
            </div>
            <div>
              <div className="text-gray-400">Max Drawdown</div>
              <div className="font-bold">10.0%</div>
            </div>
            <div>
              <div className="text-gray-400">Max Consecutive Losses</div>
              <div className="font-bold">3</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default RiskManagement;
