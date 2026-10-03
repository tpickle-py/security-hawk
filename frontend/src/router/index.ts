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

export const router = createRouter({
  // Using hash history for seamless Home Assistant Ingress compatibility without base URL issues
  history: createWebHashHistory(),
  routes,
});
