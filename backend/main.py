
import pickle
import re
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(title="Fake Internship and Job Detector")

# Allow the frontend to call the backend from VS Code Live Server.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
MODEL_PATH = BASE_DIR / "job_model.pkl"

ml_model = None

try:
    with open(MODEL_PATH, "rb") as file:
        ml_model = pickle.load(file)
    print("ML model loaded successfully.")
except (OSError, pickle.PickleError, EOFError, AttributeError,
        ImportError, ValueError) as error:
    print(f"ML model could not be loaded: {error}")


class JobAd(BaseModel):
    text: str = Field(min_length=1, max_length=50000)


COMPANY_PATTERN = re.compile(
    r"\b(?:company|organisation|organization|employer|"
    r"recruiter|hiring for|careers at)\b",
    re.IGNORECASE,
)

EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

PHONE_PATTERN = re.compile(
    r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"
)

URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


RULES = [
    {
        "id": "upfront_fee",
        "title": "Upfront payment requested",
        "patterns": [
            r"\bregistration fee\b",
            r"\bpay (?:a |the )?(?:fee|amount|money)\b",
            r"\bpay to apply\b",
            r"\bapplication fee\b",
            r"\bsecurity deposit\b",
            r"\brefundable fee\b",
            r"\bpay first\b",
        ],
        "weight": 30,
        "severity": "high",
        "reason": "The advertisement appears to request money before employment.",
        "advice": "Do not pay a fee to secure a job or internship.",
    },
    {
        "id": "training_or_certificate_fee",
        "title": "Training or certificate fee",
        "patterns": [
            r"\btraining fee\b",
            r"\bcertificate fee\b",
            r"\bpay for (?:the )?certificate\b",
            r"\bmandatory paid training\b",
        ],
        "weight": 25,
        "severity": "high",
        "reason": "A payment may be required for training or certification.",
        "advice": "Verify the employer and training provider independently.",
    },
    {
        "id": "task_or_recharge_scam",
        "title": "Recharge or task payment",
        "patterns": [
            r"\brecharge (?:your )?account\b",
            r"\bcomplete tasks? to earn\b",
            r"\bdeposit money to unlock\b",
            r"\bprepaid tasks?\b",
            r"\btask recharge\b",
        ],
        "weight": 30,
        "severity": "high",
        "reason": "The text resembles a task-based payment scheme.",
        "advice": "Do not deposit money to unlock tasks or earnings.",
    },
    {
        "id": "crypto_or_gift_card_payment",
        "title": "Crypto or gift-card payment",
        "patterns": [
            r"\bpay (?:in|using|with) cryptocurrency\b",
            r"\bbuy gift cards?\b",
            r"\bpay in bitcoin\b",
            r"\bsend crypto\b",
        ],
        "weight": 25,
        "severity": "high",
        "reason": "The advertisement mentions unusual payment methods.",
        "advice": "Do not send cryptocurrency or gift-card codes to recruiters.",
    },
    {
        "id": "sensitive_credentials",
        "title": "Sensitive account information",
        
        "patterns": [
            r"\bshare your password\b",
            r"\bprovide your otp\b",
            r"\bsend your otp\b",
            r"\bshare your banking login\b",
            r"\b(?:send|share|provide)\s+(?:your\s+)?(?:bank\s+)?pin\b",
            r"\b(?:send|share|provide)\s+(?:your\s+)?(?:bank\s+)?otp\b",
            r"\bbank pin and otp\b",
        ],

        "weight": 35,
        "severity": "high",
        "reason": "The advertisement may request sensitive account credentials.",
        "advice": "Never share passwords, OTPs, or banking login details.",
    },
    {
        "id": "identity_data",
        "title": "Sensitive identity information",
        "patterns": [
            r"\bsend (?:your )?aadhaar\b",
            r"\bshare (?:your )?pan card\b",
            r"\bsubmit (?:your )?passport copy\b",
            r"\bsend (?:your )?bank details\b",
        ],
        "weight": 20,
        "severity": "medium",
        "reason": "Sensitive personal or financial information is mentioned.",
        "advice": "Verify the employer before sharing identity documents.",
    },
    {
        "id": "fake_check_or_money_transfer",
        "title": "Money transfer request",
        "patterns": [
            r"\btransfer money on our behalf\b",
            r"\breceive money and send\b",
            r"\bdeposit this cheque\b",
            r"\bdeposit this check\b",
            r"\buse your bank account to transfer\b",
        ],
        "weight": 35,
        "severity": "high",
        "reason": "The text may involve moving money for another party.",
        "advice": "Do not transfer funds or deposit checks for an unknown recruiter.",
    },
    {
        "id": "guaranteed_job",
        "title": "Guaranteed job claim",
        "patterns": [
            r"\b100% job guarantee\b",
            r"\bguaranteed placement\b",
            r"\bjob guaranteed\b",
            r"\bguaranteed selection\b",
        ],
        "weight": 12,
        "severity": "medium",
        "reason": "A guaranteed job or selection claim appears in the text.",
        "advice": "Confirm the selection process with the official employer.",
    },
    {
        "id": "unrealistic_earnings",
        "title": "Unusually high earnings claim",
        "patterns": [
            r"\bearn \u20b9?\s?\d[\d,]*\s*(?:per day|daily)\b",
            r"\bearn lakhs? (?:daily|per day)\b",
            r"\bget rich quick\b",
            r"\bno experience.*high salary\b",
            r"\bearn money instantly\b",
        ],
        "weight": 15,
        "severity": "medium",
        "reason": "The advertisement may make unusually attractive earnings claims.",
        "advice": "Compare the pay with the role and verify the employer's offer.",
    },
    {
        "id": "urgent_pressure",
        "title": "High-pressure language",
        "patterns": [
            r"\bapply immediately or lose\b",
            r"\blimited slots only\b",
            r"\bact now\b",
            r"\blast chance\b",
            r"\bpay within \d+ hours\b",
        ],
        "weight": 7,
        "severity": "low",
        "reason": "Urgent language may pressure applicants into quick decisions.",
        "advice": "Take time to verify the opportunity before responding.",
    },
    {
        "id": "task_review_scam",
        "title": "Paid review or rating tasks",
        "patterns": [
            r"\blike and review products for money\b",
            r"\bpay for giving reviews\b",
            r"\brate products to earn\b",
            r"\bgoogle maps review job\b",
        ],
        "weight": 18,
        "severity": "medium",
        "reason": "The role resembles a paid review or rating task offer.",
        "advice": "Check the business and never pay to access tasks.",
    },
    {
        "id": "referral_income",
        "title": "Referral-based earnings",
        "patterns": [
            r"\bearn by referring people\b",
            r"\brefer \d+ people to earn\b",
            r"\bcommission for every recruit\b",
        ],
        "weight": 8,
        "severity": "low",
        "reason": "Earnings may depend heavily on recruiting other people.",
        "advice": "Check whether there is a real job and clear compensation.",
    },
]


def analyse_ad(text: str) -> dict:
    warnings = []
    lower_text = text.lower()

    # Avoid flagging a fee rule when the ad clearly says no fee is charged.
    no_fee_claim = bool(re.search(
        r"\b(?:no|zero|without)\s+(?:any\s+)?"
        r"(?:registration|application|training)\s+fees?\b",
        lower_text,
    ))

    for rule in RULES:
        if rule["id"] in {
            "upfront_fee",
            "training_or_certificate_fee",
        } and no_fee_claim:
            continue

        matched = any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in rule["patterns"]
        )

        if matched:
            warnings.append({
                "id": rule["id"],
                "title": rule["title"],
                "severity": rule["severity"],
                "reason": rule["reason"],
                "advice": rule["advice"],
                "weight": rule["weight"],
            })

    urls = URL_PATTERN.findall(text)
    links_found = []

    for url in urls:
        clean_url = url.rstrip(".,);]")
        parsed = urlparse(clean_url)
        host = parsed.netloc.lower()

        suspicious = (
            host.endswith(".xyz")
            or host.endswith(".top")
            or "bit.ly" in host
            or "tinyurl.com" in host
            or "t.co" == host
        )

        links_found.append({
            "url": clean_url,
            "domain": host,
            "suspicious": suspicious,
        })

        if suspicious:
            warnings.append({
                "id": "suspicious_short_link",
                "title": "Potentially suspicious link",
                "severity": "medium",
                "reason": f"The link uses a short-link or unusual domain: {host}",
                "advice": "Open links only after checking the official company website.",
                "weight": 10,
            })

    if not COMPANY_PATTERN.search(text):
        warnings.append({
            "id": "missing_company",
            "title": "Company details may be missing",
            "severity": "low",
            "reason": "No clear company or employer label was found.",
            "advice": "Find the company's official website and verify the job listing.",
            "weight": 6,
        })

    if not EMAIL_PATTERN.search(text) and not PHONE_PATTERN.search(text):
        warnings.append({
            "id": "missing_contact",
            "title": "Contact details may be missing",
            "severity": "low",
            "reason": "No obvious email address or phone number was found.",
            "advice": "Look for official contact details before applying.",
            "weight": 4,
        })

    # Cap the score at 100.
    risk_score = min(100, sum(item["weight"] for item in warnings))

    if risk_score >= 60:
        risk_level = "High"
        message = "Several warning signs were detected. Verify carefully before proceeding."
    elif risk_score >= 30:
        risk_level = "Medium"
        message = "Some warning signs were detected. Check the employer and offer."
    else:
        risk_level = "Low"
        message = "Fewer warning signs were detected. This does not guarantee the job is genuine."

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "warning_count": len(warnings),
        "warnings": warnings,
        "links_found": links_found,
        "message": message,
        "disclaimer": (
            "This tool provides an automated risk estimate, not a final "
            "verdict. Always verify the employer independently."
        ),
    }


@app.get("/api/health")
def health():
    return {
        "status": "success",
        "message": "Python backend is working!",
    }


@app.post("/api/check")
def check_job(job: JobAd):
    text = job.text.strip()

    if not text:
        return {
            "received": False,
            "error": "Please enter a job advertisement.",
        }

    result = analyse_ad(text)

    result["received"] = True
    result["character_count"] = len(text)
    result["ml_prediction"] = "Unavailable"
    result["ml_fake_probability"] = None
    result["ml_explanation"] = (
        "The machine-learning model is not available. "
        "The rule-based checks are still being used."
    )

    if ml_model is not None:
        try:
            prediction = int(ml_model.predict([text])[0])
            result["ml_prediction"] = (
                "Fake" if prediction == 1 else "Genuine"
            )

            if hasattr(ml_model, "predict_proba"):
                probabilities = ml_model.predict_proba([text])[0]
                classes = list(ml_model.classes_)

                if 1 in classes:
                    fake_index = classes.index(1)
                    fake_probability = float(probabilities[fake_index])
                    result["ml_fake_probability"] = round(
                        fake_probability * 100, 2
                    )

            result["ml_explanation"] = (
                "This prediction comes from the trained ML model. "
                "It should be considered alongside the warning signs."
            )

        except (ValueError, TypeError, AttributeError) as error:
            result["ml_explanation"] = (
                f"The ML prediction could not be completed: {error}"
            )

    return result


# Keep this mount after all API routes.
if FRONTEND_DIR.exists():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIR), html=True),
        name="frontend",
    )
