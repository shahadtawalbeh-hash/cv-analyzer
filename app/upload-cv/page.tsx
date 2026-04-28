"use client";

import { useState } from "react";

export default function UploadCVPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [responseMessage, setResponseMessage] = useState("");
  const [textPreview, setTextPreview] = useState("");
  const [loading, setLoading] = useState(false);

  const [fullExtractedText, setFullExtractedText] = useState("");
  const [analysisResult, setAnalysisResult] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [showAnalyze, setShowAnalyze] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setResponseMessage("");
    setTextPreview("");
    setFullExtractedText("");
    setAnalysisResult("");
    setShowAnalyze(false);
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedFile) {
      setResponseMessage("Please select a CV file first.");
      return;
    }

    if (!selectedFile.name.toLowerCase().endsWith(".pdf")) {
      setResponseMessage("Please upload a PDF file only.");
      return;
    }

    try {
      setLoading(true);
      setResponseMessage("");
      setTextPreview("");
      setFullExtractedText("");
      setAnalysisResult("");
      setShowAnalyze(false);

      const formData = new FormData();
      formData.append("cv", selectedFile);

      const response = await fetch("/api/cv/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setResponseMessage(data.message || "Upload failed.");
        return;
      }

      setResponseMessage(
        `${data.message || "Upload succeeded."} Length: ${data.extractedTextLength ?? 0}`
      );
      setTextPreview(data.extractedTextPreview || "");
      setFullExtractedText(data.extractedText || "");
      setShowAnalyze(true);

      console.log("Upload API response:", data);
    } catch (error) {
      setResponseMessage("Something went wrong while uploading the file.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    if (!fullExtractedText) {
      setResponseMessage("Please upload and extract the CV first.");
      return;
    }

    try {
      setAnalyzing(true);
      setAnalysisResult("");
      setResponseMessage("");

      const response = await fetch("/api/cv/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text: fullExtractedText }),
      });

      const data = await response.json();
      console.log("Analyze response:", data);

      if (!response.ok) {
        setResponseMessage(data.message || "Failed to analyze CV");
        return;
      }

      setAnalysisResult(data.result || "No analysis returned.");
      setResponseMessage("CV analyzed successfully.");
    } catch (error) {
      console.error(error);
      setResponseMessage("Failed to analyze CV");
    } finally {
      setAnalyzing(false);
    }
  };

  const renderAnalysis = () => {
    if (!analysisResult) {
      return (
        <div className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-4 text-sm text-gray-500">
          No analysis yet. Upload a CV first, then click "Analyze CV with Gemini".
        </div>
      );
    }

    try {
      const data = JSON.parse(analysisResult);

      return (
        <div className="space-y-5 text-sm text-gray-800">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase text-gray-500 mb-1">
                Full Name
              </p>
              <p className="text-base font-medium text-gray-900">
                {data.full_name || "N/A"}
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase text-gray-500 mb-1">
                Email
              </p>
              <p className="text-base font-medium text-gray-900">
                {data.email || "N/A"}
              </p>
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase text-gray-500 mb-1">
                Phone
              </p>
              <p className="text-base font-medium text-gray-900">
                {data.phone || "N/A"}
              </p>
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase text-gray-500 mb-2">
              Summary
            </p>
            <p className="text-gray-800 leading-6">
              {data.summary || "N/A"}
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase text-gray-500 mb-2">
                Skills
              </p>
              {data.skills?.length ? (
                <ul className="list-disc ml-5 space-y-1">
                  {data.skills.map((skill: string, index: number) => (
                    <li key={index}>{skill}</li>
                  ))}
                </ul>
              ) : (
                <p>N/A</p>
              )}
            </div>

            <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
              <p className="text-xs font-semibold uppercase text-gray-500 mb-2">
                Languages
              </p>
              {data.languages?.length ? (
                <ul className="list-disc ml-5 space-y-1">
                  {data.languages.map((language: string, index: number) => (
                    <li key={index}>{language}</li>
                  ))}
                </ul>
              ) : (
                <p>N/A</p>
              )}
            </div>
          </div>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase text-gray-500 mb-2">
              Education
            </p>
            {data.education?.length ? (
              <ul className="list-disc ml-5 space-y-1">
                {data.education.map((item: string, index: number) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>N/A</p>
            )}
          </div>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase text-gray-500 mb-2">
              Experience
            </p>
            {data.experience?.length ? (
              <ul className="list-disc ml-5 space-y-1">
                {data.experience.map((item: string, index: number) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>N/A</p>
            )}
          </div>

          <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
            <p className="text-xs font-semibold uppercase text-gray-500 mb-2">
              Certifications
            </p>
            {data.certifications?.length ? (
              <ul className="list-disc ml-5 space-y-1">
                {data.certifications.map((item: string, index: number) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : (
              <p>N/A</p>
            )}
          </div>
        </div>
      );
    } catch {
      return (
        <div className="overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-4">
          <pre className="whitespace-pre-wrap break-words text-sm leading-6 text-gray-800 font-mono">
            {analysisResult}
          </pre>
        </div>
      );
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="mx-auto w-full max-w-6xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Upload Your CV
          </h1>
          <p className="text-gray-600">
            Upload a PDF CV file, preview the extracted text, then analyze it with Gemini.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl bg-white shadow-md border border-gray-200 p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              CV Upload
            </h2>

            <form className="space-y-4" onSubmit={handleSubmit}>
              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                className="block w-full rounded-lg border border-gray-300 p-3 text-sm"
              />

              {selectedFile && (
                <div className="rounded-lg bg-gray-100 p-3 text-sm text-gray-700">
                  Selected file: <strong>{selectedFile.name}</strong>
                </div>
              )}

              <div className="flex flex-wrap gap-3">
                <button
                  type="submit"
                  disabled={loading}
                  className="rounded-xl bg-black px-6 py-3 text-white font-medium hover:opacity-90 disabled:opacity-50"
                >
                  {loading ? "Uploading..." : "Submit CV"}
                </button>

                {showAnalyze && (
                  <button
                    type="button"
                    onClick={handleAnalyze}
                    disabled={analyzing}
                    className="rounded-xl bg-green-600 px-6 py-3 text-white font-medium hover:opacity-90 disabled:opacity-50"
                  >
                    {analyzing ? "Analyzing..." : "Analyze CV with Gemini"}
                  </button>
                )}
              </div>

              {responseMessage && (
                <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-800">
                  {responseMessage}
                </div>
              )}
            </form>
          </div>

          <div className="rounded-2xl bg-white shadow-md border border-gray-200 p-6">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              Extracted Text Preview
            </h2>

            {textPreview ? (
              <div className="h-[500px] overflow-auto rounded-lg border border-gray-200 bg-gray-50 p-4">
                <pre className="whitespace-pre-wrap break-words break-all text-sm leading-6 text-gray-800 font-mono">
                  {textPreview}
                </pre>
              </div>
            ) : (
              <div className="flex h-[500px] items-center justify-center rounded-lg border border-dashed border-gray-300 bg-gray-50 text-gray-500 text-sm">
                No extracted text yet. Upload a PDF file to preview the result.
              </div>
            )}
          </div>
        </div>

        <div className="mt-6 rounded-2xl bg-white shadow-md border border-gray-200 p-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">
            Gemini Analysis Result
          </h2>

          {renderAnalysis()}
        </div>
      </div>
    </main>
  );
}