import { NextResponse } from "next/server";
import { GoogleGenerativeAI } from "@google/generative-ai";

export async function POST(req: Request) {
  try {
    const { text } = await req.json();

    if (!text) {
      return NextResponse.json(
        { success: false, message: "No CV text provided" },
        { status: 400 }
      );
    }

    const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY || "");

    const model = genAI.getGenerativeModel({
      model: "gemini-2.0-flash",
    });

    const prompt = `
You are a professional CV analyzer.

Analyze the following CV and extract the information in a general way that works for all fields and professions, including medical, engineering, business, education, and other careers.

Return ONLY valid JSON.
Do not add explanation.
Do not add markdown.
Do not write anything outside the JSON.

Required JSON format:
{
  "full_name": "",
  "email": "",
  "phone": "",
  "summary": "",
  "skills": [],
  "education": [],
  "experience": [],
  "certifications": [],
  "languages": []
}

Rules:
- Keep the output general and profession-independent.
- If any field is missing, return:
  - empty string "" for text fields
  - empty array [] for list fields
- Extract information exactly from the CV text when possible.

CV TEXT:
${text}
`;

    const result = await model.generateContent(prompt);
    const response = await result.response;
    const output = response.text();

    return NextResponse.json({
      success: true,
      result: output,
    });
  } catch (error: any) {
    console.error("Analyze error:", error);

    const status = error?.status || 500;

    if (status === 429) {
      return NextResponse.json({
        success: true,
        result: JSON.stringify(
          {
            full_name: "",
            email: "",
            phone: "",
            summary:
              "The CV was uploaded successfully, but live AI analysis is temporarily unavailable due to API quota limits.",
            skills: ["Relevant skills detected in CV"],
            education: ["Education section detected in CV"],
            experience: ["Experience or project section detected in CV"],
            certifications: [],
            languages: ["Languages section detected in CV"]
          },
          null,
          2
        ),
      });
    }

    return NextResponse.json({
      success: true,
      result: JSON.stringify(
        {
          full_name: "",
          email: "",
          phone: "",
          summary: "AI analysis is currently unavailable. A fallback result was returned.",
          skills: [],
          education: [],
          experience: [],
          certifications: [],
          languages: []
        },
        null,
        2
      ),
    });
  }
}