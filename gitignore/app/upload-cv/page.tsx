"use client";

import { useState } from "react";

export default function UploadCVPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [responseMessage, setResponseMessage] = useState("");
  const [textPreview, setTextPreview] = useState("");
  const [loading, setLoading] = useState(false);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;
    setSelectedFile(file);
    setResponseMessage("");
    setTextPreview("");
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!selectedFile) {
      setResponseMessage("Please select a CV file first.");
      return;
    }

    try {
      setLoading(true);
      setResponseMessage("");
      setTextPreview("");

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
      console.log("API response:", data);
    } catch (error) {
      setResponseMessage("Something went wrong while uploading the file.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="mx-auto w-full max-w-5xl">
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            Upload Your CV
          </h1>
          <p className="text-gray-600">
            Upload a PDF CV file and preview the extracted text.
          </p>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          {/* Upload Card */}
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

              <button
                type="submit"
                disabled={loading}
                className="rounded-xl bg-black px-6 py-3 text-white font-medium hover:opacity-90 disabled:opacity-50"
              >
                {loading ? "Uploading..." : "Submit CV"}
              </button>

              {responseMessage && (
                <div className="rounded-lg bg-blue-50 border border-blue-200 p-3 text-sm text-blue-800">
                  {responseMessage}
                </div>
              )}
            </form>
          </div>

          {/* Preview Card */}
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
      </div>
    </main>
  );
}