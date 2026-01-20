import React, { useState, useEffect } from 'react';

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

export default function Backtests() {
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [jobLog, setJobLog] = useState('');
  const [loading, setLoading] = useState(false);
  const [recentJobs, setRecentJobs] = useState([]);
  
  // Form state
  const [symbols, setSymbols] = useState(['SPY']);
  const [startDate, setStartDate] = useState('2025-08-01');
  const [endDate, setEndDate] = useState('2025-08-01');
  const [tradingMode, setTradingMode] = useState('AGGRESSIVE');
  const [tradeTypes, setTradeTypes] = useState(['DAILY']);
  const [htfWarmupDays, setHtfWarmupDays] = useState(40);
  const [initialCapital, setInitialCapital] = useState(50000);
  const [commissionModel, setCommissionModel] = useState('ibkr_fixed');

  // Load recent jobs on mount
  useEffect(() => {
    fetchRecentJobs();
    
    // Rafraîchir la liste toutes les 10 secondes
    const interval = setInterval(() => {
      fetchRecentJobs();
    }, 10000);
    
    return () => clearInterval(interval);
  }, []);

  // Poll job status
  useEffect(() => {
    if (!jobId) return;
    
    const interval = setInterval(() => {
      fetchJobStatus();
      fetchJobLog();
    }, 2000);
    
    return () => clearInterval(interval);
  }, [jobId]);

  const fetchRecentJobs = async () => {
    try {
      const res = await fetch(`${API_URL}/api/backtests?limit=10`);
      const data = await res.json();
      setRecentJobs(data.jobs || []);
    } catch (err) {
      console.error('Failed to fetch recent jobs:', err);
    }
  };

  const fetchJobStatus = async () => {
    try {
      const res = await fetch(`${API_URL}/api/backtests/${jobId}`);
      const data = await res.json();
      setJobStatus(data);
      
      if (data.status === 'done' || data.status === 'failed') {
        setLoading(false);
        // Rafraîchir la liste des jobs récents quand un job se termine
        fetchRecentJobs();
      }
    } catch (err) {
      console.error('Failed to fetch job status:', err);
    }
  };

  const fetchJobLog = async () => {
    try {
      const res = await fetch(`${API_URL}/api/backtests/${jobId}/log`);
      const data = await res.json();
      setJobLog(data.log || '');
    } catch (err) {
      console.error('Failed to fetch job log:', err);
    }
  };

  const handleRun = async () => {
    setLoading(true);
    setJobId(null);
    setJobStatus(null);
    setJobLog('');
    
    const request = {
      symbols,
      start_date: startDate,
      end_date: endDate,
      trading_mode: tradingMode,
      trade_types: tradeTypes,
      htf_warmup_days: parseInt(htfWarmupDays),
      initial_capital: parseFloat(initialCapital),
      commission_model: commissionModel,
      enable_reg_fees: true,
      slippage_model: 'pct',
      slippage_cost_pct: 0.0005,
      spread_model: 'fixed_bps',
      spread_bps: 2.0
    };
    
    try {
      const res = await fetch(`${API_URL}/api/backtests/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request)
      });
      
      if (!res.ok) {
        const error = await res.json();
        alert(`Error: ${error.detail}`);
        setLoading(false);
        return;
      }
      
      const data = await res.json();
      setJobId(data.job_id);
    } catch (err) {
      alert(`Failed to start backtest: ${err.message}`);
      setLoading(false);
    }
  };

  const handleToggleTradeType = (type) => {
    if (tradeTypes.includes(type)) {
      setTradeTypes(tradeTypes.filter(t => t !== type));
    } else {
      setTradeTypes([...tradeTypes, type]);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <h1 className="text-3xl font-bold mb-6 text-white">Backtests</h1>
      
      {/* Form */}
      <div className="bg-white shadow rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900">Run Backtest</h2>
        
        <div className="grid grid-cols-2 gap-4">
          {/* Symbols */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Symbols</label>
            <select 
              value={symbols[0]} 
              onChange={(e) => setSymbols([e.target.value])}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="SPY">SPY</option>
              <option value="QQQ">QQQ</option>
            </select>
          </div>
          
          {/* Start Date */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Start Date</label>
            <input 
              type="date" 
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          {/* End Date */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">End Date</label>
            <input 
              type="date" 
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
          
          {/* Trading Mode */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Trading Mode</label>
            <select 
              value={tradingMode}
              onChange={(e) => setTradingMode(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="AGGRESSIVE">AGGRESSIVE</option>
              <option value="SAFE">SAFE</option>
            </select>
          </div>
          
          {/* Trade Types */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Trade Types</label>
            <div className="flex gap-4">
              <label className="flex items-center text-gray-700">
                <input 
                  type="checkbox" 
                  checked={tradeTypes.includes('DAILY')}
                  onChange={() => handleToggleTradeType('DAILY')}
                  className="mr-2"
                />
                DAILY
              </label>
              <label className="flex items-center text-gray-700">
                <input 
                  type="checkbox" 
                  checked={tradeTypes.includes('SCALP')}
                  onChange={() => handleToggleTradeType('SCALP')}
                  className="mr-2"
                />
                SCALP
              </label>
            </div>
          </div>
          
          {/* HTF Warmup Days */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">HTF Warmup (days)</label>
            <input 
              type="number" 
              value={htfWarmupDays}
              onChange={(e) => setHtfWarmupDays(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min="0"
              max="60"
            />
          </div>
          
          {/* Commission Model */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Commission Model</label>
            <select 
              value={commissionModel}
              onChange={(e) => setCommissionModel(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="ibkr_fixed">IBKR Fixed ($0.005/sh)</option>
              <option value="ibkr_tiered">IBKR Tiered ($0.0035/sh)</option>
              <option value="none">None (no costs)</option>
            </select>
          </div>
          
          {/* Initial Capital */}
          <div>
            <label className="block text-sm font-medium mb-1 text-gray-700">Initial Capital ($)</label>
            <input 
              type="number" 
              value={initialCapital}
              onChange={(e) => setInitialCapital(e.target.value)}
              className="w-full border border-gray-300 rounded px-3 py-2 bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              min="1000"
              step="1000"
            />
          </div>
        </div>
        
        <button
          onClick={handleRun}
          disabled={loading || !tradeTypes.length}
          className="mt-6 bg-blue-500 text-white px-6 py-2 rounded hover:bg-blue-600 disabled:bg-gray-400"
        >
          {loading ? 'Running...' : 'Run Backtest'}
        </button>
      </div>
      
      {/* Job Status */}
      {jobId && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4 text-gray-900">Job: {jobId}</h2>
          
          {jobStatus && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">Status:</span>
                <span className={`px-3 py-1 rounded text-sm ${
                  jobStatus.status === 'done' ? 'bg-green-100 text-green-800' :
                  jobStatus.status === 'failed' ? 'bg-red-100 text-red-800' :
                  jobStatus.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
                  'bg-gray-100 text-gray-800'
                }`}>
                  {jobStatus.status}
                </span>
              </div>
              
              {jobStatus.error && (
                <div className="bg-red-50 border border-red-200 rounded p-3 text-red-800">
                  <strong>Error:</strong> {jobStatus.error}
                </div>
              )}
              
              {jobStatus.metrics && (
                <div className="bg-blue-50 border border-blue-200 rounded p-4 mt-4">
                  <h3 className="font-semibold mb-2 text-gray-900">Results</h3>
                  <div className="grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <div className="text-gray-600">Trades</div>
                      <div className="font-bold text-gray-900">{jobStatus.metrics.total_trades || 0}</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Total R Net</div>
                      <div className="font-bold text-gray-900">{(jobStatus.metrics.total_R_net || 0).toFixed(3)}R</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Total R Gross</div>
                      <div className="font-bold text-gray-500">{(jobStatus.metrics.total_R_gross || 0).toFixed(3)}R</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Total Costs</div>
                      <div className="font-bold text-red-600">${(jobStatus.metrics.total_costs_dollars || 0).toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Win Rate</div>
                      <div className="font-bold text-gray-900">{(jobStatus.metrics.winrate || 0).toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Profit Factor</div>
                      <div className="font-bold text-gray-900">{(jobStatus.metrics.profit_factor || 0).toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Expectancy</div>
                      <div className="font-bold text-gray-900">{(jobStatus.metrics.expectancy_r || 0).toFixed(3)}R</div>
                    </div>
                    <div>
                      <div className="text-gray-600">Max DD</div>
                      <div className="font-bold text-red-600">{(jobStatus.metrics.max_drawdown_r || 0).toFixed(2)}R</div>
                    </div>
                  </div>
                  
                  {jobStatus.artifact_paths && (
                    <div className="mt-4">
                      <h4 className="font-medium mb-2">Downloads</h4>
                      <div className="flex gap-2">
                        {Object.entries(jobStatus.artifact_paths).map(([name, filename]) => (
                          <a
                            key={name}
                            href={`${API_URL}/api/backtests/${jobId}/download?file=${filename}`}
                            download
                            className="text-blue-500 hover:underline text-sm"
                          >
                            {name}
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
          
          {/* Log */}
          {jobLog && (
            <div className="mt-4">
              <h3 className="font-medium text-gray-900 mb-2">Job Log</h3>
              <pre className="bg-gray-50 p-3 rounded text-xs overflow-auto max-h-64 text-gray-800 whitespace-pre-wrap">
                {jobLog}
              </pre>
            </div>
          )}
        </div>
      )}
      
      {/* Recent Jobs */}
      <div className="bg-white shadow rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4 text-gray-900">Recent Jobs</h2>
        
        {recentJobs.length === 0 ? (
          <p className="text-gray-500">No jobs yet</p>
        ) : (
          <div className="space-y-2">
            {recentJobs.map((job) => (
              <div
                key={job.job_id}
                onClick={() => setJobId(job.job_id)}
                className="border rounded p-3 hover:bg-gray-50 cursor-pointer"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-mono text-sm font-medium">{job.job_id}</span>
                    <span className={`ml-2 px-2 py-0.5 rounded text-xs ${
                      job.status === 'done' ? 'bg-green-100 text-green-800' :
                      job.status === 'failed' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="text-xs text-gray-500">
                    {new Date(job.created_at).toLocaleString()}
                  </div>
                </div>
                {job.config && (
                  <div className="text-sm text-gray-600 mt-1">
                    {job.config.symbols.join(', ')} · {job.config.start_date} → {job.config.end_date} · {job.config.trading_mode}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
