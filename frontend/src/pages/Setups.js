import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, Target, CheckCircle, AlertCircle } from 'lucide-react';
import axios from 'axios';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Setups = () => {
  const [setups, setSetups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(null);

  useEffect(() => {
    fetchSetups();
    const interval = setInterval(fetchSetups, 10000); // Update every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchSetups = async () => {
    try {
      const response = await axios.get(`${API}/trading/setups`);
      setSetups(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching setups:', error);
    }
  };

  const executeManualTrade = async (setupId) => {
    try {
      setExecuting(setupId);
      await axios.post(`${API}/trading/execute-manual`, {
        setup_id: setupId,
        override: false
      });
      alert('Trade executed successfully!');
      fetchSetups();
    } catch (error) {
      alert(`Failed to execute trade: ${error.response?.data?.detail || error.message}`);
    } finally {
      setExecuting(null);
    }
  };

  const getQualityColor = (quality) => {
    if (quality === 'A+') return 'bg-green-500';
    if (quality === 'A') return 'bg-blue-500';
    return 'bg-yellow-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading setups...</div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Setups Detected</h1>
          <p className="text-gray-400 mt-1">High-quality trading opportunities</p>
        </div>
        <Badge variant="outline" className="text-lg px-4 py-2">
          {setups.length} Active Setup{setups.length !== 1 ? 's' : ''}
        </Badge>
      </div>

      {/* Setups List */}
      {setups.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Target className="h-12 w-12 text-gray-600 mb-4" />
            <p className="text-gray-400 text-lg">No setups detected at the moment</p>
            <p className="text-gray-500 text-sm mt-2">Waiting for A+ and A quality opportunities</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {setups.map((setup) => (
            <Card key={setup.id} className="border-2 hover:border-gray-700 transition-colors">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <span>{setup.symbol}</span>
                      {setup.direction === 'LONG' ? (
                        <TrendingUp className="h-5 w-5 text-green-500" />
                      ) : (
                        <TrendingDown className="h-5 w-5 text-red-500" />
                      )}
                      <Badge className={getQualityColor(setup.quality)}>
                        {setup.quality}
                      </Badge>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {setup.trade_type} • Score: {(setup.final_score * 100).toFixed(0)}%
                    </CardDescription>
                  </div>
                  <Button
                    onClick={() => executeManualTrade(setup.id)}
                    disabled={executing === setup.id}
                    size="sm"
                    className="bg-blue-600 hover:bg-blue-700"
                  >
                    {executing === setup.id ? 'Executing...' : 'Execute'}
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Price Levels */}
                <div className="grid grid-cols-2 gap-4 p-3 bg-gray-900 rounded-lg">
                  <div>
                    <div className="text-xs text-gray-400">Entry</div>
                    <div className="text-lg font-bold">${setup.entry_price.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">Stop Loss</div>
                    <div className="text-lg font-bold text-red-400">${setup.stop_loss.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">TP1</div>
                    <div className="text-lg font-bold text-green-400">${setup.take_profit_1.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-400">R:R</div>
                    <div className="text-lg font-bold">{setup.risk_reward.toFixed(1)}:1</div>
                  </div>
                </div>

                {/* Confluences */}
                <div>
                  <div className="text-sm font-medium mb-2">Confluences ({setup.confluences_count})</div>
                  <div className="flex flex-wrap gap-2">
                    {setup.confluences_count > 0 ? (
                      <>
                        <Badge variant="outline" className="text-xs">
                          <CheckCircle className="h-3 w-3 mr-1" />
                          {setup.confluences_count} signals
                        </Badge>
                      </>
                    ) : (
                      <span className="text-xs text-gray-500">No specific confluences</span>
                    )}
                  </div>
                </div>

                {/* Playbooks */}
                {setup.playbook_matches.length > 0 && (
                  <div>
                    <div className="text-sm font-medium mb-2">Playbooks</div>
                    <div className="flex flex-wrap gap-2">
                      {setup.playbook_matches.map((playbook, idx) => (
                        <Badge key={idx} variant="secondary" className="text-xs">
                          {playbook}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Context */}
                <div className="text-xs text-gray-400 pt-2 border-t border-gray-800">
                  <div className="flex justify-between">
                    <span>Bias: {setup.market_bias}</span>
                    <span>Session: {setup.session}</span>
                    <span>{format(new Date(setup.timestamp), 'HH:mm:ss')}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default Setups;
