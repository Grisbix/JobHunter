# 0015 — An MSIX package for the Microsoft Store

Date: 2026-10-27. Status: accepted; the Store listing waits for the author's
Partner Center account.

## Context

`JobHunterSetup.exe` is not Authenticode-signed: no paid certificate, and SignPath
refused the project. Downloaded from a browser, it meets SmartScreen's « Windows a
protégé votre ordinateur », and a user must click « Informations complémentaires »
then « Exécuter quand même ». Many stop there.

winget avoids the warning (no Mark of the Web on what it downloads), but the
package request (microsoft/winget-pkgs#458350) waits for a volunteer moderator, and
winget is a command line.

## Decision

The installer workflow also packs the built application as `JobHunter.msix`
(`tools/installer/msix.py`) and attaches it to each release. It is unsigned: it is
the file uploaded to Partner Center, and the Store signs what it distributes with
Microsoft's certificate. An individual developer account is free.

Inside the package (`jobhunter.frozen.paquet_msix`), the update does not download
the installer: the package folder is read-only and Windows installs the Store's
updates. The button opens the Store's updates page instead.

The package identity (name, publisher) is the one Partner Center reserves; it comes
from the repository variables `MSIX_NOM`, `MSIX_EDITEUR`, `MSIX_EDITEUR_NOM`, never
from a file of the repository. Without them the package carries placeholders.

## Consequences

- Since 3.63 the package contains Playwright's `node.exe`, which the installer leaves
  out since 3.62 and downloads at the first browser: the Store's policy 10.2.2 forbids
  extending a product with downloaded code. Inside the package nothing is downloaded,
  neither the update nor Node.js.

- The installer and the ZIP stay: the Store is one more way in, not the only one.
- To check on a first Store install: the scheduled morning collection (the task
  calls `jobhunter-cli.exe` through the package's execution alias), and the
  Playwright browsers, which a packaged app stores in its own virtualised AppData.
- Steps left to the author: create the Partner Center account, reserve the name
  « JobHunter », copy the identity into the three variables, upload the release's
  `JobHunter.msix` and fill the listing (description, screenshots, privacy policy).
- **Updates sent by the CI** (job `store` of `installer.yml`): once the app is live,
  each release sends its `JobHunter.msix` as a new submission
  (`microsoft/microsoft-store-apppublisher`, Microsoft Store Developer CLI
  `msstore publish`). Microsoft's API only updates a published, free app; the
  first submission stays manual, and the Store certifies each update. The job stays
  off until the author, once:
  1. associates a Microsoft Entra ID tenant with the Partner Center account
     (Account settings → Tenants; free);
  2. registers an application in Entra ID, creates a client secret, and adds the
     application under Partner Center → User management → Microsoft Entra
     applications, role Manager;
  3. sets the repository secrets `AZURE_AD_TENANT_ID`, `SELLER_ID`,
     `AZURE_AD_APPLICATION_CLIENT_ID`, `AZURE_AD_APPLICATION_SECRET`, and the
     variable `MSSTORE_PRODUCT_ID` (the Store ID, 9N…), which turns the job on.
  Guide: https://learn.microsoft.com/windows/apps/publish/msstore-dev-cli/github-actions
