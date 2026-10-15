"""Régressions Indeed, sans réseau ni écriture sur les données réelles."""
import _profil_test  # noqa: F401  — les tests tournent sur le profil d'exemple
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from contextlib import redirect_stdout
from email.message import Message
from unittest.mock import patch

import job_sources as js


class Reponse(io.BytesIO):
    def __init__(self, texte, url="https://fr.indeed.com/jobs", headers=None):
        super().__init__(texte.encode())
        self.url, self.headers = url, headers or {}
    def geturl(self):
        return self.url


def page(offres):
    d = {"metaData": {"mosaicProviderJobCardsModel": {"results": offres}}}
    return Reponse('providerData["mosaic-provider-jobcards"] = ' + json.dumps(d))


def erreur(code, retry=None):
    h = Message()
    if retry is not None:
        h['Retry-After'] = str(retry)
    return urllib.error.HTTPError('https://fr.indeed.com/jobs', code, 'test', h, io.BytesIO())


class IndeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        for p in [patch.object(js, 'INDEED_ETAT', Path(self.tmp.name)/'rotation'),
                  patch.object(js, 'contrats_exclus', return_value=set()),
                  patch.object(js.time, 'sleep'),
                  patch('urllib.request.urlopen'), redirect_stdout(io.StringIO())]:
            obj = p.__enter__()
            self.addCleanup(p.__exit__, None, None, None)
            if getattr(p, 'attribute', '') == 'urlopen': self.http = obj
            if getattr(p, 'attribute', '') == 'sleep': self.sleep = obj
        js.INCIDENTS.clear()
        js.INDEED_REQUETES = 0

    def scan(self):
        return js.scan_indeed(mots=['analyste esg','finance durable'],lieux=['Paris'])

    def test_403_arrete_source_sans_attente(self):
        self.http.side_effect = erreur(403)
        self.assertEqual(self.scan(), [])
        self.assertEqual(self.http.call_count, 1)
        self.sleep.assert_not_called()
        self.assertEqual(js.INCIDENTS['indeed']['HTTP 403'], 1)

    def test_challenge_200(self):
        self.http.return_value = Reponse('<title>Security Check - Indeed.com</title>')
        self.assertEqual(self.scan(), [])
        self.assertEqual(self.http.call_count, 1)
        self.assertIn('challenge anti-bot',js.INCIDENTS['indeed'])

    def test_challenge_entete(self):
        self.http.return_value = Reponse('',headers={'cf-mitigated':'challenge'})
        self.assertEqual(self.scan(), [])
        self.assertEqual(self.http.call_count, 1)

    def test_connexion_requise(self):
        self.http.return_value = Reponse('',url='https://secure.indeed.com/auth')
        self.assertEqual(self.scan(), [])
        self.assertIn('connexion requise',js.INCIDENTS['indeed'])

    def test_format_absent(self):
        self.http.return_value = Reponse('<html>Maintenance</html>')
        self.assertEqual(self.scan(), [])
        self.assertIn('format de page non reconnu',js.INCIDENTS['indeed'])

    def test_vide_valide(self):
        self.http.side_effect = [page([]),page([])]
        self.assertEqual(self.scan(), [])
        self.assertFalse(js.INCIDENTS)
        self.assertEqual(self.http.call_count, 2)

    def test_carte_invalide_signalee(self):
        self.http.return_value = page([None])
        self.assertEqual(self.scan(), [])
        self.assertIn('format des offres non reconnu', js.INCIDENTS['indeed'])
        self.assertEqual(self.http.call_count, 1)

    def test_429_reprise(self):
        self.http.side_effect = [erreur(429,7), page([])]
        self.assertEqual(js._indeed_cartes('esg','Paris'), [])
        self.sleep.assert_called_once_with(7)
        self.assertEqual(self.http.call_count, 2)

    def test_429_persistant_arrete_source(self):
        self.http.side_effect = [erreur(429),erreur(429)]
        self.assertEqual(self.scan(), [])
        self.assertEqual(self.http.call_count, 2)
        self.sleep.assert_called_once_with(45)

    def test_retry_after_long_jamais_tronque(self):
        self.http.side_effect = erreur(429,600)
        self.assertEqual(self.scan(), [])
        self.assertEqual(self.http.call_count, 1)
        self.sleep.assert_not_called()

    def test_retry_after_date(self):
        from email.utils import formatdate
        with patch.object(js.time,'time',return_value=1000):
            self.http.side_effect = [erreur(429,formatdate(1060,usegmt=True)),page([])]
            self.assertEqual(js._indeed_cartes('esg','Paris'), [])
        self.sleep.assert_called_once_with(60)

    def test_offres_conservees_avant_refus(self):
        self.http.side_effect = [page([{'jobkey':'abc','title':'Analyste ESG','company':'Exemple','jobTypes':['CDI'],'snippet':'CSRD'}]),erreur(403)]
        offres = self.scan()
        self.assertEqual(len(offres),1)
        self.assertEqual(offres[0]['contrat'],'CDI')
        self.assertTrue(offres[0]['desc_partielle'])

    def test_cli_code_degrade_sans_mutation(self):
        js.INDEED_ETAT.write_text('7', encoding='utf-8')
        self.http.side_effect = erreur(403)
        with patch.object(sys,'argv',['job_sources.py','--indeed','--dry']), patch.object(js,'_fusionner',return_value=0) as fusion:
            self.assertEqual(js.main(),4)
        fusion.assert_called_once_with([],True)
        self.assertEqual(js.INDEED_ETAT.read_text(encoding='utf-8'), '7')


if __name__ == '__main__':
    unittest.main()
