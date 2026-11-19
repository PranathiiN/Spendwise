import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { authApi } from "../api/auth";
import { getErrorMessage } from "../api/client";
import { CategoryManager } from "../components/categories/CategoryManager";
import { ErrorAlert, PageHeader, SuccessAlert } from "../components/common/Feedback";
import { useAuth } from "../contexts/AuthContext";
import { SUPPORTED_CURRENCIES } from "../types";

const profileSchema = z.object({
  name: z.string().trim().min(1, "Name is required").max(100),
  preferred_currency: z.string(),
});
type ProfileValues = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password"),
    new_password: z
      .string()
      .min(8, "At least 8 characters")
      .max(128)
      .regex(/[A-Za-z]/, "Include at least one letter")
      .regex(/\d/, "Include at least one number"),
    confirm_password: z.string(),
  })
  .refine((v) => v.new_password === v.confirm_password, { message: "Passwords do not match", path: ["confirm_password"] });
type PasswordValues = z.infer<typeof passwordSchema>;

function ProfileForm() {
  const { user, setUser } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { name: user?.name ?? "", preferred_currency: user?.preferred_currency ?? "INR" },
  });

  const submit = async (values: ProfileValues) => {
    setError(null);
    setSaved(null);
    try {
      const updated = await authApi.updateProfile(values);
      setUser(updated);
      setSaved("Profile updated.");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="card space-y-4" noValidate>
      <h2 className="text-base font-semibold text-slate-900">Profile</h2>
      <SuccessAlert message={saved} />
      <ErrorAlert message={error} />
      <div>
        <label htmlFor="p-email" className="label">Email</label>
        <input id="p-email" className="input" value={user?.email ?? ""} disabled />
      </div>
      <div>
        <label htmlFor="p-name" className="label">Name</label>
        <input id="p-name" className={`input ${errors.name ? "input-error" : ""}`} {...register("name")} />
        {errors.name && <p className="field-error">{errors.name.message}</p>}
      </div>
      <div>
        <label htmlFor="p-currency" className="label">Preferred currency</label>
        <select id="p-currency" className="input" {...register("preferred_currency")}>
          {SUPPORTED_CURRENCIES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <p className="mt-1 text-xs text-slate-500">Changes how amounts are displayed. Stored amounts are not converted.</p>
      </div>
      <button type="submit" className="btn-primary" disabled={isSubmitting}>{isSubmitting ? "Saving..." : "Save profile"}</button>
    </form>
  );
}

function PasswordForm() {
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordValues>({
    resolver: zodResolver(passwordSchema),
    defaultValues: { current_password: "", new_password: "", confirm_password: "" },
  });

  const submit = async (values: PasswordValues) => {
    setError(null);
    setSaved(null);
    try {
      await authApi.changePassword(values.current_password, values.new_password);
      reset();
      setSaved("Password changed.");
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="card space-y-4" noValidate>
      <h2 className="text-base font-semibold text-slate-900">Change password</h2>
      <SuccessAlert message={saved} />
      <ErrorAlert message={error} />
      <div>
        <label htmlFor="pw-current" className="label">Current password</label>
        <input id="pw-current" type="password" autoComplete="current-password" className={`input ${errors.current_password ? "input-error" : ""}`} {...register("current_password")} />
        {errors.current_password && <p className="field-error">{errors.current_password.message}</p>}
      </div>
      <div>
        <label htmlFor="pw-new" className="label">New password</label>
        <input id="pw-new" type="password" autoComplete="new-password" className={`input ${errors.new_password ? "input-error" : ""}`} {...register("new_password")} />
        {errors.new_password && <p className="field-error">{errors.new_password.message}</p>}
      </div>
      <div>
        <label htmlFor="pw-confirm" className="label">Confirm new password</label>
        <input id="pw-confirm" type="password" autoComplete="new-password" className={`input ${errors.confirm_password ? "input-error" : ""}`} {...register("confirm_password")} />
        {errors.confirm_password && <p className="field-error">{errors.confirm_password.message}</p>}
      </div>
      <button type="submit" className="btn-primary" disabled={isSubmitting}>{isSubmitting ? "Saving..." : "Change password"}</button>
    </form>
  );
}

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Settings" subtitle="Manage your profile, security and categories" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ProfileForm />
        <PasswordForm />
      </div>
      <CategoryManager />
    </div>
  );
}
