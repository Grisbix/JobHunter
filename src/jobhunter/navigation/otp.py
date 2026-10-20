"""Code received by email: pastes the code, highlights Verify, the human clicks.

Part of jobhunter.navigation (formerly Scripts/web_nav.py, phase 3.6).
"""

from typing import Any

# ── OTP / email code (SEMI-AUTOMATIC: pastes the code, highlights Verify, the human clicks) ──
_OTP_RX_ATTR = r"(otp|passcode|one.?time|verification|verif|\bcode\b|s[eé]cur|security|token|\bpin\b|2fa|mfa|activation|confirm)"


_OTP_DETECT_JS = r"""
() => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0; };
  const bad = ['hidden','checkbox','radio','file','submit','button','password'];
  const ins = [...document.querySelectorAll('input')].filter(vis).filter(e=>!bad.includes((e.type||'').toLowerCase()));
  const RX = /__OTP__/i;
  const single = ins.some(e => RX.test((e.name||'')+(e.id||'')+(e.placeholder||'')+(e.getAttribute('aria-label')||'')+(e.autocomplete||'')));
  const oc = ins.some(e => e.getAttribute('autocomplete')==='one-time-code');
  const boxes = ins.filter(e => e.maxLength===1).length >= 4;
  const bodyOtp = /(code (de |à |a )?(v[eé]rification|confirmation|s[eé]curit[eé])|verification code|one.?time (code|password|passcode)|entrez le code|enter the code|saisissez le code|passcode)/i
                  .test((document.body?document.body.innerText:'').slice(0,4000));
  return {otp: !!(single||oc||boxes||bodyOtp), single, oc, boxes, bodyOtp};
}
""".replace("__OTP__", _OTP_RX_ATTR)


_OTP_FILL_JS = r"""
(code) => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>0 && r.height>0; };
  const bad = ['hidden','checkbox','radio','file','submit','button','password'];
  const ins = [...document.querySelectorAll('input')].filter(vis).filter(e=>!bad.includes((e.type||'').toLowerCase()));
  const set = (el,v)=>{ el.focus(); el.value=v; el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); };
  const RX = /__OTP__/i;
  // 1) champ unique (name/id/placeholder/aria = code) et assez large
  const single = ins.find(e => RX.test((e.name||'')+(e.id||'')+(e.placeholder||'')+(e.getAttribute('aria-label')||'')) && (e.maxLength<0 || e.maxLength>=code.length));
  if (single) { set(single, code); return {filled:1, mode:'single'}; }
  // 2) autocomplete one-time-code
  const oc = ins.find(e => e.getAttribute('autocomplete')==='one-time-code');
  if (oc) { set(oc, code); return {filled:1, mode:'auto'}; }
  // 3) boîtes 1 chiffre (maxlength=1)
  const boxes = ins.filter(e => e.maxLength===1);
  if (boxes.length >= code.length) {
    for (let i=0;i<code.length;i++) set(boxes[i], code[i]);
    return {filled:code.length, mode:'boxes'};
  }
  return {filled:0, mode:'none'};
}
""".replace("__OTP__", _OTP_RX_ATTR)


_OTP_VERIFY_JS = r"""
() => {
  const vis = el => { const r=el.getBoundingClientRect(); return r.width>4 && r.height>4; };
  const RX = /(v[eé]rifier|verify|valider|validate|confirmer|confirm|soumettre|submit|continuer|continue|activer|activate|envoyer)/i;
  const NEVER = /(annuler|cancel|renvoyer|resend|renvoi|retour|back|modifier)/i;
  const els = [...document.querySelectorAll('button,input[type=submit],a,[role=button]')].filter(vis);
  for (const el of els) {
    const t = (el.innerText||el.value||el.getAttribute('aria-label')||'').trim();
    if (t && t.length<26 && RX.test(t) && !NEVER.test(t)) {
      el.style.outline='4px solid red'; el.style.outlineOffset='2px';
      el.setAttribute('data-wn-otp','verify'); el.scrollIntoView({block:'center'});
      return t;
    }
  }
  return '';
}
"""


def otp_present(page: Any) -> bool:
    """True if the page waits for an OTP code (code field / 1-digit boxes / text)."""
    try:
        return bool(page.evaluate(_OTP_DETECT_JS).get("otp"))
    except Exception:
        return False


def paste_otp(page: Any, code: Any) -> Any:
    """Pastes the OTP code into the field(s). Does NOT submit. Returns {filled, mode}."""
    if not code:
        return {"filled": 0, "mode": "no_code"}
    try:
        return page.evaluate(_OTP_FILL_JS, str(code).strip())
    except Exception as e:
        return {"filled": 0, "mode": "err:" + type(e).__name__}


def highlight_otp_verify(page: Any) -> Any:
    """Highlights in RED the Verify/Validate button (data-wn-otp=verify).

    Does NOT click. Returns the button's label, or '' if not found.
    """
    try:
        return page.evaluate(_OTP_VERIFY_JS)
    except Exception:
        return ""


def otp_flow(page: Any, code: Any) -> dict[str, Any]:
    """SEMI-AUTOMATIC: pastes the code + highlights the validation button.

    The HUMAN clicks. Returns {pasted, mode, verify}.
    """
    r = paste_otp(page, code)
    v = highlight_otp_verify(page) if r.get("filled") else ""
    return {"pasted": r.get("filled", 0), "mode": r.get("mode"), "verify": v}
