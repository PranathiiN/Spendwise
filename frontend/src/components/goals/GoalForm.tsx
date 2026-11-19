import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { z } from "zod";
import { getErrorMessage } from "../../api/client";
import type { SavingsGoal, SavingsGoalPayload } from "../../types";
import { ColorPicker } from "../common/ColorPicker";
import { ErrorAlert } from "../common/Feedback";
import { amountSchema } from "../transactions/TransactionForm";

const schema = z.object({
  name: z.string().trim().min(1, "Name is required").max(100),
  target_amount: amountSchema,
  current_amount: z
    .string()
    .trim()
    .regex(/^(\d{1,10}(\.\d{1,2})?)?$/, "Enter a valid amount with up to 2 decimal places"),
  target_date: z.string(),
  color: z.string(),
  notes: z.string().max(1000),
});
type FormValues = z.infer<typeof schema>;

interface GoalFormProps {
  initial?: SavingsGoal | null;
  onSubmit: (payload: SavingsGoalPayload) => Promise<void>;
  onCancel: () => void;
}

export function GoalForm({ initial, onSubmit, onCancel }: GoalFormProps) {
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: initial?.name ?? "",
      target_amount: initial?.target_amount ?? "",
      current_amount: "",
      target_date: initial?.target_date ?? "",
      color: initial?.color ?? "#1baf7a",
      notes: initial?.notes ?? "",
    },
  });

  const submit = async (values: FormValues) => {
    setError(null);
    try {
      const payload: SavingsGoalPayload = {
        name: values.name,
        target_amount: values.target_amount,
        target_date: values.target_date || null,
        color: values.color,
        notes: values.notes.trim() || null,
      };
      if (!initial && values.current_amount) payload.current_amount = values.current_amount;
      await onSubmit(payload);
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="space-y-4" noValidate>
      <ErrorAlert message={error} />
      <div>
        <label htmlFor="g-name" className="label">Goal name</label>
        <input id="g-name" placeholder="e.g. Emergency fund" className={`input ${errors.name ? "input-error" : ""}`} {...register("name")} />
        {errors.name && <p className="field-error">{errors.name.message}</p>}
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="g-target" className="label">Target amount</label>
          <input id="g-target" inputMode="decimal" placeholder="0.00" className={`input ${errors.target_amount ? "input-error" : ""}`} {...register("target_amount")} />
          {errors.target_amount && <p className="field-error">{errors.target_amount.message}</p>}
        </div>
        {!initial && (
          <div>
            <label htmlFor="g-current" className="label">Already saved (optional)</label>
            <input id="g-current" inputMode="decimal" placeholder="0.00" className={`input ${errors.current_amount ? "input-error" : ""}`} {...register("current_amount")} />
            {errors.current_amount && <p className="field-error">{errors.current_amount.message}</p>}
          </div>
        )}
        <div>
          <label htmlFor="g-date" className="label">Target date (optional)</label>
          <input id="g-date" type="date" className="input" {...register("target_date")} />
        </div>
      </div>
      <div>
        <span className="label">Color</span>
        <Controller control={control} name="color" render={({ field }) => <ColorPicker value={field.value} onChange={field.onChange} />} />
      </div>
      <div>
        <label htmlFor="g-notes" className="label">Notes (optional)</label>
        <textarea id="g-notes" rows={2} className="input" {...register("notes")} />
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <button type="button" className="btn-secondary" onClick={onCancel} disabled={isSubmitting}>Cancel</button>
        <button type="submit" className="btn-primary" disabled={isSubmitting}>
          {isSubmitting ? "Saving..." : initial ? "Save changes" : "Create goal"}
        </button>
      </div>
    </form>
  );
}
