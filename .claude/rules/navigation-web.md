---
paths:
  - Scripts/web_nav.py
  - Scripts/site_strategies.py
  - src/jobhunter/navigation/*.py
  - Scripts/apply_runner.py
  - Scripts/acces.py
---
# Navigation web et candidature

`web_nav.py` (3400 lignes, le plus gros morceau) pilote Playwright (standard, sans moteur furtif) :
bannières cookies, détection d'ATS, recherche d'offre, repli sur la page carrière.
`site_strategies.py` porte les stratégies par site. `apply_runner.py` remplit et
téléverse, **et s'arrête sur le bouton Envoyer**.

## Limites qui sont des décisions, pas des manques

Elles tiennent depuis le début du projet et ne se rediscutent pas au détour d'une tâche :

- **Aucune soumission automatique.** Le clic final d'envoi est celui de l'utilisateur. Dix
  envois automatiques en juillet ont donné zéro confirmation. N'ajouter aucun drapeau
  `--auto` / `--submit` à `apply_runner.py`.
- **Aucun contournement anti-bot** : ni empreinte TLS, ni rotation d'IP, ni résolution
  de CAPTCHA, ni moteur « furtif » (patchright, rebrowser), ni masquage de
  l'automatisation (`navigator.webdriver`, `--enable-automation`,
  `AutomationControlled`), ni souris ou frappe « humaines ». Le navigateur se
  présente comme automatisé.
- **Jamais le profil Chrome personnel** (`User Data`) : il porte les sessions et
  mots de passe de l'utilisateur. Seul le profil dédié de `acces.py` sert. Un CAPTCHA détecté met en pause pour un humain. Treize sites sont
  inaccessibles et le restent.
- **Aucun mot de passe manipulé par les programmes.** Les sessions vivent dans un
  profil Chrome dédié ; la connexion se fait une fois à la main via
  `Scripts/acces.py --open <site>`.
- **Aucune création de compte, aucune lecture de boîte mail par programme.** Un code
  reçu par mail (OTP) se lit et se saisit à la main.
