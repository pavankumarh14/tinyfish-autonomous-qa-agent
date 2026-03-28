# config.py
# QA Workflow Definitions + App Settings

from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # TinyFish API (REQUIRED)
    TINYFISH_API_KEY: str = os.getenv("TINYFISH_API_KEY", "")

    # LLM Provider Selection (google, openai, groq, ollama)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "google")
    
    # Google Gemini API (FREE - 20 requests/day) https://aistudio.google.com/app/apikey
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # OpenAI API (FREE tier available) https://platform.openai.com
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    
    # Groq API (FREE - very fast!) https://console.groq.com
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    
    # Ollama (FREE - runs locally) https://ollama.com
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./qa_results.db")

    # Slack (optional)
    SLACK_WEBHOOK_URL: Optional[str] = os.getenv("SLACK_WEBHOOK_URL", None)

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()

# ---- QA Workflow Definitions - Target websites for monitoring ----
WORKFLOWS = [
    {
        "id": "login-check",
        "name": "Login Flow Check",
        "url": "https://practicetestautomation.com/practice-test-login/",
        "goal": """
            Go to the login page.
            Enter username: student
            Enter password: Password123
            Click the Login button.
            Check if you see a success message or are redirected to a dashboard.
            Return JSON: {"status": "PASS" or "FAIL", "message": "what happened"}
        """,
        "category": "Authentication"
    },
    {
        "id": "checkout-check",
        "name": "Checkout Flow Check",
        "url": "https://www.saucedemo.com",
        "goal": """
            Login with username: standard_user and password: secret_sauce.
            Click on the first product listed.
            Click Add to Cart.
            Click the cart icon.
            Click Checkout.
            Verify the checkout information page loads.
            Return JSON: {"status": "PASS" or "FAIL", "message": "what happened"}
        """,
        "category": "E-Commerce"
    },
    {
        "id": "form-check",
        "name": "Form Submission Check",
        "url": "https://demoqa.com/automation-practice-form",
        "goal": """
            Fill in the student registration form with:
            - First Name: Test
            - Last Name: User
            - Email: test@qaagent.com
            - Gender: Male (select the radio button)
            - Mobile Number: 9876543210
            Click Submit button.
            Check if a success confirmation modal or message appears.
            Return JSON: {"status": "PASS" or "FAIL", "message": "what happened"}
        """,
        "category": "Form Validation"
    }
]
