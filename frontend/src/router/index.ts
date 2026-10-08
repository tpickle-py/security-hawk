import { createRouter, createWebHashHistory } from "vue-router";
import AppShell from "@/components/layout/AppShell.vue";
import KioskView from "@/components/kiosk/KioskView.vue";

const routes = [
  {
    path: "/",
    name: "home",
    component: AppShell,
  },
  {
    path: "/kiosk/:planId?",
    name: "kiosk",
    component: KioskView,
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/",
  },
];

export function isKioskMode(): boolean {
  if (typeof window === "undefined") return false;
  if ((window as any).__IS_KIOSK__ === true) return true;
  if (window.location.pathname.startsWith("/kiosk") || window.location.pathname.includes("/kiosk")) return true;
  if (window.location.port === "8100") return true;
  return false;
}

export const router = createRouter({
  // Using hash history for seamless Home Assistant Ingress compatibility without base URL issues
  history: createWebHashHistory(),
  routes,
});

router.beforeEach((to, _from, next) => {
  if (isKioskMode() && to.name !== "kiosk") {
    return next({ name: "kiosk", query: to.query, params: to.params });
  }
  next();
});

