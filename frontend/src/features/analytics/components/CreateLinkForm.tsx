import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";

import { useAuth } from "../../../auth/use-auth";
import { useCreateCaseLink } from "../hooks";
import type { AnalyticsNodeRead } from "../types";

type LinkFormValues = {
  from_ref: string;
  to_ref: string;
};

export function CreateLinkForm({
  caseId,
  nodes,
}: {
  caseId: number;
  nodes: AnalyticsNodeRead[];
}) {
  const { permissions } = useAuth();
  const createMutation = useCreateCaseLink(caseId);

  const options = useMemo(() => {
    return [...nodes]
      .sort((left, right) => {
        if (left.ref === "OP") return -1;
        if (right.ref === "OP") return 1;
        return left.label.localeCompare(right.label);
      })
      .map((node) => ({
        value: node.ref,
        label: node.label,
      }));
  }, [nodes]);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors },
  } = useForm<LinkFormValues>({
    defaultValues: {
      from_ref: options[0]?.value || "",
      to_ref: options[1]?.value || options[0]?.value || "",
    },
  });

  useEffect(() => {
    reset({
      from_ref: options[0]?.value || "",
      to_ref: options[1]?.value || options[0]?.value || "",
    });
  }, [options, reset]);

  async function onSubmit(values: LinkFormValues) {
    if (values.from_ref === values.to_ref) {
      setError("to_ref", {
        type: "validate",
        message: "Source and target must be different.",
      });
      return;
    }

    await createMutation.mutateAsync(values);
    reset({
      from_ref: options[0]?.value || "",
      to_ref: options[1]?.value || options[0]?.value || "",
    });
  }

  if (!permissions.can_write) {
    return (
      <div className="panel stack-sm">
        <p className="eyebrow">Create link</p>
        <p className="muted">You do not have permission to add links.</p>
      </div>
    );
  }

  if (options.length < 2) {
    return (
      <div className="panel stack-sm">
        <p className="eyebrow">Create link</p>
        <p className="muted">
          At least two visible nodes are required before you can create a link.
        </p>
      </div>
    );
  }

  return (
    <form className="panel stack-md" onSubmit={handleSubmit(onSubmit)}>
      <div>
        <p className="eyebrow">Create link</p>
        <h2>Add arrow link</h2>
      </div>

      <div className="two-column-grid">
        <label className="field">
          <span>From</span>
          <select {...register("from_ref", { required: true })}>
            {options.map((option) => (
              <option key={`from-${option.value}`} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="field">
          <span>To</span>
          <select {...register("to_ref", { required: true })}>
            {options.map((option) => (
              <option key={`to-${option.value}`} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {errors.to_ref?.message ? (
        <p className="error-text">{errors.to_ref.message}</p>
      ) : null}
      {createMutation.isError ? (
        <p className="error-text">{createMutation.error.message}</p>
      ) : null}

      <button
        className="button button-primary"
        type="submit"
        disabled={createMutation.isPending}
      >
        {createMutation.isPending ? "Creating…" : "Create link"}
      </button>
    </form>
  );
}
