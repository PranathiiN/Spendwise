import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router";
import { z } from "zod";
import { getErrorMessage } from "../api/client";
import { ErrorAlert } from "../components/common/Feedback";
import { AuthLayout } from "../components/layout/AuthLayout";
import { useAuth } from "../contexts/AuthContext";
import { SUPPORTED_CURRENCIES } from "../types";

const schema = z
  .object({
    name: z.string().trim().min(1, "Name is required").max(100),
    email: z.string().trim().min(1, "Email is required").email("Enter a valid email"),
    password: z
      .string()
      .min(8, "At least 8 characters")
      .max(128)
      .regex(/[A-Za-z]/, "Include at least one letter")
      .regex(/\d/, "Include at least one number"),
    confirmPassword: z.string(),
    preferred_currency: z.string(),
  })
  .refine((v) => v.password === v.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });
type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", email: "", password: "", confirmPassword: "", preferred_currency: "INR" },
  });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      await registerUser({
        name: values.name,
        email: values.email,
        password: values.password,
        preferred_currency: values.preferred_currency,
      });
      navigate("/dashboard", { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <AuthLayout title="Create your account" subtitle="Start tracking income, expenses, budgets and goals">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <ErrorAlert message={error} />
        <div>
          <label htmlFor="name" className="label">Name</label>
          <input id="name" autoComplete="name" className={`input ${errors.name ? "input-error" : ""}`} {...register("name")} />
          {errors.name && <p className="field-error">{errors.name.message}</p>}
        </div>
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" type="email" autoComplete="email" className={`input ${errors.email ? "input-error" : ""}`} {...register("email")} />
          {errors.email && <p className="field-error">{errors.email.message}</p>}
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="password" className="label">Password</label>
            <input id="password" type="password" autoComplete="new-password" className={`input ${errors.password ? "input-error" : ""}`} {...register("password")} />
            {errors.password && <p className="field-error">{errors.password.message}</p>}
          </div>
          <div>
            <label htmlFor="confirmPassword" className="label">Confirm password</label>
            <input id="confirmPassword" type="password" autoComplete="new-password" className={`input ${errors.confirmPassword ? "input-error" : ""}`} {...register("confirmPassword")} />
            {errors.confirmPassword && <p className="field-error">{errors.confirmPassword.message}</p>}
          </div>
        </div>
        <div>
          <label htmlFor="currency" className="label">Currency</label>
          <select id="currency" className="input" {...register("preferred_currency")}>
            {SUPPORTED_CURRENCIES.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          {isSubmitting ? "Creating account..." : "Create account"}
        </button>
        <p className="text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-brand-700 hover:underline">Log in</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
