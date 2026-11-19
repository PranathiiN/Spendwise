import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useLocation, useNavigate } from "react-router";
import { z } from "zod";
import { getErrorMessage } from "../api/client";
import { ErrorAlert } from "../components/common/Feedback";
import { AuthLayout } from "../components/layout/AuthLayout";
import { useAuth } from "../contexts/AuthContext";

const schema = z.object({
  email: z.string().trim().min(1, "Email is required").email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [error, setError] = useState<string | null>(null);
  const from = (location.state as { from?: string } | null)?.from ?? "/dashboard";

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      await login(values.email, values.password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(getErrorMessage(err));
    }
  };

  return (
    <AuthLayout title="Welcome" subtitle="Log in to manage your money with SpendWise">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <ErrorAlert message={error} />
        <div>
          <label htmlFor="email" className="label">Email</label>
          <input id="email" type="email" autoComplete="email" className={`input ${errors.email ? "input-error" : ""}`} {...register("email")} />
          {errors.email && <p className="field-error">{errors.email.message}</p>}
        </div>
        <div>
          <label htmlFor="password" className="label">Password</label>
          <input id="password" type="password" autoComplete="current-password" className={`input ${errors.password ? "input-error" : ""}`} {...register("password")} />
          {errors.password && <p className="field-error">{errors.password.message}</p>}
        </div>
        <button type="submit" className="btn-primary w-full" disabled={isSubmitting}>
          {isSubmitting ? "Logging in..." : "Log in"}
        </button>
        <p className="text-center text-sm text-slate-500">
          New to SpendWise?{" "}
          <Link to="/register" className="font-medium text-brand-700 hover:underline">Create an account</Link>
        </p>
      </form>
    </AuthLayout>
  );
}
