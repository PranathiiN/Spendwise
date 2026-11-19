import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { getErrorMessage } from "../../api/client";
import type { Budget, Category } from "../../types";
import { formatMonthLabel } from "../../utils/dates";
import { ErrorAlert } from "../common/Feedback";
import { amountSchema } from "../transactions/TransactionForm";

const schema = z.object({
  category_id: z.string().min(1, "Choose a category"),
  amount: amountSchema,
  alert_threshold: z
    .string()
    .regex(/^\d{1,3}$/, "Enter a whole number")
    .refine((v) => Number(v) >= 1 && Number(v) <= 100, "Between 1 and 100"),
});
type FormValues = z.infer<typeof schema>;

export interface BudgetFormValues {
  category_id: string;
  amount: string;
  alert_threshold: number;
}

interface BudgetFormProps {
  month: string;
  /** Expense categories that don't have a budget yet this month (create mode). */
  availableCategories: Category[];
  initial?: Budget | null;
  onSubmit: (values: BudgetFormValues) => Promise<void>;
  onCancel: () => void;
}

export function BudgetForm({ month, availableCategories, initial, onSubmit, onCancel }: BudgetFormProps) {
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      category_id: initial?.category.id ?? "",
      amount: initial?.amount ?? "",
      alert_threshold: String(initial?.alert_threshold ?? 80),
    },
  });

  const submit = async (values: FormValues) => {
    setError(null);
    try {
      await onSubmit({ ...values, alert_threshold: Number(values.alert_threshold) });
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <ErrorAlert message={error} />
      <p className="text-sm text-slate-500">Budget for {formatMonthLabel(month)}</p>
      <div>
        <label htmlFor="b-category" className="label">Expense category</label>
        {initial ? (
          <input id="b-category" className="input" value={initial.category.name} disabled />
        ) : (
          <select id="b-category" className={`input ${errors.category_id ? "input-error" : ""}`} {...register("category_id")}>
            <option value="">Select a category</option>
            {availableCategories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        )}
        {errors.category_id && <p className="field-error">{errors.category_id.message}</p>}
        {!initial && availableCategories.length === 0 && (
          <p className="mt-1 text-xs text-slate-500">Every expense category already has a budget this month.</p>
        )}
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="b-amount" className="label">Monthly limit</label>
          <input id="b-amount" inputMode="decimal" placeholder="0.00" className={`input ${errors.amount ? "input-error" : ""}`} {...register("amount")} />
          {errors.amount && <p className="field-error">{errors.amount.message}</p>}
        </div>
        <div>
          <label htmlFor="b-threshold" className="label">Warn me at (%)</label>
          <input id="b-threshold" inputMode="numeric" className={`input ${errors.alert_threshold ? "input-error" : ""}`} {...register("alert_threshold")} />
          {errors.alert_threshold && <p className="field-error">{errors.alert_threshold.message}</p>}
        </div>
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : initial ? "Save changes" : "Create budget"}
        </button>
      </div>
    </form>
  );
}
