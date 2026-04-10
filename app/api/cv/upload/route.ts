import { NextResponse } from "next/server";
import PDFParser from "pdf2json";

export const runtime = "nodejs";

function extractTextFromPdfJson(pdfData: any) {
  let fullText = "";

  const pages = pdfData?.Pages || [];

  for (const page of pages) {
    const texts = page.Texts || [];

    for (const textItem of texts) {
      const runs = textItem.R || [];

      for (const run of runs) {
        if (run.T) {
          fullText += decodeURIComponent(run.T) + " ";
        }
      }
    }

    fullText += "\n";
  }

  return fullText.trim();
}

function cleanExtractedText(text: string) {
  let cleaned = text;

  cleaned = cleaned.replace(/\r/g, "");
  cleaned = cleaned.replace(/[ \t]+/g, " ");
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

  cleaned = cleaned
    .split("\n")
    .map((line) => line.trim())
    .join("\n");

  cleaned = cleaned.replace(
    /\b(?:[A-Za-z]\s+){2,}[A-Za-z]\b/g,
    (match) => match.replace(/\s+/g, "")
  );

  cleaned = cleaned.replace(
    /\b(?:[A-Za-z0-9@.+#&/_-]\s+){4,}[A-Za-z0-9@.+#&/_-]\b/g,
    (match) => match.replace(/\s+/g, "")
  );

  const headings = [
    "PROFILE SUMMARY",
    "SUMMARY",
    "EDUCATION",
    "EXPERIENCE",
    "WORK EXPERIENCE",
    "SKILLS",
    "PROJECTS",
    "CERTIFICATIONS",
    "LANGUAGES",
    "CONTACT",
  ];

  for (const heading of headings) {
    const regex = new RegExp(`\\s*${heading}\\s*`, "gi");
    cleaned = cleaned.replace(regex, `\n${heading}\n`);
  }

  cleaned = cleaned.replace(
    /([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})/g,
    "\n$1\n"
  );

  cleaned = cleaned.replace(/(\+?\d[\d\s-]{7,}\d)/g, "\n$1\n");

  cleaned = cleaned.replace(/[ \t]+/g, " ");
  cleaned = cleaned.replace(/\n{3,}/g, "\n\n");

  cleaned = cleaned
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .join("\n");

  return cleaned.trim();
}

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const file = formData.get("cv") as File | null;

    if (!file) {
      return NextResponse.json(
        { success: false, message: "No file uploaded." },
        { status: 400 }
      );
    }

    if (
      file.type !== "application/pdf" &&
      !file.name.toLowerCase().endsWith(".pdf")
    ) {
      return NextResponse.json(
        {
          success: false,
          message: "Only PDF files are supported in this step.",
        },
        { status: 400 }
      );
    }

    if (file.size > 5 * 1024 * 1024) {
      return NextResponse.json(
        {
          success: false,
          message: "File size must be less than 5MB.",
        },
        { status: 400 }
      );
    }

    const bytes = await file.arrayBuffer();
    const buffer = Buffer.from(bytes);

    const extractedText = await new Promise<string>((resolve, reject) => {
      const pdfParser = new PDFParser();

      pdfParser.on("pdfParser_dataError", (errData: any) => {
        reject(errData?.parserError || new Error("PDF parsing failed."));
      });

      pdfParser.on("pdfParser_dataReady", (pdfData: any) => {
        try {
          const rawText = extractTextFromPdfJson(pdfData);
          const cleanedText = cleanExtractedText(rawText);
          resolve(cleanedText);
        } catch (error) {
          reject(error);
        }
      });

      pdfParser.parseBuffer(buffer);
    });

    console.log("Extracted text length:", extractedText.length);
    console.log("Extracted text preview:", extractedText.slice(0, 1000));

    return NextResponse.json({
      success: true,
      message: "Text extracted successfully.",
      fileName: file.name,
      extractedText,
      extractedTextPreview: extractedText.slice(0, 1000),
      extractedTextLength: extractedText.length,
    });
  } catch (error) {
    console.error("Upload error:", error);

    return NextResponse.json(
      {
        success: false,
        message: "Something went wrong while extracting text.",
      },
      { status: 500 }
    );
  }
}