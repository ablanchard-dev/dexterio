import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Layers, Target } from 'lucide-react';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const MarketAnalysis = () => {
  const [marketState, setMarketState] = useState(null);
  const [liquidityLevels, setLiquidityLevels] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMarketData();
    const interval = setInterval(fetchMarketData, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchMarketData = async () => {
    try {
      const [marketRes, liquidityRes] = await Promise.all([
        axios.get(`${API}/trading/market-state`),
        axios.get(`${API}/trading/liquidity-levels`)
      ]);

      setMarketState(marketRes.data);
      setLiquidityLevels(liquidityRes.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching market data:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading market analysis...</div>
      </div>
    );
  }

  const getBiasIcon = (bias) => {
    if (bias === 'bullish') return <TrendingUp className="h-5 w-5 text-green-500" />;
    if (bias === 'bearish') return <TrendingDown className="h-5 w-5 text-red-500" />;
    return <Target className="h-5 w-5 text-gray-500" />;
  };

  const getBiasColor = (bias) => {
    if (bias === 'bullish') return 'bg-green-500';
    if (bias === 'bearish') return 'bg-red-500';
    return 'bg-gray-500';
  };

  const spyLevels = liquidityLevels.filter(l => l.symbol === 'SPY').sort((a, b) => b.price - a.price);
  const qqqLevels = liquidityLevels.filter(l => l.symbol === 'QQQ').sort((a, b) => b.price - a.price);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Market Analysis</h1>
        <p className="text-gray-400 mt-1">Technical structure and key levels</p>
      </div>

      {/* HTF Bias Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* SPY Bias */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                {getBiasIcon(marketState.htf_bias.SPY)}
                SPY - HTF Bias
              </span>
              <Badge className={getBiasColor(marketState.htf_bias.SPY)}>
                {marketState.htf_bias.SPY?.toUpperCase()}
              </Badge>
            </CardTitle>
            <CardDescription>Higher Timeframe Structure</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center pb-2 border-b border-gray-800">
                <span className="text-sm text-gray-400">Current Price</span>
                <span className="text-lg font-bold">${marketState.spy_price.toFixed(2)}</span>
              </div>
              <div>
                <div className="text-xs font-medium text-gray-400 mb-2">Structure</div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Daily:</span>
                    <span className="font-medium">{marketState.structure.SPY.daily || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">H4:</span>
                    <span className="font-medium">{marketState.structure.SPY.h4 || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">H1:</span>
                    <span className="font-medium">{marketState.structure.SPY.h1 || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* QQQ Bias */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                {getBiasIcon(marketState.htf_bias.QQQ)}
                QQQ - HTF Bias
              </span>
              <Badge className={getBiasColor(marketState.htf_bias.QQQ)}>
                {marketState.htf_bias.QQQ?.toUpperCase()}
              </Badge>
            </CardTitle>
            <CardDescription>Higher Timeframe Structure</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex justify-between items-center pb-2 border-b border-gray-800">
                <span className="text-sm text-gray-400">Current Price</span>
                <span className="text-lg font-bold">${marketState.qqq_price.toFixed(2)}</span>
              </div>
              <div>
                <div className="text-xs font-medium text-gray-400 mb-2">Structure</div>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Daily:</span>
                    <span className="font-medium">{marketState.structure.QQQ.daily || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">H4:</span>
                    <span className="font-medium">{marketState.structure.QQQ.h4 || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">H1:</span>
                    <span className="font-medium">{marketState.structure.QQQ.h1 || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Session Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Layers className="h-5 w-5" />
            Session Information
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-sm text-gray-400">Current Session</div>
              <div className="text-lg font-bold">{marketState.session}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">Kill Zone</div>
              <div className="text-lg font-bold">
                {marketState.kill_zone_active ? (
                  <Badge className="bg-red-500">ACTIVE</Badge>
                ) : (
                  <Badge variant="outline">Inactive</Badge>
                )}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-400">SPY Session Profile</div>
              <div className="text-lg font-bold">{marketState.session_profile.SPY}</div>
            </div>
            <div>
              <div className="text-sm text-gray-400">QQQ Session Profile</div>
              <div className="text-lg font-bold">{marketState.session_profile.QQQ}</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Liquidity Levels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* SPY Levels */}
        <Card>
          <CardHeader>
            <CardTitle>SPY - Liquidity Levels</CardTitle>
            <CardDescription>Key price levels and sweeps</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {spyLevels.length === 0 ? (
                <div className="text-center py-4 text-gray-400">No levels detected</div>
              ) : (
                spyLevels.map((level, idx) => (
                  <div
                    key={idx}
                    className={`flex justify-between items-center p-2 rounded ${
                      level.swept ? 'bg-red-900/20 border border-red-500' : 'bg-gray-900'
                    }`}
                  >
                    <div>
                      <div className="font-medium">${level.price.toFixed(2)}</div>
                      <div className="text-xs text-gray-400">{level.level_type}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Imp: {level.importance}
                      </Badge>
                      {level.swept && (
                        <Badge className="bg-red-500 text-xs">SWEPT</Badge>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* QQQ Levels */}
        <Card>
          <CardHeader>
            <CardTitle>QQQ - Liquidity Levels</CardTitle>
            <CardDescription>Key price levels and sweeps</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {qqqLevels.length === 0 ? (
                <div className="text-center py-4 text-gray-400">No levels detected</div>
              ) : (
                qqqLevels.map((level, idx) => (
                  <div
                    key={idx}
                    className={`flex justify-between items-center p-2 rounded ${
                      level.swept ? 'bg-red-900/20 border border-red-500' : 'bg-gray-900'
                    }`}
                  >
                    <div>
                      <div className="font-medium">${level.price.toFixed(2)}</div>
                      <div className="text-xs text-gray-400">{level.level_type}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        Imp: {level.importance}
                      </Badge>
                      {level.swept && (
                        <Badge className="bg-red-500 text-xs">SWEPT</Badge>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MarketAnalysis;
