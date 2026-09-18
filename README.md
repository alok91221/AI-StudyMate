# 📚 AI StudyMate

### Multimodal AI Study Assistant

AI StudyMate is a Generative AI-powered educational assistant that transforms textbook pages, diagrams, charts, graphs, tables, maps, formulas, and handwritten notes into structured and personalized study material.

It is designed to help students understand concepts, prepare for exams, revise important information, practice with MCQs, and ask questions about their uploaded study material.

---

## ✨ Features

### 📷 Multimodal Study Material Analysis

Upload one or multiple study images containing:

- Textbook pages
- Diagrams
- Charts
- Graphs
- Tables
- Maps
- Formulas
- Handwritten notes
- Educational illustrations

AI StudyMate analyzes the visual content using Google's Gemini multimodal AI.

---

## 🎯 Personalized Learning

Students can select:

- Class / Grade
- Subject
- Exam Type
- Difficulty Level
- Language
- Focus Mode

### Focus Modes

- ⚡ Quick Revision
- 📚 Detailed Learning
- 🎯 Exam Preparation
- 🧒 Explain Like I'm 10

Students can also provide custom instructions for the AI.

---

## 📖 Generated Study Material

AI StudyMate generates:

- Topic identification
- Important information
- Simple explanations
- Important terms and definitions
- Key concepts
- Summary
- Important examination questions
- Multiple-choice questions
- Exam revision points
- Diagram analysis
- Chart and graph analysis
- Formula analysis
- Personalized study tips

---

## 🧠 Interactive Quiz

The application converts generated MCQs into an interactive quiz.

Students can:

- Select answers
- Submit the quiz
- Receive a score
- See correct answers
- Read explanations

---

## 💬 AI Study Chat

Students can ask follow-up questions about their study material.

The chat assistant uses the generated study material as the primary context and provides explanations grounded in the uploaded content.

---

## 🔄 Regenerate Study Material

Students can regenerate the study material when they want a fresh explanation or different wording while maintaining the original learning context.

---

## 📄 PDF Export

Generated study material can be exported as a downloadable PDF for offline revision.

---

## 🤖 Gemini Model Fallback

AI StudyMate includes an automatic Gemini model fallback mechanism.

If a configured Gemini model reaches its current quota or rate limit, the application attempts the next configured model in the fallback chain.

This helps improve application availability when individual model quotas are exhausted.

---

## 🏗️ Project Architecture

```text
AI-StudyMate/
│
├── app.py
├── config.py
├── requirements.txt
├── .gitignore
│
├── services/
│   ├── __init__.py
│   ├── gemini_service.py
│   └── chat_service.py
│
├── prompts/
│   ├── __init__.py
│   ├── study_prompt.py
│   └── chat_prompt.py
│
└── utils/
    ├── __init__.py
    └── file_utils.py
