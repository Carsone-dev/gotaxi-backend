# 💻 GoTaxi — Guide complet de l'application web React JS

> **Version :** 1.0.0
> **Référence :** GT-WEB-2026-001
> **Stack :** React 18 · TypeScript · Vite · React Router · TanStack Query · Tailwind CSS · shadcn/ui
> **Cible :** Développeur frontend senior

Ce document est le **manuel d'exécution complet** pour bâtir les deux applications web GoTaxi : la **landing page publique** (marketing + acquisition) et le **dashboard administrateur** (pilotage opérationnel).

---

## 📑 Sommaire

1. [Vue d'ensemble & principes](#1-vue-densemble--principes)
2. [Stack technique](#2-stack-technique)
3. [Stratégie : 2 apps ou monorepo ?](#3-stratégie--2-apps-ou-monorepo-)
4. [Structure du projet](#4-structure-du-projet)
5. [Configuration](#5-configuration)
6. [Design system & Tailwind](#6-design-system--tailwind)
7. [Routing](#7-routing)
8. [Authentification admin](#8-authentification-admin)
9. [Couche API & data fetching](#9-couche-api--data-fetching)
10. [Landing page — pages détaillées](#10-landing-page--pages-détaillées)
11. [Dashboard admin — pages détaillées](#11-dashboard-admin--pages-détaillées)
12. [Composants partagés](#12-composants-partagés)
13. [Cartes & géolocalisation](#13-cartes--géolocalisation)
14. [Temps réel (WebSockets)](#14-temps-réel-websockets)
15. [Internationalisation](#15-internationalisation)
16. [SEO & performance](#16-seo--performance)
17. [Tests](#17-tests)
18. [Build & déploiement](#18-build--déploiement)
19. [Conventions de code](#19-conventions-de-code)

---

## 1. Vue d'ensemble & principes

### 1.1 Mission du web

Le web GoTaxi sert deux usages très différents :

**Site public (`gotaxi.bj`)** — vitrine marketing, conversion :
- Présentation produit (voyageurs, expéditeurs, chauffeurs)
- Recrutement chauffeurs
- Recherche rapide de trajets
- Page de suivi public d'un colis (par référence)
- Téléchargement app iOS/Android
- SEO maximal (Next-style SSG ou SSR)

**Dashboard admin (`admin.gotaxi.bj`)** — pilotage opérationnel :
- Vue d'ensemble (KPIs, revenus, activité live)
- Carte temps réel de la flotte
- Gestion utilisateurs et chauffeurs (KYC)
- Modération des colis (validation, assignation)
- Transactions Mobile Money + audit
- Gestion des avis et litiges
- Logs d'audit pour super admins

### 1.2 Principes architecturaux

- **Composants atomiques** (Atomic Design : atoms → molecules → organisms → pages)
- **Type-safe** : TypeScript strict + Zod pour la validation runtime
- **Server state** géré par TanStack Query, **client state** par Zustand
- **Mobile-first** pour la landing, **desktop-first** pour l'admin
- **Accessible** : WCAG AA minimum, focus management, ARIA
- **Performance budget** : Lighthouse ≥ 95 (landing), LCP < 2s

---

## 2. Stack technique

### 2.1 Choix de la stack

| Choix | Justification |
|-------|---------------|
| **Vite** | Dev server ultra rapide, build optimisé (Rollup) |
| **React 18** | Concurrent rendering, transitions, suspense |
| **TypeScript strict** | Type safety + DX |
| **Tailwind CSS** | Productivité, design tokens, JIT |
| **shadcn/ui** | Composants accessibles copy/paste, contrôle total |
| **TanStack Query v5** | Cache HTTP, mutations, optimistic UI |
| **TanStack Table v8** | Tables performantes (admin) |
| **Zustand** | State global léger |
| **React Router v6** | Routing déclaratif, code-splitting natif |
| **Recharts** | Charts simples et flexibles (dashboard) |
| **Mapbox GL JS** | Cartes performantes pour la flotte temps réel |
| **Zod** | Schemas runtime + inférence TS |

### 2.2 Dépendances principales

```json
{
  "name": "gotaxi-web",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest",
    "test:e2e": "playwright test"
  },
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-router-dom": "^6.27.0",
    "@tanstack/react-query": "^5.59.0",
    "@tanstack/react-table": "^8.20.0",
    "@tanstack/react-query-devtools": "^5.59.0",
    "axios": "^1.7.0",
    "zustand": "^5.0.0",
    "zod": "^3.23.0",
    "react-hook-form": "^7.53.0",
    "@hookform/resolvers": "^3.9.0",
    "recharts": "^2.13.0",
    "mapbox-gl": "^3.7.0",
    "react-map-gl": "^7.1.0",
    "date-fns": "^4.1.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.5.0",
    "class-variance-authority": "^0.7.0",
    "lucide-react": "^0.456.0",
    "sonner": "^1.7.0",
    "i18next": "^23.16.0",
    "react-i18next": "^15.1.0",
    "framer-motion": "^11.11.0",
    "react-helmet-async": "^2.0.0",
    "@radix-ui/react-dialog": "^1.1.0",
    "@radix-ui/react-dropdown-menu": "^2.1.0",
    "@radix-ui/react-select": "^2.1.0",
    "@radix-ui/react-tabs": "^1.1.0",
    "@radix-ui/react-toast": "^1.2.0",
    "@radix-ui/react-tooltip": "^1.1.0"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@types/mapbox-gl": "^3.4.0",
    "@vitejs/plugin-react-swc": "^3.7.0",
    "typescript": "^5.6.0",
    "vite": "^5.4.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "vitest": "^2.1.0",
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.6.0",
    "@playwright/test": "^1.48.0",
    "eslint": "^9.0.0",
    "@typescript-eslint/eslint-plugin": "^8.0.0",
    "prettier": "^3.3.0",
    "prettier-plugin-tailwindcss": "^0.6.0"
  }
}
```

---

## 3. Stratégie : 2 apps ou monorepo ?

### 3.1 Option recommandée : monorepo avec pnpm workspaces

```
gotaxi-web/
├── apps/
│   ├── landing/          # Site public gotaxi.bj
│   └── admin/            # Dashboard admin.gotaxi.bj
├── packages/
│   ├── ui/               # Composants partagés (shadcn-style)
│   ├── api-client/       # Client API typé (réutilisable mobile)
│   ├── theme/            # Design tokens
│   └── config/           # Configs Tailwind, ESLint, TS
├── pnpm-workspace.yaml
├── package.json
└── tsconfig.base.json
```

**Pourquoi :**
- Composants UI réutilisables (Button, Card, Modal)
- Types API partagés (cohérence avec backend)
- Theme cohérent partout
- Déploiements indépendants
- Tests partagés possibles

### 3.2 Workspace config

```yaml
# pnpm-workspace.yaml
packages:
  - "apps/*"
  - "packages/*"
```

```json
// package.json racine
{
  "name": "gotaxi-web",
  "private": true,
  "scripts": {
    "dev:landing": "pnpm --filter landing dev",
    "dev:admin": "pnpm --filter admin dev",
    "build": "pnpm -r build",
    "lint": "pnpm -r lint",
    "test": "pnpm -r test"
  },
  "devDependencies": {
    "@gotaxi/config": "workspace:*",
    "prettier": "^3.3.0",
    "typescript": "^5.6.0"
  }
}
```

---

## 4. Structure du projet

### 4.1 Structure de l'app `admin`

```
apps/admin/
├── public/
│   ├── favicon.svg
│   └── robots.txt
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/
│   │   ├── index.tsx              # Router config
│   │   ├── _layout.tsx            # Layout principal (sidebar + header)
│   │   ├── login.tsx
│   │   ├── dashboard.tsx
│   │   ├── fleet.tsx              # Carte flotte temps réel
│   │   ├── users/
│   │   │   ├── index.tsx          # Liste utilisateurs
│   │   │   └── [id].tsx           # Détail utilisateur
│   │   ├── chauffeurs/
│   │   │   ├── index.tsx
│   │   │   ├── [id].tsx
│   │   │   └── kyc-pending.tsx    # KYC à valider
│   │   ├── voyages/
│   │   │   ├── index.tsx
│   │   │   └── [id].tsx           # Détail trajet (supervision)
│   │   ├── colis/
│   │   │   ├── index.tsx
│   │   │   ├── pending.tsx        # À valider
│   │   │   ├── in-transit.tsx     # En route
│   │   │   └── [id].tsx
│   │   ├── transactions/
│   │   │   ├── index.tsx
│   │   │   └── [id].tsx
│   │   ├── reviews/
│   │   │   ├── index.tsx
│   │   │   └── disputes.tsx
│   │   ├── audit/
│   │   │   └── index.tsx
│   │   └── settings/
│   │       └── index.tsx
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   └── PageHeader.tsx
│   │   ├── dashboard/
│   │   │   ├── KPICard.tsx
│   │   │   ├── RevenueChart.tsx
│   │   │   ├── TopRoutesList.tsx
│   │   │   ├── ActivityFeed.tsx
│   │   │   └── MoMoBreakdown.tsx
│   │   ├── fleet/
│   │   │   ├── FleetMap.tsx
│   │   │   ├── DriverMarker.tsx
│   │   │   ├── ActiveTripsPanel.tsx
│   │   │   └── MapLegend.tsx
│   │   ├── users/
│   │   │   ├── UsersTable.tsx
│   │   │   ├── UserDetailDrawer.tsx
│   │   │   └── UserStatusBadge.tsx
│   │   ├── colis/
│   │   │   ├── PendingCard.tsx
│   │   │   ├── ColisTable.tsx
│   │   │   ├── AssignmentSuggestions.tsx
│   │   │   └── DisputeBox.tsx
│   │   ├── transactions/
│   │   │   ├── TransactionsTable.tsx
│   │   │   ├── OperatorCard.tsx
│   │   │   └── VolumeChart.tsx
│   │   ├── reviews/
│   │   │   ├── ReviewCard.tsx
│   │   │   ├── DisputeCard.tsx
│   │   │   └── ArbitrationDialog.tsx
│   │   └── ui/                    # Re-exports depuis @gotaxi/ui
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useDashboard.ts
│   │   ├── useFleet.ts
│   │   ├── useUsers.ts
│   │   ├── useColis.ts
│   │   ├── useTransactions.ts
│   │   ├── useDebounce.ts
│   │   └── useWebSocket.ts
│   ├── stores/
│   │   ├── authStore.ts
│   │   └── filtersStore.ts
│   ├── lib/
│   │   ├── api.ts
│   │   ├── format.ts
│   │   ├── auth.ts
│   │   └── permissions.ts
│   ├── types/
│   │   ├── api.ts
│   │   └── domain.ts
│   ├── i18n/
│   │   ├── index.ts
│   │   └── fr.json
│   └── styles/
│       └── globals.css
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── package.json
```

### 4.2 Structure de l'app `landing`

```
apps/landing/
├── public/
│   ├── favicon.svg
│   ├── og-image.png
│   ├── sitemap.xml
│   └── robots.txt
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── routes/
│   │   ├── index.tsx
│   │   ├── _layout.tsx           # Layout (header + footer)
│   │   ├── home.tsx              # Page d'accueil
│   │   ├── voyager.tsx           # "Pour les voyageurs"
│   │   ├── colis.tsx             # "Envoyer un colis"
│   │   ├── chauffeur.tsx         # "Devenir chauffeur"
│   │   ├── tarifs.tsx
│   │   ├── about.tsx
│   │   ├── help/
│   │   │   ├── index.tsx
│   │   │   └── [slug].tsx        # Articles d'aide
│   │   ├── legal/
│   │   │   ├── cgu.tsx
│   │   │   ├── privacy.tsx
│   │   │   └── cookies.tsx
│   │   ├── track/
│   │   │   └── [reference].tsx   # Suivi public colis
│   │   └── search.tsx            # Recherche rapide trajets
│   ├── components/
│   │   ├── layout/
│   │   │   ├── Header.tsx
│   │   │   ├── Footer.tsx
│   │   │   └── MobileMenu.tsx
│   │   ├── home/
│   │   │   ├── HeroSection.tsx
│   │   │   ├── SearchBar.tsx
│   │   │   ├── FeaturesGrid.tsx
│   │   │   ├── DriverCTA.tsx
│   │   │   ├── Testimonials.tsx
│   │   │   └── Stats.tsx
│   │   ├── chauffeur/
│   │   │   ├── BenefitsSection.tsx
│   │   │   ├── EarningsCalculator.tsx
│   │   │   └── ApplicationForm.tsx
│   │   ├── track/
│   │   │   ├── TrackingForm.tsx
│   │   │   └── TrackingResult.tsx
│   │   └── ui/
│   ├── hooks/
│   ├── lib/
│   ├── types/
│   ├── i18n/
│   └── styles/
├── index.html
├── vite.config.ts
└── package.json
```

---

## 5. Configuration

### 5.1 Variables d'environnement

```bash
# apps/admin/.env.example
VITE_API_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws
VITE_MAPBOX_TOKEN=pk.eyJ...
VITE_SENTRY_DSN=
VITE_ENV=development
```

```bash
# apps/landing/.env.example
VITE_API_URL=http://localhost:8000/api/v1
VITE_PUBLIC_TRACKING_URL=https://gotaxi.bj/track
VITE_GA_ID=G-XXXXXXXXXX
VITE_PLAUSIBLE_DOMAIN=gotaxi.bj
```

### 5.2 `vite.config.ts`

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@gotaxi/ui": path.resolve(__dirname, "../../packages/ui/src"),
      "@gotaxi/api-client": path.resolve(
        __dirname,
        "../../packages/api-client/src",
      ),
    },
  },
  server: {
    port: 3001, // 3000 pour landing, 3001 pour admin
    host: true,
  },
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query", "@tanstack/react-table"],
          charts: ["recharts"],
          map: ["mapbox-gl", "react-map-gl"],
        },
      },
    },
  },
});
```

### 5.3 `tsconfig.json` strict

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "resolveJsonModule": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"],
      "@gotaxi/*": ["../../packages/*/src"]
    }
  },
  "include": ["src"]
}
```

---

## 6. Design system & Tailwind

### 6.1 `tailwind.config.ts`

```typescript
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["class"],
  theme: {
    extend: {
      colors: {
        // Brand
        primary: {
          DEFAULT: "#009542",
          50: "#E8F5EE",
          100: "#C8E5D5",
          400: "#00C957",
          500: "#009542",
          600: "#007A36",
          700: "#006B30",
          900: "#004520",
        },
        accent: {
          yellow: "#FFD700",
          "yellow-dark": "#BA9700",
        },
        // Surface
        ink: {
          DEFAULT: "#1c1c1a",
          soft: "#2D2D29",
        },
        surface: {
          DEFAULT: "#F8FAF9",
          alt: "#F1EFE8",
        },
        // Semantic
        success: { DEFAULT: "#009542", bg: "#EAF6EF", text: "#0F6E56" },
        warning: { DEFAULT: "#FFD700", bg: "#FAEEDA", text: "#854F0B" },
        error: { DEFAULT: "#FF4D4D", bg: "#FCEBEB", text: "#A32D2D" },
        info: { DEFAULT: "#0066FF", bg: "#E6F1FB", text: "#185FA5" },
        // Operators
        mtn: "#FFD700",
        moov: "#00B7E2",
        orange: "#FF6600",
      },
      fontFamily: {
        sans: ['"Inter"', "system-ui", "sans-serif"],
      },
      fontSize: {
        "2xs": ["0.625rem", "0.875rem"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      boxShadow: {
        soft: "0 2px 8px rgba(0,0,0,0.05)",
        card: "0 4px 12px rgba(0,0,0,0.08)",
        elevated: "0 20px 40px rgba(0,0,0,0.15)",
      },
      backgroundImage: {
        "gradient-primary": "linear-gradient(135deg, #00C957, #006B30)",
        "gradient-dark": "linear-gradient(135deg, #1c1c1a, #2D2D29)",
        "gradient-hero": "linear-gradient(135deg, #1c1c1a 0%, #2D2D29 50%, #006B30 100%)",
      },
      animation: {
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.4s ease-out",
        "pulse-soft": "pulseSoft 2s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.6" },
        },
      },
    },
  },
  plugins: [
    require("tailwindcss-animate"),
    require("@tailwindcss/typography"),
    require("@tailwindcss/forms"),
  ],
} satisfies Config;
```

### 6.2 Variables CSS (`src/styles/globals.css`)

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 240 10% 11%;
    --primary: 144 100% 29%;
    --primary-foreground: 0 0% 100%;
    --muted: 60 6% 92%;
    --muted-foreground: 240 4% 38%;
    --border: 0 0% 90%;
    --ring: 144 100% 29%;
    --radius: 0.75rem;
  }

  body {
    @apply bg-white text-ink font-sans antialiased;
  }
}

@layer components {
  .container-page {
    @apply mx-auto max-w-7xl px-4 sm:px-6 lg:px-8;
  }
}
```

### 6.3 Composant Button avec CVA

```tsx
// packages/ui/src/Button.tsx
import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "./utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none",
  {
    variants: {
      variant: {
        primary: "bg-primary text-white hover:bg-primary-600 active:bg-primary-700",
        secondary: "bg-ink text-white hover:bg-ink-soft",
        outline: "border border-border bg-white text-ink hover:bg-surface",
        ghost: "text-ink hover:bg-surface",
        destructive: "bg-error text-white hover:bg-error/90",
      },
      size: {
        sm: "h-8 px-3 text-xs",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, loading, leftIcon, rightIcon, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    >
      {loading ? <Loader2 className="size-4 animate-spin" /> : leftIcon}
      {children}
      {!loading && rightIcon}
    </button>
  ),
);
Button.displayName = "Button";
```

---

## 7. Routing

### 7.1 Admin — `src/routes/index.tsx`

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { lazy, Suspense } from "react";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { Spinner } from "@gotaxi/ui";

const Layout = lazy(() => import("./_layout"));
const Dashboard = lazy(() => import("./dashboard"));
const Fleet = lazy(() => import("./fleet"));
const Users = lazy(() => import("./users"));
const UserDetail = lazy(() => import("./users/[id]"));
const Chauffeurs = lazy(() => import("./chauffeurs"));
const KycPending = lazy(() => import("./chauffeurs/kyc-pending"));
const Voyages = lazy(() => import("./voyages"));
const VoyageDetail = lazy(() => import("./voyages/[id]"));
const Colis = lazy(() => import("./colis"));
const ColisPending = lazy(() => import("./colis/pending"));
const ColisInTransit = lazy(() => import("./colis/in-transit"));
const Transactions = lazy(() => import("./transactions"));
const Reviews = lazy(() => import("./reviews"));
const Disputes = lazy(() => import("./reviews/disputes"));
const Audit = lazy(() => import("./audit"));
const Settings = lazy(() => import("./settings"));
const Login = lazy(() => import("./login"));

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  {
    path: "/",
    element: (
      <ProtectedRoute>
        <Layout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <Dashboard /> },
      { path: "fleet", element: <Fleet /> },
      { path: "users", element: <Users /> },
      { path: "users/:id", element: <UserDetail /> },
      { path: "chauffeurs", element: <Chauffeurs /> },
      { path: "chauffeurs/kyc-pending", element: <KycPending /> },
      { path: "voyages", element: <Voyages /> },
      { path: "voyages/:id", element: <VoyageDetail /> },
      { path: "colis", element: <Colis /> },
      { path: "colis/pending", element: <ColisPending /> },
      { path: "colis/in-transit", element: <ColisInTransit /> },
      { path: "transactions", element: <Transactions /> },
      { path: "reviews", element: <Reviews /> },
      { path: "reviews/disputes", element: <Disputes /> },
      {
        path: "audit",
        element: (
          <ProtectedRoute requireRole="SUPER_ADMIN">
            <Audit />
          </ProtectedRoute>
        ),
      },
      { path: "settings", element: <Settings /> },
    ],
  },
]);

export const AppRouter = () => (
  <Suspense fallback={<Spinner fullScreen />}>
    <RouterProvider router={router} />
  </Suspense>
);
```

### 7.2 Layout admin (`src/routes/_layout.tsx`)

```tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/layout/Sidebar";
import { Header } from "@/components/layout/Header";

export default function AdminLayout() {
  return (
    <div className="flex h-screen bg-surface-alt">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
```

### 7.3 Protected route

```tsx
// src/components/layout/ProtectedRoute.tsx
import { Navigate, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/authStore";
import type { UserRole } from "@/types/api";

interface Props {
  children: React.ReactNode;
  requireRole?: UserRole;
}

export const ProtectedRoute = ({ children, requireRole }: Props) => {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (requireRole && user?.role !== requireRole && user?.role !== "SUPER_ADMIN") {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
};
```

---

## 8. Authentification admin

### 8.1 Auth store

```typescript
// src/stores/authStore.ts
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { authApi } from "@/lib/api";
import type { AdminUser } from "@/types/api";

interface AuthState {
  user: AdminUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,

      login: async (email, password) => {
        const { user, access_token } = await authApi.adminLogin({ email, password });
        if (!["ADMIN", "SUPER_ADMIN"].includes(user.role)) {
          throw new Error("Accès refusé : compte non administrateur");
        }
        set({ user, accessToken: access_token, isAuthenticated: true });
      },

      logout: () => {
        set({ user: null, accessToken: null, isAuthenticated: false });
        window.location.href = "/login";
      },

      refresh: async () => {
        try {
          const { access_token } = await authApi.refresh();
          set({ accessToken: access_token });
        } catch {
          get().logout();
        }
      },
    }),
    {
      name: "gotaxi-admin-auth",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        isAuthenticated: state.isAuthenticated,
      }),
    },
  ),
);
```

### 8.2 Page de login

```tsx
// src/routes/login.tsx
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate, useLocation } from "react-router-dom";
import { Button, Input } from "@gotaxi/ui";
import { useAuthStore } from "@/stores/authStore";
import { toast } from "sonner";

const schema = z.object({
  email: z.string().email("Email invalide"),
  password: z.string().min(8, "8 caractères minimum"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: Location })?.from?.pathname ?? "/";

  const { register, handleSubmit, formState: { errors, isSubmitting } } =
    useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    try {
      await login(data.email, data.password);
      toast.success("Connexion réussie");
      navigate(from, { replace: true });
    } catch (e: any) {
      toast.error(e.message ?? "Identifiants invalides");
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-hero p-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-elevated">
        <div className="mb-6 flex items-center gap-2">
          <Logo size={32} />
          <span className="text-xl font-bold">
            Go<span className="text-primary">Taxi</span>{" "}
            <span className="text-xs text-muted-foreground">ADMIN</span>
          </span>
        </div>
        <h1 className="text-2xl font-extrabold">Bienvenue 👋</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Connectez-vous au tableau de bord administrateur
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <Input
            label="Email"
            type="email"
            placeholder="admin@gotaxi.bj"
            error={errors.email?.message}
            {...register("email")}
          />
          <Input
            label="Mot de passe"
            type="password"
            error={errors.password?.message}
            {...register("password")}
          />
          <Button type="submit" loading={isSubmitting} className="w-full">
            Se connecter
          </Button>
        </form>
      </div>
    </div>
  );
}
```

---

## 9. Couche API & data fetching

### 9.1 Client Axios

```typescript
// src/lib/api.ts
import axios from "axios";
import { useAuthStore } from "@/stores/authStore";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 15_000,
});

apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let isRefreshing = false;
apiClient.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      if (!isRefreshing) {
        isRefreshing = true;
        await useAuthStore.getState().refresh();
        isRefreshing = false;
      }
      return apiClient(original);
    }
    return Promise.reject(error);
  },
);

// Typed endpoints
export const dashboardApi = {
  getOverview: () =>
    apiClient.get("/admin/dashboard/overview").then((r) => r.data),
  getRevenus: (period: "7d" | "30d" | "90d") =>
    apiClient.get(`/admin/dashboard/revenus?period=${period}`).then((r) => r.data),
  getTopRoutes: () =>
    apiClient.get("/admin/dashboard/top-trajets").then((r) => r.data),
  getActivityFeed: () =>
    apiClient.get("/admin/dashboard/activity-feed").then((r) => r.data),
  getMoMoStats: () =>
    apiClient.get("/admin/dashboard/momo-stats").then((r) => r.data),
};

export const usersApi = {
  list: (params: UsersListParams) =>
    apiClient.get("/admin/users", { params }).then((r) => r.data),
  detail: (id: string) =>
    apiClient.get(`/admin/users/${id}`).then((r) => r.data),
  suspend: (id: string, reason: string) =>
    apiClient.post(`/admin/users/${id}/suspend`, { reason }).then((r) => r.data),
  activate: (id: string) =>
    apiClient.post(`/admin/users/${id}/activate`).then((r) => r.data),
};

export const colisApi = {
  pending: () =>
    apiClient.get("/admin/colis/pending").then((r) => r.data),
  inTransit: () =>
    apiClient.get("/admin/colis/in-transit").then((r) => r.data),
  validate: (id: string) =>
    apiClient.post(`/admin/colis/${id}/validate`).then((r) => r.data),
  reject: (id: string, reason: string) =>
    apiClient.post(`/admin/colis/${id}/reject`, { reason }).then((r) => r.data),
  assign: (id: string, chauffeurId: string) =>
    apiClient.post(`/admin/colis/${id}/assign`, { chauffeur_id: chauffeurId }).then((r) => r.data),
  autoAssign: (id: string) =>
    apiClient.post(`/admin/colis/${id}/auto-assign`).then((r) => r.data),
};

// ... même pattern pour transactions, reviews, audit, etc.
```

### 9.2 Setup TanStack Query

```tsx
// src/main.tsx
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { Toaster } from "sonner";
import { AppRouter } from "./routes";
import "./styles/globals.css";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      retry: 2,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <AppRouter />
    <Toaster richColors position="top-right" />
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>,
);
```

### 9.3 Hooks TanStack Query

```typescript
// src/hooks/useDashboard.ts
import { useQuery } from "@tanstack/react-query";
import { dashboardApi } from "@/lib/api";

export const useDashboardOverview = () =>
  useQuery({
    queryKey: ["dashboard", "overview"],
    queryFn: dashboardApi.getOverview,
    refetchInterval: 30_000,
  });

export const useRevenuesTrend = (period: "7d" | "30d" | "90d") =>
  useQuery({
    queryKey: ["dashboard", "revenus", period],
    queryFn: () => dashboardApi.getRevenus(period),
    staleTime: 5 * 60_000,
  });

export const useActivityFeed = () =>
  useQuery({
    queryKey: ["dashboard", "activity"],
    queryFn: dashboardApi.getActivityFeed,
    refetchInterval: 10_000,
  });
```

---

## 10. Landing page — pages détaillées

### 10.1 Layout (`apps/landing/src/routes/_layout.tsx`)

```tsx
import { Outlet } from "react-router-dom";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function LandingLayout() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}
```

### 10.2 Page d'accueil (`home.tsx`)

Structure :
- **Hero section** (gradient noir → vert) avec H1 dégradé, search bar, badges stats
- **Features grid** : 3 cartes (Suivi GPS / Mobile Money / Chauffeurs vérifiés)
- **Comment ça marche** : 4 étapes (Cherchez / Réservez / Suivez / Voyagez)
- **Section colis** : présentation envoi de colis
- **Témoignages** : 3 cartes utilisateurs
- **CTA chauffeur** : split layout (texte + témoignage chauffeur)
- **CTA téléchargement app** : QR code + boutons stores

```tsx
// apps/landing/src/routes/home.tsx
import { Helmet } from "react-helmet-async";
import { HeroSection } from "@/components/home/HeroSection";
import { FeaturesGrid } from "@/components/home/FeaturesGrid";
import { HowItWorks } from "@/components/home/HowItWorks";
import { ColisSection } from "@/components/home/ColisSection";
import { Testimonials } from "@/components/home/Testimonials";
import { DriverCTA } from "@/components/home/DriverCTA";
import { DownloadApp } from "@/components/home/DownloadApp";

export default function HomePage() {
  return (
    <>
      <Helmet>
        <title>GoTaxi — Votre course. Votre colis. En un clic.</title>
        <meta
          name="description"
          content="Plateforme de transport interurbain et livraison de colis au Bénin et au Togo. Chauffeurs vérifiés, paiement Mobile Money, suivi GPS temps réel."
        />
      </Helmet>
      <HeroSection />
      <FeaturesGrid />
      <HowItWorks />
      <ColisSection />
      <Testimonials />
      <DriverCTA />
      <DownloadApp />
    </>
  );
}
```

### 10.3 HeroSection avec search bar fonctionnelle

```tsx
// apps/landing/src/components/home/HeroSection.tsx
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import { motion } from "framer-motion";
import { Button } from "@gotaxi/ui";
import { Search, MapPin } from "lucide-react";

export function HeroSection() {
  const navigate = useNavigate();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/search?from=${from}&to=${to}`);
  };

  return (
    <section className="relative overflow-hidden bg-gradient-hero py-20 lg:py-32">
      <div className="absolute -right-20 -top-20 size-96 rounded-full bg-primary/40 blur-3xl" />
      <div className="absolute -bottom-32 -left-20 size-80 rounded-full bg-accent-yellow/15 blur-3xl" />
      <div className="container-page relative z-10 grid items-center gap-12 lg:grid-cols-[1.3fr_1fr]">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-primary-400/40 bg-primary-400/20 px-4 py-1.5 text-xs font-semibold text-white">
            🚀 Disponible au Bénin · Togo · Côte d'Ivoire bientôt
          </span>
          <h1 className="mt-5 text-5xl font-extrabold leading-tight tracking-tight text-white lg:text-7xl">
            Votre course.<br />
            Votre colis.<br />
            <span className="bg-gradient-to-r from-primary-400 to-accent-yellow bg-clip-text text-transparent">
              En un clic.
            </span>
          </h1>
          <p className="mt-5 max-w-xl text-lg text-white/85">
            Le réseau de transport interurbain et de livraison de colis le plus fiable
            d'Afrique de l'Ouest.
          </p>

          <form
            onSubmit={handleSearch}
            className="mt-8 flex flex-col gap-2 rounded-2xl bg-white p-3 shadow-elevated md:flex-row"
          >
            <div className="flex flex-1 items-center gap-2 rounded-xl bg-surface px-3 py-2">
              <span className="size-2 rounded-full bg-primary" />
              <div className="flex-1">
                <p className="text-2xs text-muted-foreground">DE</p>
                <input
                  type="text"
                  placeholder="Cotonou"
                  value={from}
                  onChange={(e) => setFrom(e.target.value)}
                  className="w-full bg-transparent text-sm font-bold outline-none"
                />
              </div>
            </div>
            <div className="flex flex-1 items-center gap-2 rounded-xl bg-surface px-3 py-2">
              <span className="size-2 rounded-full bg-error" />
              <div className="flex-1">
                <p className="text-2xs text-muted-foreground">À</p>
                <input
                  type="text"
                  placeholder="Parakou"
                  value={to}
                  onChange={(e) => setTo(e.target.value)}
                  className="w-full bg-transparent text-sm font-bold outline-none"
                />
              </div>
            </div>
            <Button type="submit" size="lg" leftIcon={<Search className="size-4" />}>
              Chercher
            </Button>
          </form>

          <div className="mt-6 flex flex-wrap gap-3">
            <a href="https://apps.apple.com/..." target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-ink hover:shadow-soft">
              <span className="text-xl"></span>
              <div className="text-left">
                <p className="text-2xs text-muted-foreground">Télécharger sur</p>
                <p className="text-sm font-extrabold">App Store</p>
              </div>
            </a>
            <a href="https://play.google.com/..." target="_blank" rel="noreferrer" className="flex items-center gap-2 rounded-xl bg-white px-4 py-3 text-ink hover:shadow-soft">
              <span className="text-xl">▶</span>
              <div className="text-left">
                <p className="text-2xs text-muted-foreground">Disponible sur</p>
                <p className="text-sm font-extrabold">Google Play</p>
              </div>
            </a>
          </div>

          <div className="mt-8 flex gap-6">
            <Stat value="50K+" label="Trajets effectués" />
            <Stat value="1 200+" label="Chauffeurs vérifiés" />
            <Stat value="⭐ 4.9" label="Note moyenne" />
          </div>
        </motion.div>

        <PhoneMockup />
      </div>
    </section>
  );
}

const Stat = ({ value, label }: { value: string; label: string }) => (
  <div>
    <p className="text-2xl font-extrabold text-accent-yellow lg:text-3xl">{value}</p>
    <p className="text-xs text-white/85">{label}</p>
  </div>
);
```

### 10.4 Page suivi public colis (`track/[reference].tsx`)

Cas d'usage : un destinataire reçoit un SMS avec une référence, il peut suivre **sans compte**.

```tsx
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { colisApi } from "@/lib/api";
import { TrackingTimeline } from "@/components/track/TrackingTimeline";
import { Spinner } from "@gotaxi/ui";

export default function TrackPage() {
  const { reference } = useParams<{ reference: string }>();
  const { data, isLoading } = useQuery({
    queryKey: ["public-tracking", reference],
    queryFn: () => colisApi.publicTrack(reference!),
    refetchInterval: 30_000,
  });

  if (isLoading) return <Spinner fullScreen />;
  if (!data) return <NotFound message="Colis introuvable" />;

  return (
    <div className="container-page py-12">
      <h1 className="text-3xl font-extrabold">Suivi du colis</h1>
      <p className="mt-2 text-muted-foreground">
        Référence : <strong>{data.reference}</strong>
      </p>
      <div className="mt-6 grid gap-6 md:grid-cols-[1fr_320px]">
        <TrackingTimeline events={data.suivi} currentStatus={data.statut} />
        <ColisSummary colis={data} />
      </div>
    </div>
  );
}
```

### 10.5 Pages secondaires

Liste complète :

| Route | Description | Notes |
|-------|-------------|-------|
| `/voyager` | Page produit voyageurs | Sections : avantages, étapes, FAQ |
| `/colis` | Page produit colis | Idem + calculateur prix interactif |
| `/chauffeur` | Recrutement chauffeurs | Formulaire candidature, calculateur revenus |
| `/tarifs` | Grille tarifaire | Tableau des prix par trajet populaire |
| `/about` | À propos GoTaxi | Histoire, équipe, valeurs |
| `/help` | Centre d'aide | Catégories d'articles |
| `/help/[slug]` | Article d'aide | Markdown rendu |
| `/legal/cgu` | CGU | Markdown |
| `/legal/privacy` | Confidentialité | Markdown |
| `/legal/cookies` | Cookies | Markdown |
| `/track/[reference]` | Suivi public colis | Refresh 30s |
| `/search` | Recherche rapide trajets | Redirige vers app si possible |

---

## 11. Dashboard admin — pages détaillées

### 11.1 Sidebar (`components/layout/Sidebar.tsx`)

```tsx
import { NavLink } from "react-router-dom";
import { cn } from "@gotaxi/ui";
import {
  LayoutDashboard, Map, Users, Car, Route as RouteIcon, Package,
  CreditCard, Wallet, Star, Lock, Settings, ChevronRight,
} from "lucide-react";
import { useDashboardCounters } from "@/hooks/useDashboard";
import { useAuthStore } from "@/stores/authStore";

const sections = [
  {
    title: "PILOTAGE",
    items: [
      { to: "/", icon: LayoutDashboard, label: "Vue d'ensemble" },
      { to: "/fleet", icon: Map, label: "Carte flotte" },
    ],
  },
  {
    title: "GESTION",
    items: [
      { to: "/users", icon: Users, label: "Utilisateurs", counterKey: "kycPending" },
      { to: "/chauffeurs", icon: Car, label: "Chauffeurs" },
      { to: "/voyages", icon: RouteIcon, label: "Voyages" },
      { to: "/colis", icon: Package, label: "Colis", counterKey: "colisPending" },
    ],
  },
  {
    title: "FINANCES",
    items: [
      { to: "/transactions", icon: CreditCard, label: "Transactions" },
      { to: "/wallets", icon: Wallet, label: "Wallets" },
    ],
  },
  {
    title: "AUTRE",
    items: [
      { to: "/reviews", icon: Star, label: "Avis & litiges" },
      { to: "/audit", icon: Lock, label: "Audit", requireRole: "SUPER_ADMIN" },
      { to: "/settings", icon: Settings, label: "Paramètres" },
    ],
  },
];

export function Sidebar() {
  const { data: counters } = useDashboardCounters();
  const user = useAuthStore((s) => s.user);

  return (
    <aside className="flex w-60 flex-col bg-ink text-white">
      <div className="flex items-center gap-2 px-5 py-5">
        <Logo />
        <span className="text-base font-extrabold">
          Go<span className="text-primary-400">Taxi</span>{" "}
          <span className="ml-1 rounded-md bg-white/10 px-1.5 py-0.5 text-2xs">ADMIN</span>
        </span>
      </div>
      <nav className="flex-1 space-y-6 px-3 pb-3">
        {sections.map((section) => (
          <div key={section.title}>
            <p className="mb-2 px-3 text-2xs font-bold tracking-wider text-white/40">
              {section.title}
            </p>
            {section.items
              .filter((it) => !it.requireRole || it.requireRole === user?.role)
              .map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors",
                      isActive
                        ? "border-l-[3px] border-primary-400 bg-primary/15 font-semibold"
                        : "opacity-70 hover:opacity-100",
                    )
                  }
                >
                  <item.icon className="size-4" />
                  <span className="flex-1">{item.label}</span>
                  {item.counterKey && counters?.[item.counterKey] && (
                    <span className="rounded-md bg-error px-1.5 py-0.5 text-2xs font-bold">
                      {counters[item.counterKey]}
                    </span>
                  )}
                </NavLink>
              ))}
          </div>
        ))}
      </nav>
      <UserProfileDropdown />
    </aside>
  );
}
```

### 11.2 Vue d'ensemble (`dashboard.tsx`)

```tsx
import { PageHeader } from "@/components/layout/PageHeader";
import { KPICard } from "@/components/dashboard/KPICard";
import { RevenueChart } from "@/components/dashboard/RevenueChart";
import { TopRoutesList } from "@/components/dashboard/TopRoutesList";
import { ActivityFeed } from "@/components/dashboard/ActivityFeed";
import { MoMoBreakdown } from "@/components/dashboard/MoMoBreakdown";
import { useDashboardOverview } from "@/hooks/useDashboard";
import { Button } from "@gotaxi/ui";
import { Bell, Plus } from "lucide-react";

export default function DashboardPage() {
  const { data, isLoading } = useDashboardOverview();

  return (
    <>
      <PageHeader
        title="Bonjour, Adelin 👋"
        subtitle="Voici ce qui se passe sur GoTaxi aujourd'hui"
        actions={
          <>
            <DateRangePicker />
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="size-4" />
              <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-error ring-2 ring-white" />
            </Button>
            <Button leftIcon={<Plus className="size-4" />}>Nouvelle action</Button>
          </>
        }
      />

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard
          variant="dark"
          label="REVENUS DU JOUR"
          value={`${formatNumber(data?.revenusJour ?? 0)} F`}
          delta="+12.5% vs hier"
          loading={isLoading}
        />
        <KPICard label="COURSES ACTIVES" value={data?.coursesActives ?? 0} sublabel={`${data?.coursesEnRoute} en route`} />
        <KPICard label="COLIS EN COURS" value={data?.colisEnCours ?? 0} sublabel={`⚠ ${data?.colisPending} en attente`} sublabelColor="warning" />
        <KPICard label="CHAUFFEURS ACTIFS" value={`${data?.chauffeursOnline}/${data?.chauffeursTotal}`} sublabel={`${data?.chauffeursPctOnline}% en ligne`} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1.5fr_1fr]">
        <RevenueChart />
        <TopRoutesList />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ActivityFeed />
        <MoMoBreakdown />
      </div>
    </>
  );
}
```

### 11.3 RevenueChart avec Recharts

```tsx
// src/components/dashboard/RevenueChart.tsx
import { useState } from "react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer } from "recharts";
import { Card, Tabs } from "@gotaxi/ui";
import { useRevenuesTrend } from "@/hooks/useDashboard";

export function RevenueChart() {
  const [period, setPeriod] = useState<"7d" | "30d" | "90d">("7d");
  const { data, isLoading } = useRevenuesTrend(period);

  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-bold">Évolution des revenus</p>
          <p className="text-xs text-muted-foreground">
            7 derniers jours · en milliers de FCFA
          </p>
        </div>
        <Tabs value={period} onValueChange={(v) => setPeriod(v as any)}>
          <Tabs.List>
            <Tabs.Trigger value="7d">7j</Tabs.Trigger>
            <Tabs.Trigger value="30d">30j</Tabs.Trigger>
            <Tabs.Trigger value="90d">90j</Tabs.Trigger>
          </Tabs.List>
        </Tabs>
      </div>

      {isLoading ? (
        <div className="h-[180px]" />
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={data?.points ?? []} margin={{ top: 8, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="grad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00C957" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#00C957" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F1EFE8" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={9} />
            <YAxis tickLine={false} axisLine={false} fontSize={9} />
            <Tooltip
              content={({ active, payload }) =>
                active && payload?.[0] ? (
                  <div className="rounded-lg bg-ink px-3 py-2 text-xs text-white">
                    <strong>{(payload[0].value as number).toLocaleString()} K F</strong>
                  </div>
                ) : null
              }
            />
            <Area type="monotone" dataKey="value" stroke="#009542" strokeWidth={2.5} fill="url(#grad)" />
          </AreaChart>
        </ResponsiveContainer>
      )}

      <div className="mt-4 grid grid-cols-3 gap-3 border-t border-dashed border-border pt-3">
        <Stat label="Total semaine" value={`${data?.totalSemaine ?? "—"}`} />
        <Stat label="Trajets" value={`${data?.totalTrajets ?? "—"}`} />
        <Stat label="Colis" value={`${data?.totalColis ?? "—"}`} />
      </div>
    </Card>
  );
}
```

### 11.4 Carte flotte temps réel (`fleet.tsx`)

```tsx
import { useState } from "react";
import Map, { Marker, Popup, NavigationControl } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import { useFleet } from "@/hooks/useFleet";
import { ActiveTripsPanel } from "@/components/fleet/ActiveTripsPanel";
import { MapLegend } from "@/components/fleet/MapLegend";
import { DriverMarker } from "@/components/fleet/DriverMarker";

export default function FleetPage() {
  const { drivers, trips, summary } = useFleet();
  const [selectedDriver, setSelectedDriver] = useState<string | null>(null);

  return (
    <div className="-m-6 lg:-m-8 flex h-[calc(100vh-64px)]">
      <div className="relative flex-1">
        <Map
          mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
          initialViewState={{ longitude: 2.3912, latitude: 6.3703, zoom: 7 }}
          style={{ width: "100%", height: "100%" }}
          mapStyle="mapbox://styles/mapbox/light-v11"
        >
          <NavigationControl position="bottom-right" />
          <MapLegend className="absolute right-4 top-4" />

          {drivers.map((driver) => (
            <Marker
              key={driver.id}
              longitude={driver.lng}
              latitude={driver.lat}
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                setSelectedDriver(driver.id);
              }}
            >
              <DriverMarker driver={driver} />
            </Marker>
          ))}

          {selectedDriver && (
            <Popup
              longitude={drivers.find((d) => d.id === selectedDriver)!.lng}
              latitude={drivers.find((d) => d.id === selectedDriver)!.lat}
              onClose={() => setSelectedDriver(null)}
            >
              <DriverPopupCard driver={drivers.find((d) => d.id === selectedDriver)!} />
            </Popup>
          )}
        </Map>

        <SummaryBox summary={summary} className="absolute bottom-4 left-4" />
      </div>
      <ActiveTripsPanel trips={trips} className="w-80 border-l border-border bg-surface" />
    </div>
  );
}
```

### 11.5 Pages détaillées (résumé)

| Page | Route | Composants clés |
|------|-------|-----------------|
| **Vue d'ensemble** | `/` | KPICard × 4, RevenueChart, TopRoutesList, ActivityFeed, MoMoBreakdown |
| **Carte flotte** | `/fleet` | FleetMap (Mapbox), ActiveTripsPanel, MapLegend, DriverMarker |
| **Utilisateurs** | `/users` | UsersTable (TanStack Table), filters, recherche, export CSV |
| **Détail user** | `/users/:id` | UserProfile, Tabs (trajets, colis, transactions, avis) |
| **Chauffeurs** | `/chauffeurs` | Pareil que users + filtres KYC |
| **KYC pending** | `/chauffeurs/kyc-pending` | Liste + drawer de validation (preview docs) |
| **Voyages** | `/voyages` | VoyagesTable + statuts |
| **Détail voyage** | `/voyages/:id` | Carte itinéraire, timeline, passagers, colis embarqués, actions |
| **Colis pending** | `/colis/pending` | Cards à valider avec assignment suggestions |
| **Colis in-transit** | `/colis/in-transit` | Table avec progression bar |
| **Transactions** | `/transactions` | Volume KPIs + opérateurs + table tx |
| **Avis** | `/reviews` | Liste avec filtres signalés |
| **Litiges** | `/reviews/disputes` | Cards d'arbitrage avec pièces jointes |
| **Audit** | `/audit` | Logs immutables (paginés + filters) |
| **Settings** | `/settings` | Paramètres système, équipe, intégrations |

---

## 12. Composants partagés

### 12.1 KPICard

```tsx
// src/components/dashboard/KPICard.tsx
import { cn } from "@gotaxi/ui";

interface KPICardProps {
  label: string;
  value: React.ReactNode;
  sublabel?: React.ReactNode;
  sublabelColor?: "default" | "success" | "warning" | "error";
  delta?: string;
  variant?: "light" | "dark";
  loading?: boolean;
  icon?: React.ReactNode;
}

export function KPICard({
  label, value, sublabel, sublabelColor = "default", delta, variant = "light", loading, icon,
}: KPICardProps) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl p-4",
        variant === "dark"
          ? "bg-gradient-dark text-white"
          : "border border-border bg-white",
      )}
    >
      {variant === "dark" && (
        <div className="absolute -right-5 -top-5 size-20 rounded-full bg-primary-400/30 blur-2xl" />
      )}
      <div className="relative">
        <div className="flex items-center justify-between">
          <p className={cn(
            "text-2xs font-semibold tracking-wider",
            variant === "dark" ? "text-white/70" : "text-muted-foreground",
          )}>
            {label}
          </p>
          {icon}
        </div>
        {loading ? (
          <Skeleton className="mt-2 h-8 w-24" />
        ) : (
          <p className="mt-1 text-2xl font-extrabold lg:text-3xl">{value}</p>
        )}
        {delta && (
          <p className="mt-1 text-2xs font-semibold text-primary-400">↗ {delta}</p>
        )}
        {sublabel && (
          <p
            className={cn(
              "mt-1 text-2xs font-semibold",
              sublabelColor === "success" && "text-success",
              sublabelColor === "warning" && "text-warning-text",
              sublabelColor === "error" && "text-error-text",
              sublabelColor === "default" && "text-muted-foreground",
            )}
          >
            {sublabel}
          </p>
        )}
      </div>
    </div>
  );
}
```

### 12.2 DataTable réutilisable

Pour toutes les tables admin (utilisateurs, transactions, colis), utiliser **TanStack Table** :

```tsx
// src/components/ui/DataTable.tsx
import {
  useReactTable, getCoreRowModel, getPaginationRowModel,
  getSortedRowModel, getFilteredRowModel, flexRender,
  type ColumnDef, type SortingState,
} from "@tanstack/react-table";
import { useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

interface DataTableProps<T> {
  data: T[];
  columns: ColumnDef<T, any>[];
  searchPlaceholder?: string;
  onRowClick?: (row: T) => void;
  pageSize?: number;
}

export function DataTable<T>({
  data, columns, searchPlaceholder, onRowClick, pageSize = 10,
}: DataTableProps<T>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data,
    columns,
    state: { sorting, globalFilter },
    onSortingChange: setSorting,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    initialState: { pagination: { pageSize } },
  });

  return (
    <div className="rounded-2xl border border-border bg-white">
      {searchPlaceholder && (
        <div className="border-b border-border p-3">
          <input
            placeholder={searchPlaceholder}
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="w-full rounded-lg bg-surface px-3 py-2 text-sm outline-none"
          />
        </div>
      )}
      <table className="w-full text-sm">
        <thead className="bg-surface">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => (
                <th
                  key={header.id}
                  onClick={header.column.getToggleSortingHandler()}
                  className="cursor-pointer p-3 text-left text-2xs font-bold uppercase tracking-wider text-muted-foreground"
                >
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick?.(row.original)}
              className="cursor-pointer border-b border-border last:border-0 hover:bg-surface"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="p-3">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <Pagination table={table} />
    </div>
  );
}
```

---

## 13. Cartes & géolocalisation

### 13.1 Mapbox setup (admin)

Pour le dashboard, **Mapbox GL JS** est préférable à Google Maps pour :
- Performances supérieures avec beaucoup de markers
- Customisation du style
- Heatmaps natifs
- Coût plus prévisible

```tsx
// src/components/fleet/FleetMap.tsx
import Map, { Marker, Source, Layer } from "react-map-gl";
import "mapbox-gl/dist/mapbox-gl.css";

const MAP_STYLE = "mapbox://styles/mapbox/light-v11";

export function FleetMap({ drivers, trips, onSelectDriver }: FleetMapProps) {
  return (
    <Map
      mapboxAccessToken={import.meta.env.VITE_MAPBOX_TOKEN}
      initialViewState={{ longitude: 2.3912, latitude: 6.3703, zoom: 7 }}
      mapStyle={MAP_STYLE}
      style={{ width: "100%", height: "100%" }}
    >
      {drivers.map((driver) => (
        <Marker
          key={driver.id}
          longitude={driver.lng}
          latitude={driver.lat}
          onClick={() => onSelectDriver(driver.id)}
        >
          <DriverMarker status={driver.status} />
        </Marker>
      ))}
      {trips.map((trip) => (
        <Source key={trip.id} type="geojson" data={trip.routeGeojson}>
          <Layer
            id={`trip-${trip.id}`}
            type="line"
            paint={{
              "line-color": "#FFD700",
              "line-width": 3,
              "line-dasharray": [4, 3],
            }}
          />
        </Source>
      ))}
    </Map>
  );
}
```

### 13.2 DriverMarker animé

```tsx
// src/components/fleet/DriverMarker.tsx
import { cn } from "@gotaxi/ui";

const colors = {
  available: "bg-primary",
  in_trip: "bg-accent-yellow",
  passenger_pickup: "bg-info",
  package_pickup: "bg-error",
};

export function DriverMarker({ status }: { status: keyof typeof colors }) {
  return (
    <div className="relative">
      {status !== "available" && (
        <div className={cn("absolute inset-0 -m-2 animate-ping rounded-full opacity-30", colors[status])} />
      )}
      <div className={cn("size-5 rounded-full ring-2 ring-white", colors[status])} />
    </div>
  );
}
```

---

## 14. Temps réel (WebSockets)

### 14.1 Hook `useWebSocket`

```typescript
// src/hooks/useWebSocket.ts
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/stores/authStore";

interface UseWebSocketOptions {
  onMessage?: (msg: any) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectDelay?: number;
}

export const useWebSocket = (channel: string, options: UseWebSocketOptions = {}) => {
  const { onMessage, onConnect, onDisconnect, reconnectDelay = 3000 } = options;
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    const token = useAuthStore.getState().accessToken;
    const url = `${import.meta.env.VITE_WS_URL}/${channel}?token=${token}`;

    const connect = () => {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        onConnect?.();
      };
      ws.onclose = () => {
        setIsConnected(false);
        onDisconnect?.();
        reconnectTimerRef.current = setTimeout(connect, reconnectDelay);
      };
      ws.onmessage = (event) => {
        try {
          onMessage?.(JSON.parse(event.data));
        } catch {}
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      reconnectTimerRef.current && clearTimeout(reconnectTimerRef.current);
      wsRef.current?.close();
    };
  }, [channel]);

  return {
    isConnected,
    send: (data: any) => wsRef.current?.send(JSON.stringify(data)),
  };
};
```

### 14.2 Activity Feed temps réel

```tsx
// src/components/dashboard/ActivityFeed.tsx
import { useWebSocket } from "@/hooks/useWebSocket";
import { useState } from "react";
import { useActivityFeed } from "@/hooks/useDashboard";

export function ActivityFeed() {
  const { data: initial } = useActivityFeed();
  const [events, setEvents] = useState<ActivityEvent[]>([]);

  const { isConnected } = useWebSocket("admin/activity", {
    onMessage: (msg) => {
      if (msg.type === "activity") {
        setEvents((prev) => [msg.event, ...prev].slice(0, 50));
      }
    },
  });

  const allEvents = [...events, ...(initial ?? [])];

  return (
    <Card>
      <CardHeader>
        <div>
          <p className="font-bold">Activité en direct</p>
          <p className="flex items-center gap-1 text-2xs text-primary">
            <span className={cn("size-1.5 rounded-full", isConnected ? "bg-primary animate-pulse" : "bg-muted-foreground")} />
            {isConnected ? "Connecté" : "Reconnexion..."}
          </p>
        </div>
      </CardHeader>
      <CardContent>
        {allEvents.map((event) => (
          <ActivityItem key={event.id} event={event} />
        ))}
      </CardContent>
    </Card>
  );
}
```

---

## 15. Internationalisation

```typescript
// src/i18n/index.ts
import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import fr from "./fr.json";
import en from "./en.json";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: { fr: { translation: fr }, en: { translation: en } },
    fallbackLng: "fr",
    interpolation: { escapeValue: false },
    detection: { order: ["localStorage", "navigator"], caches: ["localStorage"] },
  });

export default i18n;
```

---

## 16. SEO & performance

### 16.1 Métadonnées (`react-helmet-async`)

```tsx
import { Helmet } from "react-helmet-async";

export const SEO = ({ title, description, image, url }: SEOProps) => {
  const fullTitle = title ? `${title} · GoTaxi` : "GoTaxi";
  const ogImage = image ?? "https://gotaxi.bj/og-image.png";

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:image" content={ogImage} />
      <meta property="og:url" content={url} />
      <meta name="twitter:card" content="summary_large_image" />
      <link rel="canonical" href={url} />
    </Helmet>
  );
};
```

### 16.2 Sitemap dynamique

Si SSG nécessaire, utiliser `vite-plugin-sitemap` ou pré-rendre les pages avec `vite-plugin-prerender`. Sinon générer le sitemap côté backend.

### 16.3 Performance budget

| Métrique | Cible landing | Cible admin |
|----------|---------------|-------------|
| **LCP** | < 2.0s | < 2.5s |
| **FID** | < 100ms | < 100ms |
| **CLS** | < 0.1 | < 0.1 |
| **TBT** | < 200ms | < 300ms |
| **Bundle JS initial** | < 150 KB gzip | < 250 KB gzip |
| **Lighthouse** | ≥ 95 | ≥ 90 |

### 16.4 Optimisations clés

- **Code splitting** par route (déjà via lazy)
- **Image optimization** : WebP/AVIF, lazy loading natif
- **Fonts** : preload + `font-display: swap`
- **Preload** des routes critiques
- **CDN** : Cloudflare ou Bunny pour les assets
- **HTTP/3** activé sur le serveur

---

## 17. Tests

### 17.1 Tests unitaires (Vitest)

```typescript
// src/components/__tests__/KPICard.test.tsx
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { KPICard } from "../dashboard/KPICard";

describe("<KPICard />", () => {
  it("affiche le label et la valeur", () => {
    render(<KPICard label="REVENUS" value="847K F" />);
    expect(screen.getByText("REVENUS")).toBeInTheDocument();
    expect(screen.getByText("847K F")).toBeInTheDocument();
  });

  it("affiche un skeleton en loading", () => {
    render(<KPICard label="REVENUS" value="847K F" loading />);
    expect(screen.queryByText("847K F")).not.toBeInTheDocument();
  });
});
```

### 17.2 Tests E2E (Playwright)

```typescript
// e2e/admin/dashboard.spec.ts
import { test, expect } from "@playwright/test";

test.describe("Dashboard admin", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.fill('[name="email"]', "admin@gotaxi.bj");
    await page.fill('[name="password"]', "password");
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL("/");
  });

  test("affiche les KPIs principaux", async ({ page }) => {
    await expect(page.getByText("REVENUS DU JOUR")).toBeVisible();
    await expect(page.getByText("COURSES ACTIVES")).toBeVisible();
  });

  test("navigue vers la carte flotte", async ({ page }) => {
    await page.click('text=Carte flotte');
    await expect(page).toHaveURL("/fleet");
    await expect(page.locator(".mapboxgl-canvas")).toBeVisible();
  });
});
```

---

## 18. Build & déploiement

### 18.1 CI/CD (GitHub Actions)

```yaml
# .github/workflows/web-deploy.yml
name: Deploy Web

on:
  push:
    branches: [main]
    paths: ["apps/landing/**", "apps/admin/**", "packages/**"]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20, cache: pnpm }
      - run: pnpm install --frozen-lockfile
      - run: pnpm lint
      - run: pnpm test
      - run: pnpm build

  deploy-landing:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter landing build
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          command: pages deploy apps/landing/dist --project-name=gotaxi-landing

  deploy-admin:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - uses: pnpm/action-setup@v4
      - run: pnpm install --frozen-lockfile
      - run: pnpm --filter admin build
      - uses: cloudflare/wrangler-action@v3
        with:
          apiToken: ${{ secrets.CF_API_TOKEN }}
          command: pages deploy apps/admin/dist --project-name=gotaxi-admin
```

### 18.2 Hébergement recommandé

- **Landing** : Cloudflare Pages (gratuit, CDN mondial, SSL auto)
- **Admin** : Cloudflare Pages OU Vercel OU AWS S3 + CloudFront (selon préférence DevOps)
- **Headers de sécurité** :
  - `Content-Security-Policy` strict
  - `Strict-Transport-Security` 1 an
  - `X-Frame-Options: DENY` (admin)
  - `Referrer-Policy: strict-origin-when-cross-origin`

### 18.3 Production checklist

- [ ] Variables d'environnement configurées dans Cloudflare/Vercel
- [ ] DNS pointant vers le bon hébergement (gotaxi.bj, admin.gotaxi.bj)
- [ ] SSL/TLS activé
- [ ] CSP testé (rapport-only puis enforce)
- [ ] Sentry configuré (front + sourcemaps uploadées)
- [ ] Analytics actif (GA4 ou Plausible)
- [ ] Sitemap.xml et robots.txt déployés
- [ ] Tests Lighthouse passés (≥ 95 landing)
- [ ] Tests E2E passés
- [ ] Backup en place

---

## 19. Conventions de code

### 19.1 Nommage

- **Composants** : `PascalCase`, fichier = nom du composant (`KPICard.tsx`)
- **Hooks** : `useXxx` (camelCase)
- **Utils/lib** : `camelCase`
- **Types** : `PascalCase` (suffixe `Props` pour props composants)
- **Constantes** : `UPPER_SNAKE_CASE`

### 19.2 ESLint + Prettier

```javascript
// eslint.config.js
import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactPlugin from "eslint-plugin-react";
import reactHooksPlugin from "eslint-plugin-react-hooks";
import prettierConfig from "eslint-config-prettier";

export default [
  js.configs.recommended,
  ...tseslint.configs.strict,
  {
    plugins: { react: reactPlugin, "react-hooks": reactHooksPlugin },
    settings: { react: { version: "18" } },
    rules: {
      "react/jsx-uses-react": "off",
      "react/react-in-jsx-scope": "off",
      "react-hooks/rules-of-hooks": "error",
      "react-hooks/exhaustive-deps": "warn",
      "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/consistent-type-imports": "error",
    },
  },
  prettierConfig,
];
```

### 19.3 Imports order

```typescript
// 1. React et libs externes
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

// 2. Aliases internes (@/)
import { Button, Card } from "@gotaxi/ui";
import { useAuthStore } from "@/stores/authStore";
import { dashboardApi } from "@/lib/api";

// 3. Imports relatifs
import { KPICard } from "./KPICard";
import type { KPICardProps } from "./types";
```

### 19.4 Git

- Branches : `feat/...`, `fix/...`, `chore/...`
- Commits : Conventional Commits (`feat(admin): add fleet map`)
- PRs : 1 reviewer min, capture d'écran obligatoire pour les changements UI
- Squash + merge sur `main`

---

## 🎯 Roadmap d'implémentation suggérée

### Sprint 1 (semaine 1) — Setup & fondations
- Setup monorepo pnpm + Vite × 2 apps
- Design system Tailwind + shadcn-style components
- Routing + auth admin
- Layout admin (sidebar + header)

### Sprint 2 (semaine 2) — Landing page
- Hero + search bar
- Features + how it works
- Page chauffeur + recrutement
- Page suivi public colis
- SEO + performance

### Sprint 3 (semaine 3) — Admin : pilotage
- Dashboard overview avec KPIs
- Charts (revenus, top trajets)
- Activity feed temps réel
- MoMo breakdown

### Sprint 4 (semaine 4) — Admin : carte flotte
- Mapbox setup
- Markers chauffeurs animés
- Active trips panel
- Filtres carte

### Sprint 5 (semaine 5) — Admin : gestion
- Users (table, détail, suspend)
- Chauffeurs + KYC validation
- Voyages + détail supervision

### Sprint 6 (semaine 6) — Admin : opérations
- Colis pending + assignation
- Colis in-transit
- Détail colis avec timeline

### Sprint 7 (semaine 7) — Admin : finances + modération
- Transactions table + monitoring
- Avis & litiges
- Audit logs (super admin)

### Sprint 8 (semaine 8) — Polish & déploiement
- Tests E2E
- Performance (Lighthouse)
- Sentry + monitoring
- Déploiement Cloudflare Pages
- Documentation finale

---

**Fin du guide web.** Pour le backend, voir `BACKEND_FASTAPI.md`. Pour le mobile, voir `MOBILE_REACT_NATIVE.md`.
