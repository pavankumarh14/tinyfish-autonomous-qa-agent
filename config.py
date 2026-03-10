# config.py
# QA Workflow Definitions - Target websites for monitoring

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
