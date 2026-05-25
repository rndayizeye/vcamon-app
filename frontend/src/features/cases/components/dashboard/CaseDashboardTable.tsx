import React from 'react';
import type { CaseSummary } from '../../types';

interface CaseDashboardTableProps {
  cases: CaseSummary[];
  selectedCaseId: number | null;
  onCaseSelect: (id: number) => void;
}

export const CaseDashboardTable: React.FC<CaseDashboardTableProps> = ({
  cases,
  selectedCaseId,
  onCaseSelect,
}) => {
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200 shadow-sm bg-white">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">ID</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Patient</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Diagnosis</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Manager</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Reason</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Treated</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Partners</th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Updated</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {cases.map((caseItem) => (
            <tr
              key={caseItem.id}
              onClick={() => onCaseSelect(caseItem.id)}
              className={`cursor-pointer transition-colors hover:bg-blue-50 ${
                selectedCaseId === caseItem.id ? 'bg-blue-100' : ''
              } ${!caseItem.treatment_date ? 'bg-amber-50/50' : ''}`}
            >
              <td className="px-4 py-3 text-sm text-gray-900 font-medium">{caseItem.id}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{caseItem.patient_name}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{caseItem.diagnosis_code || '-'}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{caseItem.case_manager || '-'}</td>
              <td className="px-4 py-3 text-sm text-gray-700">{caseItem.reason_for_exam || '-'}</td>
              <td className="px-4 py-3 text-sm text-gray-700">
                {caseItem.treatment_date ? caseItem.treatment_date : <span className="text-amber-600 font-semibold">Pending</span>}
              </td>
              <td className="px-4 py-3 text-sm text-gray-700">{caseItem.partner_count}</td>
              <td className="px-4 py-3 text-sm text-gray-500">
                {caseItem.updated_at ? new Date(caseItem.updated_at).toLocaleDateString() : '-'}
              </td>
            </tr>
          ))}
          {cases.length === 0 && (
            <tr>
              <td colSpan={8} className="px-4 py-8 text-center text-gray-500 italic">
                No cases found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
