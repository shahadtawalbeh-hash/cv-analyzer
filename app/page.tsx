export default function HomePage() {
  return (
    <main className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-8">
      <div className="w-full max-w-3xl rounded-2xl bg-white shadow-md p-10 text-center">
        <h1 className="text-4xl font-bold text-gray-900 mb-4">
          Intelligent CV Analyzer
        </h1>

        <p className="text-lg text-gray-600 mb-8">
          Upload your CV, analyze your profile, and get job recommendations.
        </p>

        <a
          href="/upload-cv"
          className="inline-block rounded-xl bg-black px-6 py-3 text-white font-medium hover:opacity-90"
        >
          Upload CV
        </a>
      </div>
    </main>
  );
}