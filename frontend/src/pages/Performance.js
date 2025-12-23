import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, Award, Target, Activity } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Performance = () => {
  const [performance, setPerformance] = useState(null);
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPerformanceData();
  }, []);

  const fetchPerformanceData = async () => {
    try {
      const [perfRes, tradesRes] = await Promise.all([
        axios.get(`${API}/trading/performance`),
        axios.get(`${API}/trading/trades/history?limit=100`)
      ]);

      setPerformance(perfRes.data);
      setTrades(tradesRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching performance data:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading performance data...</div>
      </div>
    );
  }

  // Prepare equity curve data
  const equityCurveData = trades.map((trade, idx) => {
    const cumulativeR = trades.slice(0, idx + 1).reduce((sum, t) => sum + t.r_multiple, 0);
    return {
      index: idx + 1,
      r: parseFloat(cumulativeR.toFixed(2)),
      trade: `${trade.symbol} ${trade.direction}`
    };
  });

  // Prepare playbook data
  const playbookData = Object.entries(performance.by_playbook || {}).map(([name, stats]) => ({
    name,
    winrate: stats.winrate,
    trades: stats.trades,
    avgR: stats.avg_r
  }));

  // Prepare quality data
  const qualityData = Object.entries(performance.by_quality || {}).map(([name, stats]) => ({
    name,
    winrate: stats.winrate,
    trades: stats.trades,
    avgR: stats.avg_r
  }));

  // Win/Loss pie data
  const winLossData = [
    { name: 'Wins', value: performance.wins, color: '#10b981' },
    { name: 'Losses', value: performance.losses, color: '#ef4444' }
  ];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Performance Dashboard</h1>
        <p className="text-gray-400 mt-1">Comprehensive trading statistics</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Award className="h-4 w-4" />
              Winrate
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-500">{performance.winrate.toFixed(1)}%</div>
            <p className="text-xs text-gray-400 mt-1">{performance.wins}W / {performance.losses}L</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Target className="h-4 w-4" />
              Expectancy
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{performance.expectancy.toFixed(3)}R</div>
            <p className="text-xs text-gray-400 mt-1">Per trade average</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <TrendingUp className="h-4 w-4" />
              Profit Factor
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{performance.profit_factor.toFixed(2)}</div>
            <p className="text-xs text-gray-400 mt-1">Gross profit / loss</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-gray-400 flex items-center gap-2">
              <Activity className="h-4 w-4" />
              Max Drawdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-red-400">{performance.max_drawdown_r.toFixed(2)}R</div>
            <p className="text-xs text-gray-400 mt-1">Worst streak</p>
          </CardContent>
        </Card>
      </div>

      {/* Equity Curve */}
      <Card>
        <CardHeader>
          <CardTitle>Equity Curve</CardTitle>
          <CardDescription>Cumulative R over time</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={equityCurveData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="index" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                labelStyle={{ color: '#9ca3af' }}
              />
              <Line type="monotone" dataKey="r" stroke="#3b82f6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Win/Loss Distribution */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Win/Loss Distribution</CardTitle>
            <CardDescription>Total: {performance.total_trades} trades</CardDescription>
          </CardHeader>
          <CardContent className="flex justify-center">
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={winLossData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.name}: ${entry.value}`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {winLossData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>R Statistics</CardTitle>
            <CardDescription>Average performance breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Avg Win</span>
                  <span className="text-green-500 font-bold">+{performance.avg_win_r.toFixed(2)}R</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-green-500 h-2 rounded-full"
                    style={{ width: `${Math.min((performance.avg_win_r / 3) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Avg Loss</span>
                  <span className="text-red-500 font-bold">{performance.avg_loss_r.toFixed(2)}R</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div
                    className="bg-red-500 h-2 rounded-full"
                    style={{ width: `${Math.min((Math.abs(performance.avg_loss_r) / 3) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">Avg R</span>
                  <span className={`font-bold ${performance.avg_r >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {performance.avg_r >= 0 ? '+' : ''}{performance.avg_r.toFixed(2)}R
                  </span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <div
                    className={performance.avg_r >= 0 ? 'bg-green-500' : 'bg-red-500'}
                    style={{ width: `${Math.min((Math.abs(performance.avg_r) / 2) * 100, 100)}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Playbook Performance */}
      {playbookData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Performance by Playbook</CardTitle>
            <CardDescription>Compare playbook effectiveness</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={playbookData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Legend />
                <Bar dataKey="winrate" fill="#10b981" name="Winrate (%)" />
                <Bar dataKey="avgR" fill="#3b82f6" name="Avg R" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Quality Performance */}
      {qualityData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Performance by Setup Quality</CardTitle>
            <CardDescription>A+ vs A vs B comparison</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={qualityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" />
                <YAxis stroke="#9ca3af" />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151' }}
                  labelStyle={{ color: '#9ca3af' }}
                />
                <Legend />
                <Bar dataKey="winrate" fill="#10b981" name="Winrate (%)" />
                <Bar dataKey="trades" fill="#f59e0b" name="Trades" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default Performance;
