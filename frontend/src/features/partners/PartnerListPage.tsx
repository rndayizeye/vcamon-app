import { Link, useParams } from "react-router-dom";
import { ErrorState } from "../../components/feedback/ErrorState";
import { LoadingState } from "../../components/feedback/LoadingState";
import { useCasePartners } from "./hooks";

export function PartnerListPage() {
  const { caseId } = useParams();
  const safeCaseId = Number(caseId);
  const partnersQuery = useCasePartners(safeCaseId);

  if (partnersQuery.isLoading) {
    return <LoadingState message="Loading partners…" />;
  }

  if (partnersQuery.isError) {
    return (
      <ErrorState
        title="Failed to load partners"
        message={partnersQuery.error.message}
        onRetry={() => void partnersQuery.refetch()}
      />
    );
  }

  const partners = partnersQuery.data ?? [];

  return (
    <div className="stack-lg">
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "1rem" }}>
        <h2>Partners ({partners.length})</h2>
        <Link to="new" className="button button-primary">
          Add Partner
        </Link>
      </div>

      {partners.length === 0 ? (
        <div
          className="card text-center"
          style={{ padding: "var(--spacing-xl)" }}
        >
          <p className="text-secondary">No partners found for this case.</p>
        </div>
      ) : (
        <div className="card">
          <table className="table" style={{ width: "100%", textAlign: "left" }}>
            <thead>
              <tr>
                <th>Partner #</th>
                <th>Name</th>
                <th>Treatment Date</th>
                <th>Linked Case</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {partners.map((partner) => (
                <tr key={partner.id}>
                  <td>{partner.partner_number}</td>
                  <td>
                    {partner.name || (
                      <span className="text-secondary">Unknown</span>
                    )}
                  </td>
                  <td>
                    {partner.treatment_date || (
                      <span className="text-secondary">-</span>
                    )}
                  </td>
                  <td>
                    {partner.linked_case_id ? (
                      <Link
                        to={`/cases/${partner.linked_case_id}`}
                        style={{
                          fontSize: "0.75rem",
                          padding: "2px 8px",
                          borderRadius: "12px",
                          background: "var(--color-primary, #2563eb)",
                          color: "#fff",
                          textDecoration: "none",
                          fontWeight: 600,
                        }}
                      >
                        Case #{partner.linked_case_id}
                      </Link>
                    ) : (
                      <span className="text-secondary">—</span>
                    )}
                  </td>
                  <td>
                    {new Date(partner.created_at || "").toLocaleDateString()}
                  </td>
                  <td>
                    <Link
                      to={`${partner.id}/edit`}
                      className="text-primary"
                      style={{ fontWeight: "bold" }}
                    >
                      Edit
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
