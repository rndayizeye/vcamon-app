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
      <div className="cluster" style={{ justifyContent: "space-between" }}>
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
