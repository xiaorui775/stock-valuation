import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/api/api";
import type { User } from "@/api/types";

export default function LoginPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const next = params.get("next") ?? "/";
  // 「是否已登录」只能看 /auth/me（401 之外的 200）；/auth/status 的 initialized
  // 只表示系统有账号，之前把两者混为一谈会导致登录页一闪而过（登录页立即弹回）。
  const me = useQuery({
    queryKey: ["auth", "me", "login-page"],
    queryFn: () => api.get<User>("/auth/me"),
    retry: false,
    staleTime: 0,
  });
  // 初始化状态只在会话有效时才需要（bootstrap 接口本身会拒绝重复初始化），
  // 未登录时先显示登录表单，登录失败再引导去创建账号。
  const status = useQuery({
    queryKey: ["auth", "status", "login-page"],
    queryFn: () => api.get<{ initialized: boolean }>("/auth/status"),
    retry: false,
  });
  const needsSetup = me.isError && status?.data?.data?.initialized === false;
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const login = useMutation({
    mutationFn: () => api.post<User>("/auth/login", { email, password, remember: true }),
    onSuccess: () => navigate(next, { replace: true }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "登录失败"),
  });

  const bootstrap = useMutation({
    mutationFn: () => api.post<User>("/auth/bootstrap", { email, password, display_name: displayName || "用户" }),
    onSuccess: () => navigate(next, { replace: true }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "初始化失败"),
  });

  useEffect(() => {
    if (me.data) navigate(next, { replace: true });
  }, [me.data, navigate, next]);

  return (
    <div className="min-h-full flex items-center justify-center px-4">
      <div className="card w-full max-w-sm">
        <h1 className="text-xl font-bold mb-1">StockVal</h1>
        <p className="note mb-5">
          {me.isLoading
            ? "正在检查登录状态…"
            : me.data
              ? "已登录，正在进入…"
              : needsSetup
                ? "首次使用，请创建管理员账号。"
                : "请登录以继续。"}
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
