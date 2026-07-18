import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";
import { ArrowRight } from "lucide-react";

const HERO = "https://images.unsplash.com/photo-1581092795360-fd1ca04f0952?crop=entropy&cs=srgb&fm=jpg&q=85&w=1600";

export default function Login() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [showForgot, setShowForgot] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");

  const ADMIN_LIKE = new Set(["admin", "owner"]);

  if (user && user !== false) {
    return <Navigate to={ADMIN_LIKE.has(user.role) ? "/admin" : "/rep"} replace />;
  }

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    const r = await login(email.trim(), password);
    setBusy(false);
    if (r.ok) {
      toast.success("Signed in", { description: `Welcome, ${r.user.name}` });
      nav(ADMIN_LIKE.has(r.user.role) ? "/admin" : "/rep", { replace: true });
    } else {
      toast.error("Sign in failed", { description: r.error });
    }
  };

  return (
    <div className="min-h-screen w-full grid grid-cols-1 md:grid-cols-2 bg-[#F9F9F6]">
      {/* LEFT — editorial */}
      <div className="relative hidden md:block overflow-hidden" style={{ background: "#050A18" }}>
        <img src={HERO} alt="" className="absolute inset-0 w-full h-full object-cover opacity-70" />
        <div className="absolute inset-0 imh-login-overlay imh-grain" />
        <div className="relative z-10 h-full w-full flex flex-col justify-between p-14 text-white">
          <div className="flex items-center gap-3">
            <span className="imh-dot" style={{ background: "#fff" }} />
            <span className="imh-eyebrow" style={{ color: "#B8C1DA" }}>Independent Media Network</span>
          </div>

          <div>
            <div className="imh-eyebrow" style={{ color: "#B8C1DA" }}>Private Partner Platform</div>
            <h1 className="font-editorial text-5xl xl:text-6xl leading-[1.02] mt-4 max-w-xl">
              Built exclusively<br/>for <span className="italic">Independent Media Network</span><br/>Partners.
            </h1>
            <p className="mt-8 text-[15px] leading-relaxed text-[#C9D1E4] max-w-md">
              A private commercial environment reserved exclusively for licensed
              Independent Media Network Partners.
            </p>
          </div>

          <div className="flex items-center gap-8 text-[12px] tracking-widest uppercase text-[#8792AE]">
            <span>Network</span>
            <span>·</span>
            <span>Television</span>
            <span>·</span>
            <span>Partner</span>
            <span>·</span>
            <span>Presslab</span>
          </div>
        </div>
      </div>

      {/* RIGHT — form */}
      <div className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-[420px]">
          <div className="imh-eyebrow" data-testid="login-eyebrow">Authorized access</div>
          <h2 className="font-editorial text-4xl mt-3 leading-tight">Sign in to Independent Projects</h2>
          <p className="text-sm text-[#52525B] mt-3">
            Reserved for licensed Independent Media Network Partners.
          </p>

          {!showForgot ? (
            <form onSubmit={submit} className="mt-10 space-y-5" data-testid="login-form">
              <div>
                <Label htmlFor="email" className="text-[12px] uppercase tracking-widest text-[#52525B]">Email</Label>
                <Input id="email" type="email" required value={email}
                       onChange={(e) => setEmail(e.target.value)}
                       autoComplete="email" data-testid="login-email"
                       className="mt-2 h-11 border-[#D4D4D0] bg-white rounded-none focus-visible:ring-2 focus-visible:ring-[#0033A0]" />
              </div>
              <div>
                <Label htmlFor="password" className="text-[12px] uppercase tracking-widest text-[#52525B]">Password</Label>
                <Input id="password" type="password" required value={password}
                       onChange={(e) => setPassword(e.target.value)}
                       autoComplete="current-password" data-testid="login-password"
                       className="mt-2 h-11 border-[#D4D4D0] bg-white rounded-none focus-visible:ring-2 focus-visible:ring-[#0033A0]" />
              </div>
              <Button type="submit" disabled={busy} data-testid="login-submit"
                      className="w-full h-11 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white text-sm tracking-wide font-medium inline-flex items-center justify-center gap-2 transition-colors">
                {busy ? "Signing in…" : "Sign in"} <ArrowRight size={16} />
              </Button>
              <div className="pt-2 flex items-center justify-between text-[13px]">
                <button type="button" onClick={() => setShowForgot(true)}
                        data-testid="login-forgot-link"
                        className="text-[#0033A0] hover:text-[#002277] underline-offset-4 hover:underline">
                  Forgot password?
                </button>
                <span className="text-[#A1A1AA] text-[12px]">By invitation only</span>
              </div>
            </form>
          ) : (
            <ForgotForm email={forgotEmail} setEmail={setForgotEmail} onBack={() => setShowForgot(false)} />
          )}

          <div className="mt-16 pt-6 border-t border-[#E4E4E1] text-[11px] uppercase tracking-widest text-[#A1A1AA]">
            © Independent Media Network · Confidential
          </div>
        </div>
      </div>
    </div>
  );
}

function ForgotForm({ email, setEmail, onBack }) {
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { default: api } = await import("@/lib/api");
      await api.post("/auth/forgot-password", { email: email.trim() });
      toast.success("If that email exists, a reset link has been sent.");
      onBack();
    } catch (e) {
      toast.error("Request failed");
    } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="mt-10 space-y-5" data-testid="forgot-form">
      <div>
        <Label className="text-[12px] uppercase tracking-widest text-[#52525B]">Email</Label>
        <Input required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
               data-testid="forgot-email"
               className="mt-2 h-11 border-[#D4D4D0] rounded-none" />
      </div>
      <Button type="submit" disabled={busy} data-testid="forgot-submit"
              className="w-full h-11 rounded-none bg-[#0033A0] hover:bg-[#002277] text-white">
        {busy ? "Sending…" : "Send reset link"}
      </Button>
      <button type="button" onClick={onBack} className="text-[13px] text-[#52525B] hover:text-[#0A0A0A]" data-testid="forgot-back">
        ← Back to sign in
      </button>
    </form>
  );
}
