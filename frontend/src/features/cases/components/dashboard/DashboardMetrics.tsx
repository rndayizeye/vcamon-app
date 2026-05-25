import React from 'react';
import type { DashboardSummary } from '../../types';

interface DashboardMetricsProps {
  summary: DashboardSummary;
}

export const DashboardMetrics: React.FC<DashboardMetricsProps> = ({ summary }) => {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
      <MetricCard
        label="Total Cases"
        value={summary.total_cases}
        color="bg-white"
      />
      <MetricCard
        label="Total Partners"
        value={summary.total_partners}
        color="bg-white"
      />
      <MetricCard
        label="Treated"
        value={summary.treated_count}
        color="bg-green-50 text-green-700 border-green-200"
      />
      <MetricCard
        label="Pending Treatment"
        value={summary.untreated_count}
        color={summary.untreated_count > 0 ? "bg-amber-50 text-amber-700 border-amber-200" : "bg-white"}
      />
    </div>
  );
};

const MetricCard = ({ label, value, color }: { label: string; value: number; color: string }) => (
  <div className={`p-4 rounded-lg border shadow-sm ${color} transition-colors`}>
    <div className="text-sm font-medium text-gray-500 uppercase tracking-wider">{label}</div>
    <div className="text-3xl font-bold mt-1">{value}</div>
  </div>
);
