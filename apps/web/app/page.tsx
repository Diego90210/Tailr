import { Show, SignInButton, SignUpButton, UserButton } from "@clerk/nextjs";
import { Suspense } from "react";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-zinc-50 font-sans dark:bg-black">
      <h1 className="text-3xl font-semibold tracking-tight text-black dark:text-zinc-50">
        Tailr
      </h1>
      <Suspense>
        <Show when="signed-out">
          <div className="flex gap-3">
            <SignInButton />
            <SignUpButton />
          </div>
        </Show>
        <Show when="signed-in">
          <UserButton />
        </Show>
      </Suspense>
    </main>
  );
}
