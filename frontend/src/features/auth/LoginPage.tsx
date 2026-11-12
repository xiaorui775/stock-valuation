import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/api/api";
import { useAuthStatus } from "@/api/queries";
import type { User } from "@/api/types";

export default function LoginPage() {
  const navigate = useNavigate();
  const { data: status } = useAuthStatus();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const needsSetup = status?.data?.initialized === false;

  const login = useMutation({
    mutationFn: () => api.post<User>("/auth/login", { email, password, remember: true }),
    onSuccess: () => navigate("/", { replace: true }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "登录失败"),
  });

  const bootstrap = useMutation({
    mutationFn: () => api.post<User>("/auth/bootstrap", { email, password, display_name: displayName || "用户" }),
    onSuccess: () => navigate("/", { replace: true }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "初始化失败"),
  });

  useEffect(() => {
    if (status?.data?.initialized === true) navigate("/", { replace: true });
  }, [status, navigate]);

  return (
    <div className="min-h-full flex items-center justify-center px-4">
      <div className="card w-full max-w-sm">
        <h1 className="text-xl font-bold mb-1">StockVal</h1>
        <p className="note mb-5">
          {needsSetup ? "首次使用，请创建管理员账号。" : "请登录以继续。"}
        </p>

        <form
          className="flex flex-col gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            setError(null);
            if (needsSetup) bootstrap.mutate();
            else login.mutate();
          }}
        >
          {needsSetup && (
            <input
              className="input"
              placeholder="显示名称"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}
          <input
            className="input"
            type="email"
            placeholder="邮箱"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="username"
            required
          />
          <input
            className="input"
            type="password"
            placeholder="密码（至少 8 位）"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            minLength={needsSetup ? 8 : 1}
            required
          />
          {error && <p className="text-red text-sm">{error}</p>}
          <button className="btn btn-primary" type="submit" disabled={login.isPending || bootstrap.isPending}>
            {needsSetup ? "创建账号并进入" : "登录"}
          </button>
        </form>

        <p className="note mt-4">本工具仅供学习研究，不构成投资建议。</p>
      </div>
    </div>
  );
}
