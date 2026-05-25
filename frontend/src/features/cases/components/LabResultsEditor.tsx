import { useFieldArray, type Control } from "react-hook-form";
import {
  NON_TREPONEMAL_TEST_TYPES,
  NON_TREPONEMAL_TITERS,
  TREPONEMAL_TEST_TYPES,
  TREPONEMAL_RESULTS
} from "../../labs/constants";

interface LabResultsEditorProps {
  control: Control<any>;
  nontrepName: string;
  trepName: string;
}

export function LabResultsEditor({ control, nontrepName, trepName }: LabResultsEditorProps) {
  const { fields: nontrepFields, append: appendNontrep, remove: removeNontrep } = useFieldArray({
    control,
    name: nontrepName,
    keyName: "formId",
  });

  const { fields: trepFields, append: appendTrep, remove: removeTrep } = useFieldArray({
    control,
    name: trepName,
    keyName: "formId",
  });

  return (
    <div className="stack-md">
      <div className="two-column-grid gap-lg">
        {/* Non-Treponemal Labs */}
        <div className="stack-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-blue-600">🔵 Non-treponemal (RPR / VDRL)</h3>
            <button
              type="button"
              onClick={() => appendNontrep({ id: undefined, test_type: "", titer: "", collection_date: "" })}
              className="button small-button"
            >
              + Add Lab
            </button>
          </div>

          <div className="table-wrapper overflow-x-auto border rounded-lg">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                <tr>
                  <th className="px-3 py-2">Test</th>
                  <th className="px-3 py-2">Titer</th>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {nontrepFields.map((field, index) => (
                  <tr key={field.formId} className="border-t">
                    <td className="px-2 py-2">
                      <select
                        {...control.register(`${nontrepName}.${index}.test_type`)}
                        className="w-full p-1 border rounded"
                      >
                        <option value="">Select...</option>
                        {NON_TREPONEMAL_TEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      <select
                        {...control.register(`${nontrepName}.${index}.titer`)}
                        className="w-full p-1 border rounded"
                      >
                        <option value="">Select...</option>
                        {NON_TREPONEMAL_TITERS.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      <input
                        type="date"
                        {...control.register(`${nontrepName}.${index}.collection_date`)}
                        className="w-full p-1 border rounded"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <button type="button" onClick={() => removeNontrep(index)} className="text-red-500 hover:text-red-700">
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
                {nontrepFields.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-muted italic">No non-treponemal labs recorded</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Treponemal Labs */}
        <div className="stack-sm">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-green-600">🟢 Treponemal confirmatory</h3>
            <button
              type="button"
              onClick={() => appendTrep({ id: undefined, test_type: "", result: "", collection_date: "" })}
              className="button small-button"
            >
              + Add Lab
            </button>
          </div>

          <div className="table-wrapper overflow-x-auto border rounded-lg">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
                <tr>
                  <th className="px-3 py-2">Test</th>
                  <th className="px-3 py-2">Result</th>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2 w-10"></th>
                </tr>
              </thead>
              <tbody>
                {trepFields.map((field, index) => (
                  <tr key={field.formId} className="border-t">
                    <td className="px-2 py-2">
                      <select
                        {...control.register(`${trepName}.${index}.test_type`)}
                        className="w-full p-1 border rounded"
                      >
                        <option value="">Select...</option>
                        {TREPONEMAL_TEST_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      <select
                        {...control.register(`${trepName}.${index}.result`)}
                        className="w-full p-1 border rounded"
                      >
                        <option value="">Select...</option>
                        {TREPONEMAL_RESULTS.map(r => <option key={r} value={r}>{r}</option>)}
                      </select>
                    </td>
                    <td className="px-2 py-2">
                      <input
                        type="date"
                        {...control.register(`${trepName}.${index}.collection_date`)}
                        className="w-full p-1 border rounded"
                      />
                    </td>
                    <td className="px-2 py-2">
                      <button type="button" onClick={() => removeTrep(index)} className="text-red-500 hover:text-red-700">
                        ✕
                      </button>
                    </td>
                  </tr>
                ))}
                {trepFields.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-3 py-4 text-center text-muted italic">No treponemal labs recorded</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
