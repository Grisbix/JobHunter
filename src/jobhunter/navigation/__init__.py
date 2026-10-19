"""Web navigation (Playwright): from a company's site to the filled-in form.

Formerly Scripts/web_nav.py (3,864 lines), split in phase 3.6 of the plan:

page          cookie banner (REFUSE first), page analysis, waiting for the form
etapes        two-step buttons, portals, menus, retries
carrieres     a company's career page, then the offer in it; fallback through the home page
formulaires   multi-screen wizard, document upload, filling in the application
segment       parts of a page, recognised ATS, send button HIGHLIGHTED
compte        step-by-step login (password NEVER typed), switch to sign-up
linkedin      Easy Apply: fills in, the human sends
llm           fallback through a local model (Ollama): vision, step-by-step agent
otp           code received by email: pastes, highlights Verify, the human clicks
navigateur    standard Playwright only, typing helpers, robust loading, session
categories    strategies per site category; their tables are in strategies
confirmation  after the send (done by the human): does the page confirm? proof

Captcha and anti-bot are DETECTED to hand over to the human, never bypassed;
no stealth engine. The final send click is always the user's.

FACADE (jobhunter._facade): `import web_nav` gives this package, which sees the names
of all the submodules like the old single file.
"""

from jobhunter import _facade

_MODULES = _facade.installer(
    __name__,
    (
        "page",
        "etapes",
        "carrieres",
        "formulaires",
        "llm",
        "compte",
        "segment",
        "linkedin",
        "navigateur",
        "otp",
        "categories",
        "confirmation",
    ),
)
