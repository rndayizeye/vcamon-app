import React from 'react';
import { Link } from 'react-router-dom';
import type { CaseRead, LabResultEntry } from '../../types';

interface CaseQuickViewProps {
  caseData: CaseRead | null;
  latestLab: LabResultEntry | null;
}

export const CaseQuickView: React.FC<CaseQuickViewProps> = ({ caseData, latestLab }) => {
  if (!caseData) {
    return (
      <div className="p-6 rounded-lg border border-dashed border-gray-300 bg-gray-50 text-center text-gray-500">
        Select a case from the table to view details.
      </div>
    );
  }

  return (
    <div className="p-6 rounded-lg border border-gray-200 bg-white shadow-sm space-y-6">
      <div className="flex justify-between items-start border-b pb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">{caseData.patient_name}</h3>
          <p className="text-sm text-gray-500">Case #{caseData.id}</p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/cases/${caseData.id}/edit`}
            className="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded hover:bg-blue-700 transition-colors"
          >
            Edit Case
          </Link>
          <Link
            to={`/cases/${caseData.id}/partners`}
            className="px-3 py-1.5 bg-gray-100 text-gray-700 text-xs font-medium rounded hover:bg-gray-200 transition-colors"
          >
            Partners
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <label className="block text-gray-500 text-xs uppercase font-semibold">Diagnosis</label>
          <p className="text-gray-900">{caseData.diagnosis_code || '-'}</p>
        </div>
        <div>
          <label className="block text-gray-500 text-xs uppercase font-semibold">Manager</label>
          <p className="text-gray-900">{caseData.case_manager || '-'}</p>
        </div>
        <div>
          <label className="block text-gray-500 text-xs uppercase font-semibold">Reason</label>
          <p className="text-gray-900">{caseData.reason_for_exam || '-'}</p>
        </div>
        <div>
          <label className="block text-gray-500 text-xs uppercase font-semibold">Treated</label>
          <p className="text-gray-900">{caseData.treatment_date || 'Pending'}</p>
        </div>
      </div>

      <div className="pt-4 border-t">
        <label className="block text-gray-500 text-xs uppercase font-semibold mb-1">Latest Lab Result</label>
        {latestLab ? (
          <div className="p-3 bg-blue-50 rounded-md border border-blue-100 text-sm">
            <div className="font-bold text-blue-900">{latestLab.test_type}: {latestLab.result}</div>
            <div className="text-blue-700 text-xs">
              {latestLab.titer && <span>Titer: {latestLab.titer}</span>}
              <span className="ml-2 opacity-75">Collected: {latestLab.collection_date}</span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">No lab results recorded</p>
        )}
      </div>

      <div className="pt-4 border-t">
        <label className="block text-gray-500 text-xs uppercase font-semibold mb-1">Medical Info</label>
        <p className="text-sm text-gray-700 whitespace-pre-wrap italic">
          {caseData.medical_info || 'No medical information provided.'}
        </p>
      </div>
    </div>
  );
};
