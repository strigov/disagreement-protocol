import { useMemo, type ComponentProps } from "react";
import { Link as RouterLink, useNavigate, useParams as useRouteParams } from "react-router-dom";

// Navigation within the persistent Electron app origin.
export function useRouter() {
  const navigate = useNavigate();
  return useMemo(() => ({
    push: (href: string) => { void navigate(href); },
    replace: (href: string) => { void navigate(href, { replace: true }); },
    back: () => { void navigate(-1); },
  }), [navigate]);
}

export function useParams<T extends Record<string, string>>() {
  return useRouteParams() as T;
}

export default function Link({ href, ...props }: Omit<ComponentProps<typeof RouterLink>, "to"> & { href: string }) {
  return <RouterLink to={href} {...props} />;
}
