import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  listCases,
  getDashboardSummary,
  getCase,
  getCaseLatestLab
} from '../features/cases/api';
import type { CaseSummary, DashboardSummary, CaseRead, LabResultEntry } from '../features/cases/types';
import { DashboardMetrics } from '../features/cases/components/dashboard/DashboardMetrics';
import { CaseDashboardTable } from '../features/cases/components/dashboard/CaseDashboardTable';
import { CaseQuickView } from '../features/cases/components/dashboard/CaseQuickView';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(null);
  const [selectedCaseData, setSelectedCaseData] = useState<CaseRead | null>(null);
  const [latestLab, setLatestLab] = useState<LabResultEntry | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDashboardData = async () => {
      setIsLoading(true);
      try {
        const [summaryData, casesData] = await Promise.all([
          getDashboardSummary(),
          listCases('')
        ]);
        setSummary(summaryData);
        setCases(casesData);
      } catch (error) {
        console.error('Error loading dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };
    loadDashboardData();
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      if (searchQuery.trim()) {
        try {
          const filteredCases = await listCases(searchQuery);
          setCases(filteredCases);
        } catch (error) {
          console.error('Error searching cases:', error);
        }
      } else {
        const allCases = await listCases('');
        setCases(allCases);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  useEffect(() => {
    if (selectedCaseId) {
      const fetchCaseDetails = async () => {
        try {
          const [caseData, labData] = await Promise.all([
            getCase(selectedCaseId),
            getCaseLatestLab(selectedCaseId)
          ]);
          setSelectedCaseData(caseData);
          setLatestLab(labData);
        } catch (error) {
          console.error('Error fetching case details:', error);
        }
      };
      fetchCaseDetails();
    } else {
      setSelectedCaseData(null);
      setLatestLab(null);
    }
  }, [selectedCaseId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-gray-500 animate-pulse">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Case Dashboard</h1>
          <p className="text-gray-500">Manage VCA cases and monitor treatment status.</p>
        </div>
        <button
          onClick={() => navigate('/cases/new')}
          className="px-4 py-2 bg-blue-600 text-white rounded-md font-medium hover:bg-blue-700 transition-colors shadow-sm"
        >
          + New Case
        </button>
      </header>

      {summary && <DashboardMetrics summary={summary} />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-4">
          <div className="relative">
            <input
              type="text"
              placeholder="Search patients by name..."
              className="w-full px-4 py-2 pl-10 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none transition-all"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          <CaseDashboardTable
            cases={cases}
            selectedCaseId={selectedCaseId}
            onCaseSelect={setSelectedCaseId}
          />
        </div>

        <div className="lg:col-span-1">
          <CaseQuickView caseData={selectedCaseData} latestLab={latestLab} />
        </div>
      </div>
    </div>
  );
};
