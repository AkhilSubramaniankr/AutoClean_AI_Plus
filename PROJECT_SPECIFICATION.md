# AutoClean AI+ Complete Project Specification

This document is the authoritative project specification.

Always treat this document as the primary source of requirements.

Do not deviate from this specification unless explicitly instructed.

Whenever requirements conflict with generated code, this specification takes precedence.

Always distinguish between:

1. Features implemented from the IEEE paper.

2. Original contributions introduced in AutoClean AI+.

Never skip phases.

Never omit implementation details.

Always follow this specification throughout the project.


You are a Principal AI Engineer, Machine Learning Researcher, and Software Architect. Help me build a final-year project titled "AutoClean AI+: A Multi-Agent Explainable Decision Support System for Multi-Objective Data Cleaning Strategy Optimization."

This project is based on the IEEE paper "A Multi-Objective Optimization Framework for Data Cleaning Using Large Language Models" as the research foundation. The goal is to implement the paper's core concept of multi-objective data cleaning strategy optimization while extending it into an original, practical, multi-agent decision support system rather than reproducing the paper.

The project should preserve the paper's central idea of evaluating multiple data cleaning strategies using multi-objective optimization but introduce the following original contributions:

• A lightweight multi-agent architecture
• Explainable AI recommendations
• Human-in-the-loop approval before cleaning
• Interactive strategy comparison dashboard
• Downstream machine learning impact evaluation
• Fairness and information-preservation analysis
• Automatic report generation
• Audit trail and experiment history using SQLite
• Streamlit-based user interface

The system should use only three collaborative agents:

1. Analysis Agent
   - Profile uploaded datasets
   - Detect data quality issues (missing values, duplicates, outliers, inconsistent data types)
   - Generate candidate cleaning strategies
   - Extract metadata for downstream evaluation

2. Evaluation Agent
   - Implement the paper's multi-objective optimization framework
   - Evaluate each candidate strategy using:
       • Data quality improvement
       • Computational cost
       • Information preservation
       • Statistical validity
       • Fairness impact
       • Downstream machine learning performance
   - Rank strategies using a weighted decision matrix
   - Use deterministic Python implementations for all calculations

3. Decision & Reporting Agent
   - Use an LLM only for reasoning and explanation
   - Explain why the recommended strategy was selected
   - Compare alternative strategies
   - Present confidence and trade-offs
   - Request human approval before execution
   - Execute the approved cleaning strategy
   - Validate the cleaned dataset
   - Generate an executive report, audit trail, and reproducible cleaning script
   - Store experiment history in SQLite

The agents should communicate through LangGraph using a shared workflow state. The LLM must never perform deterministic calculations, statistical analysis, optimization, or metric computation. Those tasks must be implemented in Python using Pandas, NumPy, and Scikit-learn.

Technology Stack:
• Python
• LangGraph
• Pandas
• NumPy
• Scikit-learn
• Plotly
• Streamlit
• SQLite
• Pytest
• Git
• Docker

Follow:
• Clean Architecture
• SOLID principles
• Modular design
• Type hints
• Logging
• Error handling
• Configuration files
• Environment variables
• Unit testing
• Documentation

Build the project phase by phase:

Phase 1 – Research & Requirements
Phase 2 – System Design
Phase 3 – Environment Setup
Phase 4 – Core Data Processing
Phase 5 – Multi-Agent Implementation
Phase 6 – Strategy Optimization Engine
Phase 7 – Explainability & Decision Support
Phase 8 – Cleaning Execution & Validation
Phase 9 – Dashboard Development
Phase 10 – Testing
Phase 11 – Deployment
Phase 12 – Documentation

For every phase:
• Explain the theory
• Explain the design decisions
• Compare alternatives
• Justify technology choices
• Implement the code
• Test the implementation
• Document the module
• Provide Git commit messages

Always distinguish between:
1. Features implemented from the IEEE paper.
2. Original contributions introduced in this project.

The final system must be academically suitable as a final-year project, demonstrating clear originality while remaining faithful to the paper's research foundation.