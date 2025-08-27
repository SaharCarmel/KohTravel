import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import SignInButton from "@/components/auth/SignInButton";
import Link from "next/link";

export default function Home() {
  return (
    <div className="full-height flex items-center justify-center bg-gradient-to-br from-slate-50 to-slate-100">
      <div className="w-full max-w-5xl px-6 py-12">
          {/* Hero Section */}
          <div className="text-center mb-8">
            <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 bg-clip-text text-transparent">
              KohTravel
            </h1>
            <p className="text-slate-600 text-xl mb-6">Your AI-powered travel companion</p>
            <div className="mb-8">
              <SignInButton />
            </div>
          </div>

          {/* Feature Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
            <Card className="group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-white/80 backdrop-blur-sm border-slate-200">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center group-hover:bg-blue-200 transition-colors">
                    💬
                  </div>
                  Chat Assistant
                </CardTitle>
                <CardDescription className="text-sm">
                  Get instant answers about your travel documents and trip planning with AI assistance
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <Link href="/chat">
                  <Button className="w-full bg-blue-600 hover:bg-blue-700">Start Chat</Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-white/80 backdrop-blur-sm border-slate-200">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="w-8 h-8 bg-green-100 rounded-lg flex items-center justify-center group-hover:bg-green-200 transition-colors">
                    📄
                  </div>
                  Documents
                </CardTitle>
                <CardDescription className="text-sm">
                  Upload, organize, and manage all your travel documents with AI-powered analysis
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <Link href="/documents">
                  <Button className="w-full bg-green-600 hover:bg-green-700">Manage Documents</Button>
                </Link>
              </CardContent>
            </Card>

            <Card className="group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-white/80 backdrop-blur-sm border-slate-200">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center group-hover:bg-purple-200 transition-colors">
                    ✈️
                  </div>
                  Plan Journey
                </CardTitle>
                <CardDescription className="text-sm">
                  Create detailed travel itineraries and discover amazing destinations
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <Button className="w-full" disabled variant="secondary">Coming Soon</Button>
              </CardContent>
            </Card>

            <Card className="group hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-white/80 backdrop-blur-sm border-slate-200">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg flex items-center gap-2">
                  <div className="w-8 h-8 bg-orange-100 rounded-lg flex items-center justify-center group-hover:bg-orange-200 transition-colors">
                    💰
                  </div>
                  Track Expenses
                </CardTitle>
                <CardDescription className="text-sm">
                  Keep track of your travel budget and expenses in real-time
                </CardDescription>
              </CardHeader>
              <CardContent className="pt-0">
                <Button variant="secondary" className="w-full" disabled>Coming Soon</Button>
              </CardContent>
            </Card>
          </div>

          {/* Footer */}
          <div className="text-center mt-8">
            <p className="text-sm text-slate-500">
              Built with Next.js, FastAPI, and deployed on Vercel
            </p>
        </div>
      </div>
    </div>
  );
}