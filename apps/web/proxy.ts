import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";

// Public by design: the landing page, the onboarding entry and Clerk's own screens.
// Every other route (and future /api endpoints) requires a session.
// shortcut: path matching (createRouteMatcher) is deprecated in favour of resource-based
// checks; migrate when pages start reading protected data (DATA-08 owns the real boundary).
const isPublicRoute = createRouteMatcher([
  "/",
  "/start(.*)",
  "/sign-in(.*)",
  "/sign-up(.*)",
]);

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) await auth.protect();
});

export const config = {
  matcher: [
    "/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)",
    "/(api|trpc)(.*)",
  ],
};
