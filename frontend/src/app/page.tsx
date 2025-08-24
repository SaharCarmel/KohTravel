import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import SignInButton from "@/components/auth/SignInButton";

export default function Home() {
  return (
    <div className="min-h-screen p-8">
      <main className="max-w-4xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold mb-4">KohTravel</h1>
          <p className="text-muted-foreground text-lg">Your travel planning companion</p>
          <div className="mt-6">
            <SignInButton />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <Card>
            <CardHeader>
              <CardTitle>Plan Your Journey</CardTitle>
              <CardDescription>Create detailed travel itineraries and discover amazing destinations</CardDescription>
            </CardHeader>
            <CardContent>
              <Button className="w-full">Start Planning</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Track Expenses</CardTitle>
              <CardDescription>Keep track of your travel budget and expenses in real-time</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" className="w-full">Manage Budget</Button>
            </CardContent>
          </Card>
        </div>

        <div className="text-center">
          <p className="text-sm text-muted-foreground">
            Built with Next.js, FastAPI, and deployed on Vercel
          </p>
        </div>
      </main>
    </div>
  );
}