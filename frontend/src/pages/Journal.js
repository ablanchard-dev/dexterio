import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { ChevronDown, ChevronUp, Search, Filter } from 'lucide-react';
import axios from 'axios';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Journal = () => {
  const [trades, setTrades] = useState([]);
  const [filteredTrades, setFilteredTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expandedTrade, setExpandedTrade] = useState(null);
  const [filters, setFilters] = useState({
    search: '',
    playbook: 'all',
    quality: 'all',
    outcome: 'all'
  });

  useEffect(() => {
    fetchTrades();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [trades, filters]);

  const fetchTrades = async () => {
    try {
      const response = await axios.get(`${API}/trading/trades/history?limit=100`);
      setTrades(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching trades:', error);
    }
  };

  const applyFilters = () => {
    let filtered = [...trades];

    // Search filter
    if (filters.search) {
      filtered = filtered.filter(trade =>
        trade.symbol.toLowerCase().includes(filters.search.toLowerCase()) ||
        trade.playbook.toLowerCase().includes(filters.search.toLowerCase())
      );
    }

    // Playbook filter
    if (filters.playbook !== 'all') {
      filtered = filtered.filter(trade => trade.playbook === filters.playbook);
    }

    // Quality filter
    if (filters.quality !== 'all') {
      filtered = filtered.filter(trade => trade.setup_quality === filters.quality);
    }

    // Outcome filter
    if (filters.outcome !== 'all') {
      filtered = filtered.filter(trade => trade.outcome === filters.outcome);
    }

    setFilteredTrades(filtered);
  };

  const getOutcomeBadge = (outcome) => {
    if (outcome === 'win') return <Badge className="bg-green-500">WIN</Badge>;
    if (outcome === 'loss') return <Badge className="bg-red-500">LOSS</Badge>;
    return <Badge className="bg-gray-500">BE</Badge>;
  };

  const getQualityColor = (quality) => {
    if (quality === 'A+') return 'text-green-500';
    if (quality === 'A') return 'text-blue-500';
    return 'text-yellow-500';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-lg">Loading trade journal...</div>
      </div>
    );
  }

  // Get unique values for filters
  const playbooks = [...new Set(trades.map(t => t.playbook))];
  const qualities = [...new Set(trades.map(t => t.setup_quality))];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Trade Journal</h1>
        <p className="text-gray-400 mt-1">Complete trading history with filters</p>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Filters
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search symbol or playbook..."
                value={filters.search}
                onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                className="pl-9"
              />
            </div>

            {/* Playbook filter */}
            <Select value={filters.playbook} onValueChange={(v) => setFilters({ ...filters, playbook: v })}>
              <SelectTrigger>
                <SelectValue placeholder="All Playbooks" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Playbooks</SelectItem>
                {playbooks.map(pb => (
                  <SelectItem key={pb} value={pb}>{pb}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Quality filter */}
            <Select value={filters.quality} onValueChange={(v) => setFilters({ ...filters, quality: v })}>
              <SelectTrigger>
                <SelectValue placeholder="All Qualities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Qualities</SelectItem>
                {qualities.map(q => (
                  <SelectItem key={q} value={q}>{q}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Outcome filter */}
            <Select value={filters.outcome} onValueChange={(v) => setFilters({ ...filters, outcome: v })}>
              <SelectTrigger>
                <SelectValue placeholder="All Outcomes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Outcomes</SelectItem>
                <SelectItem value="win">Wins</SelectItem>
                <SelectItem value="loss">Losses</SelectItem>
                <SelectItem value="breakeven">Breakeven</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="mt-4 text-sm text-gray-400">
            Showing {filteredTrades.length} of {trades.length} trades
          </div>
        </CardContent>
      </Card>

      {/* Trades Table */}
      <Card>
        <CardHeader>
          <CardTitle>Trade History</CardTitle>
          <CardDescription>Click on a trade to see details</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {filteredTrades.length === 0 ? (
              <div className="text-center py-8 text-gray-400">
                No trades match your filters
              </div>
            ) : (
              filteredTrades.map((trade) => (
                <div key={trade.id} className="border border-gray-800 rounded-lg">
                  {/* Trade Row */}
                  <div
                    className="p-4 cursor-pointer hover:bg-gray-900 transition-colors"
                    onClick={() => setExpandedTrade(expandedTrade === trade.id ? null : trade.id)}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-16 text-center">
                          {getOutcomeBadge(trade.outcome)}
                        </div>
                        <div>
                          <div className="font-bold">{trade.symbol} {trade.direction}</div>
                          <div className="text-sm text-gray-400">
                            {format(new Date(trade.time_entry), 'MMM dd, yyyy HH:mm')}
                          </div>
                        </div>
                        <Badge variant="outline" className={getQualityColor(trade.setup_quality)}>
                          {trade.setup_quality}
                        </Badge>
                        <div className="text-sm text-gray-400">
                          {trade.playbook}
                        </div>
                      </div>
                      <div className="flex items-center gap-6">
                        <div className="text-right">
                          <div className={`text-lg font-bold ${trade.pnl_dollars >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            ${trade.pnl_dollars.toFixed(2)}
                          </div>
                          <div className="text-sm text-gray-400">
                            {trade.r_multiple >= 0 ? '+' : ''}{trade.r_multiple.toFixed(2)}R
                          </div>
                        </div>
                        {expandedTrade === trade.id ? (
                          <ChevronUp className="h-5 w-5 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-gray-400" />
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Expanded Details */}
                  {expandedTrade === trade.id && (
                    <div className="px-4 pb-4 border-t border-gray-800">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                        <div>
                          <div className="text-xs text-gray-400">Entry Price</div>
                          <div className="font-medium">${trade.entry_price.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Stop Loss</div>
                          <div className="font-medium text-red-400">${trade.stop_loss.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Take Profit</div>
                          <div className="font-medium text-green-400">${trade.take_profit_1.toFixed(2)}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Position Size</div>
                          <div className="font-medium">{trade.position_size}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Risk %</div>
                          <div className="font-medium">{(trade.risk_pct * 100).toFixed(1)}%</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Trade Type</div>
                          <div className="font-medium">{trade.trade_type}</div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Duration</div>
                          <div className="font-medium">
                            {trade.duration_minutes ? `${Math.round(trade.duration_minutes)} min` : 'Open'}
                          </div>
                        </div>
                        <div>
                          <div className="text-xs text-gray-400">Exit Time</div>
                          <div className="font-medium">
                            {trade.time_exit ? format(new Date(trade.time_exit), 'HH:mm') : 'Open'}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default Journal;
