import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { getErrorMessage } from "../../api/client";
import type { SavingsGoal } from "../../types";
import { ErrorAlert } from "../common/Feedback";
import { amountSchema } from "../transactions/TransactionForm";

const schema = z.object({ amount: amountSchema });
type FormValues = z.infer<typeof schema>;

interface ContributeFormProps {
  goal: SavingsGoal;
  action: "deposit" | "withdraw";
  format: (v: string) => string;
  onSubmit: (amount: string) => Promise<void>;
  onCancel: () => void;
}

export function ContributeForm({ goal, action, format, onSubmit, onCancel }: ContributeFormProps) {
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { amount: "" } });

  const submit = async (values: FormValues) => {
    setError(null);
    try {
      await onSubmit(values.amount);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <ErrorAlert message={error} />
      <p className="text-sm text-slate-600">
        <span className="font-medium text-slate-900">{goal.name}</span>: {format(goal.current_amount)} saved of{" "}
        {format(goal.target_amount)}
      </p>
      <div>
        <label htmlFor="c-amount" className="label">{action === "deposit" ? "Amount to add" : "Amount to withdraw"}</label>
        <input id="c-amount" inputMode="decimal" placeholder="0.00" autoFocus className={`input ${errors.amount ? "input-error" : ""}`} {...register("amount")} />
        {errors.amount && <p className="field-error">{errors.amount.message}</p>}
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>Cancel</button>
        <button type="submit" className={action === "deposit" ? "btn-primary" : "btn-danger"} disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : action === "deposit" ? "Add money" : "Withdraw"}
        </button>
      </div>
    </form>
  );
}
