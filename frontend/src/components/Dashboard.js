import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Slider } from './ui/slider';
import { toast } from 'sonner';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { TrendingUp, DollarSign, Calendar, Award, AlertCircle, Download, Save, History, Building2 } from 'lucide-react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const Dashboard = () => {
  const [sectors, setSectors] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [selectedSector, setSelectedSector] = useState('');
  const [selectedCompany, setSelectedCompany] = useState('');
  const [investmentUSD, setInvestmentUSD] = useState(1000000);
  const [exitYear, setExitYear] = useState([5]);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [analysisHistory, setAnalysisHistory] = useState([]);
  const [apiStatus, setApiStatus] = useState('checking');

  useEffect(() => {
    fetchSectors();
    checkApiHealth();
  }, []);

  useEffect(() => {
    if (selectedSector) {
      fetchCompanies(selectedSector);
    }
  }, [selectedSector]);

  const checkApiHealth = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/health`);
      setApiStatus('connected');
      console.log('API health check passed:', response.data);
    } catch (error) {
      setApiStatus('disconnected');
      console.error('API health check failed:', error.message);
    }
  };

  const fetchSectors = async () => {
    try {
      console.log('Fetching sectors from:', `${API}/sectors`);
      const response = await axios.get(`${API}/sectors`);
      console.log('Sectors response:', response.data);
      setSectors(response.data.sectors);
      if (response.data.sectors.length > 0) {
        toast.success(`Loaded ${response.data.sectors.length} sectors`);
      }
    } catch (error) {
      console.error('Error fetching sectors:', error);
      console.error('Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status
      });
      toast.error(`Failed to load sectors: ${error.message}`);
    }
  };

  const fetchCompanies = async (sector) => {
    try {
      const response = await axios.get(`${API}/companies?sector=${sector}`);
      setCompanies(response.data);
      setSelectedCompany('');
    } catch (error) {
      toast.error('Failed to load companies');
    }
  };

  const calculateAnalysis = async () => {
    if (!selectedCompany) {
      toast.error('Please select a company');
      return;
    }

    setIsCalculating(true);
    try {
      const response = await axios.post(
        `${API}/analysis/calculate`,
        {
          investment_usd: investmentUSD,
          exit_year: exitYear[0],
          company_id: selectedCompany
        }
      );
      setAnalysisResult(response.data);
      toast.success('Analysis complete!');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Analysis failed');
    } finally {
      setIsCalculating(false);
    }
  };

  const saveAnalysis = async () => {
    if (!analysisResult) return;

    try {
      await axios.post(
        `${API}/analysis/save`,
        { analysis: analysisResult }
      );
      toast.success('Analysis saved!');
    } catch (error) {
      toast.error('Failed to save analysis');
    }
  };

  const fetchHistory = async () => {
    try {
      const response = await axios.get(`${API}/analysis/history`);
      setAnalysisHistory(response.data.analyses);
      setShowHistory(true);
    } catch (error) {
      toast.error('Failed to load history');
    }
  };

  const exportToPDF = async () => {
    const element = document.getElementById('analysis-results');
    if (!element) return;

    try {
      const canvas = await html2canvas(element, {
        scale: 2,
        backgroundColor: '#020617'
      });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
      
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`analysis_${analysisResult.company.name}.pdf`);
      toast.success('PDF exported successfully!');
    } catch (error) {
      toast.error('Failed to export PDF');
    }
  };

  const exportToExcel = async () => {
    if (!analysisResult) return;

    try {
      const response = await axios.get(
        `${API}/analysis/${analysisResult.id}/export-excel`,
        {
          responseType: 'blob'
        }
      );
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `analysis_${analysisResult.company.name}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      toast.success('Excel exported successfully!');
    } catch (error) {
      toast.error('Failed to export Excel');
    }
  };

  const chartData = analysisResult?.yearly_dividends.map((item) => ({
    year: `Year ${item.year}`,
    dividend: parseFloat(item.dividend.toFixed(2)),
    discounted: parseFloat(item.discounted_value.toFixed(2))
  })) || [];

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900 border border-slate-700 p-3 rounded-lg shadow-xl">
          <p className="text-white font-semibold mb-1">{payload[0].payload.year}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: SAR {entry.value.toLocaleString()}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (showHistory) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-[#020617] to-[#0f172a] p-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-3xl font-bold text-white">Analysis History</h1>
            <Button
              onClick={() => setShowHistory(false)}
              data-testid="back-to-dashboard-button"
              variant="outline"
              className="border-amber-400 text-amber-400 hover:bg-amber-400/10"
            >
              Back to Dashboard
            </Button>
          </div>

          <div className="grid gap-4">
            {analysisHistory.map((analysis) => (
              <Card key={analysis.id} className="glass-card border-white/10" data-testid="history-item">
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div>
                      <CardTitle className="text-white">{analysis.company.name}</CardTitle>
                      <CardDescription className="text-slate-400">
                        {new Date(analysis.created_at).toLocaleDateString()}
                      </CardDescription>
                    </div>
                    <span className="px-3 py-1 bg-amber-400/20 text-amber-400 rounded-full text-sm font-semibold">
                      {analysis.cap_classification}
                    </span>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <p className="text-slate-400 text-sm">Investment</p>
                      <p className="text-white font-mono text-lg">
                        ${analysis.investment_usd.toLocaleString()}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400 text-sm">NPV</p>
                      <p className="text-emerald-400 font-mono text-lg">
                        SAR {analysis.npv.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400 text-sm">IRR</p>
                      <p className="text-amber-400 font-mono text-lg">
                        {(analysis.irr * 100).toFixed(2)}%
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-400 text-sm">Exit Year</p>
                      <p className="text-white font-mono text-lg">{analysis.exit_year}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#020617] to-[#0f172a] p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-4">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 gold-glow">
              <Building2 className="w-8 h-8 text-slate-950" />
            </div>
            <div>
              <h1 className="text-4xl font-bold gradient-text mb-1">Saudi Equity Nexus</h1>
              <p className="text-slate-400">Professional Investment Analysis Platform</p>
              <p className="text-xs text-slate-500 mt-1">
                API: {BACKEND_URL} 
                <span className={`ml-2 ${apiStatus === 'connected' ? 'text-emerald-400' : apiStatus === 'disconnected' ? 'text-red-400' : 'text-amber-400'}`}>
                  {apiStatus === 'connected' ? '● Connected' : apiStatus === 'disconnected' ? '● Disconnected' : '● Checking...'}
                </span>
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            {apiStatus === 'disconnected' && (
              <Button
                onClick={() => { checkApiHealth(); fetchSectors(); }}
                variant="outline"
                className="border-red-400 text-red-400 hover:bg-red-400/10"
                data-testid="retry-button"
              >
                Retry Connection
              </Button>
            )}
            <Button
              onClick={fetchHistory}
              data-testid="history-button"
              variant="outline"
              className="border-amber-400 text-amber-400 hover:bg-amber-400/10"
            >
              <History className="w-4 h-4 mr-2" />
              History
            </Button>
          </div>
        </div>

        {/* Input Section */}
        <Card className="glass-card border-white/10 mb-6" data-testid="input-section">
          <CardHeader>
            <CardTitle className="text-2xl text-white">Investment Parameters</CardTitle>
            <CardDescription className="text-slate-400">Configure your investment analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="space-y-2">
                <Label className="text-slate-300">Investment Amount (USD)</Label>
                <Input
                  type="number"
                  data-testid="investment-input"
                  value={investmentUSD}
                  onChange={(e) => setInvestmentUSD(Number(e.target.value))}
                  className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Sector</Label>
                <Select value={selectedSector} onValueChange={setSelectedSector}>
                  <SelectTrigger data-testid="sector-select" className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white">
                    <SelectValue placeholder="Select sector" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700">
                    {sectors.map((sector) => (
                      <SelectItem key={sector} value={sector} className="text-white hover:bg-slate-800">
                        {sector}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Company</Label>
                <Select value={selectedCompany} onValueChange={setSelectedCompany} disabled={!selectedSector}>
                  <SelectTrigger data-testid="company-select" className="bg-slate-900/50 border-slate-700 focus:border-amber-400 focus:ring-amber-400/20 text-white">
                    <SelectValue placeholder="Select company" />
                  </SelectTrigger>
                  <SelectContent className="bg-slate-900 border-slate-700">
                    {companies.map((company) => (
                      <SelectItem key={company.id} value={company.id} className="text-white hover:bg-slate-800">
                        {company.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-slate-300">Exit Year: {exitYear[0]}</Label>
                <Slider
                  data-testid="exit-year-slider"
                  value={exitYear}
                  onValueChange={setExitYear}
                  min={1}
                  max={10}
                  step={1}
                  className="mt-2"
                />
              </div>
            </div>

            <Button
              onClick={calculateAnalysis}
              data-testid="calculate-button"
              className="w-full mt-6 bg-gradient-to-r from-amber-400 to-amber-600 hover:from-amber-500 hover:to-amber-700 text-slate-950 font-bold py-6 text-lg"
              disabled={isCalculating}
            >
              {isCalculating ? 'Calculating...' : 'Calculate Investment Analysis'}
            </Button>
          </CardContent>
        </Card>

        {/* Results Section */}
        {analysisResult && (
          <div id="analysis-results" data-testid="analysis-results" className="space-y-6">
            {/* Action Buttons */}
            <div className="flex justify-end gap-3">
              <Button
                onClick={saveAnalysis}
                data-testid="save-analysis-button"
                variant="outline"
                className="border-emerald-400 text-emerald-400 hover:bg-emerald-400/10"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Analysis
              </Button>
              <Button
                onClick={exportToPDF}
                data-testid="export-pdf-button"
                variant="outline"
                className="border-amber-400 text-amber-400 hover:bg-amber-400/10"
              >
                <Download className="w-4 h-4 mr-2" />
                Export PDF
              </Button>
              <Button
                onClick={exportToExcel}
                data-testid="export-excel-button"
                variant="outline"
                className="border-amber-400 text-amber-400 hover:bg-amber-400/10"
              >
                <Download className="w-4 h-4 mr-2" />
                Export Excel
              </Button>
            </div>

            {/* Key Metrics Grid */}
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card className="glass-card border-white/10 gold-glow" data-testid="npv-card">
                <CardHeader className="pb-3">
                  <CardDescription className="text-slate-400 flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    Net Present Value
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold metric-value text-emerald-400">
                    SAR {analysisResult.npv.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </CardContent>
              </Card>

              <Card className="glass-card border-white/10" data-testid="irr-card">
                <CardHeader className="pb-3">
                  <CardDescription className="text-slate-400 flex items-center">
                    <DollarSign className="w-4 h-4 mr-2" />
                    Internal Rate of Return
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold metric-value text-amber-400">
                    {(analysisResult.irr * 100).toFixed(2)}%
                  </p>
                </CardContent>
              </Card>

              <Card className="glass-card border-white/10" data-testid="terminal-value-card">
                <CardHeader className="pb-3">
                  <CardDescription className="text-slate-400 flex items-center">
                    <Calendar className="w-4 h-4 mr-2" />
                    Terminal Value
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold metric-value text-cyan-400">
                    SAR {analysisResult.terminal_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                </CardContent>
              </Card>

              <Card className="glass-card border-white/10" data-testid="after-tax-return-card">
                <CardHeader className="pb-3">
                  <CardDescription className="text-slate-400 flex items-center">
                    <Award className="w-4 h-4 mr-2" />
                    After-Tax Return
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-3xl font-bold metric-value text-purple-400">
                    {analysisResult.after_tax_return.toFixed(2)}%
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Company Info & Risk */}
            <div className="grid md:grid-cols-3 gap-6">
              <Card className="glass-card border-white/10" data-testid="company-info-card">
                <CardHeader>
                  <CardTitle className="text-white">{analysisResult.company.name}</CardTitle>
                  <CardDescription className="text-slate-400">{analysisResult.company.sector}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Investment (SAR):</span>
                      <span className="text-white font-mono">{analysisResult.investment_sar.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Required Return:</span>
                      <span className="text-white font-mono">{(analysisResult.required_return * 100).toFixed(2)}%</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-card border-white/10" data-testid="classification-card">
                <CardHeader>
                  <CardTitle className="text-white">Classification</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Market Cap:</span>
                      <span className="px-3 py-1 bg-amber-400/20 text-amber-400 rounded-full text-sm font-semibold">
                        {analysisResult.cap_classification}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-slate-400">Risk Level:</span>
                      <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
                        analysisResult.risk_indicator === 'Low Risk' ? 'bg-emerald-400/20 text-emerald-400' :
                        analysisResult.risk_indicator === 'Medium Risk' ? 'bg-amber-400/20 text-amber-400' :
                        'bg-red-400/20 text-red-400'
                      }`}>
                        {analysisResult.risk_indicator}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card className="glass-card border-white/10" data-testid="tax-card">
                <CardHeader>
                  <CardTitle className="text-white">Tax Breakdown</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Capital Gains Tax:</span>
                      <span className="text-red-400 font-mono">
                        SAR {analysisResult.capital_gains_tax.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Dividend Tax:</span>
                      <span className="text-red-400 font-mono">
                        SAR {analysisResult.dividend_tax.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Charts */}
            <div className="grid lg:grid-cols-2 gap-6">
              <Card className="glass-card border-white/10" data-testid="cash-flow-chart">
                <CardHeader>
                  <CardTitle className="text-white">Cash Flow Projection</CardTitle>
                  <CardDescription className="text-slate-400">Yearly dividend distribution</CardDescription>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="year" stroke="#94a3b8" />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip content={<CustomTooltip />} />
                      <Line type="monotone" dataKey="dividend" stroke="#fbbf24" strokeWidth={2} name="Dividend" />
                      <Line type="monotone" dataKey="discounted" stroke="#06b6d4" strokeWidth={2} name="Discounted Value" />
                    </LineChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>

              <Card className="glass-card border-white/10" data-testid="dividend-table">
                <CardHeader>
                  <CardTitle className="text-white">Dividend Schedule</CardTitle>
                  <CardDescription className="text-slate-400">Year-by-year breakdown</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="overflow-auto max-h-[300px]">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-slate-800/80">
                        <tr className="border-b border-slate-700">
                          <th className="text-left py-2 px-3 text-slate-300 font-semibold">Year</th>
                          <th className="text-right py-2 px-3 text-slate-300 font-semibold">Dividend (SAR)</th>
                          <th className="text-right py-2 px-3 text-slate-300 font-semibold">PV (SAR)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {analysisResult.yearly_dividends.map((item) => (
                          <tr key={item.year} className="border-b border-slate-800 hover:bg-slate-800/50">
                            <td className="py-2 px-3 text-white font-mono">{item.year}</td>
                            <td className="py-2 px-3 text-right text-amber-400 font-mono">
                              {item.dividend.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </td>
                            <td className="py-2 px-3 text-right text-cyan-400 font-mono">
                              {item.discounted_value.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Summary Insight Box */}
            <Card className="glass-card border-amber-400/30 gold-glow" data-testid="summary-insight">
              <CardHeader>
                <CardTitle className="text-white flex items-center">
                  <AlertCircle className="w-5 h-5 mr-2 text-amber-400" />
                  Investment Summary
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-300 leading-relaxed">
                  Your investment of <span className="text-amber-400 font-mono font-bold">${analysisResult.investment_usd.toLocaleString()}</span> in{' '}
                  <span className="text-white font-semibold">{analysisResult.company.name}</span> ({analysisResult.company.sector} sector)
                  over a <span className="text-amber-400 font-bold">{analysisResult.exit_year}-year</span> period generates a projected NPV of{' '}
                  <span className="text-emerald-400 font-mono font-bold">SAR {analysisResult.npv.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>{' '}
                  with an IRR of <span className="text-amber-400 font-mono font-bold">{(analysisResult.irr * 100).toFixed(2)}%</span>.
                  After accounting for capital gains and dividend taxes, your after-tax return is projected at{' '}
                  <span className="text-purple-400 font-mono font-bold">{analysisResult.after_tax_return.toFixed(2)}%</span>.
                  This company is classified as <span className={`font-semibold ${
                    analysisResult.risk_indicator === 'Low Risk' ? 'text-emerald-400' :
                    analysisResult.risk_indicator === 'Medium Risk' ? 'text-amber-400' : 'text-red-400'
                  }`}>{analysisResult.risk_indicator}</span> based on its beta coefficient.
                </p>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
